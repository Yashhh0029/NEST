import uuid
from fastapi import status
from fastapi.testclient import TestClient
from tests.conftest import create_authenticated_user


# ==========================================
# 1. Profile Tests
# ==========================================

def test_create_profile(client: TestClient):
    """1. Create profile via PUT /api/profile/me when none exists."""
    auth = create_authenticated_user(client, "Rohan Deshmukh", "rohan.d@example.test", "helper")

    profile_payload = {
        "headline": "Senior Software Engineer & Hinjewadi Resident",
        "bio": "Living in Hinjewadi Phase 1 for 4 years. Happy to help newcomers.",
        "occupation": "Software Engineer",
        "organization": "Infosys",
        "years_experience": 4.0,
        "languages": ["English", "Hindi", "Marathi"],
        "help_description": "Can help newcomers find verified PGs in Hinjewadi and Wakad, and guide on Pune bus routes.",
        "needs_description": None,
        "availability": True,
    }

    response = client.put("/api/profile/me", json=profile_payload, headers=auth["headers"])
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["headline"] == profile_payload["headline"]
    assert data["bio"] == profile_payload["bio"]
    assert data["occupation"] == "Software Engineer"
    assert data["years_experience"] == 4.0
    assert data["languages"] == ["English", "Hindi", "Marathi"]
    assert "Hinjewadi" in data["help_description"]
    assert data["availability"] is True
    assert "user_id" in data


def test_retrieve_profile(client: TestClient):
    """2. Retrieve full profile via GET /api/profile/me."""
    auth = create_authenticated_user(client, "Ananya Rao", "ananya.r@example.test", "newcomer")

    # Initial state with no profile configured yet
    resp_empty = client.get("/api/profile/me", headers=auth["headers"])
    assert resp_empty.status_code == status.HTTP_200_OK
    data_empty = resp_empty.json()
    assert data_empty["user"]["email"] == "ananya.r@example.test"
    assert data_empty["profile"] is None
    assert data_empty["location"] is None
    assert data_empty["skills"] == []

    # Configure profile
    client.put("/api/profile/me", json={
        "headline": "Moving to Bengaluru for first job",
        "bio": "Recent graduate joining tech firm in Whitefield.",
        "help_description": None,
        "needs_description": "Need PG with vegetarian food near ITPL Whitefield.",
    }, headers=auth["headers"])

    # Retrieve again
    resp_full = client.get("/api/profile/me", headers=auth["headers"])
    assert resp_full.status_code == status.HTTP_200_OK
    data_full = resp_full.json()
    assert data_full["profile"]["headline"] == "Moving to Bengaluru for first job"
    assert "ITPL Whitefield" in data_full["profile"]["needs_description"]


def test_update_profile(client: TestClient):
    """3. Update profile via PUT /api/profile/me."""
    auth = create_authenticated_user(client, "Vikram Patil", "vikram.p@example.test", "both")

    # First put
    client.put("/api/profile/me", json={
        "headline": "Initial Headline",
        "bio": "Initial Bio",
        "availability": True,
    }, headers=auth["headers"])

    # Full update
    update_resp = client.put("/api/profile/me", json={
        "headline": "Updated Headline",
        "bio": "Updated Bio",
        "occupation": "Product Manager",
        "availability": False,
    }, headers=auth["headers"])
    assert update_resp.status_code == status.HTTP_200_OK
    data = update_resp.json()
    assert data["headline"] == "Updated Headline"
    assert data["bio"] == "Updated Bio"
    assert data["occupation"] == "Product Manager"
    assert data["availability"] is False


def test_patch_profile(client: TestClient):
    """4. Patch profile via PATCH /api/profile/me."""
    auth = create_authenticated_user(client, "Sneha Kulkarni", "sneha.k@example.test", "helper")

    client.put("/api/profile/me", json={
        "headline": "Local Guide",
        "bio": "Pune resident for 10 years.",
        "occupation": "Teacher",
        "availability": True,
    }, headers=auth["headers"])

    # Patch only availability and headline
    patch_resp = client.patch("/api/profile/me", json={
        "availability": False,
        "headline": "Local Guide (Temporarily Busy)",
    }, headers=auth["headers"])
    assert patch_resp.status_code == status.HTTP_200_OK
    data = patch_resp.json()
    assert data["headline"] == "Local Guide (Temporarily Busy)"
    assert data["availability"] is False
    # Bio and occupation should be preserved
    assert data["bio"] == "Pune resident for 10 years."
    assert data["occupation"] == "Teacher"


