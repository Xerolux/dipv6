# Production Deployment Guide

Complete guide for running DDNS service in production with Docker Compose.

## Architecture

```
                    Internet
                       ↑
         ┌─────────────────────────────┐
         │   Let's Encrypt Certs       │
         │  (ipv6, ipv4, ip domains)   │
         └──────────┬──────────────────┘
                    │
         ┌──────────▼────────────────┐
         │  Nginx Reverse Proxy      │
         │  (443 SSL/TLS)            │
         │  (80 HTTP redirect)       │
         └──────────┬────────────────┘
                    │
         ┌──────────┴────────────────────┐
         │                               │
    ┌────▼────────┐            ┌────────▼──────┐
    │ DDNS API    │            │  Web UI       │
    │ (Port 5000) │            │  (Port 5001)  │
    └────┬────────┘            └────────┬──────┘
         │                              │
    ┌────▼──────────────────────────────▼──┐
    │      ISPConfig API                    │
    │  (External ISPConfig Server)          │
    └───────────────────────────────────────┘
```

## Deployment Steps

### 1. Prepare Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker & Docker Compose
sudo apt install -y docker.io docker-compose

# Add user to docker group (optional)
sudo usermod -aG docker $USER
sudo newgrp docker

# Create directories
mkdir -p /opt/dipv6/config
mkdir -p /opt/dipv6/data
cd /opt/dipv6
```

### 2. SSL Certificates

Get certificates for all three domains:

```bash
sudo certbot certonly --standalone \
  -d ipv6.xerolux.net \
  -d ipv4.xerolux.net \
  -d ip.xerolux.net
```

Verify:
```bash
ls -la /etc/letsencrypt/live/
```

### 3. Configuration

Create `/opt/dipv6/config/config.json`:

```json
{
  "ipv6_domain": "ipv6.xerolux.net",
  "ipv4_domain": "ipv4.xerolux.net",
  "ispconfig_url": "https://YOUR_ISPCONFIG_IP:8080",
  "ispconfig_username": "admin",
  "ispconfig_password": "ENCRYPTED_BY_SERVICE",
  "ispconfig_client_id": "0",
  "domains": {},
  "auth_tokens": {
    "your-initial-token": "Setup-Token"
  }
}
```

**Permissions:**
```bash
chmod 600 /opt/dipv6/config/config.json
sudo chown 33:33 /opt/dipv6/config/config.json
```

### 4. Docker Compose Setup

Copy files:
```bash
cp docker-compose.prod.yml /opt/dipv6/docker-compose.yml
cp nginx-prod.conf /opt/dipv6/nginx.conf
cp Dockerfile /opt/dipv6/
cp Dockerfile.webui /opt/dipv6/
```

### 5. Start Services

```bash
cd /opt/dipv6

# Build images
docker-compose build

# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

Output should show:
```
NAME              SERVICE   STATUS      PORTS
ddns-api          ddns-api  running     127.0.0.1:5000->5000/tcp
ddns-webui        webui     running     127.0.0.1:5001->5001/tcp
ddns-nginx        nginx     running     80->80/tcp, 443->443/tcp
```

### 6. Verify Services

```bash
# Check API health
curl https://ipv6.xerolux.net/api/health

# Check Web-UI
curl https://ip.xerolux.net/

# View logs
docker-compose logs -f ddns-api
docker-compose logs -f ddns-webui
docker-compose logs -f ddns-nginx
```

## Security Features

### Encryption ✅
- **Config passwords**: Encrypted with Fernet (AES-128)
- **Admin passwords**: Hashed with Werkzeug bcrypt
- **Tokens**: Cryptographically secure random generation
- **HTTPS/TLS**: All traffic encrypted in transit

### Access Control ✅
- **No root services**: All run as www-data user
- **File permissions**: 600 for configs, 700 for secrets
- **Network isolation**: Docker internal network only
- **Rate limiting**: API requests limited to 10/s, Web-UI 30/s
- **Login timeouts**: 8-hour session timeout

