# DDNS Service - Installationsanleitung (Deutsch)

🌐 **Self-Hosted Dynamic DNS mit IPv4/IPv6 Dual-Domain Unterstützung**

Eine produktionsreife DDNS-Service für UniFi-Netzwerke mit ISPConfig-Integration zur automatischen DNS-Verwaltung.

## Inhaltsverzeichnis

1. [Voraussetzungen](#voraussetzungen)
2. [Systemanforderungen](#systemanforderungen)
3. [Installation mit Docker (Empfohlen)](#installation-mit-docker-empfohlen)
4. [Installation auf Bare Metal](#installation-auf-bare-metal)
5. [Konfiguration](#konfiguration)
6. [ISPConfig-Integration](#ispconfig-integration)
7. [UniFi-Integration](#unifi-integration)
8. [Überwachung und Wartung](#überwachung-und-wartung)
9. [Troubleshooting](#troubleshooting)

## Voraussetzungen

### Erforderlich
- Ubuntu 20.04+ oder Debian 11+
- ISPConfig 3.2+ mit aktivierter API
- Let's Encrypt Zertifikate (kostenlos)
- Root- oder sudo-Zugriff
- Mindestens 3 Domainnamen für die Zertifikate:
  - `ipv6.example.com` (IPv6 DDNS)
  - `ipv4.example.com` (IPv4 DDNS)  
  - `ip.example.com` (Admin-Webinterface)

### Optional
- Docker & Docker Compose (für Docker-Installation)
- UniFi Controller (für DDNS-Integration)

## Systemanforderungen

### Docker
- Docker 20.10+
- Docker Compose 1.29+
- 2 GB RAM
- 2 CPU-Kerne
- 10 GB Festplatte

### Bare Metal
- Python 3.9+
- Nginx oder Apache
- systemd (Ubuntu/Debian)
- 1 GB RAM
- 1 CPU-Kern
- 5 GB Festplatte

## Installation mit Docker (Empfohlen)

### Schritt 1: Repository klonen

```bash
cd /opt
git clone https://github.com/your-org/dipv6.git
cd dipv6
```

### Schritt 2: Verzeichnisse erstellen

```bash
sudo mkdir -p /opt/dipv6/config
sudo mkdir -p /opt/dipv6/data
sudo chown $USER:$USER /opt/dipv6/config
sudo chown $USER:$USER /opt/dipv6/data
```

### Schritt 3: SSL-Zertifikate erstellen

```bash
# certbot installieren (falls nicht vorhanden)
sudo apt update
sudo apt install -y certbot

# Zertifikate für alle drei Domainnamen erstellen
sudo certbot certonly --standalone \
  -d ipv6.example.com \
  -d ipv4.example.com \
  -d ip.example.com
```

### Schritt 4: Konfiguration erstellen

```bash
cp config.json.example config/config.json
nano config/config.json
```

Bearbeiten Sie die Datei mit Ihren ISPConfig-Anmeldedaten:

```json
{
  "ipv6_domain": "ipv6.example.com",
  "ipv4_domain": "ipv4.example.com",
  "ispconfig_url": "https://YOUR_ISPCONFIG_SERVER:8080",
  "ispconfig_username": "admin",
  "ispconfig_password": "YOUR_PASSWORD",
  "ispconfig_client_id": "0",
  "domains": {
    "ipv6.example.com": {
      "ipv4_enabled": false,
      "ipv6_enabled": true
    },
    "ipv4.example.com": {
      "ipv4_enabled": true,
      "ipv6_enabled": false
    },
    "ip.example.com": {
      "ipv4_enabled": false,
      "ipv6_enabled": false
    }
  },
  "auth_tokens": {
    "your-initial-token": "Setup-Token"
  }
}
```

### Schritt 5: Berechtigungen setzen

```bash
sudo chmod 600 config/config.json
sudo chown 33:33 config/config.json
```

### Schritt 6: Services starten

```bash
cd /opt/dipv6

# Docker-Images bauen
docker-compose -f docker-compose.prod.yml build

# Services starten
docker-compose -f docker-compose.prod.yml up -d

# Status prüfen
docker-compose ps
```

**Erwartete Ausgabe:**
```
NAME              SERVICE   STATUS      PORTS
ddns-api          api       running     127.0.0.1:5000->5000/tcp
ddns-webui        webui     running     127.0.0.1:5001->5001/tcp
ddns-nginx        nginx     running     0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
```

### Schritt 7: Service prüfen

```bash
# API-Health prüfen
curl https://ipv6.example.com/api/health

# Web-UI im Browser öffnen
# https://ip.example.com
```

## Installation auf Bare Metal

### Schritt 1: Repository klonen

```bash
git clone https://github.com/your-org/dipv6.git
cd dipv6
```

### Schritt 2: Installer ausführen

```bash
chmod +x install.sh
sudo ./install.sh
```

Der Installer führt folgende Schritte aus:
- Python 3 Dependencies installieren
- Verzeichnisse erstellen
- Berechtigungen setzen
- systemd Service-Dateien einrichten

### Schritt 3: SSL-Zertifikate erstellen

```bash
sudo apt update
sudo apt install -y certbot

sudo certbot certonly --standalone \
  -d ipv6.example.com \
  -d ipv4.example.com \
  -d ip.example.com
```

### Schritt 4: Konfiguration anpassen

```bash
sudo nano /etc/dynipv6/config.json
```

Passen Sie die Konfiguration an (siehe Docker-Schritt 4).

### Schritt 5: Services starten

```bash
# DDNS API Service
sudo systemctl start dynipv6
sudo systemctl enable dynipv6

# Web Admin Panel
sudo systemctl start dynipv6-webui
sudo systemctl enable dynipv6-webui
```

### Schritt 6: Nginx konfigurieren

```bash
# Nginx-Konfiguration kopieren
sudo cp nginx-prod.conf /etc/nginx/sites-available/dynipv6
sudo ln -s /etc/nginx/sites-available/dynipv6 /etc/nginx/sites-enabled/

# Konfiguration testen
sudo nginx -t

# Nginx neu starten
sudo systemctl restart nginx
```

### Schritt 7: Status prüfen

```bash
sudo systemctl status dynipv6
sudo systemctl status dynipv6-webui

# Logs anzeigen
sudo journalctl -u dynipv6 -n 50 -f
```

## Konfiguration

### config.json - Vollständige Referenz

```json
{
  "ipv6_domain": "ipv6.example.com",
  "ipv4_domain": "ipv4.example.com",
  "ispconfig_url": "https://ispconfig.example.com:8080",
  "ispconfig_username": "admin",
  "ispconfig_password": "ENCRYPTED_BY_SERVICE",
  "ispconfig_client_id": "0",
  "port": 5000,
  "host": "127.0.0.1",
  "domains": {
    "ipv6.example.com": {
      "ipv4_enabled": false,
      "ipv6_enabled": true
    },
    "ipv4.example.com": {
      "ipv4_enabled": true,
      "ipv6_enabled": false
    },
    "ip.example.com": {
      "ipv4_enabled": false,
      "ipv6_enabled": false
    }
  },
  "auth_tokens": {
    "your-initial-token": "Setup-Token",
    "second-token": "Second-Token"
  }
}
```

### Parameter-Erklärung

| Parameter | Beschreibung | Beispiel |
|-----------|-------------|----------|
| `ipv6_domain` | Domainname für IPv6-DDNS | ipv6.example.com |
| `ipv4_domain` | Domainname für IPv4-DDNS | ipv4.example.com |
| `ispconfig_url` | ISPConfig Server-URL mit Port | https://ispconfig.example.com:8080 |
| `ispconfig_username` | ISPConfig Benutzername | admin |
| `ispconfig_password` | ISPConfig Passwort (wird verschlüsselt) | MY_PASSWORD |
| `ispconfig_client_id` | ISPConfig Client-ID | 0 (für Admin) |
| `domains` | Pro-Domain Einstellungen | siehe unten |
| `auth_tokens` | API-Token für DDNS-Updates | siehe unten |

### Domain-Konfiguration

```json
"domains": {
  "ipv6.example.com": {
    "ipv4_enabled": false,
    "ipv6_enabled": true
  },
  "ipv4.example.com": {
    "ipv4_enabled": true,
    "ipv6_enabled": false
  }
}
```

Jede Domain kann einzeln für IPv4/IPv6 aktiviert/deaktiviert werden.

### Token-Verwaltung

Tokens sind 32 Zeichen lange Zeichenketten für API-Zugriff:

```json
"auth_tokens": {
  "your-initial-token": "Setup-Token",
  "router-token": "UniFi-Router"
}
```

Im Web-Interface können neue Tokens generiert werden.

## ISPConfig-Integration

### ISPConfig-Vorbereitung

1. **In ISPConfig anmelden** als Administrator
2. **System → API aktivieren:**
   - System → Firewall → Remote API aktivieren
   - Sicherstellen, dass Remote API-Zugriff erlaubt ist

3. **Client-ID ermitteln:**
   ```bash
   # Für Admin-Konto: Client-ID = 0
   # Für Reseller/Kunden: In ISPConfig → Management → Kunden
   ```

### Verbindung testen

Im Web-Interface (https://ip.example.com):

1. **Settings** aufrufen
2. **ISPConfig-Anmeldedaten** eingeben:
   - ISPConfig URL: `https://ispconfig.example.com:8080`
   - Benutzername: `admin`
   - Passwort: `YOUR_PASSWORD`
   - Client-ID: `0`

3. **"Test ISPConfig"** klicken

**Erfolgreiche Meldung:** "ISPConfig connection successful"

### Fehlerbehandlung

**Fehler: "Connection refused"**
- ISPConfig-URL und Port überprüfen
- Firewall-Regeln prüfen
- ISPConfig läuft und ist erreichbar

**Fehler: "Invalid credentials"**
- Benutzernamen und Passwort überprüfen
- Benutzer hat Admin/Reseller-Rechte

**Fehler: "API disabled"**
- ISPConfig Admin-Panel öffnen
- System → Firewall → Remote API prüfen

## UniFi-Integration

### UniFi DDNS konfigurieren

1. **UniFi Controller öffnen**
2. **Einstellungen → Internet** aufrufen
3. **Dynamic DNS** aufrufen
4. **Custom** auswählen
5. Folgende Einträge eintragen:

```
Service:  Custom
Hostname: ipv6.example.com
Username: YOUR_TOKEN
Password: (leer lassen)
Server:   ipv6.example.com
```

6. **Save** klicken

### IPv4-DDNS (optional)

Für separate IPv4-Updates:

```
Service:  Custom
Hostname: ipv4.example.com
Username: YOUR_TOKEN
Password: (leer lassen)
Server:   ipv4.example.com
```

### Status überprüfen

Nach der Konfiguration sollte UniFi automatische IP-Updates durchführen.

Im Web-Interface prüfen:
1. **Status** aufrufen
2. **Letzte Aktualisierungen** beobachten

## Überwachung und Wartung

### Logs anzeigen

**Docker:**
```bash
# API-Logs
docker-compose logs -f ddns-api

# Web-UI-Logs
docker-compose logs -f ddns-webui

# Nginx-Logs
docker-compose logs -f ddns-nginx

# Alle Logs
docker-compose logs -f
```

**Bare Metal:**
```bash
# API Service
sudo journalctl -u dynipv6 -f

# Web-UI Service
sudo journalctl -u dynipv6-webui -f
```

### Health Check

```bash
# API-Health
curl https://ipv6.example.com/api/health

# Web-UI
curl https://ip.example.com/ -u admin:password

# Systemstatus
curl https://ipv6.example.com/api/status
```

### Automatische Backups

```bash
# config.json sichern
sudo cp /etc/dynipv6/config.json ~/backup/config.json.backup

# Docker-Volumes sichern
docker run --rm \
  -v ddns-data:/data \
  -v /mnt/backup:/backup \
  ubuntu tar czf /backup/ddns-data.tar.gz -C /data .
```

### Updates durchführen

**Docker:**
```bash
cd /opt/dipv6

# Code updaten
git pull

# Images neu bauen
docker-compose -f docker-compose.prod.yml build

# Services neu starten
docker-compose -f docker-compose.prod.yml up -d
```

**Bare Metal:**
```bash
cd /opt/dipv6

# Code updaten
git pull

# Services neu starten
sudo systemctl restart dynipv6 dynipv6-webui
```

### Zertifikat-Erneuerung

```bash
# Automatische Erneuerung testen
sudo certbot renew --dry-run

# Nginx neu laden (nach Erneuerung)
sudo systemctl reload nginx

# Bei Docker:
docker-compose exec nginx nginx -s reload
```

## Troubleshooting

### Service startet nicht

**Bare Metal:**
```bash
# Logs prüfen
sudo journalctl -u dynipv6 -n 50

# Konfiguration validieren
sudo cat /etc/dynipv6/config.json | python3 -m json.tool

# Berechtigungen prüfen
ls -la /etc/dynipv6/
ls -la /var/lib/dynipv6/
```

**Docker:**
```bash
# Logs prüfen
docker-compose logs ddns-api

# Container-Status
docker-compose ps

# Container neu starten
docker-compose restart ddns-api
```

### ISPConfig-Verbindung schlägt fehl

1. **URL überprüfen:**
   ```bash
   curl -k https://ispconfig.example.com:8080/api/
   ```

2. **Firewall prüfen:**
   ```bash
   sudo ufw status
   sudo ufw allow 8080
   ```

3. **Berechtigungen prüfen:**
   - Admin oder Reseller-Konto verwenden
   - Remote API aktiviert

4. **Test durchführen:**
   - Web-UI öffnen
   - Settings → Test ISPConfig klicken

### DDNS-Updates funktionieren nicht

```bash
# Token überprüfen
curl -X GET "https://ipv6.example.com/api/status?token=YOUR_TOKEN"

# Manueller Update-Test
curl -X POST https://ipv6.example.com/api/update \
  -d "token=YOUR_TOKEN&ipv6=2001:db8::1"

# Logs anzeigen
docker-compose logs -f ddns-api
```

### Hohe CPU/Memory-Auslastung

```bash
# Ressourcenverbrauch prüfen
docker stats

# Memory-Leak prüfen
docker-compose logs --tail 100 | grep -i "memory\|error"

# Service neu starten
docker-compose restart ddns-api
```

### Web-UI nicht erreichbar

1. **HTTPS-Zertifikat prüfen:**
   ```bash
   sudo openssl x509 -in /etc/letsencrypt/live/ip.example.com/fullchain.pem -text -noout
   ```

2. **Nginx-Status prüfen:**
   ```bash
   # Docker
   docker-compose ps ddns-nginx
   
   # Bare Metal
   sudo systemctl status nginx
   ```

3. **Logs anzeigen:**
   ```bash
   # Docker
   docker-compose logs ddns-nginx
   
   # Bare Metal
   sudo tail -f /var/log/nginx/error.log
   ```

## Häufig gestellte Fragen

**F: Wie viele DDNS-Updates pro Sekunde sind möglich?**
A: Das System kann 100+ Updates pro Sekunde verarbeiten. Bei höherem Aufkommen limitiert Nginx automatisch auf 10 req/s für die API.

**F: Werden die ISPConfig-Passwörter sicher gespeichert?**
A: Ja, alle Passwörter werden mit AES-128 Fernet-Verschlüsselung verschlüsselt gespeichert.

**F: Kann ich das Service selbst hosten?**
A: Ja, das ist der Zweck des Service. Alles läuft auf Ihrem Server.

**F: Wie lange sind die API-Token?**
A: Token sind 32 Zeichen lange Zeichenketten, die automatisch generiert werden.

**F: Was passiert, wenn ISPConfig ausfällt?**
A: Das Service versucht 3-mal zu verbinden mit exponentieller Backoff. Nach 3 Fehlversuchen wird ein Fehler geloggt.

**F: Kann ich mehrere ISPConfig-Server verwenden?**
A: Derzeit wird nur ein ISPConfig-Server unterstützt. Sie können aber einen Load-Balancer davor setzen.

## Support und weitere Hilfe

### Dokumentation
- [README.md](README.md) - Überblick und Features
- [PRODUCTION.md](PRODUCTION.md) - Docker Deployment & Sicherheit
- [API.md](API.md) - Vollständige API-Dokumentation
- [ISPCONFIG_SETUP.md](ISPCONFIG_SETUP.md) - ISPConfig-Integration
- [WEBUI_SETUP.md](WEBUI_SETUP.md) - Web-Admin-Panel
- [UNIFI_SETUP.md](UNIFI_SETUP.md) - UniFi-Integration

### Health Check durchführen

```bash
bash test.sh
```

Dieser Befehl überprüft:
- Alle Services laufen
- Ports sind erreichbar
- Zertifikate sind gültig
- ISPConfig verbunden
- Speicher und Festplatte

## Checkliste für Produktivbetrieb

- [ ] Alle 3 Zertifikate erstellt
- [ ] config.json mit ISPConfig-Anmeldedaten konfiguriert
- [ ] ISPConfig-Verbindung getestet
- [ ] UniFi DDNS konfiguriert
- [ ] Health Check durchführen
- [ ] Automatische Backups einrichten
- [ ] Zertifikat-Erneuerung testen
- [ ] Firewall-Regeln einrichten
- [ ] Monitoring (optional) konfigurieren

---

**Für Fragen oder Probleme:** GitHub Issues oder Logs prüfen.
