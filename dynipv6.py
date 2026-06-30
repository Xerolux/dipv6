#!/usr/bin/env python3
"""
dynipv6 - a minimal self-hosted Dynamic DNS service.

A client (router, UniFi, ddclient, cron+curl, ...) authenticates with a
username and password and reports its current IP address. The service then:

  1. writes the IP into an nginx config (rendered from a template) and
     reloads nginx, so the reverse proxy always points at the client, and
  2. optionally updates the matching A/AAAA record in ISPConfig.

Everything is driven by a single config file: /etc/dynipv6/config.json
"""

import os
import sys
import json
import secrets
import tempfile
import ipaddress
import logging
import subprocess
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix

CONFIG_FILE = Path(os.environ.get("DYNIPV6_CONFIG", "/etc/dynipv6/config.json"))
STATE_FILE = Path(os.environ.get("DYNIPV6_STATE", "/var/lib/dynipv6/state.json"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("dynipv6")

app = Flask(__name__)
# Run behind nginx: trust X-Forwarded-For/-Proto/-Host/-Port from the proxy
# so request.remote_addr is the real client IP, not 127.0.0.1.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)


# --------------------------------------------------------------------------- #
# Config & state
# --------------------------------------------------------------------------- #
def load_config():
    if not CONFIG_FILE.exists():
        log.error("Config file not found: %s", CONFIG_FILE)
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    cfg.setdefault("mode", "both")          # ipv4 | ipv6 | both
    cfg.setdefault("listen_host", "127.0.0.1")
    cfg.setdefault("listen_port", 8080)
    cfg.setdefault("nginx", {})
    cfg.setdefault("ispconfig", {})
    if cfg["mode"] not in ("ipv4", "ipv6", "both"):
        log.error("Invalid mode %r (use ipv4, ipv6 or both)", cfg["mode"])
        sys.exit(1)
    return cfg


def load_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except (OSError, ValueError):
            pass
    return {"ipv4": None, "ipv6": None, "updated": None}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=STATE_FILE.parent)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, STATE_FILE)
    except Exception:
        os.unlink(tmp_path)
        raise


config = load_config()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def authenticated():
    """Accept HTTP Basic auth or username/password query params."""
    user = config.get("username")
    pw = config.get("password")
    if not user or not pw:
        return False

    auth = request.authorization
    if auth and auth.username and auth.password:
        if secrets.compare_digest(auth.username, user) and secrets.compare_digest(auth.password, pw):
            return True

    q_user = request.values.get("username")
    q_pw = request.values.get("password")
    if q_user and q_pw:
        return secrets.compare_digest(q_user, user) and secrets.compare_digest(q_pw, pw)

    return False


def classify_ip(value):
    """Return ('ipv4'|'ipv6', normalized) or (None, None) if invalid."""
    try:
        addr = ipaddress.ip_address(value)
    except ValueError:
        return None, None
    return ("ipv6" if addr.version == 6 else "ipv4"), str(addr)


def render_nginx(state):
    """Render the nginx template with the current IPs and reload nginx."""
    ng = config.get("nginx", {})
    if not ng.get("enabled"):
        return
    template_path = Path(ng["template"])
    output_path = Path(ng["output"])
    template = template_path.read_text()

    # TARGET resolves to a ready-to-use proxy_pass address: bracketed IPv6
    # if available, otherwise IPv4. Avoids "proxy_pass http://[]:80;" when
    # only one address family is known.
    if state.get("ipv6"):
        target = f"[{state['ipv6']}]"
    elif state.get("ipv4"):
        target = state["ipv4"]
    else:
        target = ""

    rendered = (
        template
        .replace("{{DOMAIN}}", config.get("domain", ""))
        .replace("{{TARGET}}", target)
        .replace("{{IPV4}}", state.get("ipv4") or "")
        .replace("{{IPV6}}", state.get("ipv6") or "")
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered)
    log.info("Wrote nginx config: %s", output_path)

    reload_cmd = ng.get("reload_command", "systemctl reload nginx")
    try:
        subprocess.run(reload_cmd, shell=True, check=True)
        log.info("Reloaded nginx")
    except subprocess.CalledProcessError as e:
        log.error("nginx reload failed: %s", e)


def update_ispconfig(state):
    """Optionally push the IPs to ISPConfig as A/AAAA records."""
    isp = config.get("ispconfig", {})
    if not isp.get("enabled"):
        return
    try:
        from ispconfig_api import ISPConfigAPI
    except ImportError:
        log.error("ispconfig_api module not available")
        return
    api = ISPConfigAPI(
        url=isp["url"],
        username=isp["username"],
        password=isp["password"],
        client_id=isp.get("client_id", "0"),
        verify_ssl=isp.get("verify_ssl", False),
    )
    domain = config.get("domain")
    if state.get("ipv4"):
        success = api.update_or_create_record(domain, "A", state["ipv4"])
        log.info("ISPConfig A record update %s", "succeeded" if success else "failed")
    if state.get("ipv6"):
        success = api.update_or_create_record(domain, "AAAA", state["ipv6"])
        log.info("ISPConfig AAAA record update %s", "succeeded" if success else "failed")


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@app.route("/update", methods=["GET", "POST"])
@app.route("/nic/update", methods=["GET", "POST"])  # ddclient / UniFi compatible
def update():
    if not authenticated():
        return jsonify(status="error", message="authentication failed"), 401

    mode = config["mode"]
    state = load_state()
    changed = False

    # Collect candidate IPs from the usual DynDNS parameter names.
    candidates = []
    for key in ("ip", "myip", "ipv4", "ipv6", "myipv6", "ipv6prefix"):
        val = request.values.get(key)
        if val:
            candidates.append(val)
    # No IP given -> use the address the client connected from.
    if not candidates:
        candidates.append(request.remote_addr)

    accepted = {}
    for raw in candidates:
        family, norm = classify_ip(raw)
        if not family:
            return jsonify(status="error", message=f"invalid IP: {raw}"), 400
        if family == "ipv4" and mode == "ipv6":
            continue
        if family == "ipv6" and mode == "ipv4":
            continue
        if state.get(family) != norm:
            state[family] = norm
            changed = True
        accepted[family] = norm

    if not accepted:
        return jsonify(status="error", message=f"no IP matching mode '{mode}'"), 400

    if changed:
        state["updated"] = datetime.now().isoformat()
        save_state(state)
        render_nginx(state)
        update_ispconfig(state)
        log.info("Updated: %s", accepted)
        return jsonify(status="success", changed=True, addresses=accepted)

    return jsonify(status="success", changed=False, addresses=accepted)


@app.route("/status", methods=["GET"])
def status():
    if not authenticated():
        return jsonify(status="error", message="authentication failed"), 401
    state = load_state()
    return jsonify(status="success", mode=config["mode"],
                   domain=config.get("domain"), addresses=state)


@app.route("/health", methods=["GET"])
def health():
    return jsonify(status="healthy")


if __name__ == "__main__":
    app.run(host=config["listen_host"], port=config["listen_port"])
