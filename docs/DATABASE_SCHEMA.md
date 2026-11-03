# Database Schema & Entity-Relationship (ER) Documentation

## 1. Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    ORGANIZATIONS ||--o{ TENANTS : "has branches"
    ORGANIZATIONS ||--o{ MEMBERSHIPS : "has memberships"
    ORGANIZATIONS ||--o{ BOARDS : "owns"
    
    TENANTS ||--o{ MEMBERSHIPS : "assigns users"
    TENANTS ||--o{ BOARDS : "scopes"
    TENANTS ||--o{ COLUMNS : "scopes"
    TENANTS ||--o{ TASKS : "scopes"
    TENANTS ||--o{ ACTIVITY_LOGS : "logs"

    USERS ||--o{ MEMBERSHIPS : "belongs to"
    USERS ||--o{ TASKS : "assigned to"
    USERS ||--o{ ACTIVITY_LOGS : "acts"

    BOARDS ||--o{ COLUMNS : "contains"
    BOARDS ||--o{ TASKS : "groups"
    BOARDS ||--o{ ACTIVITY_LOGS : "tracks"

    COLUMNS ||--o{ TASKS : "organizes"

    ORGANIZATIONS {
        string id PK "UUID"
        string name "Company name"
        string slug UK "Unique URL slug"
        datetime created_at
        datetime updated_at
    }

    TENANTS {
        string id PK "UUID"
        string org_id FK "References organizations.id"
        string name "Branch / Department name"
        string slug "Branch slug"
        string location "Geographic location"
        datetime created_at
        datetime updated_at
    }

    USERS {
        string id PK "UUID"
        string email UK "User login email"
        string name "Full name"
        string hashed_password "Bcrypt digest"
        string avatar_color "Hex code"
        datetime created_at
    }

    MEMBERSHIPS {
        string id PK "UUID"
        string user_id FK "References users.id"
        string org_id FK "References organizations.id"
        string tenant_id FK "References tenants.id (nullable for Org Admin)"
        string role "org_admin | tenant_admin | member"
        datetime created_at
    }

    BOARDS {
        string id PK "UUID"
        string org_id FK "References organizations.id"
        string tenant_id FK "References tenants.id"
        string name "Board name"
        text description
        string color "Hex code"
        string created_by_id FK "References users.id"
        datetime created_at
        datetime updated_at
    }

    COLUMNS {
        string id PK "UUID"
        string tenant_id FK "References tenants.id"
        string board_id FK "References boards.id"
        string title "Column title (e.g., In Progress)"
        float order "Fractional ordering index"
        int wip_limit "Work In Progress limit (0 = none)"
        datetime created_at
        datetime updated_at
    }

    TASKS {
        string id PK "UUID"
        string tenant_id FK "References tenants.id"
        string board_id FK "References boards.id"
        string column_id FK "References columns.id"
        string title "Task title"
        text description "Markdown description"
        string priority "low | medium | high | urgent"
        float order "Fractional ordering index"
        int version "Optimistic Concurrency Control counter"
        string assignee_id FK "References users.id"
        datetime due_date
        text tags "JSON array of tags"
        string created_by_id FK "References users.id"
        datetime created_at
        datetime updated_at
    }

    ACTIVITY_LOGS {
        string id PK "UUID"
        string tenant_id FK "References tenants.id"
        string org_id FK "References organizations.id"
        string board_id FK "References boards.id"
        string task_id "UUID of related task"
        string user_id FK "References users.id"
        string action "TASK_CREATED | TASK_MOVED | etc"
        string entity_type "task | column | board"
        string entity_id "Target UUID"
        text details "JSON audit changes"
        datetime created_at
    }
```

---

## 2. Table Specifications & Indexing Strategy

### 1. `organizations`
- **Purpose**: Top-level multi-tenant container.
- **Indexes**:
  - `PRIMARY KEY (id)`
  - `UNIQUE INDEX (slug)`

### 2. `tenants`
- **Purpose**: Branch or autonomous business unit under an organization.
- **Indexes**:
  - `PRIMARY KEY (id)`
  - `INDEX (org_id)`
  - `UNIQUE CONSTRAINT (org_id, slug)`

### 3. `users`
- **Purpose**: Global user identities across organizations.
- **Indexes**:
  - `PRIMARY KEY (id)`
  - `UNIQUE INDEX (email)`

### 4. `memberships`
- **Purpose**: Junction table binding users to organizations, branches, and roles.
- **Indexes**:
  - `PRIMARY KEY (id)`
  - `INDEX ix_membership_user_tenant (user_id, tenant_id)`
  - `INDEX ix_membership_user_org (user_id, org_id)`

### 5. `boards`
- **Purpose**: Kanban boards belonging to a tenant.
- **Indexes**:
  - `PRIMARY KEY (id)`
  - `INDEX ix_boards_tenant (tenant_id)`
  - `INDEX (org_id)`

### 6. `columns`
- **Purpose**: Workflow stages within a board.
- **Indexes**:
  - `PRIMARY KEY (id)`
  - `INDEX ix_columns_board_tenant (board_id, tenant_id)`
  - `INDEX (order)`

### 7. `tasks`
- **Purpose**: Actionable items with fractional ordering and OCC versioning.
- **Indexes**:
  - `PRIMARY KEY (id)`
  - `INDEX ix_tasks_tenant_column (tenant_id, column_id)`
  - `INDEX ix_tasks_tenant_board (tenant_id, board_id)`
  - `INDEX (order)`
  - `INDEX (priority)`
  - `INDEX (assignee_id)`

### 8. `activity_logs`
- **Purpose**: Immutable audit stream scoped by tenant.
- **Indexes**:
  - `PRIMARY KEY (id)`
  - `INDEX ix_activity_tenant_created (tenant_id, created_at)`
  - `INDEX (board_id)`
  - `INDEX (task_id)`
  - `INDEX (user_id)`
