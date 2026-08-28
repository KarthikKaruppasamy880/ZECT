"""Real governed PTY endpoints (V2 closure §10) — admin-only, workspace-
jailed pseudo-terminal sessions for the human Developer terminal.

Creation/listing/close are plain REST (same admin gate + audit trail as
App Runner's execute/start). I/O is a WebSocket: JSON control frames in
(input/resize/interrupt), raw bytes out, plus a final JSON "exited" frame.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.domains.workspace.pty_session import PtySession, get_pty_manager
from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.auth.rbac import log_audit, require_role
from app.infrastructure.database import SessionLocal, get_db

router = APIRouter(prefix="/api/workspace/pty", tags=["workspace-pty"])


class CreateSessionRequest(BaseModel):
    workspace_root: str
    cwd: Optional[str] = None
    label: str = ""
    rows: int = 24
    cols: int = 80


@router.post("/sessions")
@require_role("admin")
async def create_session(
    req: CreateSessionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.security.emergency_stop import require_not_emergency_stopped

    require_not_emergency_stopped(db)
    try:
        session = get_pty_manager().create(
            req.workspace_root,
            cwd=req.cwd,
            label=req.label,
            rows=req.rows,
            cols=req.cols,
        )
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"pty_spawn_failed:{exc}") from exc

    log_audit(
        db=db,
        user_id=current_user.user_id,
        action="pty_session_create",
        resource_type="workspace_pty",
        details={"cwd": session.cwd, "label": session.label},
    )
    return {"id": session.id, "cwd": session.cwd, "label": session.label}


@router.get("/sessions")
async def list_sessions():
    return {"sessions": get_pty_manager().list()}


@router.delete("/sessions/{session_id}")
@require_role("admin")
async def close_session(
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    closed = get_pty_manager().close(session_id)
    if not closed:
        raise HTTPException(status_code=404, detail=f"unknown_session_id:{session_id}")
    log_audit(
        db=db,
        user_id=current_user.user_id,
        action="pty_session_close",
        resource_type="workspace_pty",
        details={"session_id": session_id},
    )
    return {"ok": True}


async def _pump_output(ws: WebSocket, session: PtySession) -> None:
    loop = asyncio.get_event_loop()
    while True:
        try:
            chunk = await loop.run_in_executor(None, session.read, 4096)
        except Exception:  # noqa: BLE001
            break
        if chunk:
            await ws.send_bytes(chunk.encode("utf-8", errors="replace"))
        if not session.isalive():
            break
    try:
        await ws.send_json({"type": "exited", "exit_code": session.exit_code()})
    except Exception:  # noqa: BLE001
        pass


async def _pump_input(ws: WebSocket, session: PtySession) -> None:
    while True:
        msg = await ws.receive_json()
        kind = msg.get("type")
        if kind == "input":
            session.write(str(msg.get("data") or ""))
        elif kind == "resize":
            rows = int(msg.get("rows") or 24)
            cols = int(msg.get("cols") or 80)
            session.resize(rows, cols)
        elif kind == "interrupt":
            session.interrupt()


@router.websocket("/sessions/{session_id}/stream")
async def stream_session(websocket: WebSocket, session_id: str, token: str = Query("")):
    from app.infrastructure.auth.session_store import get_token_row

    db = SessionLocal()
    try:
        row = get_token_row(db, token)
        if not row:
            await websocket.close(code=4401)
            return
        from app.models import User

        user = db.query(User).filter(User.id == row.user_id).first()
        role = user.role if user else "developer"
    finally:
        db.close()

    if role != "admin":
        await websocket.close(code=4403)
        return

    session = get_pty_manager().get(session_id)
    if session is None:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    output_task = asyncio.ensure_future(_pump_output(websocket, session))
    input_task = asyncio.ensure_future(_pump_input(websocket, session))
    try:
        await asyncio.wait({output_task, input_task}, return_when=asyncio.FIRST_COMPLETED)
    except WebSocketDisconnect:
        pass
    finally:
        output_task.cancel()
        input_task.cancel()
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass
