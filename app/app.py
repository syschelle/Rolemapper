import csv
import hashlib
import io
import json
import os
import re
import secrets
import psycopg
from psycopg.rows import dict_row
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlparse

from werkzeug.security import check_password_hash, generate_password_hash

from flask import Flask, flash, jsonify, redirect, render_template, request, send_file, session, url_for

# --- Path setup ------------------------------------------------------------
# BASE_DIR: application source folder (app/)
# PROJECT_DIR: project root (contains app/, config/, Aufgabe/, ...)
# TASK_DIR: optional source folder used during development/migration
# CONFIG_DIR: runtime-editable configuration folder
BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
TASK_DIR = PROJECT_DIR / "Aufgabe"
CONFIG_DIR = PROJECT_DIR / "config"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

MAPPING_TXT = TASK_DIR / "mapping.txt"
MAPPING_XLSM = TASK_DIR / "LDAP2KeycloakMapping.xlsm"
PERSONAS_JSON = CONFIG_DIR / "personas.json"
ROLES_JSON = CONFIG_DIR / "roles_column_a.json"
APP_SETTINGS_JSON = CONFIG_DIR / "app_settings.json"
PERSONA_NAMES_JSON = CONFIG_DIR / "persona_names.json"
PERSONA_DESCRIPTIONS_JSON = CONFIG_DIR / "persona_descriptions.json"
ROLE_DESCRIPTIONS_JSON = CONFIG_DIR / "role_descriptions.json"
AUTH_SETTINGS_JSON = CONFIG_DIR / "auth_settings.json"
SAMPLE_ROLES_JSON = CONFIG_DIR / "sample_roles.json"
PERSONA_SOURCE_XLSX = TASK_DIR / "Rollen in DU.xlsx"
I18N_OVERRIDES_JSON = CONFIG_DIR / "i18n_overrides.json"
CHANGELOG_MD = TASK_DIR / "CHANGELOG.md"
BUNDLED_CHANGELOG_MD = BASE_DIR / "CHANGELOG_BUNDLED.md"

OUTPUT_DIR = PROJECT_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MAPPING_STORE_DIR = PROJECT_DIR / "mapping_store"
MAPPING_STORE_DIR.mkdir(parents=True, exist_ok=True)
MAPPING_LOCK_DIR = MAPPING_STORE_DIR / "_locks"
MAPPING_LOCK_DIR.mkdir(parents=True, exist_ok=True)
MAPPING_LOCK_TTL_SECONDS = 20 * 60
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rolemapper:rolemapper@db:5432/rolemapper")

# Compatibility map old <-> new permission names.
# Source of truth: Aufgabe/Persona-Permission-Mapping.xlsx, sheet "oldperm-newperm".
PERMISSION_PAIRS: List[Tuple[str, str]] = []
PERMISSION_OLD_TO_NEW: Dict[str, str] = {}
PERMISSION_NEW_TO_OLD: Dict[str, str] = {}
PERMISSION_NEW_ONLY: set[str] = set()
PERMISSION_COMPAT: Dict[str, List[str]] = {}

DEFAULT_PERSONAS = [
    "DUClinician",
    "DUReviewer",
    "DUFinalReporter",
    "DUReporter",
    "DUSystemAdministrator",
    "DUGuest",
    "DUObserver",
    "DUMedicalSecretary",
    "DUNurse",
    "DUClinicalDataAdministrator",
    "DURadiologist",
    "DUPathologist",
    "DUSpecializedClinician",
    "DUClinicalWorkflowManager",
    "DUScheduler",
    "DUTemplateDesigner",
]

app = Flask(__name__)
app.secret_key = "rolemapper-local-dev"
APP_VERSION = "1.0.15"
SUPPORTED_LANGS = ["de", "en", "it", "fr", "pt", "es"]


def _db_connect():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, autocommit=True)


def _init_mapping_db() -> None:
    with _db_connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mapping_records (
              code TEXT PRIMARY KEY,
              country TEXT NOT NULL DEFAULT '',
              postal_code TEXT NOT NULL DEFAULT '',
              city TEXT NOT NULL DEFAULT '',
              customer_no TEXT NOT NULL DEFAULT '',
              site TEXT NOT NULL DEFAULT '',
              customer TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              created_at_client TEXT NOT NULL DEFAULT '',
              updated_at TEXT NOT NULL,
              updated_at_client TEXT NOT NULL DEFAULT '',
              line_count INTEGER NOT NULL DEFAULT 0,
              source_roles_json TEXT NOT NULL DEFAULT '[]',
              mapping_lines_text TEXT NOT NULL DEFAULT '',
              deleted INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mapping_history (
              id BIGSERIAL PRIMARY KEY,
              code TEXT NOT NULL,
              event_type TEXT NOT NULL,
              changed_at TEXT NOT NULL,
              actor TEXT NOT NULL DEFAULT '',
              meta_json TEXT NOT NULL DEFAULT '{}',
              mapping_lines_text TEXT NOT NULL DEFAULT ''
            )
            """
        )


def _history_actor() -> str:
    # Prefer the resolved editor label (includes detected SSO/cookie/manual name + role).
    try:
        _eid, label = _editor_identity()
        clean = sanitize_plain_text(label or "")
        if clean:
            return clean[:120]
    except Exception:
        pass

    if session.get("auth_admin"):
        return "admin"
    if session.get("auth_i18n_langs"):
        return "localizer"
    return "user"


def _record_history(
    conn,
    code: str,
    event_type: str,
    meta: Dict[str, str],
    lines: List[str],
) -> None:
    conn.execute(
        """
        INSERT INTO mapping_history (code, event_type, changed_at, actor, meta_json, mapping_lines_text)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            code,
            event_type,
            datetime.now().isoformat(),
            _history_actor(),
            json.dumps(meta, ensure_ascii=False),
            "\n".join(lines),
        ),
    )


def mapping_record_exists(code: str) -> bool:
    safe_code = re.sub(r"[^A-Z0-9]", "", (code or "").upper())[:20]
    if not safe_code:
        return False
    _init_mapping_db()
    with _db_connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM mapping_records WHERE code = %s AND deleted = 0 LIMIT 1",
            (safe_code,),
        ).fetchone()
    return bool(row)

