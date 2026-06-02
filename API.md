# API Documentation

Complete API reference for the Dynamic IPv6/IPv4 DDNS Service.

## Base URL

```
https://ipv6.example.com
https://ipv4.example.com
```

## Authentication

All endpoints (except `/api/health` and `/`) require authentication via token.

Token can be passed as:
- Query parameter: `?token=YOUR_TOKEN`
- Header: `Authorization: Bearer YOUR_TOKEN`

## Endpoints

### 1. Health Check

Check service health. **No authentication required.**

```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-06-02T23:30:45.123456",
  "service": "dynipv6"
}
```

**Status Codes:**
- `200`: Service is healthy
- `500`: Service error

---

### 2. Update DNS Records

Update DNS records for IPv4 and/or IPv6 addresses.

```http
GET|POST /api/update
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `token` | string | Yes | Authentication token |
| `ipv6prefix` | string | No | IPv6 address or "auto" |
| `ipv4` | string | No | IPv4 address or "auto" |
| `hostname` | string | No | Source device/hostname |

**Query String Example:**
```
/api/update?ipv6prefix=auto&ipv4=auto&token=YOUR_TOKEN
```

**POST Form Data Example:**
```
token=YOUR_TOKEN
ipv6prefix=2001:db8::1
ipv4=192.0.2.1
hostname=unifi-device
```

**Response (Success):**
```json
{
  "status": "success",
  "timestamp": "2026-06-02T23:30:45.123456",
  "updates": {
    "ipv6": {
      "status": "success",
      "address": "2001:db8::1"
    },
    "ipv4": {
      "status": "success",
      "address": "192.0.2.1"
    }
  }
}
```

**Response (Error):**
```json
{
  "status": "error",
  "message": "No IPv4 or IPv6 provided"
}
```

**Status Codes:**
- `200`: Update successful
- `400`: Missing required parameters
- `401`: Authentication failed
- `500`: Server error

**Examples:**

**Update IPv6 only (auto-detect):**
```bash
curl "https://ipv6.example.com/api/update?ipv6prefix=auto&token=abc123"
```

**Update IPv4 only (explicit):**
```bash
curl "https://ipv4.example.com/api/update?ipv4=192.0.2.1&token=abc123"
```

**Update both IPv6 and IPv4:**
```bash
curl "https://ipv6.example.com/api/update?ipv6prefix=auto&ipv4=auto&token=abc123"
```

**Update with specific addresses:**
```bash
curl -X POST https://ipv6.example.com/api/update \
  -d "token=abc123&ipv6prefix=2001:db8::1&ipv4=192.0.2.1&hostname=my-router"
```

---

### 3. Get DNS Status

Get current DNS records and their update history.

```http
GET /api/status
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `token` | string | Yes | Authentication token |

**Response:**
```json
{
  "status": "success",
  "timestamp": "2026-06-02T23:30:45.123456",
  "ipv6": {
    "value": "2001:db8::1",
    "type": "AAAA",
    "domain": "ipv6.example.com",
    "hostname": "unifi-device",
    "updated": "2026-06-02T23:30:45.123456",
    "updated_by": "UniFi-Device-Name"
  },
  "ipv4": {
    "value": "192.0.2.1",
    "type": "A",
    "domain": "ipv4.example.com",
    "hostname": "unifi-device",
    "updated": "2026-06-02T23:30:45.123456",
    "updated_by": "UniFi-Device-Name"
  }
}
```

**Status Codes:**
- `200`: Success
- `401`: Authentication failed
- `500`: Server error

**Example:**
```bash
curl "https://ipv6.example.com/api/status?token=abc123"
```

---

### 4. Service Info

Get service information and available endpoints.

```http
GET /
```

**Response:**
```json
{
  "service": "Dynamic IPv6/IPv4 DDNS Service",
  "version": "1.0.0",
  "endpoints": {
    "/api/update": "Update DNS records (requires token)",
    "/api/status": "Get current records status (requires token)",
    "/api/health": "Health check"
  },
  "documentation": "See config.json for setup instructions"
}
```

---

## Common Use Cases

### UniFi DDNS Integration

In UniFi, configure custom DDNS with:

**Server URL (IPv6):**
```
https://ipv6.example.com/api/update?ipv6prefix=auto&token=YOUR_TOKEN
```

**Server URL (IPv4):**
```
https://ipv4.example.com/api/update?ipv4=auto&token=YOUR_TOKEN
```

**Server URL (Both):**
```
https://ipv6.example.com/api/update?ipv6prefix=auto&ipv4=auto&token=YOUR_TOKEN
```

