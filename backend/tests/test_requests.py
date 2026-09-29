import uuid
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from app.services.request_parser import parse_request
from tests.conftest import create_authenticated_user


# ==========================================
# 1. Basic Extraction Tests (NLP Service)
# ==========================================

def test_city_extraction():
    """1. City extraction and normalization."""
    res = parse_request("I am moving to Pune next month.")
    assert res.location.city == "Pune"
    assert res.location.state == "Maharashtra"
    assert res.location.city_source == "explicit_text"


def test_area_extraction():
    """2. Area extraction and city inference."""
    res = parse_request("Looking for a place in Whitefield.")
    assert res.location.area == "Whitefield"
    assert res.location.city == "Bengaluru"
    assert res.location.city_source == "inferred_from_area"


def test_needs_extraction():
    """3. Specific need category extraction."""
    res = parse_request("Need a PG near Wakad.")
    categories = [n.category for n in res.needs]
    assert "accommodation" in categories
    pg_need = next(n for n in res.needs if n.category == "accommodation")
    assert "PG" in pg_need.item


def test_budget_extraction():
    """4. Budget extraction."""
    res = parse_request("My budget is under ₹10,000.")
    assert res.budget is not None
    assert res.budget.amount == 10000.0
    assert res.budget.currency == "INR"
    assert res.budget.operator == "<="


def test_preference_extraction():
    """5. Preference extraction."""
    res = parse_request("I want affordable vegetarian food near metro.")
    assert "vegetarian" in res.preferences
    assert "affordable" in res.preferences
    assert "near metro" in res.preferences


def test_multiple_needs():
    """6. Multiple needs extraction across categories."""
    res = parse_request("Need a flat, vegetarian tiffin service, and a doctor nearby.")
    categories = [n.category for n in res.needs]
    assert "accommodation" in categories
    assert "food" in categories
    assert "healthcare" in categories


def test_raw_text_preservation():
    """7. Raw user text preservation."""
    raw = "Moving to Baner, Pune for first job. Need PG under 9k and veg food."
    res = parse_request(raw)
    assert res.raw_text == raw


# ==========================================
# 2. Normalization Tests
# ==========================================

def test_normalization_inr_symbol():
    """8. Currency symbol ₹10,000 normalized to 10000.0."""
    res = parse_request("Budget ₹10,000 for rent.")
    assert res.budget.amount == 10000.0


def test_normalization_rs():
    """9. Currency format Rs 10000 normalized to 10000.0."""
    res = parse_request("Rent should be Rs 10000 max.")
    assert res.budget.amount == 10000.0


def test_normalization_k_suffix():
    """10. K multiplier '10k' normalized to 10000.0."""
    res = parse_request("Looking for a room under 10k.")
    assert res.budget.amount == 10000.0


def test_normalization_bangalore_to_bengaluru():
    """11. Alias 'Bangalore' maps to canonical 'Bengaluru'."""
    res = parse_request("Moving to Bangalore near Koramangala.")
    assert res.location.city == "Bengaluru"
    assert res.location.state == "Karnataka"


def test_normalization_pg_to_accommodation():
    """12. 'PG' maps to accommodation category."""
    res = parse_request("Need a PG in Hinjewadi.")
    assert any(n.category == "accommodation" for n in res.needs)


def test_normalization_vegetarian_food():
    """13. 'veg food' maps to vegetarian preference."""
    res = parse_request("Need daily veg food near my office.")
    assert "vegetarian" in res.preferences


# ==========================================
# 3. Budget Variations & Periods
# ==========================================

def test_budget_under_operator():
    """14. 'under ₹10,000' produces operator '<='."""
    res = parse_request("Need PG under ₹10,000.")
    assert res.budget.amount == 10000.0
    assert res.budget.operator == "<="


def test_budget_monthly_period():
    """15. 'below ₹12,000/month' produces amount 12000.0 and period 'monthly'."""
    res = parse_request("Looking for flat below ₹12,000/month in Viman Nagar.")
    assert res.budget.amount == 12000.0
    assert res.budget.period == "monthly"
    assert res.budget.operator == "<="


def test_budget_weekly_period():
    """16. Weekly budget detection."""
    res = parse_request("Stay budget 3k per week.")
    assert res.budget.amount == 3000.0
    assert res.budget.period == "weekly"


