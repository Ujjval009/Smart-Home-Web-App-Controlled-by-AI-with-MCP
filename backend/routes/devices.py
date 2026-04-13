"""
Device REST API Routes
========================

WHAT: HTTP endpoints for managing smart home devices.
WHY:  Provides a standard REST API that the MCP server, frontend, and any other
      client can use to control devices.
HOW:  Each route function handles a specific HTTP method + path combination.
      FastAPI automatically validates requests using our Pydantic models.

Endpoints:
  GET    /api/devices              → List all devices
  GET    /api/devices/{id}         → Get one device
  GET    /api/devices/room/{room}  → Get devices by room
  GET    /api/devices/type/{type}  → Get devices by type
  POST   /api/devices              → Add a new device
  PUT    /api/devices/{id}/state   → Update device state (on/off)
  PUT    /api/devices/{id}/brightness → Update device brightness
  DELETE /api/devices/{id}         → Delete a device
  POST   /api/devices/{id}/toggle  → Toggle device state
  GET    /api/logs                 → Get action history
  GET    /api/logs/{device_id}     → Get logs for specific device
"""

from fastapi import APIRouter, HTTPException
from backend.models import (
    DeviceResponse, DeviceStateUpdate, DeviceBrightnessUpdate,
    DeviceCreate, ActionLogResponse
)
from database.crud import (
    get_all_devices, get_device_by_id, get_devices_by_room,
    get_devices_by_type, update_device_state, update_device_brightness,
    add_device, delete_device, get_action_logs, get_device_logs
)
from backend.routes.websocket import manager

# ─── Create a router with a prefix ───────────────────────────────────────────
# All routes defined here will be prefixed with /api
# Tags help organize the auto-generated API docs at /docs
router = APIRouter(prefix="/api", tags=["devices"])


# ═══════════════════════════════════════════════════════════════════════════════
# READ OPERATIONS (GET)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/devices", response_model=list[DeviceResponse])
async def list_devices():
    """Get all devices, ordered by room and name."""
    devices = await get_all_devices()
    return devices


@router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: int):
    """
    Get a single device by ID.
    
    Returns 404 if the device doesn't exist.
    This is a common pattern: try to find it, raise an error if not found.
    """
    device = await get_device_by_id(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    return device


@router.get("/devices/room/{room}")
async def list_devices_by_room(room: str):
    """Get all devices in a specific room (e.g., 'Living Room')."""
    devices = await get_devices_by_room(room)
    return devices


@router.get("/devices/type/{device_type}")
async def list_devices_by_type(device_type: str):
    """Get all devices of a specific type (e.g., 'light')."""
    devices = await get_devices_by_type(device_type)
    return devices


# ═══════════════════════════════════════════════════════════════════════════════
# WRITE OPERATIONS (POST, PUT, DELETE)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/devices", response_model=DeviceResponse, status_code=201)
async def create_device(device: DeviceCreate):
    """
    Add a new device to the system.
    
    Returns 201 Created (not 200 OK) because we're creating a new resource.
    This is a REST best practice.
    """
    new_device = await add_device(device.name, device.type, device.room)

    # Broadcast to all WebSocket clients that a new device was added
    await manager.broadcast({
        "type": "device_added",
        "data": new_device
    })

    return new_device


@router.put("/devices/{device_id}/state", response_model=DeviceResponse)
async def change_device_state(device_id: int, update: DeviceStateUpdate):
    """
    Update a device's on/off state.
    
    This is the main endpoint that MCP tools and the frontend call.
    After updating, it broadcasts the change via WebSocket so the
    frontend updates in real-time.
    """
    device = await update_device_state(device_id, update.state, update.source)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

    # ⚡ Broadcast the update to all connected WebSocket clients
    await manager.broadcast({
        "type": "device_update",
        "data": device
    })

    return device


@router.put("/devices/{device_id}/brightness", response_model=DeviceResponse)
async def change_device_brightness(device_id: int, update: DeviceBrightnessUpdate):
    """Update a device's brightness level (0-100)."""
    device = await update_device_brightness(device_id, update.brightness, update.source)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

    await manager.broadcast({
        "type": "device_update",
        "data": device
    })

    return device


@router.post("/devices/{device_id}/toggle", response_model=DeviceResponse)
async def toggle_device(device_id: int):
    """
    Toggle a device's state (on → off, off → on).
    
    This is a convenience endpoint. Instead of the frontend needing to know
    the current state, it can just say "toggle it".
    """
    device = await get_device_by_id(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

    # Flip the state
    new_state = "off" if device["state"] == "on" else "on"
    updated = await update_device_state(device_id, new_state, "frontend")

    await manager.broadcast({
        "type": "device_update",
        "data": updated
    })

    return updated


@router.delete("/devices/{device_id}")
async def remove_device(device_id: int):
    """Delete a device from the system."""
    success = await delete_device(device_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

    await manager.broadcast({
        "type": "device_deleted",
        "data": {"id": device_id}
    })

    return {"message": f"Device {device_id} deleted successfully"}


# ═══════════════════════════════════════════════════════════════════════════════
# ACTION LOGS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/logs")
async def list_logs(limit: int = 50):
    """Get recent action logs (newest first)."""
    logs = await get_action_logs(limit)
    return logs


@router.get("/logs/{device_id}")
async def list_device_logs(device_id: int, limit: int = 20):
    """Get action logs for a specific device."""
    logs = await get_device_logs(device_id, limit)
    return logs
