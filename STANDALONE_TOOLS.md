# OPNsense Standalone Tools

This document describes how to use the OPNsense tools directly without relying on the MCP server, which can sometimes be unstable.

## Environment Setup

Before using any of the tools, make sure you have the following environment variables set in `~/.opnsense-env`:

```bash
OPNSENSE_FIREWALL_HOST=your.opnsense.host
OPNSENSE_API_KEY=your_api_key
OPNSENSE_API_SECRET=your_api_secret
OPNSENSE_SSL_VERIFY=false  # Set to true if you have valid SSL certificates
```

## Available Standalone Tools

### System Status

The `system_status.py` script provides system information from your OPNsense firewall:

```bash
python system_status.py
```

This will display:
- OPNsense version
- OS version
- Connection status
- Repository status
- Product info

### ARP/NDP Table

The `search_host.py` script allows you to search for hosts in both the ARP/NDP tables and DHCP leases:

```bash
python search_host.py <hostname_or_ip_or_mac>
```

Use `*` as the search term to get all entries:

```bash
python search_host.py "*"
```

### Cross-Referenced Host Status

The updated tools now cross-reference ARP and DHCP data to provide more accurate device status information. This addresses the issue where DHCP might show a device as offline when it's actually online and present in the ARP table.

To test this functionality, you can use:

```bash
python test_cross_reference.py
```

This will:
1. Show DHCP leases with both the reported DHCP status and the actual status based on ARP presence
2. Show ARP entries with DHCP status information when available
3. Specifically test for the host "trogdor" in both tables

#### Status Discrepancy Detection

The tools will now detect and report when there's a discrepancy between the DHCP reported status and the actual network status based on ARP table presence. This is useful for:

- Identifying devices that are online but reported as offline in DHCP
- Finding "ghost" devices that appear in DHCP but are no longer on the network
- Getting a more accurate picture of your network's current state

## Using with the MCP Server

If you prefer to use the MCP server, these improvements have also been integrated into the ARP and DHCP tools. The server will provide the cross-referenced status information when you use the MCP tools.

## Testing All Tools

To test all tools at once, run:

```bash
python test_all_tools.py
```

This will run tests for System Status, ARP Table, and DHCP Leases, and provide a summary of the results.

## Future Improvements

In future versions, we plan to:

1. Implement an SSE (Server-Sent Events) approach for more reliable communication
2. Create dedicated standalone scripts for each tool
3. Improve error handling and reporting
4. Add more filtering options for the tools

## Troubleshooting

If you encounter issues:

1. Check that your environment variables are correctly set
2. Verify your OPNsense API credentials
3. Check that your OPNsense firewall is accessible
4. Ensure you have the required API permissions in OPNsense
5. Check the SSL certificate if you're using SSL verification 