def test_budget_yearly_period():
    """17. Yearly budget detection."""
    res = parse_request("College tuition budget 150000 per year.")
    assert res.budget.amount == 150000.0
    assert res.budget.period == "yearly"


def test_budget_unspecified_period():
    """18. When no period is mentioned, period remains None."""
    res = parse_request("I have ₹8,000 budget for PG.")
    assert res.budget.amount == 8000.0
    assert res.budget.period is None


# ==========================================
# 4. Request API & Persistence Tests
# ==========================================

def test_create_request(client: TestClient):
    """19. Create and persist request via POST /api/requests."""
    auth = create_authenticated_user(client, "Ravi Patel", "ravi.p@example.test")
    raw_query = "I am moving to Whitefield for my first IT job. Need PG under ₹10,000 and vegetarian food."

    response = client.post("/api/requests", json={"text": raw_query}, headers=auth["headers"])
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    assert data["raw_text"] == raw_query
    assert data["city"] == "Bengaluru"
    assert data["area"] == "Whitefield"
    assert data["budget_amount"] == 10000.0
    assert data["budget_currency"] == "INR"
    assert data["status"] == "OPEN"
    assert "vegetarian" in data["preferences"]
    assert "id" in data
    assert "user_id" in data


def test_retrieve_request(client: TestClient):
    """20. Retrieve specific request via GET /api/requests/{id}."""
    auth = create_authenticated_user(client, "Snehal K", "snehal.k@example.test")
    create_resp = client.post(
        "/api/requests",
        json={"text": "Need paying guest in Hinjewadi below 8k/month."},
        headers=auth["headers"],
    )
    req_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/requests/{req_id}", headers=auth["headers"])
    assert get_resp.status_code == status.HTTP_200_OK
    assert get_resp.json()["id"] == req_id
    assert get_resp.json()["area"] == "Hinjewadi"
    assert get_resp.json()["budget_amount"] == 8000.0


def test_update_request(client: TestClient):
    """21. Update request text and status via PATCH /api/requests/{id}."""
    auth = create_authenticated_user(client, "Amit Shah", "amit.s@example.test")
    create_resp = client.post(
        "/api/requests",
        json={"text": "Need PG in Baner under 7k."},
        headers=auth["headers"],
    )
    req_id = create_resp.json()["id"]

    # Update with new text (triggers re-parse) and status
    patch_resp = client.patch(
        f"/api/requests/{req_id}",
        json={
            "text": "Moving to Wakad, Pune. Need 1BHK under 15k.",
            "status": "MATCHED",
        },
        headers=auth["headers"],
    )
    assert patch_resp.status_code == status.HTTP_200_OK
    data = patch_resp.json()
    assert data["city"] == "Pune"
    assert data["area"] == "Wakad"
    assert data["budget_amount"] == 15000.0
    assert data["status"] == "MATCHED"


def test_delete_request(client: TestClient):
    """22. Delete request via DELETE /api/requests/{id}."""
    auth = create_authenticated_user(client, "Deepak Rao", "deepak.r@example.test")
    create_resp = client.post(
        "/api/requests",
        json={"text": "Temporary request in Kothrud."},
        headers=auth["headers"],
    )
    req_id = create_resp.json()["id"]

    del_resp = client.delete(f"/api/requests/{req_id}", headers=auth["headers"])
    assert del_resp.status_code == status.HTTP_200_OK
    assert "deleted successfully" in del_resp.json()["detail"]

    # Verify 404 on subsequent get
    assert client.get(f"/api/requests/{req_id}", headers=auth["headers"]).status_code == status.HTTP_404_NOT_FOUND


def test_list_own_requests(client: TestClient):
    """23. List own requests via GET /api/requests."""
    auth = create_authenticated_user(client, "Kavita S", "kavita.s@example.test")
    client.post("/api/requests", json={"text": "First request in Whitefield."}, headers=auth["headers"])
    client.post("/api/requests", json={"text": "Second request in Marathahalli."}, headers=auth["headers"])

    list_resp = client.get("/api/requests", headers=auth["headers"])
    assert list_resp.status_code == status.HTTP_200_OK
    requests = list_resp.json()
    assert len(requests) == 2


