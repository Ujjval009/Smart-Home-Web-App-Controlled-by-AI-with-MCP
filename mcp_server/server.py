"""
MCP Server — Smart Home Tool Definitions
==========================================

WHAT: A FastMCP server that exposes smart home operations as AI-callable tools.
WHY:  MCP (Model Context Protocol) by Anthropic is the standard way to give AI models
      the ability to interact with external systems. Instead of the AI generating code
      or making raw API calls, it calls well-defined tools with validated parameters.
HOW:  Each tool is a Python function decorated with @mcp.tool(). FastMCP handles:
      - Parameter validation
      - Tool discovery (AI can ask "what tools are available?")
      - Error handling and response formatting

The tools internally call our FastAPI backend via HTTP requests.
This means the MCP server and FastAPI server can run on different machines if needed.

Run with: python -m mcp_server.server
         (or use the MCP inspector: npx @modelcontextprotocol/inspector)
"""

import httpx
from mcp.server.fastmcp import FastMCP
from shared.config import BACKEND_URL, MCP_SERVER_NAME

# ─── Create the MCP Server ───────────────────────────────────────────────────
# FastMCP is Anthropic's Python framework for building MCP servers.
# It handles the protocol details so you just write tool functions.
mcp = FastMCP(
    MCP_SERVER_NAME,
    instructions="AI-powered smart home control system. Use these tools to manage smart home devices."
)

# ─── HTTP Client for calling our FastAPI backend ─────────────────────────────
# We use httpx (async HTTP client) to call our FastAPI endpoints.
# timeout=10.0 prevents hanging if the backend is down.


