#!/usr/bin/env bash
set -euo pipefail

# Reset the Rolemapper admin password inside the running Docker Compose app.
# Run this script from the Rolemapper deployment directory.

SERVICE_NAME="${ROLEMAPPER_SERVICE:-rolemapper}"
CONFIG_PATH="${ROLEMAPPER_AUTH_CONFIG:-/app/config/auth_settings.json}"

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "ERROR: Neither 'docker compose' nor 'docker-compose' was found." >&2
  exit 1
fi

if [[ ! -f docker-compose.yml && ! -f compose.yml && ! -f docker-compose.yaml && ! -f compose.yaml ]]; then
  echo "ERROR: No Docker Compose file found in the current directory." >&2
  echo "Please run this script from the Rolemapper deployment directory." >&2
  exit 1
fi

if ! "${COMPOSE[@]}" ps "$SERVICE_NAME" >/dev/null 2>&1; then
  echo "ERROR: Compose service '$SERVICE_NAME' was not found." >&2
  echo "If your service has another name, run: ROLEMAPPER_SERVICE=<name> $0" >&2
  exit 1
fi

read -rsp "New admin password: " PASSWORD_ONE
echo
read -rsp "Repeat new admin password: " PASSWORD_TWO
echo

if [[ -z "$PASSWORD_ONE" ]]; then
  echo "ERROR: Password must not be empty." >&2
  exit 1
fi

if [[ "$PASSWORD_ONE" != "$PASSWORD_TWO" ]]; then
  echo "ERROR: Passwords do not match." >&2
  exit 1
fi

printf '%s' "$PASSWORD_ONE" | "${COMPOSE[@]}" exec -T "$SERVICE_NAME" python -c '
import json
import sys
from pathlib import Path

from werkzeug.security import generate_password_hash

password = sys.stdin.read()
config_path = Path(sys.argv[1])
langs = ["de", "en", "it", "fr", "pt", "es"]

if config_path.exists():
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: Cannot parse {config_path}: {exc}")
else:
    data = {}

if not isinstance(data, dict):
    data = {}

hashes = data.get("i18n_hashes")
if not isinstance(hashes, dict):
    hashes = {}

data["admin_hash"] = generate_password_hash(password, method="pbkdf2:sha256")
data["i18n_hashes"] = {lang: str(hashes.get(lang, "") or "") for lang in langs}

config_path.parent.mkdir(parents=True, exist_ok=True)
config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Admin password reset in {config_path}.")
' "$CONFIG_PATH"

unset PASSWORD_ONE PASSWORD_TWO

echo "Done. A restart is usually not required; log in with the new admin password."
