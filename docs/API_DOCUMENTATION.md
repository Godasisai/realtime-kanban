# REST API Specification

Interactive Swagger UI documentation is available locally at:
👉 **`http://localhost:8000/docs`**  
ReDoc is available at:
👉 **`http://localhost:8000/redoc`**

---

## Base URL & Authentication
- **Base URL**: `/api`
- **Auth Scheme**: Bearer Token (JWT in `Authorization: Bearer <token>` header)

---

## Endpoints

### 1. Authentication (`/api/auth`)
| Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | Register a new user | Public |
| `POST` | `/auth/login` | Authenticate and obtain JWT token | Public |
| `GET` | `/auth/me` | Fetch current user with accessible orgs & branches | Authenticated |
| `GET` | `/auth/demo-users` | Fetch seeded demo personas for rapid evaluation | Public |

### 2. Organizations (`/api/organizations`)
| Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/organizations` | List organizations the user belongs to | Member |
| `POST` | `/organizations` | Create a new organization (caller becomes Org Admin) | Authenticated |
| `GET` | `/organizations/{org_id}` | Get organization details | Org Admin |
| `GET` | `/organizations/{org_id}/tenants` | List all branches under this organization | Org Admin |
| `POST` | `/organizations/{org_id}/tenants` | Create a new branch/tenant | Org Admin |

### 3. Tenants & Branches (`/api/tenants/{tenant_id}`)
| Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/tenants/{tenant_id}` | Fetch branch details | Member |
| `GET` | `/tenants/{tenant_id}/members` | List members of this branch | Member |
| `POST` | `/tenants/{tenant_id}/members` | Add member to branch with role | Tenant Admin |
| `GET` | `/tenants/{tenant_id}/boards` | List boards in this branch | Member |
| `POST` | `/tenants/{tenant_id}/boards` | Create a board in this branch | Tenant Admin |

### 4. Boards (`/api/tenants/{tenant_id}/boards/{board_id}`)
| Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/tenants/{tenant_id}/boards/{board_id}` | Fetch full board with columns and tasks | Member |
| `PUT` | `/tenants/{tenant_id}/boards/{board_id}` | Update board title, description, or color | Tenant Admin |
| `DELETE` | `/tenants/{tenant_id}/boards/{board_id}` | Delete board and cascade tasks | Tenant Admin |

### 5. Columns (`/api/tenants/{tenant_id}/boards/{board_id}/columns`)
| Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- |
| `POST` | `.../columns` | Add column with fractional order & WIP limit | Tenant Admin |
| `PUT` | `.../columns/{col_id}` | Update column title or WIP limit | Tenant Admin |
| `POST` | `.../columns/{col_id}/move` | Reorder column with fractional indexing | Tenant Admin |
| `DELETE` | `.../columns/{col_id}` | Delete column and cascade tasks | Tenant Admin |

### 6. Tasks (`/api/tenants/{tenant_id}/boards/{board_id}/tasks`)
| Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- |
| `POST` | `.../tasks` | Create task with fractional order | Member |
| `GET` | `.../tasks/{task_id}` | Fetch single task | Member |
| `PUT` | `.../tasks/{task_id}` | Update task with OCC (`expected_version`). Returns 409 on conflict! | Member |
| `POST` | `.../tasks/{task_id}/move` | Drag-and-drop task move across or within columns | Member |
| `DELETE` | `.../tasks/{task_id}` | Delete task | Member |

#### Task Update Payload with OCC:
```json
{
  "expected_version": 2,
  "title": "Updated Task Title",
  "description": "Refined requirements...",
  "priority": "urgent",
  "assignee_id": "usr-123",
  "tags": ["Security", "Backend"]
}
```

#### Conflict Response (`HTTP 409 Conflict`):
```json
{
  "detail": {
    "message": "Conflict detected: The task was updated by another collaborator while you were editing.",
    "client_version": 2,
    "server_version": 3,
    "server_task": {
      "id": "tsk-abc",
      "version": 3,
      "title": "Concurrent edit by peer",
      "priority": "high"
    }
  }
}
```

### 7. Activity Audit Logs (`/api/tenants/{tenant_id}/activities`)
| Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/tenants/{tenant_id}/activities` | List audit activity feed scoped strictly to tenant | Member |
