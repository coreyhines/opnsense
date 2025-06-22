#!/usr/bin/env python3

import logging
from typing import Any

from pydantic import BaseModel

from opnsense_mcp.utils.oui_lookup import OUILookup

logger = logging.getLogger(__name__)

oui_lookup = OUILookup()


class ARPEntry(BaseModel):
    """Model for ARP/NDP table entries"""

    mac: str
    ip: str
    intf: str
    manufacturer: str | None = None
    hostname: str | None = None
    expires: int | None = None
    permanent: bool | None = None
    type: str | None = None
    description: str | None = None
    dhcp_status: str | None = None  # Added field for DHCP status


class ARPTool:
    name = "arp"
    description = "Show ARP/NDP table"
    inputSchema = {"type": "object", "properties": {}, "required": []}

    def __init__(self, client):
        self.client = client

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute ARP/NDP table lookup with optional filtering by MAC,
        IPv4, or IPv6 address, or using targeted search if 'search'
        is provided. If 'search' is a hostname, resolve to IP(s) first.
        """
        try:
            if self.client is None:
                logger.warning("No OPNsense client available, returning dummy data")
                return self._get_dummy_data()

            # Get DHCP leases for cross-referencing
            dhcpv4_leases = await self.client.get_dhcpv4_leases()
            dhcpv6_leases = await self.client.get_dhcpv6_leases()

            # Create lookup dictionaries for quick access
            dhcp_ip_map = {}
            dhcp_mac_map = {}

            # Process DHCPv4 leases
            for lease in dhcpv4_leases:
                ip = lease.get("ip") or lease.get("address")
                mac = lease.get("mac")
                if ip:
                    dhcp_ip_map[ip] = lease
                if mac:
                    dhcp_mac_map[mac.lower()] = lease

            # Process DHCPv6 leases
            for lease in dhcpv6_leases:
                ip = lease.get("ip") or lease.get("address")
                mac = lease.get("mac")
                if ip:
                    dhcp_ip_map[ip] = lease
                if mac:
                    dhcp_mac_map[mac.lower()] = lease

            search_query = params.get("search")
            if search_query:
                # If wildcard or empty, use canonical endpoint for full table
                if search_query.strip() == "*" or not search_query.strip():
                    arp_data = await self.client.get_arp_table()
                    ndp_data = await self.client.get_ndp_table()
                    arp_entries = [
                        self._fill_manufacturer_and_dhcp(
                            ARPEntry(**entry).model_dump(), dhcp_ip_map, dhcp_mac_map
                        )
                        for entry in arp_data
                    ]
                    ndp_entries = [
                        self._fill_manufacturer_and_dhcp(
                            ARPEntry(**entry).model_dump(), dhcp_ip_map, dhcp_mac_map
                        )
                        for entry in ndp_data
                    ]
                    return {
                        "arp": arp_entries,
                        "ndp": ndp_entries,
                        "status": "success",
                    }
                # Otherwise, fetch full tables and match in Python
                resolved_ips = set()
                resolved_macs = set()
                resolved_hostnames = set()
                resolved_queries = set()
                if hasattr(self.client, "resolve_host_info"):
                    info = await self.client.resolve_host_info(search_query)
                    logger.debug(
                        f"[ARPTool] resolve_host_info({search_query!r}) -> {info}"
                    )
                    if info.get("ip"):
                        resolved_ips.add(info["ip"])
                    if info.get("mac"):
                        resolved_macs.add(info["mac"])
                    if info.get("hostname"):
                        resolved_hostnames.add(info["hostname"])
                    if info.get("dhcpv4"):
                        dhcp = info["dhcpv4"]
                        if dhcp.get("ip") or dhcp.get("address"):
                            resolved_ips.add(dhcp.get("ip") or dhcp.get("address"))
                        if dhcp.get("mac"):
                            resolved_macs.add(dhcp["mac"])
                        if dhcp.get("hostname") or dhcp.get("client-hostname"):
                            resolved_hostnames.add(
                                dhcp.get("hostname") or dhcp.get("client-hostname")
                            )
                    resolved_queries.add(search_query)
                else:
                    resolved_queries.add(search_query)
                all_queries = {
                    q.lower()
                    for q in (
                        resolved_queries
                        | resolved_ips
                        | resolved_macs
                        | resolved_hostnames
                    )
                    if q
                }
                logger.debug(
                    f"[ARPTool] In-memory ARP/NDP search queries: {all_queries}"
                )
                arp_data = await self.client.get_arp_table()
                ndp_data = await self.client.get_ndp_table()

                def match_any(entry):
                    return any(
                        q in str(entry.get("ip", "")).lower()
                        or q in str(entry.get("mac", "")).lower()
                        or q in str(entry.get("hostname", "")).lower()
                        for q in all_queries
                    )

                arp_entries = [
                    self._fill_manufacturer_and_dhcp(
                        ARPEntry(**entry).model_dump(), dhcp_ip_map, dhcp_mac_map
                    )
                    for entry in arp_data
                    if match_any(entry)
                ]
                ndp_entries = [
                    self._fill_manufacturer_and_dhcp(
                        ARPEntry(**entry).model_dump(), dhcp_ip_map, dhcp_mac_map
                    )
                    for entry in ndp_data
                    if match_any(entry)
                ]
                return {
                    "arp": arp_entries,
                    "ndp": ndp_entries,
                    "status": "success",
                }

            # If no search query, get full tables
            arp_data = await self.client.get_arp_table()
            ndp_data = await self.client.get_ndp_table()
            arp_entries = [
                self._fill_manufacturer_and_dhcp(
                    ARPEntry(**entry).model_dump(), dhcp_ip_map, dhcp_mac_map
                )
                for entry in arp_data
            ]
            ndp_entries = [
                self._fill_manufacturer_and_dhcp(
                    ARPEntry(**entry).model_dump(), dhcp_ip_map, dhcp_mac_map
                )
                for entry in ndp_data
            ]

            # Filtering logic
            mac_filter = params.get("mac")
            ip_filter = params.get("ip")
            ipv6_filter = params.get("ipv6")

            if mac_filter:
                mac_filter = mac_filter.lower()
                arp_entries = [
                    entry
                    for entry in arp_entries
                    if entry.get("mac", "").lower() == mac_filter
                ]
                ndp_entries = [
                    entry
                    for entry in ndp_entries
                    if entry.get("mac", "").lower() == mac_filter
                ]
            if ip_filter:
                arp_entries = [
                    entry for entry in arp_entries if entry.get("ip", "") == ip_filter
                ]
            if ipv6_filter:
                ndp_entries = [
                    entry for entry in ndp_entries if entry.get("ip", "") == ipv6_filter
                ]

        except Exception as e:
            logger.exception("Failed to get ARP/NDP tables")
            logger.error(f"Exception details: {e}")
            # Fallback to dummy data on error
            return self._get_dummy_data()
        else:
            return {
                "arp": arp_entries,
                "ndp": ndp_entries,
                "status": "success",
            }

    def _fill_manufacturer_and_dhcp(self, entry, dhcp_ip_map, dhcp_mac_map):
        # Fill manufacturer info
        if not entry.get("manufacturer"):
            mac = entry.get("mac")
            if mac:
                entry["manufacturer"] = oui_lookup.lookup(mac) or ""

        # Add DHCP information if available
        ip = entry.get("ip")
        mac = entry.get("mac", "").lower() if entry.get("mac") else None

        # Try to find DHCP info by IP or MAC
        dhcp_info = None
        if ip and ip in dhcp_ip_map:
            dhcp_info = dhcp_ip_map[ip]
        elif mac and mac in dhcp_mac_map:
            dhcp_info = dhcp_mac_map[mac]

        # If DHCP info found, add relevant details
        if dhcp_info:
            # Add hostname if missing
            if not entry.get("hostname") and (
                dhcp_info.get("hostname") or dhcp_info.get("client-hostname")
            ):
                entry["hostname"] = dhcp_info.get("hostname") or dhcp_info.get(
                    "client-hostname"
                )

            # Add DHCP status
            entry["dhcp_status"] = "Online" if dhcp_info.get("online") else "Offline"

        return entry

    def _get_dummy_data(self) -> dict[str, Any]:
        """Return dummy data for testing"""
        return {
            "arp": [
                {
                    "ip": "192.168.1.1",
                    "mac": "aa:bb:cc:dd:ee:ff",
                    "intf": "em0",
                    "manufacturer": "TestCorp",
                    "dhcp_status": "Online",
                }
            ],
            "ndp": [
                {
                    "ip": "fe80::1",
                    "mac": "aa:bb:cc:dd:ee:ff",
                    "intf": "em0",
                    "manufacturer": "TestCorp",
                    "dhcp_status": "Online",
                }
            ],
            "status": "success",
        }
