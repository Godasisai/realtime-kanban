from typing import Dict, Any

# Event Types
EVENT_TASK_CREATED = "TASK_CREATED"
EVENT_TASK_UPDATED = "TASK_UPDATED"
EVENT_TASK_MOVED = "TASK_MOVED"
EVENT_TASK_DELETED = "TASK_DELETED"

EVENT_COLUMN_CREATED = "COLUMN_CREATED"
EVENT_COLUMN_UPDATED = "COLUMN_UPDATED"
EVENT_COLUMN_MOVED = "COLUMN_MOVED"
EVENT_COLUMN_DELETED = "COLUMN_DELETED"

EVENT_BOARD_UPDATED = "BOARD_UPDATED"
EVENT_ACTIVITY_LOGGED = "ACTIVITY_LOGGED"


def build_event(event_type: str, payload: Any, user: Dict[str, Any] = None) -> Dict[str, Any]:
    return {
        "type": event_type,
        "payload": payload,
        "user": user or {},
    }
