# dynipv6

A minimal, self-hosted **Dynamic DNS** service. No web interface, no Docker, no
database — just one Python script, one config file and a systemd service.

A client (router, UniFi, ddclient, or a simple `cron` + `curl`) authenticates
with a username and password and reports its current IP address. The service
then:

1. writes the IP into an **nginx config** (rendered from a template) and reloads
   nginx, so your reverse proxy always points at the client, and
2. **optionally** updates the matching `A`/`AAAA` record in **ISPConfig**.

Works with **IPv4 only**, **IPv6 only**, or **both** — set `mode` in the config.

## Install

```bash
git clone https://github.com/xerolux/dipv6.git
cd dipv6
sudo ./install.sh
sudo nano /etc/dynipv6/config.json
sudo systemctl enable --now dynipv6
```

## Configuration

Everything lives in `/etc/dynipv6/config.json`:

```json
{
  "mode": "both",
  "domain": "home.example.com",
  "username": "myuser",
  "password": "change-me",

  "listen_host": "127.0.0.1",
  "listen_port": 8080,

  "nginx": {
    "enabled": true,
    "template": "/etc/dynipv6/nginx.conf.template",
    "output": "/etc/nginx/sites-enabled/dynipv6.conf",
    "reload_command": "systemctl reload nginx"
  },

  "ispconfig": {
    "enabled": false,
    "url": "https://ispconfig.example.com:8080",
    "username": "admin",
    "password": "change-me",
    "client_id": "0",
    "verify_ssl": false
  }
}
```

| Key | Meaning |
|-----|---------|
| `mode` | `ipv4`, `ipv6` or `both` — which address families to accept |
| `domain` | the hostname this service manages |
| `username` / `password` | credentials the client uses to authenticate |
| `listen_host` / `listen_port` | where the service listens |
| `nginx.enabled` | write/reload an nginx config on every IP change |
| `nginx.template` | template file (see `nginx.conf.template`) |
| `nginx.output` | where the rendered config is written |
| `nginx.reload_command` | command run after writing the config |
| `ispconfig.enabled` | also update DNS records in ISPConfig (optional) |

Set `nginx.enabled` to `false` if you only want ISPConfig DNS, or
`ispconfig.enabled` to `false` if you only want the nginx file. You can use
both, either, or neither.

### nginx template

`nginx.conf.template` is rendered on every IP change. Placeholders:

- `{{DOMAIN}}` → `domain` from the config
- `{{IPV4}}` → the client's current IPv4 (empty in `ipv6`-only mode)
- `{{IPV6}}` → the client's current IPv6 (empty in `ipv4`-only mode)

## Updating your IP

Send the IP (or let the service auto-detect it from the connection):

```bash
# explicit IP
curl "http://USER:PASS@your-server:8080/update?ip=2001:db8::1"

# auto-detect from the source address of the request
curl "http://USER:PASS@your-server:8080/update"
```

The endpoint is also reachable at `/nic/update` and accepts the usual DynDNS
parameter names (`myip`, `ipv4`, `ipv6`, `ipv6prefix`, ...), so **ddclient** and
**UniFi** "custom DDNS" clients work out of the box.

### UniFi

- Service / Provider: **Custom**
- Hostname: your domain
- Username / Password: as in the config
- Server: `your-server:8080/nic/update?ip=%i&hostname=%h`

### Endpoints

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `GET/POST /update`, `/nic/update` | yes | report an IP and update nginx/ISPConfig |
| `GET /status` | yes | show the current stored IPs |
| `GET /health` | no | liveness check |

## How it runs

- Service script: `/opt/dynipv6/dynipv6.py`
- Config: `/etc/dynipv6/config.json`
- State (last seen IPs): `/var/lib/dynipv6/state.json`
- systemd unit: `dynipv6.service` (`journalctl -u dynipv6 -f` for logs)

The service runs as root because it writes the nginx config and reloads nginx.
If you disable the nginx feature you can run it as an unprivileged user instead.

## License

MIT — see [LICENSE](LICENSE).
