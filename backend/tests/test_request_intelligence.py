from datetime import datetime, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
from tests.conftest import create_authenticated_user
from app.db.database import SessionLocal
from app.models.community import CommunityQuestion
from app.models.connection import Connection, ConnectionStatus
from app.models.request import Request, RequestSavedResource
from app.models.user import User, UserRole


# ============================================================================
# 1. Unauthenticated & IDOR Protection Tests
# ============================================================================

def test_unauthenticated_and_idor_protection(client: TestClient):
    alice = create_authenticated_user(client, "Alice Intel", f"alice_intel_{uuid.uuid4().hex[:6]}@example.test")
    bob = create_authenticated_user(client, "Bob Intel", f"bob_intel_{uuid.uuid4().hex[:6]}@example.test")

    # Alice creates a request
    res_req = client.post("/api/requests", headers=alice["headers"], json={
        "text": "Moving to Hinjewadi for my first job. Need a cheap PG under 10000, tiffin food, and bus commute.",
    })
    assert res_req.status_code == 201
    req_id = res_req.json()["id"]

    # 1. Unauthenticated access returns 401
    res_unauth = client.get(f"/api/requests/{req_id}/intelligence")
    assert res_unauth.status_code == 401

    # 2. Bob attempts to access Alice's intelligence -> 403 Forbidden
    res_bob_intel = client.get(f"/api/requests/{req_id}/intelligence", headers=bob["headers"])
    assert res_bob_intel.status_code == 403
    assert "permission" in res_bob_intel.json()["detail"].lower()

    # 3. Bob attempts to update Alice's need progress -> 403 Forbidden
    res_bob_prog = client.patch(f"/api/requests/{req_id}/need-progress", headers=bob["headers"], json={
        "category": "accommodation",
        "status": "RESOLVED",
    })
    assert res_bob_prog.status_code == 403

    # 4. Bob attempts to save a resource to Alice's request -> 403 Forbidden
    res_bob_save = client.post(f"/api/requests/{req_id}/saved-resources", headers=bob["headers"], json={
        "place_id": "test_place_123",
        "name": "Stolen PG",
        "category": "accommodation",
    })
    assert res_bob_save.status_code == 403

    # 5. Bob attempts to mark Alice's request resolved -> 403 Forbidden
    res_bob_resolve = client.post(f"/api/requests/{req_id}/resolve", headers=bob["headers"], json={
        "resolution_summary": "Hacked",
    })
    assert res_bob_resolve.status_code == 403


# ============================================================================
# 2. Need Decomposition & Unified Discovery
# ============================================================================

def test_need_decomposition_and_unified_discovery(client: TestClient):
    alice = create_authenticated_user(client, "Alice Dec", f"alice_dec_{uuid.uuid4().hex[:6]}@example.test")
    helper = create_authenticated_user(client, "Helper Tech", f"helper_tech_{uuid.uuid4().hex[:6]}@example.test")

    # Give helper skills and profile in Pune
    client.post("/api/profile", headers=helper["headers"], json={
        "headline": "Experienced Pune Techie & Housing Guide",
        "bio": "Living in Hinjewadi for 4 years. Can help with PG accommodation and local food.",
        "years_experience": 4,
    })
    client.post("/api/profile/skills", headers=helper["headers"], json={
        "skills": ["Relocation & Housing", "Food & Cooking", "Transit & Commute"],
    })
    client.post("/api/location/primary", headers=helper["headers"], json={
        "city": "Pune",
        "area": "Hinjewadi",
        "location_source": "manual",
    })

    # Create a community question about Hinjewadi PGs
    client.post("/api/community/questions", headers=helper["headers"], json={
        "title": "Best PG accommodation options in Hinjewadi Phase 1",
        "body": "Detailed guide on rent, deposits, and food quality near Phase 1 circle.",
        "category": "ACCOMMODATION",
        "city": "Pune",
        "area": "Hinjewadi",
    })

    # Alice creates structured request
    res_req = client.post("/api/requests", headers=alice["headers"], json={
        "text": "Moving to Hinjewadi next week. Need PG accommodation under 9000, tiffin food service, and local transport guidance.",
    })
    assert res_req.status_code == 201
    req_id = res_req.json()["id"]

    # Retrieve unified intelligence
    res_intel = client.get(f"/api/requests/{req_id}/intelligence", headers=alice["headers"])
    assert res_intel.status_code == 200
    intel = res_intel.json()

    assert intel["request_id"] == req_id
    assert intel["status"] == "OPEN"
    assert intel["city"] == "Pune"
    assert intel["area"] == "Hinjewadi"
    assert intel["total_needs"] >= 2
    assert intel["resolved_needs"] == 0
    assert intel["progress_percentage"] == 0.0

    # Verify action plan exists with deterministic actionable steps
    assert isinstance(intel["action_plan"], list)
    assert len(intel["action_plan"]) >= 1

    # Verify need bundles
    categories = [b["category"].lower() for b in intel["needs"]]
    assert any("accommodation" in c for c in categories)

    # Check accommodation bundle has community questions and/or helpers
    accom_bundle = next(b for b in intel["needs"] if "accommodation" in b["category"].lower())
    assert accom_bundle["status"] == "UNRESOLVED"
    assert isinstance(accom_bundle["matched_helpers"], list)
    assert isinstance(accom_bundle["community_questions"], list)
    assert isinstance(accom_bundle["local_resources"], list)


