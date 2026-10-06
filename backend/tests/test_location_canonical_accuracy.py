import uuid
import pytest
from app.db.database import SessionLocal
from app.models.location import Location
from app.models.request import Request
from app.models.request_location import RequestLocation
from app.models.user import User, UserRole
from app.schemas.location import LocationCreate
from app.schemas.request import RequestCreate
from app.services.google_maps_service import google_maps_service, haversine_km
from app.services.location_service import resolve_and_upsert_request_location
from app.services.profile_service import upsert_user_location
from app.services.request_service import create_user_request, get_nearby_requests_for_helper


# Constants for the two real distinct places in Maharashtra named Mahalunge:
PLACE_1_ID = "ChIJ3x-Canm2wjsRwPJ-IJb_4C8"  # Mahalunge, Maharashtra 410501 (Khed / Chakan)
PLACE_1_LAT = 18.755195
PLACE_1_LON = 73.809071
PLACE_1_ADDR = "Mahalunge, Maharashtra 410501, India"

PLACE_2_ID = "ChIJZdAjYE25wjsRrF_MZhrk_lU"  # Mahalunge, Pune, Maharashtra (near Hinjewadi / Balewadi)
PLACE_2_LAT = 18.57382
PLACE_2_LON = 73.756159
PLACE_2_ADDR = "Mahalunge, Pune, Maharashtra, India"


def test_haversine_distance_between_two_mahalunge_places():
    """
    Verify that the mathematical great-circle distance between Place 1 (Khed 410501)
    and Place 2 (Pune) is indeed 20.9 km, confirming the two places are distinct.
    """
    dist = haversine_km(PLACE_1_LAT, PLACE_1_LON, PLACE_2_LAT, PLACE_2_LON)
    assert round(dist, 1) == 20.9


def test_same_selected_place_id_yields_zero_km_distance():
    """
    When two users/requests select the same Place ID (e.g. Place 1),
    the distance between them must be 0.0 km.
    """
    dist = haversine_km(PLACE_1_LAT, PLACE_1_LON, PLACE_1_LAT, PLACE_1_LON)
    assert round(dist, 1) == 0.0


def test_request_target_location_enforces_selected_place_coordinates():
    """
    Test that resolve_and_upsert_request_location resolves canonical coordinates
    when google_place_id is provided, and synchronizes the Request model's columns.
    """
    db = SessionLocal()
    try:
        test_user = User(
            email=f"canonical_test_{uuid.uuid4().hex[:8]}@example.test",
            name="Canonical Tester",
            password_hash="hashed_pw",
            role=UserRole.NEWCOMER,
            is_active=True,
            email_verified=True,
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)

        # 1. Create a request selecting Place 1
        req1 = Request(
            user_id=test_user.id,
            raw_text="I need pg in Mahalunge",
            status="OPEN",
        )
        db.add(req1)
        db.commit()
        db.refresh(req1)

        rloc1 = resolve_and_upsert_request_location(
            db=db,
            request_id=req1.id,
            user=test_user,
            google_place_id=PLACE_1_ID,
            latitude=PLACE_1_LAT,
            longitude=PLACE_1_LON,
            formatted_address=PLACE_1_ADDR,
        )
        assert rloc1 is not None
        assert rloc1.google_place_id == PLACE_1_ID
        assert rloc1.latitude == PLACE_1_LAT
        assert rloc1.longitude == PLACE_1_LON
        # Request geography columns must be synchronized
        assert req1.city is not None

        # 2. Create a request selecting Place 2
        req2 = Request(
            user_id=test_user.id,
            raw_text="I need pg in Mahalunge Pune",
            status="OPEN",
        )
        db.add(req2)
        db.commit()
        db.refresh(req2)

        rloc2 = resolve_and_upsert_request_location(
            db=db,
            request_id=req2.id,
            user=test_user,
            google_place_id=PLACE_2_ID,
            latitude=PLACE_2_LAT,
            longitude=PLACE_2_LON,
            formatted_address=PLACE_2_ADDR,
        )
        assert rloc2 is not None
        assert rloc2.google_place_id == PLACE_2_ID
        assert rloc2.latitude == PLACE_2_LAT
        assert rloc2.longitude == PLACE_2_LON

        # Distance between req1 and req2 targets must be exactly 20.9 km
        dist = haversine_km(rloc1.latitude, rloc1.longitude, rloc2.latitude, rloc2.longitude)
        assert round(dist, 1) == 20.9

    finally:
        db.close()


