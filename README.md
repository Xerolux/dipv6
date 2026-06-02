# Dynamic IPv6/IPv4 DDNS Service

A self-hosted Dynamic DNS service supporting both IPv4 and IPv6 with dual-domain configuration. Perfect for ISPConfig with UniFi network integration.

## Features

🌐 **Dual IP Support**
- IPv4 and IPv6 on separate domains
- Auto-detect client IP or manual specification

🔐 **Security**
- SSL/TLS support (Let's Encrypt ready)
- Token-based authentication
- HTTPS-only communication

🔗 **ISPConfig Integration**
- Automatic DNS record updates
- Direct ISPConfig API integration
- Zone management support

🎯 **UniFi Compatible**
- Supports UniFi's custom DDNS service
- Drop-in replacement for dynv6.com
- Easy configuration via UniFi UI

⚡ **Systemd Service**
- Auto-start on boot
- Automatic restart on failure
- Full logging support

## Quick Start

### Installation

```bash
# Clone and install
git clone https://github.com/xerolux/dipv6.git
cd dipv6

# Run installer (requires root)
sudo bash install.sh
```

### Configuration

1. **Edit config file:**
```bash
sudo nano /etc/dynipv6/config.json
```

2. **Set ISPConfig credentials:**
```json
{
  "ispconfig_url": "https://your-ispconfig-server:8080",
  "ispconfig_username": "admin",
  "ispconfig_password": "your-password",
  "ipv6_domain": "ipv6.xerolux.net",
  "ipv4_domain": "ipv4.xerolux.net",
  "auth_tokens": {
    "your-secret-token": "UniFi-Device-Name"
  }
}
```

3. **Setup SSL (Let's Encrypt):**
```bash
sudo certbot certonly -d ipv6.xerolux.net -d ipv4.xerolux.net
```

4. **Configure reverse proxy (Nginx or Apache)**

See example configs in `/usr/share/doc/dynipv6/`

5. **Start service:**
```bash
sudo systemctl start dynipv6
sudo systemctl enable dynipv6
```

## Usage

### From UniFi

1. Settings → Internet → Dynamic DNS
2. Create New → Custom Service
3. Hostname: `ipv6.xerolux.net`
4. Server: `https://ipv6.xerolux.net/api/update?ipv6prefix=auto&token=YOUR_TOKEN`

See [UNIFI_SETUP.md](UNIFI_SETUP.md) for detailed instructions.

### API Endpoints

**Update DNS:**
```bash
GET|POST /api/update?ipv6prefix=auto&ipv4=auto&token=TOKEN
```

**Check Status:**
```bash
GET /api/status?token=TOKEN
```

**Health Check (no auth):**
```bash
GET /api/health
```

## File Structure

```
/opt/dynipv6/
├── dynipv6_service.py      # Main service application

/etc/dynipv6/
├── config.json             # Configuration (create after install)

/var/lib/dynipv6/
├── ipv6.xerolux.net_AAAA.json   # IPv6 record
├── ipv4.xerolux.net_A.json      # IPv4 record

/var/log/dynipv6/
├── dynipv6.log             # Service logs
```

## Architecture

```
┌─────────────┐
│   UniFi     │
│  Network    │
└──────┬──────┘
       │ HTTPS
       ├─────────────────────────────┐
       │                             │
       ▼                             ▼
┌─────────────────┐        ┌──────────────────┐
│ ipv6.xerolux    │        │ ipv4.xerolux     │
│    .net         │        │    .net          │
│ (Nginx/Apache)  │        │ (Nginx/Apache)   │
└────────┬────────┘        └────────┬─────────┘
         │                          │
         └──────────────┬───────────┘
                        │ Proxy
                        ▼
            ┌───────────────────────┐
            │  dynipv6_service.py   │
            │  (Port 5000 local)    │
            └───────────┬───────────┘
                        │
          ┌─────────────┴──────────────┐
          │                            │
          ▼                            ▼
    ┌──────────────┐          ┌──────────────┐
    │  ISPConfig   │          │  DNS Storage │
    │  (API)       │          │  /var/lib/   │
    └──────────────┘          └──────────────┘
```

## Dependencies

- Python 3.7+
- Flask 2.0+
- flask-cors
- requests
- Gunicorn (optional, for production)

Installed automatically with `install.sh`

## Configuration Options

### config.json

```json
{
  "ipv6_domain": "ipv6.xerolux.net",        // IPv6 domain name
  "ipv4_domain": "ipv4.xerolux.net",        // IPv4 domain name
  "ispconfig_url": "https://...:8080",      // ISPConfig API endpoint
  "ispconfig_username": "admin",             // ISPConfig username
  "ispconfig_password": "password",          // ISPConfig password
  "ispconfig_client_id": "0",                // ISPConfig client ID
  "auth_tokens": {                           // Token -> Device mapping
    "token123": "Device-Name"
  },
  "ssl_cert": "/etc/letsencrypt/.../fullchain.pem",
  "ssl_key": "/etc/letsencrypt/.../privkey.pem",
  "port": 443,                               // Service port
  "host": "0.0.0.0"                          // Bind address
}
```

## Managing Tokens

### Add New Token

```bash
sudo nano /etc/dynipv6/config.json
# Add to auth_tokens
sudo systemctl restart dynipv6
```

### Generate Secure Token

```bash
openssl rand -hex 32
# Example output: a7f3c8d9e2b1f0c4a5d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8
```

## Monitoring

### Check Service Status
```bash
systemctl status dynipv6
```

### View Live Logs
```bash
journalctl -u dynipv6 -f
```

### View Historical Logs
```bash
cat /var/log/dynipv6/dynipv6.log
```

### Monitor Specific Domain
```bash
tail -f /var/log/dynipv6/dynipv6.log | grep "ipv6.xerolux.net"
```

## Systemd Integration

The service is fully integrated with systemd:

```bash
# Start
sudo systemctl start dynipv6

# Stop
sudo systemctl stop dynipv6

# Enable auto-start on boot
sudo systemctl enable dynipv6

# Disable auto-start
sudo systemctl disable dynipv6

# Restart
sudo systemctl restart dynipv6

# Check detailed status
systemctl status dynipv6 -l
```

## Security Considerations

⚠️ **Important:**

1. **Always use HTTPS**: Never use HTTP for DNS updates
2. **Use strong tokens**: Generate with `openssl rand -hex 32`
3. **Rotate tokens**: Remove old tokens regularly
4. **Secure config file**: `chmod 600 /etc/dynipv6/config.json`
5. **Monitor logs**: Watch for suspicious update attempts
6. **Firewall rules**: Restrict access if possible
7. **ISPConfig API**: Use dedicated API account with limited permissions

## Troubleshooting

### Service won't start
```bash
journalctl -u dynipv6 -n 50 -e
```

### SSL errors
```bash
# Check certificate
openssl x509 -in /path/to/cert.pem -text -noout
# Verify domain
curl -v https://ipv6.xerolux.net/api/health
```

### DNS not updating
1. Check token is correct
2. Verify ISPConfig credentials
3. Check firewall allows outbound HTTPS
4. Review logs for ISPConfig errors

### 401 Unauthorized
- Token is missing or incorrect
- Check URL parameter: `?token=YOUR_TOKEN`
- Check config.json has token defined

## Production Deployment

For production, use Gunicorn with Nginx:

```bash
# Install Gunicorn
pip3 install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 127.0.0.1:5000 dynipv6_service:app

# Use systemd to manage (see systemd docs)
```

Or modify dynipv6.service to use Gunicorn instead of Python directly.

## Comparison

| Feature | dynv6.com | Our Service | dyndns.org |
|---------|-----------|-------------|-----------|
| IPv4 | ✅ | ✅ | ✅ |
| IPv6 | ✅ | ✅ | ❌ |
| Dual Domain | ❌ | ✅ | ❌ |
| Self-hosted | ❌ | ✅ | ❌ |
| ISPConfig | ❌ | ✅ | ❌ |
| Free | ✅ | ✅ | ❌ |
| Privacy | ❌ | ✅ | ❌ |

## License

MIT License - See LICENSE file

## Support

For issues or feature requests, create an issue on GitHub or check the documentation:
- [UniFi Setup Guide](UNIFI_SETUP.md)
- Service logs: `/var/log/dynipv6/dynipv6.log`
- Configuration: `/etc/dynipv6/config.json`

## Contributing

Pull requests welcome! Please ensure:
- Code follows PEP 8
- Commit messages are descriptive
- Documentation is updated

## Changelog

### Version 1.0.0 (2026-06-02)
- Initial release
- IPv4 and IPv6 support
- ISPConfig integration
- UniFi compatibility
- Systemd integration