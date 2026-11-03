import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import Tenant, Board, BoardColumn, Task, User
from app.schemas import BoardDetailResponse, BoardUpdate, BoardResponse, TaskResponse, ColumnWithTasks
from app.security import ROLE_TENANT_ADMIN, ROLE_MEMBER
from app.api.deps import get_current_user, require_tenant_access
from app.services.activity import log_activity
from app.websocket.manager import ws_manager
from app.websocket.events import EVENT_BOARD_UPDATED, build_event

router = APIRouter(prefix="/tenants/{tenant_id}/boards", tags=["Boards"])


@router.get("/{board_id}", response_model=BoardDetailResponse)
def get_board_detail(
    board_id: str,
    tenant: Tenant = Depends(require_tenant_access(ROLE_MEMBER)),
    db: Session = Depends(get_db),
):
    """
    Fetches complete board state including all columns and tasks ordered by fractional index.
    Strictly isolated: boards belonging to other tenants return 404.
    """
    board = (
        db.query(Board)
        .filter(Board.id == board_id, Board.tenant_id == tenant.id)
        .first()
    )
    if not board:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Board '{board_id}' not found in this tenant",
        )

    # Load columns ordered
    columns = (
        db.query(BoardColumn)
        .filter(BoardColumn.board_id == board.id, BoardColumn.tenant_id == tenant.id)
        .order_by(BoardColumn.order.asc())
        .all()
    )

    # Load tasks with assignees
    tasks = (
        db.query(Task)
        .options(joinedload(Task.assignee))
        .filter(Task.board_id == board.id, Task.tenant_id == tenant.id)
        .order_by(Task.order.asc())
        .all()
    )

    # Group tasks by column
    tasks_by_column = {col.id: [] for col in columns}
    for t in tasks:
        task_data = TaskResponse(
            id=t.id,
            tenant_id=t.tenant_id,
            board_id=t.board_id,
            column_id=t.column_id,
            title=t.title,
            description=t.description,
            priority=t.priority,
            order=t.order,
            version=t.version,
            assignee_id=t.assignee_id,
            due_date=t.due_date,
            tags=json.loads(t.tags) if t.tags else [],
            created_by_id=t.created_by_id,
            created_at=t.created_at,
            updated_at=t.updated_at,
            assignee=t.assignee,
        )
        if t.column_id in tasks_by_column:
            tasks_by_column[t.column_id].append(task_data)

    column_responses = []
    for col in columns:
        col_res = ColumnWithTasks(
            id=col.id,
            board_id=col.board_id,
            tenant_id=col.tenant_id,
            title=col.title,
            order=col.order,
            wip_limit=col.wip_limit,
            created_at=col.created_at,
            updated_at=col.updated_at,
            tasks=tasks_by_column.get(col.id, []),
        )
        column_responses.append(col_res)

    return BoardDetailResponse(
        id=board.id,
        org_id=board.org_id,
        tenant_id=board.tenant_id,
        name=board.name,
        description=board.description,
        color=board.color,
        created_by_id=board.created_by_id,
        created_at=board.created_at,
        updated_at=board.updated_at,
        columns=column_responses,
    )


@router.put("/{board_id}", response_model=BoardResponse)
async def update_board(
    board_id: str,
    board_in: BoardUpdate,
    tenant: Tenant = Depends(require_tenant_access(ROLE_TENANT_ADMIN)),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates board title, color, or description. Broadcasts real-time update."""
    board = (
        db.query(Board)
        .filter(Board.id == board_id, Board.tenant_id == tenant.id)
        .first()
    )
    if not board:
        raise HTTPException(status_code=404, detail="Board not found in this tenant")

    if board_in.name is not None:
        board.name = board_in.name
    if board_in.description is not None:
        board.description = board_in.description
    if board_in.color is not None:
        board.color = board_in.color

    db.commit()
    db.refresh(board)

    log_activity(
        db=db,
        tenant_id=tenant.id,
        org_id=tenant.org_id,
        board_id=board.id,
        user_id=current_user.id,
        action="BOARD_UPDATED",
        entity_type="board",
        entity_id=board.id,
        details={"name": board.name},
    )

    await ws_manager.broadcast_to_room(
        tenant_id=tenant.id,
        board_id=board.id,
        event=build_event(EVENT_BOARD_UPDATED, {
            "id": board.id,
            "name": board.name,
            "description": board.description,
            "color": board.color,
        }, user={"id": current_user.id, "name": current_user.name}),
    )

    return board


@router.delete("/{board_id}")
def delete_board(
    board_id: str,
    tenant: Tenant = Depends(require_tenant_access(ROLE_TENANT_ADMIN)),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes a board and all its columns and tasks. Tenant Admin required."""
    board = (
        db.query(Board)
        .filter(Board.id == board_id, Board.tenant_id == tenant.id)
        .first()
    )
    if not board:
        raise HTTPException(status_code=404, detail="Board not found in this tenant")

    board_name = board.name
    db.delete(board)
    db.commit()

    log_activity(
        db=db,
        tenant_id=tenant.id,
        org_id=tenant.org_id,
        user_id=current_user.id,
        action="BOARD_DELETED",
        entity_type="board",
        entity_id=board_id,
        details={"name": board_name},
    )

    return {"message": "Board deleted successfully"}
