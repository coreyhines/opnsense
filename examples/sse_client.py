#!/usr/bin/env python3
"""
Example client for the OPNsense MCP Server using Server-Sent Events (SSE).

This script demonstrates how to connect to the SSE-based MCP server and
make tool calls.
"""

import argparse
import asyncio
import json
import logging
import uuid
from typing import Any, Dict, Optional

import aiohttp
from sseclient import SSEClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


class OPNsenseMCPClient:
    """Client for the OPNsense MCP Server using SSE."""

    def __init__(self, base_url: str = "http://127.0.0.1:8080"):
        """Initialize the client with the server URL."""
        self.base_url = base_url
        self.client_id = str(uuid.uuid4())
        self.sse_connected = False
        self.event_handlers = {}
        self.session = None

    async def __aenter__(self):
        """Enter the async context manager."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager."""
        if self.session:
            await self.session.close()

    async def initialize(self) -> Dict[str, Any]:
        """Initialize the connection to the MCP server."""
        async with self.session.post(
            f"{self.base_url}/initialize",
            json={"protocolVersion": "2024-11-05", "clientInfo": {"name": "example-client"}},
        ) as response:
            return await response.json()

    async def list_tools(self) -> Dict[str, Any]:
        """Get the list of available tools."""
        async with self.session.get(f"{self.base_url}/tools") as response:
            return await response.json()

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = {}) -> Dict[str, Any]:
        """Call a specific tool with arguments."""
        async with self.session.post(
            f"{self.base_url}/tool/{tool_name}", json=arguments
        ) as response:
            return await response.json()

    async def jsonrpc_call(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a JSON-RPC call to the server."""
        request_id = str(uuid.uuid4())
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params:
            payload["params"] = params

        async with self.session.post(
            f"{self.base_url}/jsonrpc", json=payload
        ) as response:
            return await response.json()

    async def connect_sse(self):
        """Connect to the SSE endpoint and start listening for events."""
        headers = {"X-Client-ID": self.client_id}
        
        try:
            # Using aiohttp to get the response
            async with self.session.get(
                f"{self.base_url}/sse", headers=headers, timeout=None
            ) as response:
                # Get the response content as text
                response_text = await response.text()
                
                # Use SSE client to process the response
                client = SSEClient(response_text)
                self.sse_connected = True
                
                # Process events as they arrive
                for event in client.events():
                    if event.event == "connected":
                        logger.info(f"SSE connected: {event.data}")
                    else:
                        # Handle other events
                        event_data = json.loads(event.data)
                        event_type = event.event
                        
                        # Call registered handlers for this event type
                        if event_type in self.event_handlers:
                            for handler in self.event_handlers[event_type]:
                                await handler(event_data)
        
        except Exception as e:
            logger.error(f"SSE connection error: {e}")
            self.sse_connected = False
        
        finally:
            self.sse_connected = False

    def register_event_handler(self, event_type: str, handler):
        """Register a handler for a specific event type."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)

    async def send_event(self, event_type: str, data: Dict[str, Any]):
        """Send an event to the server."""
        payload = {
            "event": event_type,
            "id": str(uuid.uuid4()),
            "data": data,
        }
        async with self.session.post(
            f"{self.base_url}/send/{self.client_id}", json=payload
        ) as response:
            return await response.json()


async def main():
    """Run the example client."""
    parser = argparse.ArgumentParser(description="OPNsense MCP SSE Client Example")
    parser.add_argument(
        "--server", default="http://127.0.0.1:8080", help="MCP server URL"
    )
    parser.add_argument(
        "--tool", default="system", help="Tool to call (default: system)"
    )
    parser.add_argument(
        "--args", default="{}", help="JSON arguments for the tool call"
    )
    args = parser.parse_args()

    # Parse tool arguments
    try:
        tool_args = json.loads(args.args)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON arguments: {args.args}")
        return

    async with OPNsenseMCPClient(args.server) as client:
        # Initialize the connection
        logger.info("Initializing connection...")
        init_result = await client.initialize()
        logger.info(f"Server info: {init_result.get('serverInfo')}")

        # List available tools
        logger.info("Getting available tools...")
        tools_result = await client.list_tools()
        tool_names = [tool["name"] for tool in tools_result.get("tools", [])]
        logger.info(f"Available tools: {', '.join(tool_names)}")

        # Call the specified tool
        logger.info(f"Calling tool '{args.tool}' with arguments: {tool_args}")
        tool_result = await client.call_tool(args.tool, tool_args)
        
        # Print the result
        if "content" in tool_result:
            for item in tool_result["content"]:
                if item["type"] == "text":
                    print(item["text"])
        else:
            print(json.dumps(tool_result, indent=2))

        # Connect to SSE and wait for events
        logger.info("Connecting to SSE endpoint...")
        
        # Register a simple event handler
        client.register_event_handler("message", lambda data: print(f"Received message: {data}"))
        
        # Start SSE connection in the background
        sse_task = asyncio.create_task(client.connect_sse())
        
        # Wait a bit for the connection to establish
        await asyncio.sleep(1)
        
        # Send a test event
        if client.sse_connected:
            logger.info("Sending test event...")
            await client.send_event("test", {"message": "Hello from client!"})
            
            # Wait for a few seconds to receive events
            await asyncio.sleep(5)
        
        # Cancel the SSE task
        sse_task.cancel()
        try:
            await sse_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    asyncio.run(main()) 
