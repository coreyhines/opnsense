#!/usr/bin/env python3
"""Test script to directly call OPNsense API for system status."""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from opnsense_mcp.utils.api import OPNsenseClient

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(Path.home() / ".opnsense-env")


async def test_system_status() -> None:
    """Test the system status API endpoint."""
    # Get environment variables
    host = os.getenv("OPNSENSE_FIREWALL_HOST")
    api_key = os.getenv("OPNSENSE_API_KEY")
    api_secret = os.getenv("OPNSENSE_API_SECRET")

    if not all([host, api_key, api_secret]):
        logger.error("Missing required environment variables")
        logger.error("OPNSENSE_FIREWALL_HOST: %s", "Set" if host else "Not set")
        logger.error("OPNSENSE_API_KEY: %s", "Set" if api_key else "Not set")
        logger.error("OPNSENSE_API_SECRET: %s", "Set" if api_secret else "Not set")
        return

    logger.info("Creating OPNsense client with host: %s", host)
    client = OPNsenseClient(
        {
            "firewall_host": host,
            "api_key": api_key,
            "api_secret": api_secret,
            "ssl_verify": False,
        }
    )

    # Try different API endpoints
    endpoints = [
        "/api/core/diagnostics/systemhealth",
        "/api/core/firmware/status",
        "/api/diagnostics/system/health",
        "/api/diagnostics/system/status",
        "/api/diagnostics/system/information",
        "/core/system/status",
    ]

    for endpoint in endpoints:
        try:
            logger.info("Testing endpoint: %s", endpoint)
            # Using internal method directly for testing purposes
            response = await client._make_request("GET", endpoint)
            logger.info("Response: %s", json.dumps(response, indent=2))
        except Exception as e:
            logger.exception("Error with endpoint %s: %s", endpoint, str(e))


if __name__ == "__main__":
    asyncio.run(test_system_status())