def test_unauthenticated_profile_access(client: TestClient):
    """5. Unauthenticated profile access is rejected with 401."""
    assert client.get("/api/profile/me").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.put("/api/profile/me", json={"headline": "Test"}).status_code == status.HTTP_401_UNAUTHORIZED
    assert client.patch("/api/profile/me", json={"headline": "Test"}).status_code == status.HTTP_401_UNAUTHORIZED


# ==========================================
# 2. Location Tests
# ==========================================

def test_create_update_location(client: TestClient):
    """6. Create and update location via PUT /api/profile/me/location."""
    auth = create_authenticated_user(client, "Tanvi Joshi", "tanvi.j@example.test")

    loc_payload = {
        "city": "Bengaluru",
        "area": "Whitefield",
        "state": "Karnataka",
        "country": "India",
        "latitude": 12.9698,
        "longitude": 77.7499,
        "location_label": "Primary",
    }
    response = client.put("/api/profile/me/location", json=loc_payload, headers=auth["headers"])
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["city"] == "Bengaluru"
    assert data["area"] == "Whitefield"
    assert abs(data["latitude"] - 12.9698) < 1e-4
    assert abs(data["longitude"] - 77.7499) < 1e-4


def test_retrieve_location(client: TestClient):
    """7. Retrieve location via GET /api/profile/me/location."""
    auth = create_authenticated_user(client, "Karthik Iyer", "karthik.i@example.test")

    # Before setting location
    assert client.get("/api/profile/me/location", headers=auth["headers"]).status_code == status.HTTP_404_NOT_FOUND

    # Set location
    client.put("/api/profile/me/location", json={
        "city": "Pune",
        "area": "Kothrud",
        "state": "Maharashtra",
        "latitude": 18.5074,
        "longitude": 73.8077,
    }, headers=auth["headers"])

    # Retrieve location
    response = client.get("/api/profile/me/location", headers=auth["headers"])
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["city"] == "Pune"
    assert response.json()["area"] == "Kothrud"


def test_delete_location(client: TestClient):
    """8. Delete location via DELETE /api/profile/me/location."""
    auth = create_authenticated_user(client, "Meera Menon", "meera.m@example.test")

    client.put("/api/profile/me/location", json={"city": "Pune", "area": "Baner"}, headers=auth["headers"])
    assert client.get("/api/profile/me/location", headers=auth["headers"]).status_code == status.HTTP_200_OK

    del_resp = client.delete("/api/profile/me/location", headers=auth["headers"])
    assert del_resp.status_code == status.HTTP_200_OK
    assert "deleted successfully" in del_resp.json()["detail"]

    # Subsequent GET returns 404
    assert client.get("/api/profile/me/location", headers=auth["headers"]).status_code == status.HTTP_404_NOT_FOUND


def test_invalid_latitude_rejected(client: TestClient):
    """9. Latitude outside [-90, 90] is rejected with 422."""
    auth = create_authenticated_user(client, "Bad Lat", "badlat@example.test")
    resp = client.put("/api/profile/me/location", json={
        "city": "Pune",
        "latitude": 95.5,
        "longitude": 73.85,
    }, headers=auth["headers"])
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_invalid_longitude_rejected(client: TestClient):
    """10. Longitude outside [-180, 180] is rejected with 422."""
    auth = create_authenticated_user(client, "Bad Lon", "badlon@example.test")
    resp = client.put("/api/profile/me/location", json={
        "city": "Bengaluru",
        "latitude": 12.97,
        "longitude": -195.0,
    }, headers=auth["headers"])
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ==========================================
# 3. Skills Tests
# ==========================================

def test_add_skill(client: TestClient):
    """11. Add skill to user profile via POST /api/profile/me/skills."""
    auth = create_authenticated_user(client, "Sameer Khan", "sameer.k@example.test", "helper")

    skill_payload = {
        "name": "PG Housing Advice",
        "proficiency": "expert",
        "years_experience": 3.5,
    }
    response = client.post("/api/profile/me/skills", json=skill_payload, headers=auth["headers"])
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["skill_name"] == "PG Housing Advice"
    assert data["proficiency"] == "expert"
    assert data["years_experience"] == 3.5
    assert "id" in data
    assert "skill_id" in data