def test_ambiguous_text_does_not_fabricate_coordinates():
    """
    Section 4 & 6: When a user creates a request without a selected place_id or coordinates,
    the system must NOT fabricate random coordinates via forward-geocoding centroids.
    Coordinates must remain None.
    """
    db = SessionLocal()
    try:
        test_user = User(
            email=f"ambiguous_test_{uuid.uuid4().hex[:8]}@example.test",
            name="Ambiguous Tester",
            password_hash="hashed_pw",
            role=UserRole.NEWCOMER,
            is_active=True,
            email_verified=True,
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)

        req = Request(
            user_id=test_user.id,
            raw_text="I need pg somewhere ambiguous",
            status="OPEN",
        )
        db.add(req)
        db.commit()
        db.refresh(req)

        rloc = resolve_and_upsert_request_location(
            db=db,
            request_id=req.id,
            user=test_user,
            city_hint="AmbiguousTown",
            area_hint="SomeArea",
            google_place_id=None,
            latitude=None,
            longitude=None,
        )
        assert rloc is not None
        # Must preserve text hints without fabricating coordinates
        assert rloc.latitude is None
        assert rloc.longitude is None
        assert rloc.city == "AmbiguousTown"
        assert rloc.area == "SomeArea"
        assert rloc.location_source == "nlp_unresolved"

    finally:
        db.close()


def test_profile_location_resolves_canonical_coordinates():
    """
    Section 3: When a user updates their profile location with a google_place_id,
    the stored profile location must contain canonical coordinates from the selected place.
    """
    db = SessionLocal()
    try:
        test_user = User(
            email=f"profile_test_{uuid.uuid4().hex[:8]}@example.test",
            name="Profile Tester",
            password_hash="hashed_pw",
            role=UserRole.HELPER,
            is_active=True,
            email_verified=True,
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)

        loc = upsert_user_location(
            db=db,
            user=test_user,
            loc_in=LocationCreate(
                city="Mahalunge",
                area="Near Hanuman mandir",
                display_name="Ahirant Society mahalunge",
                google_place_id=PLACE_1_ID,
                latitude=PLACE_1_LAT,
                longitude=PLACE_1_LON,
                formatted_address=PLACE_1_ADDR,
            ),
        )
        assert loc is not None
        assert loc.google_place_id == PLACE_1_ID
        assert loc.latitude == PLACE_1_LAT
        assert loc.longitude == PLACE_1_LON

    finally:
        db.close()


def test_nearby_feed_derives_display_from_canonical_request_location():
    """
    Section 8: Displayed location text in nearby requests feed must derive directly
    from the canonical RequestLocation record that holds the coordinates.
    """
    db = SessionLocal()
    try:
        helper_user = User(
            email=f"helper_feed_{uuid.uuid4().hex[:8]}@example.test",
            name="Helper Feed User",
            password_hash="hashed_pw",
            role=UserRole.HELPER,
            is_active=True,
            email_verified=True,
        )
        db.add(helper_user)
        db.commit()
        db.refresh(helper_user)

        # Set helper at Place 1
        upsert_user_location(
            db=db,
            user=helper_user,
            loc_in=LocationCreate(
                city="Mahalunge",
                google_place_id=PLACE_1_ID,
                latitude=PLACE_1_LAT,
                longitude=PLACE_1_LON,
                formatted_address=PLACE_1_ADDR,
            ),
        )

        newcomer_user = User(
            email=f"newcomer_feed_{uuid.uuid4().hex[:8]}@example.test",
            name="Newcomer Feed User",
            password_hash="hashed_pw",
            role=UserRole.NEWCOMER,
            is_active=True,
            email_verified=True,
        )
        db.add(newcomer_user)
        db.commit()
        db.refresh(newcomer_user)

        # Request at Place 1 (same place)
        req_same = Request(
            user_id=newcomer_user.id,
            raw_text="I need pg in Mahalunge north",
            status="OPEN",
        )
        db.add(req_same)
        db.commit()
        db.refresh(req_same)

        resolve_and_upsert_request_location(
            db=db,
            request_id=req_same.id,
            user=newcomer_user,
            google_place_id=PLACE_1_ID,
            latitude=PLACE_1_LAT,
            longitude=PLACE_1_LON,
            formatted_address=PLACE_1_ADDR,
            display_name="Mahalunge",
        )

        items = get_nearby_requests_for_helper(db=db, helper=helper_user)
        same_item = next((i for i in items if i.id == req_same.id), None)
        assert same_item is not None
        assert same_item.distance_km == 0.0
        assert same_item.city is not None

    finally:
        db.close()