async def _api_call(method: str, path: str, json_data: dict = None) -> dict:
    """
    Internal helper to make HTTP calls to the FastAPI backend.
    
    This is a DRY pattern — all tools use this instead of duplicating HTTP logic.
    Handles errors gracefully so the AI gets useful error messages.
    """
    url = f"{BACKEND_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if method == "GET":
                response = await client.get(url)
            elif method == "POST":
                response = await client.post(url, json=json_data or {})
            elif method == "PUT":
                response = await client.put(url, json=json_data)
            elif method == "DELETE":
                response = await client.delete(url)
            else:
                return {"error": f"Unknown HTTP method: {method}"}

            # Check if the request was successful
            if response.status_code >= 400:
                return {"error": f"API returned {response.status_code}: {response.text}"}

            return response.json()

    except httpx.ConnectError:
        return {"error": f"Cannot connect to backend at {BACKEND_URL}. Is it running?"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


# ═══════════════════════════════════════════════════════════════════════════════
# MCP TOOLS — These are what the AI model calls
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
async def get_all_devices() -> str:
    """
    Get a list of all smart home devices with their current states.
    
    Use this to see what devices are available and their current status.
    Returns a list of devices with id, name, type, room, state, and brightness.
    """
    result = await _api_call("GET", "/api/devices")
    if isinstance(result, list):
        # Format nicely for the AI to read
        lines = ["📋 All Smart Home Devices:\n"]
        for d in result:
            icon = "🟢" if d["state"] == "on" else "🔴"
            lines.append(
                f"  {icon} [{d['id']}] {d['name']} ({d['type']}) "
                f"in {d['room']} — {d['state']} (brightness: {d['brightness']}%)"
            )
        return "\n".join(lines)
    return str(result)


@mcp.tool()
async def get_device_status(device_id: int) -> str:
    """
    Get the current status of a specific device by its ID.
    
    Args:
        device_id: The unique ID of the device to check.
    """
    result = await _api_call("GET", f"/api/devices/{device_id}")
    if "error" in result:
        return f"❌ Error: {result['error']}"

    icon = "🟢" if result["state"] == "on" else "🔴"
    return (
        f"{icon} Device Status:\n"
        f"  Name: {result['name']}\n"
        f"  Type: {result['type']}\n"
        f"  Room: {result['room']}\n"
        f"  State: {result['state']}\n"
        f"  Brightness: {result['brightness']}%"
    )


@mcp.tool()
async def turn_on_device(device_id: int) -> str:
    """
    Turn ON a smart home device.
    
    Args:
        device_id: The unique ID of the device to turn on.
    """
    result = await _api_call("PUT", f"/api/devices/{device_id}/state", {
        "state": "on",
        "source": "ai"  # Track that the AI triggered this
    })
    if "error" in result:
        return f"❌ Error: {result['error']}"
    return f"✅ {result['name']} in {result['room']} is now ON"


@mcp.tool()
async def turn_off_device(device_id: int) -> str:
    """
    Turn OFF a smart home device.
    
    Args:
        device_id: The unique ID of the device to turn off.
    """
    result = await _api_call("PUT", f"/api/devices/{device_id}/state", {
        "state": "off",
        "source": "ai"
    })
    if "error" in result:
        return f"❌ Error: {result['error']}"
    return f"✅ {result['name']} in {result['room']} is now OFF"


@mcp.tool()
async def toggle_device(device_id: int) -> str:
    """
    Toggle a device's state (if on → turn off, if off → turn on).
    
    Args:
        device_id: The unique ID of the device to toggle.
    """
    result = await _api_call("POST", f"/api/devices/{device_id}/toggle")
    if "error" in result:
        return f"❌ Error: {result['error']}"
    return f"✅ {result['name']} in {result['room']} is now {result['state'].upper()}"


@mcp.tool()
async def set_device_brightness(device_id: int, brightness: int) -> str:
    """
    Set the brightness level of a device (0-100).
    
    Args:
        device_id: The unique ID of the device.
        brightness: Brightness level from 0 (dimmest) to 100 (brightest).
    """
    if brightness < 0 or brightness > 100:
        return "❌ Brightness must be between 0 and 100"

    result = await _api_call("PUT", f"/api/devices/{device_id}/brightness", {
        "brightness": brightness,
        "source": "ai"
    })
    if "error" in result:
        return f"❌ Error: {result['error']}"
    return f"✅ {result['name']} brightness set to {brightness}%"


@mcp.tool()
async def get_devices_in_room(room: str) -> str:
    """
    Get all devices in a specific room.
    
    Args:
        room: The name of the room (e.g., "Living Room", "Bedroom", "Kitchen").
    """
    result = await _api_call("GET", f"/api/devices/room/{room}")
    if isinstance(result, list):
        if not result:
            return f"📭 No devices found in {room}"
        lines = [f"📋 Devices in {room}:\n"]
        for d in result:
            icon = "🟢" if d["state"] == "on" else "🔴"
            lines.append(f"  {icon} [{d['id']}] {d['name']} — {d['state']}")
        return "\n".join(lines)
    return str(result)


@mcp.tool()
async def get_action_history(limit: int = 10) -> str:
    """
    Get the recent history of smart home actions.
    
    Args:
        limit: Number of recent actions to retrieve (default: 10).
    """
    result = await _api_call("GET", f"/api/logs?limit={limit}")
    if isinstance(result, list):
        if not result:
            return "📭 No action history found"
        lines = ["📜 Recent Action History:\n"]
        for log in result:
            device_name = log.get("device_name", f"Device {log['device_id']}")
            lines.append(
                f"  [{log['timestamp']}] {device_name}: "
                f"{log['old_state']} → {log['new_state']} (by {log['source']})"
            )
        return "\n".join(lines)
    return str(result)


@mcp.tool()
async def add_new_device(name: str, device_type: str, room: str = "Unknown") -> str:
    """
    Add a new smart home device to the system.
    
    Args:
        name: Human-readable name for the device (e.g., "Desk Lamp").
        device_type: Type of device (light, fan, thermostat, lock, camera, speaker, blinds, outlet).
        room: Which room the device is in (e.g., "Living Room").
    """
    result = await _api_call("POST", "/api/devices", {
        "name": name,
        "type": device_type,
        "room": room
    })
    if "error" in result:
        return f"❌ Error: {result['error']}"
    return f"✅ Added new device: {result['name']} ({result['type']}) in {result['room']} [ID: {result['id']}]"


# ═══════════════════════════════════════════════════════════════════════════════
# MCP RESOURCES — Read-only data the AI can access
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.resource("smart-home://system/info")
async def get_system_info() -> str:
    """Provides information about the smart home system."""
    return (
        "Smart Home MCP System v1.0\n"
        "Available device types: light, fan, thermostat, lock, camera, speaker, blinds, outlet\n"
        "Control devices using the available tools.\n"
        "All actions are logged for history tracking."
    )


# ─── Run the server ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🔌 Starting Smart Home MCP Server...")
    print(f"📡 Backend URL: {BACKEND_URL}")
    print("🛠️  Available tools: get_all_devices, turn_on_device, turn_off_device, "
          "toggle_device, get_device_status, set_device_brightness, "
          "get_devices_in_room, get_action_history, add_new_device")
    
    # Run the MCP server using stdio transport (standard for MCP)
    mcp.run()
