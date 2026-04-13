"""
SQLite Database Schema & Initialization
========================================

WHAT: Creates the database tables and seeds initial device data.
WHY:  The database is our "single source of truth" — every device state is stored here.
HOW:  Uses aiosqlite for async operations (FastAPI is async, so our DB calls must be too).
WHEN: Called once on application startup via the FastAPI lifespan event.

Tables:
  - devices: Stores each smart home device (id, name, type, room, state, brightness)
  - action_logs: Records every action taken (who did what, when)
"""

import aiosqlite
import os
from shared.config import DATABASE_PATH


async def initialize_database():
    """
    Create tables if they don't exist, then seed with sample devices.
    
    This function is IDEMPOTENT — safe to call multiple times.
    'IF NOT EXISTS' ensures we don't lose data on restart.
    """
    # Ensure the database directory exists
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        # ─── Create Devices Table ─────────────────────────────────────────
        # Each device has a unique ID, a human-readable name, a type (light/fan/etc),
        # the room it's in, an on/off state, and an optional brightness level.
        await db.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                type        TEXT NOT NULL,
                room        TEXT NOT NULL DEFAULT 'Unknown',
                state       TEXT NOT NULL DEFAULT 'off' CHECK(state IN ('on', 'off')),
                brightness  INTEGER DEFAULT 100 CHECK(brightness >= 0 AND brightness <= 100),
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ─── Create Action Logs Table ─────────────────────────────────────
        # Every action is logged for debugging and history.
        # 'source' tracks WHO triggered the action (ai, frontend, api, mcp)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS action_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id   INTEGER NOT NULL,
                action      TEXT NOT NULL,
                old_state   TEXT,
                new_state   TEXT,
                source      TEXT NOT NULL DEFAULT 'unknown',
                timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES devices(id)
            )
        """)

        # ─── Seed Sample Devices (only if table is empty) ────────────────
        cursor = await db.execute("SELECT COUNT(*) FROM devices")
        count = (await cursor.fetchone())[0]

        if count == 0:
            sample_devices = [
                ("Living Room Light",   "light",      "Living Room",  "off", 100),
                ("Bedroom Light",       "light",      "Bedroom",      "off", 75),
                ("Kitchen Light",       "light",      "Kitchen",      "off", 100),
                ("Ceiling Fan",         "fan",        "Living Room",  "off", 50),
                ("Bedroom Fan",         "fan",        "Bedroom",      "off", 100),
                ("Smart Thermostat",    "thermostat", "Hallway",      "off", 72),
                ("Front Door Lock",     "lock",       "Entrance",     "off", 100),
                ("Garden Camera",       "camera",     "Garden",       "off", 100),
                ("Smart Speaker",       "speaker",    "Living Room",  "off", 60),
                ("Window Blinds",       "blinds",     "Bedroom",      "off", 100),
                ("Desk Lamp",           "light",      "Office",       "off", 80),
                ("Smart Outlet",        "outlet",     "Kitchen",      "off", 100),
            ]

            await db.executemany(
                """INSERT INTO devices (name, type, room, state, brightness) 
                   VALUES (?, ?, ?, ?, ?)""",
                sample_devices
            )
            print(f"✅ Seeded {len(sample_devices)} sample devices into database")

        await db.commit()
        print(f"✅ Database initialized at: {DATABASE_PATH}")