def test_retrieve_skills(client: TestClient):
    """12. Retrieve user skills via GET /api/profile/me/skills."""
    auth = create_authenticated_user(client, "Divya Hegde", "divya.h@example.test", "helper")

    client.post("/api/profile/me/skills", json={"name": "Vegetarian Food Guide"}, headers=auth["headers"])
    client.post("/api/profile/me/skills", json={"name": "Bus Metro Navigation"}, headers=auth["headers"])

    response = client.get("/api/profile/me/skills", headers=auth["headers"])
    assert response.status_code == status.HTTP_200_OK
    skills = response.json()
    assert len(skills) == 2
    names = [s["skill_name"] for s in skills]
    assert "Vegetarian Food Guide" in names
    assert "Bus Metro Navigation" in names


def test_delete_skill(client: TestClient):
    """13. Delete skill from user profile via DELETE /api/profile/me/skills/{id}."""
    auth = create_authenticated_user(client, "Arjun Seth", "arjun.s@example.test")

    add_resp = client.post("/api/profile/me/skills", json={"name": "Temporary Skill"}, headers=auth["headers"])
    skill_id = add_resp.json()["skill_id"]

    del_resp = client.delete(f"/api/profile/me/skills/{skill_id}", headers=auth["headers"])
    assert del_resp.status_code == status.HTTP_200_OK

    # Verify skill is unlinked
    skills_resp = client.get("/api/profile/me/skills", headers=auth["headers"])
    assert len(skills_resp.json()) == 0


def test_duplicate_skill_prevented(client: TestClient):
    """14. Duplicate skill for the same user is rejected with 400."""
    auth = create_authenticated_user(client, "Nikhil Gupta", "nikhil.g@example.test")

    resp1 = client.post("/api/profile/me/skills", json={"name": "Local Transport"}, headers=auth["headers"])
    assert resp1.status_code == status.HTTP_201_CREATED

    resp2 = client.post("/api/profile/me/skills", json={"name": "Local Transport"}, headers=auth["headers"])
    assert resp2.status_code == status.HTTP_400_BAD_REQUEST
    assert "already added" in resp2.json()["detail"]


def test_skill_name_normalization(client: TestClient):
    """15. Skill names with varying cases and whitespace normalize to the same master skill."""
    auth1 = create_authenticated_user(client, "User One", "user1@example.test")
    auth2 = create_authenticated_user(client, "User Two", "user2@example.test")

    # User 1 adds " Vegetarian Food "
    resp1 = client.post("/api/profile/me/skills", json={"name": "  Vegetarian   Food  "}, headers=auth1["headers"])
    assert resp1.status_code == status.HTTP_201_CREATED
    skill1_id = resp1.json()["skill_id"]

    # User 2 adds "vegetarian food" in lowercase
    resp2 = client.post("/api/profile/me/skills", json={"name": "vegetarian food"}, headers=auth2["headers"])
    assert resp2.status_code == status.HTTP_201_CREATED
    skill2_id = resp2.json()["skill_id"]

    # Both must reference the exact same master skill_id
    assert skill1_id == skill2_id


# ==========================================
# 4. Security & Isolation Tests
# ==========================================

def test_user_isolation(client: TestClient):
    """16. Authenticated User A cannot view or modify User B's profile data."""
    user_a = create_authenticated_user(client, "User A", "user.a@example.test")
    user_b = create_authenticated_user(client, "User B", "user.b@example.test")

    # User A sets profile
    client.put("/api/profile/me", json={"headline": "User A Headline"}, headers=user_a["headers"])
    client.put("/api/profile/me/location", json={"city": "Pune", "area": "Baner"}, headers=user_a["headers"])

    # User B checks their profile - must not see User A's data
    resp_b = client.get("/api/profile/me", headers=user_b["headers"])
    data_b = resp_b.json()
    assert data_b["user"]["email"] == "user.b@example.test"
    assert data_b["profile"] is None
    assert data_b["location"] is None


def test_password_hash_never_exposed(client: TestClient):
    """17. Password hashes never appear anywhere in profile responses."""
    auth = create_authenticated_user(client, "Security User", "sec.user@example.test")
    client.put("/api/profile/me", json={"headline": "Security Tester"}, headers=auth["headers"])
    client.put("/api/profile/me/location", json={"city": "Pune"}, headers=auth["headers"])
    client.post("/api/profile/me/skills", json={"name": "Security Skill"}, headers=auth["headers"])

    full_resp = client.get("/api/profile/me", headers=auth["headers"]).json()

    def assert_no_passwords(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                assert "password" not in k.lower()
                assert_no_passwords(v)
        elif isinstance(obj, list):
            for item in obj:
                assert_no_passwords(item)

    assert_no_passwords(full_resp)