### Health & Monitoring ✅
- **Service health checks**: Every 30 seconds
- **ISPConfig connectivity**: Monitored
- **System resources**: CPU/Memory/Disk tracked
- **Automatic restart**: Failed services restart
- **Centralized logging**: All logs in containers

### Failure Recovery ✅
- **Automatic restart**: `restart: always`
- **Health checks**: Services restart on failure
- **ISPConfig retries**: 3 attempts with backoff
- **Data persistence**: Docker volumes survive restarts
- **Graceful shutdown**: 30-second graceful timeout

## Maintenance

### Logs

View logs:
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs -f ddns-api
docker-compose logs -f ddns-webui

# With timestamps
docker-compose logs --timestamps
```

Clear old logs:
```bash
docker system prune -a
```

### Backups

Backup critical data:
```bash
# Backup config
sudo cp -r /opt/dipv6/config ~/dipv6-backup/

# Backup encryption key
sudo cp -r /etc/dynipv6/secrets ~/dipv6-backup/

# Full backup with Docker volumes
docker run --rm \
  -v ddns-data:/data \
  -v $PWD:/backup \
  ubuntu tar czf /backup/ddns-data.tar.gz -C /data .
```

### Updates

Update service:
```bash
cd /opt/dipv6

# Pull latest code
git pull

# Rebuild images
docker-compose build

# Restart services
docker-compose up -d
```

### Certificate Renewal

Certbot auto-renews, but verify:
```bash
sudo certbot renew --dry-run
```

Reload Nginx after renewal:
```bash
docker-compose exec nginx nginx -s reload
```

## Monitoring

### System Health

Check service health:
```bash
# Container status
docker-compose ps

# Resource usage
docker stats

# Container logs
docker-compose logs --tail 50
```

### Application Health

```bash
# API health
curl https://ipv6.xerolux.net/api/health

# Web-UI
curl https://ip.xerolux.net/ -u admin:password

# ISPConfig connectivity
curl -X GET "https://ipv6.xerolux.net/api/ispconfig-test?token=YOUR_TOKEN"
```

### Disk Usage

```bash
# Docker disk usage
docker system df

