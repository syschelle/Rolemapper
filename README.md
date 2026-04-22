# Rolemapper (LDAP -> Keycloak)

## Run with Docker Compose (recommended)

```bash
docker compose up -d --build
```

Service URL in LAN:
- `http://<HOST-IP>:5080`

Stop:
```bash
docker compose down
```

### Notes
- Compose starts two containers:
  - `rolemapper` (app)
  - `rolemapper-db` (PostgreSQL)
- Runtime data persists in project folders via compose mounts:
  - `./config`
  - `./output`
  - `./Aufgabe`
  - `./mapping_store` (locks/auxiliary files)
- Database data persists in Docker volume `rolemapper-db-data`.
- Server mappings use the PostgreSQL container as single source of truth.

## Run locally without Docker

```bash
cd app
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
python app.py
```

## What it does
- Loads mapping from `../Aufgabe/mapping.txt`
- Accepts CSV uploads
- Ignores code-like columns (`code`, `script`, `snippet`)
- Shows preview before processing
- Generates TXT output and offers download
