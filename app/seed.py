import json
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models import Organization, Tenant, User, Membership, Board, BoardColumn, Task, ActivityLog
from app.security import get_password_hash, ROLE_ORG_ADMIN, ROLE_TENANT_ADMIN, ROLE_MEMBER


def seed_database(db: Session) -> None:
    """Seeds the database with rich multi-org, multi-tenant sample data if empty."""
    if db.query(Organization).first():
        return  # Already seeded

    print("Seeding database with Julley Online multi-tenant dataset...")
    now = datetime.now(timezone.utc)

    # 1. Create Users
    users_data = [
        {"email": "sai@julley.com", "name": "Sai Ammanna Naidu", "color": "#6366f1"},
        {"email": "priya@julley.com", "name": "Priya Sharma", "color": "#ec4899"},
        {"email": "rahul@julley.com", "name": "Rahul Varma", "color": "#10b981"},
        {"email": "ananya@julley.com", "name": "Ananya Reddy", "color": "#f59e0b"},
        {"email": "vikram@julley.com", "name": "Vikram Rao", "color": "#8b5cf6"},
        {"email": "john@acme.com", "name": "John Doe (External Org)", "color": "#64748b"},
    ]

    users = {}
    default_hashed = get_password_hash("password123")
    for u in users_data:
        user = User(
            email=u["email"],
            name=u["name"],
            hashed_password=default_hashed,
            avatar_color=u["color"],
        )
        db.add(user)
        db.flush()
        users[u["email"]] = user

    # 2. Create Organizations
    org_julley = Organization(
        name="Julley Online Pvt. Ltd.",
        slug="julley-online",
    )
    org_acme = Organization(
        name="Acme Cloud Solutions",
        slug="acme-cloud",
    )
    db.add(org_julley)
    db.add(org_acme)
    db.flush()

    # 3. Create Tenants (Branches)
    tenant_blr = Tenant(
        org_id=org_julley.id,
        name="Bangalore Headquarters",
        slug="bangalore-hq",
        location="Bengaluru, KA, India",
    )
    tenant_hyd = Tenant(
        org_id=org_julley.id,
        name="Hyderabad Innovation Hub",
        slug="hyderabad-hub",
        location="Hyderabad, TS, India",
    )
    tenant_nyc = Tenant(
        org_id=org_acme.id,
        name="New York Branch",
        slug="nyc-branch",
        location="New York, NY, USA",
    )
    db.add(tenant_blr)
    db.add(tenant_hyd)
    db.add(tenant_nyc)
    db.flush()

    # 4. Create Memberships (RBAC Hierarchy)
    memberships_data = [
        # Sai: Org Admin of Julley Online (Access to both Bangalore & Hyderabad)
        {"user": users["sai@julley.com"], "org": org_julley, "tenant": None, "role": ROLE_ORG_ADMIN},
        {"user": users["sai@julley.com"], "org": org_julley, "tenant": tenant_blr, "role": ROLE_ORG_ADMIN},
        {"user": users["sai@julley.com"], "org": org_julley, "tenant": tenant_hyd, "role": ROLE_ORG_ADMIN},

        # Priya: Tenant Admin of Bangalore HQ
        {"user": users["priya@julley.com"], "org": org_julley, "tenant": tenant_blr, "role": ROLE_TENANT_ADMIN},

        # Rahul: Member of Bangalore HQ
        {"user": users["rahul@julley.com"], "org": org_julley, "tenant": tenant_blr, "role": ROLE_MEMBER},

        # Ananya: Tenant Admin of Hyderabad Hub
        {"user": users["ananya@julley.com"], "org": org_julley, "tenant": tenant_hyd, "role": ROLE_TENANT_ADMIN},

        # Vikram: Member of Hyderabad Hub
        {"user": users["vikram@julley.com"], "org": org_julley, "tenant": tenant_hyd, "role": ROLE_MEMBER},

        # John: Org Admin of Acme (Isolated completely from Julley)
        {"user": users["john@acme.com"], "org": org_acme, "tenant": None, "role": ROLE_ORG_ADMIN},
        {"user": users["john@acme.com"], "org": org_acme, "tenant": tenant_nyc, "role": ROLE_ORG_ADMIN},
    ]

    for m in memberships_data:
        mem = Membership(
            user_id=m["user"].id,
            org_id=m["org"].id,
            tenant_id=m["tenant"].id if m["tenant"] else None,
            role=m["role"],
        )
        db.add(mem)
    db.flush()

    # 5. Create Boards & Columns for Bangalore HQ
    board_sprint = Board(
        org_id=org_julley.id,
        tenant_id=tenant_blr.id,
        name="Platform Engineering Sprint 24",
        description="Core platform services, multi-tenant isolation, real-time collaboration, and OCC.",
        color="#4f46e5",
        created_by_id=users["sai@julley.com"].id,
    )
    db.add(board_sprint)
    db.flush()

    columns_blr = [
        {"title": "Backlog", "order": 1000.0, "wip": 0},
        {"title": "To Do", "order": 2000.0, "wip": 0},
        {"title": "In Progress", "order": 3000.0, "wip": 4},
        {"title": "In Review", "order": 4000.0, "wip": 3},
        {"title": "Done", "order": 5000.0, "wip": 0},
    ]
    cols = {}
    for c in columns_blr:
        col = BoardColumn(
            tenant_id=tenant_blr.id,
            board_id=board_sprint.id,
            title=c["title"],
            order=c["order"],
            wip_limit=c["wip"],
        )
        db.add(col)
        db.flush()
        cols[c["title"]] = col

    # 6. Create Tasks for Bangalore HQ Board
    tasks_blr = [
        {
            "col": "In Progress",
            "title": "Enforce Strict Tenant Data Isolation in Middleware",
            "desc": "Ensure every SQL query and WebSocket connection is strictly validated against the user's tenant membership to avoid cross-tenant data leakage.",
            "priority": "urgent",
            "order": 1000.0,
            "version": 3,
            "assignee": users["rahul@julley.com"],
            "tags": ["Security", "Backend", "Multi-Tenant"],
            "due": now + timedelta(days=2),
        },
        {
            "col": "In Review",
            "title": "Real-Time WebSocket Scoping per Tenant & Board",
            "desc": "Implement tenant-isolated rooms in ConnectionManager with automatic presence heartbeats and join/leave broadcast events.",
            "priority": "high",
            "order": 1000.0,
            "version": 2,
            "assignee": users["priya@julley.com"],
            "tags": ["WebSockets", "Real-Time", "Collab"],
            "due": now + timedelta(days=3),
        },
        {
            "col": "To Do",
            "title": "Optimistic Concurrency Control (OCC) with Conflict Resolution",
            "desc": "Detect concurrent edits using version increments. Return HTTP 409 Conflict with server diff and show interactive 3-way merge modal.",
            "priority": "high",
            "order": 1000.0,
            "version": 1,
            "assignee": users["sai@julley.com"],
            "tags": ["Concurrency", "OCC"],
            "due": now + timedelta(days=4),
        },
        {
            "col": "Done",
            "title": "Fractional Indexing for O(1) Drag and Drop",
            "desc": "Implemented midpoint floating-point ordering (prev + next) / 2 to avoid mass database reordering locks during task moves.",
            "priority": "medium",
            "order": 1000.0,
            "version": 4,
            "assignee": users["rahul@julley.com"],
            "tags": ["Database", "Algorithms"],
            "due": now - timedelta(days=1),
        },
        {
            "col": "To Do",
            "title": "Undo/Redo History Stack in Kanban Frontend",
            "desc": "Implement client-side action stack for moving tasks and editing details, with Ctrl+Z and Ctrl+Y keyboard shortcuts.",
            "priority": "medium",
            "order": 2000.0,
            "version": 1,
            "assignee": users["priya@julley.com"],
            "tags": ["Frontend", "UX"],
            "due": now + timedelta(days=5),
        },
        {
            "col": "Backlog",
            "title": "Real-time Presence Indicators & Active Task Focus Badges",
            "desc": "Show live avatar chips in top bar and 'Alice is viewing this task' badges in task cards when collaborator opens drawer.",
            "priority": "low",
            "order": 1000.0,
            "version": 1,
            "assignee": users["sai@julley.com"],
            "tags": ["Real-Time", "Presence"],
            "due": now + timedelta(days=7),
        },
        {
            "col": "Done",
            "title": "Comprehensive Automated Tests for RBAC & Tenant Isolation",
            "desc": "Unit and integration tests verifying cross-tenant access rejection, OCC version conflict handling, and fractional ordering.",
            "priority": "urgent",
            "order": 2000.0,
            "version": 2,
            "assignee": users["sai@julley.com"],
            "tags": ["Testing", "QA", "Security"],
            "due": now - timedelta(days=2),
        },
    ]

    for t in tasks_blr:
        task = Task(
            tenant_id=tenant_blr.id,
            board_id=board_sprint.id,
            column_id=cols[t["col"]].id,
            title=t["title"],
            description=t["desc"],
            priority=t["priority"],
            order=t["order"],
            version=t["version"],
            assignee_id=t["assignee"].id if t["assignee"] else None,
            due_date=t["due"],
            tags=json.dumps(t["tags"]),
            created_by_id=users["sai@julley.com"].id,
        )
        db.add(task)
        db.flush()

        # Seed realistic activity log
        log = ActivityLog(
            tenant_id=tenant_blr.id,
            org_id=org_julley.id,
            board_id=board_sprint.id,
            task_id=task.id,
            user_id=users["sai@julley.com"].id,
            action="TASK_CREATED",
            entity_type="task",
            entity_id=task.id,
            details=json.dumps({"title": task.title, "column": t["col"]}),
            created_at=now - timedelta(hours=4),
        )
        db.add(log)

    # 7. Create Board for Hyderabad Innovation Hub
    board_hyd = Board(
        org_id=org_julley.id,
        tenant_id=tenant_hyd.id,
        name="AI & Analytics Modernization",
        description="Autonomous agents, RAG pipeline, and real-time event analytics.",
        color="#0ea5e9",
        created_by_id=users["ananya@julley.com"].id,
    )
    db.add(board_hyd)
    db.flush()

    for title, order in [("Backlog", 1000.0), ("To Do", 2000.0), ("In Progress", 3000.0), ("Done", 4000.0)]:
        col = BoardColumn(tenant_id=tenant_hyd.id, board_id=board_hyd.id, title=title, order=order)
        db.add(col)
        db.flush()
        if title == "In Progress":
            task_hyd = Task(
                tenant_id=tenant_hyd.id,
                board_id=board_hyd.id,
                column_id=col.id,
                title="Integrate Fast Semantic Search over Task Logs",
                description="Embed activity stream using vector indices for semantic incident analysis.",
                priority="high",
                order=1000.0,
                version=1,
                assignee_id=users["vikram@julley.com"].id,
                tags=json.dumps(["AI", "Analytics"]),
                created_by_id=users["ananya@julley.com"].id,
            )
            db.add(task_hyd)

    # 8. Create Board for Acme (To prove cross-org isolation)
    board_acme = Board(
        org_id=org_acme.id,
        tenant_id=tenant_nyc.id,
        name="Acme Internal Operations",
        description="Confidential Acme Cloud internal tasks. Completely isolated from Julley.",
        color="#10b981",
        created_by_id=users["john@acme.com"].id,
    )
    db.add(board_acme)
    db.flush()
    col_acme = BoardColumn(tenant_id=tenant_nyc.id, board_id=board_acme.id, title="Confidential", order=1000.0)
    db.add(col_acme)
    db.flush()
    task_acme = Task(
        tenant_id=tenant_nyc.id,
        board_id=board_acme.id,
        column_id=col_acme.id,
        title="Acme Proprietary Infrastructure",
        description="Must never be accessible to any Julley Online users.",
        priority="urgent",
        order=1000.0,
        version=1,
        created_by_id=users["john@acme.com"].id,
    )
    db.add(task_acme)

    db.commit()
    print("Database successfully seeded with realistic multi-tenant hierarchy and boards!")
