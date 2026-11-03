import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    tenants = relationship("Tenant", back_populates="organization", cascade="all, delete-orphan")
    memberships = relationship("Membership", back_populates="organization", cascade="all, delete-orphan")
    boards = relationship("Board", back_populates="organization", cascade="all, delete-orphan")


class Tenant(Base):
    """Tenant represents a Branch or autonomous unit within an Organization."""
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    org_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, index=True)
    location = Column(String(100), nullable=True, default="")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        UniqueConstraint("org_id", "slug", name="uq_tenant_org_slug"),
    )

    # Relationships
    organization = relationship("Organization", back_populates="tenants")
    memberships = relationship("Membership", back_populates="tenant", cascade="all, delete-orphan")
    boards = relationship("Board", back_populates="tenant", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(150), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    avatar_color = Column(String(20), default="#3b82f6")
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    memberships = relationship("Membership", back_populates="user", cascade="all, delete-orphan")
    assigned_tasks = relationship("Task", foreign_keys="Task.assignee_id", back_populates="assignee")


class Membership(Base):
    """
    User membership within an organization and/or tenant.
    Roles:
      - 'org_admin': Full control across entire organization and all branches.
      - 'tenant_admin': Administrator of this specific tenant (branch).
      - 'member': Contributor in this tenant (can view, create, edit, move tasks).
    """
    __tablename__ = "memberships"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    role = Column(String(30), nullable=False, default="member")  # org_admin, tenant_admin, member
    created_at = Column(DateTime, default=utc_now)

    __table_args__ = (
        Index("ix_membership_user_tenant", "user_id", "tenant_id"),
        Index("ix_membership_user_org", "user_id", "org_id"),
    )

    # Relationships
    user = relationship("User", back_populates="memberships")
    organization = relationship("Organization", back_populates="memberships")
    tenant = relationship("Tenant", back_populates="memberships")


class Board(Base):
    __tablename__ = "boards"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    org_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    color = Column(String(30), default="#6366f1")
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("ix_boards_tenant", "tenant_id"),
    )

    # Relationships
    organization = relationship("Organization", back_populates="boards")
    tenant = relationship("Tenant", back_populates="boards")
    columns = relationship("BoardColumn", back_populates="board", cascade="all, delete-orphan", order_by="BoardColumn.order")
    tasks = relationship("Task", back_populates="board", cascade="all, delete-orphan")


class BoardColumn(Base):
    """Kanban Column scoped by tenant_id and board_id."""
    __tablename__ = "columns"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    board_id = Column(String(36), ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(100), nullable=False)
    order = Column(Float, nullable=False, default=1000.0, index=True)
    wip_limit = Column(Integer, default=0)  # 0 = no limit
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("ix_columns_board_tenant", "board_id", "tenant_id"),
    )

    # Relationships
    board = relationship("Board", back_populates="columns")
    tasks = relationship("Task", back_populates="column", cascade="all, delete-orphan", order_by="Task.order")


class Task(Base):
    """
    Task scoped by tenant_id.
    Includes:
      - `order`: Float for fractional indexing / LexoRank (avoids re-indexing on drag-and-drop).
      - `version`: Integer incremented on each update for Optimistic Concurrency Control (OCC).
    """
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    board_id = Column(String(36), ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
    column_id = Column(String(36), ForeignKey("columns.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    priority = Column(String(20), default="medium", index=True)  # low, medium, high, urgent
    order = Column(Float, nullable=False, default=1000.0, index=True)
    version = Column(Integer, nullable=False, default=1)  # OCC versioning
    assignee_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    due_date = Column(DateTime, nullable=True)
    tags = Column(Text, default="[]")  # JSON serialized list of tags
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("ix_tasks_tenant_column", "tenant_id", "column_id"),
        Index("ix_tasks_tenant_board", "tenant_id", "board_id"),
    )

    # Relationships
    column = relationship("BoardColumn", back_populates="tasks")
    board = relationship("Board", back_populates="tasks")
    assignee = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_tasks")
    creator = relationship("User", foreign_keys=[created_by_id])


class ActivityLog(Base):
    """
    Audit trail scoped by tenant_id.
    Tracks every creation, move, edit, and deletion for accountability and real-time feed.
    """
    __tablename__ = "activity_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    board_id = Column(String(36), ForeignKey("boards.id", ondelete="CASCADE"), nullable=True, index=True)
    task_id = Column(String(36), nullable=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(50), nullable=False)  # TASK_CREATED, TASK_MOVED, TASK_UPDATED, etc.
    entity_type = Column(String(30), nullable=False)  # task, column, board
    entity_id = Column(String(36), nullable=False)
    details = Column(Text, default="{}")  # JSON string
    created_at = Column(DateTime, default=utc_now, index=True)

    __table_args__ = (
        Index("ix_activity_tenant_created", "tenant_id", "created_at"),
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="activity_logs")
    user = relationship("User")
