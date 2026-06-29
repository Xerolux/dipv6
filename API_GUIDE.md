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

The endpoint iterates over **every domain configured in the Web-UI** (`config['domains']`)
and applies the update to each one based on its individual settings:

1. **IPv6/IPv4 is stored** locally in `/var/lib/dynipv6/`
2. **Per domain**, the update is routed based on its `dynamic_dns.service`:
   - `custom` → sent to the domain's custom DDNS endpoint (Hostname / Username / Password / Server from the Web-UI)
   - otherwise → **ISPConfig** updates the AAAA / A record
3. Each domain's `ipv4_enabled` / `ipv6_enabled` toggles are respected
4. If `use_calculated_ipv6` is set, the calculated host IP (e.g. `::1`) is published instead of the raw prefix
5. **Optional: Nginx is updated** if `nginx_update_enabled: true` (ISPConfig path only)

The config file is re-read on every request, so changes made in the Web-UI take
effect immediately — no service restart required.

> **Legacy fallback:** if `domains` is empty, the service falls back to the single
> `ipv6_domain` / `ipv4_domain` settings.

**Multi-domain response example:**
```json
{
  "status": "success",
  "timestamp": "2026-06-29T12:30:45.123456",
  "updates": {
    "home.blueml.one": {
      "method": "ispconfig",
      "ipv6": { "status": "success", "address": "2001:db8::1", "nginx_updated": false }
    },
    "custom.blueml.one": {
      "method": "custom",
      "result": { "status": "success", "message": "Update sent to https://provider.example.com/nic/update" }
    }
  }
}
```

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