# ==========================================
# 5. Security & Isolation Tests
# ==========================================

def test_unauthenticated_request_rejected(client: TestClient):
    """24. Unauthenticated request access is rejected with 401."""
    assert client.get("/api/requests").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.post("/api/requests", json={"text": "test"}).status_code == status.HTTP_401_UNAUTHORIZED
    fake_id = uuid.uuid4()
    assert client.get(f"/api/requests/{fake_id}").status_code == status.HTTP_401_UNAUTHORIZED


def test_user_cannot_access_other_user_request(client: TestClient):
    """25. User A cannot GET User B's request."""
    user_a = create_authenticated_user(client, "User A", "user.a.req@example.test")
    user_b = create_authenticated_user(client, "User B", "user.b.req@example.test")

    create_resp = client.post(
        "/api/requests",
        json={"text": "User A private request in Hinjewadi."},
        headers=user_a["headers"],
    )
    req_id = create_resp.json()["id"]

    # User B attempts to access User A's request
    get_resp = client.get(f"/api/requests/{req_id}", headers=user_b["headers"])
    assert get_resp.status_code == status.HTTP_403_FORBIDDEN


def test_user_cannot_modify_other_user_request(client: TestClient):
    """26. User A cannot PATCH User B's request."""
    user_a = create_authenticated_user(client, "User A Mod", "user.a.mod@example.test")
    user_b = create_authenticated_user(client, "User B Mod", "user.b.mod@example.test")

    create_resp = client.post("/api/requests", json={"text": "Original text"}, headers=user_a["headers"])
    req_id = create_resp.json()["id"]

    patch_resp = client.patch(
        f"/api/requests/{req_id}",
        json={"text": "Malicious modification"},
        headers=user_b["headers"],
    )
    assert patch_resp.status_code == status.HTTP_403_FORBIDDEN


def test_user_cannot_delete_other_user_request(client: TestClient):
    """27. User A cannot DELETE User B's request."""
    user_a = create_authenticated_user(client, "User A Del", "user.a.del@example.test")
    user_b = create_authenticated_user(client, "User B Del", "user.b.del@example.test")

    create_resp = client.post("/api/requests", json={"text": "Text to delete"}, headers=user_a["headers"])
    req_id = create_resp.json()["id"]

    del_resp = client.delete(f"/api/requests/{req_id}", headers=user_b["headers"])
    assert del_resp.status_code == status.HTTP_403_FORBIDDEN


# ==========================================
# 6. Edge Cases
# ==========================================

def test_empty_request_rejected(client: TestClient):
    """28. Empty text request is rejected with 422."""
    auth = create_authenticated_user(client, "Empty Req", "empty.req@example.test")
    resp = client.post("/api/requests", json={"text": ""}, headers=auth["headers"])
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_long_request_handled_safely():
    """29. Extremely long request is parsed safely without errors."""
    long_text = "I am moving to Whitefield Bengaluru. " + ("Need affordable vegetarian food and PG. " * 30)
    res = parse_request(long_text)
    assert res.location.city == "Bengaluru"
    assert res.location.area == "Whitefield"
    assert "vegetarian" in res.preferences


def test_no_recognizable_location():
    """30. Request with no recognizable location leaves location as None without hallucinating."""
    res = parse_request("I need a reliable friend to discuss my career options.")
    assert res.location.city is None
    assert res.location.area is None


def test_no_budget():
    """31. Request with no budget leaves budget as None without hallucinating."""
    res = parse_request("Need help finding a good doctor in Baner Pune.")
    assert res.budget is None
    assert res.location.city == "Pune"
    assert res.location.area == "Baner"


def test_multiple_locations_and_needs():
    """32. Request with multiple needs and contextual location cues."""
    text = "Relocating to Bengaluru near HSR Layout or Koramangala. Looking for a 1BHK or PG, veg mess, and advice on metro routes."
    res = parse_request(text)
    assert res.location.city == "Bengaluru"
    assert res.location.area in ["HSR Layout", "Koramangala"]
    categories = [n.category for n in res.needs]
    assert "accommodation" in categories
    assert "food" in categories
    assert "transport" in categories
