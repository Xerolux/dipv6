#!/usr/bin/env python3
"""
ISPConfig API Client for DNS Management
Handles authentication, zone lookup, and record updates
"""

import requests
import json
import logging
from typing import Optional, Dict, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class ISPConfigAPI:
    """ISPConfig SOAP-like API Client"""

    def __init__(self, url: str, username: str, password: str, client_id: str = "0", verify_ssl: bool = False):
        """Initialize ISPConfig API client

        Args:
            url: ISPConfig base URL (e.g., https://panel.example.com:8080)
            username: ISPConfig username
            password: ISPConfig password
            client_id: Client ID (default: 0 for admin)
            verify_ssl: Verify SSL certificate (default: False)
        """
        self.url = url.rstrip('/')
        self.username = username
        self.password = password
        self.client_id = client_id
        self.verify_ssl = verify_ssl

        # Create session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.session.verify = verify_ssl

    def _call_api(self, endpoint: str, method: str = "post", **kwargs) -> Dict:
        """Call ISPConfig API endpoint

        Args:
            endpoint: API endpoint (e.g., 'dnszone/get_id')
            method: HTTP method (post/get)
            **kwargs: Additional parameters

        Returns:
            API response as dictionary
        """
        url = f"{self.url}/api/{endpoint}"

        # Add authentication
        data = {
            'username': self.username,
            'password': self.password,
            'client_id': self.client_id,
        }
        data.update(kwargs)

        try:
            if method.lower() == "post":
                response = self.session.post(url, data=data, timeout=10)
            else:
                response = self.session.get(url, params=data, timeout=10)

            response.raise_for_status()

            # ISPConfig returns JSON
            try:
                result = response.json()
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON response from ISPConfig: {response.text}")
                return {"error": "Invalid response from server"}

            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"ISPConfig API error: {e}")
            return {"error": str(e)}

    def get_dns_zone_id(self, domain: str) -> Optional[str]:
        """Get DNS zone ID for domain

        Args:
            domain: Domain name (e.g., 'xerolux.net')

        Returns:
            Zone ID if found, None otherwise
        """
        # Extract base domain if subdomain given
        # e.g., 'ipv6.xerolux.net' → 'xerolux.net'
        parts = domain.split('.')
        if len(parts) > 2:
            base_domain = '.'.join(parts[-2:])
        else:
            base_domain = domain

        result = self._call_api('dnszone/get_id', name=base_domain)

        if 'id' in result:
            logger.info(f"Found DNS zone ID {result['id']} for domain {base_domain}")
            return result['id']
        elif 'error' not in result:
            logger.warning(f"No DNS zone found for {base_domain}")
            return None
        else:
            logger.error(f"Error getting zone ID: {result.get('error')}")
            return None

    def get_dns_records(self, zone_id: str) -> List[Dict]:
        """Get all DNS records for a zone

        Args:
            zone_id: DNS zone ID

        Returns:
            List of DNS records
        """
        result = self._call_api('dnsrecord/get', id=zone_id)

        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and 'error' not in result:
            return [result]
        else:
            logger.error(f"Error getting DNS records: {result}")
            return []

    def get_dns_record_id(self, zone_id: str, name: str, record_type: str) -> Optional[str]:
        """Get DNS record ID by name and type

        Args:
            zone_id: DNS zone ID
            name: Record name (FQDN or relative)
            record_type: Record type (A, AAAA, CNAME, etc.)

        Returns:
            Record ID if found, None otherwise
        """
        records = self.get_dns_records(zone_id)

        for record in records:
            # Match by name and type
            if record.get('name') == name and record.get('type') == record_type:
                logger.info(f"Found record ID {record['id']} for {name} ({record_type})")
                return record['id']
            # Also try without trailing dot
            elif record.get('name', '').rstrip('.') == name.rstrip('.') and record.get('type') == record_type:
                logger.info(f"Found record ID {record['id']} for {name} ({record_type})")
                return record['id']

        logger.warning(f"Record not found: {name} ({record_type})")
        return None

    def create_dns_record(self, zone_id: str, name: str, record_type: str, data: str, ttl: int = 3600) -> bool:
        """Create new DNS record

        Args:
            zone_id: DNS zone ID
            name: Record name (e.g., 'ipv6.xerolux.net' or '@' for root)
            record_type: Record type (A, AAAA, CNAME, MX, TXT, NS, SOA)
            data: Record data (IP address, hostname, etc.)
            ttl: Time to live in seconds (default: 3600)

        Returns:
            True if successful, False otherwise
        """
        record_data = {
            'zone': zone_id,
            'name': name,
            'type': record_type,
            'data': data,
            'ttl': ttl,
            'active': 'y'
        }

        result = self._call_api('dnsrecord/add', data=json.dumps(record_data))

        if 'id' in result:
            logger.info(f"Created DNS record {result['id']}: {name} ({record_type}) = {data}")
            return True
        else:
            logger.error(f"Failed to create DNS record: {result}")
            return False

    def update_dns_record(self, record_id: str, data: str, ttl: int = 3600) -> bool:
        """Update existing DNS record

        Args:
            record_id: DNS record ID
            data: New record data (IP address, etc.)
            ttl: Time to live in seconds (default: 3600)

        Returns:
            True if successful, False otherwise
        """
        record_data = {
            'id': record_id,
            'data': data,
            'ttl': ttl,
            'active': 'y'
        }

        result = self._call_api('dnsrecord/update', data=json.dumps(record_data))

        if 'status' in result or 'id' in result:
            logger.info(f"Updated DNS record {record_id}: data={data}, ttl={ttl}")
            return True
        else:
            logger.error(f"Failed to update DNS record {record_id}: {result}")
            return False

    def update_or_create_record(self, domain: str, record_type: str, data: str, ttl: int = 3600) -> bool:
        """Update DNS record if exists, create if not

        Args:
            domain: Full domain name (e.g., 'ipv6.xerolux.net')
            record_type: Record type (A, AAAA, etc.)
            data: Record data (IP address)
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        # Get zone ID for base domain
        zone_id = self.get_dns_zone_id(domain)
        if not zone_id:
            logger.error(f"Cannot update/create record: zone not found for {domain}")
            return False

        # Check if record exists
        record_id = self.get_dns_record_id(zone_id, domain, record_type)

        if record_id:
            # Update existing record
            return self.update_dns_record(record_id, data, ttl)
        else:
            # Create new record
            return self.create_dns_record(zone_id, domain, record_type, data, ttl)

    def test_connection(self) -> bool:
        """Test ISPConfig API connection

        Returns:
            True if connection successful, False otherwise
        """
        result = self._call_api('dnszone/get_id', name='test.invalid')

        if 'error' in result and 'not found' in str(result).lower():
            # Error is expected (test domain doesn't exist)
            logger.info("ISPConfig API connection successful")
            return True
        elif 'error' in result:
            logger.error(f"ISPConfig API error: {result['error']}")
            return False
        else:
            logger.info("ISPConfig API connection successful")
            return True


def update_dns_with_ispconfig(ispconfig_config: Dict, domain: str, record_type: str, ip_address: str) -> bool:
    """Convenience function to update DNS via ISPConfig

    Args:
        ispconfig_config: Config dict with 'url', 'username', 'password', 'client_id'
        domain: Domain name
        record_type: Record type (A or AAAA)
        ip_address: IP address to set

    Returns:
        True if successful, False otherwise
    """
    try:
        api = ISPConfigAPI(
            url=ispconfig_config['ispconfig_url'],
            username=ispconfig_config['ispconfig_username'],
            password=ispconfig_config['ispconfig_password'],
            client_id=ispconfig_config.get('ispconfig_client_id', '0'),
            verify_ssl=ispconfig_config.get('ispconfig_verify_ssl', False)
        )

        return api.update_or_create_record(domain, record_type, ip_address)
    except Exception as e:
        logger.error(f"Error updating DNS: {e}")
        return False