def test_nearby_feed_boundary_20km_rule():
    """
    NEST NEARBY REQUESTS — CANONICAL 20 KM PRODUCT RULE:
    19.9 km -> visible
    20.0 km -> visible
    20.1 km -> EXCLUDED
    20.9 km -> EXCLUDED (proves live bug fix between Place 1 and Place 2)
    Ranoli, Gujarat -> EXCLUDED for helper in Pune
    """
    db = SessionLocal()
    try:
        # Helper at Place 2 (Mahalunge, Pune: lat=18.57382, lon=73.756159)
        helper = User(
            email=f"helper_20km_{uuid.uuid4().hex[:8]}@example.test",
            name="Pune Helper",
            password_hash="hashed_pw",
            role=UserRole.HELPER,
            is_active=True,
            email_verified=True,
        )
        db.add(helper)
        db.commit()
        db.refresh(helper)

        upsert_user_location(
            db=db,
            user=helper,
            loc_in=LocationCreate(
                city="Pune",
                area="Mahalunge",
                latitude=PLACE_2_LAT,
                longitude=PLACE_2_LON,
                formatted_address=PLACE_2_ADDR,
                google_place_id=PLACE_2_ID,
            ),
        )

        newcomer = User(
            email=f"newcomer_20km_{uuid.uuid4().hex[:8]}@example.test",
            name="Newcomer 20km",
            password_hash="hashed_pw",
            role=UserRole.NEWCOMER,
            is_active=True,
            email_verified=True,
        )
        db.add(newcomer)
        db.commit()
        db.refresh(newcomer)

        # 1. Candidate at 19.9 km
        lat_19_9 = PLACE_2_LAT + (19.9 / 111.195)
        req_19_9 = Request(user_id=newcomer.id, raw_text="Request 19.9 km", status="OPEN")
        db.add(req_19_9)
        db.commit()
        db.refresh(req_19_9)
        resolve_and_upsert_request_location(
            db=db, request_id=req_19_9.id, user=newcomer,
            latitude=lat_19_9, longitude=PLACE_2_LON,
            city_hint="Pune", area_hint="North Pune",
        )

        # 2. Candidate at 20.0 km
        lat_20_0 = PLACE_2_LAT + (20.0 / 111.195)
        req_20_0 = Request(user_id=newcomer.id, raw_text="Request 20.0 km", status="OPEN")
        db.add(req_20_0)
        db.commit()
        db.refresh(req_20_0)
        resolve_and_upsert_request_location(
            db=db, request_id=req_20_0.id, user=newcomer,
            latitude=lat_20_0, longitude=PLACE_2_LON,
            city_hint="Pune", area_hint="Outer Pune",
        )

        # 3. Candidate at 20.1 km (MUST BE EXCLUDED)
        lat_20_1 = PLACE_2_LAT + (20.1 / 111.195)
        req_20_1 = Request(user_id=newcomer.id, raw_text="Request 20.1 km", status="OPEN")
        db.add(req_20_1)
        db.commit()
        db.refresh(req_20_1)
        resolve_and_upsert_request_location(
            db=db, request_id=req_20_1.id, user=newcomer,
            latitude=lat_20_1, longitude=PLACE_2_LON,
            city_hint="Pune", area_hint="Beyond 20km",
        )

        # 4. Candidate at Place 1 (20.9 km away, Mahalunge Khed 410501 - MUST BE EXCLUDED)
        req_20_9 = Request(user_id=newcomer.id, raw_text="Request 20.9 km", status="OPEN")
        db.add(req_20_9)
        db.commit()
        db.refresh(req_20_9)
        resolve_and_upsert_request_location(
            db=db, request_id=req_20_9.id, user=newcomer,
            latitude=PLACE_1_LAT, longitude=PLACE_1_LON,
            google_place_id=PLACE_1_ID, formatted_address=PLACE_1_ADDR,
        )

        # 5. Candidate in Ranoli, Gujarat (~500 km away - MUST BE EXCLUDED)
        req_ranoli = Request(
            user_id=newcomer.id,
            raw_text="I'm moving to Ranoli, Gujarat for masters study. Searching for flat and food.",
            status="OPEN",
        )
        db.add(req_ranoli)
        db.commit()
        db.refresh(req_ranoli)
        resolve_and_upsert_request_location(
            db=db, request_id=req_ranoli.id, user=newcomer,
            latitude=22.3800, longitude=73.1800,
            city_hint="Ranoli", area_hint="Ranoli",
        )

        # Fetch feed for helper
        items = get_nearby_requests_for_helper(db=db, helper=helper)
        item_ids = {i.id for i in items}

        # Assertions
        assert req_19_9.id in item_ids, "19.9 km candidate must be visible"
        assert req_20_0.id in item_ids, "20.0 km candidate must be visible"
        assert req_20_1.id not in item_ids, "20.1 km candidate must be EXCLUDED"
        assert req_20_9.id not in item_ids, "20.9 km candidate must be EXCLUDED (20km rule)"
        assert req_ranoli.id not in item_ids, "Ranoli, Gujarat must be EXCLUDED for Pune helper"

        # Check distances returned
        item_19_9 = next(i for i in items if i.id == req_19_9.id)
        assert item_19_9.distance_km == 19.9

        item_20_0 = next(i for i in items if i.id == req_20_0.id)
        assert item_20_0.distance_km == 20.0

    finally:
        db.close()


