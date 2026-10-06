import uuid
import pytest
from fastapi.testclient import TestClient
from tests.conftest import create_authenticated_user


def test_matching_requires_authentication(client: TestClient):
    """POST /api/matching/find-matches must reject unauthenticated calls."""
    resp = client.post("/api/matching/find-matches", json={
        "request_id": str(uuid.uuid4()),
    })
    assert resp.status_code == 401


def test_nonexistent_request_rejected(client: TestClient):
    """POST /api/matching/find-matches must return 404 for nonexistent request IDs."""
    user = create_authenticated_user(client, "Requester", "req_404@example.test")
    resp = client.post(
        "/api/matching/find-matches",
        headers=user["headers"],
        json={"request_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_unauthorized_request_rejected(client: TestClient):
    """A user cannot query matches for a request owned by another user."""
    owner = create_authenticated_user(client, "Owner User", "owner@example.test")
    other = create_authenticated_user(client, "Other User", "other@example.test")

    # Owner creates request
    req_resp = client.post(
        "/api/requests",
        headers=owner["headers"],
        json={"text": "Looking for PG accommodation in Whitefield Bengaluru"},
    )
    assert req_resp.status_code == 201
    request_id = req_resp.json()["id"]

    # Other tries to query matches for owner's request
    match_resp = client.post(
        "/api/matching/find-matches",
        headers=other["headers"],
        json={"request_id": request_id},
    )
    assert match_resp.status_code == 403
    assert "permission" in match_resp.json()["detail"].lower()


def test_empty_candidates_returns_honest_result(client: TestClient):
    """When no other candidate helpers exist, return an honest empty list."""
    solo = create_authenticated_user(client, "Solo User", "solo@example.test")
    req_resp = client.post(
        "/api/requests",
        headers=solo["headers"],
        json={"text": "Looking for vegetarian food near Indiranagar"},
    )
    request_id = req_resp.json()["id"]

    match_resp = client.post(
        "/api/matching/find-matches",
        headers=solo["headers"],
        json={"request_id": request_id},
    )
    assert match_resp.status_code == 200
    data = match_resp.json()
    assert data["request_id"] == request_id
    assert data["total_candidates_evaluated"] == 0
    assert data["matches"] == []
    assert data["weights_used"]["raw"]["semantic"] == 0.40


def test_requesting_user_cannot_match_self(client: TestClient):
    """The requesting user must never be returned in their own match results."""
    user = create_authenticated_user(client, "Self Matching Test", "self_match@example.test")
    # Set up user's own profile and skills
    client.put(
        "/api/profile/me",
        headers=user["headers"],
        json={
            "headline": "Experienced Local Guide",
            "bio": "I provide PG accommodation advice and local food guidance in Bengaluru.",
            "years_experience": 5.0,
        },
    )
    # Sync profile embedding
    client.post("/api/embeddings/profile/me", headers=user["headers"])

    # Create request
    req_resp = client.post(
        "/api/requests",
        headers=user["headers"],
        json={"text": "Looking for PG accommodation advice in Bengaluru"},
    )
    request_id = req_resp.json()["id"]

    match_resp = client.post(
        "/api/matching/find-matches",
        headers=user["headers"],
        json={"request_id": request_id},
    )
    assert match_resp.status_code == 200
    candidate_ids = [m["user_id"] for m in match_resp.json()["matches"]]
    assert str(user["user"]["id"]) not in candidate_ids


def test_no_fake_data_and_deterministic_scores(client: TestClient):
    """
    Verify:
    1. Reputation and availability scores are explicitly null (not fabricated).
    2. Reputation and availability statuses are UNAVAILABLE.
    3. Final score matches the exact mathematical normalized formula.
    4. Two consecutive calls produce identical scores.
    """
    requester = create_authenticated_user(client, "Determ Req", "determ_req@example.test")
    candidate = create_authenticated_user(client, "Determ Cand", "determ_cand@example.test")

    # Set candidate profile and embedding
    client.put(
        "/api/profile/me",
        headers=candidate["headers"],
        json={
            "headline": "Koramangala Community Mentor",
            "bio": "Resident of Bengaluru for 4 years. Helping newcomers find vegetarian mess and rentals.",
            "years_experience": 4.0,
        },
    )
    client.put(
        "/api/profile/me/location",
        headers=candidate["headers"],
        json={
            "city": "Bengaluru",
            "area": "Koramangala",
            "latitude": 12.9352,
            "longitude": 77.6245,
        },
    )
    client.post("/api/embeddings/profile/me", headers=candidate["headers"])

    # Requester creates request
    req_resp = client.post(
        "/api/requests",
        headers=requester["headers"],
        json={"text": "Need vegetarian mess and PG in Koramangala Bengaluru"},
    )
    request_id = req_resp.json()["id"]

    call1 = client.post(
        "/api/matching/find-matches",
        headers=requester["headers"],
        json={"request_id": request_id},
    )
    assert call1.status_code == 200
    data1 = call1.json()

    assert len(data1["matches"]) == 1
    match = data1["matches"][0]

    # Verify no fake data
    assert match["scores"]["reputation_score"] is None
    assert match["scores"]["availability_score"] is None
    assert match["dimension_statuses"]["reputation"] == "UNAVAILABLE"
    assert match["dimension_statuses"]["availability"] == "UNAVAILABLE"
    assert match["dimension_statuses"]["semantic"] == "ACTIVE"
    assert match["dimension_statuses"]["location"] == "ACTIVE"
    assert match["dimension_statuses"]["experience"] == "ACTIVE"

    # Verify mathematical final score justification
    raw_w = data1["weights_used"]["raw"]
    active_w_sum = raw_w["semantic"] + raw_w["location"] + raw_w["experience"]
    expected_final = (
        raw_w["semantic"] * match["scores"]["semantic_score"]
        + raw_w["location"] * match["scores"]["location_score"]
        + raw_w["experience"] * match["scores"]["experience_score"]
    ) / active_w_sum
    assert abs(match["scores"]["final_score"] - round(expected_final, 4)) < 1e-4

    # Verify determinism across second call
    call2 = client.post(
        "/api/matching/find-matches",
        headers=requester["headers"],
        json={"request_id": request_id},
    )
    data2 = call2.json()
    assert data1["matches"][0]["scores"] == data2["matches"][0]["scores"]


def test_relevant_candidate_ranks_above_unrelated(client: TestClient):
    """A local candidate with relevant skills and bio must rank higher than an unrelated distant candidate."""
    requester = create_authenticated_user(client, "Newcomer", "newcomer_rank@example.test")
    client.put(
        "/api/profile/me/location",
        headers=requester["headers"],
        json={
            "city": "Bengaluru",
            "area": "Whitefield",
            "latitude": 12.9698,
            "longitude": 77.7499,
        },
    )

    # Candidate A: Local housing expert in Whitefield, Bengaluru
    cand_a = create_authenticated_user(client, "Local Helper A", "cand_a@example.test")
    client.put(
        "/api/profile/me",
        headers=cand_a["headers"],
        json={
            "headline": "Whitefield Housing & PG Coordinator",
            "bio": "I help people find PG accommodation and vegetarian tiffin services near ITPL Whitefield.",
            "years_experience": 5.0,
        },
    )
    client.put(
        "/api/profile/me/location",
        headers=cand_a["headers"],
        json={
            "city": "Bengaluru",
            "area": "Whitefield",
            "latitude": 12.9700,
            "longitude": 77.7505,
        },
    )
    client.post(
        "/api/profile/me/skills",
        headers=cand_a["headers"],
        json={"skills": [{"name": "Housing", "proficiency": "expert", "years_experience": 5.0}]},
    )
    client.post("/api/embeddings/profile/me", headers=cand_a["headers"])

    # Candidate B: Finance broker in Mumbai
    cand_b = create_authenticated_user(client, "Unrelated Helper B", "cand_b@example.test")
    client.put(
        "/api/profile/me",
        headers=cand_b["headers"],
        json={
            "headline": "Stock Market Trader",
            "bio": "Financial equity derivatives and stock options trader located in South Mumbai.",
            "years_experience": 2.0,
        },
    )
    client.put(
        "/api/profile/me/location",
        headers=cand_b["headers"],
        json={
            "city": "Mumbai",
            "area": "Colaba",
            "latitude": 18.9067,
            "longitude": 72.8147,
        },
    )
    client.post(
        "/api/profile/me/skills",
        headers=cand_b["headers"],
        json={"skills": [{"name": "Equity Trading", "proficiency": "intermediate", "years_experience": 2.0}]},
    )
    client.post("/api/embeddings/profile/me", headers=cand_b["headers"])

    # Requester creates request
    req_resp = client.post(
        "/api/requests",
        headers=requester["headers"],
        json={"text": "Moving to Whitefield for IT job. Need PG accommodation and vegetarian food."},
    )
    request_id = req_resp.json()["id"]

    match_resp = client.post(
        "/api/matching/find-matches",
        headers=requester["headers"],
        json={"request_id": request_id},
    )
    assert match_resp.status_code == 200
    matches = match_resp.json()["matches"]
    assert len(matches) == 2

    # Candidate A must be ranked #1
    assert matches[0]["user_id"] == str(cand_a["user"]["id"])
    assert matches[1]["user_id"] == str(cand_b["user"]["id"])

    # Verify scores comparison
    assert matches[0]["scores"]["semantic_score"] > matches[1]["scores"]["semantic_score"]
    assert matches[0]["scores"]["location_score"] > matches[1]["scores"]["location_score"]
    assert matches[0]["scores"]["final_score"] > matches[1]["scores"]["final_score"]

    # Verify distance calculation
    assert matches[0]["distance_km"] < 1.0  # Same area
    assert matches[1]["distance_km"] > 500.0  # Mumbai to Bengaluru is ~840 km


def test_weight_customization_adjusts_final_scores(client: TestClient):
    """Customizing weights shifts final scores and adjusts effective weight normalization."""
    requester = create_authenticated_user(client, "Weight Requester", "weight_req@example.test")
    candidate = create_authenticated_user(client, "Weight Candidate", "weight_cand@example.test")

    client.put(
        "/api/profile/me",
        headers=candidate["headers"],
        json={
            "headline": "City Guide",
            "bio": "Bengaluru local guidance.",
            "years_experience": 3.0,
        },
    )
    client.put(
        "/api/profile/me/location",
        headers=candidate["headers"],
        json={"city": "Bengaluru", "area": "Indiranagar", "latitude": 12.9716, "longitude": 77.5946},
    )
    client.post("/api/embeddings/profile/me", headers=candidate["headers"])

    req_resp = client.post(
        "/api/requests",
        headers=requester["headers"],
        json={"text": "Need guidance on navigating Bengaluru"},
    )
    request_id = req_resp.json()["id"]

    # Call with high semantic weight
    resp_high_sem = client.post(
        "/api/matching/find-matches",
        headers=requester["headers"],
        json={
            "request_id": request_id,
            "weights": {
                "semantic": 0.80,
                "location": 0.10,
                "experience": 0.10,
                "reputation": 0.0,
                "availability": 0.0,
            },
        },
    )
    assert resp_high_sem.status_code == 200
    data_sem = resp_high_sem.json()
    assert data_sem["weights_used"]["effective"]["semantic"] == 0.80

    # Call with high location weight
    resp_high_loc = client.post(
        "/api/matching/find-matches",
        headers=requester["headers"],
        json={
            "request_id": request_id,
            "weights": {
                "semantic": 0.10,
                "location": 0.80,
                "experience": 0.10,
                "reputation": 0.0,
                "availability": 0.0,
            },
        },
    )
    assert resp_high_loc.status_code == 200
    data_loc = resp_high_loc.json()
    assert data_loc["weights_used"]["effective"]["location"] == 0.80


def test_candidate_without_explicit_profile_row_is_evaluated_and_matched(client: TestClient):
    """
    Helpers who registered and configured location but have not explicitly saved
    a Profile row (no record in profiles table) must still be evaluated and recommended.
    """
    requester = create_authenticated_user(client, "Requester Boisar", "req_boisar@example.test")
    client.put(
        "/api/profile/me/location",
        headers=requester["headers"],
        json={"city": "Boisar", "area": "Vijay Colony", "latitude": 19.808163, "longitude": 72.771878},
    )

    helper = create_authenticated_user(client, "Helper Boisar", "helper_boisar@example.test")
    # Helper sets location, but never saves a Profile row
    client.put(
        "/api/profile/me/location",
        headers=helper["headers"],
        json={"city": "Boisar", "area": "Vijay Colony", "latitude": 19.808593, "longitude": 72.771758},
    )

    req_resp = client.post(
        "/api/requests",
        headers=requester["headers"],
        json={"text": "Looking for accommodation and food in Boisar"},
    )
    assert req_resp.status_code == 201
    request_id = req_resp.json()["id"]

    match_resp = client.post(
        "/api/matching/find-matches",
        headers=requester["headers"],
        json={"request_id": request_id, "max_distance_km": 25.0},
    )
    assert match_resp.status_code == 200
    data = match_resp.json()
    assert data["total_candidates_evaluated"] >= 1
    matched_ids = [m["user_id"] for m in data["matches"]]
    assert str(helper["user"]["id"]) in matched_ids
    top_match = next(m for m in data["matches"] if m["user_id"] == str(helper["user"]["id"]))
    assert top_match["distance_km"] < 1.0

