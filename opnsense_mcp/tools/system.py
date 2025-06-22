#!/usr/bin/env python3
"""System tool for retrieving OPNsense system status information."""

import logging
from typing import Any

from pydantic import BaseModel

from opnsense_mcp.utils.mock_api import MockOPNsenseClient

logger = logging.getLogger(__name__)


class SystemStatus(BaseModel):
    """Model for system status data."""

    cpu_usage: float
    memory_usage: float
    filesystem_usage: dict[str, float]
    uptime: str
    versions: dict[str, str]


class SystemTool:
    """Tool for retrieving system status information from OPNsense."""

    def __init__(self, client: Any) -> None:
        """
        Initialize the SystemTool.

        Args:
            client: OPNsense API client

        """
        self.client = client

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute system status check.

        Note: If this tool is unstable or the MCP server keeps terminating,
        consider using the standalone system_status.py script instead.
        See STANDALONE_TOOLS.md for more information.

        Args:
            params: Parameters for the system status check

        Returns:
            Dict containing system status information

        """
        try:
            logger.info("SystemTool.execute called with params: %s", params)
            logger.info("Client type: %s", type(self.client).__name__)

            if self.client is None or isinstance(self.client, MockOPNsenseClient):
                logger.warning(
                    "No real OPNsense client available, returning mock "
                    "system status data"
                )

            logger.info("Calling client.get_system_status()")
            result = await self.client.get_system_status()
            logger.info("Result from get_system_status: %s", result)
            return result
        except Exception as e:
            logger.exception("Failed to get system status: %s", e)
            return {
                "error": f"Failed to get system status: {str(e)}",
                "status": "error",
            }
