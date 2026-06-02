#!/usr/bin/env python3
"""
Certbot DNS-01 Challenge Helper using ISPConfig API
Creates and removes DNS TXT records for Let's Encrypt validation
"""

import json
import time
import logging
from pathlib import Path
from ispconfig_api import ISPConfigAPI

# Configuration paths
CONFIG_DIR = Path("/etc/dynipv6")
CONFIG_FILE = CONFIG_DIR / "config.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config():
    """Load ISPConfig credentials from config.json"""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_FILE}")

    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


def get_api_client(config):
    """Create ISPConfigAPI client"""
    return ISPConfigAPI(
        url=config['ispconfig_url'],
        username=config['ispconfig_username'],
        password=config['ispconfig_password'],
        client_id=config.get('ispconfig_client_id', '0'),
        verify_ssl=config.get('ispconfig_verify_ssl', False)
    )


def create_txt_record(domain, validation_token):
    """
    Create DNS TXT record for ACME validation
    
    Args:
        domain: Domain name (e.g., example.com)
        validation_token: Token from Let's Encrypt
    
    Returns:
        Record ID or None on failure
    """
    try:
        config = load_config()
        api = get_api_client(config)

        # TXT record name for DNS-01 challenge
        txt_record_name = f"_acme-challenge.{domain}"
        
        logger.info(f"Creating TXT record: {txt_record_name} = {validation_token}")

        # Use ISPConfig API to create TXT record
        success = api.update_or_create_record(
            domain=domain,
            record_type='TXT',
            value=validation_token,
            record_name='_acme-challenge',
            ttl=60
        )

        if success:
            logger.info(f"TXT record created successfully for {domain}")
            # Wait for DNS propagation
            logger.info("Waiting 10 seconds for DNS propagation...")
            time.sleep(10)
            return True
        else:
            logger.error(f"Failed to create TXT record for {domain}")
            return False

    except Exception as e:
        logger.error(f"Error creating TXT record: {e}")
        return False


def remove_txt_record(domain):
    """
    Remove DNS TXT record after ACME validation
    
    Args:
        domain: Domain name
    
    Returns:
        True on success
    """
    try:
        config = load_config()
        api = get_api_client(config)

        txt_record_name = f"_acme-challenge.{domain}"
        
        logger.info(f"Removing TXT record: {txt_record_name}")

        # Get the record ID first
        record_id = api.get_dns_record_id(
            domain=domain,
            record_type='TXT',
            record_name='_acme-challenge'
        )

        if record_id:
            # Delete the record
            success = api.delete_dns_record(domain, record_id)
            if success:
                logger.info(f"TXT record removed successfully for {domain}")
                return True
            else:
                logger.warning(f"Failed to remove TXT record for {domain}")
                return False
        else:
            logger.warning(f"TXT record not found for {domain}")
            return True  # Continue anyway

    except Exception as e:
        logger.error(f"Error removing TXT record: {e}")
        return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: certbot_dns_helper.py <create|remove> <domain> [validation_token]")
        sys.exit(1)

    action = sys.argv[1]
    domain = sys.argv[2]
    
    if action == "create":
        if len(sys.argv) < 4:
            print("Error: validation_token required for create action")
            sys.exit(1)
        token = sys.argv[3]
        success = create_txt_record(domain, token)
        sys.exit(0 if success else 1)
    
    elif action == "remove":
        success = remove_txt_record(domain)
        sys.exit(0 if success else 1)
    
    else:
        print(f"Error: Unknown action '{action}'")
        sys.exit(1)
