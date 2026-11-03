# Slide-by-Slide PowerPoint Presentation Script
### Real-Time Collaborative Kanban Board (Multi-Organization + Multi-Tenant)
**Company**: Julley Online Pvt. Ltd. &bull; Technical Assignment Presentation  
**Presenter / Candidate**: Sai Ammanna Naidu  
**Contact**: naidugodasi751@gmail.com  
**Matching PPT Deck**: [`Julley_Kanban_Architecture_Presentation_Sai_Ammanna_Naidu.pptx`](file:///c:/Users/hp/Downloads/realtime-kanban/Julley_Kanban_Architecture_Presentation_Sai_Ammanna_Naidu.pptx)  
**Total Estimated Time**: 4 to 5 Minutes

---

## 🎙️ Slide 1: Title Slide
**Slide Visual**: Dark theme title slide showing *"Real-Time Collaborative Kanban Board - Multi-Organization & Multi-Tenant Enterprise Architecture"*, candidate details, and links.

### Spoken Script:
> *"Good morning / afternoon everyone. My name is Sai Ammanna Naidu, and today I am excited to present my architecture and technical implementation for the Real-Time Collaborative Kanban Board assignment for Julley Online Pvt. Ltd.*
>
> *The goal of this project was to design and build an enterprise-grade collaborative task board capable of handling complex multi-organization and multi-branch tenant hierarchies, strict data isolation, real-time synchronization over WebSockets, and zero-conflict concurrency control.*
>
> *Over the next few minutes, I will walk you through the architectural decisions, database modeling, concurrency strategies, and testing that make this platform robust and production-ready."*

---

## 🎙️ Slide 2: Problem Statement & Core Engineering Objectives
**Slide Visual**: Two comparison cards: "Core Business & Technical Challenges" vs "Production Solution Delivered".

### Spoken Script:
> *"Moving to Slide 2, let's examine the core problem statement.*
>
> *In enterprise environments, modern task management platforms face five fundamental architectural challenges:*
> 1. *First, modeling a true multi-tier hierarchy where holding companies have distinct branches or tenants.*
> 2. *Second, enforcing strict data isolation so that users in one branch or company can never read or tamper with another branch's tasks.*
> 3. *Third, implementing granular Role-Based Access Control across Org Admins, Tenant Admins, and Members.*
> 4. *Fourth, providing instantaneous live synchronization without polling.*
> 5. *And fifth, solving concurrent edit collisions and drag-and-drop race conditions.*
>
> *To solve these, I engineered a full-stack platform using FastAPI with asynchronous WebSockets, SQLite in high-concurrency WAL mode, and a responsive frontend with native HTML5 drag-and-drop. Crucially, I introduced Optimistic Concurrency Control with a 3-way conflict resolution modal, and Fractional Indexing for O(1) card positioning."*

---

## 🎙️ Slide 3: System Architecture: Multi-Organization Hierarchy & RBAC
**Slide Visual**: 3-column breakdown: Hierarchy Structure, Tenancy Isolation Model, and RBAC Matrix.

### Spoken Script:
> *"On Slide 3, we see the architectural hierarchy and security model.*
>
> *The hierarchy flows from Organization down to Tenants—which represent branches or divisions—then to Boards, Columns, and Tasks.*
>
> *When deciding on the tenancy model, we evaluated Database-per-tenant, Schema-per-tenant, and Shared-Database with a Tenant Discriminator. We selected the Shared-Database with Tenant Discriminator model because it provides optimal connection pooling, seamless schema migrations, and high performance, while achieving ironclad security through our application middleware.*
>
> *Security is enforced at two layers:*
> *First, every API endpoint is guarded by a dependency called `require_tenant_access`. This verifies that the authenticated user possesses valid membership in that tenant or holds an Org Admin role. Unauthorized requests immediately fail with HTTP 403 Forbidden.*
> *Second, all SQL queries perform dual-key filtering using both the entity ID and `tenant_id`. Even if an attacker guesses a task UUID from another branch, the database returns a 404 Not Found.*
>
> *Our RBAC matrix guarantees that only Org Admins can provision branches, Tenant Admins manage board columns and WIP limits, and Members focus on executing and moving tasks."*

---

## 🎙️ Slide 4: Database Schema & Entity-Relationship Design
**Slide Visual**: ER breakdown of the 8 tables and High-Performance Database Strategies (WAL mode, Foreign Keys, Indexing).

### Spoken Script:
> *"Turning to Slide 4, here is our database architecture consisting of 8 relational tables.*
>
> *The tables include `organizations`, `tenants`, `users`, `memberships`, `boards`, `columns`, `tasks`, and `activity_logs`.*
>
> *To achieve high concurrency and data integrity on SQLite, I implemented two critical engine-level configurations:*
> *1. We enable Write-Ahead Logging (WAL Mode) via SQLite PRAGMAs, allowing concurrent readers to read without blocking writers, and writers to commit without blocking readers.*
> *2. We enforce `PRAGMA foreign_keys = ON`, guaranteeing cascade deletions across tenant hierarchies.*
>
> *In addition, composite indexes are placed on `(user_id, tenant_id)` and `(tenant_id, column_id)`. Every operational change is recorded in an immutable, tenant-partitioned `activity_logs` table for compliance and real-time audit feeds."*

---

## 🎙️ Slide 5: Advanced Concurrency: OCC & Fractional Indexing (LexoRank)
**Slide Visual**: Side-by-side cards: Optimistic Concurrency Control (OCC) vs Fractional Indexing (LexoRank).

### Spoken Script:
> *"Slide 5 addresses one of the most critical aspects of the evaluation: Advanced Concurrency Handling.*
>
> *First, for concurrent task edits, we implement Optimistic Concurrency Control. Rather than acquiring pessimistic database locks which stall other users, each task maintains an atomic `version` integer. When a client submits an update, it sends the `expected_version` it currently holds.*
> *If two users edit simultaneously, the first write succeeds and increments the version. The second user's request triggers an HTTP 409 Conflict. Our frontend intercepts this and displays an interactive Side-by-Side Conflict Resolution Modal, allowing the user to Keep the Server Version, Overwrite with their changes, or Merge non-conflicting fields.*
>
> *Second, for drag-and-drop reordering, traditional integer indexing is flawed—inserting an item at the top of a 50-task column requires 50 SQL UPDATE statements. Instead, we use Fractional Indexing, inspired by Jira's LexoRank.*
> *The new position is computed as the midpoint: `(prev_order + next_order) / 2.0`. This requires exactly ONE database update—an O(1) write operation—completely eliminating mass row locking and drag-and-drop race conditions. An automatic rebalancing threshold ensures precision is maintained over time."*

---

## 🎙️ Slide 6: Scoped WebSockets Architecture & Live Presence
**Slide Visual**: WebSocket Room Quarantine details and Live Presence & Collaboration features.

### Spoken Script:
> *"On Slide 6, we explore the Real-Time WebSocket layer.*
>
> *To prevent cross-tenant message leakage, WebSockets are quarantined into rooms scoped strictly by `tenant:{tenant_id}:board:{board_id}`. During the handshake, the server verifies the JWT token and checks the user's branch membership. Unauthorized sockets are rejected immediately with code 1008.*
>
> *Collaborative features include:*
> *1. Live Presence Avatar Stack: Users can see exactly who is online in their branch.*
> *2. Active Task Focus: When a collaborator opens a task drawer, other users see a glowing red border and an avatar badge indicating who is viewing that card.*
> *3. Optimistic UI Updates: Dragged cards move instantly, with automatic rollback if an error occurs.*
> *4. Client-side Undo/Redo: Users can undo and redo task moves and edits using Ctrl+Z and Ctrl+Y shortcuts.*
> *5. Network Recovery: The client features automatic exponential-backoff reconnects and fetches a fresh board snapshot upon reconnection."*

---

## 🎙️ Slide 7: Rigorous Testing & Automated Verification
**Slide Visual**: Test results summary card showing 12/12 passing pytest integration tests and seeded demo personas.

### Spoken Script:
> *"Slide 7 showcases our testing and verification results.*
>
> *We have 12 comprehensive integration tests written in pytest that execute in under one second. These tests systematically verify:*
> *- Strict tenant data isolation: A member from Bangalore HQ attempting to query Hyderabad Hub receives a 403 Forbidden.*
> *- Cross-tenant task access prevention: Guessing a task UUID belonging to another tenant returns a 404.*
> *- Cross-organization protection: External organizations like Acme Cloud are blocked from Julley Online data.*
> *- RBAC privilege boundaries: Regular members attempting to delete columns or create branches receive a 403 Forbidden.*
> *- Concurrency validation: Concurrent edits with stale versions reliably trigger HTTP 409 Conflict.*
> *- Fractional ordering mathematics and WebSocket authentication.*
>
> *We have also pre-seeded realistic personas for instant evaluation: Sai as Org Admin, Priya and Ananya as Tenant Admins, Rahul as a Member, and John as an isolated external user."*

---

## 🎙️ Slide 8: Assignment Deliverables & Conclusion
**Slide Visual**: Checklist of all deliverables submitted for Julley Online Pvt. Ltd.

### Spoken Script:
> *"Finally, on Slide 8, here is a summary of the complete deliverables submitted:*
>
> *1. The project is deployed and live at `https://julley-kanban.loca.lt` with interactive Swagger API docs.*
> *2. The source code is pushed to GitHub at `https://github.com/Godasisai/realtime-kanban`.*
> *3. A clean ZIP archive has been generated and prepared for Google Drive upload.*
> *4. Exhaustive technical documentation has been authored covering Architecture, Database ER diagrams, REST APIs, and WebSocket protocols.*
> *5. All core and advanced criteria—from multi-tenant modeling to OCC conflict resolution and live drag-and-drop—are 100% satisfied.*
>
> *Thank you very much for your time and consideration. I would be delighted to answer any technical questions."*
