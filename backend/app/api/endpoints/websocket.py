"""
WebSocket Endpoint for Real-time Status Updates

Provides WebSocket connections for:
- Session status updates
- Agent progress events
- Tool execution events
- Error notifications
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional
import asyncio
import json
import structlog

from app.core.execution_tracker import (
    get_execution_tracker,
    ExecutionTracker,
    EventType,
    ExecutionPhase
)

logger = structlog.get_logger(__name__)

router = APIRouter()


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.

    Features:
    - Multiple connections per session
    - Broadcast to all connections for a session
    - Connection cleanup on disconnect
    """

    def __init__(self):
        # Map session_id -> list of WebSocket connections
        self._connections: dict[str, list[WebSocket]] = {}
        # Map WebSocket -> session_id (for reverse lookup)
        self._websocket_sessions: dict[WebSocket, str] = {}
        # Global connections (receive all events)
        self._global_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket, session_id: Optional[str] = None) -> None:
        """
        Accept a WebSocket connection.

        Args:
            websocket: The WebSocket connection
            session_id: Optional session to subscribe to (None for global)
        """
        await websocket.accept()

        if session_id:
            if session_id not in self._connections:
                self._connections[session_id] = []
            self._connections[session_id].append(websocket)
            self._websocket_sessions[websocket] = session_id
            logger.info(
                "WebSocket connected to session",
                session_id=session_id,
                connection_count=len(self._connections[session_id])
            )
        else:
            self._global_connections.append(websocket)
            logger.info(
                "Global WebSocket connected",
                connection_count=len(self._global_connections)
            )

    def disconnect(self, websocket: WebSocket) -> None:
        """
        Handle WebSocket disconnection.

        Args:
            websocket: The disconnected WebSocket
        """
        # Check session connections
        session_id = self._websocket_sessions.pop(websocket, None)
        if session_id and session_id in self._connections:
            if websocket in self._connections[session_id]:
                self._connections[session_id].remove(websocket)
            if not self._connections[session_id]:
                del self._connections[session_id]
            logger.info("WebSocket disconnected from session", session_id=session_id)

        # Check global connections
        if websocket in self._global_connections:
            self._global_connections.remove(websocket)
            logger.info("Global WebSocket disconnected")

    async def send_to_session(self, session_id: str, message: dict) -> None:
        """
        Send a message to all connections for a session.

        Args:
            session_id: The session to send to
            message: The message to send
        """
        connections = self._connections.get(session_id, [])
        disconnected = []

        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning("Failed to send to WebSocket", error=str(e))
                disconnected.append(websocket)

        # Clean up disconnected sockets
        for ws in disconnected:
            self.disconnect(ws)

        # Also send to global connections
        await self._send_to_global(message)

    async def _send_to_global(self, message: dict) -> None:
        """Send a message to all global connections."""
        disconnected = []

        for websocket in self._global_connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning("Failed to send to global WebSocket", error=str(e))
                disconnected.append(websocket)

        for ws in disconnected:
            self.disconnect(ws)

    async def broadcast(self, message: dict) -> None:
        """
        Broadcast a message to all connected WebSockets.

        Args:
            message: The message to broadcast
        """
        # Send to all session connections
        for session_id in list(self._connections.keys()):
            await self.send_to_session(session_id, message)

        # Send to global connections (already handled in send_to_session,
        # but call directly for messages not tied to a session)
        await self._send_to_global(message)

    def get_connection_count(self, session_id: Optional[str] = None) -> int:
        """Get the number of connections."""
        if session_id:
            return len(self._connections.get(session_id, []))
        return sum(len(c) for c in self._connections.values()) + len(self._global_connections)


# Global connection manager instance
manager = ConnectionManager()


async def handle_tracker_event(session_id: str, event_type: EventType, event_data: dict) -> None:
    """
    Handle events from ExecutionTracker and forward to WebSocket clients.

    This is registered as an async event handler with the ExecutionTracker.
    """
    await manager.send_to_session(session_id, event_data)


# Register the handler with the tracker on module import
def setup_websocket_handler():
    """Register WebSocket handler with ExecutionTracker."""
    tracker = get_execution_tracker()
    tracker.register_async_event_handler(handle_tracker_event)
    logger.info("WebSocket handler registered with ExecutionTracker")


@router.websocket("/ws")
async def websocket_global_endpoint(websocket: WebSocket):
    """
    Global WebSocket endpoint for all session events.

    Receives events from all sessions. Useful for admin dashboards.
    """
    await manager.connect(websocket)

    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()

            try:
                message = json.loads(data)

                # Handle subscription requests
                if message.get("type") == "subscribe":
                    session_id = message.get("session_id")
                    if session_id:
                        # Move from global to session-specific
                        manager.disconnect(websocket)
                        await manager.connect(websocket, session_id)
                        await websocket.send_json({
                            "type": "subscribed",
                            "session_id": session_id
                        })

                # Handle ping/pong for keepalive
                elif message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

                # Handle status request
                elif message.get("type") == "get_status":
                    session_id = message.get("session_id")
                    if session_id:
                        tracker = get_execution_tracker()
                        status = tracker.get_status(session_id)
                        if status:
                            await websocket.send_json({
                                "type": "status",
                                "session_id": session_id,
                                "status": status.to_dict()
                            })
                        else:
                            await websocket.send_json({
                                "type": "error",
                                "message": f"Session {session_id} not found"
                            })

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")


@router.websocket("/ws/{session_id}")
async def websocket_session_endpoint(websocket: WebSocket, session_id: str):
    """
    Session-specific WebSocket endpoint.

    Receives events only for the specified session.

    Args:
        session_id: The session to subscribe to
    """
    try:
        await manager.connect(websocket, session_id)
    except Exception as e:
        logger.error("Failed to accept WebSocket connection", error=str(e), session_id=session_id)
        return

    # Send current status immediately (with error handling)
    try:
        tracker = get_execution_tracker()
        status = tracker.get_status(session_id)
        if status:
            await websocket.send_json({
                "type": "status",
                "session_id": session_id,
                "status": status.to_dict()
            })
        else:
            await websocket.send_json({
                "type": "info",
                "session_id": session_id,
                "message": f"Waiting for session {session_id} to start"
            })
    except Exception as e:
        logger.error("Failed to send initial status", error=str(e), session_id=session_id)
        manager.disconnect(websocket)
        return

    try:
        while True:
            try:
                # Use wait_for with timeout to allow periodic keep-alive checks
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0  # 30 second timeout
                )
            except asyncio.TimeoutError:
                # Send a ping to keep connection alive
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    # Connection likely closed
                    break
                continue

            try:
                message = json.loads(data)

                # Handle ping/pong
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

                elif message.get("type") == "pong":
                    # Client responded to our ping, connection is alive
                    pass

                # Handle status request
                elif message.get("type") == "get_status":
                    status = tracker.get_status(session_id)
                    if status:
                        await websocket.send_json({
                            "type": "status",
                            "session_id": session_id,
                            "status": status.to_dict()
                        })

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected", session_id=session_id)
    except Exception as e:
        logger.error("WebSocket error", error=str(e), session_id=session_id)
    finally:
        manager.disconnect(websocket)


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager."""
    return manager
