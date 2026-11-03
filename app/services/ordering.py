from typing import Optional, List
from sqlalchemy.orm import Session
from app.models import Task, BoardColumn

MIN_FRACTIONAL_GAP = 1e-4
DEFAULT_INITIAL_ORDER = 1000.0
ORDER_INCREMENT = 1000.0


def calculate_fractional_order(
    prev_order: Optional[float] = None,
    next_order: Optional[float] = None,
) -> float:
    """
    Computes a fractional index between prev_order and next_order.
    - If both exist: midpoint (prev_order + next_order) / 2.0
    - If only prev exists: prev_order + ORDER_INCREMENT
    - If only next exists: next_order / 2.0 (or next_order - ORDER_INCREMENT if next > ORDER_INCREMENT)
    - If neither exists: DEFAULT_INITIAL_ORDER
    """
    if prev_order is not None and next_order is not None:
        return (prev_order + next_order) / 2.0
    elif prev_order is not None:
        return prev_order + ORDER_INCREMENT
    elif next_order is not None:
        if next_order > 1.0:
            return next_order / 2.0
        return next_order - 0.5
    else:
        return DEFAULT_INITIAL_ORDER


def check_and_rebalance_column_tasks(db: Session, column_id: str, tenant_id: str) -> None:
    """
    Checks if task orders in a column have gotten too close (< MIN_FRACTIONAL_GAP).
    If so, rebalances them uniformly to 1000, 2000, 3000...
    Scoped strictly by tenant_id!
    """
    tasks: List[Task] = (
        db.query(Task)
        .filter(Task.column_id == column_id, Task.tenant_id == tenant_id)
        .order_by(Task.order.asc())
        .all()
    )

    needs_rebalance = False
    for i in range(len(tasks) - 1):
        if (tasks[i + 1].order - tasks[i].order) < MIN_FRACTIONAL_GAP:
            needs_rebalance = True
            break

    if needs_rebalance:
        current_order = ORDER_INCREMENT
        for t in tasks:
            t.order = current_order
            current_order += ORDER_INCREMENT
        db.commit()


def check_and_rebalance_board_columns(db: Session, board_id: str, tenant_id: str) -> None:
    """Rebalances columns of a board if order gaps become too small."""
    columns: List[BoardColumn] = (
        db.query(BoardColumn)
        .filter(BoardColumn.board_id == board_id, BoardColumn.tenant_id == tenant_id)
        .order_by(BoardColumn.order.asc())
        .all()
    )

    needs_rebalance = False
    for i in range(len(columns) - 1):
        if (columns[i + 1].order - columns[i].order) < MIN_FRACTIONAL_GAP:
            needs_rebalance = True
            break

    if needs_rebalance:
        current_order = ORDER_INCREMENT
        for col in columns:
            col.order = current_order
            current_order += ORDER_INCREMENT
        db.commit()
