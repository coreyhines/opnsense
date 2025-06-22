#!/usr/bin/env python3
"""
OPNsense MCP Server entry point for SSE-based communication.

This module provides a simple entry point for running the OPNsense MCP server
with Server-Sent Events (SSE) instead of STDIO.
"""

import argparse
import os

from opnsense_mcp.server_sse import main as mcp_sse_main
from opnsense_mcp.utils.logging import setup_logging


def main() -> None:
    """
    Start the OPNsense MCP Server with SSE.

    This function parses command line arguments and starts the MCP server.
    The server communicates over HTTP with Server-Sent Events (SSE).
    """
    parser = argparse.ArgumentParser(description="OPNsense MCP Server (SSE)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    parser.add_argument("--log-file", type=str, help="Path to log file (optional)")
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_file, args.log_level)

    # Set environment variables
    os.environ["HOST"] = args.host
    os.environ["PORT"] = str(args.port)
    
    # Set environment variable for JWT secret key if not set
    if not os.environ.get("MCP_SECRET_KEY"):
        # NOTE: Hardcoded secret key for development only. Change in production!
        # Bandit: # nosec
        os.environ["MCP_SECRET_KEY"] = (
            "development-secret-key"  # pragma: allowlist secret
        )

    # Set up MCP environment
    os.environ["PYTHONUNBUFFERED"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["MCP_TRANSPORT"] = "sse"

    # Run the MCP SSE server
    mcp_sse_main()


if __name__ == "__main__":
    main() 
