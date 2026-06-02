# ISPConfig Integration Guide

Complete setup guide for integrating the DDNS service with ISPConfig.

## Overview

The service automatically updates DNS records in ISPConfig when receiving IP updates from UniFi. It handles:

✅ Automatic zone lookup
✅ Record creation (if not exists)
✅ Record updates (if exists)
✅ Error handling and retries
✅ Full audit logging

## Prerequisites

- ISPConfig 3.1+ installed
- Admin or API-capable user account
- DNS zone created for your domains
- Direct network access to ISPConfig API endpoint

## Step 1: Get ISPConfig API Credentials

### Via ISPConfig Web Interface

1. Login to ISPConfig as **admin**
2. Go to **System** → **Settings** → **API**
3. Check "Enable API"
4. Note your settings:
   - API Server: `https://your-ispconfig-ip:8080/api/`
   - Username: `admin` (or your username)
   - Password: Your ISPConfig password
   - Client ID: `0` (for admin account)

### Verify API Access

```bash
# Test with curl
curl -k -d "username=admin&password=your_password&client_id=0&name=example.com" \
  https://your-ispconfig-ip:8080/api/dnszone/get_id
```

Should return:
```json
{"id": "123"}
```

## Step 2: Update Configuration

Edit `/etc/dynipv6/config.json`:

```json
{
  "ispconfig_url": "https://192.168.1.100:8080",
  "ispconfig_username": "admin",
  "ispconfig_password": "YourPassword123",
  "ispconfig_client_id": "0",
  "ispconfig_verify_ssl": false,
  
  "ipv6_domain": "ipv6.example.com",
  "ipv4_domain": "ipv4.example.com",
  
  "auth_tokens": {
    "your-secret-token": "UniFi-Device"
  }
}
```

### Field Explanations

| Field | Example | Description |
|-------|---------|-------------|
| `ispconfig_url` | https://192.168.1.100:8080 | ISPConfig API endpoint |
| `ispconfig_username` | admin | ISPConfig login username |
| `ispconfig_password` | secret123 | ISPConfig login password |
| `ispconfig_client_id` | 0 | Client ID (0 = admin) |
| `ispconfig_verify_ssl` | false | Skip SSL verification (for self-signed certs) |

## Step 3: Create DNS Zones (if not exists)

In ISPConfig:

1. Go to **DNS** → **Zones**
2. Click **New Zone**
3. Create two zones:

### Zone 1: ipv6.example.com
```
Zone name: ipv6.example.com
Master server: (select your DNS server)
```

### Zone 2: ipv4.example.com
```
Zone name: ipv4.example.com
Master server: (select your DNS server)
```

## Step 4: Test ISPConfig Connection

### Using the API Test Endpoint

```bash
curl -k "https://ipv6.example.com/api/ispconfig-test?token=your-secret-token"
```

**Success Response:**
```json
{
  "status": "success",
  "message": "ISPConfig connection successful",
  "server": "https://192.168.1.100:8080"
}
```

**Error Response:**
```json
{
  "status": "error",
  "message": "ISPConfig connection failed",
  "server": "https://192.168.1.100:8080"
}
```

### Check Service Logs

```bash
journalctl -u dynipv6 -f
# Look for: "ISPConfig connection successful"
```

## Step 5: Verify DNS Records Are Created

### First Update

When UniFi sends the first update:

```bash
# Check ISPConfig Logs
tail -f /var/log/dynipv6/dynipv6.log | grep ISPConfig
```

Expected output:
```
2026-06-02 23:45:30 - dynipv6 - INFO - ISPConfig: Updated ipv6.example.com (AAAA) = 2a00:6020:1000:44::29f5
2026-06-02 23:45:30 - dynipv6 - INFO - ISPConfig: Updated ipv4.example.com (A) = 100.86.66.72
```

### Check ISPConfig

1. Go to **DNS** → **Zones**
2. Click on **ipv6.example.com**
3. Should see new **AAAA** record for your IPv6 address
4. Repeat for ipv4.example.com with **A** record

## How It Works

### Architecture Flow

```
┌─────────────────────────────────────────┐
│ UniFi (every 10 minutes)                │
└──────────────┬──────────────────────────┘
               │
               │ HTTPS
               ▼
┌──────────────────────────────────────────┐
│ dynipv6_service                          │
│ - Validate IP address                    │
│ - Check format (IPv4 vs IPv6)            │
│ - Store locally                          │
└──────────────┬──────────────────────────┘
               │
               │ Use ISPConfig API Client
               ▼
┌──────────────────────────────────────────┐
│ ISPConfigAPI (ispconfig_api.py)          │
│ 1. Find DNS zone ID for domain           │
│ 2. Search for existing record            │
│ 3. Update or create record               │
└──────────────┬──────────────────────────┘
               │
               │ REST API calls
               ▼
┌──────────────────────────────────────────┐
│ ISPConfig (your server)                  │
│ - Updates DNS records in database        │
│ - Notifies DNS server                    │
└──────────────────────────────────────────┘
```

### API Calls Made

**1. Get Zone ID:**
```
POST /api/dnszone/get_id
Data: name=example.com
Returns: {"id": "123"}
```

**2. Get Zone Records:**
```
POST /api/dnsrecord/get
Data: id=123
Returns: [{"id": "456", "name": "ipv6.example.com", "type": "AAAA", ...}]
```

**3. Update Record (if exists):**
```
POST /api/dnsrecord/update
Data: {
  "id": "456",
  "data": "2a00:6020:1000:44::29f5",
  "ttl": 3600,
  "active": "y"
}
```

