from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.config import PROJECT_NAME, VERSION, API_V1_PREFIX, CORS_ORIGINS, STATIC_DIR
from app.database import engine, Base, SessionLocal
from app.models import User, Membership, Tenant
from app.security import decode_access_token, ROLE_ORG_ADMIN
from app.websocket.manager import ws_manager
from app.seed import seed_database

# Routers
from app.api.auth import router as auth_router
from app.api.organizations import router as org_router
from app.api.tenants import router as tenant_router
from app.api.boards import router as board_router
from app.api.columns import router as column_router
from app.api.tasks import router as task_router
from app.api.activities import router as activity_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    # Seed database with realistic multi-organization & multi-tenant demo data
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=PROJECT_NAME,
    description="Production-grade Real-Time Collaborative Kanban Board with Multi-Organization and Multi-Tenant Hierarchy, Strict Tenant Data Isolation, Optimistic Concurrency Control, and Live WebSockets.",
    version=VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth_router, prefix=API_V1_PREFIX)
app.include_router(org_router, prefix=API_V1_PREFIX)
app.include_router(tenant_router, prefix=API_V1_PREFIX)
app.include_router(board_router, prefix=API_V1_PREFIX)
app.include_router(column_router, prefix=API_V1_PREFIX)
app.include_router(task_router, prefix=API_V1_PREFIX)
app.include_router(activity_router, prefix=API_V1_PREFIX)


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": VERSION}


# ==================== Real-Time WebSocket Endpoint ====================

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT Bearer token"),
    tenant_id: str = Query(..., description="Tenant ID to scope connection"),
    board_id: str = Query(..., description="Board ID to scope connection"),
):
    """
    Authenticated WebSocket connection endpoint.
    Strictly enforces tenant data isolation:
      1. Validates JWT signature and expiration.
      2. Validates user membership in tenant_id (or Org Admin role).
      3. Closes unauthorized connection immediately before joining room.
      4. Dispatches presence events and real-time updates within tenant/board scope only.
    """
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return

    user_id = payload.get("sub")
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
            return

        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Tenant not found")
            return

        # Check tenant access
        membership = (
            db.query(Membership)
            .filter(
                Membership.user_id == user.id,
                ((Membership.tenant_id == tenant_id) |
                 ((Membership.org_id == tenant.org_id) & (Membership.role == ROLE_ORG_ADMIN))),
            )
            .first()
        )

        if not membership:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Access to tenant denied")
            return

        user_info = {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "avatar_color": user.avatar_color,
            "role": membership.role,
        }
    finally:
        db.close()

    # Connect to scoped channel
    await ws_manager.connect(
        websocket=websocket,
        tenant_id=tenant_id,
        board_id=board_id,
        user=user_info,
    )

    try:
        while True:
            data = await websocket.receive_text()
            await ws_manager.handle_client_message(websocket, data)
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception:
        await ws_manager.disconnect(websocket)


# Mount Static Files & SPA Route
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Kanban API is running. Build frontend static files."}