### Manual Update via cron

Update every 5 minutes:

```bash
*/5 * * * * curl -s "https://ipv6.example.com/api/update?ipv6prefix=auto&ipv4=auto&token=YOUR_TOKEN" >> /var/log/ddns_update.log 2>&1
```

### Bash Script

```bash
#!/bin/bash

TOKEN="your-secret-token"
IPV6=$(ip -6 addr show | grep 'inet6 ' | grep -v '::1' | grep -v 'fe80:' | awk '{print $2}' | cut -d'/' -f1 | head -1)
IPV4=$(curl -s https://api.ipify.org)

curl -s "https://ipv6.example.com/api/update?token=$TOKEN&ipv6prefix=$IPV6&ipv4=$IPV4"
```

### Python Script

```python
import requests
import socket

TOKEN = "your-secret-token"
BASE_URL = "https://ipv6.example.com/api"

def get_ipv4():
    try:
        return requests.get('https://api.ipify.org').text
    except:
        return None

def get_ipv6():
    try:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        sock.connect(("2001:4860:4860::8888", 80))
        return sock.getsockname()[0]
    except:
        return None

def update_dns():
    params = {
        'token': TOKEN,
        'ipv6prefix': get_ipv6() or 'auto',
        'ipv4': get_ipv4() or 'auto'
    }
    response = requests.get(f"{BASE_URL}/update", params=params, verify=True)
    return response.json()

if __name__ == "__main__":
    result = update_dns()
    print(result)
```

### Using curl with Authorization Header

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://ipv6.example.com/api/update?ipv6prefix=auto&ipv4=auto"
```

### Monitoring Service Health

```bash
# Check health regularly
while true; do
  STATUS=$(curl -s https://ipv6.example.com/api/health | jq -r '.status')
  if [ "$STATUS" != "healthy" ]; then
    echo "Service is $STATUS" | mail -s "DDNS Service Alert" admin@example.com
  fi
  sleep 300
done
```

---

## Response Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 400 | Bad Request | Missing or invalid parameters |
| 401 | Unauthorized | Token missing or invalid |
| 404 | Not Found | Endpoint not found |
| 500 | Server Error | Internal server error |

---

## Error Handling

**Missing Token:**
```json
{
  "status": "error",
  "message": "Missing token"
}
```

**Invalid Token:**
```json
{
  "status": "error",
  "message": "Invalid token"
}
```

**Server Error:**
```json
{
  "status": "error",
  "message": "Internal server error"
}
```

---

## Rate Limiting

Currently, no rate limiting is implemented. In production, consider adding:

- Max 60 updates per minute per token
- Cache updates (don't update if IP unchanged for 5 minutes)
- Implement circuit breaker for ISPConfig API

---

## Security Notes

1. **Always use HTTPS**: Never send tokens over HTTP
2. **Token rotation**: Change tokens periodically
3. **Monitor updates**: Watch logs for suspicious patterns
4. **Firewall rules**: Restrict API access if possible
5. **Log retention**: Keep logs for audit trail

---

## Troubleshooting

### 401 Unauthorized

- Token missing: add `?token=YOUR_TOKEN` to URL
- Token invalid: check token in `/etc/dynipv6/config.json`
- Token format: use exact token from config

### No IP Update

- Check network connectivity
- Verify token is valid
- Check service logs: `journalctl -u dynipv6 -f`
- Ensure ISPConfig API is accessible

### Slow Response

- Check server load: `top`
- Monitor network: `nethogs`
- Review ISPConfig API response time
- Consider adding reverse proxy caching

---

## Example Integration Flows

### Flow 1: UniFi Auto-Update

```
UniFi (every 10min)
  ↓
HTTPS POST /api/update
  ↓
Validate token
  ↓
Store record in /var/lib/dynipv6/
  ↓
Update ISPConfig via API
  ↓
Return success response
```

### Flow 2: Manual Script

```
Cron job (every 5min)
  ↓
Run bash/python script
  ↓
Get current IP (auto or explicit)
  ↓
Call /api/update with token
  ↓
Log response
```

### Flow 3: Monitoring

```
Monitoring system (every 5min)
  ↓
Call /api/health
  ↓
Call /api/status
  ↓
Compare with expected values
  ↓
Alert if mismatch
```

---

## Changelog

### v1.0.0 (2026-06-02)
- Initial API release
- Support for IPv4 and IPv6
- Token-based authentication
- ISPConfig integration
- Health check endpoint
