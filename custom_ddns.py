#!/usr/bin/env python3
"""
Custom Dynamic DNS Update Handler
Sends DNS updates to custom API endpoints
"""

import logging
import requests
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class CustomDDNSClient:
    """Handle updates for custom DDNS providers"""

    def __init__(self, hostname: str, username: str, password: str, server: str):
        """
        Initialize Custom DDNS client

        Args:
            hostname: Domain name to update
            username: API username
            password: API password/token
            server: API endpoint URL
        """
        self.hostname = hostname
        self.username = username
        self.password = password
        self.server = server

    def update(self, ipv4: Optional[str] = None, ipv6: Optional[str] = None) -> Dict:
        """
        Send update request to custom DDNS server

        Args:
            ipv4: IPv4 address to update (optional)
            ipv6: IPv6 address to update (optional)

        Returns:
            Dict with status and result
        """
        if not ipv4 and not ipv6:
            return {
                'status': 'error',
                'message': 'At least one IP address must be provided'
            }

        try:
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'DynIPv6-Client/1.0'
            }

            payload = {
                'hostname': self.hostname,
                'username': self.username,
                'password': self.password
            }

            if ipv4:
                payload['ipv4'] = ipv4
            if ipv6:
                payload['ipv6'] = ipv6

            response = requests.post(
                self.server,
                json=payload,
                headers=headers,
                timeout=10,
                verify=True
            )

            if response.status_code in [200, 201]:
                logger.info(f"Custom DDNS update successful for {self.hostname}")
                return {
                    'status': 'success',
                    'message': f'Update sent to {self.server}',
                    'ipv4': ipv4,
                    'ipv6': ipv6
                }
            else:
                error_msg = response.text or f"HTTP {response.status_code}"
                logger.error(f"Custom DDNS update failed for {self.hostname}: {error_msg}")
                return {
                    'status': 'error',
                    'message': f'Server returned: {error_msg}'
                }

        except requests.exceptions.Timeout:
            logger.error(f"Custom DDNS update timeout for {self.hostname}")
            return {
                'status': 'error',
                'message': 'Request timeout (exceeded 10 seconds)'
            }
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Custom DDNS connection error for {self.hostname}: {e}")
            return {
                'status': 'error',
                'message': f'Connection error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Custom DDNS update error for {self.hostname}: {e}")
            return {
                'status': 'error',
                'message': f'Error: {str(e)}'
            }


def send_custom_ddns_update(domain_config: Dict, ipv4: Optional[str] = None, ipv6: Optional[str] = None) -> Dict:
    """
    Send update to custom DDNS provider from domain config

    Args:
        domain_config: Domain configuration dict
        ipv4: IPv4 address to update
        ipv6: IPv6 address to update

    Returns:
        Dict with status and result
    """
    ddns = domain_config.get('dynamic_dns', {})

    if ddns.get('service') != 'custom':
        return {
            'status': 'skipped',
            'message': 'No custom DDNS configured'
        }

    required_fields = ['hostname', 'username', 'password', 'server']
    missing = [f for f in required_fields if not ddns.get(f)]
    if missing:
        return {
            'status': 'error',
            'message': f'Missing DDNS config: {", ".join(missing)}'
        }

    client = CustomDDNSClient(
        hostname=ddns['hostname'],
        username=ddns['username'],
        password=ddns['password'],
        server=ddns['server']
    )

    return client.update(ipv4=ipv4, ipv6=ipv6)
