#!/usr/bin/env python3
"""Test script to verify ARP, DHCP, and System tools work correctly."""

import logging
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(Path.home() / ".opnsense-env")


def get_system_status() -> dict | None:
    """
    Get system status from OPNsense API.

    Returns:
        dict: System status information or None if an error occurs

    """
    # Get environment variables
    host = os.getenv("OPNSENSE_FIREWALL_HOST")
    api_key = os.getenv("OPNSENSE_API_KEY")
    api_secret = os.getenv("OPNSENSE_API_SECRET")

    if not all([host, api_key, api_secret]):
        logger.error("Missing required environment variables")
        logger.error("OPNSENSE_FIREWALL_HOST: %s", "Set" if host else "Not set")
        logger.error("OPNSENSE_API_KEY: %s", "Set" if api_key else "Not set")
        logger.error("OPNSENSE_API_SECRET: %s", "Set" if api_secret else "Not set")
        return None

    logger.info("Getting system status from %s", host)

    # Create auth header
    auth = (api_key, api_secret)

    # Make request to firmware status endpoint
    url = f"https://{host}/api/core/firmware/status"
    try:
        response = requests.get(url, auth=auth, verify=False)
        response.raise_for_status()
        data = response.json()

        # Format and print the response
        print("\n=== OPNsense System Status ===\n")
        print(f"OPNsense Version: {data.get('product_version', 'N/A')}")
        print(f"OS Version: {data.get('os_version', 'N/A')}")
        print(f"Connection Status: {data.get('connection', 'unknown')}")
        print(f"Repository Status: {data.get('repository', 'unknown')}")
        print(f"Last Check: {data.get('last_check', 'unknown')}")

        # Extract product information
        product = data.get("product", {})
        if product:
            print("\n=== Product Information ===\n")
            print(f"Product Name: {product.get('product_name', 'OPNsense')}")
            print(f"Product Nickname: {product.get('product_nickname', '')}")
            print(f"Product Architecture: {product.get('product_arch', '')}")
            print(f"Product Copyright: {product.get('product_copyright_owner', '')}")
            print(f"Product Website: {product.get('product_website', '')}")

        return data
    except requests.exceptions.RequestException as e:
        logger.exception("Error getting system status: %s", e)
        return None


def get_arp_table() -> list | None:
    """
    Get ARP table from OPNsense API.

    Returns:
        list: ARP table entries or None if an error occurs

    """
    # Get environment variables
    host = os.getenv("OPNSENSE_FIREWALL_HOST")
    api_key = os.getenv("OPNSENSE_API_KEY")
    api_secret = os.getenv("OPNSENSE_API_SECRET")

    if not all([host, api_key, api_secret]):
        logger.error("Missing required environment variables")
        return None

    logger.info("Getting ARP table from %s", host)

    # Create auth header
    auth = (api_key, api_secret)

    # Make request to ARP endpoint
    url = f"https://{host}/api/diagnostics/interface/get_arp"
    try:
        response = requests.get(url, auth=auth, verify=False)
        response.raise_for_status()
        data = response.json()

        # Format and print the response
        print("\n=== OPNsense ARP Table ===\n")
        print(f"Found {len(data)} entries")

        # Print first 5 entries as sample
        for i, entry in enumerate(data[:5]):
            print(f"\nEntry {i+1}:")
            print(f"  IP: {entry.get('ip', 'N/A')}")
            print(f"  MAC: {entry.get('mac', 'N/A')}")
            print(f"  Interface: {entry.get('intf', 'N/A')}")
            print(f"  Hostname: {entry.get('hostname', 'N/A')}")

        return data
    except requests.exceptions.RequestException as e:
        logger.exception("Error getting ARP table: %s", e)
        return None


def get_dhcp_leases() -> list | None:
    """
    Get DHCP leases from OPNsense API.

    Returns:
        list: DHCP lease entries or None if an error occurs

    """
    # Get environment variables
    host = os.getenv("OPNSENSE_FIREWALL_HOST")
    api_key = os.getenv("OPNSENSE_API_KEY")
    api_secret = os.getenv("OPNSENSE_API_SECRET")

    if not all([host, api_key, api_secret]):
        logger.error("Missing required environment variables")
        return None

    logger.info("Getting DHCP leases from %s", host)

    # Create auth header
    auth = (api_key, api_secret)

    # Make request to DHCP endpoint
    url = f"https://{host}/api/dhcpv4/leases/search_lease"
    try:
        response = requests.get(url, auth=auth, verify=False)
        response.raise_for_status()
        data = response.json()

        # Format and print the response
        print("\n=== OPNsense DHCP Leases ===\n")

        # Check different response formats
        if isinstance(data, dict):
            if "rows" in data:
                leases = data["rows"]
            elif "leases" in data:
                leases = data["leases"]
            else:
                leases = []
        elif isinstance(data, list):
            leases = data
        else:
            leases = []

        print(f"Found {len(leases)} leases")

        # Print first 5 entries as sample
        for i, lease in enumerate(leases[:5]):
            print(f"\nLease {i+1}:")
            ip_addr = lease.get("ip", lease.get("address", "N/A"))
            hostname = lease.get("hostname", lease.get("client-hostname", "N/A"))
            print(f"  IP: {ip_addr}")
            print(f"  MAC: {lease.get('mac', 'N/A')}")
            print(f"  Hostname: {hostname}")
            print(f"  Status: {'Online' if lease.get('online') else 'Offline'}")

        return leases
    except requests.exceptions.RequestException as e:
        logger.exception("Error getting DHCP leases: %s", e)
        return None


def main() -> None:
    """Run all tests."""
    print("\n=== Testing System Status ===")
    system_status = get_system_status()

    print("\n=== Testing ARP Table ===")
    arp_table = get_arp_table()

    print("\n=== Testing DHCP Leases ===")
    dhcp_leases = get_dhcp_leases()

    # Summary
    print("\n=== Test Summary ===")
    print(f"System Status: {'Success' if system_status else 'Failed'}")
    print(f"ARP Table: {'Success' if arp_table else 'Failed'}")
    print(f"DHCP Leases: {'Success' if dhcp_leases else 'Failed'}")


if __name__ == "__main__":
    main()
