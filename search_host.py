#!/usr/bin/env python3
"""Script to search for a specific hostname in ARP and DHCP tables."""

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


def search_host(hostname):
    """
    Search for a specific hostname in ARP and DHCP tables.

    Args:
        hostname: Hostname to search for

    """
    # Get environment variables
    host = os.getenv("OPNSENSE_FIREWALL_HOST")
    api_key = os.getenv("OPNSENSE_API_KEY")
    api_secret = os.getenv("OPNSENSE_API_SECRET")

    if not all([host, api_key, api_secret]):
        logger.error("Missing required environment variables")
        return

    # Create auth header
    auth = (api_key, api_secret)

    # Store ARP entries for cross-referencing
    arp_entries = []
    arp_ips = set()
    arp_macs = set()

    # Search ARP table
    logger.info(f"Searching ARP table for {hostname}")
    arp_url = f"https://{host}/api/diagnostics/interface/get_arp"

    try:
        response = requests.get(arp_url, auth=auth, verify=False)
        response.raise_for_status()
        arp_data = response.json()

        # Store all ARP entries for cross-referencing
        for entry in arp_data:
            if entry.get("ip"):
                arp_ips.add(entry.get("ip"))
            if entry.get("mac"):
                arp_macs.add(entry.get("mac"))
            arp_entries.append(entry)

        # Filter for hostname
        matches = [
            entry
            for entry in arp_data
            if hostname.lower() in str(entry.get("hostname", "")).lower()
        ]

        if matches:
            print(f"\n=== ARP matches for {hostname} ===\n")
            for entry in matches:
                print(f"IP: {entry.get('ip', 'N/A')}")
                print(f"MAC: {entry.get('mac', 'N/A')}")
                print(f"Interface: {entry.get('intf', 'N/A')}")
                print(f"Hostname: {entry.get('hostname', 'N/A')}")
                print()
        else:
            print(f"No ARP matches found for {hostname}")

        # Now let's check all ARP entries for any clues
        print("\n=== Checking all ARP entries for possible matches ===\n")
        for entry in arp_data:
            if entry.get("hostname"):
                print(
                    f"Hostname: {entry.get('hostname')} - IP: {entry.get('ip')} - MAC: {entry.get('mac')}"
                )

    except requests.exceptions.RequestException as e:
        logger.exception(f"Error searching ARP table: {e}")

    # Search DHCP leases
    logger.info(f"Searching DHCP leases for {hostname}")
    dhcp_url = f"https://{host}/api/dhcpv4/leases/search_lease"

    try:
        response = requests.get(dhcp_url, auth=auth, verify=False)
        response.raise_for_status()
        dhcp_data = response.json()

        # Extract leases from different response formats
        if isinstance(dhcp_data, dict):
            if "rows" in dhcp_data:
                leases = dhcp_data["rows"]
            elif "leases" in dhcp_data:
                leases = dhcp_data["leases"]
            else:
                leases = []
        elif isinstance(dhcp_data, list):
            leases = dhcp_data
        else:
            leases = []

        # Filter for hostname
        matches = [
            lease
            for lease in leases
            if hostname.lower() in str(lease.get("hostname", "")).lower()
            or hostname.lower() in str(lease.get("client-hostname", "")).lower()
        ]

        if matches:
            print(f"\n=== DHCP matches for {hostname} ===\n")
            for lease in matches:
                # Get IP and MAC
                ip = lease.get("ip", lease.get("address", "N/A"))
                mac = lease.get("mac", "N/A")

                # Cross-reference with ARP table to determine true online status
                # If the IP or MAC is in the ARP table, the device is online regardless of DHCP status
                is_in_arp = (ip in arp_ips) or (mac in arp_macs)

                # Use ARP presence to override DHCP status if needed
                online_status = (
                    "Online"
                    if is_in_arp
                    else ("Online" if lease.get("online") else "Offline")
                )

                print(f"IP: {ip}")
                print(f"MAC: {mac}")
                print(
                    f"Hostname: {lease.get('hostname', lease.get('client-hostname', 'N/A'))}"
                )
                print(f"Status: {online_status}")
                if is_in_arp and not lease.get("online"):
                    print("Note: Device appears in ARP table but DHCP shows offline")
                print()
        else:
            print(f"No DHCP matches found for {hostname}")

        # Now let's check all DHCP entries for any clues
        print("\n=== Checking all DHCP leases for possible matches ===\n")
        for lease in leases:
            hostname = lease.get("hostname", lease.get("client-hostname", ""))
            if hostname:
                print(
                    f"Hostname: {hostname} - IP: {lease.get('ip', lease.get('address', 'N/A'))} - MAC: {lease.get('mac', 'N/A')}"
                )

    except requests.exceptions.RequestException as e:
        logger.exception(f"Error searching DHCP leases: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python search_host.py <hostname>")
        sys.exit(1)

    hostname = sys.argv[1]
    search_host(hostname)
