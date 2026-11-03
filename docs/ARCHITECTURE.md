# System Architecture & Technical Design

## 1. System Overview

The **Julley Real-Time Collaborative Kanban System** is engineered to support enterprise-grade multi-organization and multi-tenant hierarchies with strict tenant data isolation, real-time live synchronization over WebSockets, and conflict-free collaboration using Optimistic Concurrency Control (OCC) and Fractional Indexing (LexoRank).

```
                      +-----------------------------+
                      |       Web Client (SPA)      |
                      |  Tailwind + Vanilla JS + WS |
                      +--------------+--------------+
                                     |
                         HTTPS / WSS Connection
                                     |
                      +--------------v--------------+
                      |      FastAPI ASGI Server    |
                      +--------------+--------------+
                                     |
          +--------------------------+--------------------------+
          |                                                     |
+---------v---------+                                 +---------v---------+
|   REST API Layer  |                                 | WebSocket Manager |
| - Auth & JWT      |                                 | - Scoped Channels |
| - Tenancy Check   |                                 | - Presence Hub    |
| - RBAC Guard      |                                 | - Focus Tracking  |
| - OCC Validator   |                                 | - Broadcast Hub   |
+---------+---------+                                 +---------+---------+
          |                                                     |
          +--------------------------+--------------------------+
                                     |
                      +--------------v--------------+
                      |   SQLAlchemy ORM + SQLite   |
                      |  (WAL Mode + Foreign Keys)  |
                      +-----------------------------+
```

---

## 2. Multi-Organization & Multi-Tenant Hierarchy

### Hierarchy Breakdown:
1. **Organization**: The top-level corporate account (e.g., `Julley Online Pvt. Ltd.`, `Acme Cloud`).
2. **Tenant (Branch)**: Autonomous organizational division or physical branch (e.g., `Bangalore HQ`, `Hyderabad Innovation Hub`).
3. **Board**: Kanban boards scoped strictly to a specific Tenant (e.g., `Platform Engineering Sprint 24`).
4. **Column**: Workflow stage scoped to a Board and Tenant (e.g., `Backlog`, `To Do`, `In Progress`, `Done`).
5. **Task**: Work item scoped to a Column, Board, and Tenant.
6. **Activity Log**: Immutable audit trail scoped to a Tenant.

---

## 3. Tenancy Isolation Strategies & Architectural Trade-offs

| Strategy | Data Isolation Level | Operational Overhead | Schema Migrations | Cost & Resource Utilization | Why Julley Chose Shared Database + Discriminator |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Database-per-Tenant** | Highest (physical separation) | Very High (managing hundreds of databases) | Complex (rolling migrations per DB) | High (idle database overhead, connection pooling exhaustion) | Too heavy for dynamic branch creation and cross-branch analytics. |
| **Schema-per-Tenant** | High (PostgreSQL schemas) | Moderate | Moderate (must run migrations per schema) | Moderate | SQLite does not support schemas natively; adds schema switching complexity. |
| **Shared Database + Tenant Discriminator (Chosen)** | High (enforced in middleware and query filters) | Minimal (single database, unified migrations) | Zero-friction (single migration for all tenants) | Optimal (pooled connections, efficient caching, low memory) | **Best balance for scale, agile branch creation, and low overhead, backed by strict ORM/middleware scoping.** |

### Security Guarantees in Shared-Database Tenancy:
1. **API Dependency Injection (`require_tenant_access`)**:
   - The route dependency intercepts incoming requests, resolves `tenant_id` from the path, and validates that the authenticated user possesses valid `Membership` in that specific tenant (or is Org Admin).
   - Unauthorized attempts return `403 Forbidden` immediately.
2. **Double-Filter SQL Scoping**:
   - Every lookup query explicitly filters `WHERE id = :entity_id AND tenant_id = :tenant_id`.
   - Even if a malicious actor enumerates or guesses a task UUID from another branch, the database returns `404 Not Found`.

---

## 4. Role-Based Access Control (RBAC) Matrix

