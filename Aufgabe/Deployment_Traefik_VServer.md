# Rolemapper Deployment auf VServer mit bestehendem Traefik (Docker)

## Ziel
Diese Anleitung zeigt, wie du den Python-Rolemapper produktiv auf einem VServer betreibst, wenn **Docker + Traefik bereits laufen**.

---

## Voraussetzungen

- Docker + Docker Compose installiert
- Traefik läuft bereits als Docker-Container
- Traefik-Docker-Netzwerk vorhanden (z. B. `traefik`)
- DNS-Eintrag gesetzt, z. B.:
  - `rolemapper.deinedomain.tld` → öffentliche IP des VServers

> Passe Domain, Pfade und Netzwerknamen an deine Umgebung an.

---

## 1) Projekt auf den Server kopieren

Beispiel-Zielpfad:

```bash
/opt/rolemapper
```

Dorthin sollten mindestens diese Dateien/Ordner:

- `app/`
- `config/`
- `requirements.txt`
- `Dockerfile`

Optional:

- `output/` (wird sonst automatisch erstellt)
- `Aufgabe/` (wenn du Referenzdateien dort brauchst)

---

## 2) Docker Compose für Rolemapper anlegen

Datei: `/opt/rolemapper/docker-compose.yml`

```yaml
services:
  rolemapper:
    build: .
    container_name: rolemapper
    restart: unless-stopped
    environment:
      - TZ=Europe/Berlin
    volumes:
      - ./config:/app/config
      - ./output:/app/output
      - ./Aufgabe:/app/Aufgabe
    networks:
      - traefik
    labels:
      - traefik.enable=true

      # Router
      - traefik.http.routers.rolemapper.rule=Host(`rolemapper.deinedomain.tld`)
      - traefik.http.routers.rolemapper.entrypoints=websecure
      - traefik.http.routers.rolemapper.tls=true
      - traefik.http.routers.rolemapper.tls.certresolver=letsencrypt

      # Service (interner Port der Flask-App im Container)
      - traefik.http.services.rolemapper.loadbalancer.server.port=5080

      # Security Header Middleware (empfohlen)
      - traefik.http.middlewares.rolemapper-sec.headers.contentTypeNosniff=true
      - traefik.http.middlewares.rolemapper-sec.headers.browserXssFilter=true
      - traefik.http.middlewares.rolemapper-sec.headers.frameDeny=true
      - traefik.http.middlewares.rolemapper-sec.headers.referrerPolicy=no-referrer
      - traefik.http.routers.rolemapper.middlewares=rolemapper-sec

networks:
  traefik:
    external: true
```

---

## 3) Container starten

```bash
cd /opt/rolemapper
docker compose up -d --build
```

Status prüfen:

```bash
docker compose ps
docker compose logs -f rolemapper
```

---

## 4) App-Funktion prüfen

Im Browser:

- `https://rolemapper.deinedomain.tld`

Testen:

- Seite lädt
- Sprachumschaltung
- CSV/Testmodus
- TXT-Generierung
- Config-Seiten speichern

---

## 5) Wichtige Produktions-Hinweise

## 5.1 Zugriffsschutz (dringend)
Wenn die App öffentlich erreichbar ist, schütze sie mindestens mit Auth.

Optionen:
- Basic Auth via Traefik Middleware
- ForwardAuth / SSO (z. B. Authelia, OAuth2-Proxy)
- IP-Allowlist (falls nur intern genutzt)

## 5.2 Backups
Regelmäßig sichern:

- `/opt/rolemapper/config`
- `/opt/rolemapper/output`
- optional `/opt/rolemapper/Aufgabe`

## 5.3 Updates
Bei Änderungen im Code:

```bash
cd /opt/rolemapper
docker compose up -d --build
```

---

## 6) Optional: Gunicorn statt Flask Dev-Server

Für stabilen Produktivbetrieb ist Gunicorn empfohlen.

Beispiel Startkommando im Container:

```bash
gunicorn -w 2 -b 0.0.0.0:5080 app.app:app
```

Wenn du willst, kann das direkt in Dockerfile/Compose fest verdrahtet werden.

---

## 7) Troubleshooting

### 404/502 über Traefik
- Prüfe Traefik-Netzwerkname (`traefik`)
- Prüfe Label `loadbalancer.server.port=5080`
- Prüfe, ob Container im selben Netzwerk wie Traefik ist

### Zertifikat kommt nicht
- DNS zeigt nicht auf den Server
- CertResolver-Name (`letsencrypt`) passt nicht zu deiner Traefik-Konfiguration
- Port 80/443 nicht offen

### Änderungen in config werden nicht wirksam
- Volume-Mounts prüfen
- Container neu starten

```bash
docker compose restart rolemapper
```

---

## 8) Beispiel für Basic Auth Middleware (Traefik)

Zusätzlich in Labels (optional):

```yaml
- traefik.http.middlewares.rolemapper-auth.basicauth.users=<USER>:<HASH>
- traefik.http.routers.rolemapper.middlewares=rolemapper-auth,rolemapper-sec
```

`<HASH>` erzeugst du z. B. mit `htpasswd`.

---

Wenn du möchtest, erstelle ich dir im nächsten Schritt eine **an deine Domain + dein Traefik-Netzwerk angepasste, sofort startbare** `docker-compose.yml` (copy/paste-fertig).