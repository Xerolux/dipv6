# Web Admin Panel - IP.XEROLUX.NET

Secure web-based administration panel for managing DDNS domains and tokens.

## Features

✅ **Secure Login** - HTTPS with session management
✅ **Domain Management** - Add, edit, delete domains with IPv4/IPv6 toggle
✅ **Token Management** - Create and manage authentication tokens
✅ **Real-time Status** - View current IP addresses and update history
✅ **ISPConfig Settings** - Configure ISPConfig credentials from UI
✅ **Admin Panel** - Change admin password
✅ **Auto-refresh** - Dashboard updates every 30 seconds
✅ **Responsive Design** - Works on desktop, tablet, mobile

## Installation

### Step 1: Install Web-UI

The web-UI is included in your installation. Just copy the service file:

```bash
sudo cp /home/user/dipv6/dynipv6-webui.service /etc/systemd/system/
```

### Step 2: Start Web-UI Service

```bash
sudo systemctl daemon-reload
sudo systemctl start dynipv6-webui
sudo systemctl enable dynipv6-webui
```

### Step 3: Configure Nginx Reverse Proxy

Create `/etc/nginx/sites-available/webui`:

```nginx
# HTTP redirect
server {
    listen 80;
    listen [::]:80;
    server_name ip.example.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ip.example.com;

    ssl_certificate /etc/letsencrypt/live/ip.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ip.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy to Flask app
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Session timeout
        proxy_read_timeout 3600;
    }
}
```

Enable it:

```bash
sudo ln -s /etc/nginx/sites-available/webui /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Step 4: Get SSL Certificate

```bash
sudo certbot certonly -d ip.example.com
```

### Step 5: Access Web-UI

Open your browser and go to:
```
https://ip.example.com
```

**Default Login:**
- Username: `admin`
- Password: `admin123`

⚠️ **CHANGE THE PASSWORD IMMEDIATELY!**

## Usage

### Dashboard

Shows overview with:
- Total domains configured
- Active tokens
- IP addresses tracked
- Last updates
- Quick actions

### Domain Management

**Add Domain:**
1. Click "Add New Domain"
2. Enter domain name (e.g., `ipv6.example.com`)
3. Toggle IPv4/IPv6 as needed
4. Click "Add Domain"

**Edit Domain:**
1. Click "Edit" on domain row
2. Toggle IPv4/IPv6 enable/disable
3. Click "Save Changes"

**Delete Domain:**
1. Click "Delete" on domain row
2. Confirm deletion

### Token Management

**Create Token:**
1. Click "Create New Token"
2. Enter token name (e.g., "UniFi Lab")
3. Enter device name (e.g., "UniFi-Gateway-Lab")
4. Click "Create Token"
5. **Copy the token immediately** (you won't see it again!)

**Delete Token:**
1. Click "Delete" next to token
2. Confirm deletion

**Use Token in UniFi:**

Go to UniFi Settings → Internet → Dynamic DNS → Custom Service:

```
Server: https://ip.example.com/api/update?ipv6prefix=auto&ipv4=auto&token=YOUR_TOKEN
```

### Settings

**ISPConfig Configuration:**
1. Go to Settings
2. Enter ISPConfig URL (e.g., `https://192.168.1.100:8080`)
3. Enter ISPConfig username and password
4. Enter Client ID (0 for admin)
5. Click "Save Settings"

**Change Admin Password:**
1. Go to Settings
2. Enter current password
3. Enter new password
4. Confirm new password
5. Click "Change Password"

## Security

### Built-in Security Features

✅ **HTTPS/SSL only** - All communication encrypted
✅ **Session management** - 8-hour timeout
✅ **Secure cookies** - HttpOnly, Secure, SameSite flags
✅ **Password hashing** - Bcrypt hashing with salt
✅ **CSRF protection** - Cross-site request forgery prevention
✅ **Login logging** - All logins are logged
✅ **Token management** - Separate token per device
✅ **No token display** - Tokens only shown once on creation

### Security Best Practices

1. **Change default password immediately**
   ```bash
   # From browser: Settings → Change Password
   ```

2. **Use strong password**
   - Min 12 characters
   - Mix upper/lower case
   - Include numbers and symbols

3. **Keep HTTPS certificate valid**
   ```bash
   sudo certbot renew --dry-run  # Test renewal
   ```

4. **Restrict firewall access**
   ```bash
   sudo ufw allow from 192.168.0.0/16 to any port 443
   sudo ufw enable
   ```

