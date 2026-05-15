"""Real-time Collaboration — WebSocket-based live updates.

Provides WebSocket connections for:
- Live presence (who is on which page)
- Real-time notifications
- Agent Mode progress streaming
- Collaborative editing signals
"""

import json
import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel

router = APIRouter(tags=["realtime"])


class ConnectionManager:
    """Manages active WebSocket connections and room-based messaging."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}  # room -> connections
        self.user_info: dict[int, dict] = {}  # ws_id -> {user, page, room}
        self._counter = 0

    async def connect(self, websocket: WebSocket, room: str, user: str = "anonymous") -> int:
        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = []
        self.active_connections[room].append(websocket)
        self._counter += 1
        ws_id = self._counter
        self.user_info[ws_id] = {
            "user": user,
            "room": room,
            "page": "",
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }
        return ws_id

    def disconnect(self, websocket: WebSocket, room: str, ws_id: int):
        if room in self.active_connections:
            try:
                self.active_connections[room].remove(websocket)
            except ValueError:
                pass
            if not self.active_connections[room]:
                del self.active_connections[room]
        self.user_info.pop(ws_id, None)

    async def broadcast(self, room: str, message: dict):
        """Send a message to all connections in a room."""
        if room not in self.active_connections:
            return
        dead = []
        for ws in self.active_connections[room]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            try:
                self.active_connections[room].remove(ws)
            except ValueError:
                pass

    async def send_to(self, websocket: WebSocket, message: dict):
        """Send a message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception:
            pass

    def get_presence(self, room: str) -> list[dict]:
        """Get current presence info for a room."""
        count = len(self.active_connections.get(room, []))
        users = [
            info for info in self.user_info.values()
            if info["room"] == room
        ]
        return users

    def get_all_rooms(self) -> dict:
        return {
            room: len(conns) for room, conns in self.active_connections.items()
        }


manager = ConnectionManager()


@router.websocket("/ws/{room}")
async def websocket_endpoint(
    websocket: WebSocket,
    room: str,
    user: str = Query(default="anonymous"),
):
    """WebSocket endpoint for real-time collaboration.

    Message types:
    - presence: user joined/left
    - page_change: user navigated to a page
    - notification: system notification
    - agent_progress: agent mode step completed
    - cursor: cursor position update
    - edit_signal: file being edited notification
    """
    ws_id = await manager.connect(websocket, room, user)

    # Announce join
    await manager.broadcast(room, {
        "type": "presence",
        "action": "joined",
        "user": user,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_users": len(manager.active_connections.get(room, [])),
    })

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "page_change":
                if ws_id in manager.user_info:
                    manager.user_info[ws_id]["page"] = data.get("page", "")
                await manager.broadcast(room, {
                    "type": "page_change",
                    "user": user,
                    "page": data.get("page", ""),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            elif msg_type == "cursor":
                await manager.broadcast(room, {
                    "type": "cursor",
                    "user": user,
                    "file": data.get("file", ""),
                    "line": data.get("line", 0),
                    "column": data.get("column", 0),
                })

            elif msg_type == "edit_signal":
                await manager.broadcast(room, {
                    "type": "edit_signal",
                    "user": user,
                    "file": data.get("file", ""),
                    "action": data.get("action", "editing"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            elif msg_type == "notification":
                await manager.broadcast(room, {
                    "type": "notification",
                    "user": user,
                    "message": data.get("message", ""),
                    "level": data.get("level", "info"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            elif msg_type == "ping":
                await manager.send_to(websocket, {"type": "pong"})

            else:
                # Forward any other message type to the room
                data["user"] = user
                data["timestamp"] = datetime.now(timezone.utc).isoformat()
                await manager.broadcast(room, data)

    except WebSocketDisconnect:
        manager.disconnect(websocket, room, ws_id)
        await manager.broadcast(room, {
            "type": "presence",
            "action": "left",
            "user": user,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_users": len(manager.active_connections.get(room, [])),
        })
    except Exception:
        manager.disconnect(websocket, room, ws_id)


@router.get("/api/realtime/presence/{room}")
def get_room_presence(room: str):
    """Get current presence information for a room."""
    users = manager.get_presence(room)
    return {
        "room": room,
        "active_users": len(users),
        "users": users,
    }


@router.get("/api/realtime/rooms")
def get_all_rooms():
    """Get all active rooms with connection counts."""
    return manager.get_all_rooms()