# ============================================================================
# 3. Saved Resources Lifecycle
# ============================================================================

def test_saved_resources_lifecycle(client: TestClient):
    alice = create_authenticated_user(client, "Alice Res", f"alice_res_{uuid.uuid4().hex[:6]}@example.test")

    res_req = client.post("/api/requests", headers=alice["headers"], json={
        "text": "Looking for tiffin service in Baner Pune.",
    })
    req_id = res_req.json()["id"]

    # 1. Save resource
    res_save = client.post(f"/api/requests/{req_id}/saved-resources", headers=alice["headers"], json={
        "place_id": "chij_tiffin_baner_1",
        "name": "Annapurna Healthy Tiffin Services",
        "category": "food",
        "formatted_address": "Near Balewadi High Street, Baner, Pune",
        "rating": 4.6,
        "user_ratings_total": 42,
        "latitude": 18.5590,
        "longitude": 73.7868,
        "notes": "Delivers lunch and dinner, pure veg.",
    })
    assert res_save.status_code == 201
    saved_data = res_save.json()
    assert saved_data["place_id"] == "chij_tiffin_baner_1"
    assert saved_data["rating"] == 4.6
    assert saved_data["notes"] == "Delivers lunch and dinner, pure veg."

    # 2. List saved resources
    res_list = client.get(f"/api/requests/{req_id}/saved-resources", headers=alice["headers"])
    assert res_list.status_code == 200
    items = res_list.json()
    assert len(items) == 1
    assert items[0]["place_id"] == "chij_tiffin_baner_1"

    # 3. Idempotent save with updated notes
    res_upsert = client.post(f"/api/requests/{req_id}/saved-resources", headers=alice["headers"], json={
        "place_id": "chij_tiffin_baner_1",
        "name": "Annapurna Healthy Tiffin Services",
        "category": "food",
        "notes": "Called them: 3000/month for 2 meals daily.",
    })
    assert res_upsert.status_code == 201
    assert res_upsert.json()["notes"] == "Called them: 3000/month for 2 meals daily."

    # 4. Delete saved resource
    res_del = client.delete(f"/api/requests/{req_id}/saved-resources/chij_tiffin_baner_1", headers=alice["headers"])
    assert res_del.status_code == 204

    # Verify empty
    res_list_after = client.get(f"/api/requests/{req_id}/saved-resources", headers=alice["headers"])
    assert len(res_list_after.json()) == 0


# ============================================================================
# 4. Entity Validation & Anti-Injection on Need Progress
# ============================================================================

def test_entity_validation_on_need_progress(client: TestClient):
    alice = create_authenticated_user(client, "Alice Val", f"alice_val_{uuid.uuid4().hex[:6]}@example.test")
    bob = create_authenticated_user(client, "Bob Val", f"bob_val_{uuid.uuid4().hex[:6]}@example.test")

    res_req = client.post("/api/requests", headers=alice["headers"], json={
        "text": "Need PG accommodation in Wakad Pune.",
    })
    req_id = res_req.json()["id"]

    # 1. Invalid UUID format for connection
    res_bad_uuid = client.patch(f"/api/requests/{req_id}/need-progress", headers=alice["headers"], json={
        "category": "accommodation",
        "status": "RESOLVED",
        "resolved_via": "connection",
        "resolved_entity_id": "not-a-valid-uuid",
    })
    assert res_bad_uuid.status_code == 400

    # 2. Non-existent connection UUID
    fake_conn_id = str(uuid.uuid4())
    res_fake_conn = client.patch(f"/api/requests/{req_id}/need-progress", headers=alice["headers"], json={
        "category": "accommodation",
        "status": "RESOLVED",
        "resolved_via": "connection",
        "resolved_entity_id": fake_conn_id,
    })
    assert res_fake_conn.status_code == 404

    # 3. Connection belonging to Bob's different request
    res_bob_req = client.post("/api/requests", headers=bob["headers"], json={
        "text": "Bob's separate request.",
    })
    bob_req_id = res_bob_req.json()["id"]

    db = SessionLocal()
    try:
        bob_conn = Connection(
            id=uuid.uuid4(),
            request_id=uuid.UUID(bob_req_id),
            requester_id=uuid.UUID(bob["user"]["id"]),
            helper_id=uuid.UUID(alice["user"]["id"]),
            status=ConnectionStatus.ACCEPTED.value,
        )
        db.add(bob_conn)
        db.commit()
        bob_conn_id = str(bob_conn.id)
    finally:
        db.close()

    # Alice tries to claim resolution using Bob's connection ID -> 400 Bad Request
    res_mismatched_conn = client.patch(f"/api/requests/{req_id}/need-progress", headers=alice["headers"], json={
        "category": "accommodation",
        "status": "RESOLVED",
        "resolved_via": "connection",
        "resolved_entity_id": bob_conn_id,
    })
    assert res_mismatched_conn.status_code == 400
    assert "does not belong to this request" in res_mismatched_conn.json()["detail"].lower()


