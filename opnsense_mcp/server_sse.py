#!/usr/bin/env python3
"""OPNsense Model Context Protocol server using Server-Sent Events (SSE)"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import (BackgroundTasks, Depends, FastAPI, HTTPException, Request,
                     Response)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from opnsense_mcp.tools.arp import ARPTool
from opnsense_mcp.tools.dhcp import DHCPTool
from opnsense_mcp.tools.firewall_logs import FirewallLogsTool
from opnsense_mcp.tools.fw_rules import FwRulesTool
from opnsense_mcp.tools.interface_list import InterfaceListTool
from opnsense_mcp.tools.lldp import LLDPTool
from opnsense_mcp.tools.mkfw_rule import MkfwRuleTool
from opnsense_mcp.tools.rmfw_rule import RmfwRuleTool
from opnsense_mcp.tools.system import SystemTool
from opnsense_mcp.utils.api import OPNsenseClient
from opnsense_mcp.utils.jwt_helper import JWTError, create_jwt, decode_jwt
from opnsense_mcp.utils.mock_api import MockOPNsenseClient

# Load environment variables from ~/.opnsense-env by default
load_dotenv(os.path.expanduser("~/.opnsense-env"))

# Configure logging
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="OPNsense MCP Server",
    description="OPNsense Model Context Protocol server using Server-Sent Events (SSE)",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store client connections
client_connections = {}

# Create Pydantic models for API requests
class InitializeRequest(BaseModel):
    protocolVersion: str = "2024-11-05"
    clientInfo: Dict[str, Any] = Field(default_factory=dict)

class ToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)

class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: str
    params: Optional[Dict[str, Any]] = None

# Create global client and tools
opnsense_client = None
firewall_logs = None
arp_tool = None
dhcp_tool = None
lldp_tool = None
system_tool = None
fw_rules_tool = None
mkfw_rule_tool = None
rmfw_rule_tool = None
interface_list_tool = None

def get_opnsense_client():
    """Get OPNsense client based on environment"""
    host = os.getenv("OPNSENSE_API_HOST")  # Use correct env var name
    api_key = os.getenv("OPNSENSE_API_KEY")
    api_secret = os.getenv("OPNSENSE_API_SECRET")
    ssl_verify = os.getenv("OPNSENSE_SSL_VERIFY", "false").lower() == "true"

    if host and api_key and api_secret:
        logger.info("Using real OPNsense client")
        return OPNsenseClient(
            {
                "firewall_host": host,
                "api_key": api_key,
                "api_secret": api_secret,
                "verify_ssl": ssl_verify,
            }
        )
    logger.warning("No OPNsense credentials found, using mock client")
    workspace_root = Path(__file__).parent.parent
    mock_data_path = workspace_root / "examples" / "mock_data"
    config = {"development": {"mock_data_path": str(mock_data_path)}}
    return MockOPNsenseClient(config)

def initialize_tools():
    """Initialize all tools with the OPNsense client"""
    global opnsense_client, firewall_logs, arp_tool, dhcp_tool, lldp_tool
    global system_tool, fw_rules_tool, mkfw_rule_tool, rmfw_rule_tool, interface_list_tool
    
    opnsense_client = get_opnsense_client()
    firewall_logs = FirewallLogsTool(opnsense_client)
    arp_tool = ARPTool(opnsense_client)
    dhcp_tool = DHCPTool(opnsense_client)
    lldp_tool = LLDPTool(opnsense_client)
    system_tool = SystemTool(opnsense_client)
    fw_rules_tool = FwRulesTool(opnsense_client)
    mkfw_rule_tool = MkfwRuleTool(opnsense_client)
    rmfw_rule_tool = RmfwRuleTool(opnsense_client)
    interface_list_tool = InterfaceListTool(opnsense_client)

@app.on_event("startup")
async def startup_event():
    """Initialize tools on startup"""
    initialize_tools()
    logger.info("OPNsense MCP Server started")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

@app.post("/initialize")
async def initialize(request: InitializeRequest):
    """Initialize the MCP connection"""
    protocol_version = request.protocolVersion
    if not protocol_version or protocol_version == "undefined":
        protocol_version = "2024-11-05"
    
    return {
        "protocolVersion": protocol_version,
        "serverInfo": {"name": "opnsense-mcp", "version": "1.0.0"},
        "capabilities": {"tools": {"listChanged": False}},
    }

@app.get("/tools")
async def list_tools():
    """List available tools"""
    tools = [
        {
            "name": "get_logs",
            "description": "Get firewall logs with optional filtering",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": {"type": "number", "optional": True},
                    "action": {"type": "string", "optional": True},
                    "src_ip": {"type": "string", "optional": True},
                    "dst_ip": {"type": "string", "optional": True},
                    "protocol": {"type": "string", "optional": True},
                },
                "required": [],
            },
        },
        {
            "name": "arp",
            "description": "Show ARP/NDP table",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "mac": {
                        "type": "string",
                        "description": "Filter by MAC address",
                        "optional": True,
                    },
                    "ip": {
                        "type": "string",
                        "description": "Filter by IP address",
                        "optional": True,
                    },
                    "search": {
                        "type": "string",
                        "description": ("Targeted search by IP/MAC/hostname"),
                        "optional": True,
                    },
                },
                "required": [],
            },
        },
        {
            "name": "dhcp",
            "description": "Show DHCP lease information",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        "description": ("Search by hostname/IP/MAC"),
                        "optional": True,
                    },
                },
                "required": [],
            },
        },
        {
            "name": "lldp",
            "description": "Show LLDP neighbor table",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "system",
            "description": "Show system status information",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "fw_rules",
            "description": (
                "Get the current firewall rule set for context and reasoning"
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "interface": {
                        "type": "string",
                        "description": (
                            "Filter by interface name "
                            "(supports partial matching and groups)"
                        ),
                        "optional": True,
                    },
                    "action": {
                        "type": "string",
                        "description": (
                            "Filter by action (pass, block, reject, etc.)"
                        ),
                        "optional": True,
                    },
                    "enabled": {
                        "type": "boolean",
                        "description": "Filter by enabled status",
                        "optional": True,
                    },
                    "protocol": {
                        "type": "string",
                        "description": (
                            "Filter by protocol (tcp, udp, icmp, etc.)"
                        ),
                        "optional": True,
                    },
                },
                "required": [],
            },
        },
        {
            "name": "mkfw_rule",
            "description": (
                "Create a new firewall rule and optionally apply changes"
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": ("Description of the rule (required)"),
                    },
                    "interface": {
                        "type": "string",
                        "description": "Interface name (default: 'lan')",
                        "optional": True,
                    },
                    "action": {
                        "type": "string",
                        "description": ("pass, block, or reject (default: 'pass')"),
                        "optional": True,
                    },
                    "protocol": {
                        "type": "string",
                        "description": (
                            "any, tcp, udp, icmp, etc. (default: 'any')"
                        ),
                        "optional": True,
                    },
                    "source_net": {
                        "type": "string",
                        "description": ("Source network/IP (default: 'any')"),
                        "optional": True,
                    },
                    "source_port": {
                        "type": "string",
                        "description": "Source port (default: 'any')",
                        "optional": True,
                    },
                    "destination_net": {
                        "type": "string",
                        "description": ("Destination network/IP (default: 'any')"),
                        "optional": True,
                    },
                    "destination_port": {
                        "type": "string",
                        "description": "Destination port (default: 'any')",
                        "optional": True,
                    },
                    "direction": {
                        "type": "string",
                        "description": "in or out (default: 'in')",
                        "optional": True,
                    },
                    "ipprotocol": {
                        "type": "string",
                        "description": "inet or inet6 (default: 'inet')",
                        "optional": True,
                    },
                    "enabled": {
                        "type": "boolean",
                        "description": "true or false (default: true)",
                        "optional": True,
                    },
                    "gateway": {
                        "type": "string",
                        "description": "Gateway to use (default: '')",
                        "optional": True,
                    },
                    "apply": {
                        "type": "boolean",
                        "description": (
                            "Whether to apply changes immediately (default: true)"
                        ),
                        "optional": True,
                    },
                },
                "required": ["description"],
            },
        },
        {
            "name": "rmfw_rule",
            "description": ("Delete a firewall rule and optionally apply changes"),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "rule_uuid": {
                        "type": "string",
                        "description": ("UUID of the rule to delete (required)"),
                    },
                    "apply": {
                        "type": "boolean",
                        "description": (
                            "Whether to apply changes immediately (default: true)"
                        ),
                        "optional": True,
                    },
                },
                "required": ["rule_uuid"],
            },
        },
        {
            "name": "interface_list",
            "description": "Get available interface names for firewall rules",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    ]
    return {"tools": tools}

@app.post("/tool/{tool_name}")
async def call_tool(tool_name: str, arguments: Dict[str, Any] = {}):
    """Call a specific tool with arguments"""
    try:
        if tool_name == "arp":
            result = await arp_tool.execute(arguments)
            return {"content": [{"type": "text", "text": str(result)}]}
        
        elif tool_name == "dhcp":
            result = await dhcp_tool.execute(arguments)
            return {"content": [{"type": "text", "text": str(result)}]}
        
        elif tool_name == "get_logs":
            logs = await firewall_logs.get_logs(
                limit=arguments.get("limit", 500),
                action=arguments.get("action"),
                src_ip=arguments.get("src_ip"),
                dst_ip=arguments.get("dst_ip"),
                protocol=arguments.get("protocol"),
            )
            return {"content": [{"type": "text", "text": str(logs)}]}
        
        elif tool_name == "lldp":
            result = await lldp_tool.execute(arguments)
            return {"content": [{"type": "text", "text": str(result)}]}
        
        elif tool_name == "system":
            result = await system_tool.execute(arguments)
            return {"content": [{"type": "text", "text": str(result)}]}
        
        elif tool_name == "fw_rules":
            result = await fw_rules_tool.execute(arguments)
            return {"content": [{"type": "text", "text": str(result)}]}
        
        elif tool_name == "mkfw_rule":
            result = await mkfw_rule_tool.execute(arguments)
            return {"content": [{"type": "text", "text": str(result)}]}
        
        elif tool_name == "rmfw_rule":
            result = await rmfw_rule_tool.execute(arguments)
            return {"content": [{"type": "text", "text": str(result)}]}
        
        elif tool_name == "interface_list":
            result = await interface_list_tool.execute(arguments)
            return {"content": [{"type": "text", "text": str(result)}]}
        
        else:
            raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
    
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error executing tool: {str(e)}")

@app.post("/jsonrpc")
async def jsonrpc_endpoint(request: JsonRpcRequest):
    """Handle JSON-RPC requests"""
    try:
        method = request.method
        params = request.params or {}
        msg_id = request.id
        
        # Handle initialize method
        if method == "initialize":
            protocol_version = params.get("protocolVersion")
            if not protocol_version or protocol_version == "undefined":
                protocol_version = "2024-11-05"
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": protocol_version,
                    "serverInfo": {"name": "opnsense-mcp", "version": "1.0.0"},
                    "capabilities": {"tools": {"listChanged": False}},
                },
            }
        
        # Handle tools/list method
        elif method in ("tools/list", "ListOfferings"):
            tools = await list_tools()
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": tools
            }
        
        # Handle tools/call method
        elif method in ("tools/call", "tool/call"):
            tool_name = params.get("name") or params.get("tool")
            arguments = params.get("arguments") or params.get("args") or {}
            
            if not tool_name:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: tool name is required",
                    },
                }
            
            try:
                result = await call_tool(tool_name, arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": result
                }
            except HTTPException as e:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601 if e.status_code == 404 else -32603,
                        "message": e.detail,
                    },
                }
        
        # Handle unknown method
        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
            }
    
    except Exception as e:
        logger.error(f"Error handling JSON-RPC request: {e}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "id": request.id,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}",
            },
        }

@app.get("/sse")
async def sse_endpoint(request: Request):
    """Server-Sent Events endpoint for real-time communication"""
    client_id = request.headers.get("X-Client-ID", str(id(request)))
    
    async def event_generator():
        try:
            # Send initial connection message
            yield {
                "event": "connected",
                "id": client_id,
                "data": json.dumps({"status": "connected", "client_id": client_id})
            }
            
            # Register this client
            client_connections[client_id] = asyncio.Queue()
            
            # Keep the connection open and send events as they come
            while True:
                # Wait for events to be added to this client's queue
                event = await client_connections[client_id].get()
                
                if event is None:  # None is our signal to close the connection
                    break
                
                yield event
        
        except asyncio.CancelledError:
            logger.info(f"Client {client_id} disconnected")
        finally:
            # Clean up when the client disconnects
            if client_id in client_connections:
                del client_connections[client_id]
    
    return EventSourceResponse(event_generator())

@app.post("/send/{client_id}")
async def send_to_client(client_id: str, data: Dict[str, Any]):
    """Send an event to a specific client"""
    if client_id not in client_connections:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not connected")
    
    event = {
        "event": data.get("event", "message"),
        "id": data.get("id", str(id(data))),
        "data": json.dumps(data.get("data", {}))
    }
    
    await client_connections[client_id].put(event)
    return {"status": "sent"}

def main():
    """Main entry point"""
    # Configure logging
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    
    # Get server configuration from environment
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8080"))
    
    # Start the server
    logger.info(f"Starting OPNsense MCP Server (SSE) on {host}:{port}")
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    main() 
