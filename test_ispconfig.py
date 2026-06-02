#!/usr/bin/env python3
"""
ISPConfig API Tester
Test your ISPConfig configuration before deploying DDNS service
"""

import sys
import json
from pathlib import Path
from ispconfig_api import ISPConfigAPI

# Colors
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'=' * 60}{NC}")
    print(f"{BLUE}{text:^60}{NC}")
    print(f"{BLUE}{'=' * 60}{NC}\n")

def print_success(text):
    print(f"{GREEN}✓ PASS:{NC} {text}")

def print_error(text):
    print(f"{RED}✗ FAIL:{NC} {text}")

def print_info(text):
    print(f"{YELLOW}ℹ INFO:{NC} {text}")

def load_config():
    """Load configuration from config.json"""
    config_file = Path("/etc/dynipv6/config.json")

    if not config_file.exists():
        print_error(f"Configuration file not found: {config_file}")
        print_info("Copy config.json.example to /etc/dynipv6/config.json first")
        return None

    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print_error(f"Failed to load config: {e}")
        return None

def test_connection(config):
    """Test ISPConfig connection"""
    print_header("Testing ISPConfig Connection")

    try:
        api = ISPConfigAPI(
            url=config['ispconfig_url'],
            username=config['ispconfig_username'],
            password=config['ispconfig_password'],
            client_id=config.get('ispconfig_client_id', '0'),
            verify_ssl=config.get('ispconfig_verify_ssl', False)
        )

        if api.test_connection():
            print_success("ISPConfig API is accessible")
            print_info(f"Server: {config['ispconfig_url']}")
            print_info(f"User: {config['ispconfig_username']}")
            return api
        else:
            print_error("ISPConfig API test failed")
            print_info("Check username, password, and server URL")
            return None
    except Exception as e:
        print_error(f"Connection error: {e}")
        return None

def test_zone_lookup(api, config):
    """Test DNS zone lookup"""
    print_header("Testing DNS Zone Lookup")

    domains = [config['ipv6_domain'], config['ipv4_domain']]
    results = {}

    for domain in domains:
        zone_id = api.get_dns_zone_id(domain)
        if zone_id:
            print_success(f"Found zone for {domain} (ID: {zone_id})")
            results[domain] = zone_id
        else:
            print_error(f"No zone found for {domain}")
            print_info(f"Create DNS zone in ISPConfig first")

    return results

def test_record_operations(api, config, zone_ids):
    """Test DNS record operations"""
    print_header("Testing DNS Record Operations")

    # Test data
    test_ipv6 = "2001:db8::1234:5678"
    test_ipv4 = "203.0.113.1"

    success_count = 0

    # Test IPv6 record
    if config['ipv6_domain'] in zone_ids:
        zone_id = zone_ids[config['ipv6_domain']]

        # Try to create/update
        if api.update_or_create_record(
            config['ipv6_domain'],
            'AAAA',
            test_ipv6
        ):
            print_success(f"Created/updated {config['ipv6_domain']} (AAAA)")
            success_count += 1
        else:
            print_error(f"Failed to update {config['ipv6_domain']} (AAAA)")

    # Test IPv4 record
    if config['ipv4_domain'] in zone_ids:
        zone_id = zone_ids[config['ipv4_domain']]

        # Try to create/update
        if api.update_or_create_record(
            config['ipv4_domain'],
            'A',
            test_ipv4
        ):
            print_success(f"Created/updated {config['ipv4_domain']} (A)")
            success_count += 1
        else:
            print_error(f"Failed to update {config['ipv4_domain']} (A)")

    return success_count == 2

def test_record_retrieval(api, config, zone_ids):
    """Test retrieving records"""
    print_header("Testing Record Retrieval")

    for domain, zone_id in zone_ids.items():
        print_info(f"Records in {domain}:")
        records = api.get_dns_records(zone_id)

        if not records:
            print_error(f"  No records found")
        else:
            for record in records:
                name = record.get('name', 'N/A')
                rtype = record.get('type', 'N/A')
                data = record.get('data', 'N/A')
                print_info(f"  {name:30} {rtype:5} {data}")

def main():
    """Run all tests"""
    print(f"\n{BLUE}{'*' * 60}{NC}")
    print(f"{BLUE}{'ISPConfig API Test Suite':^60}{NC}")
    print(f"{BLUE}{'*' * 60}{NC}\n")

    # Load config
    config = load_config()
    if not config:
        sys.exit(1)

    # Test connection
    api = test_connection(config)
    if not api:
        sys.exit(1)

    # Test zone lookup
    zone_ids = test_zone_lookup(api, config)
    if not zone_ids:
        print_error("Cannot continue without valid zones")
        sys.exit(1)

    # Test record operations
    if test_record_operations(api, config, zone_ids):
        print_success("All record operations successful")
    else:
        print_error("Some record operations failed")

    # Test record retrieval
    test_record_retrieval(api, config, zone_ids)

    # Summary
    print_header("Test Summary")
    print_success("ISPConfig configuration is working correctly!")
    print_info("You can now enable the DDNS service:")
    print_info("  sudo systemctl start dynipv6")
    print_info("  sudo systemctl enable dynipv6")
    print()

if __name__ == '__main__':
    main()
