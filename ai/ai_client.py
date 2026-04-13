"""
AI Client — Example of AI ↔ MCP Integration
==============================================

WHAT: Demonstrates how an AI model (like Claude) calls MCP tools to control smart home devices.
WHY:  Shows the complete flow: User → AI → MCP → Backend → Database.
HOW:  Uses the MCP Python SDK to connect to our MCP server and call tools.

IMPORTANT: This is an EXAMPLE script. In a real system, the AI model would be
           connected via an AI platform (Claude Desktop, LangChain, etc.).
           This script simulates that interaction for learning purposes.

To run: python -m ai.ai_client
Prerequisite: The FastAPI backend must be running (python run.py)
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run_ai_demo():
    """
    Demo: Connect to the MCP server and call tools as if we were an AI model.
    
    This simulates what happens when Claude or another AI decides to call a tool.
    In a real system, the AI model would do this automatically based on user prompts.
    """
    print("=" * 60)
    print("🤖 Smart Home AI Demo")
    print("=" * 60)
    print()

    # ─── Connect to the MCP Server ───────────────────────────────────────
    # StdioServerParameters tells the client how to start the MCP server.
    # The MCP server communicates via stdin/stdout (standard MCP transport).
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "mcp_server.server"],
    )

    print("📡 Connecting to Smart Home MCP Server...")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the MCP session
            await session.initialize()

            # ─── Step 1: Discover available tools ─────────────────────
            print("\n🛠️  Discovering available tools...")
            tools = await session.list_tools()
            print(f"   Found {len(tools.tools)} tools:")
            for tool in tools.tools:
                print(f"   • {tool.name}: {tool.description[:80]}...")

            # ─── Step 2: Get all devices ──────────────────────────────
            print("\n📋 AI Action: 'Show me all devices'")
            result = await session.call_tool("get_all_devices", {})
            print(result.content[0].text)

            # ─── Step 3: Turn on a device ─────────────────────────────
            print("\n💡 AI Action: 'Turn on the living room light (ID: 1)'")
            result = await session.call_tool("turn_on_device", {"device_id": 1})
            print(result.content[0].text)

            # ─── Step 4: Check device status ──────────────────────────
            print("\n🔍 AI Action: 'What's the status of device 1?'")
            result = await session.call_tool("get_device_status", {"device_id": 1})
            print(result.content[0].text)

            # ─── Step 5: Set brightness ───────────────────────────────
            print("\n🔆 AI Action: 'Set living room light to 50% brightness'")
            result = await session.call_tool("set_device_brightness", {
                "device_id": 1,
                "brightness": 50
            })
            print(result.content[0].text)

            # ─── Step 6: Get devices in a room ───────────────────────
            print("\n🏠 AI Action: 'What devices are in the Living Room?'")
            result = await session.call_tool("get_devices_in_room", {"room": "Living Room"})
            print(result.content[0].text)

            # ─── Step 7: Toggle a device ──────────────────────────────
            print("\n🔄 AI Action: 'Toggle the ceiling fan'")
            result = await session.call_tool("toggle_device", {"device_id": 4})
            print(result.content[0].text)

            # ─── Step 8: Check action history ─────────────────────────
            print("\n📜 AI Action: 'Show me recent actions'")
            result = await session.call_tool("get_action_history", {"limit": 5})
            print(result.content[0].text)

            # ─── Step 9: Turn off device ──────────────────────────────
            print("\n🌙 AI Action: 'Turn off the living room light'")
            result = await session.call_tool("turn_off_device", {"device_id": 1})
            print(result.content[0].text)

    print("\n" + "=" * 60)
    print("✅ AI Demo Complete!")
    print("=" * 60)


# ─── Alternative: Direct API calls (without MCP) ────────────────────────────
async def run_direct_api_demo():
    """
    Alternative demo: Call the FastAPI backend directly without MCP.
    
    This shows that the backend works independently of MCP.
    Useful for testing or when you don't need AI in the loop.
    """
    import httpx
    from shared.config import BACKEND_URL

    print("=" * 60)
    print("🔧 Direct API Demo (no AI/MCP)")
    print("=" * 60)

    async with httpx.AsyncClient(base_url=BACKEND_URL) as client:
        # Get all devices
        print("\n📋 Getting all devices...")
        response = await client.get("/api/devices")
        devices = response.json()
        for d in devices:
            icon = "🟢" if d["state"] == "on" else "🔴"
            print(f"  {icon} [{d['id']}] {d['name']} — {d['state']}")

        # Toggle first device
        if devices:
            device_id = devices[0]["id"]
            print(f"\n🔄 Toggling device {device_id}...")
            response = await client.post(f"/api/devices/{device_id}/toggle")
            result = response.json()
            print(f"  {result['name']} is now {result['state']}")

        # Check logs
        print("\n📜 Recent logs...")
        response = await client.get("/api/logs?limit=5")
        logs = response.json()
        for log in logs:
            print(f"  [{log['timestamp']}] Device {log['device_id']}: {log['action']}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--direct":
        # Run without MCP: python -m ai.ai_client --direct
        asyncio.run(run_direct_api_demo())
    else:
        # Run with MCP: python -m ai.ai_client
        asyncio.run(run_ai_demo())