def test_nearby_feed_location_precision_and_target_semantics():
    """
    Verify location precision differentiation and target location semantics:
    1. Area-level target (e.g. Mahalunge) preserves area-level precision ('locality'/'approximate').
    2. Street-level target (e.g. 'XYZ Road, Mahalunge, Pune') has exact precision ('street'/'rooftop').
    3. Requester profile location (e.g. 150 km away in Mumbai) does NOT affect matching or distance;
       only REQUEST TARGET LOCATION is used for helper proximity.
    """
    db = SessionLocal()
    try:
        helper = User(
            email=f"helper_prec_{uuid.uuid4().hex[:8]}@example.test",
            name="Precision Helper",
            password_hash="hashed_pw",
            role=UserRole.HELPER,
            is_active=True,
            email_verified=True,
        )
        db.add(helper)
        db.commit()
        db.refresh(helper)

        # Helper located in Pune at (18.57382, 73.756159)
        upsert_user_location(
            db=db,
            user=helper,
            loc_in=LocationCreate(
                city="Pune",
                area="Mahalunge",
                latitude=PLACE_2_LAT,
                longitude=PLACE_2_LON,
                formatted_address=PLACE_2_ADDR,
                google_place_id=PLACE_2_ID,
            ),
        )

        # Newcomer with profile location in Mumbai (~120 km away from Pune)
        newcomer_mumbai = User(
            email=f"newcomer_mum_{uuid.uuid4().hex[:8]}@example.test",
            name="Newcomer From Mumbai",
            password_hash="hashed_pw",
            role=UserRole.NEWCOMER,
            is_active=True,
            email_verified=True,
        )
        db.add(newcomer_mumbai)
        db.commit()
        db.refresh(newcomer_mumbai)

        upsert_user_location(
            db=db,
            user=newcomer_mumbai,
            loc_in=LocationCreate(
                city="Mumbai",
                area="Andheri",
                latitude=19.1136,
                longitude=72.8697,
                formatted_address="Andheri, Mumbai, Maharashtra",
            ),
        )

        # Newcomer creates request whose TARGET is XYZ Road, Mahalunge, Pune (3.7 km from helper)
        # Lat ~18.57382 + (3.7 / 111.195) = ~18.60709
        target_lat_3_7 = PLACE_2_LAT + (3.7 / 111.195)
        req_street = Request(
            user_id=newcomer_mumbai.id,
            raw_text="Need rental flat near XYZ Road, Mahalunge, Pune",
            status="OPEN",
        )
        db.add(req_street)
        db.commit()
        db.refresh(req_street)

        resolve_and_upsert_request_location(
            db=db,
            request_id=req_street.id,
            user=newcomer_mumbai,
            latitude=target_lat_3_7,
            longitude=PLACE_2_LON,
            city_hint="Pune",
            area_hint="Mahalunge",
            display_name="XYZ Road, Mahalunge, Pune",
            formatted_address="XYZ Road, Mahalunge, Pune, Maharashtra",
        )
        # Set precision to street
        rloc = db.query(RequestLocation).filter(RequestLocation.request_id == req_street.id).first()
        rloc.location_precision = "street"
        db.commit()

        # Newcomer creates area-level request for Mahalunge
        req_area = Request(
            user_id=newcomer_mumbai.id,
            raw_text="I am moving to Mahalunge, need general advice",
            status="OPEN",
        )
        db.add(req_area)
        db.commit()
        db.refresh(req_area)

        resolve_and_upsert_request_location(
            db=db,
            request_id=req_area.id,
            user=newcomer_mumbai,
            latitude=PLACE_2_LAT,
            longitude=PLACE_2_LON,
            city_hint="Pune",
            area_hint="Mahalunge",
            display_name="Mahalunge",
            formatted_address="Mahalunge, Pune, Maharashtra, India",
        )
        rloc_area = db.query(RequestLocation).filter(RequestLocation.request_id == req_area.id).first()
        rloc_area.location_precision = "locality"
        db.commit()

        # Helper queries feed
        items = get_nearby_requests_for_helper(db=db, helper=helper)
        item_street = next(i for i in items if i.id == req_street.id)
        item_area = next(i for i in items if i.id == req_area.id)

        # 1. Street target must show exact distance ~3.7 km and precision 'street'
        assert item_street is not None
        assert item_street.distance_km == 3.7
        assert item_street.location_precision == "street"

        # 2. Area target must show precision 'locality' (area-level)
        assert item_area is not None
        assert item_area.location_precision == "locality"

        # 3. Requester profile location (Mumbai, 120km away) did NOT cause distance to be 120km
        assert item_street.distance_km < 20.0
        assert item_area.distance_km < 20.0

    finally:
        db.close()


