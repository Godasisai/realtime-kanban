import json
import logging
from typing import Dict, Set, Optional, Any
from fastapi import WebSocket

logger = logging.getLogger("kanban.websocket")


class ConnectionManager:
    """
    Manages WebSocket connections strictly scoped by Tenant and Board.
    Guarantees cross-tenant channel isolation:
    - A connection in Tenant A will NEVER receive events from Tenant B.
    - Tracks live presence (online users and focused tasks) per tenant/board.
    """

    def __init__(self):
        # Maps room_key -> Set[WebSocket]
        # room_key format: "tenant:{tenant_id}:board:{board_id}"
        self.rooms: Dict[str, Set[WebSocket]] = {}

        # Maps WebSocket -> socket metadata (tenant_id, board_id, user dict)
        self.socket_meta: Dict[WebSocket, Dict[str, Any]] = {}

        # Active presence: tenant_id -> board_id -> { user_id: { user_info, focused_task_id, socket_count } }
        self.presence: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def _get_room_key(self, tenant_id: str, board_id: str) -> str:
        return f"tenant:{tenant_id}:board:{board_id}"

    async def connect(
        self,
        websocket: WebSocket,
        tenant_id: str,
        board_id: str,
        user: Dict[str, Any],
    ) -> None:
        await websocket.accept()

        room_key = self._get_room_key(tenant_id, board_id)
        if room_key not in self.rooms:
            self.rooms[room_key] = set()
        self.rooms[room_key].add(websocket)

        self.socket_meta[websocket] = {
            "tenant_id": tenant_id,
            "board_id": board_id,
            "user": user,
            "focused_task_id": None,
        }

        # Update presence
        if tenant_id not in self.presence:
            self.presence[tenant_id] = {}
        if board_id not in self.presence[tenant_id]:
            self.presence[tenant_id][board_id] = {}

        user_id = user["id"]
        if user_id in self.presence[tenant_id][board_id]:
            self.presence[tenant_id][board_id][user_id]["socket_count"] += 1
        else:
            self.presence[tenant_id][board_id][user_id] = {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "avatar_color": user.get("avatar_color", "#3b82f6"),
                "focused_task_id": None,
                "socket_count": 1,
            }

        # Notify room of user joined
        await self.broadcast_to_room(
            tenant_id=tenant_id,
            board_id=board_id,
            event={
                "type": "USER_JOINED",
                "payload": {
                    "user": user,
                    "presence": list(self.presence[tenant_id][board_id].values()),
                },
            },
        )

        # Send initial full presence sync to the newly connected user
        await websocket.send_text(json.dumps({
            "type": "PRESENCE_SYNC",
            "payload": {
                "presence": list(self.presence[tenant_id][board_id].values()),
            },
        }))

    async def disconnect(self, websocket: WebSocket) -> None:
        meta = self.socket_meta.pop(websocket, None)
        if not meta:
            return

        tenant_id = meta["tenant_id"]
        board_id = meta["board_id"]
        user = meta["user"]
        user_id = user["id"]
        room_key = self._get_room_key(tenant_id, board_id)

        if room_key in self.rooms:
            self.rooms[room_key].discard(websocket)
            if not self.rooms[room_key]:
                del self.rooms[room_key]

        # Update presence
        if tenant_id in self.presence and board_id in self.presence[tenant_id]:
            if user_id in self.presence[tenant_id][board_id]:
                self.presence[tenant_id][board_id][user_id]["socket_count"] -= 1
                if self.presence[tenant_id][board_id][user_id]["socket_count"] <= 0:
                    del self.presence[tenant_id][board_id][user_id]

            # Broadcast user left
            await self.broadcast_to_room(
                tenant_id=tenant_id,
                board_id=board_id,
                event={
                    "type": "USER_LEFT",
                    "payload": {
                        "user_id": user_id,
                        "presence": list(self.presence[tenant_id][board_id].values()),
                    },
                },
            )

    async def handle_client_message(self, websocket: WebSocket, data: str) -> None:
        """Processes client-to-server WS actions like task focusing."""
        try:
            message = json.loads(data)
            msg_type = message.get("type")
            meta = self.socket_meta.get(websocket)
            if not meta:
                return

            tenant_id = meta["tenant_id"]
            board_id = meta["board_id"]
            user = meta["user"]
            user_id = user["id"]

            if msg_type == "FOCUS_TASK":
                task_id = message.get("task_id")
                meta["focused_task_id"] = task_id
                if tenant_id in self.presence and board_id in self.presence[tenant_id]:
                    if user_id in self.presence[tenant_id][board_id]:
                        self.presence[tenant_id][board_id][user_id]["focused_task_id"] = task_id

                await self.broadcast_to_room(
                    tenant_id=tenant_id,
                    board_id=board_id,
                    event={
                        "type": "USER_FOCUS_TASK",
                        "payload": {
                            "user_id": user_id,
                            "user_name": user["name"],
                            "task_id": task_id,
                        },
                    },
                    exclude_socket=websocket,
                )

            elif msg_type == "BLUR_TASK":
                meta["focused_task_id"] = None
                if tenant_id in self.presence and board_id in self.presence[tenant_id]:
                    if user_id in self.presence[tenant_id][board_id]:
                        self.presence[tenant_id][board_id][user_id]["focused_task_id"] = None

                await self.broadcast_to_room(
                    tenant_id=tenant_id,
                    board_id=board_id,
                    event={
                        "type": "USER_BLUR_TASK",
                        "payload": {
                            "user_id": user_id,
                        },
                    },
                    exclude_socket=websocket,
                )

            elif msg_type == "PING":
                await websocket.send_text(json.dumps({"type": "PONG"}))

        except Exception as e:
            logger.error(f"Error handling client WS message: {e}")

    async def broadcast_to_room(
        self,
        tenant_id: str,
        board_id: str,
        event: Dict[str, Any],
        exclude_socket: Optional[WebSocket] = None,
    ) -> None:
        """
        Broadcasts an event strictly to sockets within tenant_id and board_id.
        No other tenant will ever receive this event.
        """
        room_key = self._get_room_key(tenant_id, board_id)
        subscribers = self.rooms.get(room_key, set())
        if not subscribers:
            return

        dead_sockets = set()
        message_str = json.dumps(event)

        for ws in subscribers:
            if ws == exclude_socket:
                continue
            try:
                await ws.send_text(message_str)
            except Exception:
                dead_sockets.add(ws)

        for dead_ws in dead_sockets:
            await self.disconnect(dead_ws)


ws_manager = ConnectionManager()
