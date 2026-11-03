import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import Tenant, Board, BoardColumn, Task, User
from app.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskMoveRequest,
    TaskResponse,
    UserPublic,
)
from app.security import ROLE_MEMBER, ROLE_TENANT_ADMIN
from app.api.deps import get_current_user, require_tenant_access
from app.services.ordering import (
    calculate_fractional_order,
    check_and_rebalance_column_tasks,
)
from app.services.activity import log_activity
from app.websocket.manager import ws_manager
from app.websocket.events import (
    EVENT_TASK_CREATED,
    EVENT_TASK_UPDATED,
    EVENT_TASK_MOVED,
    EVENT_TASK_DELETED,
    build_event,
)

router = APIRouter(prefix="/tenants/{tenant_id}/boards/{board_id}/tasks", tags=["Tasks"])


def serialize_task(t: Task) -> TaskResponse:
    """Helper to convert Task ORM model to TaskResponse schema."""
    assignee_public = None
    if t.assignee:
        assignee_public = UserPublic(
            id=t.assignee.id,
            name=t.assignee.name,
            email=t.assignee.email,
            avatar_color=t.assignee.avatar_color,
        )

    return TaskResponse(
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
        assignee=assignee_public,
    )


@router.post("", response_model=TaskResponse)
async def create_task(
    board_id: str,
    task_in: TaskCreate,
    tenant: Tenant = Depends(require_tenant_access(ROLE_MEMBER)),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Creates a new task in a specified column with fractional indexing.
    Broadcasts real-time event to all collaborators in the tenant room.
    """
    column = (
        db.query(BoardColumn)
        .filter(BoardColumn.id == task_in.column_id, BoardColumn.board_id == board_id, BoardColumn.tenant_id == tenant.id)
        .first()
    )
    if not column:
        raise HTTPException(status_code=404, detail="Column not found on this board")

    if task_in.order is not None:
        new_order = task_in.order
    else:
        # Place at bottom of column
        last_task = (
            db.query(Task)
            .filter(Task.column_id == column.id, Task.tenant_id == tenant.id)
            .order_by(Task.order.desc())
            .first()
        )
        new_order = calculate_fractional_order(prev_order=last_task.order if last_task else None)

    task = Task(
        tenant_id=tenant.id,
        board_id=board_id,
        column_id=column.id,
        title=task_in.title,
        description=task_in.description or "",
        priority=task_in.priority or "medium",
        order=new_order,
        version=1,
        assignee_id=task_in.assignee_id,
        due_date=task_in.due_date,
        tags=json.dumps(task_in.tags or []),
        created_by_id=current_user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Load relationship for response
    if task.assignee_id:
        task.assignee = db.query(User).filter(User.id == task.assignee_id).first()

    res = serialize_task(task)

    log_activity(
        db=db,
        tenant_id=tenant.id,
        org_id=tenant.org_id,
        board_id=board_id,
        task_id=task.id,
        user_id=current_user.id,
        action="TASK_CREATED",
        entity_type="task",
        entity_id=task.id,
        details={"title": task.title, "column": column.title, "priority": task.priority},
    )

    await ws_manager.broadcast_to_room(
        tenant_id=tenant.id,
        board_id=board_id,
        event=build_event(EVENT_TASK_CREATED, res.model_dump(mode="json"), user={
            "id": current_user.id,
            "name": current_user.name,
        }),
    )

    return res


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    board_id: str,
    task_id: str,
    tenant: Tenant = Depends(require_tenant_access(ROLE_MEMBER)),
    db: Session = Depends(get_db),
):
    """Fetches single task. Scoped by tenant_id to prevent cross-tenant data leakage."""
    task = (
        db.query(Task)
        .options(joinedload(Task.assignee))
        .filter(Task.id == task_id, Task.board_id == board_id, Task.tenant_id == tenant.id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found in this tenant")

    return serialize_task(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    board_id: str,
    task_id: str,
    task_in: TaskUpdate,
    tenant: Tenant = Depends(require_tenant_access(ROLE_MEMBER)),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Updates task details using Optimistic Concurrency Control (OCC).
    Validates expected_version against current database version:
      - If versions match: applies update and increments version (version += 1).
      - If mismatch: returns HTTP 409 Conflict with the server's current state.
    """
    task = (
        db.query(Task)
        .options(joinedload(Task.assignee))
        .filter(Task.id == task_id, Task.board_id == board_id, Task.tenant_id == tenant.id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found in this tenant")

    # OCC Check
    if task.version != task_in.expected_version:
        server_state = serialize_task(task).model_dump(mode="json")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Conflict detected: The task was updated by another collaborator while you were editing.",
                "server_task": server_state,
                "client_version": task_in.expected_version,
                "server_version": task.version,
            },
        )

    # Track changed fields for activity logging
    changes = {}
    if task_in.title is not None and task_in.title != task.title:
        changes["title"] = {"old": task.title, "new": task_in.title}
        task.title = task_in.title
    if task_in.description is not None and task_in.description != task.description:
        changes["description"] = "updated"
        task.description = task_in.description
    if task_in.priority is not None and task_in.priority != task.priority:
        changes["priority"] = {"old": task.priority, "new": task_in.priority}
        task.priority = task_in.priority
    if task_in.assignee_id is not None and task_in.assignee_id != task.assignee_id:
        changes["assignee_id"] = {"old": task.assignee_id, "new": task_in.assignee_id}
        task.assignee_id = task_in.assignee_id
    if task_in.due_date is not None:
        task.due_date = task_in.due_date
    if task_in.tags is not None:
        task.tags = json.dumps(task_in.tags)

    # Increment OCC version
    task.version += 1
    db.commit()
    db.refresh(task)

    if task.assignee_id:
        task.assignee = db.query(User).filter(User.id == task.assignee_id).first()
    else:
        task.assignee = None

    res = serialize_task(task)

    log_activity(
        db=db,
        tenant_id=tenant.id,
        org_id=tenant.org_id,
        board_id=board_id,
        task_id=task.id,
        user_id=current_user.id,
        action="TASK_UPDATED",
        entity_type="task",
        entity_id=task.id,
        details={"changes": changes, "new_version": task.version},
    )

    await ws_manager.broadcast_to_room(
        tenant_id=tenant.id,
        board_id=board_id,
        event=build_event(EVENT_TASK_UPDATED, res.model_dump(mode="json"), user={
            "id": current_user.id,
            "name": current_user.name,
        }),
    )

    return res


@router.post("/{task_id}/move", response_model=TaskResponse)
async def move_task(
    board_id: str,
    task_id: str,
    move_req: TaskMoveRequest,
    tenant: Tenant = Depends(require_tenant_access(ROLE_MEMBER)),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Handles Drag-and-Drop movement within or across columns using Fractional Indexing.
    O(1) database update without mass row locking or drag-drop conflicts.
    """
    task = (
        db.query(Task)
        .options(joinedload(Task.assignee))
        .filter(Task.id == task_id, Task.board_id == board_id, Task.tenant_id == tenant.id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found in this tenant")

    target_column = (
        db.query(BoardColumn)
        .filter(BoardColumn.id == move_req.target_column_id, BoardColumn.board_id == board_id, BoardColumn.tenant_id == tenant.id)
        .first()
    )
    if not target_column:
        raise HTTPException(status_code=404, detail="Target column not found on this board")

    source_column_id = task.column_id
    new_order = calculate_fractional_order(
        prev_order=move_req.prev_order,
        next_order=move_req.next_order,
    )

    task.column_id = target_column.id
    task.order = new_order
    task.version += 1
    db.commit()
    db.refresh(task)

    # Check if fractional ordering precision needs rebalancing
    check_and_rebalance_column_tasks(db, column_id=target_column.id, tenant_id=tenant.id)

    res = serialize_task(task)

    log_activity(
        db=db,
        tenant_id=tenant.id,
        org_id=tenant.org_id,
        board_id=board_id,
        task_id=task.id,
        user_id=current_user.id,
        action="TASK_MOVED",
        entity_type="task",
        entity_id=task.id,
        details={
            "from_column_id": source_column_id,
            "to_column_id": target_column.id,
            "to_column_title": target_column.title,
            "new_order": task.order,
            "version": task.version,
        },
    )

    await ws_manager.broadcast_to_room(
        tenant_id=tenant.id,
        board_id=board_id,
        event=build_event(EVENT_TASK_MOVED, {
            "task_id": task.id,
            "source_column_id": source_column_id,
            "target_column_id": target_column.id,
            "order": task.order,
            "version": task.version,
            "task": res.model_dump(mode="json"),
        }, user={"id": current_user.id, "name": current_user.name}),
    )

    return res


@router.delete("/{task_id}")
async def delete_task(
    board_id: str,
    task_id: str,
    tenant: Tenant = Depends(require_tenant_access(ROLE_MEMBER)),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes task and broadcasts removal event."""
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.board_id == board_id, Task.tenant_id == tenant.id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found in this tenant")

    title = task.title
    column_id = task.column_id
    db.delete(task)
    db.commit()

    log_activity(
        db=db,
        tenant_id=tenant.id,
        org_id=tenant.org_id,
        board_id=board_id,
        task_id=task_id,
        user_id=current_user.id,
        action="TASK_DELETED",
        entity_type="task",
        entity_id=task_id,
        details={"title": title, "column_id": column_id},
    )

    await ws_manager.broadcast_to_room(
        tenant_id=tenant.id,
        board_id=board_id,
        event=build_event(EVENT_TASK_DELETED, {
            "task_id": task_id,
            "column_id": column_id,
        }, user={"id": current_user.id, "name": current_user.name}),
    )

    return {"message": "Task deleted successfully"}
