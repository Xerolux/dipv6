#!/usr/bin/env python3
"""
Web-UI Admin Panel for Dynamic IPv6/IPv4 DDNS Service
Secure management interface for domain and token configuration
"""

import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
import logging

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import jwt

# Configuration paths
CONFIG_DIR = Path("/etc/dynipv6")
DATA_DIR = Path("/var/lib/dynipv6")
TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)

# Admin credentials file
ADMIN_FILE = CONFIG_DIR / "admin.json"
DEFAULT_ADMIN = {
    "username": "admin",
    "password_hash": generate_password_hash("admin123"),  # Change on first login!
    "last_login": None
}


class ConfigManager:
    """Manage DDNS configuration"""

    def __init__(self, config_file=None):
        self.config_file = config_file or (CONFIG_DIR / "config.json")
        self.load()

    def load(self):
        """Load configuration from file"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = self._default_config()

    def _default_config(self):
        """Default configuration"""
        return {
            "ispconfig_url": "https://your-ispconfig:8080",
            "ispconfig_username": "admin",
            "ispconfig_password": "password",
            "ispconfig_client_id": "0",
            "domains": {},
            "auth_tokens": {}
        }

    def save(self):
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
        logger.info(f"Configuration saved to {self.config_file}")

    def add_domain(self, domain_name, ipv4_enabled=True, ipv6_enabled=True, use_calculated_ipv6=False):
        """Add or update domain configuration"""
        self.config['domains'][domain_name] = {
            "ipv4_enabled": ipv4_enabled,
            "ipv6_enabled": ipv6_enabled,
            "use_calculated_ipv6": use_calculated_ipv6,
            "created": datetime.now().isoformat(),
            "last_update": None,
            "last_ipv4": None,
            "last_ipv6": None
        }
        self.save()
        logger.info(f"Domain added/updated: {domain_name}")

    def delete_domain(self, domain_name):
        """Delete domain configuration"""
        if domain_name in self.config['domains']:
            del self.config['domains'][domain_name]
            self.save()
            logger.info(f"Domain deleted: {domain_name}")
            return True
        return False

    def add_token(self, token_name, device_name):
        """Add authentication token"""
        token = secrets.token_urlsafe(32)
        self.config['auth_tokens'][token] = {
            "name": token_name,
            "device_name": device_name,
            "created": datetime.now().isoformat(),
            "last_used": None
        }
        self.save()
        logger.info(f"Token added: {token_name}")
        return token

    def delete_token(self, token):
        """Delete authentication token"""
        if token in self.config['auth_tokens']:
            del self.config['auth_tokens'][token]
            self.save()
            logger.info(f"Token deleted: {token}")
            return True
        return False

    def get_domain_status(self, domain_name):
        """Get domain status from local files"""
        ipv4_file = DATA_DIR / f"{domain_name}_A.json"
        ipv6_file = DATA_DIR / f"{domain_name}_AAAA.json"

        status = {
            "domain": domain_name,
            "ipv4": None,
            "ipv6": None,
            "ipv6_original": None,
            "ipv6_host": None,
            "last_update": None
        }

        if ipv4_file.exists():
            with open(ipv4_file, 'r') as f:
                data = json.load(f)
                status['ipv4'] = data.get('value')
                status['last_update'] = data.get('updated')

        if ipv6_file.exists():
            with open(ipv6_file, 'r') as f:
                data = json.load(f)
                status['ipv6'] = data.get('value')
                status['ipv6_original'] = data.get('value_original')
                status['ipv6_host'] = data.get('value_host')
                if not status['last_update'] or data.get('updated') > status['last_update']:
                    status['last_update'] = data.get('updated')

        return status


def load_admin():
    """Load admin credentials"""
    if ADMIN_FILE.exists():
        with open(ADMIN_FILE, 'r') as f:
            return json.load(f)
    else:
        # Create default admin
        with open(ADMIN_FILE, 'w') as f:
            json.dump(DEFAULT_ADMIN, f, indent=2)
        os.chmod(ADMIN_FILE, 0o600)
        return DEFAULT_ADMIN


def save_admin(admin_data):
    """Save admin credentials"""
    with open(ADMIN_FILE, 'w') as f:
        json.dump(admin_data, f, indent=2)
    os.chmod(ADMIN_FILE, 0o600)


def login_required(f):
    """Require login for route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# Routes

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        admin = load_admin()

        if username == admin['username'] and check_password_hash(admin['password_hash'], password):
            session.permanent = True
            session['username'] = username
            admin['last_login'] = datetime.now().isoformat()
            save_admin(admin)
            logger.info(f"Admin login successful: {username}")
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'error')
            logger.warning(f"Failed login attempt for: {username}")

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Admin logout"""
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))


@app.route('/')
@login_required
def dashboard():
    """Main dashboard"""
    config_manager = ConfigManager()

    # Get all domains with status
    domains = []
    for domain_name in config_manager.config['domains']:
        status = config_manager.get_domain_status(domain_name)
        domain_config = config_manager.config['domains'][domain_name]
        status.update({
            'ipv4_enabled': domain_config.get('ipv4_enabled'),
            'ipv6_enabled': domain_config.get('ipv6_enabled'),
            'use_calculated_ipv6': domain_config.get('use_calculated_ipv6', False)
        })
        domains.append(status)

    # Get token count
    token_count = len(config_manager.config['auth_tokens'])

    return render_template('dashboard.html', domains=domains, token_count=token_count)


@app.route('/domains')
@login_required
def manage_domains():
    """Manage domains"""
    config_manager = ConfigManager()

    domains = []
    for domain_name in config_manager.config['domains']:
        status = config_manager.get_domain_status(domain_name)
        domain_config = config_manager.config['domains'][domain_name]
        status.update({
            'config': domain_config,
            'ipv4_enabled': domain_config.get('ipv4_enabled'),
            'ipv6_enabled': domain_config.get('ipv6_enabled'),
            'use_calculated_ipv6': domain_config.get('use_calculated_ipv6', False)
        })
        domains.append(status)

    return render_template('domains.html', domains=domains)


@app.route('/api/domain/add', methods=['POST'])
@login_required
def api_add_domain():
    """Add new domain"""
    data = request.get_json()
    domain_name = data.get('domain_name')
    ipv4_enabled = data.get('ipv4_enabled', True)
    ipv6_enabled = data.get('ipv6_enabled', True)

    if not domain_name:
        return jsonify({'error': 'Domain name required'}), 400

    config_manager = ConfigManager()
    config_manager.add_domain(domain_name, ipv4_enabled, ipv6_enabled)

    logger.info(f"Domain added by {session['username']}: {domain_name}")
    return jsonify({'status': 'success', 'message': f'Domain {domain_name} added'})


@app.route('/api/domain/delete/<domain_name>', methods=['POST'])
@login_required
def api_delete_domain(domain_name):
    """Delete domain"""
    config_manager = ConfigManager()

    if config_manager.delete_domain(domain_name):
        logger.info(f"Domain deleted by {session['username']}: {domain_name}")
        return jsonify({'status': 'success', 'message': f'Domain {domain_name} deleted'})
    else:
        return jsonify({'error': 'Domain not found'}), 404


@app.route('/api/domain/update/<domain_name>', methods=['POST'])
@login_required
def api_update_domain(domain_name):
    """Update domain configuration"""
    data = request.get_json()
    ipv4_enabled = data.get('ipv4_enabled', True)
    ipv6_enabled = data.get('ipv6_enabled', True)
    use_calculated_ipv6 = data.get('use_calculated_ipv6', False)

    config_manager = ConfigManager()
    config_manager.add_domain(domain_name, ipv4_enabled, ipv6_enabled, use_calculated_ipv6)

    logger.info(f"Domain updated by {session['username']}: {domain_name}")
    return jsonify({'status': 'success', 'message': f'Domain {domain_name} updated'})


@app.route('/api/domain/set-ip/<domain_name>', methods=['POST'])
@login_required
def api_set_ip_manual(domain_name):
    """Manually set IPv4/IPv6 addresses"""
    import ipaddress
    data = request.get_json()
    ipv4 = data.get('ipv4')
    ipv6 = data.get('ipv6')

    # Validate IPv4 if provided
    if ipv4:
        try:
            ipaddress.IPv4Address(ipv4)
        except ipaddress.AddressValueError:
            return jsonify({'error': f'Invalid IPv4 address: {ipv4}'}), 400

    # Validate IPv6 if provided
    if ipv6:
        try:
            ipaddress.IPv6Address(ipv6)
        except ipaddress.AddressValueError:
            return jsonify({'error': f'Invalid IPv6 address: {ipv6}'}), 400

    # Save IPv4
    if ipv4:
        ipv4_file = DATA_DIR / f"{domain_name}_A.json"
        with open(ipv4_file, 'w') as f:
            json.dump({
                'value': ipv4,
                'updated': datetime.now().isoformat(),
                'source': 'manual'
            }, f)
        logger.info(f"IPv4 set manually for {domain_name}: {ipv4} by {session['username']}")

    # Save IPv6
    if ipv6:
        ipv6_file = DATA_DIR / f"{domain_name}_AAAA.json"
        with open(ipv6_file, 'w') as f:
            json.dump({
                'value': ipv6,
                'updated': datetime.now().isoformat(),
                'source': 'manual'
            }, f)
        logger.info(f"IPv6 set manually for {domain_name}: {ipv6} by {session['username']}")

    return jsonify({
        'status': 'success',
        'message': f'IP addresses set for {domain_name}',
        'ipv4': ipv4,
        'ipv6': ipv6
    })


@app.route('/tokens')
@login_required
def manage_tokens():
    """Manage authentication tokens"""
    config_manager = ConfigManager()
    tokens = []

    for token, token_data in config_manager.config['auth_tokens'].items():
        tokens.append({
            'token': token[:10] + '...',  # Show only first 10 chars
            'full_token': token,
            'name': token_data.get('name', 'Unknown'),
            'device_name': token_data.get('device_name', 'N/A'),
            'created': token_data.get('created'),
            'last_used': token_data.get('last_used')
        })

    return render_template('tokens.html', tokens=tokens)


@app.route('/api/token/add', methods=['POST'])
@login_required
def api_add_token():
    """Add new token"""
    data = request.get_json()
    token_name = data.get('token_name')
    device_name = data.get('device_name')

    if not token_name or not device_name:
        return jsonify({'error': 'Token name and device name required'}), 400

    config_manager = ConfigManager()
    token = config_manager.add_token(token_name, device_name)

    logger.info(f"Token created by {session['username']}: {token_name}")
    return jsonify({'status': 'success', 'token': token, 'message': 'Token created successfully'})


@app.route('/api/token/delete/<token>', methods=['POST'])
@login_required
def api_delete_token(token):
    """Delete token"""
    config_manager = ConfigManager()

    if config_manager.delete_token(token):
        logger.info(f"Token deleted by {session['username']}")
        return jsonify({'status': 'success', 'message': 'Token deleted'})
    else:
        return jsonify({'error': 'Token not found'}), 404


@app.route('/settings')
@login_required
def settings():
    """Settings page"""
    config_manager = ConfigManager()
    admin = load_admin()

    ispconfig_config = {
        'url': config_manager.config.get('ispconfig_url', ''),
        'username': config_manager.config.get('ispconfig_username', ''),
        'client_id': config_manager.config.get('ispconfig_client_id', '0')
    }

    return render_template('settings.html', ispconfig=ispconfig_config, admin=admin)


@app.route('/api/settings/ispconfig', methods=['POST'])
@login_required
def api_update_ispconfig():
    """Update ISPConfig settings"""
    data = request.get_json()

    config_manager = ConfigManager()
    config_manager.config['ispconfig_url'] = data.get('ispconfig_url')
    config_manager.config['ispconfig_username'] = data.get('ispconfig_username')
    config_manager.config['ispconfig_password'] = data.get('ispconfig_password')
    config_manager.config['ispconfig_client_id'] = data.get('ispconfig_client_id')
    config_manager.save()

    logger.info(f"ISPConfig settings updated by {session['username']}")
    return jsonify({'status': 'success', 'message': 'ISPConfig settings updated'})


@app.route('/api/settings/password', methods=['POST'])
@login_required
def api_change_password():
    """Change admin password"""
    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not current_password or not new_password:
        return jsonify({'error': 'Both passwords required'}), 400

    admin = load_admin()

    if not check_password_hash(admin['password_hash'], current_password):
        return jsonify({'error': 'Current password incorrect'}), 401

    admin['password_hash'] = generate_password_hash(new_password)
    save_admin(admin)

    logger.info(f"Password changed by {session['username']}")
    flash('Password changed successfully', 'success')
    return jsonify({'status': 'success', 'message': 'Password changed'})


@app.route('/api/status')
@login_required
def api_status():
    """Get overall service status"""
    config_manager = ConfigManager()

    status = {
        'service': 'running',
        'domains': len(config_manager.config['domains']),
        'tokens': len(config_manager.config['auth_tokens']),
        'ispconfig_url': config_manager.config.get('ispconfig_url'),
        'timestamp': datetime.now().isoformat()
    }

    return jsonify(status)


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=False)
