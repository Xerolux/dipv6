#!/usr/bin/env python3
"""
Dynamic IPv6/IPv4 DDNS Service
Dual-domain support for UniFi integration
"""

import os
import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import ipaddress
from functools import wraps
from werkzeug.middleware.proxy_fix import ProxyFix
from ispconfig_api import ISPConfigAPI
from nginx_updater import update_and_reload_nginx
from custom_ddns import send_custom_ddns_update

# Configuration
CONFIG_DIR = Path("/etc/dynipv6")
DATA_DIR = Path("/var/lib/dynipv6")
LOG_DIR = Path("/var/log/dynipv6")

# Create directories if they don't exist
for directory in [CONFIG_DIR, DATA_DIR, LOG_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "dynipv6.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

# Load configuration
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_CONFIG = {
    "ipv6_domain": "ipv6.xerolux.net",
    "ipv4_domain": "ipv4.xerolux.net",
    "ispconfig_url": "https://your-ispconfig-server.com:8080",
    "ispconfig_username": "admin",
    "ispconfig_password": "your-password",
    "ispconfig_client_id": "0",
    "auth_tokens": {
        "example_token": "example_device_name"
    },
    "ssl_cert": "/etc/letsencrypt/live/ipv6.xerolux.net/fullchain.pem",
    "ssl_key": "/etc/letsencrypt/live/ipv6.xerolux.net/privkey.pem",
    "port": 5000,
    "host": "127.0.0.1",
    "nginx_update_enabled": False
}

def load_config():
    """Load configuration from file or create default"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    else:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        logger.info(f"Created default config at {CONFIG_FILE}")
        return DEFAULT_CONFIG

config = load_config()


def reload_config():
    """Reload configuration from file so changes made via the Web-UI take effect
    without restarting the service."""
    global config
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
    return config


def get_device_name(token_data):
    """Extract a device name from a token entry, tolerating both formats:
    - Web-UI format: {"name": ..., "device_name": ..., ...}
    - Legacy format: "device_name" (plain string)
    """
    if isinstance(token_data, dict):
        return token_data.get('device_name') or token_data.get('name') or 'unknown'
    return token_data or 'unknown'


def get_target_domains():
    """Return a dict of {domain_name: domain_config} that should be updated.

    Prefers the Web-UI managed `domains` map. Falls back to the legacy single
    `ipv6_domain` / `ipv4_domain` settings when no domains are configured.
    """
    domains = config.get('domains')
    if domains:
        return domains

    # Legacy fallback - synthesize domain configs from old-style settings
    legacy = {}
    ipv6_domain = config.get('ipv6_domain')
    ipv4_domain = config.get('ipv4_domain')

    if ipv6_domain:
        legacy[ipv6_domain] = {
            'ipv4_enabled': ipv6_domain == ipv4_domain,
            'ipv6_enabled': True,
            'dynamic_dns': {}
        }
    if ipv4_domain and ipv4_domain != ipv6_domain:
        legacy[ipv4_domain] = {
            'ipv4_enabled': True,
            'ipv6_enabled': False,
            'dynamic_dns': {}
        }
    return legacy


def calculate_ipv6_host_ip(ipv6_input):
    """
    Calculate host IP from IPv6 network prefix.
    E.g., 2001:db8:1234:5600::/56 → 2001:db8:1234:56::1
    Also handles bare addresses: 2001:db8:1234:5600:: → 2001:db8:1234:56::1
    Returns tuple (original_ip, calculated_ip) or (ip, ip) if no calculation needed
    """
    try:
        # Try to parse as network (with /prefix)
        if '/' in ipv6_input:
            network = ipaddress.IPv6Network(ipv6_input, strict=False)
            host_ip = network.network_address + 1  # First usable host in network
            return (str(network.network_address), str(host_ip))
        else:
            # Try as address and assume /56 or /64
            addr = ipaddress.IPv6Address(ipv6_input)
            # Check if it looks like a network address (ends with ::)
            addr_str = str(addr)
            if addr_str.endswith('::') or addr_str.endswith(':0'):
                # Likely a network address, calculate host IP
                # For /56: keep first 7 groups, set last group to 1
                # For simplicity: treat as /56 network and get first host
                network = ipaddress.IPv6Network(f"{ipv6_input}/56", strict=False)
                host_ip = network.network_address + 1
                return (str(network.network_address), str(host_ip))
            else:
                # Regular address
                return (str(addr), str(addr))
    except Exception as e:
        logger.warning(f"Could not calculate IPv6 host IP for {ipv6_input}: {e}")
        return (ipv6_input, ipv6_input)


class DNSRecord:
    """Store and manage DNS records"""
    def __init__(self, domain, record_type):
        self.domain = domain
        self.record_type = record_type
        self.file = DATA_DIR / f"{domain}_{record_type}.json"

    def get(self):
        """Get current DNS record"""
        if self.file.exists():
            with open(self.file, 'r') as f:
                return json.load(f)
        return None

    def set(self, value, hostname="", username=""):
        """Set DNS record with metadata"""
        data = {
            "value": value,
            "type": self.record_type,
            "domain": self.domain,
            "hostname": hostname,
            "updated": datetime.now().isoformat(),
            "updated_by": username
        }

        # For IPv6 (AAAA records), calculate and store host IP variant
        if self.record_type == 'AAAA':
            original_ip, host_ip = calculate_ipv6_host_ip(value)
            data["value_original"] = original_ip
            data["value_host"] = host_ip

        with open(self.file, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Updated {self.domain} ({self.record_type}): {value}")
        return data

def validate_token(f):
    """Validate authentication token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Reload config so tokens/domains added via the Web-UI are picked up
        reload_config()

        token = request.args.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')

        if not token:
            return jsonify({"status": "error", "message": "Missing token"}), 401

        if token not in config.get("auth_tokens", {}):
            return jsonify({"status": "error", "message": "Invalid token"}), 401

        request.device_name = get_device_name(config["auth_tokens"][token])
        request.token = token
        return f(*args, **kwargs)

    return decorated_function

def update_ispconfig_dns(domain, record_type, value):
    """Update or create DNS record in ISPConfig"""
    try:
        api = ISPConfigAPI(
            url=config['ispconfig_url'],
            username=config['ispconfig_username'],
            password=config['ispconfig_password'],
            client_id=config.get('ispconfig_client_id', '0'),
            verify_ssl=config.get('ispconfig_verify_ssl', False)
        )

        success = api.update_or_create_record(domain, record_type, value, ttl=3600)

        if success:
            logger.info(f"ISPConfig: Updated {domain} ({record_type}) = {value}")
        else:
            logger.warning(f"ISPConfig: Failed to update {domain} ({record_type})")

        return success
    except Exception as e:
        logger.error(f"ISPConfig update error: {e}")
        return False

def apply_update_for_domain(domain_name, domain_cfg, ipv6, ipv4, hostname, device_name):
    """Apply an IP update to a single domain, respecting its enabled flags and
    routing through Custom DDNS or ISPConfig depending on its configuration.

    Returns a result dict, or None if nothing applied to this domain.
    """
    ddns = domain_cfg.get('dynamic_dns', {}) or {}
    use_custom = ddns.get('service') == 'custom'

    pub_ipv6 = None
    pub_ipv4 = None

    # Store records locally and determine the address to publish
    if ipv6 and domain_cfg.get('ipv6_enabled', True):
        data = DNSRecord(domain_name, 'AAAA').set(ipv6, hostname, device_name)
        pub_ipv6 = ipv6
        # Optionally publish the calculated host IP instead of the raw prefix
        if domain_cfg.get('use_calculated_ipv6') and data.get('value_host'):
            pub_ipv6 = data['value_host']

    if ipv4 and domain_cfg.get('ipv4_enabled', True):
        DNSRecord(domain_name, 'A').set(ipv4, hostname, device_name)
        pub_ipv4 = ipv4

    if not pub_ipv6 and not pub_ipv4:
        return None

    result = {}

    if use_custom:
        # Route the update to the per-domain custom DDNS endpoint
        ddns_result = send_custom_ddns_update(domain_cfg, ipv4=pub_ipv4, ipv6=pub_ipv6)
        result['method'] = 'custom'
        result['result'] = ddns_result
        logger.info(f"Custom DDNS update for {domain_name}: {ddns_result.get('status')}")
        return result

    # Default: route through ISPConfig
    result['method'] = 'ispconfig'

    if pub_ipv6:
        ok = update_ispconfig_dns(domain_name, 'AAAA', pub_ipv6)
        nginx_updated = False
        if config.get('nginx_update_enabled', False):
            nginx_updated = update_and_reload_nginx(pub_ipv6, domain_name)
            if nginx_updated:
                logger.info(f"Nginx updated with IPv6: {pub_ipv6}")
            else:
                logger.warning(f"Nginx update failed for {domain_name}")
        result['ipv6'] = {
            "status": "success" if ok else "error",
            "address": pub_ipv6,
            "nginx_updated": nginx_updated
        }

    if pub_ipv4:
        ok = update_ispconfig_dns(domain_name, 'A', pub_ipv4)
        result['ipv4'] = {
            "status": "success" if ok else "error",
            "address": pub_ipv4
        }

    return result


@app.route('/api/update', methods=['GET', 'POST'])
@validate_token
def update_dns():
    """Update DNS records - compatible with UniFi and dynv6 clients.

    Iterates over all configured domains and routes each through Custom DDNS or
    ISPConfig based on its per-domain configuration.
    """
    try:
        # Get parameters from query string or POST data (accept ipv6prefix or ipv6)
        ipv6 = (request.args.get('ipv6prefix') or request.form.get('ipv6prefix')
                or request.args.get('ipv6') or request.form.get('ipv6'))
        ipv4 = request.args.get('ipv4') or request.form.get('ipv4')
        hostname = request.args.get('hostname') or request.form.get('hostname')

        # Resolve 'auto' to the request source address
        if ipv6 and ipv6.lower() == 'auto':
            ipv6 = request.remote_addr
        if ipv4 and ipv4.lower() == 'auto':
            ipv4 = request.remote_addr

        # Validate provided addresses
        if ipv6:
            try:
                if ipaddress.ip_address(ipv6).version != 6:
                    raise ValueError()
            except ValueError:
                return jsonify({"status": "error", "message": f"Invalid IPv6 address: {ipv6}"}), 400
        if ipv4:
            try:
                if ipaddress.ip_address(ipv4).version != 4:
                    raise ValueError()
            except ValueError:
                return jsonify({"status": "error", "message": f"Invalid IPv4 address: {ipv4}"}), 400

        if not ipv6 and not ipv4:
            return jsonify({"status": "error", "message": "No IPv4 or IPv6 provided"}), 400

        targets = get_target_domains()
        if not targets:
            return jsonify({"status": "error", "message": "No domains configured"}), 400

        device_name = getattr(request, 'device_name', 'unknown')
        updates = {}
        for domain_name, domain_cfg in targets.items():
            domain_result = apply_update_for_domain(
                domain_name, domain_cfg, ipv6, ipv4, hostname, device_name
            )
            if domain_result:
                updates[domain_name] = domain_result

        if not updates:
            return jsonify({
                "status": "error",
                "message": "No domain accepted the update (check enabled flags)"
            }), 400

        return jsonify({
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "updates": updates
        })

    except Exception as e:
        logger.error(f"Update error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/status', methods=['GET'])
@validate_token
def get_status():
    """Get current DNS records status for all configured domains"""
    try:
        domains_status = {}
        for domain_name, domain_cfg in get_target_domains().items():
            domains_status[domain_name] = {
                "ipv6": DNSRecord(domain_name, 'AAAA').get(),
                "ipv4": DNSRecord(domain_name, 'A').get(),
                "ipv6_enabled": domain_cfg.get('ipv6_enabled', True),
                "ipv4_enabled": domain_cfg.get('ipv4_enabled', True),
                "ddns_service": (domain_cfg.get('dynamic_dns', {}) or {}).get('service', 'none')
            }

        return jsonify({
            "status": "success",
            "domains": domains_status,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Status error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint (no auth required)"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "dynipv6"
    })

@app.route('/api/ispconfig-test', methods=['GET'])
@validate_token
def test_ispconfig():
    """Test ISPConfig API connection"""
    try:
        api = ISPConfigAPI(
            url=config['ispconfig_url'],
            username=config['ispconfig_username'],
            password=config['ispconfig_password'],
            client_id=config.get('ispconfig_client_id', '0'),
            verify_ssl=config.get('ispconfig_verify_ssl', False)
        )

        if api.test_connection():
            return jsonify({
                "status": "success",
                "message": "ISPConfig connection successful",
                "server": config['ispconfig_url']
            })
        else:
            return jsonify({
                "status": "error",
                "message": "ISPConfig connection failed",
                "server": config['ispconfig_url']
            }), 503
    except Exception as e:
        logger.error(f"ISPConfig test error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/', methods=['GET'])
def index():
    """Service information"""
    return jsonify({
        "service": "Dynamic IPv6/IPv4 DDNS Service",
        "version": "1.0.0",
        "endpoints": {
            "/api/update": "Update DNS records (requires token)",
            "/api/status": "Get current records status (requires token)",
            "/api/ispconfig-test": "Test ISPConfig connection (requires token)",
            "/api/health": "Health check"
        },
        "documentation": "See README.md for setup instructions"
    })

@app.errorhandler(404)
def not_found(e):
    return jsonify({"status": "error", "message": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal error: {e}")
    return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == '__main__':
    # Check if SSL certificates exist
    ssl_context = None
    if os.path.exists(config['ssl_cert']) and os.path.exists(config['ssl_key']):
        ssl_context = (config['ssl_cert'], config['ssl_key'])
        logger.info("Starting with SSL/TLS")
    else:
        logger.warning("SSL certificates not found, starting in HTTP mode")

    app.run(
        host=config['host'],
        port=config['port'],
        ssl_context=ssl_context,
        debug=False
    )
