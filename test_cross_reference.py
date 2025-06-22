#!/usr/bin/env python3
"""Test script to verify the cross-referencing between ARP and DHCP tools."""

import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from opnsense_mcp.tools.arp import ARPTool
from opnsense_mcp.tools.dhcp import DHCPTool
from opnsense_mcp.utils.api import OPNsenseClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(Path.home() / ".opnsense-env")


async def test_cross_reference():
    """Test the cross-referencing between ARP and DHCP tools."""
    # Get environment variables
    host = os.getenv("OPNSENSE_FIREWALL_HOST")
    api_key = os.getenv("OPNSENSE_API_KEY")
    api_secret = os.getenv("OPNSENSE_API_SECRET")

    if not all([host, api_key, api_secret]):
        logger.error("Missing required environment variables")
        return

    # Initialize OPNsense client
    client = OPNsenseClient(
        {
            "firewall_host": host,
            "api_key": api_key,
            "api_secret": api_secret,
            "ssl_verify": False,
        }
    )

    # Initialize tools
    arp_tool = ARPTool(client)
    dhcp_tool = DHCPTool(client)

    # Test DHCP tool with cross-referencing
    logger.info("Testing DHCP tool with cross-referencing...")
    dhcp_result = await dhcp_tool.execute({})

    # Print DHCPv4 leases with actual status
    print("\n=== DHCPv4 Leases with Cross-Referenced Status ===\n")
    for lease in dhcp_result.get("dhcpv4", []):
        if lease.get("hostname"):
            print(f"Hostname: {lease.get('hostname')}")
            print(f"IP: {lease.get('ip')}")
            print(f"MAC: {lease.get('mac')}")
            print(f"DHCP Status: {'Online' if lease.get('online') else 'Offline'}")
            print(f"Actual Status: {lease.get('actual_status')}")
            if lease.get("actual_status") != (
                "Online" if lease.get("online") else "Offline"
            ):
                print("Note: Status discrepancy detected!")
            print()

    # Test ARP tool with DHCP information
    logger.info("Testing ARP tool with DHCP information...")
    arp_result = await arp_tool.execute({})

    # Print ARP entries with DHCP status
    print("\n=== ARP Entries with DHCP Status ===\n")
    for entry in arp_result.get("arp", []):
        if entry.get("hostname"):
            print(f"Hostname: {entry.get('hostname')}")
            print(f"IP: {entry.get('ip')}")
            print(f"MAC: {entry.get('mac')}")
            print(f"Interface: {entry.get('intf')}")
            print(f"DHCP Status: {entry.get('dhcp_status', 'N/A')}")
            print()

    # Test specific host (trogdor)
    logger.info("Testing specific host (trogdor)...")

    # Search in DHCP
    dhcp_trogdor = await dhcp_tool.execute({"search": "trogdor"})

    # Search in ARP
    arp_trogdor = await arp_tool.execute({"search": "trogdor"})

    # Print trogdor's information
    print("\n=== Trogdor's Information ===\n")

    # From DHCP
    for lease in dhcp_trogdor.get("dhcpv4", []):
        if "trogdor" in str(lease.get("hostname", "")).lower():
            print("DHCP Information:")
            print(f"Hostname: {lease.get('hostname')}")
            print(f"IP: {lease.get('ip')}")
            print(f"MAC: {lease.get('mac')}")
            print(f"DHCP Status: {'Online' if lease.get('online') else 'Offline'}")
            print(f"Actual Status: {lease.get('actual_status')}")
            print()

    # From ARP
    for entry in arp_trogdor.get("arp", []):
        if "trogdor" in str(entry.get("hostname", "")).lower():
            print("ARP Information:")
            print(f"Hostname: {entry.get('hostname')}")
            print(f"IP: {entry.get('ip')}")
            print(f"MAC: {entry.get('mac')}")
            print(f"Interface: {entry.get('intf')}")
            print(f"DHCP Status: {entry.get('dhcp_status', 'N/A')}")
            print()


if __name__ == "__main__":
    asyncio.run(test_cross_reference())
