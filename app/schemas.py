from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


# ==================== User & Auth Schemas ====================

class UserBase(BaseModel):
    email: str
    name: str
    avatar_color: Optional[str] = "#3b82f6"


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(UserBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UserPublic(BaseModel):
    id: str
    name: str
    email: str
    avatar_color: str
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenPayload(BaseModel):
    sub: str
    exp: int


# ==================== Organization & Tenant Schemas ====================

class OrgBase(BaseModel):
    name: str
    slug: str


class OrgCreate(OrgBase):
    pass


class OrgResponse(OrgBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TenantBase(BaseModel):
    name: str
    slug: str
    location: Optional[str] = ""


class TenantCreate(TenantBase):
    pass


class TenantResponse(TenantBase):
    id: str
    org_id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class MembershipResponse(BaseModel):
    id: str
    user_id: str
    org_id: str
    tenant_id: Optional[str] = None
    role: str
    user: Optional[UserPublic] = None
    model_config = ConfigDict(from_attributes=True)


# ==================== Board Schemas ====================

class BoardBase(BaseModel):
    name: str
    description: Optional[str] = ""
    color: Optional[str] = "#6366f1"


class BoardCreate(BoardBase):
    pass


class BoardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None


class BoardResponse(BoardBase):
    id: str
    org_id: str
    tenant_id: str
    created_by_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ==================== Column Schemas ====================

class ColumnBase(BaseModel):
    title: str
    wip_limit: Optional[int] = 0


class ColumnCreate(ColumnBase):
    order: Optional[float] = None


class ColumnUpdate(BaseModel):
    title: Optional[str] = None
    wip_limit: Optional[int] = None
    order: Optional[float] = None


class ColumnMoveRequest(BaseModel):
    prev_order: Optional[float] = None
    next_order: Optional[float] = None


class ColumnResponse(ColumnBase):
    id: str
    board_id: str
    tenant_id: str
    order: float
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ==================== Task Schemas ====================

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = ""
    priority: Optional[str] = "medium"  # low, medium, high, urgent
    assignee_id: Optional[str] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = []


class TaskCreate(TaskBase):
    column_id: str
    order: Optional[float] = None


class TaskUpdate(BaseModel):
    """
    Optimistic Concurrency Control (OCC) requires `expected_version`.
    If client's expected_version != server's current version, a 409 Conflict is raised.
    """
    expected_version: int = Field(..., description="The version of the task known to the client for OCC")
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[str] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None


class TaskMoveRequest(BaseModel):
    """
    Drag and Drop move request using Fractional Indexing.
    `prev_order`: order value of the task immediately before target position (or None if moving to top)
    `next_order`: order value of the task immediately after target position (or None if moving to bottom)
    `target_column_id`: destination column
    `expected_version`: for OCC verification
    """
    target_column_id: str
    prev_order: Optional[float] = None
    next_order: Optional[float] = None
    expected_version: Optional[int] = None


class TaskResponse(TaskBase):
    id: str
    tenant_id: str
    board_id: str
    column_id: str
    order: float
    version: int
    created_by_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    assignee: Optional[UserPublic] = None
    model_config = ConfigDict(from_attributes=True)


class ConflictDetail(BaseModel):
    message: str
    conflicting_task: TaskResponse
    client_version: int
    server_version: int


# ==================== Composite Board View ====================

class ColumnWithTasks(ColumnResponse):
    tasks: List[TaskResponse] = []


class BoardDetailResponse(BoardResponse):
    columns: List[ColumnWithTasks] = []


# ==================== Activity Log Schemas ====================

class ActivityLogResponse(BaseModel):
    id: str
    tenant_id: str
    org_id: str
    board_id: Optional[str] = None
    task_id: Optional[str] = None
    user_id: Optional[str] = None
    action: str
    entity_type: str
    entity_id: str
    details: Dict[str, Any] = {}
    created_at: datetime
    user: Optional[UserPublic] = None
    model_config = ConfigDict(from_attributes=True)
