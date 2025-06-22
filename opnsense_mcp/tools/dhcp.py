#!/usr/bin/env python3

import logging
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DHCPLease(BaseModel):
    ip: str
    mac: str
    hostname: str | None = None
    start: str | None = None
    end: str | None = None
    online: bool | None = None
    lease_type: str | None = None
    description: str | None = None
    actual_status: str | None = None  # Added field for cross-referenced status


class DHCPTool:
    name = "dhcp"
    description = "Show DHCPv4 and DHCPv6 lease tables"
    inputSchema = {"type": "object", "properties": {}, "required": []}

    def __init__(self, client):
        self.client = client

    def _normalize_lease_entry(self, entry):
        # Map 'address' to 'ip' if present
        if "address" in entry and "ip" not in entry:
            entry["ip"] = entry.pop("address")
        return entry

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute DHCP lease table lookup for both IPv4 and IPv6"""
        try:
            if self.client is None:
                logger.warning(
                    "No OPNsense client available, returning dummy DHCP data"
                )
                return self._get_dummy_data()

            # Get DHCP leases
            leases_v4 = await self.client.get_dhcpv4_leases()
            leases_v6 = await self.client.get_dhcpv6_leases()

            # Get ARP and NDP tables for cross-referencing
            arp_data = await self.client.get_arp_table()
            ndp_data = await self.client.get_ndp_table()

            # Create sets of IPs and MACs in ARP/NDP tables for quick lookup
            arp_ips = {entry.get("ip") for entry in arp_data if entry.get("ip")}
            arp_macs = {entry.get("mac") for entry in arp_data if entry.get("mac")}
            ndp_ips = {entry.get("ip") for entry in ndp_data if entry.get("ip")}
            ndp_macs = {entry.get("mac") for entry in ndp_data if entry.get("mac")}

            # Process DHCP leases with cross-referenced status
            lease_entries_v4 = []
            for entry in leases_v4:
                normalized = self._normalize_lease_entry(entry)

                # Cross-reference with ARP table to determine true online status
                ip = normalized.get("ip")
                mac = normalized.get("mac")
                is_in_arp = (ip in arp_ips) or (mac in arp_macs)

                # Use ARP presence to override DHCP status if needed
                dhcp_status = normalized.get("online", False)
                actual_status = (
                    "Online" if is_in_arp else ("Online" if dhcp_status else "Offline")
                )
                normalized["actual_status"] = actual_status

                lease_entries_v4.append(DHCPLease(**normalized).model_dump())

            # Process DHCPv6 leases with cross-referenced status
            lease_entries_v6 = []
            for entry in leases_v6:
                normalized = self._normalize_lease_entry(entry)

                # Cross-reference with NDP table to determine true online status
                ip = normalized.get("ip")
                mac = normalized.get("mac")
                is_in_ndp = (ip in ndp_ips) or (mac in ndp_macs)

                # Use NDP presence to override DHCP status if needed
                dhcp_status = normalized.get("online", False)
                actual_status = (
                    "Online" if is_in_ndp else ("Online" if dhcp_status else "Offline")
                )
                normalized["actual_status"] = actual_status

                lease_entries_v6.append(DHCPLease(**normalized).model_dump())

            # Determine status
            if leases_v4 is None and leases_v6 is None:
                dhcp_status = (
                    "API returned nothing (possible misconfiguration or "
                    "permissions issue)"
                )
            elif not lease_entries_v4 and not lease_entries_v6:
                dhcp_status = (
                    "No DHCP leases found. Check DHCP server status, "
                    "configuration, and API permissions."
                )
            else:
                dhcp_status = "OK"
        except Exception as e:
            logger.exception("Failed to get DHCP lease tables")
            return {
                "dhcpv4": [],
                "dhcpv6": [],
                "status": "error",
                "dhcp_status": f"Error retrieving DHCP leases: {str(e)}",
            }
        else:
            return {
                "dhcpv4": lease_entries_v4,
                "dhcpv6": lease_entries_v6,
                "status": "success",
                "dhcp_status": dhcp_status,
            }

    def _get_dummy_data(self):
        return {
            "dhcpv4": [
                {
                    "ip": "192.168.1.100",
                    "mac": "00:11:22:33:44:55",
                    "hostname": "dummy-client",
                    "start": ("2025-01-01T00:00:00"),
                    "end": ("2025-01-01T12:00:00"),
                    "online": True,
                    "actual_status": "Online",
                    "lease_type": "dynamic",
                    "description": ("Dummy lease entry"),
                }
            ],
            "dhcpv6": [
                {
                    "ip": "2001:db8::100",
                    "mac": "00:11:22:33:44:66",
                    "hostname": "dummy6-client",
                    "start": ("2025-01-01T00:00:00"),
                    "end": ("2025-01-01T12:00:00"),
                    "online": True,
                    "actual_status": "Online",
                    "lease_type": "dynamic",
                    "description": ("Dummy DHCPv6 lease entry"),
                }
            ],
            "status": "dummy",
        }
