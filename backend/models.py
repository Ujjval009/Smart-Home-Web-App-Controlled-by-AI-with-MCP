"""
Pydantic Models for Request/Response Validation
=================================================

WHAT: Data models that define the shape of API requests and responses.
WHY:  FastAPI uses these to automatically validate incoming data and generate
      API documentation. If someone sends {"state": "maybe"}, FastAPI will 
      reject it before your code even runs.
HOW:  Pydantic validates data at runtime using Python type hints.
      Invalid data raises a 422 Validation Error with helpful details.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class DeviceResponse(BaseModel):
    """What a device looks like in API responses."""
    id: int
    name: str
    type: str
    room: str
    state: Literal["on", "off"]  # Only "on" or "off" allowed
    brightness: int = Field(ge=0, le=100)  # 0-100 range enforced
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class DeviceStateUpdate(BaseModel):
    """
    Request body for updating a device's state.
    
    Example: {"state": "on", "source": "frontend"}
    """
    state: Literal["on", "off"]  # Rejects anything other than "on"/"off"
    source: str = "api"          # Who triggered this (defaults to "api")


class DeviceBrightnessUpdate(BaseModel):
    """Request body for updating brightness."""
    brightness: int = Field(ge=0, le=100, description="Brightness level 0-100")
    source: str = "api"


class DeviceCreate(BaseModel):
    """Request body for adding a new device."""
    name: str = Field(min_length=1, max_length=100)
    type: str = Field(min_length=1, max_length=50)
    room: str = Field(default="Unknown", max_length=100)


class ActionLogResponse(BaseModel):
    """What an action log entry looks like in API responses."""
    id: int
    device_id: int
    action: str
    old_state: Optional[str]
    new_state: Optional[str]
    source: str
    timestamp: Optional[str]
    device_name: Optional[str] = None
    device_type: Optional[str] = None


class WebSocketMessage(BaseModel):
    """
    Structure of WebSocket messages sent to connected clients.
    
    type: The kind of event (e.g., "device_update", "device_added")
    data: The payload (usually the updated device data)
    """
    type: str
    data: dict
