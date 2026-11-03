from app.models import Tenant, Board, BoardColumn, Task


def test_optimistic_concurrency_control_success(client, db, user_tokens):
    """Verifies that an update with matching expected_version increments version and updates fields."""
    token = user_tokens["rahul@julley.com"]
    blr_tenant = db.query(Tenant).filter(Tenant.slug == "bangalore-hq").first()
    blr_board = db.query(Board).filter(Board.tenant_id == blr_tenant.id).first()
    task = db.query(Task).filter(Task.board_id == blr_board.id).first()

    initial_version = task.version
    new_title = "Updated Title with Matching Version"

    res = client.put(
        f"/api/tenants/{blr_tenant.id}/boards/{blr_board.id}/tasks/{task.id}",
        json={"expected_version": initial_version, "title": new_title},
        headers=token,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == new_title
    assert data["version"] == initial_version + 1


def test_optimistic_concurrency_control_conflict(client, db, user_tokens):
    """
    Simulates concurrent edits:
    User A updates the task successfully.
    User B (having a stale expected_version) attempts an update -> returns 409 Conflict.
    """
    user_a_token = user_tokens["priya@julley.com"]
    user_b_token = user_tokens["rahul@julley.com"]

    blr_tenant = db.query(Tenant).filter(Tenant.slug == "bangalore-hq").first()
    blr_board = db.query(Board).filter(Board.tenant_id == blr_tenant.id).first()
    task = db.query(Task).filter(Task.board_id == blr_board.id).first()

    base_version = task.version

    # User A updates the task -> version becomes base_version + 1
    res_a = client.put(
        f"/api/tenants/{blr_tenant.id}/boards/{blr_board.id}/tasks/{task.id}",
        json={"expected_version": base_version, "title": "User A change"},
        headers=user_a_token,
    )
    assert res_a.status_code == 200
    assert res_a.json()["version"] == base_version + 1

    # User B tries to update using old base_version
    res_b = client.put(
        f"/api/tenants/{blr_tenant.id}/boards/{blr_board.id}/tasks/{task.id}",
        json={"expected_version": base_version, "title": "User B colliding change"},
        headers=user_b_token,
    )

    # Must return 409 Conflict
    assert res_b.status_code == 409
    detail = res_b.json()["detail"]
    assert "Conflict detected" in detail["message"]
    assert detail["client_version"] == base_version
    assert detail["server_version"] == base_version + 1
    assert detail["server_task"]["title"] == "User A change"
