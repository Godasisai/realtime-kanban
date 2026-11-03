# Scoped WebSocket Protocol & Real-Time Collaboration

## 1. Connection Handshake & Authentication

```
Client  --------------------------------------------------->  Server
        CONNECT /ws?token={JWT}&tenant_id={ID}&board_id={ID}
        
Server  <---------------------------------------------------  Server
        1. Decodes JWT & verifies signature
        2. Queries database for membership in tenant_id
        3. Rejects with 1008 Policy Violation if unauthorized
        4. Accepts socket into room "tenant:{tenant_id}:board:{board_id}"
        5. Dispatches USER_JOINED & sends PRESENCE_SYNC
```

---

## 2. Real-Time Broadcast Events (Server &rarr; Client)

### `TASK_CREATED`
Dispatched when any member creates a task on the board.
```json
{
  "type": "TASK_CREATED",
  "payload": {
    "id": "tsk-uuid",
    "tenant_id": "ten-uuid",
    "board_id": "brd-uuid",
    "column_id": "col-uuid",
    "title": "Enforce Strict Tenant Isolation",
    "priority": "urgent",
    "order": 1000.0,
    "version": 1,
    "assignee": { "id": "usr-1", "name": "Rahul Varma" }
  },
  "user": { "id": "usr-1", "name": "Rahul Varma" }
}
```

### `TASK_MOVED` (Drag-and-Drop)
Dispatched when a task is reordered within a column or moved between columns using Fractional Indexing.
```json
{
  "type": "TASK_MOVED",
  "payload": {
    "task_id": "tsk-uuid",
    "source_column_id": "col-todo",
    "target_column_id": "col-progress",
    "order": 1500.0,
    "version": 3,
    "task": { ... }
  },
  "user": { "id": "usr-2", "name": "Priya Sharma" }
}
```

### `TASK_UPDATED`
Dispatched upon successful task update with incremented OCC version.
```json
{
  "type": "TASK_UPDATED",
  "payload": {
    "id": "tsk-uuid",
    "title": "Updated Title",
    "version": 4,
    "priority": "high"
  },
  "user": { "id": "usr-3", "name": "Sai Ammanna Naidu" }
}
```

### `TASK_DELETED`
```json
{
  "type": "TASK_DELETED",
  "payload": {
    "task_id": "tsk-uuid",
    "column_id": "col-uuid"
  },
  "user": { "id": "usr-3", "name": "Sai Ammanna Naidu" }
}
```

---

## 3. Presence & Focus Tracking

### `PRESENCE_SYNC` / `USER_JOINED` / `USER_LEFT`
Maintains live active collaborator list for the board.
```json
{
  "type": "PRESENCE_SYNC",
  "payload": {
    "presence": [
      {
        "id": "usr-1",
        "name": "Sai Ammanna Naidu",
        "email": "sai@julley.com",
        "avatar_color": "#6366f1",
        "focused_task_id": "tsk-100"
      },
      {
        "id": "usr-2",
        "name": "Priya Sharma",
        "email": "priya@julley.com",
        "avatar_color": "#ec4899",
        "focused_task_id": null
      }
    ]
  }
}
```

### `USER_FOCUS_TASK` & `USER_BLUR_TASK`
Client sends `FOCUS_TASK` when opening a task drawer.
The server broadcasts to peers so they see a live visual indicator on that card:
```json
{
  "type": "USER_FOCUS_TASK",
  "payload": {
    "user_id": "usr-1",
    "user_name": "Sai Ammanna Naidu",
    "task_id": "tsk-100"
  }
}
```
Client sends `BLUR_TASK` when drawer is closed.

---

## 4. Heartbeat & Liveness
- Client sends `{"type": "PING"}` every 25 seconds.
- Server replies `{"type": "PONG"}`.
- If socket disconnects, the client engages exponential backoff and triggers a board snapshot refresh upon reconnection.
