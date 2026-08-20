"""
End-to-end smoke test for the backend API.

Start the backend first (start_backend.bat), then run:

    .venv\\Scripts\\python.exe test_backend.py

Run it twice: once with Member 3's AI service running, and once with it stopped.
Both runs must pass — that is the reliability guarantee being tested.
"""

import os
import sys
import time

import httpx

from api import routing

BASE_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8001")

STAFF_EMAIL = os.getenv("TEST_STAFF_EMAIL", "staff@support.com")
STAFF_PASSWORD = os.getenv("TEST_STAFF_PASSWORD", "staff1234")

COMPLAINT = "My credit card was charged twice for one order."


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def register_and_login(client, label):
    """Create a throwaway customer so repeated runs never collide."""

    email = f"test_{label}_{int(time.time() * 1000)}@example.com"
    password = "testpass123"

    response = client.post(
        "/auth/register",
        json={"email": email, "password": password, "name": f"Test {label}"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["role"] == "customer"

    # An email may only be registered once.
    duplicate = client.post(
        "/auth/register",
        json={"email": email, "password": password, "name": "Impostor"},
    )
    assert duplicate.status_code == 400, duplicate.text

    response = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text

    return email, response.json()["access_token"]


def main():
    client = httpx.Client(base_url=BASE_URL, timeout=20.0)

    # --- health -------------------------------------------------------
    health = client.get("/health")
    assert health.status_code == 200, health.text
    health = health.json()
    assert health["database"] == "connected", health

    ai_up = health["ai_service"] == "reachable"
    print(f"AI service: {health['ai_service']}")
    print()

    # --- registration and login ---------------------------------------
    email, token = register_and_login(client, "a")

    me = client.get("/auth/me", headers=auth(token))
    assert me.status_code == 200, me.text
    assert me.json()["email"] == email
    print("PASS  register, duplicate rejected, login, /auth/me")

    # --- authentication is enforced -----------------------------------
    assert client.get("/tickets").status_code == 401
    assert client.post("/tickets", json={"complaint": COMPLAINT}).status_code == 401
    assert client.get("/tickets", headers=auth("not-a-real-token")).status_code == 401
    print("PASS  missing and invalid tokens rejected with 401")

    # --- validation ---------------------------------------------------
    assert client.post(
        "/tickets", json={"complaint": "hi"}, headers=auth(token)
    ).status_code == 422
    # Whitespace-only input passes a raw length check but is still empty.
    assert client.post(
        "/tickets", json={"complaint": "      "}, headers=auth(token)
    ).status_code == 422
    print("PASS  short and whitespace-only complaints rejected with 422")

    # --- submit, classify, route --------------------------------------
    response = client.post(
        "/tickets", json={"complaint": COMPLAINT}, headers=auth(token)
    )
    assert response.status_code == 201, response.text
    ticket = response.json()
    ticket_id = ticket["id"]

    # True in both branches: the complaint is stored, routed, and has a deadline.
    assert ticket["complaint"] == COMPLAINT
    assert ticket["sla_due_at"] is not None
    assert ticket["department"], ticket
    assert ticket["priority"] in ("high", "medium", "low"), ticket

    if ai_up:
        assert ticket["status"] == "open", ticket
        assert ticket["category"] in routing.CATEGORY_TO_DEPARTMENT, ticket
        assert ticket["department"] == routing.department_for(ticket["category"])
        assert ticket["classified_at"] is not None
        assert 0.0 <= ticket["category_confidence"] <= 1.0
        print(
            f"PASS  ticket classified as {ticket['category']} / "
            f"{ticket['priority']} and routed to {ticket['department']}"
        )
    else:
        assert ticket["status"] == "pending_classification", ticket
        assert ticket["category"] is None, ticket
        assert ticket["department"] == routing.DEFAULT_DEPARTMENT, ticket
        assert ticket["priority"] == routing.DEFAULT_PRIORITY, ticket
        print("PASS  AI service down, ticket stored as pending_classification")

    # --- the owner can read it back -----------------------------------
    listed = client.get("/tickets", headers=auth(token)).json()
    assert [t["id"] for t in listed] == [ticket_id], listed
    assert client.get(f"/tickets/{ticket_id}", headers=auth(token)).status_code == 200
    print("PASS  customer sees their own ticket")

    # --- another customer cannot ---------------------------------------
    _, other_token = register_and_login(client, "b")
    assert (
        client.get(f"/tickets/{ticket_id}", headers=auth(other_token)).status_code
        == 404
    )
    assert client.get("/tickets", headers=auth(other_token)).json() == []
    print("PASS  another customer cannot read or list that ticket")

    # Keep this test self-contained on a clean deployment instead of relying
    # on the optional local seed dataset for the staff multi-customer check.
    other_ticket = client.post(
        "/tickets",
        json={"complaint": "My delivery has not arrived yet."},
        headers=auth(other_token),
    )
    assert other_ticket.status_code == 201, other_ticket.text

    # --- customers cannot use staff endpoints --------------------------
    assert (
        client.patch(
            f"/tickets/{ticket_id}",
            json={"status": "closed"},
            headers=auth(token),
        ).status_code
        == 403
    )
    assert client.get("/stats", headers=auth(token)).status_code == 403
    assert (
        client.post(
            f"/tickets/{ticket_id}/reclassify", headers=auth(token)
        ).status_code
        == 403
    )
    print("PASS  staff-only endpoints refuse customers with 403")

    # --- staff --------------------------------------------------------
    staff_login = client.post(
        "/auth/login", json={"email": STAFF_EMAIL, "password": STAFF_PASSWORD}
    )

    if staff_login.status_code != 200:
        print()
        print("SKIPPED staff checks: no seeded staff account.")
        print("Run 'python seed.py' and try again.")
        print()
        print("All customer-side checks passed.")
        return

    staff_token = staff_login.json()["access_token"]
    assert staff_login.json()["role"] == "staff"

    all_tickets = client.get("/tickets", headers=auth(staff_token)).json()
    assert len(all_tickets) > 1, "staff should see more than one customer's tickets"
    assert ticket_id in [t["id"] for t in all_tickets]
    print("PASS  staff sees all tickets")

    high = client.get(
        "/tickets", params={"priority": "high"}, headers=auth(staff_token)
    ).json()
    assert all(t["priority"] == "high" for t in high), high
    overdue = client.get(
        "/tickets", params={"overdue": "true"}, headers=auth(staff_token)
    ).json()
    assert all(
        t["status"] in ("pending_classification", "open", "in_progress")
        for t in overdue
    ), "a resolved or closed ticket must never count as overdue"
    print(f"PASS  staff filters work ({len(high)} high, {len(overdue)} overdue)")

    updated = client.patch(
        f"/tickets/{ticket_id}",
        json={"status": "in_progress"},
        headers=auth(staff_token),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["status"] == "in_progress"
    customer_view = client.get(
        f"/tickets/{ticket_id}", headers=auth(token)
    )
    assert customer_view.status_code == 200, customer_view.text
    assert customer_view.json()["status"] == "in_progress"
    assert (
        client.patch(
            f"/tickets/{ticket_id}",
            json={"status": "not_a_status"},
            headers=auth(staff_token),
        ).status_code
        == 422
    )
    print("PASS  staff can change status, invalid status rejected")

    # --- reclassify ----------------------------------------------------
    reclassified = client.post(
        f"/tickets/{ticket_id}/reclassify", headers=auth(staff_token)
    )

    if ai_up:
        assert reclassified.status_code == 200, reclassified.text
        body = reclassified.json()
        assert body["category"] in routing.CATEGORY_TO_DEPARTMENT, body
        # A ticket already being worked on keeps its place in the workflow.
        assert body["status"] == "in_progress", body
        print("PASS  reclassify succeeds without resetting workflow status")
    else:
        assert reclassified.status_code == 503, reclassified.text
        unchanged = client.get(
            f"/tickets/{ticket_id}", headers=auth(staff_token)
        ).json()
        assert unchanged["category"] is None, unchanged
        assert unchanged["status"] == "in_progress", unchanged
        print("PASS  reclassify returns 503 and leaves the ticket untouched")

    # --- stats ---------------------------------------------------------
    stats = client.get("/stats", headers=auth(staff_token))
    assert stats.status_code == 200, stats.text
    stats = stats.json()
    for key in (
        "total_tickets",
        "by_status",
        "by_category",
        "by_priority",
        "by_department",
        "overdue",
        "pending_classification",
    ):
        assert key in stats, f"missing key: {key}"
    assert stats["total_tickets"] == sum(stats["by_status"].values())
    print(f"PASS  stats consistent ({stats['total_tickets']} tickets total)")

    print()
    print("All checks passed.")


if __name__ == "__main__":
    try:
        main()
    except httpx.ConnectError:
        print(f"Could not reach the backend at {BASE_URL}.")
        print("Start it with start_backend.bat and try again.")
        sys.exit(1)