I18N_EDITOR_DEFAULTS: Dict[str, Dict[str, str]] = {
    "de": {
        "menu": "Menü / Navigation",
        "nav.main": "Hauptseite", "nav.serverMappings": "Server-Mappings", "server.title": "Server-Mappings", "server.hint": "Kein Mapping-Inhalt wird angezeigt. Datum/Uhrzeit nutzt primär Browserzeit (Fallback: Serverzeit).", "server.searchCountry": "Suche Land (z.B. DE)", "server.searchPostal": "Suche PLZ", "server.searchCity": "Suche Stadt", "server.searchCustomerNo": "Suche Kundennummer", "server.searchCustomer": "Suche Kunde", "server.colAction": "Aktion", "server.colTxt": "TXT", "server.colCode": "Code", "server.colCountry": "Land", "server.colPostal": "PLZ", "server.colCity": "Stadt", "server.colCustomerNo": "Kundennummer", "server.colSide": "Side", "server.colCustomer": "Kunde", "server.colLines": "Zeilen", "server.colUpdated": "Zuletzt geändert", "server.btnLoad": "Laden", "server.empty": "Keine gespeicherten Mappings gefunden.",
        "nav.guide": "Anleitung / Guide",
        "nav.personaConfig": "Persona-Konfiguration",
        "nav.roles": "Rollenliste bearbeiten",
        "nav.personaNames": "Persona-Liste bearbeiten",
        "hint": "CSV hochladen oder Testmodus nutzen, Personas zuordnen, TXT herunterladen.",
        "sec.uploadTitle": "1) CSV Upload / CSV hochladen oder TXT Upload / TXT hochladen",
        "sec.uploadHint": "Hinweis: Mögliche Dateien werden akzeptiert. CSV mit den Rollen der externen Authentifizierung oder bestehende mapping.txt (bzw. neueste mapping-*.txt).",
        "btn.validate": "Validieren & Zuordnung vorbereiten",
        "sec.testTitle": "2) Test ohne CSV",
        "btn.createTest": "Test-Zuordnung erstellen",
        "sec.loadTitle": "Mapping laden", "sec.mappingTitle": "Mapping (Drag & Drop)",
        "msg.loadFirst": "Bitte zuerst mapping.txt importieren, externe Rollen einfügen oder Mapping-Code vom Server eingeben, damit LDAP/ORBIS-Rollen angezeigt werden.",
        "copyFrom": "In diese Rolle kopieren von:",
        "selectRole": "-- Rolle wählen --",
        "copyBtn": "Kopieren",
        "generateTxt": "TXT erzeugen",
        "chooseFile": "Datei auswählen",
        "noFile": "Keine Datei ausgewählt", "showDesc": "Erklärung anzeigen",
        "guide.title": "Anleitung",
        "guide.h1": "So bedienst du die Hauptseite",
        "guide.s1": "Datei laden: CSV hochladen oder Testmodus nutzen.",
        "guide.s2": "Automatische Vorbelegung: vorhandene mapping.txt / mapping-*.txt wird berücksichtigt.",
        "guide.s3": "Mapping erstellen: Personas per Drag & Drop auf LDAP/ORBIS-Rollen ziehen.",
        "guide.s4": "Optional kopieren: Mit „Copy from“ Zuordnung von einer Rolle auf eine andere übernehmen.",
        "guide.s5": "TXT erzeugen: Button klicken, Download startet automatisch.",
        "guide.s6": "Permission-Modus: In Persona-Konfiguration Auto/Force old/Force new einstellen.", "guide.s7": "Externer Zugriff: Mit https://FQDN/api/edit-mapping/<Mappingcode> ein gespeichertes Mapping direkt laden und bearbeiten.",
        "guide.tips": "Tipps",
        "guide.t1": "Doppelklick auf einen Eintrag im Zielbereich entfernt ihn.",
        "guide.t2": "Die Sprache ist live umschaltbar; Personas/Rollen bleiben unverändert.",
        "guide.t3": "Wenn etwas fehlt: Seite mit Strg+F5 neu laden.",
        "persona_names.title": "Persona-Liste bearbeiten", "persona_names.hint": "Personas A-Z sortiert. Bestehende Personas-Namen sind nicht editierbar, nur die Erklärung darf bearbeitet werden. Neue Zeile hinzufügen erlaubt neue Persona.", "persona_names.count": "Aktuelle Anzahl:", "persona_names.colPersona": "Persona", "persona_names.colDesc": "Erklärung", "persona_names.colAction": "Aktion", "persona_names.addRow": "+ Neue Zeile", "persona_names.delete": "Löschen", "persona_names.confirmDelete": "Zeile wirklich löschen?", "persona_names.searchPh": "Suchen...",
        "auth_config.title": "Konfiguration", "auth_config.status": "Status:", "auth_config.adminSet": "Admin gesetzt", "auth_config.i18nSet": "I18N gesetzt", "auth_config.yes": "ja", "auth_config.no": "nein", "auth_config.adminPw": "Admin-Passwort", "auth_config.newAdminPw": "Neues Admin-Passwort", "auth_config.confirmAdminPw": "Admin-Passwort bestätigen", "auth_config.i18nPw": "I18N-Passwort (nur Lokalisierung)", "auth_config.newI18nPw": "Neues I18N-Passwort", "auth_config.confirmI18nPw": "I18N-Passwort bestätigen", "auth_config.save": "Speichern", "auth_config.sampleRoles": "Beispiel AD/ORBIS Gruppen", "auth_config.sampleRolesHint": "Eine Rolle pro Zeile. Wird für den Button „Beispielrollen einfügen“ genutzt."
    },
    "en": {
        "menu": "Menu / Navigation", "nav.main": "Main page", "nav.serverMappings": "Server mappings", "server.title": "Server mappings", "server.hint": "No mapping content is shown. Date/time primarily uses browser time (fallback: server time).", "server.searchCountry": "Search country (e.g. DE)", "server.searchPostal": "Search ZIP", "server.searchCity": "Search city", "server.searchCustomerNo": "Search customer no.", "server.searchCustomer": "Search customer", "server.colAction": "Action", "server.colTxt": "TXT", "server.colCode": "Code", "server.colCountry": "Country", "server.colPostal": "ZIP", "server.colCity": "City", "server.colCustomerNo": "Customer no.", "server.colSide": "Side", "server.colCustomer": "Customer", "server.colLines": "Lines", "server.colUpdated": "Last updated", "server.btnLoad": "Load", "server.empty": "No saved mappings found.", "nav.guide": "Guide", "nav.personaConfig": "Persona configuration", "nav.roles": "Edit roles list", "nav.personaNames": "Edit persona names",
        "hint": "Upload CSV or use test mode, map personas, download TXT.", "sec.uploadTitle": "1) CSV upload or TXT upload", "sec.uploadHint": "Note: Supported files are accepted. CSV with external authentication roles or existing mapping.txt (or newest mapping-*.txt).",
        "btn.validate": "Validate & prepare assignment", "sec.testTitle": "2) Test without CSV", "btn.createTest": "Create test assignment", "sec.loadTitle": "Load mapping", "sec.mappingTitle": "Mapping (Drag & Drop)",
        "msg.loadFirst": "Please import mapping.txt, paste external roles, or enter a mapping code from server first so LDAP/ORBIS roles become visible.", "copyFrom": "Copy to this role from:", "selectRole": "-- select role --", "copyBtn": "Copy", "generateTxt": "Generate TXT", "chooseFile": "Choose file", "noFile": "No file selected", "showDesc": "Show description",
        "guide.title": "Guide", "guide.h1": "How to use the main page", "guide.s1": "Load file: upload CSV or use test mode.", "guide.s2": "Auto prefill: existing mapping.txt / mapping-*.txt is considered.", "guide.s3": "Build mapping: drag personas onto LDAP/ORBIS roles.",
        "guide.s4": "Optional copy: use \"Copy from\" to duplicate mappings between roles.", "guide.s5": "Generate TXT: click button, download starts automatically.", "guide.s6": "Permission mode: set Auto/Force old/Force new in persona configuration.", "guide.s7": "External access: Use https://FQDN/api/edit-mapping/<Mappingcode> to load and edit a saved mapping directly.",
        "guide.tips": "Tips", "guide.t1": "Double-click an entry in target area to remove it.", "guide.t2": "Language switches live; personas/roles stay unchanged.", "guide.t3": "If something is missing: hard refresh with Ctrl+F5.",
        "persona_names.title": "Edit persona list", "persona_names.hint": "Personas sorted A-Z. Existing persona names are not editable; only the description may be edited. Adding a new row allows a new persona.", "persona_names.count": "Current count:", "persona_names.colPersona": "Persona", "persona_names.colDesc": "Description", "persona_names.colAction": "Action", "persona_names.addRow": "+ Add row", "persona_names.delete": "Delete", "persona_names.confirmDelete": "Really delete this row?", "persona_names.searchPh": "Search...",
        "auth_config.title": "Configuration", "auth_config.status": "Status:", "auth_config.adminSet": "Admin set", "auth_config.i18nSet": "I18N set", "auth_config.yes": "yes", "auth_config.no": "no", "auth_config.adminPw": "Admin password", "auth_config.newAdminPw": "New admin password", "auth_config.confirmAdminPw": "Confirm admin password", "auth_config.i18nPw": "I18N password (localization only)", "auth_config.newI18nPw": "New I18N password", "auth_config.confirmI18nPw": "Confirm I18N password", "auth_config.save": "Save", "auth_config.sampleRoles": "Sample AD/ORBIS groups", "auth_config.sampleRolesHint": "One role per line. Used by the \"Insert sample roles\" button."
    },
    "it": {
        "menu": "Menu / Navigazione", "nav.main": "Pagina principale", "nav.serverMappings": "Mapping server", "server.title": "Mapping server", "server.hint": "Il contenuto del mapping non viene mostrato. Data/ora usa principalmente l'ora del browser (fallback: ora server).", "server.searchCountry": "Cerca paese (es. DE)", "server.searchPostal": "Cerca CAP", "server.searchCity": "Cerca città", "server.searchCustomerNo": "Cerca numero cliente", "server.searchCustomer": "Cerca cliente", "server.colAction": "Azione", "server.colTxt": "TXT", "server.colCode": "Codice", "server.colCountry": "Paese", "server.colPostal": "CAP", "server.colCity": "Città", "server.colCustomerNo": "Numero cliente", "server.colSide": "Side", "server.colCustomer": "Cliente", "server.colLines": "Righe", "server.colUpdated": "Ultima modifica", "server.btnLoad": "Carica", "server.empty": "Nessun mapping salvato trovato.", "nav.guide": "Guida", "nav.personaConfig": "Configurazione persona", "nav.roles": "Modifica elenco ruoli", "nav.personaNames": "Modifica elenco persona",
        "hint": "Carica CSV o usa la modalità test, mappa le personas e scarica TXT.", "sec.uploadTitle": "1) Carica CSV o TXT", "sec.uploadHint": "Nota: sono accettati file supportati. CSV con ruoli di autenticazione esterna o mapping.txt esistente (o il più recente mapping-*.txt).",
        "btn.validate": "Valida e prepara assegnazione", "sec.testTitle": "2) Test senza CSV", "btn.createTest": "Crea assegnazione di test", "sec.loadTitle": "Carica mapping", "sec.mappingTitle": "Mappatura (Drag & Drop)",
        "msg.loadFirst": "Importa prima mapping.txt, incolla ruoli esterni o inserisci un codice mapping dal server per mostrare i ruoli LDAP/ORBIS.", "copyFrom": "Copia in questo ruolo da:", "selectRole": "-- seleziona ruolo --", "copyBtn": "Copia", "generateTxt": "Genera TXT", "chooseFile": "Scegli file", "noFile": "Nessun file selezionato", "showDesc": "Mostra descrizione",
        "guide.title": "Guida", "guide.h1": "Come usare la pagina principale", "guide.s1": "Carica file: CSV o modalità test.", "guide.s2": "Prefill automatico: considera mapping.txt / mapping-*.txt.", "guide.s3": "Crea mapping: trascina personas sui ruoli LDAP/ORBIS.",
        "guide.s4": "Copia opzionale: usa \"Copy from\" per duplicare mappature.", "guide.s5": "Genera TXT: clicca il pulsante, download automatico.", "guide.s6": "Modalità permessi: imposta Auto/Force old/Force new nella configurazione persona.", "guide.s7": "Accesso esterno: usa https://FQDN/api/edit-mapping/<Mappingcode> per caricare e modificare direttamente un mapping salvato.",
        "guide.tips": "Suggerimenti", "guide.t1": "Doppio click su una voce nell'area target per rimuoverla.", "guide.t2": "La lingua cambia al volo; personas/ruoli restano invariati.", "guide.t3": "Se manca qualcosa: aggiorna con Ctrl+F5.",
        "persona_names.title": "Modifica elenco persona", "persona_names.hint": "Personas ordinate A-Z. I nomi delle personas esistenti non sono modificabili; è modificabile solo la descrizione. Aggiungere una nuova riga consente una nuova persona.", "persona_names.count": "Conteggio attuale:", "persona_names.colPersona": "Persona", "persona_names.colDesc": "Descrizione", "persona_names.colAction": "Azione", "persona_names.addRow": "+ Nuova riga", "persona_names.delete": "Elimina", "persona_names.confirmDelete": "Eliminare davvero questa riga?", "persona_names.searchPh": "Cerca...",
        "auth_config.title": "Configurazione", "auth_config.status": "Stato:", "auth_config.adminSet": "Admin impostato", "auth_config.i18nSet": "I18N impostato", "auth_config.yes": "sì", "auth_config.no": "no", "auth_config.adminPw": "Password admin", "auth_config.newAdminPw": "Nuova password admin", "auth_config.confirmAdminPw": "Conferma password admin", "auth_config.i18nPw": "Password I18N (solo localizzazione)", "auth_config.newI18nPw": "Nuova password I18N", "auth_config.confirmI18nPw": "Conferma password I18N", "auth_config.save": "Salva", "auth_config.sampleRoles": "Gruppi AD/ORBIS di esempio", "auth_config.sampleRolesHint": "Un ruolo per riga. Usato dal pulsante per inserire ruoli di esempio."
    },
    "fr": {
        "menu": "Menu / Navigation", "nav.main": "Page principale", "nav.serverMappings": "Mappings serveur", "server.title": "Mappings serveur", "server.hint": "Le contenu du mapping n'est pas affiché. Date/heure utilise d'abord l'heure du navigateur (fallback : serveur).", "server.searchCountry": "Rechercher pays (ex. DE)", "server.searchPostal": "Rechercher CP", "server.searchCity": "Rechercher ville", "server.searchCustomerNo": "Rechercher n° client", "server.searchCustomer": "Rechercher client", "server.colAction": "Action", "server.colTxt": "TXT", "server.colCode": "Code", "server.colCountry": "Pays", "server.colPostal": "CP", "server.colCity": "Ville", "server.colCustomerNo": "N° client", "server.colSide": "Side", "server.colCustomer": "Client", "server.colLines": "Lignes", "server.colUpdated": "Dernière modification", "server.btnLoad": "Charger", "server.empty": "Aucun mapping enregistré trouvé.", "nav.guide": "Guide", "nav.personaConfig": "Configuration des personas", "nav.roles": "Modifier la liste des rôles", "nav.personaNames": "Modifier la liste des personas",
        "hint": "Téléchargez un CSV ou utilisez le mode test, mappez les personas, téléchargez le TXT.", "sec.uploadTitle": "1) Téléchargement CSV ou TXT", "sec.uploadHint": "Remarque : les fichiers pris en charge sont acceptés. CSV avec les rôles d'authentification externe ou mapping.txt existant (ou le plus récent mapping-*.txt).",
        "btn.validate": "Valider et préparer l'affectation", "sec.testTitle": "2) Test sans CSV", "btn.createTest": "Créer une affectation de test", "sec.loadTitle": "Charger mapping", "sec.mappingTitle": "Mapping (Glisser-déposer)",
        "msg.loadFirst": "Veuillez d'abord importer mapping.txt, coller des rôles externes ou saisir un code mapping du serveur afin d'afficher les rôles LDAP/ORBIS.", "copyFrom": "Copier vers ce rôle depuis :", "selectRole": "-- sélectionner un rôle --", "copyBtn": "Copier", "generateTxt": "Générer TXT", "chooseFile": "Choisir un fichier", "noFile": "Aucun fichier sélectionné", "showDesc": "Afficher la description",
        "guide.title": "Guide", "guide.h1": "Comment utiliser la page principale", "guide.s1": "Charger un fichier : téléverser CSV ou utiliser le mode test.", "guide.s2": "Préremplissage auto : mapping.txt / mapping-*.txt existant est pris en compte.", "guide.s3": "Créer le mapping : glisser-déposer les personas sur les rôles LDAP/ORBIS.",
        "guide.s4": "Copie optionnelle : utilisez \"Copy from\" pour copier une affectation.", "guide.s5": "Générer TXT : cliquez, le téléchargement démarre automatiquement.", "guide.s6": "Mode de permission : régler Auto/Force old/Force new dans la config persona.", "guide.s7": "Accès externe : utilisez https://FQDN/api/edit-mapping/<Mappingcode> pour charger et modifier directement un mapping enregistré.",
        "guide.tips": "Conseils", "guide.t1": "Double-cliquez une entrée dans la zone cible pour la supprimer.", "guide.t2": "La langue change à chaud ; personas/rôles restent inchangés.", "guide.t3": "Si quelque chose manque : rechargez avec Ctrl+F5.",
        "persona_names.title": "Modifier la liste des personas", "persona_names.hint": "Personas triés A-Z. Les noms de personas existants ne sont pas modifiables ; seule la description peut être modifiée. Ajouter une nouvelle ligne permet un nouveau persona.", "persona_names.count": "Nombre actuel :", "persona_names.colPersona": "Persona", "persona_names.colDesc": "Description", "persona_names.colAction": "Action", "persona_names.addRow": "+ Nouvelle ligne", "persona_names.delete": "Supprimer", "persona_names.confirmDelete": "Supprimer vraiment cette ligne ?", "persona_names.searchPh": "Rechercher...",
        "auth_config.title": "Configuration", "auth_config.status": "Statut :", "auth_config.adminSet": "Admin défini", "auth_config.i18nSet": "I18N défini", "auth_config.yes": "oui", "auth_config.no": "non", "auth_config.adminPw": "Mot de passe admin", "auth_config.newAdminPw": "Nouveau mot de passe admin", "auth_config.confirmAdminPw": "Confirmer le mot de passe admin", "auth_config.i18nPw": "Mot de passe I18N (localisation uniquement)", "auth_config.newI18nPw": "Nouveau mot de passe I18N", "auth_config.confirmI18nPw": "Confirmer le mot de passe I18N", "auth_config.save": "Enregistrer", "auth_config.sampleRoles": "Groupes AD/ORBIS d'exemple", "auth_config.sampleRolesHint": "Un rôle par ligne. Utilisé par le bouton d'insertion de rôles d'exemple."
    },
    "pt": {
        "menu": "Menu / Navegação", "nav.main": "Página principal", "nav.serverMappings": "Mapeamentos do servidor", "server.title": "Mapeamentos do servidor", "server.hint": "O conteúdo do mapping não é exibido. Data/hora usa principalmente o horário do navegador (fallback: servidor).", "server.searchCountry": "Buscar país (ex. DE)", "server.searchPostal": "Buscar CEP", "server.searchCity": "Buscar cidade", "server.searchCustomerNo": "Buscar nº do cliente", "server.searchCustomer": "Buscar cliente", "server.colAction": "Ação", "server.colTxt": "TXT", "server.colCode": "Código", "server.colCountry": "País", "server.colPostal": "CEP", "server.colCity": "Cidade", "server.colCustomerNo": "Nº cliente", "server.colSide": "Side", "server.colCustomer": "Cliente", "server.colLines": "Linhas", "server.colUpdated": "Última alteração", "server.btnLoad": "Carregar", "server.empty": "Nenhum mapping salvo encontrado.", "nav.guide": "Guia", "nav.personaConfig": "Configuração de personas", "nav.roles": "Editar lista de roles", "nav.personaNames": "Editar lista de personas",
        "hint": "Envie CSV ou use modo de teste, mapeie personas e baixe TXT.", "sec.uploadTitle": "1) Upload CSV ou upload TXT", "sec.uploadHint": "Nota: arquivos suportados são aceitos. CSV com papéis de autenticação externa ou mapping.txt existente (ou o mais recente mapping-*.txt).",
        "btn.validate": "Validar e preparar atribuição", "sec.testTitle": "Teste sem CSV", "btn.createTest": "Criar atribuição de teste", "sec.loadTitle": "Carregar mapping", "sec.mappingTitle": "Mapeamento (Arrastar e soltar)",
        "msg.loadFirst": "Importe mapping.txt, cole roles externos ou informe o código de mapping do servidor para mostrar os papéis LDAP/ORBIS.", "copyFrom": "Copiar para este role de:", "selectRole": "-- selecionar role --", "copyBtn": "Copiar", "generateTxt": "Gerar TXT", "chooseFile": "Selecionar arquivo", "noFile": "Nenhum arquivo selecionado", "showDesc": "Mostrar descrição",
        "guide.title": "Guia", "guide.h1": "Como usar a página principal", "guide.s1": "Carregar arquivo: enviar CSV ou usar modo teste.", "guide.s2": "Pré-preenchimento automático: mapping.txt / mapping-*.txt existente é usado.", "guide.s3": "Criar mapeamento: arraste personas para roles LDAP/ORBIS.",
        "guide.s4": "Cópia opcional: use \"Copy from\" para copiar mapeamentos.", "guide.s5": "Gerar TXT: clique no botão, download inicia automaticamente.", "guide.s6": "Modo de permissão: definir Auto/Force old/Force new na configuração.", "guide.s7": "Acesso externo: use https://FQDN/api/edit-mapping/<Mappingcode> para carregar e editar diretamente um mapping salvo.",
        "guide.tips": "Dicas", "guide.t1": "Duplo clique remove item da área de destino.", "guide.t2": "Idioma muda ao vivo; personas/roles não são traduzidos.", "guide.t3": "Se faltar algo: recarregue com Ctrl+F5.",
        "persona_names.title": "Editar lista de personas", "persona_names.hint": "Personas ordenadas de A-Z. Os nomes das personas existentes não são editáveis; apenas a descrição pode ser editada. Adicionar uma nova linha permite uma nova persona.", "persona_names.count": "Quantidade atual:", "persona_names.colPersona": "Persona", "persona_names.colDesc": "Descrição", "persona_names.colAction": "Ação", "persona_names.addRow": "+ Nova linha", "persona_names.delete": "Excluir", "persona_names.confirmDelete": "Excluir esta linha mesmo?", "persona_names.searchPh": "Buscar...",
        "auth_config.title": "Configuración", "auth_config.status": "Estado:", "auth_config.adminSet": "Admin configurado", "auth_config.i18nSet": "I18N configurado", "auth_config.yes": "sí", "auth_config.no": "no", "auth_config.adminPw": "Contraseña admin", "auth_config.newAdminPw": "Nueva contraseña admin", "auth_config.confirmAdminPw": "Confirmar contraseña admin", "auth_config.i18nPw": "Contraseña I18N (solo localización)", "auth_config.newI18nPw": "Nueva contraseña I18N", "auth_config.confirmI18nPw": "Confirmar contraseña I18N", "auth_config.save": "Guardar", "auth_config.sampleRoles": "Grupos AD/ORBIS de ejemplo", "auth_config.sampleRolesHint": "Un rol por línea. Se usa para el botón de insertar roles de ejemplo.", "auth_config.sampleRoles": "Grupos AD/ORBIS de exemplo", "auth_config.sampleRolesHint": "Um role por linha. Usado pelo botão de inserir roles de exemplo."
    },
    "es": {
        "menu": "Menú / Navegación", "nav.main": "Página principal", "nav.guide": "Guía", "nav.personaConfig": "Configuración de personas", "nav.roles": "Editar lista de roles", "nav.personaNames": "Editar lista de personas",
        "hint": "Sube CSV o usa modo prueba, asigna personas y descarga TXT.", "sec.uploadTitle": "1) Carga CSV o carga TXT", "sec.uploadHint": "Nota: se aceptan archivos compatibles. CSV con roles de autenticación externa o mapping.txt existente (o el más reciente mapping-*.txt).",
        "btn.validate": "Validar y preparar asignación", "sec.testTitle": "Prueba sin CSV", "btn.createTest": "Crear asignación de prueba", "sec.loadTitle": "Cargar mapping", "sec.mappingTitle": "Mapeo (Arrastrar y soltar)",
        "msg.loadFirst": "Primero importa mapping.txt, pega roles externos o introduce un código de mapping del servidor para mostrar los roles LDAP/ORBIS.", "copyFrom": "Copiar a este rol desde:", "selectRole": "-- seleccionar rol --", "copyBtn": "Copiar", "generateTxt": "Generar TXT", "chooseFile": "Seleccionar archivo", "noFile": "Ningún archivo seleccionado", "showDesc": "Mostrar descripción",
        "guide.title": "Guía", "guide.h1": "Cómo usar la página principal", "guide.s1": "Cargar archivo: subir CSV o usar modo prueba.", "guide.s2": "Prefill automático: se considera mapping.txt / mapping-*.txt existente.", "guide.s3": "Crear mapeo: arrastra personas sobre roles LDAP/ORBIS.",
        "guide.s4": "Copia opcional: usa \"Copy from\" para duplicar mapeos.", "guide.s5": "Generar TXT: pulsa el botón, la descarga inicia automáticamente.", "guide.s6": "Modo de permisos: configura Auto/Force old/Force new en configuración.", "guide.s7": "Acceso externo: usa https://FQDN/api/edit-mapping/<Mappingcode> para cargar y editar directamente un mapping guardado.",
        "guide.tips": "Consejos", "guide.t1": "Doble clic elimina una entrada del área destino.", "guide.t2": "El idioma cambia al vuelo; personas/roles no se traducen.", "guide.t3": "Si falta algo: recarga con Ctrl+F5.",
        "persona_names.title": "Editar lista de personas", "persona_names.hint": "Personas ordenadas A-Z. Los nombres de personas existentes no se pueden editar; solo se puede editar la descripción. Agregar una nueva fila permite una nueva persona.", "persona_names.count": "Cantidad actual:", "persona_names.colPersona": "Persona", "persona_names.colDesc": "Descripción", "persona_names.colAction": "Acción", "persona_names.addRow": "+ Nueva fila", "persona_names.delete": "Eliminar", "persona_names.confirmDelete": "¿Eliminar realmente esta fila?", "persona_names.searchPh": "Buscar...",
        "auth_config.title": "Configuración", "auth_config.status": "Estado:", "auth_config.adminSet": "Admin configurado", "auth_config.i18nSet": "I18N configurado", "auth_config.yes": "sí", "auth_config.no": "no", "auth_config.adminPw": "Contraseña admin", "auth_config.newAdminPw": "Nueva contraseña admin", "auth_config.confirmAdminPw": "Confirmar contraseña admin", "auth_config.i18nPw": "Contraseña I18N (solo localización)", "auth_config.newI18nPw": "Nueva contraseña I18N", "auth_config.confirmI18nPw": "Confirmar contraseña I18N", "auth_config.save": "Guardar"
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    """Translate helper using in-code defaults (overrides are applied in templates)."""
    lang = (lang or "de").lower()
    if lang not in I18N_EDITOR_DEFAULTS:
        lang = "en"
    return I18N_EDITOR_DEFAULTS.get(lang, {}).get(key, key).format(**kwargs)


def build_unmapped_roles_warning(lang: str, roles: List[str]) -> str:
    role_list = ", ".join(roles)
    messages = {
        "de": f"Hinweis: Folgende AD/ORBIS-Rollen haben kein Mapping und erscheinen daher nicht in der TXT: {role_list}",
        "en": f"Note: The following AD/ORBIS roles have no mapping and therefore do not appear in the TXT: {role_list}",
        "it": f"Nota: I seguenti ruoli AD/ORBIS non hanno mapping e quindi non compaiono nel TXT: {role_list}",
        "fr": f"Remarque : les rôles AD/ORBIS suivants n'ont pas de mapping et n'apparaissent donc pas dans le TXT : {role_list}",
        "pt": f"Observação: os seguintes roles AD/ORBIS não têm mapping e por isso não aparecem no TXT: {role_list}",
        "es": f"Nota: los siguientes roles AD/ORBIS no tienen mapping y por eso no aparecen en el TXT: {role_list}",
    }
    return messages.get((lang or "de").lower(), messages["de"])


def build_unmapped_roles_header(lang: str) -> str:
    messages = {
        "de": "Hinweis: Folgende AD/ORBIS-Rollen haben kein Mapping und erscheinen daher nicht in der TXT:",
        "en": "Note: The following AD/ORBIS roles have no mapping and therefore do not appear in the TXT:",
        "it": "Nota: I seguenti ruoli AD/ORBIS non hanno mapping e quindi non compaiono nel TXT:",
        "fr": "Remarque : les rôles AD/ORBIS suivants n'ont pas de mapping et n'apparaissent donc pas dans le TXT :",
        "pt": "Observação: os seguintes roles AD/ORBIS não têm mapping e por isso não aparecem no TXT:",
        "es": "Nota: los siguientes roles AD/ORBIS no tienen mapping y por eso no aparecen en el TXT:",
    }
    return messages.get((lang or "de").lower(), messages["de"])


def build_unmapped_roles_file_line(lang: str, filename: str) -> str:
    messages = {
        "de": f"Erzeugte Datei: {filename}",
        "en": f"Generated file: {filename}",
        "it": f"File generato: {filename}",
        "fr": f"Fichier généré : {filename}",
        "pt": f"Arquivo gerado: {filename}",
        "es": f"Archivo generado: {filename}",
    }
    return messages.get((lang or "de").lower(), messages["de"])


def load_i18n_overrides() -> Dict[str, Dict[str, str]]:
    if not I18N_OVERRIDES_JSON.exists():
        return {}
    try:
        raw = json.loads(I18N_OVERRIDES_JSON.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return {}
        out: Dict[str, Dict[str, str]] = {}
        for lang, values in raw.items():
            if not isinstance(values, dict):
                continue
            clean: Dict[str, str] = {}
            for k, v in values.items():
                key = str(k).strip()
                if not key or key.startswith("insider"):
                    continue
                clean[key] = str(v)
            if clean:
                out[str(lang)] = clean
        return out
    except Exception:
        return {}

def save_i18n_overrides(data: Dict[str, Dict[str, str]]) -> None:
    clean_all: Dict[str, Dict[str, str]] = {}
    for lang, values in (data or {}).items():
        if not isinstance(values, dict):
            continue
        clean: Dict[str, str] = {}
        for k, v in values.items():
            key = str(k).strip()
            if not key or key.startswith("insider"):
                continue
            clean[key] = str(v)
        clean_all[str(lang)] = clean
    I18N_OVERRIDES_JSON.write_text(json.dumps(clean_all, indent=2, ensure_ascii=False), encoding="utf-8")

def load_sample_roles_text() -> str:
    if not SAMPLE_ROLES_JSON.exists():
        return ""
    try:
        raw = json.loads(SAMPLE_ROLES_JSON.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return str(raw.get("sample_roles_text", "") or "")
    except Exception:
        pass
    return ""

def save_sample_roles_text(text: str) -> None:
    lines = [x.strip() for x in str(text or "").splitlines()]
    clean = "\n".join(sanitize_lines(lines))
    SAMPLE_ROLES_JSON.write_text(
        json.dumps({"sample_roles_text": clean}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# --- Session/auth helpers ---------------------------------------------------
def _safe_next_path(raw_next: str | None) -> str:
    val = str(raw_next or "").strip()
    if not val:
        return "/"
    try:
        parsed = urlparse(val)
        if parsed.scheme or parsed.netloc:
            return "/"
    except Exception:
        return "/"
    return val if val.startswith("/") else "/"


def _is_admin_authenticated() -> bool:
    return bool(session.get("auth_admin"))


def _is_i18n_authenticated(lang: str | None = None) -> bool:
    langs = session.get("auth_i18n_langs", [])
    if not isinstance(langs, list):
        langs = []
    if lang:
        return str(lang).lower() in [str(l).lower() for l in langs]
    return bool(langs)


def _set_login_challenge(scope: str, next_path: str = "/", lang: str | None = None) -> None:
    session["login_scope"] = str(scope or "").strip().lower()
    session["login_next"] = _safe_next_path(next_path)
    if lang:
        session["login_lang"] = str(lang).strip().lower()


# Load persisted authentication hashes (admin + per-language localizer).
def load_auth_settings() -> Dict[str, object]:
    defaults: Dict[str, object] = {
        "admin_hash": "",
        "i18n_hashes": {lang: "" for lang in SUPPORTED_LANGS},
    }
    if not AUTH_SETTINGS_JSON.exists():
        return defaults
    try:
        raw = json.loads(AUTH_SETTINGS_JSON.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return defaults
        admin_hash = str(raw.get("admin_hash", "") or "")
        raw_hashes = raw.get("i18n_hashes")
        i18n_hashes = {lang: "" for lang in SUPPORTED_LANGS}
        if isinstance(raw_hashes, dict):
            for lang in SUPPORTED_LANGS:
                i18n_hashes[lang] = str(raw_hashes.get(lang, "") or "")
        return {"admin_hash": admin_hash, "i18n_hashes": i18n_hashes}
    except Exception:
        return defaults


def save_auth_settings(settings: Dict[str, object]) -> None:
    admin_hash = str((settings or {}).get("admin_hash", "") or "")
    raw_hashes = (settings or {}).get("i18n_hashes", {})
    i18n_hashes = {lang: "" for lang in SUPPORTED_LANGS}
    if isinstance(raw_hashes, dict):
        for lang in SUPPORTED_LANGS:
            i18n_hashes[lang] = str(raw_hashes.get(lang, "") or "")
    AUTH_SETTINGS_JSON.write_text(
        json.dumps({"admin_hash": admin_hash, "i18n_hashes": i18n_hashes}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


@app.context_processor
def inject_app_meta():
    """Expose app metadata to all templates."""
    settings = load_app_settings()
    requested_lang = (request.args.get("lang") or request.cookies.get("rolemapper_lang") or "de").strip().lower()
    if requested_lang not in SUPPORTED_LANGS:
        requested_lang = "de"
    return {
        "app_version": APP_VERSION,
        "i18n_overrides": load_i18n_overrides(),
        "auth_admin": bool(session.get("auth_admin")),
        "auth_i18n": _is_i18n_authenticated(),
        "show_test_banner": bool(settings.get("show_test_banner", True)),
        "current_lang": requested_lang,
    }


def sanitize_plain_text(value: str) -> str:
    """Keep plain text safe for UI rendering/storage (no HTML interpretation)."""
    v = str(value or "")
    v = v.replace("\x00", "")
    v = v.replace("<", "‹").replace(">", "›")
    return v.strip()

def sanitize_lines(values: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for v in values:
        c = sanitize_plain_text(v)
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out

def load_mapping(mapping_file: Path) -> Dict[str, List[str]]:
    """Load mapping lines in format SOURCE=TARGET from txt file."""
    mapping: Dict[str, List[str]] = {}
    if not mapping_file.exists():
        return mapping

    with mapping_file.open("r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or "=" not in line:
                continue
            source, target = line.split("=", 1)
            source = sanitize_plain_text(source)
            target = sanitize_plain_text(target)
            if not source or not target:
                continue
            if len(source) > 256 or len(target) > 256:
                continue
            if source.lower().startswith("javascript:") or target.lower().startswith("javascript:"):
                continue
            mapping.setdefault(source, [])
            if target not in mapping[source]:
                mapping[source].append(target)
    return mapping


def load_mapping_from_content(content: str) -> Dict[str, List[str]]:
    """Load mapping lines in format SOURCE=TARGET from plain text content."""
    mapping: Dict[str, List[str]] = {}
    for raw in str(content or "").splitlines():
        line = raw.strip()
        if not line or "=" not in line:
            continue
        source, target = line.split("=", 1)
        source = sanitize_plain_text(source)
        target = sanitize_plain_text(target)
        if not source or not target:
            continue
        if len(source) > 256 or len(target) > 256:
            continue
        if source.lower().startswith("javascript:") or target.lower().startswith("javascript:"):
            continue
        mapping.setdefault(source, [])
        if target not in mapping[source]:
            mapping[source].append(target)
    return mapping

def load_seed_mapping_for_prefill(task_dir: Path) -> Dict[str, List[str]]:
    """Load latest mapping-*.txt from Aufgabe as prefill source (fallback mapping.txt)."""
    candidates = sorted(task_dir.glob("mapping-*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    if candidates:
        return load_mapping(candidates[0])
    return load_mapping(task_dir / "mapping.txt")

def build_prefill_personas(
    source_roles: List[str],
    personas: Dict[str, List[str]],
    seed_mapping: Dict[str, List[str]],
) -> Dict[str, List[str]]:
    """Build initial persona assignments for UI from existing mapping TXT."""
    persona_names = set(personas.keys())
    prefill: Dict[str, List[str]] = {}

    for src in source_roles:
        targets = seed_mapping.get(src, [])
        selected = [t for t in targets if t in persona_names]
        prefill[src] = sorted(set(selected))

    return prefill

def build_prefill_roles(
    source_roles: List[str],
    persona_names: List[str],
    seed_mapping: Dict[str, List[str]],
) -> Dict[str, List[str]]:
    """Build initial direct role assignments for UI from existing mapping TXT."""
    persona_set = set(persona_names)
    prefill: Dict[str, List[str]] = {}
    for src in source_roles:
        targets = seed_mapping.get(src, [])
        # everything not recognized as persona is treated as direct role mapping
        selected = [t for t in targets if t not in persona_set]
        prefill[src] = sorted(set(selected))
    return prefill

def load_roles_from_xlsm(xlsm_file: Path) -> List[str]:
    """Read role list from column A in sheet1 of the xlsm file."""
    if not xlsm_file.exists():
        return []

    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    roles: List[str] = []

    with zipfile.ZipFile(xlsm_file) as zf:
        shared = []
        if "xl/sharedStrings.xml" in zf.namelist():
            sst = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in sst.findall("a:si", ns):
                txt = "".join(node.text or "" for node in si.findall(".//a:t", ns)).strip()
                shared.append(txt)

        ws = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
        for row in ws.findall(".//a:sheetData/a:row", ns):
            row_idx = int(row.attrib.get("r", "0"))
            if row_idx < 6:
                continue
            for cell in row.findall("a:c", ns):
                ref = cell.attrib.get("r", "")
                if not ref.startswith("A"):
                    continue
                ctype = cell.attrib.get("t")
                val_node = cell.find("a:v", ns)
                if val_node is None:
                    continue
                raw_val = val_node.text or ""
                if ctype == "s" and raw_val.isdigit():
                    idx = int(raw_val)
                    value = shared[idx] if idx < len(shared) else ""
                else:
                    value = raw_val
                value = value.strip()
                if value and value not in roles:
                    roles.append(value)

    return roles

def load_available_roles() -> List[str]:
    """Load editable roles list from JSON; fallback to XLSM and create JSON."""
    if ROLES_JSON.exists():
        try:
            data = json.loads(ROLES_JSON.read_text(encoding="utf-8"))
            if isinstance(data, list):
                roles = [str(x).strip() for x in data if str(x).strip()]
                return ensure_compat_roles(roles)
        except Exception:
            pass

    roles = load_roles_from_xlsm(MAPPING_XLSM)
    roles = ensure_compat_roles(roles)
    ROLES_JSON.write_text(json.dumps(roles, indent=2, ensure_ascii=False), encoding="utf-8")
    return roles

def ensure_compat_roles(roles: List[str]) -> List[str]:
    """Ensure both old and new permission names are available for compatibility."""
    out = []
    seen = set()

    for role in roles:
        r = str(role).strip()
        if not r:
            continue
        if r not in seen:
            seen.add(r)
            out.append(r)

        for alias in PERMISSION_COMPAT.get(r, []):
            if alias not in seen:
                seen.add(alias)
                out.append(alias)

    # Also ensure any explicitly new-only permission exists.
    if "report-ecg@duviewer" not in seen:
        out.append("report-ecg@duviewer")
    return out

def choose_permission_mode(roles: List[str], forced_mode: str = "auto") -> str:
    """Pick output mode (old/new) without mixing both at the same time."""
    fm = (forced_mode or "auto").strip().lower()
    if fm in {"old", "new"}:
        return fm
    old_count = 0
    new_count = 0

    for role in roles:
        r = str(role).strip()
        if not r:
            continue
        if r in PERMISSION_OLD_TO_NEW:
            old_count += 1
        elif r in PERMISSION_NEW_TO_OLD or r in PERMISSION_NEW_ONLY:
            new_count += 1

    # If both appear, pick the dominant style. Tie -> prefer NEW.
    if new_count >= old_count:
        return "new"
    return "old"

def expand_compat_permissions(roles: List[str], forced_mode: str = "auto") -> List[str]:
    """Normalize selected permissions to one style (old OR new), never both."""
    mode = choose_permission_mode(roles, forced_mode)

    expanded: List[str] = []
    seen = set()

    for role in roles:
        r = str(role).strip()
        if not r:
            continue

        candidate = r
        if mode == "new":
            if r in PERMISSION_OLD_TO_NEW:
                candidate = PERMISSION_OLD_TO_NEW[r]
        else:  # mode == "old"
            if r in PERMISSION_NEW_TO_OLD:
                candidate = PERMISSION_NEW_TO_OLD[r]
            elif r in PERMISSION_NEW_ONLY:
                # No old equivalent exists -> skip in old mode.
                continue

        if candidate not in seen:
            seen.add(candidate)
            expanded.append(candidate)

    return expanded

def roles_for_display_by_mode(roles: List[str], mode: str) -> List[str]:
    """Prepare role list for UI display depending on selected mode."""
    m = (mode or "auto").strip().lower()
    if m not in {"auto", "old", "new"}:
        m = "auto"

    if m == "auto":
        return roles

    out: List[str] = []
    seen = set()
    for role in roles:
        r = str(role).strip()
        if not r:
            continue

        candidate = r
        if m == "new":
            if r in PERMISSION_OLD_TO_NEW:
                candidate = PERMISSION_OLD_TO_NEW[r]
        else:  # old
            if r in PERMISSION_NEW_TO_OLD:
                candidate = PERMISSION_NEW_TO_OLD[r]
            elif r in PERMISSION_NEW_ONLY:
                continue

        if candidate not in seen:
            seen.add(candidate)
            out.append(candidate)
    return out

def save_available_roles(roles: List[str]) -> None:
    """Persist editable roles list."""
    cleaned = ensure_compat_roles(roles)
    ROLES_JSON.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False), encoding="utf-8")

def load_app_settings() -> Dict[str, object]:
    """Load app settings."""
    default: Dict[str, object] = {
        "permission_mode": "auto",
        "show_test_banner": True,
    }
    if not APP_SETTINGS_JSON.exists():
        APP_SETTINGS_JSON.write_text(json.dumps(default, indent=2, ensure_ascii=False), encoding="utf-8")
        return default
    try:
        data = json.loads(APP_SETTINGS_JSON.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            mode = str(data.get("permission_mode", "auto")).strip().lower()
            if mode not in {"auto", "old", "new"}:
                mode = "auto"
            show_test_banner = bool(data.get("show_test_banner", True))
            return {
                "permission_mode": mode,
                "show_test_banner": show_test_banner,
            }
    except Exception:
        pass
    return default

def save_app_settings(settings: Dict[str, object]) -> None:
    current = load_app_settings()
    mode = str(settings.get("permission_mode", current.get("permission_mode", "auto"))).strip().lower()
    if mode not in {"auto", "old", "new"}:
        mode = "auto"
    show_test_banner = bool(settings.get("show_test_banner", current.get("show_test_banner", True)))
    APP_SETTINGS_JSON.write_text(
        json.dumps({"permission_mode": mode, "show_test_banner": show_test_banner}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

def load_permission_pairs_from_xlsx(xlsx_file: Path) -> List[Tuple[str, str]]:
    """Read old/new permission pairs from sheet oldperm-newperm."""
    if not xlsx_file.exists():
        return []

    ns = {
        "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "p": "http://schemas.openxmlformats.org/package/2006/relationships",
    }

    pairs: List[Tuple[str, str]] = []

    try:
        with zipfile.ZipFile(xlsx_file) as zf:
            shared: List[str] = []
            if "xl/sharedStrings.xml" in zf.namelist():
                sst = ET.fromstring(zf.read("xl/sharedStrings.xml"))
                for si in sst.findall("a:si", ns):
                    txt = "".join(node.text or "" for node in si.findall(".//a:t", ns)).strip()
                    shared.append(txt)

            wb = ET.fromstring(zf.read("xl/workbook.xml"))
            rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
            relmap = {r.attrib.get("Id"): r.attrib.get("Target", "") for r in rels.findall("p:Relationship", ns)}

            sheet_target = ""
            for sheet in wb.findall("a:sheets/a:sheet", ns):
                if (sheet.attrib.get("name") or "").strip().lower() == "oldperm-newperm":
                    rid = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
                    sheet_target = relmap.get(rid, "")
                    break

            if not sheet_target:
                return []

            sheet_path = "xl/" + sheet_target.replace("\\", "/")
            ws = ET.fromstring(zf.read(sheet_path))

            for row in ws.findall(".//a:sheetData/a:row", ns):
                row_idx = int(row.attrib.get("r", "0"))
                if row_idx < 2:
                    continue

                old_val = ""
                new_val = ""

                for cell in row.findall("a:c", ns):
                    ref = cell.attrib.get("r", "")
                    col = re.match(r"[A-Z]+", ref)
                    if not col:
                        continue
                    col_name = col.group(0)
                    v = cell.find("a:v", ns)
                    if v is None:
                        continue
                    raw = v.text or ""
                    ctype = cell.attrib.get("t")
                    val = shared[int(raw)] if ctype == "s" and raw.isdigit() and int(raw) < len(shared) else raw
                    val = val.strip().replace("\xa0", "")

                    if col_name == "A":
                        old_val = val
                    elif col_name == "B":
                        new_val = val

                if not new_val:
                    continue
                pairs.append((old_val, new_val))
    except Exception:
        return []

    return pairs

def refresh_permission_maps() -> None:
    """Load permission compatibility maps from mapping workbook."""
    global PERMISSION_PAIRS, PERMISSION_OLD_TO_NEW, PERMISSION_NEW_TO_OLD, PERMISSION_NEW_ONLY, PERMISSION_COMPAT

    pairs = load_permission_pairs_from_xlsx(TASK_DIR / "Persona-Permission-Mapping.xlsx")
    PERMISSION_PAIRS = pairs
    PERMISSION_OLD_TO_NEW = {}
    PERMISSION_NEW_TO_OLD = {}
    PERMISSION_NEW_ONLY = set()
    PERMISSION_COMPAT = {}

    for old_name, new_name in PERMISSION_PAIRS:
        old_clean = (old_name or "").strip()
        new_clean = (new_name or "").strip()
        if not new_clean:
            continue

        if old_clean and old_clean.upper() != "NEW":
            PERMISSION_OLD_TO_NEW[old_clean] = new_clean
            PERMISSION_NEW_TO_OLD[new_clean] = old_clean
            PERMISSION_COMPAT.setdefault(old_clean, []).append(new_clean)
            PERMISSION_COMPAT.setdefault(new_clean, []).append(old_clean)
        else:
            PERMISSION_NEW_ONLY.add(new_clean)
            PERMISSION_COMPAT.setdefault(new_clean, [])

def load_persona_names() -> List[str]:
    """Load editable persona names list."""
    if not PERSONA_NAMES_JSON.exists():
        PERSONA_NAMES_JSON.write_text(json.dumps(DEFAULT_PERSONAS, indent=2, ensure_ascii=False), encoding="utf-8")
        return list(DEFAULT_PERSONAS)

    try:
        data = json.loads(PERSONA_NAMES_JSON.read_text(encoding="utf-8"))
        if isinstance(data, list):
            cleaned = []
            seen = set()
            for x in data:
                name = str(x).strip()
                if name and name not in seen:
                    seen.add(name)
                    cleaned.append(name)
            if cleaned:
                return cleaned
    except Exception:
        pass

    return list(DEFAULT_PERSONAS)

def save_persona_names(names: List[str]) -> None:
    """Persist editable persona names list."""
    cleaned = []
    seen = set()
    for n in names:
        nn = str(n).strip()
        if nn and nn not in seen:
            seen.add(nn)
            cleaned.append(nn)
    PERSONA_NAMES_JSON.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False), encoding="utf-8")

def load_personas() -> Dict[str, List[str]]:
    """Load persona configuration from JSON; align with editable persona names."""
    persona_names = load_persona_names()

    if not PERSONAS_JSON.exists():
        defaults = {name: [] for name in persona_names}
        PERSONAS_JSON.write_text(json.dumps(defaults, indent=2, ensure_ascii=False), encoding="utf-8")
        return defaults

    try:
        data = json.loads(PERSONAS_JSON.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            normalized: Dict[str, List[str]] = {}
            for name in persona_names:
                val = data.get(name, [])
                if isinstance(val, list):
                    normalized[name] = [str(x) for x in val]
                else:
                    normalized[name] = []
            return normalized
    except Exception:
        pass

    return {name: [] for name in persona_names}

def save_personas(personas: Dict[str, List[str]]) -> None:
    """Persist personas to JSON."""
    PERSONAS_JSON.write_text(json.dumps(personas, indent=2, ensure_ascii=False), encoding="utf-8")



def load_persona_descriptions_from_xlsx(xlsx_file: Path) -> Dict[str, Dict[str, str]]:
    """Read persona descriptions from sheet1: A=Persona, C=Beschreibung (ignore B)."""
    if not xlsx_file.exists():
        return {}

    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    result: Dict[str, Dict[str, str]] = {}

    with zipfile.ZipFile(xlsx_file) as zf:
        shared: List[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            sst = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in sst.findall("a:si", ns):
                txt = "".join(node.text or "" for node in si.findall(".//a:t", ns)).strip()
                shared.append(txt)

        ws = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
        for row in ws.findall(".//a:sheetData/a:row", ns):
            persona = ""
            desc = ""
            for cell in row.findall("a:c", ns):
                ref = cell.attrib.get("r", "")
                if not (ref.startswith("A") or ref.startswith("C")):
                    continue
                ctype = cell.attrib.get("t")
                val_node = cell.find("a:v", ns)
                if val_node is None:
                    continue
                raw_val = val_node.text or ""
                if ctype == "s" and raw_val.isdigit():
                    idx = int(raw_val)
                    value = shared[idx] if idx < len(shared) else ""
                else:
                    value = raw_val
                value = sanitize_plain_text(value)
                if ref.startswith("A"):
                    persona = value
                elif ref.startswith("C"):
                    desc = value

            if persona:
                result[persona] = {lang: desc for lang in SUPPORTED_LANGS}

    return result

def _normalize_desc_value(value) -> Dict[str, str]:
    if isinstance(value, dict):
        base = {lang: sanitize_plain_text(value.get(lang, "")) for lang in SUPPORTED_LANGS}
        # fallback from de into empty languages
        seed = base.get("de", "")
        for lang in SUPPORTED_LANGS:
            if not base[lang]:
                base[lang] = seed
        return base
    txt = sanitize_plain_text(value)
    return {lang: txt for lang in SUPPORTED_LANGS}

def load_persona_descriptions() -> Dict[str, Dict[str, str]]:
    if PERSONA_DESCRIPTIONS_JSON.exists():
        try:
            data = json.loads(PERSONA_DESCRIPTIONS_JSON.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                out: Dict[str, Dict[str, str]] = {}
                for k, v in data.items():
                    persona = sanitize_plain_text(k)
                    if persona:
                        out[persona] = _normalize_desc_value(v)
                return out
        except Exception:
            pass

    from_xlsx = load_persona_descriptions_from_xlsx(PERSONA_SOURCE_XLSX)
    if from_xlsx:
        save_persona_descriptions(from_xlsx)
    return from_xlsx

def save_persona_descriptions(data: Dict[str, Dict[str, str]]) -> None:
    clean: Dict[str, Dict[str, str]] = {}
    for k, v in (data or {}).items():
        persona = sanitize_plain_text(k)
        if not persona:
            continue
        clean[persona] = _normalize_desc_value(v)
    PERSONA_DESCRIPTIONS_JSON.write_text(json.dumps(clean, indent=2, ensure_ascii=False), encoding="utf-8")



def load_role_descriptions() -> Dict[str, Dict[str, str]]:
    if ROLE_DESCRIPTIONS_JSON.exists():
        try:
            data = json.loads(ROLE_DESCRIPTIONS_JSON.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                out: Dict[str, Dict[str, str]] = {}
                for k, v in data.items():
                    role = sanitize_plain_text(k)
                    if role:
                        out[role] = _normalize_desc_value(v)
                return out
        except Exception:
            pass
    return {}

def save_role_descriptions(data: Dict[str, Dict[str, str]]) -> None:
    clean: Dict[str, Dict[str, str]] = {}
    for k, v in (data or {}).items():
        role = sanitize_plain_text(k)
        if not role:
            continue
        clean[role] = _normalize_desc_value(v)
    ROLE_DESCRIPTIONS_JSON.write_text(json.dumps(clean, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_mapping_sources_from_txt(content: str) -> List[str]:
    """Extract unique SOURCE values from mapping lines SOURCE=TARGET."""
    out: List[str] = []
    seen = set()
    for raw in (content or "").splitlines():
        line = sanitize_plain_text(raw)
        if not line or "=" not in line:
            continue
        src = sanitize_plain_text(line.split("=", 1)[0])
        if len(src) > 256:
            continue
        if src.lower().startswith("javascript:"):
            continue
        if src and src not in seen:
            seen.add(src)
            out.append(src)
    return out

def parse_mapping_dict_from_txt(content: str) -> Dict[str, List[str]]:
    """Parse SOURCE=TARGET lines from uploaded txt content into a mapping dict (sanitized)."""
    mapping: Dict[str, List[str]] = {}
    for raw in (content or "").splitlines():
        line = sanitize_plain_text(raw)
        if not line or "=" not in line:
            continue
        src_raw, tgt_raw = line.split("=", 1)
        src = sanitize_plain_text(src_raw)
        tgt = sanitize_plain_text(tgt_raw)
        if not src or not tgt:
            continue
        if len(src) > 256 or len(tgt) > 256:
            continue
        if src.lower().startswith("javascript:") or tgt.lower().startswith("javascript:"):
            continue
        mapping.setdefault(src, [])
        if tgt not in mapping[src]:
            mapping[src].append(tgt)
    return mapping

def detect_delimiter(sample: str) -> str:
    """Detect delimiter; fallback to semicolon."""
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except Exception:
        return ";"

def parse_csv(content: str) -> Tuple[List[str], List[dict], str]:
    """Parse CSV text and return sanitized headers + rows + delimiter used."""
    sample = content[:2000]
    delimiter = detect_delimiter(sample)
    reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)

    raw_headers = reader.fieldnames or []
    headers = [sanitize_plain_text(h) for h in raw_headers if sanitize_plain_text(h)]

    rows: List[dict] = []
    for raw_row in reader:
        safe_row: Dict[str, str] = {}
        for k, v in (raw_row or {}).items():
            sk = sanitize_plain_text(k)
            if not sk:
                continue
            safe_row[sk] = sanitize_plain_text(v)
        rows.append(safe_row)

    return headers, rows, delimiter

def find_role_column(headers: List[str]) -> str:
    """Find best role/source column by common names."""
    candidates = ["role", "rolle", "ldap_role", "orbis_role", "group", "gruppe"]
    normalized = {h.lower().strip(): h for h in headers}
    for c in candidates:
        if c in normalized:
            return normalized[c]
    return headers[0] if headers else ""

def is_code_column(column_name: str) -> bool:
    """Treat code-like columns as ignorable according to requirement."""
    return bool(re.search(r"code|script|snippet", column_name, re.IGNORECASE))

def parse_dirty_keycloak_lines(content: str) -> Dict[str, List[str]]:
    """Parse lines like RoleMapper_<SOURCE>_to_<TARGET> into mapping dict.

    Tolerates leading/trailing spaces and ignores tab-separated extra columns.
    """
    mapping: Dict[str, List[str]] = {}
    for raw in str(content or "").splitlines():
        line = str(raw or "").strip()
        if not line:
            continue

        first_col = line.split("	", 1)[0].strip()
        m = re.match(r"^RoleMapper_(.+?)_to_(.+)$", first_col)
        if not m:
            continue

        source = sanitize_plain_text(m.group(1).strip().strip('"').strip("'"))
        target = sanitize_plain_text(m.group(2).strip().strip('"').strip("'"))
        if not source or not target:
            continue

        mapping.setdefault(source, []).append(target)
    return mapping


def parse_module_option_mapping_block(content: str) -> Dict[str, List[str]]:
    """Parse JBoss module-option mapping block lines: ^SOURCE$=TARGET.

    Accepts full XML snippet; extracts content between <module-option name="mapping"> ... </module-option>.
    Skips obvious regex-pattern sources and keeps concrete source-role mappings.
    """
    text = str(content or "")
    m = re.search(r"<module-option\\s+name=['\"]mapping['\"]\\s*>(.*?)</module-option>", text, flags=re.IGNORECASE | re.DOTALL)
    block = m.group(1) if m else text

    mapping: Dict[str, List[str]] = {}
    for raw in block.splitlines():
        line = str(raw or "").strip()
        if not line:
            continue
        if line.startswith("<!--") or line.startswith("--"):
            continue
        if "$=" not in line:
            continue

        left, right = line.split("$=", 1)
        source = sanitize_plain_text(left.strip())
        target = sanitize_plain_text(right.strip())

        if source.startswith("^"):
            source = source[1:]
        if source.endswith("$"):
            source = source[:-1]
        source = sanitize_plain_text(source)

        # Ignore regex-heavy sources (non-concrete role patterns)
        if re.search(r'[\[\]\(\)\*\+\?\|\\]', source):
            continue
        if not source or not target:
            continue
        mapping.setdefault(source, []).append(target)

    return mapping


def unique_source_roles(rows: List[dict], role_column: str) -> List[str]:
    """Extract unique source roles from csv rows."""
    seen = set()
    out = []
    for row in rows:
        value = (row.get(role_column) or "").strip()
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out

def get_writable_output_dir() -> Path:
    """Return a writable output directory with fallback when share is read-only."""
    candidates = [OUTPUT_DIR, Path("/tmp/rolemapper-output")]
    for d in candidates:
        try:
            d.mkdir(parents=True, exist_ok=True)
            test_file = d / ".write_test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
            return d
        except Exception:
            continue
    # Last resort: current working directory
    fallback = Path("./output")
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback

def save_output(lines: List[str]) -> str:
    """Save generated lines to txt file and return filename."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_name = f"mapping-{timestamp}.txt"
    out_dir = get_writable_output_dir()
    out_path = out_dir / out_name
    out_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return out_name

def build_mapping_code() -> str:
    seed = f"{datetime.now().isoformat()}-{secrets.token_hex(4)}"
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10].upper()

def _detect_request_user() -> str:
    """Try to detect real user from common reverse-proxy / SSO headers."""
    candidates = [
        request.headers.get("X-Forwarded-User"),
        request.headers.get("X-Auth-Request-User"),
        request.headers.get("Remote-User"),
        request.environ.get("REMOTE_USER"),
    ]
    for c in candidates:
        v = sanitize_plain_text(c or "")
        if v:
            return v[:80]
    return ""


def _editor_identity() -> Tuple[str, str]:
    eid = str(session.get("editor_id", "") or "").strip()
    if not eid:
        eid = secrets.token_hex(8)
        session["editor_id"] = eid

    detected_user = _detect_request_user()
    posted_name = sanitize_plain_text((request.form.get("editor_name_manual", "") if request.method == "POST" else "") or "")
    cookie_name = sanitize_plain_text(request.cookies.get("rolemapper_editor_name", "") or "")

    if detected_user:
        session["editor_name"] = detected_user
    elif posted_name:
        session["editor_name"] = posted_name[:80]
    elif cookie_name and not session.get("editor_name"):
        session["editor_name"] = cookie_name[:80]

    editor_name = sanitize_plain_text(session.get("editor_name", "") or "")

    role = "admin" if session.get("auth_admin") else ("localizer" if _is_i18n_authenticated() else "user")
    if editor_name:
        label = f"{editor_name} ({role})"
    else:
        ip = sanitize_plain_text((request.headers.get("X-Forwarded-For", "").split(",")[0] or request.remote_addr or "")[:64])
        label = f"{role}-{eid[:6]}" + (f" @{ip}" if ip else "")
    return eid, label


def _lock_path_for_code(code: str) -> Path:
    safe = re.sub(r"[^A-Z0-9]", "", str(code or "").upper())[:20]
    return MAPPING_LOCK_DIR / f"lock-{safe}.json"


def _read_mapping_lock(code: str) -> Dict[str, str]:
    path = _lock_path_for_code(code)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        ts_raw = str(data.get("updated_at", "") or "")
        if ts_raw:
            try:
                ts = datetime.fromisoformat(ts_raw)
                if (datetime.now() - ts).total_seconds() > MAPPING_LOCK_TTL_SECONDS:
                    try:
                        path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    return {}
            except Exception:
                pass
        return data
    except Exception:
        return {}


def _acquire_mapping_lock(code: str, editor_id: str, editor_label: str) -> Tuple[bool, Dict[str, str]]:
    safe = re.sub(r"[^A-Z0-9]", "", str(code or "").upper())[:20]
    if not safe:
        return False, {}
    current = _read_mapping_lock(safe)
    holder_id = str(current.get("editor_id", "") or "")
    if current and holder_id and holder_id != editor_id:
        return False, current
    payload = {
        "code": safe,
        "editor_id": editor_id,
        "editor_label": editor_label,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    _lock_path_for_code(safe).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return True, payload


def _lock_release_notice_text(lang: str) -> str:
    l = (lang or "de").strip().lower()
    return {
        "de": "Hinweis: Der Bearbeitungs-Lock für dieses Mapping wurde nach dem Speichern/Aktualisieren aufgehoben.",
        "en": "Note: The edit lock for this mapping was released after save/update.",
        "it": "Nota: il lock di modifica per questo mapping è stato rilasciato dopo salvataggio/aggiornamento.",
        "fr": "Remarque : le verrou d'édition pour ce mapping a été levé après l'enregistrement/la mise à jour.",
        "pt": "Observação: o bloqueio de edição deste mapping foi liberado após salvar/atualizar.",
        "es": "Nota: el bloqueo de edición de este mapping se liberó tras guardar/actualizar.",
    }.get(l, "Hinweis: Der Bearbeitungs-Lock für dieses Mapping wurde nach dem Speichern/Aktualisieren aufgehoben.")


def _release_mapping_lock(code: str, editor_id: str) -> None:
    safe = re.sub(r"[^A-Z0-9]", "", str(code or "").upper())[:20]
    if not safe:
        return
    path = _lock_path_for_code(safe)
    cur = _read_mapping_lock(safe)
    if not cur:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
        return
    if str(cur.get("editor_id", "") or "") == str(editor_id or ""):
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass


# Persist mapping snapshot and metadata to mapping_store/.
# This is used by "save mapping", "update mapping", and server list/download features.
def save_mapping_plus(
    code: str,
    lines: List[str],
    country: str = "",
    postal_code: str = "",
    city: str = "",
    customer_no: str = "",
    side: str = "",
    customer: str = "",
    client_ts: str = "",
    source_roles: List[str] | None = None,
) -> None:
    safe_code = re.sub(r"[^A-Z0-9]", "", (code or "").upper())[:20]
    if not safe_code:
        return
    _init_mapping_db()
    existing: Dict[str, str] = {}
    with _db_connect() as conn:
        row = conn.execute(
            "SELECT * FROM mapping_records WHERE code = %s AND deleted = 0",
            (safe_code,),
        ).fetchone()
        if row:
            existing = {
                "created_at": str(row["created_at"] or ""),
                "created_at_client": str(row["created_at_client"] or ""),
            }

    now_server = datetime.now().isoformat()
    client_val = sanitize_plain_text(client_ts or "")
    created_at = str(existing.get("created_at") or now_server)
    created_at_client = sanitize_plain_text(existing.get("created_at_client") or "")
    if not created_at_client:
        created_at_client = client_val
    clean_source_roles = [sanitize_plain_text(r) for r in (source_roles or []) if sanitize_plain_text(r)]
    clean_lines = [str(x) for x in (lines or [])]
    meta_obj = {
        "code": safe_code,
        "country": sanitize_plain_text(country or ""),
        "postal_code": sanitize_plain_text(postal_code or ""),
        "city": sanitize_plain_text(city or ""),
        "customer_no": sanitize_plain_text(customer_no or ""),
        "site": sanitize_plain_text(side or ""),
        "customer": sanitize_plain_text(customer or ""),
        "created_at": created_at,
        "created_at_client": created_at_client,
        "updated_at": now_server,
        "updated_at_client": client_val,
        "line_count": len(clean_lines),
        "source_roles": clean_source_roles,
    }

    with _db_connect() as conn:
        conn.execute(
            """
            INSERT INTO mapping_records (
              code, country, postal_code, city, customer_no, site, customer,
              created_at, created_at_client, updated_at, updated_at_client,
              line_count, source_roles_json, mapping_lines_text, deleted
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
            ON CONFLICT(code) DO UPDATE SET
              country=excluded.country,
              postal_code=excluded.postal_code,
              city=excluded.city,
              customer_no=excluded.customer_no,
              site=excluded.site,
              customer=excluded.customer,
              updated_at=excluded.updated_at,
              updated_at_client=excluded.updated_at_client,
              line_count=excluded.line_count,
              source_roles_json=excluded.source_roles_json,
              mapping_lines_text=excluded.mapping_lines_text,
              deleted=0
            """,
            (
                safe_code,
                meta_obj["country"],
                meta_obj["postal_code"],
                meta_obj["city"],
                meta_obj["customer_no"],
                meta_obj["site"],
                meta_obj["customer"],
                meta_obj["created_at"],
                meta_obj["created_at_client"],
                meta_obj["updated_at"],
                meta_obj["updated_at_client"],
                meta_obj["line_count"],
                json.dumps(clean_source_roles, ensure_ascii=False),
                "\n".join(clean_lines),
            ),
        )
        _record_history(conn, safe_code, "upsert", meta_obj, clean_lines)

def load_mapping_plus_bundle(code: str) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    safe_code = re.sub(r"[^A-Z0-9]", "", (code or "").upper())[:20]
    if not safe_code:
        return {}, {"country": "", "postal_code": "", "city": "", "customer_no": "", "side": "", "customer": ""}
    _init_mapping_db()
    mapping: Dict[str, List[str]] = {}
    meta_out = {"country": "", "postal_code": "", "city": "", "customer_no": "", "side": "", "customer": ""}
    meta: Dict[str, object] = {}
    with _db_connect() as conn:
        row = conn.execute(
            "SELECT * FROM mapping_records WHERE code = %s AND deleted = 0",
            (safe_code,),
        ).fetchone()
    if not row:
        return {}, meta_out

    raw_lines = str(row["mapping_lines_text"] or "")
    mapping = load_mapping_from_content(raw_lines)

    meta_out["country"] = sanitize_plain_text(row["country"] or "")
    meta_out["postal_code"] = sanitize_plain_text(row["postal_code"] or "")
    meta_out["city"] = sanitize_plain_text(row["city"] or "")
    meta_out["customer_no"] = sanitize_plain_text(row["customer_no"] or "")
    meta_out["side"] = sanitize_plain_text(row["site"] or "")
    meta_out["customer"] = sanitize_plain_text(row["customer"] or "")
    meta = {
        "source_roles": [],
    }
    try:
        meta["source_roles"] = json.loads(str(row["source_roles_json"] or "[]"))
    except Exception:
        meta["source_roles"] = []

    # Keep source roles in memory even when they have no target mapping lines.
    # This preserves external auth roles in DB/UI while still exporting only mapped lines.
    if isinstance(meta, dict):
        raw_roles = meta.get("source_roles", [])
        if isinstance(raw_roles, list):
            clean_roles = [sanitize_plain_text(r) for r in raw_roles if sanitize_plain_text(r)]
            for role in clean_roles:
                mapping.setdefault(role, [])

    return mapping, meta_out

def generate_from_persona_assignments(
    source_roles: List[str],
    selected_personas: Dict[str, List[str]],
    personas: Dict[str, List[str]],
    permission_mode: str = "auto",
    selected_roles: Dict[str, List[str]] | None = None,
) -> List[str]:
    """Create SOURCE=TARGET lines with persona names + expanded role permissions + direct role assignments."""
    lines: List[str] = []
    selected_roles = selected_roles or {}
    for src in source_roles:
        persona_names = [p for p in selected_personas.get(src, []) if p]
        direct_roles = [r for r in selected_roles.get(src, []) if r]

        # 1) Add persona mappings directly.
        for pname in sorted(set(persona_names)):
            lines.append(f"{src}={pname}")

        # 2) Add role mappings from persona definitions.
        expanded_roles: List[str] = []
        for pname in persona_names:
            expanded_roles.extend(personas.get(pname, []))

        compatible_roles = expand_compat_permissions(sorted(set(expanded_roles)), permission_mode)
        merged_roles = sorted(set(compatible_roles) | set(direct_roles))
        for role in merged_roles:
            lines.append(f"{src}={role}")
    return lines

# Initialize compatibility map from Persona-Permission-Mapping.xlsx.
refresh_permission_maps()

# Initialize SQLite storage for server mappings.
_init_mapping_db()

# Central route guard:
# - public pages stay accessible
# - admin pages require admin session
# - i18n pages require admin OR language-specific localizer session
@app.before_request
def enforce_auth_guards():
    endpoint = request.endpoint or ""
    if endpoint in {"static", "index", "guide_page", "auth_login", "login_page", "logout_page", "download", "download_compose_example", "download_project_zip", "download_deploy_bundle"}:
        return None

    auth = load_auth_settings()
    admin_required = {"config_auth", "config_persona_names", "download_config_backup"}
    i18n_or_admin_required = {"config_roles", "config_i18n"}

    if endpoint in admin_required:
        if not auth.get("admin_hash"):
            # Bootstrap mode: allow admin config page only until first admin password set.
            if endpoint == "config_auth":
                return None
        if not _is_admin_authenticated():
            _set_login_challenge("admin", request.full_path.rstrip("?"))
            return redirect(url_for("index"))

    if endpoint in i18n_or_admin_required:
        cookie_lang = (request.cookies.get("rolemapper_lang", "") or "").strip().lower()
        selected_lang = (request.values.get("lang") or request.values.get("active_lang") or cookie_lang or "de").strip().lower()
        if selected_lang not in SUPPORTED_LANGS:
            selected_lang = "de"

        if request.method == "POST":
            post_lang = (request.form.get("active_lang", selected_lang) or selected_lang).strip().lower()
            if post_lang in SUPPORTED_LANGS:
                selected_lang = post_lang

        if not (_is_admin_authenticated() or _is_i18n_authenticated(selected_lang)):
            _set_login_challenge("i18n", request.full_path.rstrip("?"), selected_lang)
            return redirect(url_for("index"))

    if endpoint == "config_i18n":
        cookie_lang = (request.cookies.get("rolemapper_lang", "") or "").strip().lower()
        selected_lang = (request.values.get("lang") or cookie_lang or "de").strip().lower()
        if selected_lang not in SUPPORTED_LANGS:
            selected_lang = "de"

        if request.method == "POST":
            post_lang = (request.form.get("lang", selected_lang) or selected_lang).strip().lower()
            if post_lang in SUPPORTED_LANGS:
                selected_lang = post_lang
            if not (_is_admin_authenticated() or _is_i18n_authenticated(selected_lang)):
                _set_login_challenge("i18n", request.full_path.rstrip("?"), selected_lang)
                return redirect(url_for("index"))
        else:
            if not (_is_admin_authenticated() or _is_i18n_authenticated()):
                _set_login_challenge("i18n", request.full_path.rstrip("?"), selected_lang)
                return redirect(url_for("index"))

    return None

@app.route("/login", methods=["GET"])
def login_page():
    # Fallback login page (works even if client-side modal JS fails).
    lang = (request.args.get("lang") or request.cookies.get("rolemapper_lang") or "de").strip().lower()
    if lang not in SUPPORTED_LANGS:
        lang = "de"
    return render_template("login.html", selected_lang=lang, langs=SUPPORTED_LANGS)

@app.route("/auth-login", methods=["POST"])
def auth_login():
    required_scope = (session.get("login_scope", "") or "").strip().lower()
    posted_scope = (request.form.get("scope", "admin") or "admin").strip().lower()
    scope = required_scope if required_scope in {"admin", "i18n"} else posted_scope
    if scope not in {"admin", "i18n"}:
        scope = "admin"

    next_path = _safe_next_path(session.get("login_next", "/"))

    required_lang = (session.get("login_lang", "") or "").strip().lower()
    posted_lang = (request.form.get("lang", "") or "").strip().lower()
    login_lang = required_lang if (scope == "i18n" and required_lang in SUPPORTED_LANGS) else posted_lang
    if login_lang not in SUPPORTED_LANGS:
        login_lang = "de"

    password = (request.form.get("password", "") or "").strip()
    auth = load_auth_settings()

    if scope == "admin":
        if auth.get("admin_hash") and check_password_hash(auth["admin_hash"], password):
            session["auth_admin"] = True
            session.pop("login_scope", None)
            session.pop("login_next", None)
            session.pop("login_lang", None)
            return redirect(next_path)
        flash("Ungültiges Admin-Passwort.")
        return redirect(url_for("index"))

    raw_i18n_hashes = auth.get("i18n_hashes", {})
    i18n_hashes = raw_i18n_hashes if isinstance(raw_i18n_hashes, dict) else {}
    lang_hash = str(i18n_hashes.get(login_lang, "") or "")
    i18n_ok = bool(lang_hash) and check_password_hash(lang_hash, password)
    admin_ok = auth.get("admin_hash") and check_password_hash(str(auth.get("admin_hash", "")), password)
    if i18n_ok or admin_ok:
        if admin_ok:
            session["auth_admin"] = True
        if i18n_ok:
            langs = session.get("auth_i18n_langs", [])
            if not isinstance(langs, list):
                langs = []
            if login_lang not in langs:
                langs.append(login_lang)
            session["auth_i18n_langs"] = [l for l in langs if l in SUPPORTED_LANGS]
        session.pop("login_scope", None)
        session.pop("login_next", None)
        session.pop("login_lang", None)
        return redirect(next_path)

    flash(f"Ungültiges Passwort für Sprache: {login_lang.upper()}")
    return redirect(url_for("index"))

@app.route("/logout")
def logout_page():
    editor_id = str(session.get("editor_id", "") or "")
    active_code = re.sub(r"[^A-Z0-9]", "", str(session.get("editing_mapping_code", "") or "").upper())[:20]
    if editor_id and active_code:
        _release_mapping_lock(active_code, editor_id)
    session.pop("editing_mapping_code", None)
    session.pop("auth_admin", None)
    session.pop("auth_i18n", None)
    session.pop("auth_i18n_langs", None)
    session.pop("login_scope", None)
    session.pop("login_next", None)
    session.pop("login_lang", None)
    return redirect(url_for("index"))

@app.route("/config-auth", methods=["GET", "POST"])
def config_auth():
    auth = load_auth_settings()
    raw_hashes = auth.get("i18n_hashes", {})
    i18n_hashes = raw_hashes if isinstance(raw_hashes, dict) else {lang: "" for lang in SUPPORTED_LANGS}

    sample_roles_text = load_sample_roles_text()
    app_settings = load_app_settings()

    if request.method == "POST":
        ui_lang = (request.form.get("ui_lang", "") or request.cookies.get("rolemapper_lang", "de") or "de").strip().lower()
        if ui_lang not in SUPPORTED_LANGS:
            ui_lang = "de"

        admin_pw = (request.form.get("admin_password", "") or "").strip()

        if admin_pw:
            auth["admin_hash"] = generate_password_hash(admin_pw, method="pbkdf2:sha256")

        for lang in SUPPORTED_LANGS:
            val = (request.form.get(f"i18n_password_{lang}", "") or "").strip()
            if val:
                i18n_hashes[lang] = generate_password_hash(val, method="pbkdf2:sha256")

        save_sample_roles_text(request.form.get("sample_roles_text", "") or "")

        show_test_banner = (request.form.get("show_test_banner", "") == "1")
        save_app_settings({
            "permission_mode": app_settings.get("permission_mode", "auto"),
            "show_test_banner": show_test_banner,
        })

        auth["i18n_hashes"] = {lang: str(i18n_hashes.get(lang, "") or "") for lang in SUPPORTED_LANGS}
        save_auth_settings(auth)
        flash("Passwörter gespeichert.")
        return redirect(url_for("config_auth", lang=ui_lang))

    status_by_lang = {lang: bool(i18n_hashes.get(lang, "")) for lang in SUPPORTED_LANGS}
    return render_template(
        "config_auth.html",
        has_admin=bool(auth.get("admin_hash")),
        status_by_lang=status_by_lang,
        langs=SUPPORTED_LANGS,
        sample_roles_text=sample_roles_text,
        show_test_banner=bool(app_settings.get("show_test_banner", True)),
    )


@app.route("/download/config-backup")
def download_config_backup():
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"rolemapper-config-backup-{timestamp}.zip"

    backup_files = [
        PERSONAS_JSON,
        PERSONA_NAMES_JSON,
        PERSONA_DESCRIPTIONS_JSON,
        ROLES_JSON,
        ROLE_DESCRIPTIONS_JSON,
        I18N_OVERRIDES_JSON,
        APP_SETTINGS_JSON,
        SAMPLE_ROLES_JSON,
    ]

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        manifest = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "version": APP_VERSION,
            "files": [],
        }

        for file_path in backup_files:
            if not file_path.exists():
                continue
            arcname = f"config/{file_path.name}"
            zf.write(file_path, arcname=arcname)
            manifest["files"].append(arcname)

        # Include DB-backed server mappings.
        if MAPPING_DB_PATH.exists():
            arcname = f"mapping_store/{MAPPING_DB_PATH.name}"
            zf.write(MAPPING_DB_PATH, arcname=arcname)
            manifest["files"].append(arcname)

        zf.writestr("BACKUP_INFO.json", json.dumps(manifest, indent=2, ensure_ascii=False))

    mem.seek(0)
    return send_file(mem, as_attachment=True, download_name=filename, mimetype="application/zip")

@app.route("/", methods=["GET", "POST"])
def index():
    mapping = load_mapping(MAPPING_TXT)
    keycloak_roles = load_available_roles()
    personas = load_personas()
    settings = load_app_settings()

    preview = []
    headers = []
    role_column = ""
    generated_file = None
    source_roles: List[str] = []
    prefill_personas: Dict[str, List[str]] = {}
    prefill_roles: Dict[str, List[str]] = {}
    show_role_pool = True
    mapping_plus_country = ""
    mapping_plus_postal_code = ""
    mapping_plus_city = ""
    mapping_plus_customer_no = ""
    mapping_plus_side = ""
    mapping_plus_customer = ""
    mapping_plus_code = ""
    mapping_loaded_from_server = False
    unmapped_warning_roles: List[str] = []
    added_source_roles: List[str] = []
    unmapped_warning_header = ""
    unmapped_warning_filename = ""
    permission_mode = settings.get("permission_mode", "auto")
    sample_roles_text = load_sample_roles_text().strip()
    if sample_roles_text:
        default_test_roles = "\n".join(sanitize_lines([x.strip() for x in sample_roles_text.splitlines()]))
    else:
        sample_roles = sorted([
            k for k in mapping.keys()
            if (k.upper().startswith("PROS SUB") or k.upper().startswith("PRO SUB")) and "MHB" not in k.upper()
        ])
        if not sample_roles:
            sample_roles = sorted([r for r in keycloak_roles if "MHB" not in r.upper()])
        default_test_roles = "\n".join(sample_roles)

    login_scope = (session.get("login_scope", "") or "")
    login_lang = (session.get("login_lang", "") or "")
    editor_id, editor_label = _editor_identity()
    active_edit_code = re.sub(r"[^A-Z0-9]", "", str(session.get("editing_mapping_code", "") or "").upper())[:20]

    load_code = sanitize_plain_text(request.args.get("api_code", "") or request.args.get("load_mapping_code", ""))
    if request.method == "GET" and not load_code and active_edit_code:
        _release_mapping_lock(active_edit_code, editor_id)
        session.pop("editing_mapping_code", None)

    if request.method == "GET" and load_code:
        safe_code = re.sub(r"[^A-Z0-9]", "", load_code.upper())[:20]
        ok_lock, lock_info = _acquire_mapping_lock(safe_code, editor_id, editor_label)
        if not ok_lock:
            holder = lock_info.get("editor_label", "anderer Benutzer")
            flash(f"Mapping {safe_code} ist aktuell gesperrt ({holder}).")
        else:
            session["editing_mapping_code"] = safe_code
            seed_mapping, loaded_meta = load_mapping_plus_bundle(safe_code)
            if seed_mapping or mapping_record_exists(safe_code):
                source_roles = sorted(seed_mapping.keys())
                prefill_personas = build_prefill_personas(source_roles, personas, seed_mapping)
                prefill_roles = build_prefill_roles(source_roles, list(personas.keys()), seed_mapping)
                show_role_pool = True
                mapping_loaded_from_server = True
                mapping_plus_code = safe_code
                mapping_plus_country = loaded_meta.get("country", "") or ""
                mapping_plus_postal_code = loaded_meta.get("postal_code", "") or ""
                mapping_plus_city = loaded_meta.get("city", "") or ""
                mapping_plus_customer_no = loaded_meta.get("customer_no", "") or ""
                mapping_plus_side = loaded_meta.get("side", "") or ""
                mapping_plus_customer = loaded_meta.get("customer", "") or ""
                flash(f"Mapping geladen für Code: {mapping_plus_code}")
            else:
                flash("Kein gespeichertes Mapping für diesen Code gefunden.")

    if request.method == "POST":
        def _parse_assignment_payload(payload: str) -> Dict[str, Dict[str, List[str]]]:
            result: Dict[str, Dict[str, List[str]]] = {}
            if not str(payload or "").strip():
                return result
            try:
                parsed = json.loads(payload)
            except Exception:
                return result
            if not isinstance(parsed, dict):
                return result
            for raw_src, raw_values in parsed.items():
                src = sanitize_plain_text(str(raw_src or ""))
                if not src:
                    continue
                personas_vals: List[str] = []
                roles_vals: List[str] = []
                if isinstance(raw_values, dict):
                    pvals = raw_values.get("personas", [])
                    rvals = raw_values.get("roles", [])
                    if isinstance(pvals, list):
                        personas_vals = [sanitize_plain_text(str(v)) for v in pvals if sanitize_plain_text(str(v))]
                    if isinstance(rvals, list):
                        roles_vals = [sanitize_plain_text(str(v)) for v in rvals if sanitize_plain_text(str(v))]
                elif isinstance(raw_values, list):
                    personas_vals = [sanitize_plain_text(str(v)) for v in raw_values if sanitize_plain_text(str(v))]
                result[src] = {
                    "personas": list(dict.fromkeys(personas_vals)),
                    "roles": list(dict.fromkeys(roles_vals)),
                }
            return result

        def _merge_source_context(
            existing_sources: List[str],
            existing_assignments: Dict[str, Dict[str, List[str]]],
            incoming_sources: List[str],
            incoming_personas: Dict[str, List[str]],
            incoming_roles: Dict[str, List[str]],
        ) -> Tuple[List[str], Dict[str, List[str]], Dict[str, List[str]], List[str]]:
            existing_clean = [sanitize_plain_text(x) for x in (existing_sources or []) if sanitize_plain_text(x)]
            incoming_clean = [sanitize_plain_text(x) for x in (incoming_sources or []) if sanitize_plain_text(x)]
            existing_set = set(existing_clean)
            ordered_sources = list(dict.fromkeys(existing_clean + incoming_clean))
            added = [src for src in incoming_clean if src not in existing_set]

            merged_personas: Dict[str, List[str]] = {}
            merged_roles: Dict[str, List[str]] = {}
            for src in ordered_sources:
                existing_for_src = existing_assignments.get(src, {}) if isinstance(existing_assignments, dict) else {}
                p_existing = existing_for_src.get("personas", []) if isinstance(existing_for_src, dict) else []
                r_existing = existing_for_src.get("roles", []) if isinstance(existing_for_src, dict) else []
                p_existing_clean = [sanitize_plain_text(x) for x in (p_existing or []) if sanitize_plain_text(x)]
                r_existing_clean = [sanitize_plain_text(x) for x in (r_existing or []) if sanitize_plain_text(x)]
                if p_existing_clean or r_existing_clean:
                    merged_personas[src] = list(dict.fromkeys(p_existing_clean))
                    merged_roles[src] = list(dict.fromkeys(r_existing_clean))
                    continue
                p_in = [sanitize_plain_text(x) for x in (incoming_personas.get(src, []) if incoming_personas else []) if sanitize_plain_text(x)]
                r_in = [sanitize_plain_text(x) for x in (incoming_roles.get(src, []) if incoming_roles else []) if sanitize_plain_text(x)]
                merged_personas[src] = list(dict.fromkeys(p_in))
                merged_roles[src] = list(dict.fromkeys(r_in))

            return ordered_sources, merged_personas, merged_roles, added

        action = request.form.get("action", "csv_upload")
        ui_lang = (request.form.get("ui_lang", "") or "").strip().lower()
        if ui_lang not in SUPPORTED_LANGS:
            ui_lang = (request.cookies.get("rolemapper_lang", "de") or "de").strip().lower()
        if ui_lang not in SUPPORTED_LANGS:
            ui_lang = "de"
        mapping_plus_country = sanitize_plain_text(request.form.get("mapping_plus_country", ""))
        mapping_plus_postal_code = sanitize_plain_text(request.form.get("mapping_plus_postal_code", ""))
        mapping_plus_city = sanitize_plain_text(request.form.get("mapping_plus_city", ""))
        mapping_plus_customer_no = sanitize_plain_text(request.form.get("mapping_plus_customer_no", ""))
        mapping_plus_side = sanitize_plain_text(request.form.get("mapping_plus_side", ""))
        mapping_plus_customer = sanitize_plain_text(request.form.get("mapping_plus_customer", ""))
        mapping_plus_code = sanitize_plain_text(request.form.get("mapping_plus_code", ""))
        mapping_client_ts = sanitize_plain_text(request.form.get("mapping_client_ts", ""))
        mapping_loaded_from_server = (request.form.get("mapping_loaded_from_server", "0") == "1")
        active_server_code = re.sub(r"[^A-Z0-9]", "", (mapping_plus_code or "").upper())[:20]
        existing_source_roles = [sanitize_plain_text(x) for x in request.form.getlist("existing_source_roles") if sanitize_plain_text(x)]
        existing_assignments_json = request.form.get("existing_assignments_json", "")
        existing_assignments = _parse_assignment_payload(existing_assignments_json)

        # Keep active API-loaded customer context even when entry forms do not post hidden fields.
        if not active_server_code and active_edit_code:
            fallback_mapping, fallback_meta = load_mapping_plus_bundle(active_edit_code)
            if fallback_mapping or mapping_record_exists(active_edit_code):
                active_server_code = active_edit_code
                mapping_plus_code = active_edit_code
                mapping_loaded_from_server = True
                mapping_plus_country = fallback_meta.get("country", "") or mapping_plus_country
                mapping_plus_postal_code = fallback_meta.get("postal_code", "") or mapping_plus_postal_code
                mapping_plus_city = fallback_meta.get("city", "") or mapping_plus_city
                mapping_plus_customer_no = fallback_meta.get("customer_no", "") or mapping_plus_customer_no
                mapping_plus_side = fallback_meta.get("side", "") or mapping_plus_side
                mapping_plus_customer = fallback_meta.get("customer", "") or mapping_plus_customer

        # Customer metadata can be edited by users on the main mapping page.

        if action == "mapping_plus_load":
            raw_text = request.form.get("mapping_raw_text", "")
            if str(raw_text or "").strip():
                if active_edit_code:
                    _release_mapping_lock(active_edit_code, editor_id)
                    session.pop("editing_mapping_code", None)
                    active_edit_code = ""
                seed_mapping = parse_module_option_mapping_block(raw_text)
                if not seed_mapping:
                    flash("Keine verwertbaren Mapping-Zeilen im Text gefunden.")
                else:
                    incoming_source_roles = sorted(seed_mapping.keys())
                    incoming_prefill_personas = build_prefill_personas(incoming_source_roles, personas, seed_mapping)
                    incoming_prefill_roles = build_prefill_roles(incoming_source_roles, list(personas.keys()), seed_mapping)
                    source_roles, prefill_personas, prefill_roles, added_source_roles = _merge_source_context(
                        existing_source_roles,
                        existing_assignments,
                        incoming_source_roles,
                        incoming_prefill_personas,
                        incoming_prefill_roles,
                    )
                    show_role_pool = True
                    mapping_loaded_from_server = False
                    mapping_plus_code = ""
                    flash(f"Text-Mapping geladen. {len(incoming_source_roles)} SOURCE-Rollen erkannt.")
            else:
                code_in = sanitize_plain_text(request.form.get("mapping_plus_code", ""))
                safe_code = re.sub(r"[^A-Z0-9]", "", code_in.upper())[:20]
                ok_lock, lock_info = _acquire_mapping_lock(safe_code, editor_id, editor_label)
                if not ok_lock:
                    holder = lock_info.get("editor_label", "anderer Benutzer")
                    flash(f"Mapping {safe_code} ist aktuell gesperrt ({holder}).")
                else:
                    if active_edit_code and active_edit_code != safe_code:
                        _release_mapping_lock(active_edit_code, editor_id)
                    session["editing_mapping_code"] = safe_code
                    seed_mapping, loaded_meta = load_mapping_plus_bundle(safe_code)
                    mapping_plus_country = loaded_meta.get("country", "") or mapping_plus_country
                    mapping_plus_postal_code = loaded_meta.get("postal_code", "") or mapping_plus_postal_code
                    mapping_plus_city = loaded_meta.get("city", "") or mapping_plus_city
                    mapping_plus_customer_no = loaded_meta.get("customer_no", "") or mapping_plus_customer_no
                    mapping_plus_side = loaded_meta.get("side", "") or mapping_plus_side
                    mapping_plus_customer = loaded_meta.get("customer", "") or mapping_plus_customer
                    if not seed_mapping and not mapping_record_exists(safe_code):
                        flash("Kein gespeichertes Mapping für diesen Code gefunden.")
                    else:
                        incoming_source_roles = sorted(seed_mapping.keys())
                        incoming_prefill_personas = build_prefill_personas(incoming_source_roles, personas, seed_mapping)
                        incoming_prefill_roles = build_prefill_roles(incoming_source_roles, list(personas.keys()), seed_mapping)
                        source_roles, prefill_personas, prefill_roles, added_source_roles = _merge_source_context(
                            existing_source_roles,
                            existing_assignments,
                            incoming_source_roles,
                            incoming_prefill_personas,
                            incoming_prefill_roles,
                        )
                        show_role_pool = True
                        mapping_loaded_from_server = True
                        mapping_plus_code = safe_code
                        flash(f"Mapping geladen für Code: {mapping_plus_code}")

        elif action == "mapping_upload":
            if active_edit_code:
                _release_mapping_lock(active_edit_code, editor_id)
                session.pop("editing_mapping_code", None)
                active_edit_code = ""
            file = request.files.get("mapping_file")
            if not file or not file.filename:
                flash(t(ui_lang, "mapping_required"))
                return render_template(
                    "index.html",
                    preview=preview,
                    headers=headers,
                    role_column=role_column,
                    generated_file=generated_file,
                    source_roles=source_roles,
                    keycloak_roles=keycloak_roles,
                    default_test_roles=default_test_roles,
                    personas=personas,
                )
            try:
                content = file.read().decode("utf-8-sig", errors="ignore")
                source_roles = parse_mapping_sources_from_txt(content)
                if not source_roles:
                    flash(t(ui_lang, "mapping_no_sources"))
                else:
                    uploaded_mapping = parse_mapping_dict_from_txt(content)
                    incoming_source_roles = source_roles
                    incoming_prefill_personas = build_prefill_personas(incoming_source_roles, personas, uploaded_mapping)
                    incoming_prefill_roles = build_prefill_roles(incoming_source_roles, list(personas.keys()), uploaded_mapping)
                    source_roles, prefill_personas, prefill_roles, added_source_roles = _merge_source_context(
                        existing_source_roles,
                        existing_assignments,
                        incoming_source_roles,
                        incoming_prefill_personas,
                        incoming_prefill_roles,
                    )
                    show_role_pool = True
                    mapping_loaded_from_server = bool(active_server_code)
                    flash(t(ui_lang, "mapping_loaded", n=len(incoming_source_roles)))
            except Exception as exc:
                flash(t(ui_lang, "processing_failed", err=exc))

        elif action == "csv_upload":
            if active_edit_code:
                _release_mapping_lock(active_edit_code, editor_id)
                session.pop("editing_mapping_code", None)
                active_edit_code = ""
            file = request.files.get("csv_file")
            if not file or not file.filename:
                flash(t(ui_lang, "upload_required"))
                return render_template(
                    "index.html",
                    preview=preview,
                    headers=headers,
                    role_column=role_column,
                    generated_file=generated_file,
                    source_roles=source_roles,
                    keycloak_roles=keycloak_roles,
                    default_test_roles=default_test_roles,
                    personas=personas,
                )

            try:
                content = file.read().decode("utf-8-sig", errors="ignore")
                headers, rows, _delimiter = parse_csv(content)

                if not headers:
                    flash(t(ui_lang, "csv_no_header"))
                    return render_template(
                        "index.html",
                        preview=preview,
                        headers=headers,
                        role_column=role_column,
                        generated_file=generated_file,
                        source_roles=source_roles,
                        keycloak_roles=keycloak_roles,
                        default_test_roles=default_test_roles,
                        personas=personas,
                    )

                filtered_headers = [h for h in headers if not is_code_column(h)]
                if not filtered_headers:
                    flash(t(ui_lang, "all_code_columns"))
                    return render_template(
                        "index.html",
                        preview=preview,
                        headers=headers,
                        role_column=role_column,
                        generated_file=generated_file,
                        source_roles=source_roles,
                        keycloak_roles=keycloak_roles,
                        default_test_roles=default_test_roles,
                        personas=personas,
                    )

                role_column = find_role_column(filtered_headers)
                if not role_column:
                    flash(t(ui_lang, "role_col_missing"))
                    return render_template(
                        "index.html",
                        preview=preview,
                        headers=headers,
                        role_column=role_column,
                        generated_file=generated_file,
                        source_roles=source_roles,
                        keycloak_roles=keycloak_roles,
                        default_test_roles=default_test_roles,
                        personas=personas,
                    )

                for row in rows[:10]:
                    preview.append({h: row.get(h, "") for h in filtered_headers})

                source_roles = unique_source_roles(rows, role_column)
                seed_mapping = load_seed_mapping_for_prefill(TASK_DIR)
                incoming_source_roles = source_roles
                incoming_prefill_personas = build_prefill_personas(incoming_source_roles, personas, seed_mapping)
                incoming_prefill_roles = build_prefill_roles(incoming_source_roles, list(personas.keys()), seed_mapping)
                source_roles, prefill_personas, prefill_roles, added_source_roles = _merge_source_context(
                    existing_source_roles,
                    existing_assignments,
                    incoming_source_roles,
                    incoming_prefill_personas,
                    incoming_prefill_roles,
                )
                show_role_pool = True
                mapping_loaded_from_server = bool(active_server_code)
                if not incoming_source_roles:
                    flash(t(ui_lang, "no_source_roles"))
                else:
                    flash(t(ui_lang, "csv_loaded", n=len(incoming_source_roles)))

                headers = filtered_headers

            except Exception as exc:
                flash(t(ui_lang, "processing_failed", err=exc))

        elif action == "manual_test":
            if active_edit_code:
                _release_mapping_lock(active_edit_code, editor_id)
                session.pop("editing_mapping_code", None)
                active_edit_code = ""
            raw_roles = request.form.get("manual_roles", "")
            parsed = [r.strip() for r in re.split(r"[\n,;]+", raw_roles) if r.strip()]
            seen = set()
            source_roles = []
            for r in parsed:
                if r not in seen:
                    seen.add(r)
                    source_roles.append(r)
            if not source_roles:
                flash(t(ui_lang, "test_no_roles"))
            else:
                seed_mapping = load_seed_mapping_for_prefill(TASK_DIR)
                incoming_source_roles = source_roles
                incoming_prefill_personas = build_prefill_personas(incoming_source_roles, personas, seed_mapping)

                auto_map_external_to_individual = (request.form.get("auto_map_external_to_individual", "") == "1")
                if auto_map_external_to_individual:
                    # Pre-fill each source role with itself as direct individual role mapping.
                    incoming_prefill_roles = {src: [src] for src in incoming_source_roles}
                else:
                    incoming_prefill_roles = {}

                source_roles, prefill_personas, prefill_roles, added_source_roles = _merge_source_context(
                    existing_source_roles,
                    existing_assignments,
                    incoming_source_roles,
                    incoming_prefill_personas,
                    incoming_prefill_roles,
                )

                show_role_pool = True
                mapping_loaded_from_server = bool(active_server_code)
                flash(t(ui_lang, "test_ready", n=len(incoming_source_roles)))

        elif action == "dirty_keycloak_import":
            if active_edit_code:
                _release_mapping_lock(active_edit_code, editor_id)
                session.pop("editing_mapping_code", None)
                active_edit_code = ""
            raw_dirty = request.form.get("dirty_keycloak_text", "")
            seed_mapping = parse_dirty_keycloak_lines(raw_dirty)
            if not seed_mapping:
                flash("Keine verwertbaren RoleMapper_-Zeilen gefunden.")
            else:
                incoming_source_roles = sorted(seed_mapping.keys())
                incoming_prefill_personas = build_prefill_personas(incoming_source_roles, personas, seed_mapping)
                incoming_prefill_roles = build_prefill_roles(incoming_source_roles, list(personas.keys()), seed_mapping)
                source_roles, prefill_personas, prefill_roles, added_source_roles = _merge_source_context(
                    existing_source_roles,
                    existing_assignments,
                    incoming_source_roles,
                    incoming_prefill_personas,
                    incoming_prefill_roles,
                )
                show_role_pool = True
                mapping_loaded_from_server = bool(active_server_code)
                flash(f"Dirty-Keycloak-Import bereit. {len(incoming_source_roles)} SOURCE-Rollen erkannt.")

        elif action == "generate_assigned":
            source_roles = request.form.getlist("source_roles")
            permission_mode = (request.form.get("permission_mode", permission_mode) or permission_mode).strip().lower()
            if permission_mode not in {"auto", "old", "new"}:
                permission_mode = "auto"
            selected_personas: Dict[str, List[str]] = {}
            selected_roles: Dict[str, List[str]] = {}
            show_role_pool = (request.form.get("show_role_pool", "0") == "1")

            assignments_json = request.form.get("assignments_json", "").strip()
            if assignments_json:
                try:
                    parsed = json.loads(assignments_json)
                    if isinstance(parsed, dict):
                        for src in source_roles:
                            values = parsed.get(src, [])
                            if isinstance(values, dict):
                                pvals = values.get("personas", [])
                                rvals = values.get("roles", [])
                                if isinstance(pvals, list):
                                    selected_personas[src] = [str(v).strip() for v in pvals if str(v).strip()]
                                if isinstance(rvals, list):
                                    selected_roles[src] = [str(v).strip() for v in rvals if str(v).strip()]
                            elif isinstance(values, list):
                                # backward compatibility: old payload with personas-only list
                                selected_personas[src] = [str(v).strip() for v in values if str(v).strip()]
                except Exception:
                    flash(t(ui_lang, "assignment_json_bad"))

            lines = generate_from_persona_assignments(source_roles, selected_personas, personas, permission_mode, selected_roles)
            submit_mode = (request.form.get("submit_mode", "generate_txt") or "generate_txt").strip().lower()

            missing_meta = not all([
                (mapping_plus_country or "").strip(),
                (mapping_plus_postal_code or "").strip(),
                (mapping_plus_city or "").strip(),
                (mapping_plus_side or "").strip(),
                (mapping_plus_customer or "").strip(),
            ])

            if submit_mode == "save_mapping":
                if missing_meta:
                    flash(t(ui_lang, "metaRequired"))
                else:
                    mapping_plus_code = build_mapping_code()
                    save_mapping_plus(mapping_plus_code, lines, mapping_plus_country, mapping_plus_postal_code, mapping_plus_city, mapping_plus_customer_no, mapping_plus_side, mapping_plus_customer, mapping_client_ts, source_roles)
                    if active_edit_code and active_edit_code != mapping_plus_code:
                        _release_mapping_lock(active_edit_code, editor_id)
                    _acquire_mapping_lock(mapping_plus_code, editor_id, editor_label)
                    session["editing_mapping_code"] = mapping_plus_code
                    flash(f"Mapping gespeichert. Code: {mapping_plus_code}")
                    flash(f"Es wurden {len(lines)} Zeilen für Mapping gespeichert (Modus: {permission_mode}).")
                    flash(_lock_release_notice_text(ui_lang))
                    _release_mapping_lock(mapping_plus_code, editor_id)
                    session.pop("editing_mapping_code", None)
                    active_edit_code = ""
            elif submit_mode == "update_mapping":
                existing_code = re.sub(r"[^A-Z0-9]", "", (mapping_plus_code or "").upper())[:20]
                if missing_meta:
                    flash(t(ui_lang, "metaRequired"))
                elif not existing_code:
                    flash("Kein bestehender Mapping Code vorhanden. Bitte zuerst speichern oder laden.")
                elif not source_roles:
                    flash("Keine SOURCE-Rollen im Formular gefunden. Aktualisierung wurde abgebrochen, um leere Serverdaten zu vermeiden.")
                else:
                    ok_lock, lock_info = _acquire_mapping_lock(existing_code, editor_id, editor_label)
                    if not ok_lock:
                        holder = lock_info.get("editor_label", "anderer Benutzer")
                        flash(f"Mapping {existing_code} ist aktuell gesperrt ({holder}).")
                    else:
                        session["editing_mapping_code"] = existing_code
                        save_mapping_plus(existing_code, lines, mapping_plus_country, mapping_plus_postal_code, mapping_plus_city, mapping_plus_customer_no, mapping_plus_side, mapping_plus_customer, mapping_client_ts, source_roles)
                        mapping_plus_code = existing_code

                        # Reload just-saved server mapping so the main page reflects the persisted state.
                        reloaded_mapping, reloaded_meta = load_mapping_plus_bundle(existing_code)
                        if reloaded_mapping:
                            source_roles = sorted(reloaded_mapping.keys())
                            prefill_personas = build_prefill_personas(source_roles, personas, reloaded_mapping)
                            prefill_roles = build_prefill_roles(source_roles, list(personas.keys()), reloaded_mapping)
                            show_role_pool = True
                            mapping_loaded_from_server = True
                            mapping_plus_country = reloaded_meta.get("country", "") or mapping_plus_country
                            mapping_plus_postal_code = reloaded_meta.get("postal_code", "") or mapping_plus_postal_code
                            mapping_plus_city = reloaded_meta.get("city", "") or mapping_plus_city
                            mapping_plus_customer_no = reloaded_meta.get("customer_no", "") or mapping_plus_customer_no
                            mapping_plus_side = reloaded_meta.get("side", "") or mapping_plus_side
                            mapping_plus_customer = reloaded_meta.get("customer", "") or mapping_plus_customer

                        flash(f"Mapping aktualisiert. Code: {mapping_plus_code}")
                        flash("Hinweis: Es gibt keine Änderungshistorie. Die vorherige Server-Version wurde überschrieben.")
                        flash(_lock_release_notice_text(ui_lang))
                        _release_mapping_lock(mapping_plus_code, editor_id)
                        session.pop("editing_mapping_code", None)
                        active_edit_code = ""
            else:
                unmapped_roles = []
                for src in source_roles:
                    has_persona = bool(selected_personas.get(src, []))
                    has_role = bool(selected_roles.get(src, []))
                    if not has_persona and not has_role:
                        unmapped_roles.append(src)
                generated_file = save_output(lines)
                if unmapped_roles:
                    unmapped_warning_roles = sorted(set(unmapped_roles), key=lambda x: x.lower())
                    unmapped_warning_header = build_unmapped_roles_header(ui_lang)
                    unmapped_warning_filename = generated_file
                flash(t(ui_lang, "done_generated", n=len(lines), mode=permission_mode))

    # One-shot login challenge: show once, then clear to avoid persistent modal on every load.
    if request.method == "GET":
        session.pop("login_scope", None)
        session.pop("login_next", None)
        session.pop("login_lang", None)

    return render_template(
        "index.html",
        preview=preview,
        headers=headers,
        role_column=role_column,
        generated_file=generated_file,
        source_roles=source_roles,
        keycloak_roles=keycloak_roles,
        default_test_roles=default_test_roles,
        personas=personas,
        prefill_personas=prefill_personas,
        prefill_roles=prefill_roles,
        added_source_roles=added_source_roles,
        show_role_pool=show_role_pool,
        permission_mode=permission_mode,
        login_scope=session.get("login_scope", ""),
        login_lang=session.get("login_lang", "de"),
        supported_langs=SUPPORTED_LANGS,
        mapping_plus_country=mapping_plus_country,
        mapping_plus_postal_code=mapping_plus_postal_code,
        mapping_plus_city=mapping_plus_city,
        mapping_plus_customer_no=mapping_plus_customer_no,
        mapping_plus_side=mapping_plus_side,
        mapping_plus_customer=mapping_plus_customer,
        mapping_plus_code=mapping_plus_code,
        mapping_loaded_from_server=mapping_loaded_from_server,
        unmapped_warning_roles=unmapped_warning_roles,
        unmapped_warning_header=unmapped_warning_header,
        unmapped_warning_filename=unmapped_warning_filename,
    )

@app.route("/config-personas", methods=["GET", "POST"])
def config_personas():
    keycloak_roles = load_available_roles()
    personas = load_personas()
    persona_descriptions = load_persona_descriptions()
    settings = load_app_settings()
    can_edit = _is_admin_authenticated()

    if request.method == "POST":
        if not can_edit:
            flash("Nur Admin darf Persona-Konfiguration ändern.")
            return redirect(url_for("config_personas"))
        action = (request.form.get("action", "save_personas") or "save_personas").strip().lower()

        if action == "set_mode":
            new_mode = (request.form.get("permission_mode", settings.get("permission_mode", "auto")) or "auto").strip().lower()
            save_app_settings({"permission_mode": new_mode})
            flash(f"Permission mode set to: {new_mode}")
            return redirect(url_for("config_personas"))

        updated: Dict[str, List[str]] = {}

        assignments_json = request.form.get("assignments_json", "").strip()
        if assignments_json:
            try:
                parsed = json.loads(assignments_json)
                if isinstance(parsed, dict):
                    for pname in personas.keys():
                        values = parsed.get(pname, [])
                        if isinstance(values, list):
                            updated[pname] = sorted(set(str(v).strip() for v in values if str(v).strip()))
                        else:
                            updated[pname] = []
                else:
                    for pname in personas.keys():
                        updated[pname] = []
            except Exception:
                for pname in personas.keys():
                    values = request.form.getlist(f"roles__{pname}")
                    updated[pname] = sorted(set(v.strip() for v in values if v.strip()))
        else:
            for pname in personas.keys():
                values = request.form.getlist(f"roles__{pname}")
                updated[pname] = sorted(set(v.strip() for v in values if v.strip()))

        save_personas(updated)
        new_mode = (request.form.get("permission_mode", settings.get("permission_mode", "auto")) or "auto").strip().lower()
        save_app_settings({"permission_mode": new_mode})
        flash("Persona configuration saved.")
        return redirect(url_for("config_personas"))

    current_mode = settings.get("permission_mode", "auto")
    display_roles = roles_for_display_by_mode(keycloak_roles, current_mode)
    display_personas = {k: roles_for_display_by_mode(v, current_mode) for k, v in personas.items()}

    return render_template(
        "config_personas.html",
        personas=display_personas,
        keycloak_roles=display_roles,
        permission_mode=current_mode,
        persona_descriptions=persona_descriptions,
        can_edit=can_edit,
    )

@app.route("/config-roles", methods=["GET", "POST"])
def config_roles():
    roles = sorted(load_available_roles(), key=lambda x: x.lower())
    role_descriptions = load_role_descriptions()
    cookie_lang = (request.cookies.get("rolemapper_lang", "") or "").strip().lower()
    active_lang = (request.values.get("lang") or request.values.get("active_lang") or cookie_lang or "de").strip().lower()
    if active_lang not in SUPPORTED_LANGS:
        active_lang = "de"

    is_admin = _is_admin_authenticated()

    if request.method == "POST":
        active_lang = (request.form.get("active_lang", active_lang) or active_lang).strip().lower()
        if active_lang not in SUPPORTED_LANGS:
            active_lang = "de"

        rows_json = (request.form.get("rows_json", "") or "").strip()

        parsed_raw: List[str] = []
        descriptions_raw: Dict[str, Dict[str, str]] = {}

        if rows_json:
            try:
                rows = json.loads(rows_json)
                if isinstance(rows, list):
                    for row in rows:
                        if isinstance(row, dict):
                            role = str(row.get("role", "")).strip()
                            if role:
                                parsed_raw.append(role)
                                descriptions_raw[role] = _normalize_desc_value(row.get("description", {}))
            except Exception:
                parsed_raw = []
                descriptions_raw = {}
        else:
            raw = request.form.get("roles_text", "")
            parsed_raw = [r.strip() for r in raw.splitlines() if r.strip()]

        if is_admin:
            parsed = sorted(sanitize_lines(parsed_raw), key=lambda x: x.lower())
            save_available_roles(parsed)

            normalized_desc: Dict[str, Dict[str, str]] = {}
            for role in parsed:
                existing = role_descriptions.get(role, {lang: "" for lang in SUPPORTED_LANGS})
                incoming = descriptions_raw.get(role, existing)
                normalized_desc[role] = _normalize_desc_value(incoming)
            save_role_descriptions(normalized_desc)

            changed = len(parsed_raw) != len(parsed) or any(a != b for a, b in zip(parsed_raw, parsed))
            if changed:
                flash("Hinweis: Unsichere Zeichen wurden in Rollen neutralisiert.")
            flash(f"Roles list saved. {len(parsed)} entries.")
        else:
            incoming_by_role = {str(k): v for k, v in descriptions_raw.items()}
            updated = dict(role_descriptions)
            for role in roles:
                existing = _normalize_desc_value(updated.get(role, {}))
                incoming = _normalize_desc_value(incoming_by_role.get(role, {}))
                existing[active_lang] = sanitize_plain_text(str(incoming.get(active_lang, existing.get(active_lang, "")) or ""))
                updated[role] = existing
            save_role_descriptions(updated)
            flash(f"Role descriptions saved for language: {active_lang}")

        return redirect(url_for("config_roles", lang=active_lang))

    rows = [{"role": r, "description": role_descriptions.get(r, {lang: "" for lang in SUPPORTED_LANGS})} for r in roles]
    return render_template("config_roles.html", rows=rows, count=len(roles), langs=SUPPORTED_LANGS, active_lang=active_lang, can_manage_lists=is_admin)

@app.route("/guide")
def guide_page():
    return render_template("guide.html")

@app.route("/config-persona-names", methods=["GET", "POST"])
def config_persona_names():
    names = load_persona_names()
    descriptions = load_persona_descriptions()
    cookie_lang = (request.cookies.get("rolemapper_lang", "") or "").strip().lower()
    active_lang = (request.values.get("lang") or request.values.get("active_lang") or cookie_lang or "de").strip().lower()
    if active_lang not in SUPPORTED_LANGS:
        active_lang = "de"

    is_admin = _is_admin_authenticated()

    if request.method == "POST":
        active_lang = (request.form.get("active_lang", active_lang) or active_lang).strip().lower()
        if active_lang not in SUPPORTED_LANGS:
            active_lang = "de"

        rows_json = (request.form.get("rows_json", "") or "").strip()
        rows = []
        if rows_json:
            try:
                parsed = json.loads(rows_json)
                if isinstance(parsed, list):
                    rows = parsed
            except Exception:
                rows = []

        cleaned: Dict[str, Dict[str, str]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            persona = sanitize_plain_text(row.get("persona", ""))
            raw_desc = row.get("description", {})
            desc_by_lang = _normalize_desc_value(raw_desc)
            if persona:
                cleaned[persona] = desc_by_lang

        if is_admin:
            sorted_names = sorted(cleaned.keys(), key=lambda x: x.lower())
            save_persona_names(sorted_names)
            save_persona_descriptions({k: cleaned.get(k, "") for k in sorted_names})

            current = load_personas()
            aligned = {name: current.get(name, []) for name in sorted_names}
            save_personas(aligned)

            flash(f"Persona data saved. {len(sorted_names)} entries.")
        else:
            flash("Nur Admin darf Persona-Liste ändern.")

        return redirect(url_for("config_persona_names", lang=active_lang))

    merged_names = sorted(set(names) | set(descriptions.keys()), key=lambda x: x.lower())
    rows = [{"persona": n, "description": descriptions.get(n, {lang:"" for lang in SUPPORTED_LANGS})} for n in merged_names]
    return render_template("config_persona_names.html", rows=rows, count=len(rows), langs=SUPPORTED_LANGS, active_lang=active_lang, can_manage_lists=is_admin)


@app.route("/config-i18n", methods=["GET", "POST"])
def config_i18n():
    langs = ["de", "en", "it", "fr", "pt", "es"]
    cookie_lang = (request.cookies.get("rolemapper_lang", "") or "").strip().lower()
    selected_lang = (request.values.get("lang") or cookie_lang or "de").strip().lower()
    if selected_lang not in langs:
        selected_lang = "de"

    current = load_i18n_overrides()
    defaults = I18N_EDITOR_DEFAULTS.get(selected_lang, I18N_EDITOR_DEFAULTS.get("en", {}))

    if request.method == "POST":
        lang = (request.form.get("lang", selected_lang) or selected_lang).strip().lower()
        if lang not in langs:
            lang = "de"

        if not _is_i18n_authenticated(lang):
            flash(f"Für Sprache {lang.upper()} fehlt die passende Anmeldung.")
            return redirect(url_for("config_i18n", lang=lang))

        updated_lang: Dict[str, str] = {}
        source_defaults = I18N_EDITOR_DEFAULTS.get(lang, I18N_EDITOR_DEFAULTS.get("en", {}))
        for key in source_defaults.keys():
            value = request.form.get(f"val__{key}", "")
            if value is None:
                continue
            v = str(value).strip()
            if v:
                updated_lang[key] = sanitize_plain_text(v)

        merged = load_i18n_overrides()
        merged[lang] = updated_lang
        save_i18n_overrides(merged)
        flash("Hinweis: Lokalisierung wird als reiner Text gespeichert (HTML neutralisiert).")
        flash(f"Localization saved for language: {lang}")
        return redirect(url_for("config_i18n", lang=lang))

    existing = current.get(selected_lang, {})
    rows = []
    for key, default_text in defaults.items():
        rows.append({
            "key": key,
            "example": default_text,
            "value": existing.get(key, default_text),
        })

    return render_template(
        "config_i18n.html",
        langs=langs,
        selected_lang=selected_lang,
        rows=rows,
        can_edit=_is_i18n_authenticated(selected_lang),
    )

def load_changelog_content() -> str:
    for p in (CHANGELOG_MD, BUNDLED_CHANGELOG_MD):
        if p.exists():
            try:
                return p.read_text(encoding="utf-8")
            except Exception as exc:
                return f"CHANGELOG konnte nicht gelesen werden: {exc}"
    return "Noch kein CHANGELOG vorhanden."


def build_simple_pdf_from_text(title: str, text: str) -> bytes:
    """Create a tiny text-only PDF without external dependencies."""
    def _esc(s: str) -> str:
        return str(s).replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')

    lines = [str(title or "").strip(), ""] + [str(x) for x in str(text or "").splitlines()]
    content_lines = ["BT", "/F1 10 Tf", "50 800 Td", "14 TL"]
    first = True
    for raw in lines[:250]:
        safe = _esc(raw)
        if first:
            content_lines.append(f"({_esc(safe)}) Tj")
            first = False
        else:
            content_lines.append(f"T* ({safe}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", errors="replace")

    objs = []
    objs.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objs.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objs.append(b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 5 0 R /Resources << /Font << /F1 4 0 R >> >> >>endobj\n")
    objs.append(b"4 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")
    objs.append(f"5 0 obj<< /Length {len(stream)} >>stream\n".encode("ascii") + stream + b"\nendstream endobj\n")

    out = bytearray(b"%PDF-1.4\n")
    xref = [0]
    for obj in objs:
        xref.append(len(out))
        out.extend(obj)
    xref_pos = len(out)
    out.extend(f"xref\n0 {len(xref)}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for off in xref[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    out.extend(f"trailer<< /Size {len(xref)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii"))
    return bytes(out)

@app.route("/changelog")
def changelog_page():
    content = load_changelog_content()
    return render_template("changelog.html", changelog_content=content)

@app.route("/download/changelog-pdf")
def download_changelog_pdf():
    content = load_changelog_content()

    pdf_bytes = build_simple_pdf_from_text(f"Rolemapper Changelog v{APP_VERSION}", content)
    name = f"rolemapper-changelog-v{APP_VERSION}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        download_name=name,
        mimetype="application/pdf",
    )

@app.route("/download/docker-compose-example")
def download_compose_example():
    candidates = [
        PROJECT_DIR / "docker-compose.yml",
        PROJECT_DIR / "docker-compose.yaml",
        PROJECT_DIR / "docker-composefile.yaml",
    ]
    src = next((p for p in candidates if p.exists()), None)
    if src:
        content = src.read_text(encoding="utf-8", errors="ignore")
    else:
        content = """services:\n  rolemapper:\n    build:\n      context: .\n      dockerfile: Dockerfile\n    container_name: rolemapper\n    restart: unless-stopped\n    ports:\n      - \"5080:5080\"\n    environment:\n      - TZ=Europe/Berlin\n    volumes:\n      - ./config:/app/config\n      - ./output:/app/output\n      - ./Aufgabe:/app/Aufgabe\n      - ./mapping_store:/app/mapping_store\n"""
    return send_file(
        io.BytesIO(content.encode("utf-8")),
        mimetype="text/yaml",
        as_attachment=True,
        download_name="docker-compose.example.yaml",
    )

@app.route("/download/project-zip")
def download_project_zip():
    zip_name = f"rolemapper-v{APP_VERSION}.zip"

    exclude_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv"}
    exclude_suffixes = {".pyc", ".pyo"}

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in PROJECT_DIR.rglob("*"):
            rel = path.relative_to(PROJECT_DIR)
            if any(part in exclude_dirs for part in rel.parts):
                continue
            if path.is_dir():
                continue
            if path.suffix.lower() in exclude_suffixes:
                continue
            zf.write(path, arcname=str(rel))

    mem.seek(0)
    return send_file(mem, as_attachment=True, download_name=zip_name, mimetype="application/zip")

# Build a deployment ZIP that is self-contained (no Aufgabe/ dependency required at runtime).
@app.route("/download/deploy-bundle")
def download_deploy_bundle():
    compose_candidates = [
        PROJECT_DIR / "docker-compose.yml",
        PROJECT_DIR / "docker-compose.yaml",
        PROJECT_DIR / "docker-composefile.yaml",
        PROJECT_DIR / "docker-compose.example.yaml",
    ]
    compose_src = next((p for p in compose_candidates if p.exists()), None)
    dockerfile_src = PROJECT_DIR / "Dockerfile"

    # Fallback templates allow deploy-bundle generation even when external nodes
    # don't carry all source files next to the running app.
    compose_fallback = """services:\n  db:\n    image: postgres:16-alpine\n    container_name: rolemapper-db\n    restart: unless-stopped\n    environment:\n      POSTGRES_DB: rolemapper\n      POSTGRES_USER: rolemapper\n      POSTGRES_PASSWORD: rolemapper\n    volumes:\n      - rolemapper-db-data:/var/lib/postgresql/data\n    healthcheck:\n      test: [\"CMD-SHELL\", \"pg_isready -U rolemapper -d rolemapper\"]\n      interval: 10s\n      timeout: 5s\n      retries: 10\n\n  rolemapper:\n    build:\n      context: .\n      dockerfile: Dockerfile\n    container_name: rolemapper\n    restart: unless-stopped\n    depends_on:\n      db:\n        condition: service_healthy\n    ports:\n      - \"5080:5080\"\n    environment:\n      - TZ=Europe/Berlin\n      - DATABASE_URL=postgresql://rolemapper:rolemapper@db:5432/rolemapper\n    volumes:\n      - ./config:/app/config\n      - ./output:/app/output\n      - ./Aufgabe:/app/Aufgabe\n      - ./mapping_store:/app/mapping_store\n\nvolumes:\n  rolemapper-db-data:\n"""
    dockerfile_fallback = """FROM python:3.12-slim\n\nWORKDIR /app\n\nENV PYTHONDONTWRITEBYTECODE=1 \\\n    PYTHONUNBUFFERED=1 \\\n    TZ=Europe/Berlin\n\nCOPY requirements.txt ./\nRUN pip install --no-cache-dir -r requirements.txt\n\nCOPY . .\n\nEXPOSE 5080\n\nCMD [\"python\", \"app/app.py\"]\n"""

    compose_content = compose_src.read_text(encoding="utf-8", errors="ignore") if compose_src else compose_fallback
    dockerfile_content = dockerfile_src.read_text(encoding="utf-8", errors="ignore") if dockerfile_src.exists() else dockerfile_fallback

    initial_admin_password = "Rm-Init#2026-Safe"
    initial_auth_settings = {
        "admin_hash": generate_password_hash(initial_admin_password, method="pbkdf2:sha256"),
        "i18n_hashes": {lang: "" for lang in SUPPORTED_LANGS},
    }

    guide = f"""# Rolemapper Deployment (Docker + Traefik)

This bundle contains:
- Program files (`app/`, `requirements.txt`, optional `README.md`)
- `config/` (embedded defaults, roles/personas/settings)
- `docker-compose.example.yaml`
- `Dockerfile`
- `DEPLOY_EN.md`
- `config/auth_settings.json` (with initial admin password hash)
- `app/CHANGELOG_BUNDLED.md` (embedded changelog fallback)

Note: `Aufgabe/` is intentionally NOT included in this bundle.

## Initial admin login
- Username: not required (password only)
- Initial admin password: `{initial_admin_password}`
- Please change the admin password immediately after first login in `Auth configuration`.

## 1) Prepare folder
Extract this bundle into your deployment directory, e.g. `/opt/rolemapper`.

## 2) Check compose values
Open `docker-compose.example.yaml` and adjust:
- Hostname rule (Traefik label)
- Certificate resolver name
- External Docker network name
- Volume paths

## 2a) Traefik TLS checklist (recommended)
For HTTPS with Let's Encrypt, make sure these labels are present on the rolemapper service:
- `traefik.http.routers.rolemapper.entrypoints=https`
- `traefik.http.routers.rolemapper.tls=true`
- `traefik.http.routers.rolemapper.tls.certresolver=<your-certresolver-name>`
- `traefik.http.services.rolemapper.loadbalancer.server.port=5080`
- `traefik.docker.network=<your-traefik-network>`

Common pitfall:
- If `tls.certresolver` is missing, Traefik routes traffic but does not request/store a Let's Encrypt cert for this router.
- The certresolver value must match your Traefik configuration name exactly (example only: `le`).

## 3) Start
```bash
cd /opt/rolemapper
docker compose -f docker-compose.example.yaml up -d --build
```

## 4) Verify
```bash
docker compose -f docker-compose.example.yaml ps
docker compose -f docker-compose.example.yaml logs -f
```
Then open your configured HTTPS URL.

## 5) Updates
When code changes:
```bash
docker compose -f docker-compose.example.yaml up -d --build
```

Bundle generated from Rolemapper {APP_VERSION}.
"""

    bundled_changelog = "Noch kein CHANGELOG vorhanden."
    if CHANGELOG_MD.exists():
        try:
            bundled_changelog = CHANGELOG_MD.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
        # Build/deploy files
        zf.writestr("docker-compose.example.yaml", compose_content)
        zf.writestr("Dockerfile", dockerfile_content)
        zf.writestr("DEPLOY_EN.md", guide)
        zf.writestr("config/auth_settings.json", json.dumps(initial_auth_settings, indent=2, ensure_ascii=False))
        zf.writestr("app/CHANGELOG_BUNDLED.md", bundled_changelog)

        # Program files (without Aufgabe)
        required_files = [
            PROJECT_DIR / "requirements.txt",
            PROJECT_DIR / "README.md",
        ]
        for f in required_files:
            if f.exists() and f.is_file():
                zf.write(f, arcname=f.name)

        config_dir = PROJECT_DIR / "config"
        if config_dir.exists():
            for path in config_dir.rglob("*.json"):
                if path.is_dir():
                    continue
                if path.name == "auth_settings.json":
                    continue
                zf.write(path, arcname=str(path.relative_to(PROJECT_DIR)))

        app_dir = PROJECT_DIR / "app"
        if app_dir.exists():
            for path in app_dir.rglob("*"):
                if path.is_dir():
                    continue
                if path.suffix.lower() in {".pyc", ".pyo"}:
                    continue
                zf.write(path, arcname=str(path.relative_to(PROJECT_DIR)))

    mem.seek(0)
    return send_file(mem, as_attachment=True, download_name=f"rolemapper-deploy-bundle-v{APP_VERSION}.zip", mimetype="application/zip")

@app.route("/download/<filename>")
def download(filename: str):
    safe_name = os.path.basename(filename)
    candidates = [OUTPUT_DIR / safe_name, Path('/tmp/rolemapper-output') / safe_name, Path('./output') / safe_name]
    file_path = next((p for p in candidates if p.exists()), None)
    if not file_path:
        flash("File not found.")
        return redirect(url_for("index"))
    return send_file(file_path, as_attachment=True)

def list_mapping_plus_entries() -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []
    _init_mapping_db()
    with _db_connect() as conn:
        rows = conn.execute(
            """
            SELECT code, country, postal_code, city, customer_no, site, customer,
                   created_at, created_at_client, updated_at, updated_at_client,
                   line_count, mapping_lines_text
            FROM mapping_records
            WHERE deleted = 0
            """
        ).fetchall()
    for row in rows:
        client_ts = sanitize_plain_text(row["updated_at_client"] or row["created_at_client"] or "")
        server_ts = sanitize_plain_text(row["updated_at"] or row["created_at"] or "")
        has_txt = "1" if str(row["mapping_lines_text"] or "").strip() else "0"
        entries.append(
            {
                "code": sanitize_plain_text(row["code"] or ""),
                "country": sanitize_plain_text(row["country"] or ""),
                "postal_code": sanitize_plain_text(row["postal_code"] or ""),
                "city": sanitize_plain_text(row["city"] or ""),
                "customer_no": sanitize_plain_text(row["customer_no"] or ""),
                "side": sanitize_plain_text(row["site"] or ""),
                "customer": sanitize_plain_text(row["customer"] or ""),
                "client_ts": client_ts,
                "server_ts": server_ts,
                "line_count": str(row["line_count"] if row["line_count"] is not None else ""),
                "has_txt": has_txt,
            }
        )
    entries.sort(key=lambda x: (x.get("client_ts") or x.get("server_ts") or ""), reverse=True)
    return entries

@app.route("/admin-mappings")
def admin_mappings():
    ui_lang = (request.args.get("lang") or request.cookies.get("rolemapper_lang") or "de").strip().lower()
    if ui_lang not in SUPPORTED_LANGS:
        ui_lang = "de"
    entries = list_mapping_plus_entries()
    return render_template(
        "admin_mappings.html",
        ui_lang=ui_lang,
        app_version=APP_VERSION,
        auth_admin=_is_admin_authenticated(),
        auth_i18n=bool(session.get("auth_i18n_langs")),
        mapping_entries=entries,
    )



@app.route("/api/mapping-codes")
def api_mapping_codes():
    """API: list all server-side stored mapping codes with concise metadata."""
    raw_entries = list_mapping_plus_entries()
    entries = []
    for e in raw_entries:
        code = e.get("code", "")
        updated_ts = e.get("client_ts") or e.get("server_ts") or ""

        mapping_lines: List[str] = []
        if code:
            with _db_connect() as conn:
                row = conn.execute(
                    "SELECT mapping_lines_text FROM mapping_records WHERE code = %s AND deleted = 0",
                    (code,),
                ).fetchone()
            if row:
                mapping_lines = str(row["mapping_lines_text"] or "").splitlines()

        entries.append(
            {
                "code": code,
                "country": e.get("country", ""),
                "postal_code": e.get("postal_code", ""),
                "city": e.get("city", ""),
                "customer_no": e.get("customer_no", ""),
                "site": e.get("side", ""),
                "customer": e.get("customer", ""),
                "line_count": e.get("line_count", ""),
                "updated_ts": updated_ts,
                "mapping": mapping_lines,
            }
        )

    payload = {
        "ok": True,
        "count": len(entries),
        "codes": [e.get("code", "") for e in entries],
        "entries": entries,
    }
    return app.response_class(
        response=json.dumps(payload, indent=2, ensure_ascii=False),
        status=200,
        mimetype="application/json",
    )


@app.route("/api/mapping-load/<code>")
def api_mapping_load(code: str):
    """API: load stored mapping payload by code (instead of URL query on '/')."""
    safe_code = re.sub(r"[^A-Z0-9]", "", (code or "").upper())[:20]
    if not safe_code:
        return jsonify({"ok": False, "error": "invalid_code"}), 400

    mapping, meta = load_mapping_plus_bundle(safe_code)
    if not mapping and not any(meta.values()):
        return jsonify({"ok": False, "error": "not_found"}), 404

    return jsonify(
        {
            "ok": True,
            "code": safe_code,
            "mapping": mapping,
            "meta": {
                "country": meta.get("country", ""),
                "postal_code": meta.get("postal_code", ""),
                "city": meta.get("city", ""),
                "customer_no": meta.get("customer_no", ""),
                "site": meta.get("side", ""),
                "customer": meta.get("customer", ""),
            },
            "ui_load_url": f"/api/edit-mapping/{safe_code}",
        }
    )


@app.route("/api/mapping-download/<code>")
def api_mapping_download(code: str):
    """API: download mapping text by code with integration-friendly filename."""
    safe_code = re.sub(r"[^A-Z0-9]", "", (code or "").upper())[:20]
    if not safe_code:
        return jsonify({"ok": False, "error": "invalid_code"}), 400

    mapping, _meta = load_mapping_plus_bundle(safe_code)
    if not mapping:
        return jsonify({"ok": False, "error": "not_found"}), 404

    lines: List[str] = []
    for src in sorted(mapping.keys()):
        for tgt in mapping.get(src, []):
            lines.append(f"{src}={tgt}")
    content = "\n".join(lines) + ("\n" if lines else "")
    mem = io.BytesIO(content.encode("utf-8"))

    return send_file(
        mem,
        as_attachment=True,
        download_name=f"mapping-{safe_code}.txt",
        mimetype="text/plain",
    )


@app.route("/api/edit-mapping/<code>")
def api_edit_mapping(code: str):
    """UI helper: open main page with a server mapping code."""
    safe_code = re.sub(r"[^A-Z0-9]", "", (code or "").upper())[:20]
    if not safe_code:
        flash("Ungültiger Mapping-Code.")
        return redirect(url_for("index"))
    return redirect(url_for("index", api_code=safe_code))


@app.route("/api/mapping-init", methods=["GET", "POST"])
def api_mapping_init():
    """API: create mapping/customer-data structure on server and return load URL."""
    payload = request.get_json(silent=True) if request.method == "POST" else None

    def _pick(name: str, default: str = "") -> str:
        if isinstance(payload, dict):
            return sanitize_plain_text(payload.get(name, default))
        # GET support via query string, POST fallback via form fields.
        return sanitize_plain_text(request.values.get(name, default))

    code_raw = _pick("code")
    safe_code = re.sub(r"[^A-Z0-9]", "", (code_raw or "").upper())[:20] or build_mapping_code()

    country = _pick("country")
    postal_code = _pick("postal_code")
    city = _pick("city")
    customer_no = _pick("customer_no")
    side = _pick("site") or _pick("side")
    customer = _pick("customer")
    client_ts = _pick("client_ts")

    source_roles: List[str] = []
    if isinstance(payload, dict):
        raw_roles = payload.get("source_roles", [])
        if isinstance(raw_roles, list):
            source_roles = [sanitize_plain_text(r) for r in raw_roles if sanitize_plain_text(r)]
    else:
        raw_roles_values = request.values.getlist("source_roles")
        if raw_roles_values:
            source_roles = [sanitize_plain_text(x) for x in raw_roles_values if sanitize_plain_text(x)]
        else:
            raw_roles_txt = request.values.get("source_roles", "")
            if raw_roles_txt:
                source_roles = [sanitize_plain_text(x) for x in re.split(r"[\\n,;]+", raw_roles_txt) if sanitize_plain_text(x)]

    # Prevent creating duplicate customers on init.
    def _norm(v: str) -> str:
        return sanitize_plain_text(v).strip().casefold()

    allow_existing = _pick("allow_existing").lower() in {"1", "true", "yes", "on"}
    existing_code = ""
    entries = list_mapping_plus_entries()

    # Primary duplicate key: customer_no (if provided).
    if customer_no:
        wanted_no = _norm(customer_no)
        for e in entries:
            if _norm(e.get("customer_no", "")) == wanted_no:
                existing_code = e.get("code", "")
                break

    # Fallback duplicate key if no customer_no is provided.
    if not existing_code and not customer_no and customer:
        wanted_customer = _norm(customer)
        wanted_postal = _norm(postal_code)
        wanted_city = _norm(city)
        wanted_side = _norm(side)
        for e in entries:
            if _norm(e.get("customer", "")) != wanted_customer:
                continue
            if wanted_postal and _norm(e.get("postal_code", "")) != wanted_postal:
                continue
            if wanted_city and _norm(e.get("city", "")) != wanted_city:
                continue
            if wanted_side and _norm(e.get("side", "")) != wanted_side:
                continue
            existing_code = e.get("code", "")
            break

    if existing_code and not allow_existing:
        return jsonify(
            {
                "ok": False,
                "error": "customer_exists",
                "code": existing_code,
                "load_url": f"/api/edit-mapping/{existing_code}",
                "download_url": f"/api/mapping-download/{existing_code}",
            }
        ), 409

    # Create server-side structure even without lines.
    save_mapping_plus(
        safe_code,
        lines=[],
        country=country,
        postal_code=postal_code,
        city=city,
        customer_no=customer_no,
        side=side,
        customer=customer,
        client_ts=client_ts,
        source_roles=source_roles,
    )

    return jsonify(
        {
            "ok": True,
            "code": safe_code,
            "load_url": f"/api/edit-mapping/{safe_code}",
            "download_url": f"/api/mapping-download/{safe_code}",
        }
    )

@app.route("/download-mapping-plus/<code>")
def download_mapping_plus(code: str):
    safe_code = re.sub(r"[^A-Z0-9]", "", (code or "").upper())[:20]
    if not safe_code:
        flash("Ungültiger Mapping-Code.")
        return redirect(url_for("admin_mappings"))

    mapping, _meta = load_mapping_plus_bundle(safe_code)
    if not mapping:
        flash("Mapping-TXT nicht gefunden.")
        return redirect(url_for("admin_mappings"))

    lines: List[str] = []
    for src in sorted(mapping.keys()):
        for tgt in mapping.get(src, []):
            lines.append(f"{src}={tgt}")
    content = "\n".join(lines) + ("\n" if lines else "")
    mem = io.BytesIO(content.encode("utf-8"))
    download_name = f"mappingplus-{safe_code}.txt"
    return send_file(mem, as_attachment=True, download_name=download_name, mimetype="text/plain")


@app.route("/mapping-plus-content/<code>")
def mapping_plus_content(code: str):
    safe_code = re.sub(r"[^A-Z0-9]", "", (code or "").upper())[:20]
    if not safe_code:
        return jsonify({"ok": False, "error": "invalid_code"}), 400

    _init_mapping_db()
    with _db_connect() as conn:
        row = conn.execute(
            "SELECT mapping_lines_text FROM mapping_records WHERE code = %s AND deleted = 0",
            (safe_code,),
        ).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "not_found"}), 404

    content = str(row["mapping_lines_text"] or "")
    return jsonify({"ok": True, "code": safe_code, "content": content})


@app.route("/mapping-plus-history/<code>")
def mapping_plus_history(code: str):
    safe_code = re.sub(r"[^A-Z0-9]", "", (code or "").upper())[:20]
    if not safe_code:
        return jsonify({"ok": False, "error": "invalid_code"}), 400

    _init_mapping_db()
    with _db_connect() as conn:
        rows = conn.execute(
            """
            SELECT id, event_type, changed_at, actor, mapping_lines_text
            FROM mapping_history
            WHERE code = %s
            ORDER BY id DESC
            LIMIT 200
            """,
            (safe_code,),
        ).fetchall()

    entries = []
    for r in rows:
        lines = str(r["mapping_lines_text"] or "").splitlines()
        entries.append(
            {
                "id": int(r["id"]),
                "event_type": sanitize_plain_text(r["event_type"] or ""),
                "changed_at": sanitize_plain_text(r["changed_at"] or ""),
                "actor": sanitize_plain_text(r["actor"] or ""),
                "line_count": len(lines),
            }
        )

    return jsonify({"ok": True, "code": safe_code, "entries": entries})


@app.route("/mapping-plus-restore", methods=["POST"])
def mapping_plus_restore():
    if not _is_admin_authenticated():
        return jsonify({"ok": False, "error": "forbidden"}), 403

    code = sanitize_plain_text(request.form.get("code", ""))
    history_id_raw = sanitize_plain_text(request.form.get("history_id", ""))
    safe_code = re.sub(r"[^A-Z0-9]", "", (code or "").upper())[:20]
    if not safe_code:
        return jsonify({"ok": False, "error": "invalid_code"}), 400
    try:
        history_id = int(history_id_raw)
    except Exception:
        return jsonify({"ok": False, "error": "invalid_history_id"}), 400

    _init_mapping_db()
    with _db_connect() as conn:
        hist = conn.execute(
            "SELECT * FROM mapping_history WHERE id = %s AND code = %s LIMIT 1",
            (history_id, safe_code),
        ).fetchone()
        if not hist:
            return jsonify({"ok": False, "error": "history_not_found"}), 404

        cur = conn.execute(
            "SELECT * FROM mapping_records WHERE code = %s LIMIT 1",
            (safe_code,),
        ).fetchone()
        if not cur:
            return jsonify({"ok": False, "error": "record_not_found"}), 404

        lines = str(hist["mapping_lines_text"] or "").splitlines()
        meta = {}
        try:
            meta = json.loads(str(hist["meta_json"] or "{}"))
        except Exception:
            meta = {}

        def _m(key: str) -> str:
            return sanitize_plain_text(str(meta.get(key, "") or "")) if isinstance(meta, dict) else ""

        source_roles = []
        if isinstance(meta, dict) and isinstance(meta.get("source_roles"), list):
            source_roles = [sanitize_plain_text(str(x)) for x in meta.get("source_roles", []) if sanitize_plain_text(str(x))]
        if not source_roles:
            try:
                source_roles = [
                    sanitize_plain_text(str(x))
                    for x in json.loads(str(cur["source_roles_json"] or "[]"))
                    if sanitize_plain_text(str(x))
                ]
            except Exception:
                source_roles = []

        now_server = datetime.now().isoformat()
        country = _m("country") or sanitize_plain_text(cur["country"] or "")
        postal_code = _m("postal_code") or sanitize_plain_text(cur["postal_code"] or "")
        city = _m("city") or sanitize_plain_text(cur["city"] or "")
        customer_no = _m("customer_no") or sanitize_plain_text(cur["customer_no"] or "")
        site = _m("site") or sanitize_plain_text(cur["site"] or "")
        customer = _m("customer") or sanitize_plain_text(cur["customer"] or "")

        conn.execute(
            """
            UPDATE mapping_records
            SET country = %s,
                postal_code = %s,
                city = %s,
                customer_no = %s,
                site = %s,
                customer = %s,
                updated_at = %s,
                line_count = %s,
                source_roles_json = %s,
                mapping_lines_text = %s,
                deleted = 0
            WHERE code = %s
            """,
            (
                country,
                postal_code,
                city,
                customer_no,
                site,
                customer,
                now_server,
                len(lines),
                json.dumps(source_roles, ensure_ascii=False),
                "\n".join(lines),
                safe_code,
            ),
        )

        meta_obj = {
            "code": safe_code,
            "country": country,
            "postal_code": postal_code,
            "city": city,
            "customer_no": customer_no,
            "site": site,
            "customer": customer,
            "updated_at": now_server,
            "line_count": len(lines),
            "source_roles": source_roles,
            "restored_from_history_id": history_id,
        }
        _record_history(conn, safe_code, "restore", meta_obj, lines)

    return jsonify({"ok": True, "code": safe_code, "line_count": len(lines)})


@app.route("/admin-mappings-delete-line", methods=["POST"])
def admin_mappings_delete_line():
    if not _is_admin_authenticated():
        return jsonify({"ok": False, "error": "forbidden"}), 403

    code = sanitize_plain_text(request.form.get("code", ""))
    line_idx_raw = sanitize_plain_text(request.form.get("line_idx", ""))
    safe_code = re.sub(r"[^A-Z0-9]", "", (code or "").upper())[:20]
    if not safe_code:
        return jsonify({"ok": False, "error": "invalid_code"}), 400

    try:
        line_idx = int(line_idx_raw)
    except Exception:
        return jsonify({"ok": False, "error": "invalid_index"}), 400

    _init_mapping_db()
    with _db_connect() as conn:
        row = conn.execute(
            "SELECT * FROM mapping_records WHERE code = %s AND deleted = 0",
            (safe_code,),
        ).fetchone()
        if not row:
            return jsonify({"ok": False, "error": "not_found"}), 404

        lines = str(row["mapping_lines_text"] or "").splitlines()
        if line_idx < 0 or line_idx >= len(lines):
            return jsonify({"ok": False, "error": "index_out_of_range"}), 400

        del lines[line_idx]
        now_server = datetime.now().isoformat()
        conn.execute(
            """
            UPDATE mapping_records
            SET mapping_lines_text = %s, line_count = %s, updated_at = %s
            WHERE code = %s
            """,
            ("\n".join(lines), len(lines), now_server, safe_code),
        )
        meta_obj = {
            "code": safe_code,
            "country": sanitize_plain_text(row["country"] or ""),
            "postal_code": sanitize_plain_text(row["postal_code"] or ""),
            "city": sanitize_plain_text(row["city"] or ""),
            "customer_no": sanitize_plain_text(row["customer_no"] or ""),
            "site": sanitize_plain_text(row["site"] or ""),
            "customer": sanitize_plain_text(row["customer"] or ""),
            "line_count": len(lines),
            "updated_at": now_server,
        }
        _record_history(conn, safe_code, "delete_line", meta_obj, lines)

    return jsonify({"ok": True, "line_count": len(lines)})


@app.route("/admin-mappings-delete-code", methods=["POST"])
def admin_mappings_delete_code():
    if not _is_admin_authenticated():
        return jsonify({"ok": False, "error": "forbidden"}), 403

    code = sanitize_plain_text(request.form.get("code", ""))
    safe_code = re.sub(r"[^A-Z0-9]", "", (code or "").upper())[:20]
    if not safe_code:
        return jsonify({"ok": False, "error": "invalid_code"}), 400

    _init_mapping_db()
    with _db_connect() as conn:
        row = conn.execute(
            "SELECT * FROM mapping_records WHERE code = %s AND deleted = 0",
            (safe_code,),
        ).fetchone()
        if not row:
            return jsonify({"ok": False, "error": "not_found"}), 404

        lines = str(row["mapping_lines_text"] or "").splitlines()
        meta_obj = {
            "code": safe_code,
            "country": sanitize_plain_text(row["country"] or ""),
            "postal_code": sanitize_plain_text(row["postal_code"] or ""),
            "city": sanitize_plain_text(row["city"] or ""),
            "customer_no": sanitize_plain_text(row["customer_no"] or ""),
            "site": sanitize_plain_text(row["site"] or ""),
            "customer": sanitize_plain_text(row["customer"] or ""),
            "line_count": int(row["line_count"] or 0),
        }
        conn.execute(
            "UPDATE mapping_records SET deleted = 1, updated_at = %s WHERE code = %s",
            (datetime.now().isoformat(), safe_code),
        )
        _record_history(conn, safe_code, "delete_code", meta_obj, lines)

    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5080, debug=False)
