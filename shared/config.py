"""
Central Configuration for the Smart Home MCP System
====================================================

WHAT: A single file containing ALL configuration values for every component.
WHY:  Prevents hardcoded values scattered across files. Change a port once here,
      and it updates everywhere.
HOW:  Uses simple Python constants. In production, you'd use environment variables
      or a .env file with python-dotenv.
"""

import os

# ─── Backend (FastAPI) Configuration ──────────────────────────────────────────
BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"

# ─── Database Configuration ──────────────────────────────────────────────────
# Using a file-based SQLite database (not in-memory) so data persists
DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "smart_home.db")
)

# ─── MCP Server Configuration ────────────────────────────────────────────────
MCP_SERVER_NAME = "SmartHomeMCP"

# ─── Frontend Configuration ──────────────────────────────────────────────────
# CORS origins allowed to access the backend
CORS_ORIGINS = [
    "http://localhost:5500",      # VS Code Live Server
    "http://127.0.0.1:5500",
    "http://localhost:8000",      # Same-origin (served by FastAPI)
    "http://127.0.0.1:8000",
    "http://localhost:3000",      # React dev server (if used later)
    "*",                          # Allow all for development — REMOVE in production!
]

# ─── Device Types (shared vocabulary) ────────────────────────────────────────
# These are the valid device types the system recognizes
DEVICE_TYPES = [
    "light",
    "fan",
    "thermostat",
    "lock",
    "camera",
    "speaker",
    "blinds",
    "outlet",
]