# ============================================================================
# 5. Connection Completion != Need Resolution (Mandatory Adjustment 3)
# ============================================================================

def test_connection_completion_does_not_force_resolution(client: TestClient):
    alice = create_authenticated_user(client, "Alice Rule3", f"alice_r3_{uuid.uuid4().hex[:6]}@example.test")
    bob = create_authenticated_user(client, "Bob Rule3", f"bob_r3_{uuid.uuid4().hex[:6]}@example.test")

    res_req = client.post("/api/requests", headers=alice["headers"], json={
        "text": "Need PG accommodation in Baner Pune.",
    })
    req_id = res_req.json()["id"]

    # Create and accept connection
    res_conn = client.post("/api/connections", headers=alice["headers"], json={
        "request_id": req_id,
        "helper_id": bob["user"]["id"],
        "initial_message": "Can you help me find a PG?",
    })
    conn_id = res_conn.json()["id"]

    client.post(f"/api/connections/{conn_id}/accept", headers=bob["headers"])

    # Mark connection COMPLETED
    client.post(f"/api/connections/{conn_id}/complete", headers=alice["headers"])

    # Verify need in intelligence is NOT automatically RESOLVED (remains UNRESOLVED or EXPLORING)
    res_intel = client.get(f"/api/requests/{req_id}/intelligence", headers=alice["headers"])
    intel = res_intel.json()

    accom_bundle = next(b for b in intel["needs"] if "accommodation" in b["category"].lower())
    assert accom_bundle["status"] != "RESOLVED"
    assert intel["status"] != "RESOLVED"

    # Only when Alice explicitly marks it resolved does it become RESOLVED
    res_resolve_need = client.patch(f"/api/requests/{req_id}/need-progress", headers=alice["headers"], json={
        "category": "accommodation",
        "status": "RESOLVED",
        "resolved_via": "connection",
        "resolved_entity_id": conn_id,
        "notes": "Bob showed me a great PG.",
    })
    assert res_resolve_need.status_code == 200
    intel_after = res_resolve_need.json()
    accom_after = next(b for b in intel_after["needs"] if "accommodation" in b["category"].lower())
    assert accom_after["status"] == "RESOLVED"
    assert intel_after["status"] == "RESOLVED"


# ============================================================================
# 6. Request State Transitions: PARTIALLY_RESOLVED vs RESOLVED
# ============================================================================

def test_request_state_transitions(client: TestClient):
    alice = create_authenticated_user(client, "Alice Trans", f"alice_trans_{uuid.uuid4().hex[:6]}@example.test")

    # Request with 2 needs: accommodation and food
    res_req = client.post("/api/requests", headers=alice["headers"], json={
        "text": "Need 1BHK flat accommodation and tiffin food service in Kothrud Pune.",
    })
    req_id = res_req.json()["id"]

    # Initial state
    intel_init = client.get(f"/api/requests/{req_id}/intelligence", headers=alice["headers"]).json()
    assert intel_init["status"] == "OPEN"
    assert intel_init["resolved_needs"] == 0

    # 1. Resolve first need (accommodation) -> PARTIALLY_RESOLVED
    res_p1 = client.patch(f"/api/requests/{req_id}/need-progress", headers=alice["headers"], json={
        "category": "accommodation",
        "status": "RESOLVED",
        "resolved_via": "manual",
        "notes": "Found flat through family.",
    })
    assert res_p1.status_code == 200
    intel_p1 = res_p1.json()
    assert intel_p1["status"] == "PARTIALLY_RESOLVED"
    assert intel_p1["resolved_needs"] == 1
    assert intel_p1["progress_percentage"] > 0

    # 2. Overall resolution endpoint resolves everything
    res_all = client.post(f"/api/requests/{req_id}/resolve", headers=alice["headers"], json={
        "resolution_summary": "All needs fulfilled, happy in Pune!",
    })
    assert res_all.status_code == 200
    intel_all = res_all.json()
    assert intel_all["status"] == "RESOLVED"
    assert intel_all["progress_percentage"] == 100.0
    assert intel_all["resolution_summary"] == "All needs fulfilled, happy in Pune!"
    assert intel_all["resolved_at"] is not None


# ============================================================================
# 7. Compatibility with Existing Results Page
# ============================================================================

def test_results_page_compatibility(client: TestClient):
    alice = create_authenticated_user(client, "Alice Comp", f"alice_comp_{uuid.uuid4().hex[:6]}@example.test")

    res_req = client.post("/api/requests", headers=alice["headers"], json={
        "text": "Need relocation guidance in Viman Nagar Pune.",
    })
    req_id = res_req.json()["id"]

    # Verify existing POST /api/matching/find-matches endpoint still returns valid matches
    res_match = client.post(
        "/api/matching/find-matches",
        headers=alice["headers"],
        json={"request_id": req_id, "limit": 10},
    )
    assert res_match.status_code == 200
    match_data = res_match.json()
    assert "matches" in match_data
    assert "target_location" in match_data