# Volume usage
du -sh /var/lib/docker/volumes/*
```

## Troubleshooting

### Service won't start

```bash
# Check logs
docker-compose logs ddns-api
docker-compose logs ddns-webui

# Check images
docker images

# Rebuild
docker-compose build --no-cache
docker-compose up -d
```

### ISPConfig connection fails

```bash
# Test from container
docker-compose exec ddns-api curl -k \
  https://YOUR_ISPCONFIG_IP:8080/api/dnszone/get_id \
  -d "username=admin&password=pwd&client_id=0"

# Check credentials in config
cat /opt/dipv6/config/config.json | grep ispconfig
```

### Nginx SSL errors

```bash
# Check certificates
sudo openssl x509 -in /etc/letsencrypt/live/ipv6.xerolux.net/fullchain.pem -text -noout

# Test SSL
openssl s_client -connect ipv6.xerolux.net:443

# Reload Nginx
docker-compose exec nginx nginx -s reload
```

### High memory/CPU usage

```bash
# Check resource usage
docker stats

# Check for memory leaks
docker-compose logs --tail 100 | grep -i "memory\|error"

# Restart service
docker-compose restart ddns-api
```

## Performance Tuning

### Nginx optimization

Already configured in `nginx-prod.conf`:
- Worker connections: 2048
- Gzip compression: Level 6
- Keepalive timeout: 65s
- Rate limiting: 10 req/s (API), 30 req/s (Web-UI)

### ISPConfig API optimization

Already configured in `ispconfig_api.py`:
- Connection pooling
- Retry logic (3 attempts)
- Exponential backoff
- Request timeout: 10s
- Keep-alive connections

### Flask optimization

Already configured in `Dockerfile.webui`:
- 4 Gunicorn workers
- 2 threads per worker
- Graceful timeout: 30s
- Keep-alive: 5s

## Scaling

### Multiple domains

Configuration handles unlimited domains:
```json
{
  "domains": {
    "ipv6.xerolux.net": {"ipv4_enabled": false, "ipv6_enabled": true},
    "ipv4.xerolux.net": {"ipv4_enabled": true, "ipv6_enabled": false},
    "dns.xerolux.net": {"ipv4_enabled": true, "ipv6_enabled": true}
  }
}
```

### Multiple ISPConfig instances

Create load balancer or use DNS round-robin:
```bash
# ISPConfig 1
server1.example.com

# ISPConfig 2
server2.example.com

# Load balancer
ispconfig.example.com (round-robin)
```

Update config with load balancer hostname.

## Data Persistence

All critical data persists in Docker volumes:

```yaml
volumes:
  ddns-data:          # DNS records
  ddns-logs:          # Application logs
  ddns-secrets:       # Encryption keys
  nginx-logs:         # Web server logs
  prometheus-data:    # Monitoring metrics
  loki-data:          # Log aggregation
```

Backup volumes:
```bash
docker run --rm \
  -v ddns-data:/data \
  -v /mnt/backup:/backup \
  ubuntu tar czf /backup/ddns-data-$(date +%Y%m%d).tar.gz -C /data .
```

## Security Hardening

### Additional measures

1. **Firewall rules**
   ```bash
   sudo ufw allow 22/tcp    # SSH
   sudo ufw allow 80/tcp    # HTTP
   sudo ufw allow 443/tcp   # HTTPS
   sudo ufw deny from any to any port 5000  # Block API port
   sudo ufw deny from any to any port 5001  # Block Web-UI port
   sudo ufw enable
   ```

2. **SELinux** (if enabled)
   ```bash
   semanage fcontext -a -t container_file_t "/opt/dipv6(/.*)?"
   restorecon -Rv /opt/dipv6
   ```

3. **Fail2ban** (optional)
   ```bash
   sudo apt install fail2ban
   # Create /etc/fail2ban/jail.d/nginx-http-auth.conf
   ```

4. **Regular audits**
   ```bash
   # Check for vulnerabilities
   docker run --rm \
     -v /var/run/docker.sock:/var/run/docker.sock \
     aquasec/trivy image ddns-api:latest
   ```

## Support & Monitoring

### Logs location in container

- API logs: `/var/log/dynipv6/dynipv6.log`
- Web-UI logs: stdout (journalctl)
- Nginx logs: `/var/log/nginx/`

### View logs

```bash
# API service
docker-compose logs -f ddns-api

# Web-UI
docker-compose logs -f ddns-webui

# Nginx
docker-compose logs -f ddns-nginx
```

### Health check endpoints

- API: `https://ipv6.xerolux.net/api/health`
- Web-UI: `https://ip.xerolux.net/login`
- Nginx: `http://localhost/health`

## Emergency Procedures

### Service failure recovery

```bash
# 1. Check what failed
docker-compose ps

# 2. View logs
docker-compose logs --tail 100

# 3. Restart failed service
docker-compose restart ddns-api

# 4. If that doesn't work, full restart
docker-compose down
docker-compose up -d

# 5. Verify
docker-compose ps
```

### Full rollback

```bash
# Save current config
cp /opt/dipv6/config/config.json /opt/dipv6/config/config.json.backup

# Restore from backup
cp /opt/dipv6/config/config.json.old /opt/dipv6/config/config.json

# Restart services
docker-compose restart
```

### Restore from backup

```bash
# Stop services
docker-compose down

# Restore data
docker run --rm \
  -v ddns-data:/data \
  -v /mnt/backup:/backup \
  ubuntu tar xzf /backup/ddns-data-20260602.tar.gz -C /data

# Restore config
cp /backup/config.json.backup /opt/dipv6/config/config.json

# Start services
docker-compose up -d
```

## Support

For issues:
1. Check logs: `docker-compose logs -f`
2. Verify connectivity: `curl https://ipv6.xerolux.net/api/health`
3. Test ISPConfig: Web-UI → Settings → Test ISPConfig
4. Review documentation in ISPCONFIG_SETUP.md and WEBUI_SETUP.md
