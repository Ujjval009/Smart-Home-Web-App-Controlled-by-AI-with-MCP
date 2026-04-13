# 🏠 Smart Home MCP System

An AI-powered smart home control system using **MCP (Model Context Protocol)**, **FastAPI**, **SQLite**, and a real-time web dashboard.

## Architecture

```
User → AI Model → MCP Server → FastAPI Backend → SQLite Database → Frontend (WebSocket)
```

## Quick Start

### 1. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
```

### 2. Start the Backend

```bash
python run.py
```

This starts:
- 🌐 **Frontend**: http://localhost:8000
- 📖 **API Docs**: http://localhost:8000/docs
- 🔌 **WebSocket**: ws://localhost:8000/ws

### 3. Test the MCP Server

```bash
# Using MCP Inspector (visual tool)
npx @modelcontextprotocol/inspector python -m mcp_server.server

# Or test AI client directly (backend must be running)
python -m ai.ai_client --direct
```

## Project Structure

```
├── ai/              → AI integration examples
├── mcp_server/      → MCP tool definitions (AI ↔ Backend bridge)
├── backend/         → FastAPI server (REST + WebSocket)
├── database/        → SQLite schema & CRUD operations
├── frontend/        → Web dashboard (HTML/CSS/JS)
├── shared/          → Central configuration
├── run.py           → Server entry point
└── requirements.txt → Python dependencies
```

## MCP Tools Available

| Tool | Description |
|------|-------------|
| `get_all_devices` | List all devices with states |
| `get_device_status` | Get a specific device's status |
| `turn_on_device` | Turn a device on |
| `turn_off_device` | Turn a device off |
| `toggle_device` | Toggle a device's state |
| `set_device_brightness` | Set brightness (0-100) |
| `get_devices_in_room` | List devices by room |
| `get_action_history` | View recent action log |
| `add_new_device` | Add a new device |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/devices` | List all devices |
| GET | `/api/devices/{id}` | Get device by ID |
| POST | `/api/devices` | Add new device |
| PUT | `/api/devices/{id}/state` | Update state |
| PUT | `/api/devices/{id}/brightness` | Update brightness |
| POST | `/api/devices/{id}/toggle` | Toggle state |
| DELETE | `/api/devices/{id}` | Delete device |
| GET | `/api/logs` | Action history |
| GET | `/health` | Health check |

## License

MIT

## Author

Ujjval Sharma

