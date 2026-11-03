import json
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import Tenant, ActivityLog, User
from app.schemas import ActivityLogResponse, UserPublic
from app.security import ROLE_MEMBER
from app.api.deps import require_tenant_access

router = APIRouter(prefix="/tenants/{tenant_id}/activities", tags=["Activity Logs"])


@router.get("", response_model=List[ActivityLogResponse])
def get_tenant_activities(
    board_id: Optional[str] = Query(None, description="Filter by board ID"),
    task_id: Optional[str] = Query(None, description="Filter by task ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tenant: Tenant = Depends(require_tenant_access(ROLE_MEMBER)),
    db: Session = Depends(get_db),
):
    """
    Fetches real-time activity and audit logs strictly scoped to this tenant/branch.
    Zero cross-tenant data leakage.
    """
    query = (
        db.query(ActivityLog)
        .options(joinedload(ActivityLog.user))
        .filter(ActivityLog.tenant_id == tenant.id)
    )

    if board_id:
        query = query.filter(ActivityLog.board_id == board_id)
    if task_id:
        query = query.filter(ActivityLog.task_id == task_id)

    logs = query.order_by(ActivityLog.created_at.desc()).offset(offset).limit(limit).all()

    result = []
    for log in logs:
        user_public = None
        if log.user:
            user_public = UserPublic(
                id=log.user.id,
                name=log.user.name,
                email=log.user.email,
                avatar_color=log.user.avatar_color,
            )

        details_parsed = {}
        if log.details:
            try:
                details_parsed = json.loads(log.details)
            except Exception:
                details_parsed = {"raw": log.details}

        result.append(
            ActivityLogResponse(
                id=log.id,
                tenant_id=log.tenant_id,
                org_id=log.org_id,
                board_id=log.board_id,
                task_id=log.task_id,
                user_id=log.user_id,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                details=details_parsed,
                created_at=log.created_at,
                user=user_public,
            )
        )

    return result
