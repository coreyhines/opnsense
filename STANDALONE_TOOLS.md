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
- Product information

### ARP Table

You can use the `test_all_tools.py` script to retrieve the ARP table:

```bash
python test_all_tools.py
```

This will show:
- Number of ARP entries
- Sample entries with IP, MAC, interface, and hostname

### DHCP Leases

The same `test_all_tools.py` script can be used to retrieve DHCP leases:

```bash
python test_all_tools.py
```

This will display:
- Number of DHCP leases
- Sample leases with IP, MAC, hostname, and status

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