def test_autocomplete_location_bias_and_disambiguation():
    """
    Test that autocomplete_places supports locationBias and returns distinct Place IDs
    for same-name/ambiguous locations (e.g. Pune Mahalunge vs Khed Mahalunge).
    """
    # 1. Without bias or with Pune bias
    predictions = google_maps_service.autocomplete_places(
        input_text="Mahalunge",
        latitude=PLACE_2_LAT,
        longitude=PLACE_2_LON,
    )
    assert len(predictions) >= 2
    place_ids = [p.place_id for p in predictions]
    # Both distinct places must be present in suggestions for user disambiguation
    assert PLACE_2_ID in place_ids
    assert PLACE_1_ID in place_ids

    # 2. Verify place details for both places remain completely distinct
    det_pune = google_maps_service.get_place_details(PLACE_2_ID)
    det_khed = google_maps_service.get_place_details(PLACE_1_ID)

    assert det_pune is not None
    assert det_khed is not None
    assert det_pune.google_place_id == PLACE_2_ID
    assert det_khed.google_place_id == PLACE_1_ID
    assert det_pune.postal_code == "411045"
    assert det_khed.postal_code == "410501"
    assert round(det_pune.latitude, 2) == 18.57
    assert round(det_khed.latitude, 2) == 18.76


