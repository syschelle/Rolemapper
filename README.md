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

Reset admin password from the console:
```bash
./reset-admin-password.sh
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

## Install from a Docker image

The GitHub workflow publishes the app image to GitHub Container Registry:

```text
ghcr.io/syschelle/rolemapper
```

Create local runtime folders if they do not exist yet:

```bash
mkdir -p config output Aufgabe mapping_store
```

Copy the example environment and adjust secrets:

```bash
cp .env.example .env
```

Start the image-based setup:

```bash
docker compose -f docker-compose.image.yml up -d
```

Use a specific image tag when needed:

```bash
ROLEMAPPER_IMAGE=ghcr.io/syschelle/rolemapper:sha-<commit> docker compose -f docker-compose.image.yml up -d
```

Service URL in LAN:
- `http://<HOST-IP>:5080`

### Image build workflow

GitHub Actions builds and publishes the Docker image on:
- pushes to `main` or `master`
- tags matching `v*`
- manual workflow runs

Published tags include:
- branch name, for example `main`
- commit tag, for example `sha-424f4d2...`
- Git tags, for example `v1.0.0`
- `latest` on the default branch

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
