from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Tenant, Board, BoardColumn, User
from app.schemas import (
    ColumnCreate,
    ColumnUpdate,
    ColumnMoveRequest,
    ColumnResponse,
)
from app.security import ROLE_TENANT_ADMIN, ROLE_MEMBER
from app.api.deps import get_current_user, require_tenant_access
from app.services.ordering import (
    calculate_fractional_order,
    check_and_rebalance_board_columns,
)
from app.services.activity import log_activity
from app.websocket.manager import ws_manager
from app.websocket.events import (
    EVENT_COLUMN_CREATED,
    EVENT_COLUMN_UPDATED,
    EVENT_COLUMN_MOVED,
    EVENT_COLUMN_DELETED,
    build_event,
)

router = APIRouter(prefix="/tenants/{tenant_id}/boards/{board_id}/columns", tags=["Columns"])


@router.post("", response_model=ColumnResponse)
async def create_column(
    board_id: str,
    col_in: ColumnCreate,
    tenant: Tenant = Depends(require_tenant_access(ROLE_TENANT_ADMIN)),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Creates a new column on the board with automatic fractional ordering."""
    board = db.query(Board).filter(Board.id == board_id, Board.tenant_id == tenant.id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found in this tenant")

    if col_in.order is not None:
        new_order = col_in.order
    else:
        last_col = (
            db.query(BoardColumn)
            .filter(BoardColumn.board_id == board_id, BoardColumn.tenant_id == tenant.id)
            .order_by(BoardColumn.order.desc())
            .first()
        )
        new_order = calculate_fractional_order(prev_order=last_col.order if last_col else None)

    column = BoardColumn(
        tenant_id=tenant.id,
        board_id=board.id,
        title=col_in.title,
        order=new_order,
        wip_limit=col_in.wip_limit or 0,
    )
    db.add(column)
    db.commit()
    db.refresh(column)

    log_activity(
        db=db,
        tenant_id=tenant.id,
        org_id=tenant.org_id,
        board_id=board.id,
        user_id=current_user.id,
        action="COLUMN_CREATED",
        entity_type="column",
        entity_id=column.id,
        details={"title": column.title, "order": column.order},
    )

    await ws_manager.broadcast_to_room(
        tenant_id=tenant.id,
        board_id=board.id,
        event=build_event(EVENT_COLUMN_CREATED, {
            "id": column.id,
            "board_id": column.board_id,
            "tenant_id": column.tenant_id,
            "title": column.title,
            "order": column.order,
            "wip_limit": column.wip_limit,
            "created_at": column.created_at.isoformat(),
            "updated_at": column.updated_at.isoformat(),
            "tasks": [],
        }, user={"id": current_user.id, "name": current_user.name}),
    )

    return column


@router.put("/{column_id}", response_model=ColumnResponse)
async def update_column(
    board_id: str,
    column_id: str,
    col_in: ColumnUpdate,
    tenant: Tenant = Depends(require_tenant_access(ROLE_TENANT_ADMIN)),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates column title or WIP limit."""
    column = (
        db.query(BoardColumn)
        .filter(BoardColumn.id == column_id, BoardColumn.board_id == board_id, BoardColumn.tenant_id == tenant.id)
        .first()
    )
    if not column:
        raise HTTPException(status_code=404, detail="Column not found in this tenant")

    if col_in.title is not None:
        column.title = col_in.title
    if col_in.wip_limit is not None:
        column.wip_limit = col_in.wip_limit
    if col_in.order is not None:
        column.order = col_in.order

    db.commit()
    db.refresh(column)

    log_activity(
        db=db,
        tenant_id=tenant.id,
        org_id=tenant.org_id,
        board_id=board_id,
        user_id=current_user.id,
        action="COLUMN_UPDATED",
        entity_type="column",
        entity_id=column.id,
        details={"title": column.title, "wip_limit": column.wip_limit},
    )

    await ws_manager.broadcast_to_room(
        tenant_id=tenant.id,
        board_id=board_id,
        event=build_event(EVENT_COLUMN_UPDATED, {
            "id": column.id,
            "title": column.title,
            "wip_limit": column.wip_limit,
            "order": column.order,
        }, user={"id": current_user.id, "name": current_user.name}),
    )

    return column


@router.post("/{column_id}/move", response_model=ColumnResponse)
async def move_column(
    board_id: str,
    column_id: str,
    move_req: ColumnMoveRequest,
    tenant: Tenant = Depends(require_tenant_access(ROLE_TENANT_ADMIN)),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reorders column using fractional indexing."""
    column = (
        db.query(BoardColumn)
        .filter(BoardColumn.id == column_id, BoardColumn.board_id == board_id, BoardColumn.tenant_id == tenant.id)
        .first()
    )
    if not column:
        raise HTTPException(status_code=404, detail="Column not found in this tenant")

    new_order = calculate_fractional_order(
        prev_order=move_req.prev_order,
        next_order=move_req.next_order,
    )
    column.order = new_order
    db.commit()
    db.refresh(column)

    check_and_rebalance_board_columns(db, board_id=board_id, tenant_id=tenant.id)

    log_activity(
        db=db,
        tenant_id=tenant.id,
        org_id=tenant.org_id,
        board_id=board_id,
        user_id=current_user.id,
        action="COLUMN_MOVED",
        entity_type="column",
        entity_id=column.id,
        details={"title": column.title, "new_order": column.order},
    )

    await ws_manager.broadcast_to_room(
        tenant_id=tenant.id,
        board_id=board_id,
        event=build_event(EVENT_COLUMN_MOVED, {
            "id": column.id,
            "order": column.order,
        }, user={"id": current_user.id, "name": current_user.name}),
    )

    return column


@router.delete("/{column_id}")
async def delete_column(
    board_id: str,
    column_id: str,
    tenant: Tenant = Depends(require_tenant_access(ROLE_TENANT_ADMIN)),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes column and cascades to its tasks. Tenant Admin required."""
    column = (
        db.query(BoardColumn)
        .filter(BoardColumn.id == column_id, BoardColumn.board_id == board_id, BoardColumn.tenant_id == tenant.id)
        .first()
    )
    if not column:
        raise HTTPException(status_code=404, detail="Column not found in this tenant")

    col_title = column.title
    db.delete(column)
    db.commit()

    log_activity(
        db=db,
        tenant_id=tenant.id,
        org_id=tenant.org_id,
        board_id=board_id,
        user_id=current_user.id,
        action="COLUMN_DELETED",
        entity_type="column",
        entity_id=column_id,
        details={"title": col_title},
    )

    await ws_manager.broadcast_to_room(
        tenant_id=tenant.id,
        board_id=board_id,
        event=build_event(EVENT_COLUMN_DELETED, {
            "id": column_id,
        }, user={"id": current_user.id, "name": current_user.name}),
    )

    return {"message": "Column deleted successfully"}