**Or Create Record (if not exists):**
```
POST /api/dnsrecord/add
Data: {
  "zone": "123",
  "name": "ipv6.example.com",
  "type": "AAAA",
  "data": "2a00:6020:1000:44::29f5",
  "ttl": 3600,
  "active": "y"
}
```

## Troubleshooting

### "ISPConfig connection failed"

**Check 1: Network connectivity**
```bash
ping your-ispconfig-ip
curl -k https://your-ispconfig-ip:8080/api/dnszone/get_id \
  -d "username=admin&password=pwd&client_id=0"
```

**Check 2: Credentials**
```bash
# Verify in config.json
cat /etc/dynipv6/config.json | grep ispconfig
```

**Check 3: API enabled in ISPConfig**
- Go to ISPConfig → System → Settings → API
- Check "Enable API" checkbox
- Save

### "Zone not found"

**Solution: Create the DNS zone**
1. ISPConfig → DNS → Zones
2. Click "New Zone"
3. Add zone: `example.com` or `ipv6.example.com`

Note: For `ipv6.example.com`, you may want to create it as a subdomain under `example.com` or as a separate zone.

### "Permission denied"

**Cause:** Client ID doesn't have access

**Solution:**
1. Use admin account (client_id: 0)
2. Or create dedicated API user:
   - ISPConfig → System → Users
   - New User with DNS permissions
   - Get client_id from reseller/user list

### Records not updating

**Check logs:**
```bash
journalctl -u dynipv6 | tail -20
```

**Common issues:**
- Record name mismatch (use FQDN: `ipv6.example.com`, not `ipv6`)
- Zone not found
- API credentials wrong
- Firewall blocking port 8080

### DNS propagation

After record is created/updated, it may take:
- **Immediate:** Updated in ISPConfig database
- **5-30 seconds:** ISPConfig pushes to DNS server
- **15 minutes:** TTL propagation to resolvers

Check with:
```bash
dig ipv6.example.com AAAA
dig ipv4.example.com A
```

## ISPConfigAPI Class Reference

Located in `ispconfig_api.py`

### Usage Example

```python
from ispconfig_api import ISPConfigAPI

api = ISPConfigAPI(
    url="https://192.168.1.100:8080",
    username="admin",
    password="secret",
    client_id="0"
)

# Get zone ID
zone_id = api.get_dns_zone_id("example.com")

# Get all records for zone
records = api.get_dns_records(zone_id)

# Get specific record ID
record_id = api.get_dns_record_id(zone_id, "ipv6.example.com", "AAAA")

# Update existing record
api.update_dns_record(record_id, "2001:db8::1", ttl=3600)

# Create new record
api.create_dns_record(zone_id, "ipv6.example.com", "AAAA", "2001:db8::1")

# Update or create (automatic)
api.update_or_create_record("ipv6.example.com", "AAAA", "2001:db8::1")

# Test connection
api.test_connection()
```

## Advanced Configuration

### Multiple ISPConfig Servers

Not directly supported, but you can:
1. Use DNS CNAME to single ISPConfig
2. Set up multiple zones in same ISPConfig
3. Use load balancer in front of ISPConfig

### Using Subdomain Zones

If `ipv6.example.com` is a subdomain zone:

**In ISPConfig:**
- Zone: `ipv6.example.com`
- Record name: `@` (for zone root)
- Or: `mail.ipv6.example.com` (for subdomain)

**In config.json:**
```json
{
  "ipv6_domain": "ipv6.example.com",
  // Service will use this as-is
}
```

### Custom TTL

Default TTL is 3600 seconds (1 hour). To change:

Edit `dynipv6_service.py` line where `update_ispconfig_dns` is called:
```python
success = api.update_or_create_record(domain, record_type, value, ttl=300)  # 5 minutes
```

## Security Best Practices

1. **Use API user, not admin password** - Create dedicated API account with DNS permissions
2. **Firewall ISPConfig** - Only allow DDNS service to access port 8080
3. **Use strong password** - ISPConfig password stored in plaintext in config
4. **Rotate credentials** - Change password periodically
5. **Monitor logs** - Watch for failed API calls
6. **Verify SSL** - Use proper SSL certificates (not self-signed if possible)

## Testing Your Setup

### Full Integration Test

```bash
#!/bin/bash

TOKEN="your-secret-token"
SERVICE="https://ipv6.example.com"

echo "1. Test health..."
curl -s $SERVICE/api/health

echo -e "\n2. Test ISPConfig connection..."
curl -s "$SERVICE/api/ispconfig-test?token=$TOKEN"

echo -e "\n3. Test DNS update..."
curl -s "$SERVICE/api/update?ipv6prefix=auto&ipv4=auto&token=$TOKEN"

echo -e "\n4. Check status..."
curl -s "$SERVICE/api/status?token=$TOKEN"

echo -e "\n5. Verify DNS..."
dig ipv6.example.com AAAA
dig ipv4.example.com A
```

## Support

### Logs to Check

1. **Service logs:**
   ```bash
   journalctl -u dynipv6 -f
   ```

2. **ISPConfig API logs:**
   ```bash
   tail -f /var/log/ispconfig/
   ```

3. **DNS server logs:**
   ```bash
   # For BIND
   tail -f /var/log/syslog | grep named
   ```

### Debug Mode

Add to `dynipv6_service.py`:
```python
logging.basicConfig(level=logging.DEBUG)
```

Then check logs for detailed API calls.

## References

- [ISPConfig API Documentation](https://www.ispconfig.org/documentation/)
- [ISPConfig REST API](https://www.ispconfig.org/documentation/admin/ispconfig-rest-api/)
- [DNS Management in ISPConfig](https://www.ispconfig.org/documentation/user/dns-management/)
