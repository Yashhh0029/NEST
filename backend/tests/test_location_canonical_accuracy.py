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
