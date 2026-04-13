"""
FastAPI Application Entry Point
=================================

WHAT: The main FastAPI application that ties everything together.
WHY:  This is the "heart" of the backend — it configures CORS, registers routes,
      sets up WebSocket, initializes the database, and serves the frontend.
HOW:  Uses FastAPI's lifespan events for startup/shutdown, mounts static files
      for the frontend, and includes all route modules.

Run with: python run.py (or uvicorn backend.main:app --reload)
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from shared.config import CORS_ORIGINS
from database.schema import initialize_database
from backend.routes.devices import router as device_router
from backend.routes.websocket import manager


# ─── Lifespan: Startup & Shutdown Logic ──────────────────────────────────────
# This runs ONCE when the server starts, and once when it shuts down.
# Perfect for database initialization, connection pools, etc.
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager — replaces the old @app.on_event("startup").
    
    Everything before 'yield' runs on STARTUP.
    Everything after 'yield' runs on SHUTDOWN.
    """
    # ── STARTUP ──
    print("🚀 Starting Smart Home Backend...")
    await initialize_database()
    print("✅ Backend is ready!")
    print("📖 API docs available at: http://localhost:8000/docs")
    print("🏠 Frontend available at: http://localhost:8000")

    yield  # Server is running during this yield

    # ── SHUTDOWN ──
    print("👋 Shutting down Smart Home Backend...")


# ─── Create the FastAPI app ──────────────────────────────────────────────────
app = FastAPI(
    title="🏠 Smart Home MCP API",
    description="AI-powered smart home control system using MCP (Model Context Protocol)",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS Middleware ─────────────────────────────────────────────────────────
# CORS (Cross-Origin Resource Sharing) controls which websites can call your API.
# Without this, a frontend on localhost:5500 can't call an API on localhost:8000.
# In production, replace "*" with your actual frontend domain!
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],        # Allow GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],        # Allow all headers
)

# ─── Include REST API Routes ─────────────────────────────────────────────────
app.include_router(device_router)


# ─── WebSocket Endpoint ──────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time device updates.
    
    Flow:
    1. Client connects to ws://localhost:8000/ws
    2. Server accepts the connection
    3. Server sends updates whenever device states change
    4. Client can also send messages (e.g., requesting a refresh)
    5. When the client disconnects, we clean up
    
    This runs in an infinite loop — one coroutine per connected client.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Wait for any message from the client
            # (This keeps the connection alive and lets us detect disconnects)
            data = await websocket.receive_text()

            # Optional: handle client messages (e.g., "ping" for keepalive)
            if data == "ping":
                await manager.send_personal(websocket, {"type": "pong"})

    except WebSocketDisconnect:
        # Client closed the connection normally
        manager.disconnect(websocket)
    except Exception as e:
        # Unexpected error — still clean up
        print(f"⚠️ WebSocket error: {e}")
        manager.disconnect(websocket)


# ─── Serve Frontend Static Files ─────────────────────────────────────────────
# This lets us serve the frontend from the same server as the API.
# No need for a separate web server!
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

if os.path.exists(frontend_path):
    # Serve static files (CSS, JS) from /static path
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    # Serve index.html at the root URL
    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_path, "index.html"))


# ─── Health Check ────────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health_check():
    """Simple health check endpoint — used for monitoring."""
    return {
        "status": "healthy",
        "service": "Smart Home MCP Backend",
        "websocket_connections": len(manager.active_connections)
    }