def test_pune_user_intentionally_searching_kochi_with_bias():
    """
    Verify that providing Pune coordinates as locationBias does NOT restrict or
    prevent searching another distant city/state such as Kochi, Kerala.
    """
    predictions = google_maps_service.autocomplete_places(
        input_text="Kochi",
        latitude=PLACE_2_LAT,
        longitude=PLACE_2_LON,
    )
    assert len(predictions) > 0
    # Must find Kochi despite Pune location bias
    matching = [p for p in predictions if "kochi" in p.main_text.lower() or "kochi" in p.description.lower()]
    assert len(matching) > 0


def test_reverse_geocoding_current_gps_around_mahalunge_pune():
    """
    Verify that GPS coordinates in the Pune/Balewadi/Mahalunge region (18.5738, 73.7561)
    resolve to the Pune area (PIN 411045), and NEVER to the Chakan/Khed side (PIN 410501).
    """
    resolved = google_maps_service.reverse_geocode(
        latitude=PLACE_2_LAT,
        longitude=PLACE_2_LON,
    )
    assert resolved is not None
    # Must resolve to Pune / Mahalunge / Balewadi, not Chakan / 410501
    assert resolved.postal_code == "411045"
    assert resolved.postal_code != "410501"
    assert resolved.city in ["Pune", "Mahalunge", "Balewadi"]
    assert resolved.state == "Maharashtra"


def test_gps_reverse_geocoding_strips_business_and_preserves_exact_device_coords():
    """
    Verify that reverse-geocoding browser GPS:
    1. NEVER stores a commercial business Place ID (e.g. hotel, shop, restaurant). google_place_id must be None.
    2. NEVER uses a business name (e.g. 'The Orchid Hotel Pune') as the user's geographic location.
    3. Preserves exact device latitude/longitude for authoritative distance matching.
    4. Extracts clean administrative components (neighborhood/area, locality/city, state, postal_code).
    5. Sets location_source to 'browser_geolocation'.
    """
    gps_lat = 18.57382
    gps_lon = 73.756159

    resolved = google_maps_service.reverse_geocode(
        latitude=gps_lat,
        longitude=gps_lon,
    )
    assert resolved is not None
    # 1. Commercial business Place ID blocked
    assert resolved.google_place_id is None

    # 2. Commercial establishment name stripped
    assert "The Orchid Hotel" not in resolved.name
    assert "The Orchid Hotel" not in resolved.display_name
    assert "The Orchid Hotel" not in resolved.formatted_address

    # 3. Exact device coordinates preserved
    assert resolved.latitude == pytest.approx(gps_lat, abs=1e-5)
    assert resolved.longitude == pytest.approx(gps_lon, abs=1e-5)

    # 4. Clean administrative components
    assert resolved.city in ["Pune", "Mahalunge", "Balewadi"]
    assert resolved.state == "Maharashtra"
    assert resolved.postal_code == "411045"
    assert resolved.country == "India"
    assert resolved.location_source == "browser_geolocation"
    assert resolved.location_precision in ["neighborhood", "locality"]


def test_administrative_hierarchy_and_mahalunge_disambiguation():
    """
    Verify full administrative hierarchy:
    - Mahalunge Khed (18.755195, 73.809071) resolves with Taluka Khed, District Pune, PIN 410501
    - Mahalunge Pune (18.57382, 73.756159) resolves with District Pune, PIN 411045
    - The two locations are clearly differentiated by coordinates, PIN, and administrative hierarchy
    """
    khed_res = google_maps_service.reverse_geocode(18.755195, 73.809071)
    assert khed_res is not None
    assert khed_res.taluka == "Khed"
    assert khed_res.district == "Pune"
    assert khed_res.postal_code == "410501"
    assert "Khed" in khed_res.display_name
    assert "410501" in khed_res.formatted_address

    pune_res = google_maps_service.reverse_geocode(18.57382, 73.756159)
    assert pune_res is not None
    assert pune_res.postal_code == "411045"
    assert pune_res.district == "Pune"
    assert pune_res.postal_code != khed_res.postal_code




