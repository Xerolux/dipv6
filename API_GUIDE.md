# DynIPv6 API Guide

## UniFi Integration - IPv6 Update

**Base URL:** `https://dyn.blueml.one`

### Update IPv6 Address

Send the current IPv6 address from UniFi Dream Machine or any client.

**Endpoint:**
```
GET/POST /api/update?token=YOUR_TOKEN&ipv6prefix=2001:db8::1
```

**Parameters:**
- `token` (required): Authentication token from config
- `ipv6prefix` (required): IPv6 address or prefix (e.g., `2001:db8::1` or `2001:db8:1234:5600::/56`)
- `ipv4` (optional): IPv4 address
- `hostname` (optional): Device hostname

**Examples:**

```bash
# Update IPv6 from UniFi
curl "https://dyn.blueml.one/api/update?token=your-secret-token&ipv6prefix=2001:db8::1"

# Update with hostname
curl "https://dyn.blueml.one/api/update?token=your-secret-token&ipv6prefix=2001:db8::1&hostname=unifi-dream-machine"

# Using POST
curl -X POST "https://dyn.blueml.one/api/update" \
  -d "token=your-secret-token&ipv6prefix=2001:db8::1"
```

**Response:**
```json
{
  "status": "success",
  "timestamp": "2026-06-29T12:30:45.123456",
  "updates": {
    "ipv6": {
      "status": "success",
      "address": "2001:db8::1",
      "nginx_updated": false
    }
  }
}
```

## What Happens on Update

1. **IPv6 is stored** locally in `/var/lib/dynipv6/`
2. **ISPConfig is updated** with the new AAAA record for the configured domain
3. **DNS propagates** - `home.blueml.one` now resolves to the new IPv6 address
4. **Optional: Nginx is updated** if `nginx_update_enabled: true` in config

## UniFi Setup

In UniFi Dream Machine, configure Dynamic DNS with:
- **Service:** Custom
- **Hostname:** `home.blueml.one`
- **Username:** (any value, e.g., `unifi`)
- **Password:** (your token from auth_tokens)
- **Server:** `https://dyn.blueml.one/api/update`

UniFi will automatically send the IPv6 prefix to this endpoint.

## Configuration

Edit `/etc/dynipv6/config.json`:

```json
{
  "ipv6_domain": "home.blueml.one",
  "ispconfig_url": "https://your-ispconfig:8080",
  "ispconfig_username": "admin",
  "ispconfig_password": "password",
  "auth_tokens": {
    "your-secret-token": "UniFi-Device"
  },
  "nginx_update_enabled": false
}
```

- **ipv6_domain:** Domain that receives IPv6 AAAA record updates
- **ispconfig_*:** ISPConfig credentials for DNS updates
- **auth_tokens:** Tokens UniFi uses for authentication
- **nginx_update_enabled:** Enable Nginx configuration updates (default: false)
