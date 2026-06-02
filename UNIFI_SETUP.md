# UniFi DDNS Integration Guide

## Overview

This guide explains how to configure UniFi to use your custom Dynamic IPv6/IPv4 DDNS service.

## Prerequisites

- ✅ dynipv6 service installed and running
- ✅ SSL/HTTPS configured (Let's Encrypt)
- ✅ Valid authentication token configured in `/etc/dynipv6/config.json`
- ✅ Reverse proxy (Nginx/Apache) configured
- ✅ Firewall rules allowing HTTPS (port 443)

## UniFi Configuration Steps

### 1. Create Custom DDNS Service

In UniFi Network Application:

1. Go to **Settings** → **Internet** → **Dynamic DNS**
2. Click **Create New Dynamic DNS**
3. Select **Service Type: Custom**

### 2. Configuration Fields (as shown in your screenshot)

Fill in the following fields:

| Field | Value |
|-------|-------|
| **Service** | Custom |
| **Hostname** | `ipv6.xerolux.net` (for IPv6) or `ipv4.xerolux.net` (for IPv4) |
| **Username** | `ignored` (can be any value, token goes in URL) |
| **Password** | `ignored` (can be any value, token goes in URL) |
| **Server** | `https://ipv6.xerolux.net/api/update?ipv6prefix=auto&token=YOUR_TOKEN_HERE` |

### 3. IPv6 Setup (ipv6.xerolux.net)

**Example Server URL for IPv6:**
```
https://ipv6.xerolux.net/api/update?ipv6prefix=auto&token=your-secret-token
```

### 4. IPv4 Setup (ipv4.xerolux.net)

**Example Server URL for IPv4:**
```
https://ipv4.xerolux.net/api/update?ipv4=auto&token=your-secret-token
```

### 5. Both IPv6 and IPv4 (Single Configuration)

**If using single domain for both:**
```
https://ipv6.xerolux.net/api/update?ipv6prefix=auto&ipv4=auto&token=your-secret-token
```

## API Endpoints

### Update DNS Records

**Endpoint:** `POST/GET /api/update`

**Parameters:**
- `token` (required): Authentication token
- `ipv6prefix` (optional): IPv6 address or "auto" for client IP
- `ipv4` (optional): IPv4 address or "auto" for client IP
- `hostname` (optional): Source hostname/device name

**Examples:**

Update IPv6 automatically:
```
https://ipv6.xerolux.net/api/update?ipv6prefix=auto&token=TOKEN
```

Update both IPv4 and IPv6:
```
https://ipv6.xerolux.net/api/update?ipv6prefix=auto&ipv4=auto&token=TOKEN
```

Explicit IP:
```
https://ipv6.xerolux.net/api/update?ipv6prefix=2001:db8::1&token=TOKEN
```

### Check Current Status

**Endpoint:** `GET /api/status`

```
https://ipv6.xerolux.net/api/status?token=TOKEN
```

**Response:**
```json
{
  "status": "success",
  "ipv6": {
    "value": "2001:db8::1",
    "type": "AAAA",
    "domain": "ipv6.xerolux.net",
    "updated": "2026-06-02T23:30:45.123456"
  },
  "ipv4": {
    "value": "192.0.2.1",
    "type": "A",
    "domain": "ipv4.xerolux.net",
    "updated": "2026-06-02T23:30:45.123456"
  }
}
```

### Health Check

**Endpoint:** `GET /api/health`

No authentication required. Used for uptime monitoring.

```
https://ipv6.xerolux.net/api/health
```

## Token Management

### Generate New Token

Edit `/etc/dynipv6/config.json`:

```json
{
  "auth_tokens": {
    "your-secret-token-123": "UniFi-Device-Name",
    "another-long-token-456": "Secondary-Device"
  }
}
```

Then restart the service:
```bash
systemctl restart dynipv6
```

### Security Best Practices

1. **Use strong tokens**: Generate with `openssl rand -hex 32`
2. **Rotate tokens regularly**: Remove old tokens from config
3. **Use HTTPS only**: Never use HTTP for updates
4. **Restrict firewall**: Only allow necessary IPs to update DNS
5. **Monitor logs**: Check `/var/log/dynipv6/dynipv6.log`

## Testing from UniFi

1. In UniFi, go to the DDNS configuration
2. Click the test icon next to your DDNS entry
3. Check `/var/log/dynipv6/dynipv6.log` for update confirmation:
   ```
   2026-06-02 23:30:45 - dynipv6 - INFO - Updated ipv6.xerolux.net (AAAA): 2001:db8::1
   ```

## Troubleshooting

### Service Not Running

```bash
systemctl status dynipv6
journalctl -u dynipv6 -n 50 -f
```

### SSL Certificate Issues

```bash
# Check certificate validity
openssl x509 -in /etc/letsencrypt/live/ipv6.xerolux.net/fullchain.pem -text -noout
```

### DNS Not Updating

1. Check authentication token is correct
2. Verify ISPConfig credentials in `/etc/dynipv6/config.json`
3. Check firewall allows outbound HTTPS to ISPConfig
4. Review logs: `journalctl -u dynipv6 -f`

### Can't Connect to Service

```bash
# Test local connectivity
curl -k https://localhost/api/health

# Test from another machine
curl -k https://ipv6.xerolux.net/api/health
```

## Advanced Configuration

### Multiple Devices

Create separate tokens for each UniFi device:

```json
{
  "auth_tokens": {
    "token-unifi-lab": "Lab-UniFi-Device",
    "token-unifi-prod": "Production-UniFi-Device",
    "token-unifi-remote": "Remote-Site-Device"
  }
}
```

### ISPConfig Integration

The service automatically updates DNS records in ISPConfig. Ensure:

1. ISPConfig API access is enabled
2. Admin credentials are correct in config
3. Client ID is set appropriately

For ISPConfig API documentation, see: https://www.ispconfig.org/documentation/

## Example UniFi Screenshots

See the screenshot provided - it shows:
- Service: **Custom**
- Hostname: **ipv6.xerolux.net**
- Username: `ignored`
- Password: `ignored`  
- Server: `https://ipv6.xerolux.net/api/update?ipv6prefix=auto&token=YOUR_TOKEN`

## Support

For issues, check:
1. Service logs: `journalctl -u dynipv6 -f`
2. Configuration: `/etc/dynipv6/config.json`
3. File permissions: `ls -la /var/lib/dynipv6/`

## Comparison with dynv6

| Feature | dynv6.com | Our Service |
|---------|-----------|-------------|
| IPv4 Support | ✅ | ✅ |
| IPv6 Support | ✅ | ✅ |
| Dual Domain | ❌ | ✅ |
| Self-hosted | ❌ | ✅ |
| ISPConfig Integration | ❌ | ✅ |
| UniFi Compatible | ✅ | ✅ |
| Cost | $$ | Free |
| Data Privacy | Shared | Your Server |
