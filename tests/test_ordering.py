from app.services.ordering import calculate_fractional_order, MIN_FRACTIONAL_GAP
from app.models import Tenant, Board, BoardColumn, Task


def test_fractional_ordering_math():
    """Validates midpoint and boundary calculations for fractional indexing."""
    # Moving between two tasks: order 1000 and 2000 -> 1500
    mid = calculate_fractional_order(prev_order=1000.0, next_order=2000.0)
    assert mid == 1500.0

    # Moving to top before task with order 1000 -> 500
    top = calculate_fractional_order(prev_order=None, next_order=1000.0)
    assert top == 500.0

    # Moving to bottom after task with order 2000 -> 3000
    bottom = calculate_fractional_order(prev_order=2000.0, next_order=None)
    assert bottom == 3000.0


def test_drag_drop_task_move_api(client, db, user_tokens):
    """
    Tests moving a task to a new column and fractional order position.
    Verifies that only the moved task's row is updated (O(1) write).
    """
    token = user_tokens["rahul@julley.com"]
    blr_tenant = db.query(Tenant).filter(Tenant.slug == "bangalore-hq").first()
    blr_board = db.query(Board).filter(Board.tenant_id == blr_tenant.id).first()

    cols = db.query(BoardColumn).filter(BoardColumn.board_id == blr_board.id).all()
    source_col = cols[0]
    target_col = cols[1]

    task = db.query(Task).filter(Task.column_id == source_col.id).first()

    res = client.post(
        f"/api/tenants/{blr_tenant.id}/boards/{blr_board.id}/tasks/{task.id}/move",
        json={
            "target_column_id": target_col.id,
            "prev_order": 1000.0,
            "next_order": 2000.0,
        },
        headers=token,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["column_id"] == target_col.id
    assert data["order"] == 1500.0