5. **Monitor login attempts**
   ```bash
   journalctl -u dynipv6-webui | grep login
   ```

6. **Change tokens regularly**
   - Delete old tokens
   - Create new ones for devices

## Troubleshooting

### Can't access web-UI

**Check service status:**
```bash
systemctl status dynipv6-webui
journalctl -u dynipv6-webui -f
```

**Check port 5001:**
```bash
sudo netstat -tlnp | grep 5001
```

**Check Nginx:**
```bash
sudo nginx -t
sudo systemctl status nginx
```

### Forgot admin password

Reset default credentials:

```bash
sudo systemctl stop dynipv6-webui
sudo rm /etc/dynipv6/admin.json
sudo systemctl start dynipv6-webui
```

Default login is now `admin` / `admin123`

### Can't save settings

**Check permissions:**
```bash
sudo ls -la /etc/dynipv6/
sudo chown www-data:www-data /etc/dynipv6
```

**Check logs:**
```bash
journalctl -u dynipv6-webui -n 50
```

### SSL certificate errors

**Renew certificate:**
```bash
sudo certbot renew
sudo systemctl reload nginx
```

**Check certificate validity:**
```bash
openssl x509 -in /etc/letsencrypt/live/ip.example.com/fullchain.pem -noout -dates
```

## Architecture

```
┌──────────────────────────────────────┐
│   Your Computer / Smartphone         │
│   Browser: https://ip.example.com   │
└──────────────────┬──────────────────┘
                   │ HTTPS
                   ▼
┌──────────────────────────────────────┐
│   Nginx Reverse Proxy (443)          │
│   - SSL/TLS termination              │
│   - Security headers                 │
└──────────────────┬──────────────────┘
                   │ HTTP
                   ▼
┌──────────────────────────────────────┐
│   Flask Web-UI (Port 5001)           │
│   - Session management               │
│   - Authentication                   │
│   - Domain management                │
│   - Token management                 │
└──────────────────┬──────────────────┘
                   │
          ┌────────┴────────┐
          │                 │
          ▼                 ▼
   /etc/dynipv6/    /var/lib/dynipv6/
   config.json      (status data)
```

## File Locations

| File | Location | Purpose |
|------|----------|---------|
| Web UI Code | `/opt/dynipv6/webui.py` | Flask application |
| Templates | `/opt/dynipv6/templates/` | HTML templates |
| Config | `/etc/dynipv6/config.json` | Configuration |
| Admin | `/etc/dynipv6/admin.json` | Admin credentials |
| Status | `/var/lib/dynipv6/` | DNS status files |
| Systemd | `/etc/systemd/system/dynipv6-webui.service` | Service definition |
| Nginx | `/etc/nginx/sites-available/webui` | Reverse proxy |

## API Reference

The web-UI uses the same API as UniFi clients:

### Update DNS

```bash
curl "https://ip.example.com/api/update?ipv6prefix=auto&ipv4=auto&token=TOKEN"
```

### Check Status

```bash
curl "https://ip.example.com/api/status?token=TOKEN"
```

### Health Check

```bash
curl "https://ip.example.com/api/health"
```

## Logs

### View Web-UI Logs

```bash
# Real-time
journalctl -u dynipv6-webui -f

# Last 50 lines
journalctl -u dynipv6-webui -n 50

# Errors only
journalctl -u dynipv6-webui | grep ERROR
```

### View Service Logs

```bash
journalctl -u dynipv6 -f
```

### View Nginx Logs

```bash
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log
```

## Configuration Examples

### Single Domain (both IPv4 and IPv6)

1. Domain: `dns.example.com`
2. Enable both IPv4 and IPv6
3. Create token: "DNS Device"
4. Use in UniFi: `https://ip.example.com/api/update?ipv6prefix=auto&ipv4=auto&token=TOKEN`

### Separate Domains (IPv4 and IPv6)

1. Domain 1: `ipv4.example.com` - IPv4 only
2. Domain 2: `ipv6.example.com` - IPv6 only
3. Create separate tokens for each
4. Use in UniFi with separate DDNS configs

### Multiple UniFi Devices

1. Create domain for each site/device
2. Create separate token for each
3. Configure each UniFi with its own token and domain

## Support

For issues or questions:
1. Check logs: `journalctl -u dynipv6-webui -f`
2. Review documentation: `README.md`, `ISPCONFIG_SETUP.md`
3. Test connectivity: `curl https://ip.example.com/api/health`
