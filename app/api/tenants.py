from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Tenant, Membership, User, Board, BoardColumn
from app.schemas import TenantResponse, BoardCreate, BoardResponse, UserPublic
from app.security import ROLE_ORG_ADMIN, ROLE_TENANT_ADMIN, ROLE_MEMBER
from app.api.deps import get_current_user, require_tenant_access
from app.services.activity import log_activity

router = APIRouter(prefix="/tenants", tags=["Tenants & Branches"])


class AddMemberRequest(BaseModel):
    email: EmailStr
    role: str = ROLE_MEMBER  # tenant_admin or member


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant_details(
    tenant: Tenant = Depends(require_tenant_access(ROLE_MEMBER)),
):
    """Fetches details of a specific branch/tenant. Requires membership in the tenant or org admin."""
    return tenant


@router.get("/{tenant_id}/members")
def list_tenant_members(
    tenant: Tenant = Depends(require_tenant_access(ROLE_MEMBER)),
    db: Session = Depends(get_db),
):
    """Lists all members assigned to this specific branch/tenant."""
    memberships = (
        db.query(Membership)
        .filter(Membership.tenant_id == tenant.id)
        .all()
    )

    # Also include org admins who have implicit access
    org_admins = (
        db.query(Membership)
        .filter(Membership.org_id == tenant.org_id, Membership.role == ROLE_ORG_ADMIN, Membership.tenant_id == None)
        .all()
    )

    all_members = {}
    for m in memberships:
        if m.user:
            all_members[m.user.id] = {
                "id": m.user.id,
                "name": m.user.name,
                "email": m.user.email,
                "avatar_color": m.user.avatar_color,
                "role": m.role,
                "membership_id": m.id,
            }

    for m in org_admins:
        if m.user and m.user.id not in all_members:
            all_members[m.user.id] = {
                "id": m.user.id,
                "name": m.user.name,
                "email": m.user.email,
                "avatar_color": m.user.avatar_color,
                "role": ROLE_ORG_ADMIN,
                "membership_id": m.id,
            }

    return list(all_members.values())


@router.post("/{tenant_id}/members")
def add_tenant_member(
    req: AddMemberRequest,
    tenant: Tenant = Depends(require_tenant_access(ROLE_TENANT_ADMIN)),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Adds a user to this branch with a specific role (Tenant Admin or Member). Requires Tenant Admin."""
    target_user = db.query(User).filter(User.email == req.email.lower()).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{req.email}' not found.",
        )

    # Check if already a member
    existing = (
        db.query(Membership)
        .filter(Membership.user_id == target_user.id, Membership.tenant_id == tenant.id)
        .first()
    )
    if existing:
        existing.role = req.role
        db.commit()
        return {"message": "Membership updated", "role": req.role}

    membership = Membership(
        user_id=target_user.id,
        org_id=tenant.org_id,
        tenant_id=tenant.id,
        role=req.role,
    )
    db.add(membership)
    db.commit()

    log_activity(
        db=db,
        tenant_id=tenant.id,
        org_id=tenant.org_id,
        user_id=current_user.id,
        action="MEMBER_ADDED",
        entity_type="membership",
        entity_id=membership.id,
        details={"member_name": target_user.name, "member_email": target_user.email, "role": req.role},
    )

    return {"message": "Member added successfully", "membership_id": membership.id}


@router.get("/{tenant_id}/boards", response_model=List[BoardResponse])
def list_tenant_boards(
    tenant: Tenant = Depends(require_tenant_access(ROLE_MEMBER)),
    db: Session = Depends(get_db),
):
    """Lists all Kanban boards within this branch/tenant."""
    return db.query(Board).filter(Board.tenant_id == tenant.id).order_by(Board.created_at.desc()).all()


@router.post("/{tenant_id}/boards", response_model=BoardResponse)
def create_tenant_board(
    board_in: BoardCreate,
    tenant: Tenant = Depends(require_tenant_access(ROLE_TENANT_ADMIN)),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Creates a new Kanban Board scoped to this branch/tenant.
    Automatically initializes standard Kanban columns: 'Backlog', 'To Do', 'In Progress', 'Done'.
    """
    board = Board(
        org_id=tenant.org_id,
        tenant_id=tenant.id,
        name=board_in.name,
        description=board_in.description or "",
        color=board_in.color or "#6366f1",
        created_by_id=current_user.id,
    )
    db.add(board)
    db.flush()

    # Pre-populate default columns
    default_columns = [
        {"title": "Backlog", "order": 1000.0, "wip_limit": 0},
        {"title": "To Do", "order": 2000.0, "wip_limit": 0},
        {"title": "In Progress", "order": 3000.0, "wip_limit": 5},
        {"title": "Done", "order": 4000.0, "wip_limit": 0},
    ]
    for col_data in default_columns:
        col = BoardColumn(
            tenant_id=tenant.id,
            board_id=board.id,
            title=col_data["title"],
            order=col_data["order"],
            wip_limit=col_data["wip_limit"],
        )
        db.add(col)

    db.commit()
    db.refresh(board)

    log_activity(
        db=db,
        tenant_id=tenant.id,
        org_id=tenant.org_id,
        board_id=board.id,
        user_id=current_user.id,
        action="BOARD_CREATED",
        entity_type="board",
        entity_id=board.id,
        details={"name": board.name},
    )

    return board
