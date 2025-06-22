#!/usr/bin/env python3
"""Simple script to call the MCP system tool directly."""

import json
from typing import Any

import requests


def call_mcp_system() -> dict[str, Any] | None:
    """
    Call the MCP system tool directly.

    Returns:
        Optional[Dict[str, Any]]: Response data from the MCP system tool or None if error

    """
    url = "http://localhost:8080/api/jsonrpc"
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/execute",
        "params": {"tool": "system", "args": {"random_string": "true"}},
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        print(json.dumps(data, indent=2))
        return data
    except Exception as e:
        print(f"Error calling MCP system tool: {e}")
        return None


if __name__ == "__main__":
    call_mcp_system()
