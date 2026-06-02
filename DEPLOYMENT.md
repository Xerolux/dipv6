# Deployment Guide

This guide covers deploying the Dynamic IPv6/IPv4 DDNS Service on your ISPConfig server.

## Table of Contents

1. [Bare Metal Installation](#bare-metal-installation)
2. [Docker Deployment](#docker-deployment)
3. [ISPConfig Integration](#ispconfig-integration)
4. [SSL/TLS Certificate Setup](#ssltls-certificate-setup)
5. [Reverse Proxy Configuration](#reverse-proxy-configuration)
6. [Production Considerations](#production-considerations)

## Bare Metal Installation

### Prerequisites

- Ubuntu 20.04+ or Debian 10+
- Root access
- ISPConfig with admin privileges
- Domain names: `ipv6.xerolux.net` and `ipv4.xerolux.net`

### Step 1: Download and Install

```bash
# Clone repository
git clone https://github.com/xerolux/dipv6.git
cd dipv6

# Run installer
sudo bash install.sh

# Check installation
sudo systemctl status dynipv6
```

### Step 2: Configure Service

Edit `/etc/dynipv6/config.json`:

```bash
sudo nano /etc/dynipv6/config.json
```

Update these fields:

```json
{
  "ispconfig_url": "https://your-ispconfig-ip:8080",
  "ispconfig_username": "admin",
  "ispconfig_password": "your-password",
  "ipv6_domain": "ipv6.xerolux.net",
  "ipv4_domain": "ipv4.xerolux.net",
  "auth_tokens": {
    "generate-strong-token-here": "UniFi-Device"
  }
}
```

#### Generate Strong Token

```bash
openssl rand -hex 32
```

### Step 3: SSL Certificate Setup

Using Let's Encrypt:

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate for both domains
sudo certbot certonly --nginx -d ipv6.xerolux.net -d ipv4.xerolux.net

# Verify paths in config.json
sudo ls -la /etc/letsencrypt/live/ipv6.xerolux.net/
```

### Step 4: Configure Reverse Proxy

#### Option A: Nginx (Recommended)

```bash
# Copy example configuration
sudo cp nginx.conf /etc/nginx/sites-available/dynipv6

# Enable site
sudo ln -s /etc/nginx/sites-available/dynipv6 /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

#### Option B: Apache

```bash
# Enable required modules
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod ssl

# Copy configuration
sudo cp apache-example.conf /etc/apache2/sites-available/dynipv6.conf

# Enable site
sudo a2ensite dynipv6

# Test configuration
sudo apache2ctl configtest

# Restart Apache
sudo systemctl restart apache2
```

### Step 5: Start Service

```bash
# Start service
sudo systemctl start dynipv6

# Enable auto-start
sudo systemctl enable dynipv6

# Check status
sudo systemctl status dynipv6

# View logs
sudo journalctl -u dynipv6 -f
```

## Docker Deployment

### Prerequisites

- Docker 20.10+
- Docker Compose 1.29+
- Let's Encrypt certificates

### Step 1: Prepare Configuration

```bash
# Copy and edit config
cp config.json.example config.json
nano config.json
```

### Step 2: Update Domains (Optional)

In `docker-compose.yml`, replace `ipv6.xerolux.net` and `ipv4.xerolux.net` with your domains.

### Step 3: Start Services

```bash
# Build and start
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f dynipv6
```

### Step 4: Verify

```bash
# Test API
curl -k http://localhost:5000/api/health

# Check through Nginx
curl https://ipv6.xerolux.net/api/health
```

### Docker Useful Commands

```bash
# Stop services
docker-compose down

# Rebuild image
docker-compose up --build -d

# View logs for specific service
docker-compose logs dynipv6

# Execute command in container
docker-compose exec dynipv6 ls /var/lib/dynipv6
```

## ISPConfig Integration

### DNS Zone Setup

1. Login to ISPConfig
2. Go to **DNS** → **Zones**
3. Ensure zones exist for:
   - `ipv6.xerolux.net`
   - `ipv4.xerolux.net`

### DNS Records Setup

For each domain, create A/AAAA records:

**For ipv6.xerolux.net:**
- Type: AAAA
- Name: (leave blank for root)
- Data: (will be updated by service)
- TTL: 3600

**For ipv4.xerolux.net:**
- Type: A
- Name: (leave blank for root)
- Data: (will be updated by service)
- TTL: 3600

### ISPConfig API Credentials

The service needs ISPConfig API access. Make sure:

1. API is enabled in ISPConfig Settings
2. API user has DNS zone permissions
3. Credentials are correct in config.json

## SSL/TLS Certificate Setup

### Automatic with Let's Encrypt

```bash
# Using certbot with Nginx
sudo certbot certonly --nginx \
  -d ipv6.xerolux.net \
  -d ipv4.xerolux.net

# Or using standalone
sudo certbot certonly --standalone \
  -d ipv6.xerolux.net \
  -d ipv4.xerolux.net
```

### Auto-Renewal

```bash
# Certbot sets up auto-renewal automatically
# Verify it's enabled
sudo systemctl enable certbot.timer
sudo systemctl status certbot.timer
```

### Manual Certificate

If not using Let's Encrypt:

1. Place certificate at: `/etc/letsencrypt/live/ipv6.xerolux.net/fullchain.pem`
2. Place key at: `/etc/letsencrypt/live/ipv6.xerolux.net/privkey.pem`
3. Update paths in config.json if different

## Reverse Proxy Configuration

### Nginx Configuration

The provided `nginx.conf` includes:

- HTTP to HTTPS redirect
- Security headers (HSTS, X-Frame-Options, etc.)
- Gzip compression
- Caching for performance
- Separate servers for each domain
- Health check endpoint

Features:

```nginx
# Security headers
add_header Strict-Transport-Security "max-age=31536000";

# Caching
proxy_cache dynipv6_cache;
proxy_cache_valid 200 1m;

# Performance
gzip on;
tcp_nodelay on;
keepalive_timeout 65;
```

### Apache Configuration

See `apache-example.conf` for Apache VirtualHost setup.

## Production Considerations

### 1. Firewall Rules

```bash
# Allow HTTPS
sudo ufw allow 443/tcp

# Allow HTTP (for ACME challenge)
sudo ufw allow 80/tcp

# Block direct access to service port
sudo ufw deny 5000/tcp
```

### 2. Monitoring

Set up monitoring for:

```bash
# Service health
systemctl status dynipv6

# Port listening
sudo netstat -tlnp | grep python

# Logs for errors
journalctl -u dynipv6 --since "2 hours ago" | grep ERROR

# Certificate expiration
sudo certbot renew --dry-run
```

### 3. Backup Configuration

```bash
# Backup config and data
sudo tar -czf dynipv6_backup.tar.gz \
  /etc/dynipv6 \
  /var/lib/dynipv6

# Restore
sudo tar -xzf dynipv6_backup.tar.gz -C /
```

### 4. Performance Tuning

#### Nginx Tuning

```nginx
# Worker processes
worker_processes auto;

# Connections per worker
worker_connections 2048;

# Buffer sizes
client_body_buffer_size 128k;
proxy_buffer_size 128k;

# Timeouts
proxy_connect_timeout 10s;
proxy_send_timeout 30s;
proxy_read_timeout 30s;
```

#### Python Tuning

Modify service startup for production:

```bash
# Using Gunicorn (edit dynipv6.service)
ExecStart=/usr/bin/gunicorn \
  --workers 4 \
  --worker-class sync \
  --timeout 120 \
  --access-logfile /var/log/dynipv6/access.log \
  dynipv6_service:app
```

### 5. Security Hardening

```bash
# Restrict config file permissions
sudo chmod 600 /etc/dynipv6/config.json

# View-only access to logs
sudo chmod 640 /var/log/dynipv6/dynipv6.log

# Only www-data can write to data directory
sudo chown www-data:www-data /var/lib/dynipv6
sudo chmod 750 /var/lib/dynipv6

# Set SELinux context (if applicable)
sudo semanage fcontext -a -t httpd_sys_rw_content_t "/var/lib/dynipv6(/.*)?"
```

### 6. High Availability

For multiple servers:

```bash
# Use shared storage for DNS records
# Example: NFS mount to /var/lib/dynipv6

# Or sync between servers
rsync -avz /var/lib/dynipv6 remote:/var/lib/dynipv6
```

### 7. Logging & Monitoring

```bash
# Enable structured logging
# Edit dynipv6_service.py to use JSON logging

# Monitor with external tool
# Example: ELK Stack, Syslog, etc.

# Systemd journal forwarding
sudo journalctl -u dynipv6 --follow
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
journalctl -u dynipv6 -n 50 -e

# Check syntax
python3 -m py_compile dynipv6_service.py

# Check permissions
ls -la /etc/dynipv6/config.json
```

### Nginx/Apache Not Proxying

```bash
# Check reverse proxy is running
systemctl status nginx
# or
systemctl status apache2

# Test local connection
curl -v http://127.0.0.1:5000/api/health

# Check proxy logs
tail -f /var/log/nginx/error.log
# or
tail -f /var/log/apache2/error.log
```

### SSL Certificate Issues

```bash
# Check certificate
openssl x509 -in /etc/letsencrypt/live/ipv6.xerolux.net/fullchain.pem -text

# Test SSL
openssl s_client -connect ipv6.xerolux.net:443

# Check renewal
sudo certbot renew --dry-run
```

### ISPConfig API Errors

```bash
# Check API is enabled
# Log into ISPConfig → System → Settings → API

# Test ISPConfig connectivity
curl -k https://your-ispconfig:8080/api/

# Check credentials in config.json
sudo cat /etc/dynipv6/config.json | grep ispconfig
```

## Next Steps

1. ✅ Installation complete
2. ✅ SSL configured
3. ✅ Reverse proxy running
4. 👉 Configure UniFi (see UNIFI_SETUP.md)
5. 👉 Monitor service regularly
6. 👉 Set up automated backups
