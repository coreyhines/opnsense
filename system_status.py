#!/usr/bin/env python3
"""Simple script to get system status from OPNsense."""

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
    handlers=[logging.StreamHandler(sys.stdout)]
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
        
        # Check for updates
        updates = data.get("upgrade_packages", [])
        if updates:
            print("\n=== Updates Available ===\n")
            print(f"Number of updates: {len(updates)}")
            print(f"Needs reboot: {'Yes' if data.get('needs_reboot') == '1' else 'No'}")
        else:
            print("\nNo updates available.")

        return data
    except requests.exceptions.RequestException as e:
        logger.exception("Error getting system status: %s", e)
        return None

if __name__ == "__main__":
    get_system_status()
