#!/usr/bin/env python3
"""
Nginx Configuration Updater
Dynamically update Nginx configuration with new IPv6 addresses
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def update_nginx_ipv6(ipv6_address: str, domain: str, nginx_config_dir: str = "/etc/nginx/conf.d") -> bool:
    """
    Update Nginx configuration with IPv6 address

    Args:
        ipv6_address: IPv6 address to configure
        domain: Domain name for the configuration
        nginx_config_dir: Directory where Nginx config files are located

    Returns:
        True if successful, False otherwise
    """
    try:
        config_file = Path(nginx_config_dir) / f"{domain}.conf"

        if not config_file.exists():
            logger.warning(f"Nginx config not found: {config_file}")
            return False

        with open(config_file, 'r') as f:
            content = f.read()

        # Find and replace or add IPv6 listen directive
        lines = content.split('\n')
        updated_lines = []
        found_ipv6_listen = False

        for line in lines:
            if 'listen' in line and '::' in line:
                # Replace existing IPv6 listen directive
                updated_lines.append(f"    listen [{ipv6_address}]:443 ssl http2;")
                found_ipv6_listen = True
            elif 'listen' in line and ':443' in line and '::' not in line:
                # Found IPv4 listen, keep it
                updated_lines.append(line)
            else:
                updated_lines.append(line)

        # If no IPv6 listen found, add it after IPv4 listen
        if not found_ipv6_listen:
            new_lines = []
            for i, line in enumerate(updated_lines):
                new_lines.append(line)
                if 'listen' in line and ':443' in line and '::' not in line:
                    new_lines.append(f"    listen [{ipv6_address}]:443 ssl http2;")

            updated_lines = new_lines

        updated_content = '\n'.join(updated_lines)

        with open(config_file, 'w') as f:
            f.write(updated_content)

        logger.info(f"Updated Nginx config for {domain} with IPv6: {ipv6_address}")
        return True

    except Exception as e:
        logger.error(f"Error updating Nginx config: {e}")
        return False


def reload_nginx() -> bool:
    """
    Reload Nginx configuration

    Returns:
        True if successful, False otherwise
    """
    try:
        # Test configuration first
        result = subprocess.run(
            ['nginx', '-t'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            logger.error(f"Nginx config test failed: {result.stderr}")
            return False

        # Reload Nginx
        result = subprocess.run(
            ['nginx', '-s', 'reload'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            logger.info("Nginx reloaded successfully")
            return True
        else:
            logger.error(f"Nginx reload failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("Nginx operation timeout")
        return False
    except Exception as e:
        logger.error(f"Error reloading Nginx: {e}")
        return False


def update_and_reload_nginx(ipv6_address: str, domain: str) -> bool:
    """
    Update Nginx configuration and reload

    Args:
        ipv6_address: IPv6 address to configure
        domain: Domain name

    Returns:
        True if successful, False otherwise
    """
    if update_nginx_ipv6(ipv6_address, domain):
        return reload_nginx()
    return False