| Capability / Action | Org Admin | Tenant Admin | Member |
| :--- | :---: | :---: | :---: |
| Create new Tenants / Branches | ✅ | ❌ | ❌ |
| Manage Organization Memberships | ✅ | ❌ | ❌ |
| Access all Branches under the Organization | ✅ | ❌ | ❌ |
| Create / Edit / Delete Boards in Branch | ✅ | ✅ | ❌ |
| Create / Edit / Delete Columns in Board | ✅ | ✅ | ❌ |
| Set Column WIP Limits | ✅ | ✅ | ❌ |
| Add Members to Branch | ✅ | ✅ | ❌ |
| Create / Update / Move Tasks | ✅ | ✅ | ✅ |
| Delete Tasks | ✅ | ✅ | ✅ |
| View Tenant Activity Audit Stream | ✅ | ✅ | ✅ |

---

## 5. Concurrency Control & Conflict Resolution Strategy

### A. Optimistic Concurrency Control (OCC)
In real-time multi-user environments, Pessimistic Locking (locking rows during edit) causes severe database deadlocks and prevents collaborators from viewing or updating related fields. Instead, we implement **Optimistic Concurrency Control**:
1. Every `Task` row has a `version` integer (starting at `1`).
2. When the client opens a task or initiates an update, it submits `expected_version`.
3. If `task.version == expected_version`:
   - Update is applied.
   - `task.version` increments to `version + 1`.
   - Update event is broadcast over WebSockets.
4. If `task.version != expected_version`:
   - Server returns **HTTP 409 Conflict**.
   - Body contains the server's latest state, client's stale version, and server's current version.
   - Client displays a **Side-by-Side Conflict Resolution Modal** offering 3 paths:
     - **Keep Server Version**: Discards local edits and updates the client to latest state.
     - **Overwrite with My Changes**: Forces the update by submitting against latest version.
     - **Merge Changes**: Automatically merges non-conflicting fields.

### B. Fractional Indexing for Drag-and-Drop (LexoRank)
Traditional integer ranking (`order = 1, 2, 3...`) requires updating all subsequent rows whenever an item is inserted or moved:
- **Integer Reordering**: Moving task to position 2 in a column of 50 tasks triggers **49 SQL UPDATE statements**, mass row locks, and drag-and-drop race conditions.
- **Fractional Indexing (Our Solution)**:
  - Task order is a 64-bit floating point number.
  - Inserting between Task A (`1000.0`) and Task B (`2000.0`):
    $$\text{new\_order} = \frac{1000.0 + 2000.0}{2.0} = 1500.0$$
  - Requires **exactly ONE SQL UPDATE statement** ($O(1)$ database write).
  - **Auto-Rebalancing**: If the fractional gap between tasks falls below $1 \times 10^{-4}$, the backend automatically re-spaces tasks ($1000, 2000, 3000...$) asynchronously.

---

## 6. Real-Time WebSocket Architecture

### Scoped Channels per Tenant:
- WebSocket endpoint: `/ws?token={jwt}&tenant_id={tenant_id}&board_id={board_id}`.
- Connection verification: Validates JWT signature and asserts that the user belongs to `tenant_id`. Unauthorized connections are closed with code `1008 Policy Violation`.
- Room Key: `tenant:{tenant_id}:board:{board_id}`.
- All broadcasts are strictly restricted to the room key, completely eliminating cross-tenant event leakage.

### Presence & Focus Indicators:
- **Join/Leave**: When a socket connects or disconnects, the server updates active presence and broadcasts `USER_JOINED` / `USER_LEFT`.
- **Task Focus**: When a user opens a task detail drawer, client sends `FOCUS_TASK`. Collaborators see a real-time glowing border and avatar chip: *"Alice is viewing this task"*.
- **Heartbeat**: Ping/Pong every 25 seconds keeps connections alive through firewalls and NAT gateways.
- **Network Recovery**: On connection loss, the client attempts reconnection with exponential backoff and automatically resynchronizes board state from REST API on recovery.
