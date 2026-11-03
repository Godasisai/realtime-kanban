# Presentation & Video Recording Script
### Real-Time Collaborative Kanban Board (Multi-Organization + Multi-Tenant)
**Company**: Julley Online Pvt. Ltd. &bull; Technical Assignment Submission  
**Candidate**: Sai Ammanna Naidu  
**Email**: naidugodasi751@gmail.com  
**GitHub**: [https://github.com/Godasisai/realtime-kanban](https://github.com/Godasisai/realtime-kanban)  
**Live Published URL**: [https://julley-kanban.loca.lt](https://julley-kanban.loca.lt) *(Tunnel Password: 219.91.208.112)*  
**Presentation File (.pptx)**: [`Julley_Kanban_Architecture_Presentation_Sai_Ammanna_Naidu.pptx`](file:///c:/Users/hp/Downloads/realtime-kanban/Julley_Kanban_Architecture_Presentation_Sai_Ammanna_Naidu.pptx)

---

## 🎬 Part 1: Word-for-Word Video Recording Script (3 to 4 Minutes)

> **Preparation Before Starting Recording**:
> 1. In terminal, start the server: `python run.py`.
> 2. Open two browser windows side-by-side:
>    - **Left Window**: [http://localhost:8000](http://localhost:8000) (Logged in as **Sai Ammanna Naidu** - Org Admin).
>    - **Right Window**: [http://localhost:8000](http://localhost:8000) (Use top-right switcher to switch to **Priya Sharma** - Tenant Admin).
> 3. Start your screen recording software (OBS, Loom, Windows Game Bar `Win + Alt + R`).

---

### [0:00 - 0:35] Introduction & Multi-Tenant Hierarchy
- **Screen Action**: Show the left browser window full screen, highlighting the top executive header bar, Organization dropdown, and Branch switcher.
- **Spoken Script**:
  > *"Hello team at Julley Online. My name is Sai Ammanna Naidu, and today I am excited to demonstrate my submission for the Real-Time Collaborative Kanban Board assignment with Multi-Organization and Multi-Tenant architecture.*
  >
  > *In this project, I have modeled a complete 5-tier enterprise hierarchy:*
  > *Organization &rarr; Tenants (or Branches) &rarr; Boards &rarr; Columns &rarr; Tasks.*
  >
  > *In the top navigation bar, notice our Organization selector: here we have 'Julley Online Pvt. Ltd.', and under it, multiple branches such as 'Bangalore Headquarters' and 'Hyderabad Innovation Hub'. All business data is strictly scoped by Tenant ID at both the database and middleware layers, preventing any cross-tenant data leakage."*

---

### [0:35 - 1:20] Real-Time Sync & Live Presence (Dual-Window Demonstration)
- **Screen Action**: Arrange the two browser windows side-by-side.
  - Left window: **Sai** (Org Admin).
  - Right window: **Priya** (Tenant Admin).
  - Point mouse at the top-right **Presence Avatars** stack showing "2 online".
  - Drag a task card on the Left Window from *"In Progress"* to *"In Review"*.
- **Spoken Script**:
  > *"Now let's observe live synchronization across collaborators in the same branch. On the left, I am logged in as Sai, the Org Admin, and on the right, I have Priya, the Tenant Admin of Bangalore HQ.*
  >
  > *Notice the top bar: the WebSocket presence tracker immediately displays live avatar chips and an active collaborator count.*
  >
  > *Now watch closely as I drag this task—'Enforce Strict Tenant Data Isolation'—from 'In Progress' to 'In Review' on the left window.*
  >
  > *Immediately, without reloading or polling, Priya's board on the right updates instantly in real time! We also see a live toast notification announcing that Sai moved the task."*

---

### [1:20 - 1:55] Fractional Indexing (LexoRank) & Active Task Focus Indicator
- **Screen Action**:
  - Click on the task card on the Left Window to open the Slide-over Detail Drawer.
  - Notice the Right Window: the task card now displays a glowing red outline and an avatar badge: *"Sai viewing"*.
  - Explain the ordering mathematics.
- **Spoken Script**:
  > *"For task positioning, instead of integer re-indexing which locks the entire database table, I implemented Fractional Indexing—similar to Jira's LexoRank.*
  >
  > *When a task is dropped between two items, its new position is computed as the midpoint: (prev_order + next_order) / 2. This requires exactly ONE database write, completely eliminating drag-and-drop lock contention.*
  >
  > *Furthermore, as I open the Task Detail Drawer on the left, look at Priya's screen on the right: a live presence indicator glows with an active focus badge indicating that Sai is viewing this task right now. When I close the drawer, the focus badge automatically clears."*

---

### [1:55 - 2:40] Optimistic Concurrency Control (OCC) & Conflict Resolution Modal
- **Screen Action**:
  - Open the same task on BOTH windows simultaneously.
  - On Right Window (Priya): Edit title to `"Title by Priya"` and click **Save Changes**. (Version increments to v4).
  - On Left Window (Sai): Without refreshing, edit title to `"Conflicting Title by Sai"` and click **Save Changes**.
  - The **Conflict Resolution Modal** pops up with a side-by-side diff table!
- **Spoken Script**:
  > *"Now let's demonstrate one of the most critical enterprise edge cases: Concurrent Edits.*
  >
  > *Both Sai and Priya have opened this task at version 3. Priya edits the title and clicks Save Changes. Her update succeeds and the server increments the task version to 4.*
  >
  > *Now, Sai attempts to save his changes using the stale version 3. Rather than silently overwriting Priya's work, our FastAPI backend detects the version mismatch and responds with HTTP 409 Conflict.*
  >
  > *The frontend immediately intercepts this and renders our 3-Way Conflict Resolution Modal. It shows a clear side-by-side comparison of Sai's local changes versus the server's latest version. Sai can choose to 'Keep Server Version', 'Overwrite with My Changes', or 'Merge Changes'. Let's click Merge—and the task is cleanly reconciled without data loss!"*

---

### [2:40 - 3:15] Tenant Data Isolation & RBAC Boundaries
- **Screen Action**:
  - In the left window, switch Tenant to `"Hyderabad Innovation Hub"`.
  - Show that Bangalore's tasks disappear and only Hyderabad's boards appear.
  - In the right window, switch user to `"John Doe (Acme Cloud)"`.
  - Show that John is completely blocked from accessing Julley Online data.
  - Click the **"Architecture & ER"** button in the header to show the built-in interactive schema modal.
- **Spoken Script**:
  > *"To demonstrate strict tenant isolation: when Sai switches to the 'Hyderabad Innovation Hub' branch, the board and WebSocket room are re-scoped instantly. Bangalore's tasks are completely invisible.*
  >
  > *If an external user like John Doe from Acme Cloud attempts to access Julley's branch endpoints, our require_tenant_access middleware blocks the request with HTTP 403 Forbidden.*
  >
  > *We also have built-in Undo/Redo with Ctrl+Z shortcuts, a tenant-scoped Activity Audit stream, and an interactive ER diagram viewer right in the application."*

---

### [3:15 - 3:45] Automated Test Suite & Conclusion
- **Screen Action**:
  - Switch to Terminal.
  - Run: `python -m pytest -v`.
  - Show all 12 tests passing with green checkmarks.
- **Spoken Script**:
  > *"Finally, let's run our automated test suite using pytest.*
  >
  > *In under 1 second, all 12 integration tests pass: validating tenant data isolation, cross-organization protection, RBAC boundaries, OCC 409 conflict detection, fractional indexing math, and WebSocket authorization.*
  >
  > *The project is pushed to GitHub at Godasisai/realtime-kanban, a clean submission ZIP has been packaged, and the application is live. Thank you for your time and consideration!"*

---

## 📊 Part 2: Slide-by-Slide PowerPoint Deck Overview

The PowerPoint file has been generated and saved at:  
👉 [`c:\Users\hp\Downloads\realtime-kanban\Julley_Kanban_Architecture_Presentation_Sai_Ammanna_Naidu.pptx`](file:///c:/Users/hp/Downloads/realtime-kanban/Julley_Kanban_Architecture_Presentation_Sai_Ammanna_Naidu.pptx)

### Slide 1: Title Slide
- **Title**: Real-Time Collaborative Kanban Board
- **Subtitle**: Multi-Organization & Multi-Tenant Enterprise Task Management Architecture
- **Company**: Julley Online Pvt. Ltd. &bull; Technical Assignment
- **Candidate**: Sai Ammanna Naidu (`naidugodasi751@gmail.com`)
- **Links**: GitHub: `https://github.com/Godasisai/realtime-kanban` | Live Demo: `https://julley-kanban.loca.lt`

### Slide 2: Problem Statement & Engineering Objectives
- **Hierarchy Requirements**: Support parent organizations with autonomous branches/tenants.
- **Tenant Isolation**: Guarantee zero cross-tenant data leakage across REST queries and WebSocket feeds.
- **RBAC**: Enforce distinct privileges for Org Admin, Tenant Admin, and Members.
- **Real-Time Sync**: Instant multi-user synchronization with presence tracking.
- **Concurrency & Drag-Drop**: Prevent update collisions and database row locks during reordering.

### Slide 3: System Architecture & Tenancy Hierarchy
- **5-Tier Hierarchy**: `Organization` &rarr; `Tenants` &rarr; `Boards` &rarr; `Columns` &rarr; `Tasks`.
- **Tenancy Model**: Shared Database with Tenant Discriminator foreign keys and composite indexing.
- **Dependency Guard**: `require_tenant_access` dependency intercepts every request, validates JWT against tenant memberships, and rejects unauthorized access with 403 Forbidden.

### Slide 4: Database Schema & ER Design
- **8 Core Tables**: `organizations`, `tenants`, `users`, `memberships`, `boards`, `columns`, `tasks`, `activity_logs`.
- **High Concurrency Optimization**: SQLite WAL (Write-Ahead Logging) mode enabled with PRAGMA foreign keys for concurrent reads and writes without database locks.
- **Audit Trail**: Every creation, move, edit, and deletion is recorded in tenant-partitioned `activity_logs`.

### Slide 5: Advanced Concurrency & Conflict Handling
- **Optimistic Concurrency Control (OCC)**: Atomic `version` tracking on tasks. Stale updates return HTTP 409 Conflict.
- **3-Way Conflict Resolution**: Side-by-side comparison modal with *Keep Server Version*, *Overwrite*, and *Merge* options.
- **Fractional Indexing (LexoRank)**: Midpoint floating-point ordering $\frac{\text{prev} + \text{next}}{2.0}$. $O(1)$ database updates without mass row locks.

### Slide 6: Scoped WebSockets & Live Presence
- **Room Quarantine**: Connections scoped to `tenant:{tenant_id}:board:{board_id}`.
- **Presence Avatars**: Live chip stack showing all collaborators viewing the board.
- **Active Task Focus**: Glowing card outlines and badges showing who is viewing which task.
- **Optimistic UI Updates**: Immediate card movement with automatic rollback on error.
- **Undo / Redo**: Client history stack with `Ctrl+Z` / `Ctrl+Y` shortcuts.

### Slide 7: Automated Test Suite & Verification
- **12/12 Pytest Tests Passing in < 1s**:
  - `test_tenant_data_isolation_read`: Cross-tenant board listing blocked (403).
  - `test_cross_tenant_task_access_prevention`: Cross-tenant task lookup blocked (404).
  - `test_cross_organization_leakage_prevention`: External org admin blocked from Julley data.
  - `test_member_cannot_delete_column`: Member RBAC boundary enforced.
  - `test_optimistic_concurrency_control_conflict`: Version mismatch triggers 409 Conflict.
  - `test_drag_drop_task_move_api`: Midpoint fractional ordering verified.
  - `test_websocket_auth_and_tenant_scoping`: Unauthorized WS connection rejected (1008).

### Slide 8: Submission Summary & Deliverables
- **GitHub Repository**: [https://github.com/Godasisai/realtime-kanban](https://github.com/Godasisai/realtime-kanban)
- **Live Published Link**: [https://julley-kanban.loca.lt](https://julley-kanban.loca.lt)
- **Clean Submission ZIP**: `Julley_RealTime_Kanban_Assignment_Sai_Ammanna_Naidu.zip`
- **100% Core & Advanced Requirements Satisfied**.
