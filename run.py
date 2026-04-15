"""
Run Script — Start the Smart Home Backend
==========================================

Single entry point to start the FastAPI server.
Run with: python run.py

This starts:
  - FastAPI backend on http://localhost:8000
  - WebSocket server on ws://localhost:8000/ws
  - Frontend UI on http://localhost:8000
  - API docs on http://localhost:8000/docs
"""

import uvicorn
from shared.config import BACKEND_HOST, BACKEND_PORT

if __name__ == "__main__":
    print("🏠 Smart Home MCP System")
    print("=" * 50)
    print(f"🌐 Starting server at http://{BACKEND_HOST}:{BACKEND_PORT}")
    print(f"📖 API docs: http://{BACKEND_HOST}:{BACKEND_PORT}/docs")
    print(f"🔌 WebSocket: ws://{BACKEND_HOST}:{BACKEND_PORT}/ws")
    print("=" * 50)

    uvicorn.run(
        "backend.main:app",     # Import path to the FastAPI app
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        reload=True,            # Auto-reload on code changes (dev only!)
        log_level="info",
    )
