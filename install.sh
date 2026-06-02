#!/bin/bash
###############################################################################
# Installation script for Dynamic IPv6/IPv4 DDNS Service
# For Ubuntu/Debian with ISPConfig
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Dynamic IPv6/IPv4 DDNS Service Installer ===${NC}"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}"
   exit 1
fi

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
apt-get update
apt-get install -y python3 python3-pip python3-venv

pip3 install flask flask-cors requests gunicorn

# Create directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p /opt/dynipv6
mkdir -p /etc/dynipv6
mkdir -p /var/lib/dynipv6
mkdir -p /var/log/dynipv6
mkdir -p /usr/share/doc/dynipv6

# Copy files
echo -e "${YELLOW}Installing service files...${NC}"
cp dynipv6_service.py /opt/dynipv6/
cp dynipv6.service /etc/systemd/system/
cp config.json.example /etc/dynipv6/config.json || true
cp README.md /usr/share/doc/dynipv6/

# Set permissions
chmod 755 /opt/dynipv6/dynipv6_service.py
chmod 644 /etc/systemd/system/dynipv6.service
chmod 644 /etc/dynipv6/config.json
chown -R www-data:www-data /var/lib/dynipv6
chown -R www-data:www-data /var/log/dynipv6
chown -R www-data:www-data /opt/dynipv6

# Create nginx/Apache reverse proxy example
echo -e "${YELLOW}Creating reverse proxy configuration examples...${NC}"

# Nginx example
cat > /usr/share/doc/dynipv6/nginx-example.conf << 'EOF'
# Nginx reverse proxy for dynipv6 service
# Place this in /etc/nginx/sites-available/ and enable with a2ensite

# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name ipv6.xerolux.net ipv4.xerolux.net;
    return 301 https://$server_name$request_uri;
}

# HTTPS servers
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ipv6.xerolux.net;

    ssl_certificate /etc/letsencrypt/live/ipv6.xerolux.net/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ipv6.xerolux.net/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ipv4.xerolux.net;

    ssl_certificate /etc/letsencrypt/live/ipv4.xerolux.net/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ipv4.xerolux.net/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Apache example
cat > /usr/share/doc/dynipv6/apache-example.conf << 'EOF'
# Apache reverse proxy for dynipv6 service
# Place this in /etc/apache2/sites-available/ and enable with a2ensite

# Ensure mod_proxy and mod_ssl are enabled:
# a2enmod proxy
# a2enmod proxy_http
# a2enmod ssl

# HTTP to HTTPS redirect
<VirtualHost *:80>
    ServerName ipv6.xerolux.net
    ServerName ipv4.xerolux.net
    Redirect permanent / https://ipv6.xerolux.net/
</VirtualHost>

# IPv6 DDNS endpoint
<VirtualHost *:443>
    ServerName ipv6.xerolux.net
    DocumentRoot /var/www/html

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/ipv6.xerolux.net/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/ipv6.xerolux.net/privkey.pem

    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:5000/
    ProxyPassReverse / http://127.0.0.1:5000/
</VirtualHost>

# IPv4 DDNS endpoint
<VirtualHost *:443>
    ServerName ipv4.xerolux.net
    DocumentRoot /var/www/html

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/ipv4.xerolux.net/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/ipv4.xerolux.net/privkey.pem

    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:5000/
    ProxyPassReverse / http://127.0.0.1:5000/
</VirtualHost>
EOF

echo -e "${YELLOW}Reload systemd daemon...${NC}"
systemctl daemon-reload

echo ""
echo -e "${GREEN}=== Installation Complete ===${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Edit /etc/dynipv6/config.json with your ISPConfig credentials"
echo "2. Configure SSL certificates (use Let's Encrypt):"
echo "   certbot certonly -d ipv6.xerolux.net -d ipv4.xerolux.net"
echo "3. Configure nginx or Apache as reverse proxy (see /usr/share/doc/dynipv6/)"
echo "4. Start the service:"
echo "   systemctl start dynipv6"
echo "   systemctl enable dynipv6"
echo "5. Check status:"
echo "   systemctl status dynipv6"
echo "   journalctl -u dynipv6 -f"
echo ""
echo -e "${YELLOW}For UniFi configuration, see UNIFI_SETUP.md${NC}"
echo ""
