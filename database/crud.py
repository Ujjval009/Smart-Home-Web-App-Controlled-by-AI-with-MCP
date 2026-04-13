"""
CRUD Operations for Smart Home Database
=========================================

WHAT: Functions to Create, Read, Update, and Delete database records.
WHY:  Isolates all SQL queries in one place. If you change the database schema
      or switch to PostgreSQL, you only modify this file.
HOW:  Each function opens an async connection, executes a parameterized query,
      and returns Python dictionaries (not raw tuples).

IMPORTANT: All queries use parameterized placeholders (?) to prevent SQL injection.
           NEVER use f-strings or .format() to build SQL queries!
"""

import aiosqlite
from datetime import datetime
from shared.config import DATABASE_PATH


def _row_to_dict(row, columns):
    """
    Convert a database row (tuple) to a dictionary.
    
    SQLite returns rows as tuples like (1, "Light", "on").
    We convert them to dicts like {"id": 1, "name": "Light", "state": "on"}
    so they're easy to work with and serialize to JSON.
    """
    return dict(zip(columns, row))


# ═══════════════════════════════════════════════════════════════════════════════
# DEVICE OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

async def get_all_devices():
    """Fetch all devices from the database, returned as a list of dicts."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT * FROM devices ORDER BY room, name")
        columns = [description[0] for description in cursor.description]
        rows = await cursor.fetchall()
        return [_row_to_dict(row, columns) for row in rows]


async def get_device_by_id(device_id: int):
    """
    Fetch a single device by its ID.
    Returns None if the device doesn't exist (important for error handling!).
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT * FROM devices WHERE id = ?", (device_id,))
        columns = [description[0] for description in cursor.description]
        row = await cursor.fetchone()
        return _row_to_dict(row, columns) if row else None


async def get_devices_by_room(room: str):
    """Fetch all devices in a specific room."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT * FROM devices WHERE room = ? ORDER BY name",
            (room,)
        )
        columns = [description[0] for description in cursor.description]
        rows = await cursor.fetchall()
        return [_row_to_dict(row, columns) for row in rows]


async def get_devices_by_type(device_type: str):
    """Fetch all devices of a specific type (e.g., all 'light' devices)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT * FROM devices WHERE type = ? ORDER BY room, name",
            (device_type,)
        )
        columns = [description[0] for description in cursor.description]
        rows = await cursor.fetchall()
        return [_row_to_dict(row, columns) for row in rows]


async def update_device_state(device_id: int, new_state: str, source: str = "api"):
    """
    Update a device's on/off state and log the action.
    
    Args:
        device_id: The ID of the device to update
        new_state: Either "on" or "off"
        source: Who triggered this change ("ai", "frontend", "mcp", "api")
    
    Returns:
        The updated device dict, or None if device doesn't exist
    """
    # First, get the current device state (for logging)
    device = await get_device_by_id(device_id)
    if not device:
        return None

    old_state = device["state"]

    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Update the device state
        await db.execute(
            """UPDATE devices 
               SET state = ?, updated_at = CURRENT_TIMESTAMP 
               WHERE id = ?""",
            (new_state, device_id)
        )

        # Log the action (for history/debugging)
        await db.execute(
            """INSERT INTO action_logs (device_id, action, old_state, new_state, source) 
               VALUES (?, ?, ?, ?, ?)""",
            (device_id, f"state_change", old_state, new_state, source)
        )

        await db.commit()

    # Return the updated device
    return await get_device_by_id(device_id)


async def update_device_brightness(device_id: int, brightness: int, source: str = "api"):
    """
    Update a device's brightness level (0-100).
    
    This is separate from state because you might want to set brightness
    without turning the device on/off.
    """
    device = await get_device_by_id(device_id)
    if not device:
        return None

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """UPDATE devices 
               SET brightness = ?, updated_at = CURRENT_TIMESTAMP 
               WHERE id = ?""",
            (brightness, device_id)
        )

        await db.execute(
            """INSERT INTO action_logs (device_id, action, old_state, new_state, source)
               VALUES (?, ?, ?, ?, ?)""",
            (device_id, "brightness_change", str(device["brightness"]), str(brightness), source)
        )

        await db.commit()

    return await get_device_by_id(device_id)


async def add_device(name: str, device_type: str, room: str = "Unknown"):
    """
    Add a new device to the system.
    Returns the newly created device dict.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO devices (name, type, room) 
               VALUES (?, ?, ?)""",
            (name, device_type, room)
        )
        await db.commit()
        new_id = cursor.lastrowid

    return await get_device_by_id(new_id)


async def delete_device(device_id: int):
    """
    Delete a device from the system.
    Returns True if deleted, False if device didn't exist.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("DELETE FROM devices WHERE id = ?", (device_id,))
        await db.commit()
        return cursor.rowcount > 0


# ═══════════════════════════════════════════════════════════════════════════════
# ACTION LOG OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

async def get_action_logs(limit: int = 50):
    """
    Fetch recent action logs, newest first.
    Joins with devices table to include device names.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """SELECT al.*, d.name as device_name, d.type as device_type
               FROM action_logs al
               JOIN devices d ON al.device_id = d.id
               ORDER BY al.timestamp DESC
               LIMIT ?""",
            (limit,)
        )
        columns = [description[0] for description in cursor.description]
        rows = await cursor.fetchall()
        return [_row_to_dict(row, columns) for row in rows]


async def get_device_logs(device_id: int, limit: int = 20):
    """Fetch action logs for a specific device."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """SELECT * FROM action_logs 
               WHERE device_id = ? 
               ORDER BY timestamp DESC 
               LIMIT ?""",
            (device_id, limit)
        )
        columns = [description[0] for description in cursor.description]
        rows = await cursor.fetchall()
        return [_row_to_dict(row, columns) for row in rows]
