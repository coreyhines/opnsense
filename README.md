# OPNsense MCP Server

This server provides OPNsense API functionality through a Model Context Protocol
(MCP) interface (JSON-RPC over stdio), not HTTP REST endpoints.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

1. Configure your OPNsense credentials in a `.env` file (in the project root) or
   in `~/.opnsense-env`:

```env
OPNSENSE_API_KEY=your_api_key
OPNSENSE_API_SECRET=your_api_secret
OPNSENSE_API_HOST=your.opnsense.host
MCP_SECRET_KEY=your_jwt_secret_key
```

You can use a `.env` file in the project root, or set these in your shell
environment. The server will automatically load from `~/.opnsense-env` if present.

## Running the Server

Start the server with:

```bash
python main.py
```

## New SSE-Based Server (Beta)

We've added a new server implementation that uses Server-Sent Events (SSE) instead
of STDIO for communication. This allows for real-time bidirectional communication
over HTTP, making it easier to integrate with web applications and services.

### Running the SSE Server

Start the SSE server with:

```bash
python main_sse.py --host 127.0.0.1 --port 8080
```

### SSE Server Features

- HTTP-based communication with JSON-RPC and REST endpoints
- Real-time bidirectional communication using Server-Sent Events
- Support for multiple concurrent clients
- Compatible with existing MCP tools and clients
- Web browser integration

### Example SSE Clients

We provide two example clients for the SSE server:

1. Python client: `examples/sse_client.py`
2. Web browser client: `examples/sse_client.html`

To run the Python client:

```bash
python examples/sse_client.py --server http://127.0.0.1:8080 --tool system
```

To use the web client, open `examples/sse_client.html` in a web browser.

## IDE Integration

- The server is designed for integration with Cursor IDE and other MCP-compatible
  IDEs.
- The STDIO-based server is compatible with existing MCP clients.
- The SSE-based server can be used with any HTTP client or SSE-compatible
  application.

## Available Tools

The following tools are available:

1. `get_logs` - Get firewall logs with optional filtering
2. `arp` - Show ARP/NDP table
3. `dhcp` - Show DHCP lease information
4. `lldp` - Show LLDP neighbor table
5. `system` - Show system status information
6. `fw_rules` - Get the current firewall rule set
7. `mkfw_rule` - Create a new firewall rule
8. `rmfw_rule` - Delete a firewall rule
9. `interface_list` - Get available interface names for firewall rules

## Tool Usage Examples

### Get Firewall Logs

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "tools/call",
  "params": {
    "name": "get_logs",
    "arguments": {
      "limit": 5,
      "action": "block"
    }
  }
}
```

### Show ARP Table

```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "method": "tools/call",
  "params": {
    "name": "arp",
    "arguments": {
      "search": "192.168.1.1"
    }
  }
}
```

### Show DHCP Leases

```json
{
  "jsonrpc": "2.0",
  "id": "3",
  "method": "tools/call",
  "params": {
    "name": "dhcp",
    "arguments": {}
  }
}
```

## Security Notes

- Always store API credentials in `.env` files or environment variables, not in
  code.
- For production use, generate a secure random string for `MCP_SECRET_KEY`.
- The SSE server uses CORS headers that allow all origins by default. In
  production, restrict this to specific allowed origins.

## Development

For development information, see the `docs/PROJECT_GUIDE.md` file.

## Example MCP Tool Output

Here are some example queries and anonymized responses you might see when
interacting with the MCP server via a chat interface:

---

**User:** Tell me about hostA.

**MCP Response:**
Host: `hostA`
IP Address: `192.168.1.42`
MAC Address: `AA:BB:CC:DD:EE:01`
DHCP Lease: Active (expires in 2 hours)
ARP Entry: Present
LLDP Neighbor: Not detected

---

**User:** What is the hostname for this MAC address: `AA:BB:CC:DD:EE:02`?

**MCP Response:**
MAC Address: `AA:BB:CC:DD:EE:02`
Hostname: `printer-01`
IP Address: `192.168.1.55`
DHCP Lease: Active (expires in 1 day)
ARP Entry: Present

---

**User:** List all devices currently on the network.

**MCP Response:**

1. Hostname: `hostA`, IP: `192.168.1.42`, MAC: `AA:BB:CC:DD:EE:01`
2. Hostname: `printer-01`, IP: `192.168.1.55`, MAC: `AA:BB:CC:DD:EE:02`
3. Hostname: `laptop-guest`, IP: `192.168.1.77`, MAC: `AA:BB:CC:DD:EE:03`

---

**User:** Show me the current system status.

**MCP Response:**
CPU Usage: 12%
Memory Usage: 1.2 GB / 8 GB
Filesystem Usage: 40% used
Uptime: 5 days, 3 hours

---

**User:** Who is using IP address `192.168.1.77`?

**MCP Response:**
IP Address: `192.168.1.77`
Hostname: `laptop-guest`
MAC Address: `AA:BB:CC:DD:EE:03`
DHCP Lease: Expired
ARP Entry: Present

---

**User:** Show me recent firewall logs for host `hostA`.

**MCP Response:**
Recent firewall log entries for `hostA` (`192.168.1.42`):

| Time       | Action | Source IP    | Dest IP     | Protocol | Port |
|------------|--------|--------------|-------------|----------|------|
| 2024-06-20 | Block  | 192.168.1.42 | 8.8.8.8     | UDP      | 53   |
| 2024-06-20 | Pass   | 192.168.1.42 | 192.168.1.1 | TCP      | 443  |
| 2024-06-20 | Pass   | 192.168.1.42 | 10.0.0.5    | TCP      | 22   |

---

**User:** Show LLDP neighbors.

**MCP Response:**
No LLDP neighbors detected.

## Troubleshooting

- **Import errors**: Ensure all dependencies are installed
- **Port conflicts**: Change the port in your config or launch arguments
- **Missing dependencies**: Install the missing package
- **Authentication fails**: Check your environment and credentials

## Verification

- All core functionality and tests should pass after cleanup
- Project is ready for further development

## Notes

- For production, always use the main server with all dependencies installed
- The server communicates via MCP protocol (JSON-RPC over stdio), not HTTP
  REST endpoints
- Podman is the preferred container runtime
- Use vi/vim for editing; VS Code is supported as an IDE only
- Always clean up temporary and test files (use `tmp_` or `test_` prefixes)
- Store all secrets in `.env` or a secure store, never in code
