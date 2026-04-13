"""
WebSocket Connection Manager
==============================

WHAT: Manages WebSocket connections and broadcasts device state changes in real-time.
WHY:  Without WebSocket, the frontend would need to constantly poll the API ("Are there 
      updates? Are there updates?"). WebSocket lets the server PUSH updates instantly.
HOW:  Maintains a set of active connections. When a device state changes, broadcasts
      the update to ALL connected clients simultaneously.

WHEN to use: Real-time dashboards, live notifications, collaborative features.
WHEN NOT to use: Simple CRUD apps where occasional page refreshes are fine.
"""

from fastapi import WebSocket
import json
from typing import Set


class ConnectionManager:
    """
    Manages active WebSocket connections.
    
    Think of it like a group chat room:
    - connect(): Someone joins the room
    - disconnect(): Someone leaves the room  
    - broadcast(): Send a message to everyone in the room
    """

    def __init__(self):
        # A set of all currently connected WebSocket clients
        # Using a set (not a list) because we need fast add/remove operations
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection and add it to active connections."""
        await websocket.accept()
        self.active_connections.add(websocket)
        print(f"🔌 WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection from active connections."""
        self.active_connections.discard(websocket)  # discard() won't error if not found
        print(f"🔌 WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """
        Send a message to ALL connected clients.
        
        If a client has disconnected unexpectedly (network drop), we catch the error
        and clean up. This prevents one dead connection from blocking all updates.
        """
        # Create a copy of the set because we might modify it during iteration
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Connection is dead — mark for removal
                disconnected.add(connection)

        # Clean up dead connections
        for conn in disconnected:
            self.active_connections.discard(conn)

    async def send_personal(self, websocket: WebSocket, message: dict):
        """Send a message to a specific client (not broadcast)."""
        try:
            await websocket.send_json(message)
        except Exception:
            self.active_connections.discard(websocket)


# ─── Global instance (shared across the entire app) ──────────────────────────
# This is a singleton pattern — there should only be ONE connection manager
manager = ConnectionManager()
