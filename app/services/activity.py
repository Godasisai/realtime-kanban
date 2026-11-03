import json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models import ActivityLog


def log_activity(
    db: Session,
    tenant_id: str,
    org_id: str,
    user_id: Optional[str],
    action: str,
    entity_type: str,
    entity_id: str,
    board_id: Optional[str] = None,
    task_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> ActivityLog:
    """
    Creates an audit trail entry scoped strictly by tenant_id.
    Ensures zero cross-tenant leakage.
    """
    details_str = json.dumps(details or {})
    log_entry = ActivityLog(
        tenant_id=tenant_id,
        org_id=org_id,
        board_id=board_id,
        task_id=task_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details_str,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry
