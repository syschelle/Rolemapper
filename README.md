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
- Runtime data persists in project folders via compose mounts:
  - `./config`
  - `./output`
  - `./Aufgabe`
  - `./mapping_store` (includes `mapping_store.db`)
- Server mappings use DB-only storage (`mapping_store/mapping_store.db`).

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
