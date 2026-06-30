#!/bin/bash
###############################################################################
# Installer for dynipv6 - minimal self-hosted Dynamic DNS service
###############################################################################
set -e

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root." >&2
    exit 1
fi

echo "=== Installing dynipv6 ==="

apt-get update
apt-get install -y python3 python3-venv

# Directories
mkdir -p /opt/dynipv6 /etc/dynipv6 /var/lib/dynipv6

# Python venv
python3 -m venv /opt/dynipv6/venv
/opt/dynipv6/venv/bin/pip install --upgrade pip
/opt/dynipv6/venv/bin/pip install -r requirements.txt

# Program files
cp dynipv6.py ispconfig_api.py /opt/dynipv6/
cp dynipv6.service /etc/systemd/system/

# Config + nginx template (don't overwrite existing config on upgrade)
if [ ! -f /etc/dynipv6/config.json ]; then
    cp config.json.example /etc/dynipv6/config.json
    echo "Created /etc/dynipv6/config.json - edit it before starting!"
else
    echo "Keeping existing /etc/dynipv6/config.json"
fi
cp nginx.conf.template /etc/dynipv6/nginx.conf.template

chmod 600 /etc/dynipv6/config.json

systemctl daemon-reload

echo ""
echo "=== Done ==="
echo "Next steps:"
echo "  1. Edit /etc/dynipv6/config.json (mode, domain, username, password, nginx, ispconfig)"
echo "  2. Adjust /etc/dynipv6/nginx.conf.template to your needs"
echo "  3. systemctl enable --now dynipv6"
echo "  4. journalctl -u dynipv6 -f"
