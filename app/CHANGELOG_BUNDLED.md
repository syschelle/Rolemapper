# Rolemapper – Änderungsprotokoll (fortlaufend)

Dieses Dokument hält die Änderungen pro Version fest.

## Permanente Systembeschreibung

- Produkt: Flask-basierter LDAP/ORBIS → Keycloak Rolemapper (Python)
- UI-Grundlayout: Header + linke Navigation + rechte Inhaltsfläche, responsive
- Hauptfunktion:
  - Import von `mapping.txt` / `mapping-*.txt`
  - Import von „Dirty Keycloak“-Zeilen im Format `RoleMapper_<SOURCE>_to_<TARGET>`, der Rest wird ignoriert.
  - Zuordnung je SOURCE-Rolle via Drag&Drop
  - Ausgabe als `mapping-YYYYMMDD-HHMMSS.txt`
- Mapping-Logik:
  - Persona-Zuweisungen pro SOURCE
  - Direkte Rollen-Zuweisungen pro SOURCE (zusätzlicher Rollen-Pool auf Hauptseite)
  - Ausgabe enthält Persona-Linien plus Rollen-Linien (inkl. Kompatibilitäts-Expansion old/new)
  - Quellrollen ohne Zuordnung werden serverseitig mitgespeichert (`source_roles`), auch wenn noch keine Mapping-Zeilen existieren
- Kundendaten-Metadaten (Server-Mapping):
  - `country`, `postal_code`, `city`, `customer_no`, `site`, `customer`
  - Hinweis: `site` ist der aktuelle Feldname (rückwärtskompatibles Lesen von Altfeld `side` bleibt erhalten)
- Vorbelegung:
  - Aus neuester Mapping-TXT werden Persona- und Rollen-Treffer automatisch vorbelegt
- Sicherheit/Härtung:
  - Eingaben/Uploads als Plain Text sanitisiert
  - TXT-Import gehärtet (Token-Sanitizing, Längenlimit, Blockierung von `javascript:`-Präfixen)
  - Sichere Redirect-Validierung (`next` nur intern)
- Rollen- und Rechtemodell:
  - Nicht angemeldet:
    - Hauptseite: sichtbar + nutzbar
    - Guide: sichtbar (read)
    - Persona-Konfiguration: sichtbar (read-only)
    - Changelog + Changelog-PDF-Download: sichtbar/erlaubt
  - Admin:
    - alle Seiten sichtbar
    - volle Schreibrechte (Config, Listen, i18n, Auth, Server-Mappings löschen)
  - Lokalisierer:
    - sichtbare Seiten: Hauptseite, Guide, Rollenliste, Lokalisierung, Changelog
    - Schreibrechte nur sprachgebunden (passendes Sprachpasswort) in:
      - Lokalisierungstexte bearbeiten
      - Rollenliste (nur Beschreibungsfeld der autorisierten Sprache)
- Server-Mappings:
  - Listenansicht unter `/admin-mappings`
  - Aktionen pro Eintrag: Laden, TXT-Download, Zeilenansicht
  - Admin-only Löschung direkt in Tabellen-Spalte „Löschen“
- Konfigurierbare Datenquellen (`config/`):
  - `personas.json`, `roles_column_a.json`, `persona_names.json`
  - `persona_descriptions.json`, `role_descriptions.json`
  - `app_settings.json`, `i18n_overrides.json`, `auth_settings.json`, `sample_roles.json`
- Backup:
  - In „Konfiguration“: ZIP-Backup via `/download/config-backup`
  - Enthält Konfigurationsdateien + `mapping_store/` (Server-Mappings)
- APIs:
  - `GET /api/mapping-download/<code>` → Download mit Dateiname `mapping-<CODE>.txt`
  - `GET|POST /api/mapping-init`
    - Schnittstelle: erzeugt Server-Struktur (Kundendaten + optionale `source_roles`)
    - Response: `code`, `load_url`, `download_url`
    - Duplikatprüfung: `409 customer_exists` (Override: `allow_existing=true`)
    - Beispiel (GET): `/api/mapping-init?country=DE&postal_code=50667&city=K%C3%B6ln&customer_no=K-10042&site=Zentrale&customer=Beispiel%20GmbH&source_roles=ROLE_SALES,ROLE_SUPPORT`
    - Beispiel-Response: `{"ok":true,"code":"AB12CD34","load_url":"/api/edit-mapping/AB12CD34","download_url":"/api/mapping-download/AB12CD34"}`
  - `GET /api/mapping-load/<code>` → liefert gespeichertes Mapping + Metadaten als JSON (`site` in Meta)
  - `GET /api/mapping-codes` → liefert alle serverseitig gespeicherten Codes als leserliches JSON inkl. kompakter Metadaten, `updated_ts` und `mapping` (Zeilenarray)
  - Für UI-Direktladen nutzt die API ` /api/edit-mapping/<CODE> ` (`ui_load_url` in API-Antwort aus `/api/mapping-load/<code>`).

- Changelog/Transparenz:
  - In-App Changelog-Ansicht mit farblicher Semantik
  - PDF-Export „on the fly“ aus aktuellem Changelog

## v1.0.9 (current)
- Anfrage: In der History wird der Benutzer aus dem Cookie nicht angezeigt.
- Antwort: Behoben. History-Einträge verwenden jetzt bevorzugt die aufgelöste Editor-Identität (inkl. Cookie-/SSO-/manuellem Namen + Rolle) statt nur generischer Werte wie `admin`/`user`.
- Änderungen:
  - `app.py`:
    - `_history_actor()` auf `_editor_identity()` umgestellt (mit Fallback).
    - Dadurch erscheinen in neuen Historieneinträgen z. B. `Sylvio (admin)` statt nur `admin`.

## v1.0.8
- Anfrage: Zugriff auf eine History, um Änderungen im Mapping zurückzuspielen.
- Antwort: Umgesetzt. In `Server-Mappings` gibt es jetzt eine History-Aktion pro Mapping-Code inkl. Restore-Funktion (Admin).
- Änderungen:
  - `app.py`:
    - Neue API: `GET /mapping-plus-history/<code>` (liefert Historieneinträge).
    - Neue API: `POST /mapping-plus-restore` (stellt eine gewählte Historienversion wieder her, admin-only).
    - Beim Restore wird ein neuer History-Eintrag `restore` geschrieben.
  - `admin_mappings.html`:
    - Neue Spalte/Action `History` pro Mapping.
    - Popup/Fenster mit Historieneinträgen (ID, Event, Zeit, Actor, Zeilen).
    - Für Admin: Button `Restore` je Eintrag (mit Bestätigung).
    - Layout/Colspan entsprechend erweitert.
    - i18n-Keys für History-Spalte/-Button in DE/EN/IT/FR/PT/ES ergänzt.

## v1.0.7
- Anfrage: In „Rollenliste anzeigen“ neu hinzugefügte Rollen mit aufführen/parkieren und einen Export als reine Textdatei (ohne Mapping) ermöglichen.
- Antwort: Umgesetzt. Das Rollenlisten-Fenster gruppiert jetzt Rollen in „Neu hinzugefügt“ und „Bestehend“; zusätzlich gibt es einen TXT-Export aller aktuellen AD/ORBIS-SOURCE-Rollen ohne Mappinginhalte.
- Änderungen:
  - `index.html`:
    - Modal „Rollenliste anzeigen“ erweitert um Button `Export TXT`.
    - Rollenliste im Modal gruppiert:
      - `sourceRolesNew` (neu hinzugefügt)
      - `sourceRolesExisting` (bestehend)
    - Neue Rollen erhalten auch in der Listenansicht das „Neu“-Badge.
    - Export erzeugt Datei `source-roles-<timestamp>.txt` (eine Rolle pro Zeile, ohne Mapping).
    - Neue i18n-Keys ergänzt für DE/EN/IT/FR/PT/ES:
      - `sourceRolesNew`, `sourceRolesExisting`, `sourceRolesExport`

## v1.0.6
- Anfrage: Der Button „Ändern“ in den AD/ORBIS-Rollen wird beim Sprachwechsel nicht übersetzt.
- Antwort: Behoben. Die Buttons im AD/ORBIS-Bereich sind jetzt vollständig i18n-fähig (inkl. dynamischer Zeilen und Edit-Status).
- Änderungen:
  - `index.html`:
    - Statische Buttons mit i18n-Keys versehen:
      - `metaEditBtn` -> `metaEdit`
      - Rollenzeilen-Buttons -> `sourceEdit`, `sourceDelete`
    - JS-Textumschaltung von Hardcoded-Strings auf i18n-Keys umgestellt:
      - `sourceOk`, `sourceEdit`
      - `metaOk`, `metaEdit`
    - Dynamisch erzeugte Rollenzeilen verwenden ebenfalls i18n-Keys.
    - Neue Übersetzungskeys ergänzt für DE/EN/IT/FR/PT/ES.
    - Beim Sprachwechsel wird der Meta-Edit-Buttonzustand neu lokalisiert.

## v1.0.5
- Anfrage: Die Hervorhebung neuer AD/ORBIS-Rollen soll markanter sein; außerdem Übersetzungen für andere Sprachen berücksichtigen.
- Antwort: Umgesetzt. Die visuelle Hervorhebung wurde deutlich verstärkt (stärkerer Verlauf + linker Akzentbalken), und das Badge ist jetzt vollständig i18n-fähig in allen unterstützten UI-Sprachen.
- Änderungen:
  - `index.html`:
    - Hervorhebung `.newly-added-source` markanter gestaltet:
      - stärkerer Hintergrundverlauf
      - zusätzlicher linker Akzentbalken in Headerfarbe
    - Badge-Stil sichtbar kräftiger gemacht.
    - Badge-Text auf i18n-Key umgestellt (`newRoleBadge`).
    - Übersetzungen ergänzt für DE/EN/IT/FR/PT/ES.

## v1.0.4
- Anfrage: Der Rahmen für neu hinzugefügte Rollen wirkt optisch nicht schön; bitte wieder wie vorher, aber neue Rollen trotzdem klar erkennbar machen.
- Antwort: Umgesetzt. Der Standard-Rahmen wurde zurückgesetzt, stattdessen gibt es jetzt eine dezentere visuelle Hervorhebung für neue Rollen.
- Änderungen:
  - `index.html`:
    - Rahmen wieder auf den bisherigen Standard (`#dfe7ef`) gesetzt.
    - Für neu hinzugefügte Rollen-Buckets (`.newly-added-source`) dezenter Hintergrundverlauf ergänzt.
    - Neues Badge `✨ Neu` direkt neben dem Rollennamen für klare Kennzeichnung ergänzt.

## v1.0.3
- Anfrage: Der Rahmen neu hinzugefügter AD/ORBIS-Rollen soll in Header-Farbe erscheinen; bisher sichtbar nicht zuverlässig umgesetzt.
- Antwort: Behoben. Statt `var(--primary)` (nicht überall definiert) wird nun explizit die Header-Farbe `#0d3b66` verwendet, zusätzlich mit Klasse `.newly-added-source` als visuelle Absicherung.
- Änderungen:
  - `index.html`:
    - Rahmenfarbe neu hinzugefügter SOURCE-Buckets auf `#0d3b66` gesetzt.
    - CSS-Klasse `.newly-added-source` ergänzt (`border-color` + subtiler Inset-Highlight), damit der Effekt auch bei künftigen Style-Änderungen stabil bleibt.

## v1.0.2
- Anfrage: Auch bei bereits geladenem Mapping (Server oder mapping.txt) sollen über alle 4 oberen Optionen zusätzliche AD/ORBIS-Rollen ergänzt werden können, statt die bestehenden zu ersetzen.
- Antwort: Umgesetzt. Die vier Einstiegsaktionen mergen jetzt neue SOURCE-Rollen in den aktuellen Mapping-Kontext hinein (inkl. bestehender Zuordnungen), statt den Zustand zu überschreiben.
- Anfrage: Neu über die oberen Optionen ergänzte AD/ORBIS-Rollen sollen mit Header-Farbe hervorgehoben werden.
- Antwort: Umgesetzt. Neu hinzugefügte Rollen-Buckets werden in der SOURCE-Liste mit Rahmenfarbe `var(--primary)` (Header-Farbton) markiert.
- Änderungen:
  - `app.py`:
    - `APP_VERSION` auf `1.0.2` erhöht.
    - Merge-Logik für Kontext-Erweiterung ergänzt:
      - Parsen bestehender Zuordnungen aus `existing_assignments_json`
      - Zusammenführen von bestehenden + neu importierten SOURCE-Rollen für `mapping_upload`, `manual_test`, `dirty_keycloak_import`, `mapping_plus_load`
      - Beibehaltung vorhandener Persona-/Rollen-Zuordnungen; neue Rollen werden additiv ergänzt.
    - Rückgabe neuer Template-Variable `added_source_roles` zur UI-Hervorhebung.
  - `index.html`:
    - Einstiegs-Sperre entfernt (`entry_locked = false`), damit alle 4 oberen Optionen auch im laufenden Mapping nutzbar bleiben.
    - Top-Formulare senden den aktuellen Mapping-Kontext mit (`existing_source_roles`, `existing_assignments_json`).
    - JS ergänzt, das vor Submit der oberen Formulare die aktuelle Bucket-Struktur serialisiert und mitschickt.
    - Neu ergänzte SOURCE-Rollen erhalten einen Rahmen in Header-Farbe.

## v1.0.1
- Anfrage: Externe Authentifizierungsrollen ohne Zuordnung sollen in der Datenbank erhalten bleiben, aber nicht in die `mapping.txt` exportiert werden.
- Antwort: Umgesetzt. Ungemappte SOURCE-Rollen bleiben jetzt als `source_roles` im Server-Mapping erhalten und erscheinen wieder beim Laden, werden aber weiterhin nicht als `SOURCE=TARGET` in die Export-TXT geschrieben.
- Anfrage: Kundendaten-Änderung auf der Hauptseite wieder aktivieren.
- Antwort: Umgesetzt. Die Schreibsperre für Nicht-Admin im Hauptseiten-Flow wurde entfernt und der Inline-Button `Ändern` in der Kundendatenzeile wieder sichtbar/funktionsfähig gemacht.
- Anfrage: In „Externe Authentifizierungsrollen“ eine Checkbox ergänzen, um externe Rollen automatisch als individuelle Rollen pro AD/ORBIS-Rolle vorzubelegen.
- Antwort: Umgesetzt. Neue Checkbox unterhalb der Textarea ergänzt; bei aktivierter Option werden die eingegebenen externen Rollen beim Start direkt als individuelle Rollen (`SOURCE -> SOURCE`) rechts vorbefüllt.
- Änderungen:
  - `app.py`:
    - `APP_VERSION` auf `1.0.1` erhöht.
    - `load_mapping_plus_bundle(...)` rekonstruiert `source_roles` robust als leere Buckets, auch wenn bereits einzelne Mapping-Zeilen vorhanden sind.
    - `manual_test` unterstützt `auto_map_external_to_individual` und setzt bei aktivierter Checkbox `prefill_roles = {src: [src]}`.
    - Kundendaten-Edit-Sperre für Nicht-Admin auf der Hauptseite entfernt.
  - `index.html`:
    - Inline-Kundendaten-Button `Ändern` nicht mehr nur admin-gebunden.
    - Neue Checkbox in der Kachel „Externe Authentifizierungsrollen“ ergänzt.

## v1.0.0
- Stable Release `1.0.0` erstellt und für GitHub-Deployment vorbereitet.
- Version im Backend auf `APP_VERSION = "1.0.0"` angehoben.
- Deployment-/Compose-Stand konsolidiert (inkl. DB-Persistenz über `mapping_store`).

## v0.3.3
- Versionspflege ergänzt: `APP_VERSION` auf `0.3.3` gesetzt.
- `/api/mapping-init`:
  - unterstützt `GET|POST`
  - Duplikatschutz mit `409 customer_exists`
  - Override via `allow_existing=true`
- UI-Direktladen standardisiert auf `/api/edit-mapping/<CODE>` (inkl. `load_url`/`ui_load_url`).
- Server-Mappings auf DB-only-Backend (`mapping_store/mapping_store.db`) mit Historientabelle umgestellt.
- Admin-Metadaten:
  - Button „Ändern“ nur für Admin sichtbar
  - Kundendaten bei Nicht-Admin gegen ungewollte Änderungen geschützt
- Konfiguration:
  - Checkbox für Badge „Testversion not for production“ ergänzt
  - Übersetzungen + Sprachpersistenz über Seitenwechsel stabilisiert
- Linkleiste/Sprachen:
  - Link-Aufrufe vereinheitlicht
  - „Konfiguration“-Link korrekt lokalisiert
- Changelog/API-Texte nachgezogen (inkl. gruppierter Darstellung für `mapping-init`).

## v0.3.0 (pre-release)
- Release-Markierung auf Wunsch gesetzt: neuer Pre-Release-Stand `0.3.0`.
- Versionsstrategie ab jetzt: Patch-Zähler hochzählen (`0.3.1`, `0.3.2`, ...).

## v0.3.1 (Rollback)
- Anfrage: Auf Version `0.3.1` zurückgehen.
- Antwort: Umgesetzt. Versionsstand im Backend wurde auf `0.3.1` zurückgesetzt.

## v0.3.2 (post-rollback)
- Anfrage: In den APIs soll die `→`-Beschreibung wieder sichtbar sein und in anderen Sprachen übersetzt werden.
- Antwort: Umgesetzt.
- Änderungen:
  - `changelog.html`:
    - API-Zeilen in der „Permanenten Systembeschreibung“ (Nicht-DE) enthalten wieder explizite `→`-Beschreibungen.
    - API-Beschreibungen für IT/FR/PT/ES lokalisiert ergänzt.
    - EN-Block ebenfalls mit vollständigen `→`-API-Beschreibungen ergänzt.

## v0.3.1
- Anfrage: `/?load_mapping_code=` auf API-Code umstellen, in der „Permanenten Systembeschreibung“ unter APIs dokumentieren und die „Permanente Systembeschreibung“ mehrsprachig bei Sprachwechsel anzeigen (Versionsdoku bleibt deutsch).
- Antwort: Umgesetzt.
- Änderungen:
  - Routing/API:
    - Neuer Hauptparameter für Direktladen: `/?api_code=<CODE>`.
    - Rückwärtskompatibel bleibt `load_mapping_code` als Fallback lesbar.
    - API-Antworten `load_url`/`ui_load_url` liefern jetzt `/?api_code=<CODE>`.
  - Dokumentation:
    - „## Permanente Systembeschreibung“ unter APIs auf `api_code` aktualisiert.
  - Changelog-Ansicht (`changelog.html`):
    - „Permanente Systembeschreibung“ wird bei Sprachwechsel übersetzt dargestellt.
    - Versionsdokumentation (`## v...`) bleibt unverändert auf Deutsch.

## v0.3.2
- Anfrage: In englischer Sprache bleibt „## Permanente Systembeschreibung“ weiterhin deutsch.
- Antwort: Behoben.
- Änderungen:
  - `changelog.html`:
    - Übersetzungslogik der „Permanenten Systembeschreibung“ auf führende Einrückungen robust gemacht.
    - Dadurch greifen Übersetzungen auch für eingerückte Zeilen/Bullet-Listen.
    - Zusätzliche Schlüssel für häufige Unterpunkte ergänzt.

## v0.3.3
- Anfrage: Der gesamte Text der „Permanenten Systembeschreibung“ soll bei Sprachwechsel übersetzt werden (inkl. Überschrift), während die Versionsdokumentation deutsch bleibt.
- Antwort: Umgesetzt.
- Änderungen:
  - `changelog.html`:
    - Übersetzungslogik für die „Permanente Systembeschreibung“ erweitert.
    - Überschrift wird pro Sprache übersetzt.
    - Unterpunkte werden umfassend übersetzt; bei Nicht-DE fällt die Darstellung auf die vollständige EN-Übersetzung zurück.
    - Versionseinträge (`## v...`) bleiben unverändert deutsch.

## v0.3.4
- Anfrage: Der Text der „Permanenten Systembeschreibung“ ist weiterhin nur teilweise übersetzt.
- Antwort: Behoben.
- Änderungen:
  - `changelog.html`:
    - Für Nicht-DE wird die „Permanente Systembeschreibung“ jetzt als vollständiger übersetzter Block gerendert (nicht mehr zeilenweise/teilweise).
    - Überschrift ist enthalten.
    - Versionseinträge (`## v...`) bleiben weiterhin deutsch.

## v0.3.5
- Anfrage: In Nicht-DE fehlt die Hälfte der „Permanenten Systembeschreibung“.
- Antwort: Behoben.
- Änderungen:
  - `changelog.html`:
    - Intro-Rendering auf vollständige Zeilenverarbeitung zurückgestellt (kein Abschneiden des restlichen Blocks mehr).
    - Damit bleibt die „Permanente Systembeschreibung“ in allen Sprachen vollständig sichtbar.
    - Versionseinträge bleiben weiterhin deutsch.

## v0.3.6
- Anfrage: Permanente Systembeschreibung besser strukturieren; bisher weiterhin nur teilweise übersetzt.
- Antwort: Vollständig neu aufgebaut.
- Änderungen:
  - `changelog.html`:
    - Permanente Systembeschreibung wird jetzt als eigenständiger, strukturierter Block je Sprache gerendert (DE/EN/IT/FR/PT/ES).
    - Kein teilweises Zeilen-Mapping mehr; dadurch keine Mischsprache/Teilübersetzung.
    - Original-Intro aus Markdown wird beim Rendern bewusst übersprungen, um konsistente Vollübersetzung sicherzustellen.
    - Versionseinträge (`## v...`) bleiben weiterhin deutsch.

## v0.3.7
- Anfrage: Die neue Struktur der „Permanenten Systembeschreibung“ war zu stark gekürzt; vorheriger Volltext war besser.
- Antwort: Korrigiert.
- Änderungen:
  - `changelog.html`:
    - Auf Volltext-Rendering zurückgestellt (kein Ersatz durch Kurzblock mehr).
    - Übersetzungs-Pass bleibt aktiv (v. a. Überschrift + zentrale Abschnittslabels), ohne Inhalte abzuschneiden.
    - Dadurch bleibt die komplette Systembeschreibung sichtbar; nicht gemappte Zeilen bleiben fallback-sicher erhalten.

## v0.3.8
- Anfrage: Permanente Systembeschreibung weiterhin nur teilweise übersetzt.
- Antwort: Neu umgesetzt mit vollständigem Intro-Block für Nicht-DE.
- Änderungen:
  - `changelog.html`:
    - Für Nicht-DE wird die komplette Permanente Systembeschreibung als voller übersetzter Block gerendert (kein Mischtext mehr).
    - EN ist vollständig ausformuliert; IT/FR/PT/ES erhalten denselben Vollinhalt mit lokalisierter Überschrift (ohne deutsche Restzeilen).
    - Versionseinträge bleiben deutsch.

## v0.2.89
- Anfrage: Hauptseite wird gar nicht mehr übersetzt.
- Antwort: Behoben.
- Ursache:
  - JavaScript-i18n auf `index.html` war durch ein nicht escaptes Apostroph im FR-Text (`Rôles d'autorisation DU`) gebrochen.
- Änderungen:
  - FR-String korrekt escaped (`Rôles d'autorisation DU`).
  - PT-Block von versehentlich doppelten/vermischten ES-Keys bereinigt.
  - ES-Keys für linken Bereich ergänzt (`rolesColA`, `customRoles`, `customRolesPh`, `addCustomRoles`).

## v0.2.88
- Anfrage: Auf der Hauptseite werden links beim Sprachwechsel „DU Berechtigungsrollen“, „Individuelle Rollen“, der Hint im individuellen Rollen-Textfeld und der Button „Rollen hinzufügen“ nicht übersetzt.
- Antwort: Behoben.
- Änderungen:
  - `index.html` i18n ergänzt/vereinheitlicht (DE/EN/IT/FR/PT/ES):
    - `rolesColA`
    - `customRoles`
    - `customRolesPh`
    - `addCustomRoles`

## v0.2.87
- Anfrage: Hint im Textfeld von „ad-ds oder orbis-ds code“ auf „Inhalt der orbis-ds.xml oder ad-ds.xml einfügen“ ändern und mehrsprachig pflegen.
- Antwort: Umgesetzt.
- Änderungen:
  - `index.html`:
    - Placeholder-Text im Textfeld angepasst.
    - i18n-Key `mappingRawPh` für DE/EN/IT/FR/PT/ES lokalisiert aktualisiert.

## v0.2.86
- Anfrage: „Mapping laden" in „ad-ds oder orbis-ds code" umbenennen.
- Antwort: Umgesetzt.
- Änderungen:
  - `index.html`: Titel der entsprechenden Karte angepasst (`sec.loadTitle`, DE).

## v0.2.85
- Anfrage: Im Bereich „Mapping laden" den bisherigen Inhalt ersetzen durch ein Textfeld zum Parsen von JBoss-`module-option name="mapping"`-Inhalten.
- Antwort: Umgesetzt.
- Änderungen:
  - `index.html`:
    - Karte „Mapping laden" auf Text-Parser umgestellt:
      - großes Textfeld für Rohinhalt
      - Button `Text parsen & laden`
    - Neue i18n-Keys für DE/EN/IT/FR/PT/ES:
      - `btn.parseMappingText`
      - `mappingRawPh`
  - `app.py`:
    - Neue Parser-Funktion `parse_module_option_mapping_block(...)`:
      - extrahiert Inhalt zwischen `<module-option name="mapping"> ... </module-option>`
      - verarbeitet Zeilen im Schema `^SOURCE$=TARGET`
      - ignoriert regex-lastige Pattern-Quellen
    - Action `mapping_plus_load` erweitert:
      - wenn Text vorhanden → Parser-Load in die Hauptseite (Drag&Drop-Vorbelegung)
      - sonst bleibt Code-basiertes Laden als Fallback erhalten.

## v0.2.84
- Anfrage: In der Persona-Liste im Extrafenster den Aufzählungspunkt entfernen.
- Antwort: Umgesetzt.
- Änderungen:
  - `config_persona_names.html`: Listenstil auf ohne Bullet umgestellt (`list-style:none`).

## v0.2.83
- Anfrage: In „Persona-Liste bearbeiten“ ein Extrafenster mit Liste der aktuell konfigurierten Personas.
- Antwort: Umgesetzt.
- Änderungen:
  - `config_persona_names.html`:
    - Neuer Button `Persona-Liste anzeigen` in der Toolbar.
    - Neues Modal mit alphabetischer Liste aller aktuell konfigurierten Personas und Zähler.
    - Schließen per Button oder Klick auf Overlay.
    - i18n-Keys für DE/EN/IT/FR/PT/ES ergänzt.

## v0.2.82
- Anfrage: Benutzername manuell abfragen und im Cookie speichern, damit er in Lock-Nachrichten angezeigt werden kann.
- Antwort: Umgesetzt.
- Änderungen:
  - `index.html`:
    - Beim ersten Aufruf ohne vorhandenen Namen wird ein Prompt angezeigt (manuelle Eingabe, z. B. Vorname).
    - Name wird in Cookie `rolemapper_editor_name` + `localStorage` gespeichert (1 Jahr).
    - Nach Erfassung einmaliger Reload, damit Backend den Namen direkt für Lock-Labels nutzt.
  - `app.py`:
    - `_editor_identity()` nutzt nun zusätzlich:
      - POST-Feld `editor_name_manual` (falls vorhanden),
      - Cookie `rolemapper_editor_name` als Fallback,
      - weiterhin SSO/Proxy-Header mit höchster Priorität.

## v0.2.81
- Anfrage: Angemeldeten/erkannten Nutzer in der Lock-Nachricht anzeigen.
- Antwort: Umgesetzt.
- Änderungen:
  - `app.py`:
    - Nutzererkennung über gängige Proxy/SSO-Header ergänzt (`X-Forwarded-User`, `X-Auth-Request-User`, `Remote-User`, `REMOTE_USER`).
    - Lock-Label verwendet jetzt bevorzugt den erkannten Nutzernamen inkl. Rolle (`<user> (admin|localizer|user)`).
    - Fallback ohne Userheader: weiterhin Session-Label, ergänzt um Client-IP (`role-xxxxxx @ip`).
- Ergebnis:
  - Lock-Hinweise zeigen jetzt nachvollziehbarer, **wer** ein Mapping hält.

## v0.2.80
- Anfrage: Bearbeitungs-Lock direkt nach „Mapping speichern/aktualisieren“ freigeben und mehrsprachigen Hinweis anzeigen; TTL auf ca. 20 Minuten reduzieren.
- Antwort: Umgesetzt.
- Änderungen:
  - `app.py`:
    - Lock-TTL von 4h auf 20 Minuten reduziert (`MAPPING_LOCK_TTL_SECONDS = 20 * 60`).
    - Nach `save_mapping` wird der Lock direkt freigegeben.
    - Nach `update_mapping` wird der Lock direkt freigegeben.
    - Mehrsprachiger Hinweistext zur Lock-Freigabe ergänzt (DE/EN/IT/FR/PT/ES) und als Flash nach Save/Update angezeigt.
    - `update_mapping` lädt weiterhin den frisch gespeicherten Serverstand in die Hauptseite, aber ohne Lock erneut zu halten.

## v0.2.79
- Anfrage: Multi-User-Sperre so umsetzen, dass immer nur ein Benutzer ein Mapping gleichzeitig bearbeiten kann.
- Antwort: Umgesetzt (Code-basierter Edit-Lock).
- Änderungen:
  - `app.py`:
    - Locking-Infrastruktur ergänzt (`mapping_store/_locks`, TTL 4h).
    - Beim Laden eines Mapping-Codes (`GET load_mapping_code` + Action `mapping_plus_load`) wird exklusiver Lock geprüft/gesetzt.
    - Wenn ein Lock von einem anderen Benutzer gehalten wird, wird das Laden/Bearbeiten blockiert und ein Hinweis angezeigt.
    - Beim Start eines neuen lokalen Flows (CSV/TXT/Test/Dirty-Import) wird ein eigener aktiver Mapping-Lock freigegeben.
    - Beim Speichern eines neuen Mapping-Codes wird Lock auf den neuen Code übernommen.
    - Beim `update_mapping` wird Lock zwingend geprüft; Update bei Fremd-Lock blockiert.
    - Beim Logout wird der aktive Lock des Benutzers freigegeben.

## v0.2.78
- Anfrage: Auf der Hauptseite einen Button für eine AD/ORBIS-Rollenliste in einem extra Fenster ergänzen.
- Antwort: Umgesetzt.
- Änderungen:
  - `index.html`:
    - Neuer Button `Rollenliste anzeigen` neben dem AD/ORBIS-Filter.
    - Neues Modal/Fenster mit Liste aller aktuell geladenen AD/ORBIS-SOURCE-Rollen.
    - Anzeige enthält auch einen Zähler der gelisteten Rollen.
    - Schließen per Button oder Klick auf Overlay.
    - i18n-Keys für DE/EN/IT/FR/PT/ES ergänzt.

## v0.2.77
- Anfrage: Nach „Mapping am Server aktualisieren“ ist die Hauptseite leer; stattdessen sollen die aktualisierten Serverdaten direkt wieder angezeigt werden.
- Antwort: Behoben.
- Änderungen:
  - `app.py` (`submit_mode == update_mapping`):
    - Nach erfolgreichem Update erfolgt ein harter Reload via Redirect auf `/?load_mapping_code=<CODE>&lang=<ui_lang>`.
    - Dadurch wird die Hauptseite immer aus den frisch gespeicherten Serverdaten neu aufgebaut.
    - Schutz ergänzt: wenn beim Update keine SOURCE-Rollen im Formular ankommen, wird das Update abgebrochen (verhindert versehentlich leere Serverdaten).

## v0.2.76
- Anfrage: Zugewiesene Personas, DU-Berechtigungsrollen und individuelle Rollen rechts auf der Hauptseite mit kleinem Mülleimer zum einfachen Entfernen versehen.
- Antwort: Umgesetzt.
- Änderungen:
  - `index.html`:
    - In allen rechten Bucket-Zuweisungs-Pills wird automatisch ein kleines 🗑-Symbol eingeblendet.
    - Klick auf 🗑 entfernt die jeweilige Zuweisung direkt aus dem Bucket.
    - Styling für kleine Trash-Schaltfläche ergänzt.
    - Logik zentral über `ensureBucketPillDeleteButtons()` in die bestehende Bucket-Aktualisierung integriert.

## v0.2.74
- Anfrage: Persona-Tooltip erscheint nicht.
- Antwort: Behoben.
- Änderungen:
  - `index.html`:
    - Tooltip-Eventbindung von delegiertem `mouseover/mouseout` auf stabile direkte `mouseenter/mouseleave`-Bindings pro Persona-Pill umgestellt.
    - Dadurch zuverlässige Hover-Erkennung inkl. 3-Sekunden-Verzögerung.

## v0.2.73
- Anfrage: Auf der Hauptseite links bei Personas Tooltip mit den in der Persona-Konfiguration gemappten Rollen anzeigen (nach ca. 3 Sekunden Hover).
- Antwort: Umgesetzt.
- Änderungen:
  - `index.html`:
    - Persona-Pills im linken Pool tragen jetzt `data-persona-roles` mit den zugehörigen Rollen.
    - Neuer Tooltip-Mechanismus (`.persona-tooltip`) ergänzt.
    - Tooltip erscheint nach 3 Sekunden Hover auf einer Persona und zeigt:
      - Persona-Name
      - zugeordnete Rollen aus Persona-Konfiguration
    - Tooltip verschwindet beim Verlassen/Scrollen.

## v0.2.72
- Anfrage (Option B):
  - Bulk-Feature umsetzen (Drag&Drop auf alle aktuell sichtbaren Rollen).
  - Kundendaten-Bereich auf Stand v0.70 zurückführen.
- Antwort: Umgesetzt.
- Änderungen:
  - `index.html`:
    - Neuer Bulk-Drop-Bereich rechts: Rolle/Persona auf Zone ziehen → Zuweisung auf alle aktuell sichtbaren (gefilterten) AD/ORBIS-Rollen.
    - Duplikate werden pro Bucket verhindert.
    - Mehrsprachiger Hinweistext (`bulkAssignHint`) für DE/EN/IT/FR/PT/ES ergänzt.
  - Kundendaten:
    - Verhalten auf v0.70-Stand belassen (Inline-Bearbeitung in derselben Zeile mit `Ändern/OK`-Toggle; keine separate Bearbeitungszeile darunter).

## v0.2.71
- Anfrage: Bei Kundendaten soll „Ändern" die Werte direkt in derselben Zeile in Inputfelder umschalten (nicht separat darunter).
- Antwort: Umgesetzt und visuell zusammengeführt.
- Änderungen:
  - `index.html`:
    - Kundendatenzeile auf echten Inline-Edit-Modus umgestellt.
    - Pro Feld gibt es jetzt View (`strong`) + Edit (`input/select`) am selben Platz.
    - `Ändern/OK` blendet innerhalb derselben Zeile um.
    - Separates `metaEditPanel` darunter entfernt.

## v0.2.70
- Anfrage: PLZ-Feld im Inline-Kundendateneditor ebenfalls auf ca. 2/3 Länge verkleinern.
- Antwort: Umgesetzt.
- Änderungen:
  - `index.html`: `metaEditPostal` Breite reduziert (60px).

## v0.2.69
- Anfrage: Inline-Kundendatenfelder für Land, Kundennummer und Standort deutlich verkleinern (ca. 2/3), damit alles in einer Zeile bleibt.
- Antwort: Umgesetzt.
- Änderungen:
  - `index.html` (Inline-Editor Kundendaten):
    - `metaEditCountry` Breite reduziert (58px)
    - `metaEditCustomerNo` Breite reduziert (72px)
    - `metaEditSide` Breite reduziert (72px)

## v0.2.68
- Anfrage: Bei Kundendaten soll „Ändern“ die Felder direkt in derselben Infozeile editierbar machen (nicht in einer separaten Zeile darunter).
- Antwort: Umgesetzt.
- Änderungen:
  - `index.html`:
    - Separates Edit-Panel unter der Kundendatenzeile entfernt.
    - Inline-Edit in derselben Zeile umgesetzt:
      - Anzeige-Modus: Label + `strong` Werte
      - Edit-Modus: dieselben Positionen als Input/Select-Felder
    - `Ändern/OK` toggelt zwischen Anzeige- und Edit-Modus in derselben Zeile.

## v0.2.67
- Anfrage: Beim Kundendaten-Editor soll derselbe „Ändern“-Button in „OK“ wechseln und mit erneutem Klick die Bearbeitung beenden.
- Antwort: Umgesetzt.
- Änderungen:
  - `index.html`:
    - Separaten `OK`-Button im Kundendaten-Editor entfernt.
    - `Ändern`-Button als Toggle umgesetzt:
      - 1. Klick: wechselt zu `OK` und öffnet Editor.
      - 2. Klick: übernimmt Werte, schließt Editor, wechselt zurück zu `Ändern`.

## v0.2.66
- Anfrage: Kundendaten-Änderungen werden weiterhin nicht in der Anzeige übernommen.
- Antwort: Editor-Übernahme nochmals robuster umgesetzt.
- Änderungen:
  - `index.html`:
    - Neue zentrale Funktion `applyMetaEditorValues()` für direkte Übernahme in Hidden-Felder + Preview.
    - Live-Übernahme bereits beim Tippen/Ändern (`input` + `change`) im Kundendaten-Editor.
    - `OK` nutzt dieselbe zentrale Übernahmefunktion und schließt den Editor.

## v0.2.65
- Anfrage: Änderungen aus dem Kundendaten-Editor werden nicht in der Anzeige übernommen.
- Antwort: Behoben.
- Änderungen:
  - `index.html`:
    - `OK`-Handler des Kundendaten-Editors überarbeitet.
    - Werte werden nun explizit in Hidden-Felder geschrieben **und** sofort direkt in die read-only Anzeige (`countryPreview`, `postalPreview`, `cityPreview`, `customerNoPreview`, `sidePreview`, `customerPreview`) übernommen.
    - Danach zusätzlicher `syncCustomerPreview()`-Abgleich.

## v0.2.64
- Anfrage: Für die Kundendaten-Zusammenfassung im Mapping-Bereich einen Edit-Button wie bei AD/ORBIS-Rollen hinzufügen.
- Antwort: Umgesetzt.
- Änderungen:
  - `index.html`:
    - Im read-only Kundendatenblock unten rechts Button `Ändern` ergänzt.
    - Auf Klick öffnet sich ein Inline-Editor mit Feldern für Land/PLZ/Stadt/Kundennummer/Standort/Kunde.
    - `OK` übernimmt Werte in die Formular-Hidden-Felder und aktualisiert sofort die read-only Vorschau.

## v0.2.63
- Anfrage: Kundendaten-Anzeige war genau verkehrt herum umgesetzt; gewünscht ist Anzeige unten im Mapping-Bereich (read-only), nicht oben als editierbare Felder.
- Antwort: Korrigiert.
- Änderungen:
  - `index.html`:
    - Obere editierbare Kundendatenfelder entfernt.
    - Unten im rechten Mapping-Bereich wieder als read-only Zusammenfassung eingefügt.
    - Werte werden weiterhin über Hidden-Felder im Formular mitgeführt (für Speichern/Update/TXT-Flows).

## v0.2.62
- Anfrage: Kundendaten auf der Hauptseite nicht doppelt anzeigen (Bereich 1 + Bereich 2 im Screenshot).
- Antwort: Umgesetzt. Doppelte Anzeige im rechten Mapping-Bereich entfernt.
- Änderungen:
  - `index.html`:
    - Read-only Kundendaten-Zeile oberhalb der Source-Rollen entfernt.
    - Kundendaten bleiben als Eingabefelder nur im oberen Bereich (eine Stelle zur Pflege).

## v0.2.61
- Anfrage: Chinesisch aus sämtlichem Code, Templates und JSON entfernen.
- Antwort: Umgesetzt.
- Änderungen:
  - Entfernt in Templates:
    - `index.html`
    - `admin_mappings.html`
    - `changelog.html`
    - `config_i18n.html`
    - `config_persona_names.html`
    - `config_personas.html`
    - `config_roles.html`
    - `guide.html`
  - Entfernt in JSON:
    - `config/persona_descriptions.json` (`zh`-Einträge entfernt)
  - Sprachlisten bereinigt (`zh` aus JS-Arrays entfernt, wo vorhanden).

## v0.2.60
- Anfrage: Prüfen, ob die Kürzung von „Mapping (Drag & Drop)“ auf „Mapping" in allen Sprachen umgesetzt ist.
- Antwort: Ergänzt. Fehlende Sprachvarianten wurden nachgezogen.
- Änderungen:
  - `index.html` i18n `sec.mappingTitle` angepasst:
    - IT: `Mappatura`
    - FR: `Mapping`
    - PT: `Mapeamento`
    - ES: `Mapeo`
    - ZH: `映射`

## v0.2.59
- Anfrage: Titel „Mapping (Drag & Drop)" auf „Mapping" kürzen.
- Antwort: Umgesetzt.
- Änderungen:
  - `index.html`: Titeltext und i18n-Werte von „Mapping (Drag & Drop)" auf „Mapping" geändert.

## v0.2.58
- Anfrage: Button „Neu beginnen“ rechts neben „Mapping (Drag & Drop)“ platzieren.
- Antwort: Umgesetzt.
- Änderungen:
  - `index.html`:
    - Button `Neu beginnen` aus der unteren Aktionszeile in die Titelzeile der Mapping-Karte verschoben.

## v0.2.57
- Anfrage: „Jungfräulich beginnen“ in „Neu beginnen“ umbenennen.
- Antwort: Umgesetzt.
- Änderungen:
  - `index.html`: Button-Text angepasst.
  - `index.html` i18n (DE): `btn.freshStart` von „Jungfräulich beginnen“ auf „Neu beginnen“ geändert.

## v0.2.56
- Anfrage: Auf der Hauptseite einen Button, um „jungfräulich“ neu zu starten (wie frisch geladene Seite).
- Antwort: Umgesetzt. Neuer Button für frischen Start auf der Hauptseite ergänzt.
- Änderungen:
  - `index.html`:
    - Neuer Button `Jungfräulich beginnen` im Aktionsbereich der Mapping-Sektion.
    - Klick führt auf `/?lang=<aktuelle-sprache>` und setzt den UI-Zustand der Seite zurück.
    - i18n-Key `btn.freshStart` für DE/EN/IT/FR/PT/ES ergänzt.

## v0.2.55
- Anfrage: Auf der Hauptseite bleibt trotz `?lang=it` die Sprache deutsch.
- Antwort: Behoben. Ursache war ein JavaScript-Syntaxfehler in der FR-i18n-Zeile (`d'abord` nicht escaped), wodurch die gesamte i18n-Initialisierung auf der Hauptseite ausfiel.
- Änderungen:
  - `index.html`: Apostroph in FR-String korrekt escaped (`d'abord`).
- Ergebnis: `?lang=<code>` wird auf der Hauptseite wieder korrekt angewendet.

## v0.2.54
- Anfrage: Nur auf der Hauptseite springt die Sprache beim Seitenwechsel/Reload auf DE zurück.
- Antwort: Behoben. Die Hauptseite priorisiert jetzt korrekt die Sprache aus URL (`?lang=`), danach `localStorage`, dann Cookie.
- Änderungen:
  - `index.html`:
    - Initiale Sprachermittlung auf `langFromUrl -> langFromStorage -> langFromCookie -> de` umgestellt.
    - Initialisierung von `langSwitch` und allen `ui-lang-field` auf die ermittelte Sprache synchronisiert.
    - Restverwendung von `savedLang` auf `initialLang` korrigiert.

## v0.2.53
- Anfrage: Beim Seitenwechsel springt die App wieder auf DE zurück; Sprache soll beibehalten werden.
- Antwort: Behoben. Navigationslinks behalten die gewählte Sprache jetzt stabil beim Seitenwechsel.
- Änderungen:
  - `_sidebar.html`:
    - JS ergänzt, das alle internen Sidebar-Links automatisch mit `?lang=<aktuelle-sprache>` versieht.
    - Sprache wird aus `langSwitch`, `localStorage` und Cookie ermittelt (Fallback `de`).
    - Bei Sprachwechsel werden Sidebar-Links direkt neu gesetzt.

## v0.2.52
- Anfrage: Übersetzungen der Hauptseite prüfen.
- Antwort: Geprüft und Lücken im oberen Bereich geschlossen.
- Änderungen (i18n `index.html`):
  - IT/FR/PT/ES: fehlende Keys ergänzt
    - `postalLabel`, `postalPh`
    - `cityLabel`, `cityPh`
- Ergebnis: Sprachwechsel auf der Hauptseite ist für die oberen Eingabefelder konsistent.

## v0.2.51
- Anfrage: Übersetzungen im oberen Bereich passen nach Sprachwechsel nicht.
- Antwort: Behoben. Fehlende i18n-Keys für den neuen „Dirty Keycloak“-Einstieg wurden ergänzt.
- Änderungen:
  - `index.html` i18n:
    - Französisch: `sec.dirtyTitle` ergänzt.
    - Italienisch/Französisch/Portugiesisch/Spanisch: `dirtyPh` (Placeholder) ergänzt.

## v0.2.50
- Anfrage: Die vier Einstiegspunkte auf der Hauptseite sperren, sobald bereits Rollen im Drag&Drop-Kontext geladen sind, damit keine Kunden/Standorte vermischt werden.
- Antwort: Umgesetzt. Sobald ein Mapping-Kontext aktiv ist (`source_roles` vorhanden), werden die vier Einstiegsfunktionen deaktiviert.
- Änderungen:
  - `index.html`:
    - Neue Lock-Logik `entry_locked` basierend auf vorhandenem Mapping-Kontext.
    - Bereiche gesperrt: `mapping.txt importieren`, `Externe Authentifizierungsrollen`, `Dirty Keycloak importieren`, `Mapping laden`.
    - Relevante Inputs/Buttons erhalten `disabled`.
    - Zusätzlicher Hinweistext pro gesperrtem Einstieg (mehrsprachig DE/EN/IT/FR/PT/ES).
    - Disabled-Button-Styling ergänzt.

## v0.2.48
- Anfrage: Die vier Einstiegsoptionen oben sollen in einer Zeile stehen.
- Antwort: Umgesetzt. Das Grid im oberen Bereich wurde auf 4 Spalten umgestellt, sodass alle vier Karten nebeneinander erscheinen (bei ausreichend Breite).
- Änderungen:
  - `index.html`: `.grid` von 3 auf 4 Spalten (`repeat(4, minmax(0, 1fr))`) angepasst.

## v0.2.47
- Anfrage: Vierten Einstiegspunkt auf der Hauptseite ergänzen, um „dirty“ Keycloak-Zeilen per Textfeld zu importieren (`RoleMapper_<SOURCE>_to_<TARGET>`).
- Antwort: Umgesetzt. Es gibt jetzt den Bereich „Dirty Keycloak importieren“ mit Parser und direkter Vorbelegung der Mapping-Ansicht.
- Änderungen:
  - `index.html`:
    - Neue Karte „Dirty Keycloak importieren“ im oberen Bereich.
    - Textfeld + Import-Button ergänzt.
    - i18n-Keys für Titel/Button/Placeholder ergänzt.
  - `app.py`:
    - Neue Parser-Funktion `parse_dirty_keycloak_lines(...)`.
    - Neue Action `dirty_keycloak_import` im `index()`-POST-Flow.
    - Ergebnis: SOURCE-Rollen werden erkannt und direkt als Buckets/Vorbelegung geladen.

## v0.2.46
- Anfrage: JavaScript-Fehler auf der Hauptseite (`Unexpected identifier 'ont'`) beim Laden eines Mappings.
- Antwort: Behoben. Ursache war ein nicht escaptes Apostroph in der französischen i18n-Zeichenkette (`n'ont`, `n'apparaissent`), das das JS-Objekt ungültig machte.
- Änderungen:
  - `index.html`: Französische Zeichenkette für `warn.unmappedHeader` korrekt escaped (`n'ont`, `n'apparaissent`).

## v0.2.45
- Anfrage: „AD/ORBIS-Rollen filtern“ auf der Hauptseite funktioniert nicht mehr.
- Antwort: Filterlogik robuster gemacht. Die Suche filtert jetzt gezielt innerhalb des Rollen-Wrappers und berücksichtigt sowohl `data-source-row` als auch den sichtbaren Rollennamen.
- Änderungen:
  - `index.html`:
    - `applySourceRoleFilter()` auf robustere Selektion/Matching umgestellt.
    - Eventbindung erweitert (`input` + `keyup`) für zuverlässige Aktualisierung.

## v0.2.44
- Anfrage: In `/api/mapping-codes` zusätzlich das Mapping im JSON zurückgeben.
- Antwort: Umgesetzt. Jeder Eintrag enthält jetzt zusätzlich `mapping` als Liste der Mapping-Zeilen.
- Änderungen:
  - `api_mapping_codes()` liest pro Code `mappingplus-<CODE>.txt` und liefert:
    - `mapping`: Array mit Zeileninhalt

## v0.2.43
- Anfrage: In `GET /api/mapping-codes` keine separaten `client_ts`/`server_ts` ausgeben; nur einen Zeitstempel der letzten Änderung.
- Antwort: Umgesetzt. Die API liefert jetzt nur noch `updated_ts` pro Eintrag.
- Änderungen:
  - `api_mapping_codes()` gibt jetzt ein kompaktes Entry-Format zurück mit:
    - `code`, Kundendatenfelder, `line_count`, `updated_ts`
  - `updated_ts` wird priorisiert aus `client_ts`, sonst `server_ts` befüllt.
  - Felder `client_ts` und `server_ts` entfallen in der API-Antwort.

## v0.2.42
- Anfrage: JSON-Ausgabe von `GET /api/mapping-codes` leserlich formatieren.
- Antwort: Umgesetzt. Die API liefert jetzt Pretty-Printed JSON (Einrückung) statt kompakter Ein-Zeilen-Ausgabe.
- Änderungen:
  - `api_mapping_codes()` nutzt jetzt `json.dumps(..., indent=2, ensure_ascii=False)` über `app.response_class`.

## v0.2.41
- Anfrage: API ergänzen, die alle serverseitig gespeicherten Mapping-Codes als JSON zurückliefert.
- Antwort: Umgesetzt. Es gibt jetzt eine dedizierte Codes-API mit kompletter Liste und Metadaten.
- Änderungen:
  - Neue Route: `GET /api/mapping-codes`
    - Antwort enthält:
      - `count` (Anzahl)
      - `codes` (nur Codes)
      - `entries` (Codes + Basis-Metadaten aus Server-Mappings)

## v0.2.40
- Anfrage: Den externen Ladepfad `https://FQDN/?load_mapping_code=<Mappingcode>` in Code und „Permanente Systembeschreibung“ API-basiert abbilden.
- Antwort: Umgesetzt. Es gibt jetzt eine dedizierte API zum Laden eines gespeicherten Mappings per Code.
- Änderungen:
  - Neue API-Route: `GET /api/mapping-load/<code>`
    - liefert Mapping + Metadaten als JSON
    - enthält zusätzlich `ui_load_url` für die bestehende UI-Kompatibilität
  - „Permanente Systembeschreibung“ aktualisiert:
    - externer Zugriff jetzt primär über `GET /api/mapping-load/<Mappingcode>` beschrieben

## v0.2.39
- Anfrage: Kundendaten-Struktur von `side` auf `site` umstellen und bestehende Server-Mappings nachziehen.
- Antwort: Umgesetzt. Die Metadaten speichern jetzt `site` statt `side`; bestehende Mapping-Metadaten wurden serverseitig migriert.
- Änderungen:
  - `app.py`:
    - Speichern: schreibt Feld `site` in Mapping-Metadaten.
    - Laden/Listen: liest `site` mit Fallback auf `side` (rückwärtskompatibel).
    - API `/api/mapping-init`: akzeptiert `site` (Fallback `side`).
  - Datenmigration:
    - Vorhandene `mapping_store/mappingplus-*.json` wurden nachgezogen (`side` -> `site`).

## v0.2.38
- Anfrage: Zwei API-Schnittstellen bereitstellen: (1) Download der mapping.txt mit Dateinamen `mapping-<Code>.txt`, (2) automatisches Anlegen der Kundendaten-Struktur auf dem Server (ähnlich Laden per `/?load_mapping_code=<Code>`).
- Antwort: Umgesetzt. Es gibt jetzt eine Download-API mit gewünschtem Dateinamen und eine Init-API zum serverseitigen Anlegen der Mapping-/Kundendaten-Struktur.
- Änderungen:
  - Neue Route: `GET /api/mapping-download/<code>`
    - liefert Mapping als Download mit Name `mapping-<CODE>.txt`
  - Neue Route: `POST /api/mapping-init`
    - legt Server-Struktur an (auch ohne Mapping-Zeilen)
    - akzeptiert Kundendatenfelder (`country`, `postal_code`, `city`, `customer_no`, `side`, `customer`)
    - optional `source_roles`
    - Antwort enthält `code`, `load_url`, `download_url`

## v0.2.37
- Anfrage: Spalte „Löschen“ in Server-Mappings für nicht angemeldete Benutzer komplett ausblenden.
- Antwort: Umgesetzt. Die komplette Lösch-Spalte wird jetzt nur noch für Admins gerendert.
- Änderungen:
  - `admin_mappings.html`:
    - Tabellenkopf „Löschen“ nur bei `auth_admin`.
    - Zellen mit Löschbutton nur bei `auth_admin`.
    - `colspan` der Leerzeile dynamisch angepasst (Admin: 12, sonst: 11).

## v0.2.36
- Anfrage: Das Aussehen des roten Löschen-Buttons aus „Server-Mappings“ auf alle Seiten mit Löschen-Buttons übernehmen.
- Antwort: Umgesetzt. Das Danger-Button-Styling wurde vereinheitlicht.
- Änderungen:
  - `config_roles.html` und `config_persona_names.html`:
    - `.btn-danger` auf das gleiche rot/hellrot-Styling wie in Server-Mappings umgestellt.
  - `index.html`:
    - rechter Bereich (`.source-del-btn`) auf das gleiche Danger-Styling gebracht.

## v0.2.35
- Anfrage: Der Löschen-Button soll optisch wie `class="btn-danger delete-row"` wirken (kräftiger rot).
- Antwort: Umgesetzt. Der Button nutzt jetzt genau diese Klassenkombination und ein eigenständiges Danger-Styling.
- Änderungen:
  - `admin_mappings.html`:
    - Buttonklasse auf `btn-danger delete-row` geändert.
    - JS-Selector von `.delete-row-btn` auf `.delete-row` angepasst.
    - `.btn-danger` als eigenständiger Button-Stil (Padding, Border, Hover) definiert.

## v0.2.34
- Anfrage: Für den Löschbutton bitte den Übersetzungsschlüssel `persona_names.delete` verwenden.
- Antwort: Umgesetzt. Der Löschbutton in „Server-Mappings“ nutzt jetzt den bestehenden i18n-Key `persona_names.delete` statt eines separaten Textschlüssels.
- Änderungen:
  - `admin_mappings.html`:
    - `data-i18n` von `server.btnDelete` auf `persona_names.delete` umgestellt.

## v0.2.33
- Anfrage: Löschbutton in „Server-Mappings“ rot einfärben wie die anderen Löschen-Buttons in der Anwendung.
- Antwort: Umgesetzt. Der Löschbutton in der Tabellen-Spalte „Löschen“ nutzt jetzt ein rotes Danger-Styling.
- Änderungen:
  - `admin_mappings.html`:
    - Neue CSS-Klasse `.btn-danger` (rote Farben, roter Hover).
    - Löschbutton pro Zeile auf `class="btn btn-danger delete-row-btn"` umgestellt.

## v0.2.32
- Anfrage: Löschen nicht im Popup, sondern als eigene Spalte direkt in der Server-Mappings-Liste.
- Antwort: Umgesetzt. In der Tabelle „Server-Mappings“ gibt es jetzt eine separate Spalte „Löschen“ mit Button pro Eintrag (nur für Admin).
- Änderungen:
  - `admin_mappings.html`:
    - Neue Spalte `server.colDelete` + Button `server.btnDelete` pro Tabellenzeile.
    - Mehrsprachige Texte für DE/EN/IT/FR/PT/ES ergänzt.
    - Client-Handler ergänzt: Löschen mit Bestätigung und sofortigem Entfernen der Tabellenzeile.
  - `app.py`:
    - Neue Admin-Route `POST /admin-mappings-delete-code`.
    - Löscht Mapping-Dateien (`mappingplus-<code>.txt` und `.json`) eines Eintrags vollständig.

## v0.2.31
- Anfrage: In „Server-Mappings“ ist in den Zeilen kein Löschbutton sichtbar.
- Antwort: Behoben. Im Popup-Renderer fehlte die Berechnung der Indexliste für gefilterte Zeilen (`filteredIndices`), wodurch die Zeilen-Action fehlschlug und der Löschen-Button nicht korrekt angezeigt wurde.
- Änderungen:
  - `admin_mappings.html`: `render()` korrigiert:
    - `filteredIndices` wird jetzt beim Filtern aufgebaut
    - Löschbutton kann den korrekten Zeilenindex wieder verwenden

## v0.2.30
- Anfrage: Login funktioniert nicht mehr.
- Antwort: Robustheits-Fix umgesetzt. Zusätzlich zur JS-Modal-Anmeldung gibt es jetzt eine direkte Login-Seite als Fallback ohne JavaScript.
- Änderungen:
  - Neue Template-Seite: `templates/login.html`
  - Route `/login` rendert nun ein echtes Login-Formular (Admin/Lokalisierer + Sprache + Passwort).
  - Hauptseite: Login-Link zeigt auf `/login` statt `#`.
  - Ergebnis: Anmeldung funktioniert auch dann, wenn clientseitiges JS (Modal) ausfällt.

## v0.2.29
- Anfrage: "Generated file:" ist nicht übersetzt.
- Antwort: Behoben. Die Dateizeile in der Warnbox wird jetzt über Frontend-i18n gerendert, statt als serverseitig vorbereiteter Text.
- Änderungen:
  - `index.html`: Neuer i18n-Key `warn.generatedFile` für die Dateiname-Zeile.
  - `app.py`: Übergibt nur noch den Dateinamen (`unmapped_warning_filename`) statt eines bereits lokalisierten Kompletttexts.

## v0.2.28
- Anfrage: In der Warnung zu fehlenden Mappings statt „TXT“ den tatsächlich erzeugten Dateinamen anzeigen.
- Antwort: Umgesetzt. Die Warnbox zeigt jetzt zusätzlich die konkret erzeugte Datei an (mehrsprachig).
- Änderungen:
  - `app.py`:
    - Neue Helper-Funktion `build_unmapped_roles_file_line(lang, filename)`.
    - Nach `save_output(...)` wird die Dateiname-Zeile gesetzt und ans Template übergeben.
  - `index.html`:
    - Warnbox zeigt unter der Überschrift jetzt die erzeugte Datei (`unmapped_warning_file_line`).

## v0.2.27
- Anfrage: Die formatierte Warnung für fehlende Mappings berücksichtigt die Sprache nicht.
- Antwort: Behoben. Die Warn-Überschrift wird jetzt über i18n-Schlüssel im Frontend übersetzt und die Sprachermittlung im POST-Flow wurde robuster gemacht.
- Änderungen:
  - `index.html`:
    - Warn-Überschrift auf `data-i18n="warn.unmappedHeader"` umgestellt.
    - Übersetzungen für DE/EN/IT/FR/PT/ES ergänzt.
  - `app.py`:
    - `ui_lang`-Ermittlung im POST-Flow robust gemacht (Form → Cookie → Fallback `de`).

## v0.2.26
- Anfrage: Meldung über fehlende Mappings besser formatieren.
- Antwort: Umgesetzt. Der Hinweis wird jetzt als klar strukturierter Warnblock mit Überschrift und Rollenliste angezeigt.
- Änderungen:
  - `index()`:
    - Übergibt `unmapped_warning_roles` + sprachabhängige Überschrift an das Template.
  - `index.html`:
    - Neuer formatierter Hinweisblock (orange) mit `<ul>`-Liste der betroffenen Rollen.

## v0.2.24
- Anfrage: Wenn AD/ORBIS-Rollen über „Mapping beginnen“ geladen werden, sollen sie beim Speichern erhalten bleiben – auch ohne zugewiesenes Mapping. Aktuell werden sonst nur Kundendaten gespeichert.
- Antwort: Umgesetzt. Beim Server-Speichern werden die Quellrollen jetzt zusätzlich in den Mapping-Metadaten abgelegt. Beim Laden werden diese Rollen auch dann wiederhergestellt, wenn noch keine `SOURCE=TARGET`-Zeilen vorhanden sind.
- Änderungen:
  - `save_mapping_plus(...)` erweitert um `source_roles`.
  - Metadaten (`mappingplus-*.json`) enthalten jetzt `source_roles`.
  - `load_mapping_plus_bundle(...)` ergänzt: Wenn TXT keine Mapping-Zeilen enthält, werden Quellrollen aus `source_roles` als leere Buckets rekonstruiert.
  - Aufrufe bei `save_mapping` und `update_mapping` übergeben jetzt die aktuellen `source_roles`.

## v0.2.23
- Anfrage: Begriff „Side“ in der Anwendung auf „Standort“ umstellen und alle Sprachen berücksichtigen.
- Antwort: Umgesetzt. Die UI-Bezeichnung wurde mehrsprachig angepasst.
- Änderungen:
  - `index.html`:
    - `sideLabel` / `sidePh` in aktiven Sprachen angepasst:
      - DE: Standort
      - EN: Location
      - IT: Sede
      - FR: Site
      - PT: Local
      - ES: Ubicación
    - Standard-Placeholder/Label auf Hauptseite ebenfalls aktualisiert.
  - `admin_mappings.html`:
    - Spaltenbezeichnung `server.colSide` mehrsprachig angepasst.
    - Popup-Kundeninfos verwendet jetzt lokalisierte Side-Bezeichnung über `server.colSide`.

## v0.2.22
- Anfrage: „AD/ORBIS-Rollen filtern:“ und das Inputfeld sollen in einer Zeile stehen.
- Antwort: Umgesetzt. Label und Suchfeld sind jetzt horizontal in einer Zeile ausgerichtet (mit responsivem Umbruch bei kleinen Breiten).
- Änderungen:
  - `index.html`: Filter-Container auf `display:flex` umgestellt; Label + Input inline ausgerichtet.

## v0.2.21
- Anfrage: Suchmaske für AD/ORBIS-Rollen rechts nicht so breit. Zusätzlich vor dem Inputfeld den Text „AD/ORBIS-Rollen filtern:“ anzeigen. Mehrsprachigkeit beachten.
- Antwort: Umgesetzt. Das Suchfeld im rechten Bereich wurde schmaler gemacht und um ein mehrsprachiges Label oberhalb des Feldes ergänzt.
- Änderungen:
  - `index.html`:
    - Label vor Suchfeld ergänzt: `sourceRolesFilterLabel`
    - Suchfeldbreite angepasst auf `width: 420px; max-width: 100%`
    - i18n-Keys für Label + Placeholder ergänzt/erweitert für aktive Sprachen (DE/EN/IT/FR/PT/ES)

## v0.2.20
- Anfrage: Auf der Hauptseite rechts eine Suchmaske für AD-/ORBIS-Rollen ergänzen und die Liste auf Treffer reduzieren.
- Antwort: Umgesetzt. Im rechten Bereich gibt es jetzt ein Suchfeld für die Quellrollen. Die Rollen-Buckets werden beim Tippen live gefiltert, sodass nur passende Treffer sichtbar bleiben.
- Änderungen:
  - `index.html`:
    - Neues Inputfeld `sourceRolesSearch` im rechten Bereich ergänzt.
    - Live-Filterlogik `applySourceRoleFilter()` für `.source-bucket-row` ergänzt.
    - Filter wird nach Hinzufügen/Umbenennen/Löschen von Quellrollen automatisch neu angewendet.
    - i18n Placeholder ergänzt (DE/EN).

## v0.2.19
- Anfrage: Server-Mappings sollen ebenfalls im Konfigurations-Backup enthalten sein.
- Antwort: Umgesetzt. Das ZIP-Backup enthält jetzt zusätzlich den kompletten `mapping_store` (gespeicherte Server-Mappings inkl. Metadaten und TXT-Inhalt).
- Änderungen:
  - `download_config_backup()` erweitert:
    - `mapping_store/mappingplus-*.json`
    - `mapping_store/mappingplus-*.txt`
  - `BACKUP_INFO.json` listet jetzt die vollständigen Archivpfade (`config/...`, `mapping_store/...`).

## v0.2.18
- Anfrage: In „Konfiguration“ einen Button bereitstellen, der ein ZIP-Backup für Persona-Konfiguration, Persona-Liste, Rollenliste und Lokalisierungstexte automatisch herunterlädt.
- Antwort: Umgesetzt. In der Konfigurationsseite gibt es jetzt einen dedizierten Backup-Bereich mit Download-Button. Der Download erzeugt eine ZIP-Datei mit allen relevanten Konfigurationsdateien.
- Änderungen:
  - Neue Route: `/download/config-backup`
    - Erstellt ein ZIP mit:
      - `personas.json`
      - `persona_names.json`
      - `persona_descriptions.json`
      - `roles_column_a.json`
      - `role_descriptions.json`
      - `i18n_overrides.json`
      - `app_settings.json`
      - `sample_roles.json`
      - `BACKUP_INFO.json` (Metadaten)
  - Auth-Guard erweitert: Route ist admin-geschützt.
  - `config_auth.html`:
    - Neuer Bereich „Konfigurations-Backup“ inkl. Download-Button.
    - Mehrsprachige Labels/Hinweise (DE/EN/IT/FR/PT/ES).

## v0.2.17
- Anfrage: Den Button „Löschen“ im rechten Bereich weiter nach rechts platzieren, damit man ihn nicht versehentlich anklickt.
- Antwort: Umgesetzt. In der Quellrollen-Zeile wurde „Löschen“ optisch nach ganz rechts geschoben; „Ändern“ bleibt links neben dem Rollennamen.
- Änderungen:
  - `index.html`:
    - Quellrollen-Header um Spacer ergänzt (`source-action-spacer`).
    - `source-del-btn` mit rechter Ausrichtung (`margin-left:auto`).
    - Gilt für bestehende und dynamisch hinzugefügte Quellrollen.

## v0.2.16
- Anfrage: Nach Klick auf „OK“ bleibt das Inputfeld weiterhin bearbeitbar.
- Antwort: Fehler behoben. Ursache war eine zu frühe Prüfung auf `.source-role-name`, die im Edit-Modus nicht mehr existiert und den Save-Teil blockiert hat.
- Änderungen:
  - `index.html` (rechter Bereich / Inline-Edit):
    - Prüfung auf `.source-role-name` nur noch beim Einstieg in den Edit-Modus.
    - Save-Zweig (`OK`) läuft nun korrekt durch und ersetzt das Inputfeld wieder durch den sichtbaren Rollennamen.

## v0.2.15
- Anfrage: Bei Klick auf „OK“ soll das Inputfeld verschwinden, der Rollenname aber sichtbar bleiben.
- Antwort: Umgesetzt. Der Inline-Edit wird jetzt in jedem Fall sauber beendet: Beim Klick auf `OK` wird das Eingabefeld wieder in den sichtbaren Rollennamen zurückgewandelt.
- Änderungen:
  - `index.html` (rechter Bereich / Inline-Edit):
    - Leere Eingabe führt nicht mehr zum „hängenbleibenden“ Inputfeld.
    - Fallback auf bisherigen Namen (`oldName`), danach Rückbau auf Label-Ansicht.

## v0.2.14
- Anfrage: Beim Inline-Umbenennen im rechten Bereich den Buttontext von „Speichern“ auf „OK“ ändern, da noch nichts final gespeichert wird.
- Antwort: Umgesetzt. Der Inline-Button zeigt im Edit-Modus jetzt „OK“ statt „Speichern“.
- Änderungen:
  - `index.html`: Buttontextwechsel im Quellrollen-Inline-Edit von `Speichern` auf `OK`.

## v0.2.13
- Anfrage: Im rechten Bereich soll beim Umbenennen kein Popup mehr erscheinen; die Bezeichnung soll direkt zur Inputbox werden.
- Antwort: Umgesetzt. Das Umbenennen der Quellrolle erfolgt jetzt inline im Rollen-Header statt per Prompt-Dialog.
- Änderungen:
  - `index.html` (rechter Bereich, Quellrollen):
    - Klick auf `Ändern` schaltet den Rollennamen in ein Eingabefeld um.
    - Buttontext wechselt auf `Speichern`.
    - Enter speichert, Escape bricht ab und stellt den alten Namen wieder her.
    - Nach Speichern werden wie bisher Hidden-Input, Bucket-Attribute und Copy-Selects konsistent aktualisiert.

## v0.2.12
- Anfrage: Korrektur zur letzten Änderung: Bearbeiten/Löschen soll im rechten Bereich der Hauptseite gelten (LDAP/ORBIS-Quellrollen-Buckets), nicht im linken Rollenpool. Linke Änderung bitte zurücknehmen.
- Antwort: Umgesetzt. Die Buttons im linken Rollenbereich wurden zurückgenommen. Stattdessen gibt es jetzt im rechten Bereich pro Quellrolle die Aktionen „Ändern“ und „Löschen“ direkt am Rollen-Header.
- Änderungen:
  - `index.html`:
    - Linker Rollenpool wieder ohne Bearbeiten/Löschen-Buttons.
    - Rechter Bereich (`source-bucket-row`) erweitert um Buttons:
      - `Ändern`: benennt die Quellrolle um (inkl. Update von Hidden-Input, Bucket-Attributen und Copy-Selects)
      - `Löschen`: entfernt die komplette Quellrolle inkl. zugehörigem Hidden-Input
    - Dynamisch neu hinzugefügte Quellrollen erhalten dieselben Buttons.

## v0.2.11
- Anfrage: Auf der linken Hauptseite (Rollenbereich) soll es pro Rolle die Möglichkeit geben, den Namen nur per Klick auf einen „Ändern“-Button zu bearbeiten oder die Rolle über einen „Löschen“-Button zu entfernen.
- Antwort: Umgesetzt. Für Rollen in der linken Auswahlliste wurden explizite Aktionen ergänzt: umbenennen per Button und löschen per Button. Die Funktionen gelten auch für den Bereich „Individuelle Rollen“.
- Änderungen:
  - `index.html`:
    - Rollen in den Pool-Bereichen als `pool-item` mit Aktionsbuttons dargestellt (`Ändern`, `Löschen`).
    - JS-Logik ergänzt für:
      - Umbenennen einer Rolle per Button (Duplikatprüfung im jeweiligen Pool)
      - Löschen einer Rolle per Button
      - automatische Aktualisierung der Unknown-Markierung nach Änderungen
    - Suchfilter für Rollen auf `pool-item`-Darstellung angepasst.

## v0.2.10
- Anfrage: Nach „Mapping am Server aktualisieren“ soll die Hauptseite den tatsächlich aktuell gespeicherten Stand des Mappings anzeigen.
- Antwort: Umgesetzt. Nach dem Update wird das Mapping jetzt sofort erneut aus dem Server-Store geladen und die Hauptseite mit den persistierten Daten (inkl. Metadaten) neu befüllt.
- Änderungen:
  - `index()` / `submit_mode == "update_mapping"`:
    - Nach `save_mapping_plus(...)` erfolgt ein `load_mapping_plus_bundle(existing_code)`.
    - `source_roles`, `prefill_personas`, `prefill_roles`, `mapping_loaded_from_server` und Metadatenfelder werden aus dem Reload gesetzt.

## v0.2.9
- Anfrage: Trotz vorherigem Fix wird im Extrafenster weiterhin keine Mappingliste angezeigt.
- Antwort: Tiefgreifend behoben. Die Popup-Erzeugung wurde von einem komplexen `document.write`-Inline-Script auf eine robuste DOM-basierte Darstellung umgestellt. Dadurch entfallen String-/Escaping-Probleme, die das Rendering der Liste verhindern konnten.
- Änderungen:
  - `admin_mappings.html`:
    - Popup wird jetzt als leeres Dokument geöffnet und anschließend per DOM API aufgebaut.
    - Mappingzeilen werden direkt als DOM-Elemente gerendert (`textContent`), inkl. Live-Suche und Trefferzähler.
    - Kundeninfos + Mappingbereich bleiben visuell getrennt.

## v0.2.8
- Anfrage: Das Textfeld mit den Mappings wird im Extrafenster nicht angezeigt.
- Antwort: Behoben. Ursache war die Einbettung des Mapping-Textes in ein JavaScript-Stringliteral im Popup; bestimmte Inhalte konnten das Script brechen. Der Inhalt wird jetzt robust per `JSON.stringify(...)` eingebettet und anschließend zeilenweise gerendert.
- Änderungen:
  - `admin_mappings.html` Popup-Script angepasst:
    - Mapping-Inhalt via `const raw = ${JSON.stringify(data.content || '')}`
    - stabile Aufteilung in Zeilen und Darstellung in der Trefferliste

## v0.2.7
- Anfrage: Wenn keine Suchanfrage im Extrafenster vorliegt, soll die komplette Liste angezeigt werden. Außerdem ist das Suchfeld im Extrafenster zu lang.
- Antwort: Umgesetzt. Die Suche behandelt jetzt Leerzeichen korrekt (Trim), sodass bei leerer Eingabe wieder die vollständige Liste angezeigt wird. Zusätzlich wurde die Suchfeld-Breite reduziert.
- Änderungen:
  - `admin_mappings.html` (Popup):
    - Suchwert wird vor dem Filtern getrimmt (`trim()`), damit „leer“ wirklich alle Zeilen zeigt.
    - Suchfeldbreite angepasst von `width:100%` auf `width:360px; max-width:100%`.

## v0.2.6
- Anfrage: Mappingliste im Extrafenster durchsuchbar machen und die Anzeige auf Suchtreffer reduzieren.
- Antwort: Umgesetzt. Das Extrafenster enthält jetzt ein Suchfeld, das die angezeigten Mapping-Zeilen live filtert. Es werden nur Treffer angezeigt.
- Änderungen:
  - `admin_mappings.html` Popup erweitert um:
    - Suchfeld `mapSearch`
    - dynamische Trefferliste `mapList`
    - Trefferzähler `Treffer: x / y`
  - Live-Filter über alle Mapping-Zeilen per `input`-Event.

## v0.2.5
- Anfrage: Der Link in der Spalte „Zeilen“ soll als Button angezeigt werden; der Text soll weiterhin die Zeilenanzahl sein.
- Antwort: Umgesetzt. Der klickbare Zeilenwert wird jetzt im gleichen Button-Stil wie die übrigen Aktionen dargestellt. Die Beschriftung bleibt die jeweilige Zeilenanzahl.
- Änderungen:
  - `admin_mappings.html`: `lines-link` in der Spalte `Zeilen` zusätzlich mit Klasse `btn` versehen.

## v0.2.4
- Anfrage: Im Extrafenster beim Klick auf die Zeilenzahl sollen oben zusätzlich die Kundeninformationen angezeigt werden; optisch getrennt vom Mapping-Inhalt.
- Antwort: Umgesetzt. Das Popup zeigt jetzt einen separaten Bereich „Kundeninformationen“ oberhalb des eigentlichen Mapping-Textes.
- Änderungen:
  - `admin_mappings.html`:
    - Zeilen-Link um Metadaten ergänzt (Land, PLZ, Stadt, Kundennummer, Side, Kunde).
    - Popup-Layout angepasst: zwei klar getrennte Boxen
      1) Kundeninformationen
      2) Inhalt des Mappings

## v0.2.3
- Anfrage: Beim Klick auf die Zeilenzahl in „Server-Mappings“ erscheint „Mapping-Inhalt konnte nicht geladen werden.“
- Antwort: Behoben. Die neue JSON-Route für den Mapping-Inhalt nutzte `jsonify`, aber der Import fehlte in `app.py`. Dadurch schlug der Request serverseitig fehl und im Frontend erschien die generische Fehlermeldung.
- Änderungen:
  - `app.py`: Flask-Import ergänzt um `jsonify`.
  - Ergebnis: Klick auf die Zeilenzahl lädt den Mapping-Inhalt wieder korrekt im neuen Fenster.

## v0.2.2
- Anfrage: In „Server-Mappings“ soll die Spalte „Zeilen“ als Link funktionieren. Beim Klick soll ein extra Fenster mit dem Inhalt des Mappings der gewählten Zeile geöffnet werden.
- Antwort: Umgesetzt. Die Zeilenzahl ist jetzt klickbar und öffnet ein neues Fenster mit dem vollständigen Mapping-Text für den ausgewählten Code.
- Änderungen:
  - `admin_mappings.html`:
    - Spalte `Zeilen` als klickbarer Link (`.lines-link`) umgesetzt.
    - JS ergänzt: Klick lädt Mapping-Inhalt und öffnet neues Fenster mit formatiertem Text.
    - Mehrsprachige Meldungen für Popup-Titel/Fehler ergänzt (DE/EN/IT/FR/PT/ES).
  - `app.py`:
    - Neue Route `/mapping-plus-content/<code>` (JSON-Antwort mit Mapping-Inhalt).

## v0.2.1
- Anfrage: In „Mapping (Drag & Drop)“ sollen „DU Berechtigungsrollen“ zuklappbar sein. Zusätzlich ein dritter Abschnitt „Individuelle Rollen“, in den rot markierte (nicht passende) Rollen automatisch landen. Dieser Abschnitt soll ebenfalls zuklappbar sein. Außerdem sollen Rollen per Copy&Paste hinzugefügt werden können und in der Auswahl erscheinen. Personas sollen zur besseren Unterscheidung in einem Grünton dargestellt werden.
- Antwort: Umgesetzt. Die linke Mapping-Seite wurde in drei klar unterscheidbare, klappbare Bereiche erweitert (Personas, DU Berechtigungsrollen, Individuelle Rollen). Unbekannte Rollen aus dem rechten Bereich werden jetzt automatisch in den neuen Bereich „Individuelle Rollen“ übernommen und bleiben dort für weitere Zuordnungen verfügbar. Zusätzlich können individuelle Rollen per Copy&Paste ergänzt werden. Personas sind visuell auf Grün umgestellt, damit die Trennung zu Rollen schneller erkennbar ist.
- Änderungen:
  - Linke Mapping-Spalte erweitert:
    - `DU Berechtigungsrollen` zuklappbar
    - neuer Abschnitt `Individuelle Rollen` (zuklappbar)
  - Auto-Sammlung unbekannter Rollen:
    - rote Rollen (`data-known="0"`) aus Buckets werden automatisch in `Individuelle Rollen` übernommen
  - Manuelle Ergänzung individueller Rollen:
    - Textarea + „Rollen hinzufügen“
    - Unterstützung für Eingaben je Zeile, Komma oder Semikolon
  - Personas visuell hervorgehoben:
    - Persona-Pills in Grünton für bessere Unterscheidung

## v0.2.0 (Pre-Release)
- Anfrage: Diese Version als Pre-Release 0.2 markieren. Sichtbaren roten Hinweis „Testversion not for production“ ergänzen. Für zukünftige Änderungen auf Versionsschema `0.2.x` umstellen.
- Antwort: Umgesetzt. Die App ist jetzt auf `v0.2.0` gesetzt und zeigt in der Kopfzeile einen klar sichtbaren roten Testhinweis an. Das Versionsschema wird ab jetzt auf `0.2.x` fortgeführt, wobei `x` pro Änderung weiter inkrementiert wird.
- Änderungen:
  - `APP_VERSION` auf `0.2.0` gesetzt.
  - Roter Hinweistext in Header integriert: `Testversion not for production`.
  - Gültig für Hauptseite und Seiten mit gemeinsamem Header-Partial.

### Nachtrag ohne Versionssprung
- Deployment Bundle ZIP: Download robust gemacht, auch wenn Compose-/Dockerfile-Dateien auf externen Nodes fehlen (Fallback-Inhalte werden erzeugt).
- Changelog als PDF: bleibt weiterhin verfügbar; Changelog-Inhalt wird wie bisher aus Standard-/Fallback-Quelle geladen.
- Flash-Fehler "Deployment bundle files not found..." wird in diesem Fall nicht mehr erzeugt.

## v0.1.172
- Anfrage: Der Button „Mapping am Server aktualisieren“ auf der Hauptseite soll nur bei serverseitig geladenem Mapping sichtbar sein. Außerdem soll vor dem Speichern auf dem Server geprüft werden, ob Land, PLZ, Stadt, Side und Kunde belegt sind; sonst Warnung (mehrsprachig), kein Speichern, aber Seiteninhalt beibehalten.
- Antwort: Umgesetzt. Die Sichtbarkeit des Update-Buttons wurde an den Zustand „Mapping vom Server geladen“ gebunden. Zusätzlich gibt es jetzt eine verpflichtende Metadaten-Prüfung vor Server-Speichervorgängen (`save_mapping`/`update_mapping`). Bei fehlenden Feldern wird nur eine lokalisierte Warnung angezeigt; die aktuelle Zuordnung auf der Hauptseite bleibt vollständig erhalten.
- Änderungen:
  - `index.html`: Button „Mapping am Server aktualisieren“ nur noch sichtbar bei `mapping_loaded_from_server = true`.
  - `app.py`: Validierung vor Server-Speichern ergänzt für Pflichtfelder:
    - Land
    - PLZ
    - Stadt
    - Side
    - Kunde
  - Neue mehrsprachige Meldung `metaRequired` in den i18n-Defaults (DE/EN/IT/FR/PT/ES).

## v0.1.171
- Anfrage: Nach dem letzten Fix erscheint jetzt generell eine Anmeldemaske beim Laden der Seite.
- Antwort: Behoben. Die Login-Challenge-Daten (`login_scope/login_next/login_lang`) wurden bisher in der Session stehen gelassen und dadurch bei jedem weiteren Aufruf der Hauptseite erneut als Modal getriggert. Die Challenge wird jetzt als One-Shot behandelt: einmal anzeigen, danach aus der Session entfernen.
- Änderungen:
  - `index()` angepasst:
    - Login-Challenge-Werte werden zunächst lokal gelesen
    - nach GET-Rendern aus der Session entfernt
  - Ergebnis: Kein dauerhaftes Anmelde-Modal mehr auf jeder Seitenladung; Challenge erscheint nur noch einmal pro tatsächlicher Schutz-Umleitung.

## v0.1.170
- Anfrage: Bitte prüfen — auf „Lokalisierungstexte bearbeiten“ hat der Admin keinen Zugriff; stattdessen erscheint die Lokalisierer-Anmeldemaske.
- Antwort: Fehler behoben. Im `before_request`-Guard gab es für `config_i18n` eine zusätzliche Prüfung, die nur Lokalisierer akzeptierte und Admin-Sessions fälschlich erneut challengte. Die Prüfung wurde korrigiert, sodass Admin **oder** berechtigter Lokalisierer zugelassen wird.
- Änderungen:
  - Auth-Guard für Endpoint `config_i18n` angepasst:
    - GET: erlaubt jetzt `admin || i18n-authenticated`
    - POST: erlaubt jetzt `admin || i18n-authenticated(selected_lang)`
  - Ergebnis: Admin kann „Lokalisierungstexte bearbeiten“ wieder ohne Lokalisierer-Login öffnen.

## v0.1.169
- Anfrage: „Rollen (Spalte A)" in allen Teilen der Anwendung in „DU Berechtigungsrollen" umbenennen. Hinweis: In `app.py` ist noch Code für die chinesische Sprachunterstützung sichtbar.
- Antwort: Umgesetzt. Die Bezeichnung wurde in der Anwendung konsistent auf „DU Berechtigungsrollen" vereinheitlicht. Zusätzlich wurden die verbliebenen chinesischen Sprachreste in `app.py` vollständig entfernt. Im Zuge der Bereinigung wurde außerdem ein versehentlich beschädigter Abschnitt (`load_auth_settings`/Template-Kontext) repariert, damit die Seiten wieder fehlerfrei laden.
- Änderungen:
  - Bezeichnung vereinheitlicht: `DU Berechtigungsrollen`.
  - `app.py` bereinigt: keine `zh`-Einträge mehr in Sprachlisten/Defaults.
  - Auth-/Session-Helfer und `context_processor` wiederhergestellt (`load_auth_settings`, `save_auth_settings`, `_is_admin_authenticated`, `_is_i18n_authenticated`, `_safe_next_path`, `_set_login_challenge`, `inject_app_meta`).

## v0.1.168
- Anfrage: „Rollen (Spalte A)“ in allen Teilen der Anwendung in „DU Berechigungsrollen" umbenennen. Zusätzlich Hinweis: In `app.py` ist noch Code für chinesische Sprachunterstützung sichtbar.
- Antwort: Umgesetzt. Die Bezeichnung wurde durchgehend vereinheitlicht auf „DU Berechtigungsrollen" (korrigierte Schreibweise). Zusätzlich wurden die verbliebenen chinesischen Sprachreste in `app.py` bereinigt (inkl. i18n-Sprachliste in der i18n-Konfig-Route).
- Änderungen:
  - Label-/Textersetzung für Rollenbezeichnung an allen relevanten UI-Stellen auf `DU Berechtigungsrollen`.
  - `app.py` weiter bereinigt: keine aktive `zh`-Sprache in `SUPPORTED_LANGS` und keine `zh`-Auswahl in der i18n-Konfig-Liste.

## v0.1.167
- Anfrage: Bitte in `app.py` englische Kommentare zur besseren Lesbarkeit ergänzen, um ein Review zu erleichtern.
- Antwort: Umgesetzt. Ich habe gezielt an den zentralen Architekturstellen englische Kommentare ergänzt, damit Reviewer schneller den Zweck wichtiger Blöcke erfassen können, ohne das Verhalten zu ändern.
- Änderungen:
  - Englische Struktur-/Kontextkommentare ergänzt in `app.py`, u. a. bei:
    - Pfad-/Projektstruktur-Setup
    - Auth-Settings-Ladefunktion
    - zentraler Auth-Guard (`before_request`)
    - Mapping-Snapshot-Persistenz (`save_mapping_plus`)
    - Deployment-Bundle-Generator
  - Keine funktionalen Änderungen am Laufzeitverhalten.

## v0.1.166
- Anfrage: Linke Seite im Bereich „Mapping (Drag & Drop)" ist nicht mehr scrollbar. Zusätzlich soll es die Möglichkeit geben, Personas zuzuklappen.
- Antwort: Umgesetzt. Die linke Mapping-Spalte ist wieder scrollbar, und der Persona-Bereich kann jetzt per Toggle ein- und ausgeklappt werden. Dadurch bleibt die Oberfläche bei langen Listen bedienbar und aufgeräumt.
- Änderungen:
  - `mapping-left` wieder mit vertikalem Scrollverhalten versehen (`max-height` + `overflow:auto`).
  - Persona-Sektion in einen separaten Bereich gelegt (`personaSection`).
  - Toggle-Button ergänzt (`togglePersonaBtn`) zum Ein-/Ausklappen der Persona-Liste.

## v0.1.165
- Anfrage: Die Rollen aus „Rollenliste bearbeiten“ sollen auf der Hauptseite unter „Mapping (Drag & Drop)“ immer mit unter den Personas angezeigt werden und für die rechte Seite zuweisbar sein. Außerdem die Limitierung bei „Mapping beginnen“ wieder entfernen.
- Antwort: Umgesetzt. Der Rollen-Pool ist auf der Hauptseite nun dauerhaft aktiv und steht damit unabhängig vom Einstiegspfad zur Verfügung. Dadurch sind die Rollen aus der Rollenliste jederzeit links sichtbar und können direkt auf die rechte Seite zugeordnet werden — auch nach „Mapping beginnen“.
- Änderungen:
  - Standardzustand `show_role_pool` auf aktiv gesetzt.
  - Im Pfad `manual_test` (Button „Mapping beginnen“) die frühere Einschränkung entfernt (`show_role_pool` bleibt aktiv).
  - Ergebnis: Rollen-Pool (aus Rollenliste) ist durchgehend verfügbar und konfigurierbar per Drag & Drop.

## v0.1.164
- Anfrage: Auf der Hauptseite sollen links im Bereich „Mapping (Drag & Drop)" die Rollen immer zusammen mit den Personas angezeigt werden.
- Antwort: Umgesetzt. Die Rollenliste im linken Pool ist jetzt dauerhaft sichtbar und nicht mehr vom bisherigen Schalterzustand abhängig. Dadurch sind Personas und Rollen jederzeit parallel verfügbar.
- Änderungen:
  - In `index.html` die bedingte Anzeige des Rollen-Pools entfernt (`show_role_pool`-Guard).
  - Linker Mapping-Pool zeigt nun immer:
    - Personas
    - Rollen (Spalte A) inkl. Rollen-Suche

## v0.1.163
- Anfrage: Beispielrollen in einer separaten JSON-Datei speichern. Zukünftig soll der Button „Beispielrollen einfügen" genau den Inhalt verwenden, der unter „Konfiguration → Beispiel AD/ORBIS Gruppen" definiert wurde.
- Antwort: Umgesetzt. Die Beispielrollen sind jetzt technisch von den allgemeinen App-Settings getrennt und werden in einer eigenen JSON-Datei verwaltet. Der Button auf der Hauptseite greift prioritär auf diese definierte Liste zu.
- Änderungen:
  - Neue Konfig-Datei eingeführt: `config/sample_roles.json`.
  - Neue Helper in `app.py`:
    - `load_sample_roles_text()`
    - `save_sample_roles_text(...)`
  - Seite `Konfiguration` speichert das Feld „Beispiel AD/ORBIS Gruppen" nun in `sample_roles.json`.
  - Hauptseite liest für „Beispielrollen einfügen" zuerst aus `sample_roles.json`; nur wenn leer, greift weiterhin die bestehende Fallback-Ermittlung.

## v0.1.162
- Anfrage: „Auth-Konfiguration" in „Konfiguration" ändern (in allen Sprachen) und Links ggf. anpassen.
- Antwort: Umgesetzt. Die Bezeichnung wurde sprachübergreifend vereinheitlicht, sodass im UI nicht mehr „Auth-Konfiguration", sondern die allgemeinere Form „Konfiguration" (bzw. jeweilige Sprachvariante) verwendet wird. Die Navigationslinks bleiben funktional unverändert und zeigen nun die neuen Labels.
- Änderungen:
  - Texte in Templates aktualisiert:
    - DE: `Auth-Konfiguration` -> `Konfiguration`
    - EN: `Auth configuration` -> `Configuration`
    - IT: `Configurazione auth` -> `Configurazione`
    - FR: `Configuration auth` -> `Configuration`
    - PT: `Configuração auth` -> `Configuração`
    - ES: `Configuración auth` -> `Configuración`
  - `_sidebar.html` Linktext entsprechend angepasst.
  - `I18N`/Defaults in `app.py` für `auth_config.title` bzw. `nav.auth` konsistent nachgezogen.

## v0.1.161
- Anfrage: Beispielrollen im Webinterface editierbar machen; passt gut auf die Seite „Auth-Konfiguration“. Ein Textfeld reicht.
- Antwort: Umgesetzt. Auf der Seite „Auth-Konfiguration“ gibt es jetzt ein zentrales Textfeld für Beispiel-AD/ORBIS-Gruppen (eine Rolle pro Zeile). Diese Liste wird gespeichert und auf der Hauptseite direkt für den Button „Beispielrollen einfügen“ verwendet.
- Änderungen:
  - `config-auth` erweitert um Textbereich `sample_roles_text`.
  - Speicherung in `app_settings.json` über neuen Schlüssel `sample_roles_text`.
  - `index()` nutzt zuerst die gespeicherte Liste aus den App-Settings; wenn leer, greift weiterhin die bestehende Auto-Ermittlung/Fallback-Logik.
  - i18n-Texte für neue Felder ergänzt (DE/EN/IT/FR/PT/ES) und in `I18N_EDITOR_DEFAULTS` nachgezogen.

## v0.1.160
- Anfrage: Bei den Beispiel-AD/ORBIS-Gruppen gibt es einen Fehler: Es werden Rollen für das Mapping importiert, nicht die PROS SUB-Rollen.
- Antwort: Umgesetzt. Die Filterlogik für die Beispielrollen wurde korrigiert, sodass jetzt die erwarteten PROS SUB-Rollen zuverlässig ermittelt werden. Zusätzlich bleibt die bisherige Schreibweise (`PRO SUB`) weiterhin kompatibel, falls historische Daten diese Form enthalten.
- Änderungen:
  - `default_test_roles`-Filter in `app.py` angepasst:
    - akzeptiert `PROS SUB` (gewünscht)
    - akzeptiert zusätzlich `PRO SUB` (Kompatibilität)
  - Ergebnis: Button „Beispielrollen einfügen“ nutzt wieder die korrekte PROS-SUB-Basis.

## v0.1.159
- Anfrage: Chinesisch als Sprache entfernen, einschließlich aller Komponenten.
- Antwort: Umgesetzt. Die Sprache Chinesisch wurde aus den aktiven Sprachkomponenten entfernt. Dadurch ist Chinesisch nicht mehr auswählbar, nicht mehr als unterstützte Sprache im Rechtemodell enthalten und nicht mehr Teil der regulären Sprachflüsse in UI/Auth/Editor.
- Änderungen:
  - `SUPPORTED_LANGS` in `app.py` auf `de/en/it/fr/pt/es` reduziert (`zh` entfernt).
  - Sprachauswahl in den Header-Komponenten ohne `zh/中文` umgesetzt.
  - Folgeeffekte:
    - keine chinesische Sprachauswahl im Frontend
    - keine chinesischen i18n-Passwort-Slots im Auth-Setup
    - keine chinesische Sprache im i18n-Editor als aktive Bearbeitungssprache

## v0.1.158
- Anfrage: Bitte ändere den Hinweis „zuerst mapping.txt importieren oder externe Rollen einfügen, damit LDAP/ORBIS-Rollen angezeigt werden“ und ergänze „Mapping-Code vom Server eingeben“, da es jetzt drei Startfunktionen gibt.
- Antwort: Umgesetzt. Der Einstiegshinweis wurde in allen unterstützten Sprachen erweitert und nennt jetzt alle drei Startwege klar und konsistent: `mapping.txt importieren`, `externe Rollen einfügen` oder `Mapping-Code vom Server eingeben`. Dadurch ist die Bedienlogik auf der Hauptseite für neue Nutzer und bei Mehrsprachigkeit eindeutig.
- Änderungen:
  - `msg.loadFirst` in `index.html` (alle Sprachblöcke) aktualisiert.
  - `msg.loadFirst` in `I18N_EDITOR_DEFAULTS` (`app.py`) entsprechend nachgezogen, damit die Texte in „Lokalisierungstexte bearbeiten" konsistent bleiben.

## v0.1.157
- Anfrage: Bei Neuinstallation sind die Beispielrollen über den Button nicht sichtbar. Kommen diese aus dem Aufgabe-Verzeichnis? Zusätzlich: in Changelog-Einträgen bei "Antwort" etwas mehr erklärenden Text.
- Antwort: Ja, die bisherigen Beispielrollen kamen primär indirekt aus den Daten im `Aufgabe`-Pfad (über geladenes Mapping). In einer frischen Deployment-Umgebung ohne `Aufgabe` konnte der Button daher leer bleiben. Ich habe die Logik angepasst, damit der Button zuverlässig funktioniert: Wenn keine passenden Rollen aus `mapping` vorhanden sind, wird automatisch auf die Rollenliste aus der App-Konfiguration (`roles_column_a.json`) zurückgefallen. Dadurch sind Beispielrollen auch bei Neuinstallation ohne `Aufgabe` sichtbar. Für kommende Changelog-Einträge formuliere ich den Abschnitt "Antwort" ausführlicher und erklärender.
- Änderungen:
  - Fallback für `default_test_roles` ergänzt:
    - primär aus Mapping-Daten (`PRO SUB`)
    - falls leer: aus `keycloak_roles`/Konfig-Rollen
  - Ergebnis: Button „Beispielrollen einfügen“ liefert auch bei frischer Deployment-Installation Werte.

## v0.1.156
- Anfrage: Doku-Tipp für `tls.certresolver` neutral formulieren (kein fester Wert wie `le`). Zusätzlich Version/Changelog aktualisieren.
- Antwort: Umgesetzt.
- Änderungen:
  - Deployment-Doku angepasst auf Platzhalter:
    - `traefik.http.routers.rolemapper.tls.certresolver=<your-certresolver-name>`
  - Klarstellung ergänzt: Wert muss exakt dem in Traefik konfigurierten Resolvernamen entsprechen.

## v0.1.155
- Anfrage: TLS-Checkliste in die Deployment-Doku aufnehmen und Deployment-Bundle entsprechend aktualisieren.
- Antwort: Umgesetzt.
- Änderungen:
  - `DEPLOY_EN.md` (im Bundle-Generator) um eine explizite Traefik TLS-Checkliste erweitert.
  - Enthält nun die erforderlichen Labels inkl. `tls.certresolver` sowie Hinweis auf den typischen Fehlerfall.
  - Deployment-Bundle liefert diese aktualisierte Doku direkt mit aus.

## v0.1.154
- Anfrage: v0.1.153 erscheint im Deployment-ZIP-Changelog nicht aktualisiert.
- Antwort: Bereinigt.
- Änderungen:
  - `app/CHANGELOG_BUNDLED.md` als feste Datei erzeugt und mit aktuellem Changelog synchronisiert.
  - Damit enthält das Deploy-ZIP den aktuellen Changelog-Stand direkt als Datei.
  - Hinweis: Für den neuen Stand bitte das Deployment-Bundle neu herunterladen.

## v0.1.153
- Anfrage: Daten aus `Aufgabe` (z. B. Rollen) fest in die App/Deploy-ZIP integrieren und Changelog fest befüllen, damit im Deployment kein Zugriff auf `Aufgabe` nötig ist.
- Antwort: Umgesetzt.
- Änderungen:
  - Changelog-Ladepfad erweitert:
    - primär `Aufgabe/CHANGELOG.md`
    - Fallback: `app/CHANGELOG_BUNDLED.md`
  - Deploy-Bundle erweitert:
    - `config/` wird in die ZIP aufgenommen (JSON-Defaults für Rollen/Personas/Settings)
    - `app/CHANGELOG_BUNDLED.md` wird beim Bundle-Erzeugen fest eingebettet
    - `config/auth_settings.json` bleibt mit initialem Admin-Hash enthalten
  - Ergebnis: Deploy ohne `Aufgabe/` enthält trotzdem Rollen-/Config-Basis und Changelog-Inhalt.

## v0.1.152
- Anfrage: Im `rolemapper-deploy-bundle.zip` ein sicheres initiales Standardpasswort für Admin hinterlegen und in `DEPLOY_EN.md` dokumentieren.
- Antwort: Umgesetzt.
- Änderungen:
  - Deploy-Bundle enthält jetzt zusätzlich `config/auth_settings.json` mit vorinitialisiertem `admin_hash`.
  - Initiales Admin-Passwort im Bundle festgelegt und in `DEPLOY_EN.md` dokumentiert.
  - Hinweis in `DEPLOY_EN.md` ergänzt, das Admin-Passwort nach erstem Login sofort zu ändern.

## v0.1.151
- Anfrage: Unter "Permanente Systembeschreibung" Rubrik "Externer Zugriff" ergänzen mit `https://FQDN/?load_mapping_code=<Mappingcode>` und kurzen Bedienhinweis in allen Sprachen.
- Antwort: Umgesetzt.
- Änderungen:
  - In `## Permanente Systembeschreibung` neue Rubrik **Externer Zugriff** ergänzt.
  - URL ergänzt: `https://FQDN/?load_mapping_code=<Mappingcode>`.
  - Guide (`guide.html`) in allen Sprachen um neuen Punkt `s7` erweitert (Bedienung externer Zugriff).
  - `I18N_EDITOR_DEFAULTS` um `guide.s7` für DE/EN/IT/FR/PT/ES/ZH erweitert (damit in "Lokalisierungstexte bearbeiten" editierbar).

## v0.1.150
- Anfrage: Metainformationen für Server-Mapping um `PLZ` und `Stadt` erweitern; Inputfelder und Anzeigen in Hauptseite und Server-Mappings aktualisieren.
- Antwort: Umgesetzt.
- Änderungen:
  - Server-Meta erweitert um:
    - `postal_code` (PLZ)
    - `city` (Stadt)
  - Speichern/Laden/Update von Mapping-Meta in `app.py` entsprechend erweitert.
  - Hauptseite (`index.html`):
    - Neue Inputfelder `PLZ` und `Stadt` ergänzt.
    - Rechte Meta-Vorschau um `PLZ` und `Stadt` erweitert (inkl. Live-Sync).
  - Server-Mappings (`admin_mappings.html`):
    - Tabelle um Spalten `PLZ` und `Stadt` erweitert.
    - Filter um Suche nach `PLZ` und `Stadt` ergänzt.
  - i18n-Keys für neue Felder/Spalten/Filter ergänzt (inkl. Defaults für Lokalisierungstexte).

## v0.1.149
- Anfrage: Zentrale CSS-Datei für alle Seiten, damit Styling nicht pro Seite separat gepflegt wird.
- Antwort: Umgesetzt.
- Änderungen:
  - Neue zentrale CSS-Datei angelegt: `app/static/style.css`.
  - Alle Templates auf Einbindung der zentralen CSS umgestellt (`url_for('static', filename='style.css')`).
  - Enthaltene gemeinsame Basisstile: Theme-Variablen, Header, Layout, Sidebar, Cards, Buttons, Responsive-Verhalten.
  - Seite-spezifische CSS-Blöcke bleiben vorerst ergänzend bestehen (für individuelle Komponenten), gemeinsame Basis kommt jetzt zentral.

## v0.1.148
- Anfrage: Link-Höhen/Abstände in der Sidebar sind zwischen Hauptseite und den übrigen Seiten unterschiedlich (Padding-Verdacht).
- Antwort: Bestätigt und angeglichen.
- Änderungen:
  - Sidebar-Linkstil auf der Hauptseite an den gemeinsamen Sidebar-Stil angepasst.
  - In `index.html` für `.menu a` ergänzt/vereinheitlicht:
    - `line-height: 1.2`
    - `margin: 2px 0`
  - Damit sind die vertikalen Abstände zwischen den Navigationslinks konsistent.

## v0.1.147
- Anfrage: Abstände/Höhen der Links in der linken Navigation springen je nach Seite.
- Antwort: Umgesetzt.
- Änderungen:
  - Einheitliche Link-Höhe/-Abstände direkt im gemeinsamen Sidebar-Partial (`_sidebar.html`) festgelegt.
  - Konsistente Werte für alle Menüpunkte: `display`, `padding`, `line-height`, `margin`, `border-radius`.
  - Überschrift der Navigation ebenfalls mit festem Abstand versehen.

## v0.1.146
- Anfrage: Header, Linkleiste und Seiteninhalt im Code trennen (Code-Reduzierung, keine Wiederholung pro Seite).
- Antwort: Umgesetzt.
- Änderungen:
  - Neue gemeinsame Template-Bausteine eingeführt:
    - `app/templates/_header.html`
    - `app/templates/_sidebar.html`
  - Mehrere Seiten auf Includes umgestellt (statt Header/Sidebar pro Seite zu duplizieren):
    - `guide.html`
    - `changelog.html`
    - `config_auth.html`
    - `config_i18n.html`
    - `config_persona_names.html`
    - `config_personas.html`
    - `config_roles.html`
    - `admin_mappings.html`
  - Ergebnis: weniger doppelter Code, konsistentere Navigation/Struktur, einfachere Pflege.

## v0.1.145
- Anfrage: In der Changelog-Seite wird noch ein Seitenlink/Adressleisten-Hinweis angezeigt; bitte entfernen.
- Antwort: Umgesetzt.
- Änderungen:
  - Alte Formulierung in `v0.1.42` bereinigt (kein Hinweis auf Adressleisten-/`history.replaceState`-Verhalten mehr).

## v0.1.144
- Anfrage: In Server-Mappings sollen die Buttons "Laden" und "TXT" beim Hover die Farbe nicht ändern (wie bei den anderen Buttons).
- Antwort: Umgesetzt.
- Änderungen:
  - Einheitliches Hover-Verhalten für `.btn` in `admin_mappings.html` gesetzt.
  - Hover jetzt wie im restlichen UI: dezenter Hintergrund, Textfarbe bleibt konsistent.

## v0.1.143
- Anfrage: Anleitung/Guide in allen Sprachen aktualisieren.
- Antwort: Umgesetzt.
- Änderungen:
  - Guide-Inhalte (`s1`–`s5`) in DE/EN/IT/FR/PT/ES/ZH auf den aktuellen Workflow aktualisiert:
    - mapping.txt / externe Rollen
    - Mapping-Code laden (inkl. Server-Mappings)
    - Drag&Drop inkl. Metadaten
    - Server-Speichern/-Aktualisieren (ohne Historie)
    - TXT-Download (Hauptseite + Server-Mappings)
  - Navigationstext `nav.serverMappings` in der Guide-Seite für alle Sprachen ergänzt.
  - Fehlerhaften Redirect-Script-Block in `guide.html` entfernt (zwanghafter Pfadwechsel auf `/`).

## v0.1.142
- Anfrage: Dropdown für Länderauswahl und automatisches Reduzieren der Liste.
- Antwort: Umgesetzt.
- Änderungen:
  - Länderfilter in `Server-Mappings` von Freitext auf Dropdown umgestellt.
  - Dropdown wird dynamisch aus vorhandenen Länderwerten befüllt (einzigartig + alphabetisch).
  - Automatische Listenreduktion beim Ändern des Länder-Dropdowns sowie bei Eingabe in Kundennummer/Kunde.

## v0.1.141
- Anfrage: Verdacht auf separates CSS bei Server-Mappings; Schriftart/Farben stimmen nicht mit Hauptseite.
- Antwort: Angeglichen.
- Änderungen:
  - CSS der Seite `Server-Mappings` auf die gleichen Basiswerte wie Hauptseite umgestellt:
    - `font-family: Calibri, Arial, sans-serif`
    - gleiche Farbtokens/Theme-Farben
    - gleiche Headerhöhe/-farbe
    - gleiche Sidebar-/Card-/Tabellenoptik
    - gleiche responsive Breakpoints/Offsets
  - Ziel: visuell konsistentes UI ohne abweichenden „Sonderstil“.

## v0.1.140
- Anfrage: Server-Mappings UI soll exakt wie die anderen Seiten aussehen; Sprachauswahl fehlt; Übersetzungen nachziehen und Lokalisierungstexte-Bearbeitung aktualisieren.
- Antwort: Umgesetzt.
- Änderungen:
  - `admin_mappings.html` auf Standard-App-Layout gebracht:
    - gleicher Header-Stil inkl. Rolle/Login/Version
    - gleiche linke Sidebar-Struktur
    - responsive Hamburger-Menü + Overlay wie Hauptseitenstil
  - Sprachauswahl (`DE/EN/IT/FR/PT/ES/ZH`) auf Server-Mappings ergänzt.
  - i18n für Server-Mappings ergänzt (Titel, Hinweise, Tabellenköpfe, Filterfelder, Buttons, Navigation).
  - Neue i18n-Keys in `I18N_EDITOR_DEFAULTS` (alle unterstützten Sprachen) ergänzt, u. a.:
    - `nav.serverMappings`
    - `server.*` (Titel, Filter, Spalten, Buttons, Leerzustand)
  - Damit sind die neuen Texte in `Lokalisierungstexte bearbeiten` sichtbar/änderbar.

## v0.1.139
- Anfrage: In Server-Mappings zusätzlich "TXT erzeugen"/Download integrieren, damit der TXT-Download direkt aus der Liste gestartet werden kann.
- Antwort: Umgesetzt.
- Änderungen:
  - Neue Route: `/download-mapping-plus/<code>` für direkten Download der gespeicherten Mapping-TXT aus `mapping_store`.
  - In `Server-Mappings` je Zeile neue Aktion `TXT` ergänzt (direkter Download-Button).
  - Tabellenlayout um TXT-Spalte erweitert.

## v0.1.138
- Anfrage: Server-Mappings farblich/layout-technisch wie die anderen Seiten; Link in linker Liste direkt nach Hauptseite; Suche nach Kundennummer, Land oder Kunde.
- Antwort: Umgesetzt.
- Änderungen:
  - `admin_mappings.html` auf App-Layout angepasst (Header + Sidebar + Card-/Farbwelt wie Hauptseitenstil).
  - Sidebar-Reihenfolge angepasst: `Server-Mappings` steht direkt nach `Hauptseite`.
  - Linkposition in linken Navigationsleisten konsolidiert.
  - Filterfunktion auf Server-Mappings ergänzt:
    - Suche nach `Land`
    - Suche nach `Kundennummer`
    - Suche nach `Kunde`
  - Clientseitiges Live-Filtering ohne Neuladen.

## v0.1.137
- Anfrage: Server-Mappings-Seite wie die anderen Seiten mit Header + Linkleiste; pro Zeile Button zum direkten Laden in Hauptseite (wie Code-Eingabe); Seite für alle sichtbar.
- Antwort: Umgesetzt.
- Änderungen:
  - `/admin-mappings` Layout auf App-Standard gebracht (Header + linke Navigation).
  - Link `Server-Mappings` in der linken Navigation sichtbar gemacht.
  - Zugriff geöffnet: Seite ist nicht mehr admin-only.
  - Pro Mapping-Zeile neuer Button `Laden`:
    - öffnet Hauptseite mit `load_mapping_code=<CODE>`
    - Mapping wird dort direkt vorbefüllt, wie beim manuellen Code-Laden.
  - Mapping-Inhalt bleibt weiterhin ausgeblendet (nur Metadatenliste).

## v0.1.136
- Anfrage: `/admin-mappings` wirft weiterhin Internal Server Error.
- Antwort: Behoben.
- Änderungen:
  - Fehlerursache gefixt: nicht vorhandene Funktion `_pick_ui_lang()` in der neuen Route ersetzt.
  - Sprachwahl in `/admin-mappings` jetzt robust über `?lang`, Cookie oder Fallback `de`.

## v0.1.135
- Anfrage: Klick auf Sidebar-Link führt zu "Not Found"; Admin-Link soll funktionieren und nur für Admin sichtbar sein.
- Antwort: Behoben.
- Änderungen:
  - Fehlende Route `/admin-mappings` in `app.py` (inkl. Datenaufbereitung) korrekt ergänzt.
  - Admin-Seite bleibt ohne Anzeige des Mapping-Inhalts (nur Metadatenliste).
  - Sidebar-Integration bleibt admin-only.

## v0.1.134
- Anfrage: Admin-Mappingseite in die linke Linkleiste integrieren und nur für Admins sichtbar machen.
- Antwort: Umgesetzt.
- Änderungen:
  - Sidebar-Link `Server-Mappings` in die linken Navigationsleisten integriert.
  - Link erscheint ausschließlich im Admin-Bereich der Navigation.
  - Auf relevanten Seiten mit Sidebar konsistent ergänzt.

## v0.1.133
- Anfrage: Admin-Seite mit Liste aller serverseitig gespeicherten Mappings inkl. Erstellungs-/Änderungsdatum; Anzeige soll Browserdatum/-zeit berücksichtigen, nicht Serverzeit.
- Antwort: Umgesetzt.
- Änderungen:
  - Neue Admin-Seite: `/admin-mappings` mit Tabelle aller gespeicherten Mapping-Codes und Metadaten.
  - Neue Template-Datei: `app/templates/admin_mappings.html`.
  - Sichtbarer Link für Admins in der Sidebar: `Server-Mappings`.
  - Metadaten-Speicherung erweitert:
    - `created_at_client` (erstes Speichern, Browserzeit)
    - `updated_at_client` (letzte Änderung, Browserzeit)
    - bestehende Serverzeit-Felder bleiben als Fallback erhalten.
  - Beim Speichern/Aktualisieren wird ein Browser-Zeitstempel aus dem Formular mitgegeben (`mapping_client_ts`).
  - Admin-Liste priorisiert Browserzeit (Client-Timestamp) für die Datumsanzeige.

## v0.1.132
- Anfrage: Changelog anpassen (v0.1.131 entfernen), Ländercodes bei Land alphabetisch sortieren und Luxemburg hinzufügen.
- Antwort: Umgesetzt.
- Änderungen:
  - Eintrag `v0.1.131` aus dem Changelog entfernt (Rollback war bereits auf v0.1.130 erfolgt).
  - Länderliste im Feld `Land` alphabetisch nach Code sortiert.
  - Code `LU` (Luxemburg) ergänzt.

## v0.1.130
- Anfrage: In den Kundenmetas zusätzlich Land aufnehmen (als erstes Feld), dann Kundennummer, Side, Kundenname; Länder gekürzt für Deutschland, Österreich, Schweiz, Belgien, Frankreich, England, Brasilien. Metainformation beim Speichern auf Server ebenfalls erweitern.
- Antwort: Umgesetzt.
- Änderungen:
  - Neues Meta-Feld `country` eingeführt (zusätzlich zu `customer_no`, `side`, `customer`).
  - UI in "Mapping (Drag & Drop)" erweitert und Reihenfolge gesetzt auf:
    - Land (Select): `DE`, `AT`, `CH`, `BE`, `FR`, `EN`, `BR`
    - Kundennummer
    - Side
    - Kundenname
  - Rechte Vorschau zeigt jetzt ebenfalls Land + Kundennummer + Side + Kundenname (Live-Sync).
  - Server-Meta (`mappingplus-<CODE>.json`) beim Speichern/Aktualisieren um `country` erweitert.
  - Beim Laden eines gespeicherten Mappings wird `country` mit geladen/vorbefüllt.
  - Neue i18n-Keys ergänzt: `countryLabel`, `countryPh` (alle unterstützten Sprachen + Defaults).

## v0.1.129
- Anfrage: Kundenmetas um Kundennummer und Side erweitern, als Inputfelder in Mapping (Drag & Drop) in Reihenfolge Kundennummer -> Side -> Kundenname.
- Antwort: Umgesetzt.
- Änderungen:
  - Mapping-Metadaten erweitert:
    - `customer_no`
    - `side`
    - `customer`
  - Speicherung/Update im Server-Meta (`mappingplus-<code>.json`) entsprechend erweitert.
  - Beim Laden eines gespeicherten Mappings werden alle drei Felder wieder vorbefüllt.
  - UI in Schritt "Mapping (Drag & Drop)" angepasst:
    - Reihenfolge: Kundennummer, Side, Kundenname.
    - Rechte Vorschau zeigt alle drei Werte.
    - Live-Sync der Vorschau beim Tippen.
  - Neue i18n-Keys ergänzt (`customerNoLabel`, `sideLabel`, `customerNoPh`, `sidePh`) inkl. Lokalisierungseditor-Defaults.

## v0.1.128
- Anfrage: Kundenfeld aus dem unteren Bereich in die Zeile "Mapping (Drag & Drop)" verschieben und auch rechts anzeigen.
- Antwort: Umgesetzt.
- Änderungen:
  - Kundenfeld in Schritt 4 nach oben in die Header-Zeile von "Mapping (Drag & Drop)" verschoben.
  - Zusätzliche Anzeige rechts im Mapping-Bereich ergänzt (`Kunde: ...`) mit Live-Synchronisierung beim Tippen.
  - Kundenfeld aus der unteren Button-Zeile entfernt.
  - Neuer i18n-Key `customerLabel` für alle Sprachen ergänzt (inkl. Lokalisierungstexte-Bearbeitung).

## v0.1.127
- Anfrage: Wenn eine Seite mit geladenem Mapping geöffnet ist, soll der Button "Mapping speichern" unten nicht angezeigt werden; nur bei Neu-Laden, TXT-Import oder Mapping beginnen.
- Antwort: Umgesetzt.
- Änderungen:
  - Status-Flag `mapping_loaded_from_server` eingeführt und im Formularfluss mitgeführt.
  - Bei `Mapping laden` wird Flag gesetzt -> `Mapping speichern` ausgeblendet.
  - Bei Neu-Laden/TXT-Import/Mapping beginnen wird Flag zurückgesetzt -> `Mapping speichern` sichtbar.
  - `Mapping am Server aktualisieren` bleibt sichtbar.

## v0.1.126
- Anfrage: "Load mapping" steht auf der Hauptseite; Übersetzungen in allen Sprachen prüfen.
- Antwort: Geprüft und korrigiert.
- Änderungen:
  - `sec.loadTitle` in `index.html` für alle Sprachblöcke überprüft und vereinheitlicht.
  - Englisch korrigiert auf `Load mapping` (statt falschem deutschem Text).
  - Fehlende `sec.loadTitle`-Einträge in FR/PT/ES/ZH ergänzt.

## v0.1.125
- Anfrage: Auf der Hauptseite die Nummerierung 1) 2) 3) 4) entfernen.
- Antwort: Umgesetzt.
- Änderungen:
  - Titel der vier Hauptblöcke auf der Startseite ohne führende Nummern dargestellt.
  - Entsprechende i18n-Texte in allen unterstützten Sprachen angepasst.
  - `I18N_EDITOR_DEFAULTS` in `app.py` synchronisiert, damit die Lokalisierungsseite dieselben (nummernlosen) Default-Texte zeigt.

## v0.1.124
- Anfrage: "Mapping+" bitte in "Mapping" umbenennen.
- Antwort: Umgesetzt.
- Änderungen:
  - UI-/Hinweistexte auf Hauptseite angepasst: "Mapping+" -> "Mapping".
  - Backend-Flashtexte entsprechend angepasst.
  - Interne technische Variablennamen/Dateinamen bleiben unverändert für Kompatibilität.

## v0.1.123
- Anfrage: Möglichkeit, geladene Mappings nach Änderungen auf dem Server zu aktualisieren, inkl. Hinweis auf fehlende Änderungshistorie.
- Antwort: Umgesetzt.
- Änderungen:
  - Schritt 4 (Mapping): zusätzlicher Button `Mapping am Server aktualisieren`.
  - Verhalten:
    - aktualisiert den aktuell geladenen Mapping+-Code auf dem Server (gleicher Code wird überschrieben)
    - falls kein Code vorhanden ist, wird ein Hinweis ausgegeben.
  - Deutlicher Hinweis im UI + Flash:
    - Es gibt **keine Änderungshistorie**
    - die vorherige Server-Version wird beim Update überschrieben.
  - Neue Texte/Keys in allen unterstützten Sprachen ergänzt und in Lokalisierungstexte-Bearbeitung verfügbar gemacht.

## v0.1.122
- Anfrage: Übersetzungen aller bestehenden Sprachen nachziehen und Lokalisierungstexte bearbeiten aktualisieren.
- Antwort: Umgesetzt.
- Änderungen:
  - Hauptseite (`index.html`) neue UI-Elemente vollständig i18n-fähig gemacht:
    - `3) Mapping laden`
    - Placeholder/Buttons für Mapping-Code laden
    - Placeholder/Buttons für neue LDAP/ORBIS-Rolle
    - Persona-/Rollen-Filterfelder
    - Kundenfeld-Placeholder in Schritt 4
  - Mapping-Schritt konsistent auf `4) Mapping (Drag & Drop)` in allen Sprach-Dictionaries.
  - `I18N_EDITOR_DEFAULTS` in `app.py` erweitert/aktualisiert, damit die neuen Keys in „Lokalisierungstexte bearbeiten" editierbar sind.

## v0.1.121
- Anfrage: Kundenbezeichnung nur in 4) Mapping (Drag & Drop): manuell eingeben oder aus servergeladener Datei übernehmen.
- Antwort: Umgesetzt.
- Änderungen:
  - Kundenfeld aus den oberen Blöcken (1/2/3) entfernt.
  - Kundenfeld ausschließlich im Mapping-Bereich (Schritt 4) platziert.
  - Beim Laden eines gespeicherten Mapping+ Codes wird die Kundenbezeichnung aus der Server-Metadatei übernommen und im Feld vorausgefüllt.
  - Download-Datei bleibt weiterhin ohne Kundennamen.

## v0.1.120
- Anfrage: Die Blöcke 1) mapping.txt importieren, 2) Externe Authentifizierungsrollen und 3) Mapping laden sollen nebeneinander stehen.
- Antwort: Umgesetzt.
- Änderungen:
  - Layout der oberen Karten auf der Hauptseite von 2 auf 3 Spalten umgestellt (`.grid: 1fr 1fr 1fr`).
  - Mobile/kleine Auflösungen bleiben weiterhin auf 1 Spalte (responsive Breakpoint unverändert).

## v0.1.119
- Anfrage: Separate Möglichkeit gewünscht: "TXT erzeugen" und "Mapping speichern".
- Antwort: Umgesetzt. Es gibt jetzt zwei getrennte Buttons mit getrenntem Verhalten.
- Änderungen:
  - Hauptseite, Schritt Mapping:
    - Button 1: `TXT erzeugen` -> erzeugt/ladet nur die TXT.
    - Button 2: `Mapping speichern` -> speichert Mapping+ auf dem Server und erzeugt Code, ohne TXT-Download.
  - Backend-Handling über `submit_mode` ergänzt.
  - Label für `Mapping speichern` in i18n-Dictionaries auf der Hauptseite ergänzt.

## v0.1.116
- Anfrage: Rechter LDAP/ORBIS-Zuordnungsbereich wird zu schmal, und "TXT erzeugen" bleibt rechts.
- Antwort: Layout korrigiert.
- Änderungen:
  - In `index.html` fehlenden Container-Abschluss im Mapping-Bereich ergänzt.
  - Dadurch ist die Mapping-Layout-Struktur wieder korrekt:
    - rechter Zuordnungsbereich wieder normale Breite
    - "TXT erzeugen" wieder unterhalb des gesamten Mapping-Layouts links positioniert.

## v0.1.115
- Anfrage: Der Button "TXT erzeugen" ist nach rechts oben gewandert; bitte wieder ganz unten links.
- Antwort: Umgesetzt. Der Button ist wieder unten links unterhalb des Mapping-Bereichs positioniert.
- Änderungen:
  - Submit-Button auf der Hauptseite in einen eigenen unteren Linksbündig-Container gesetzt.

## v0.1.114
- Anfrage: Unknown-Red-Markierung beim TXT-Beispiel funktioniert nicht wie erwartet.
- Antwort: Nachgebessert.
- Änderungen:
  - Zusätzliche clientseitige Validierung in der Hauptseite:
    - Rechte Bucket-Einträge werden jetzt nach Rendern/Drop/Copy gegen bekannte Persona- und Rollen-Pools geprüft.
    - Nicht erkennbare Einträge werden automatisch mit `unknown` markiert (rote Darstellung).
  - Dadurch greift die rote Markierung robust, auch wenn Einträge über verschiedene Wege in den Bucket gelangen.

## v0.1.113
- Anfrage: Wenn beim TXT-Import keine Matches zu definierten Personas oder Rollen gefunden werden, diese trotzdem rechts anzeigen und in roter Schrift markieren.
- Antwort: Umgesetzt.
- Änderungen:
  - Hauptseiten-Mapping:
    - Unbekannte Targets aus TXT bleiben in der rechten Vorbelegung sichtbar.
    - Unbekannte Einträge werden visuell rot markiert (`.pill.unknown`).
  - Markierungslogik:
    - Persona-Einträge gelten als bekannt.
    - Rollen-Einträge gelten als bekannt, wenn sie in "Rollen (Spalte A)" enthalten sind.
    - Sonst `data-known=0` + rote Darstellung.
  - Copy-Funktion erweitert, damit die Unknown-Markierung beim Kopieren zwischen Source-Rollen erhalten bleibt.

## v0.1.112
- Anfrage: Vorbelegung auf der rechten Seite beim TXT-Import ist unvollständig; Beispielmapping wird nicht vollständig vorbelegt.
- Antwort: Korrigiert.
- Änderungen:
  - Vorbelegung nach TXT-Upload basiert jetzt direkt auf dem **hochgeladenen Inhalt** (nicht auf einer anderen Seed-Datei im Aufgabe-Ordner).
  - Neue Parser-Funktion für Upload-Inhalt (`parse_mapping_dict_from_txt`) mit Sanitizing/Härtung.
  - Rollen-Vorbelegung erweitert:
    - Alle Targets, die keine Persona sind, werden als direkte Rollen-Vorbelegung übernommen.
    - Dadurch erscheinen auch Einträge, die nicht in der Rollenliste aus Spalte A stehen, weiterhin rechts vorbelegt.

## v0.1.111
- Anfrage: "Rollen (Spalte A)" auf der Hauptseite nur nach TXT-Import anzeigen und bei Nutzung von "2) Externe Authentifizierungsrollen" wieder ausblenden. Zusätzlich Persona-Suche zurückbringen und auch für Rollen (Spalte A) ergänzen.
- Antwort: Umgesetzt.
- Änderungen:
  - Hauptseite zeigt die Box "Rollen (Spalte A)" jetzt kontextabhängig:
    - sichtbar nach erfolgreichem TXT-Import
    - ausgeblendet bei Start über "Externe Authentifizierungsrollen" (manual_test)
  - Status wird über `show_role_pool` serverseitig geführt und beim Generieren beibehalten.
  - Zusätzliche Suchfelder auf der Hauptseite ergänzt:
    - Filter für Persona-Pool
    - Filter für Rollen-Pool (Spalte A)
  - TXT-Import-Härtung blieb aktiv (Sanitizing/Limits/`javascript:`-Block).

## v0.1.110
- Anfrage: Nach TXT-Import auf der Hauptseite zusätzlich die Box "Rollen (Spalte A)" unter Personas anzeigen, automatische Vorbelegung aus TXT rechts anzeigen und TXT-Import gegen Script-Injektion härten.
- Antwort: Umgesetzt.
- Änderungen:
  - Hauptseite Mapping-Bereich erweitert:
    - zusätzliche Rolle-Pool-Box "Rollen (Spalte A)" unter dem Persona-Pool.
    - Rollen können nun zusätzlich direkt pro Source-Rolle zugewiesen werden.
  - Vorbelegung aus vorhandener Mapping-TXT erweitert:
    - Persona-Matches werden wie bisher vorbelegt.
    - direkte Rollen-Matches werden zusätzlich rechts vorbelegt.
  - Assignment-JSON erweitert auf getrennte Struktur:
    - `personas` + `roles` je Source-Rolle (mit Rückwärtskompatibilität zum alten Format).
  - Ausgabeerzeugung erweitert:
    - direkte Rollenzuweisungen werden mit den aus Personas expandierten Rollen zusammengeführt.
  - TXT-Import-Härtung verbessert:
    - zusätzliche Sanitization bei SOURCE/TARGET,
    - Längenlimit für Tokens,
    - Blockierung von `javascript:`-Präfixen.

## v0.1.109
- Anfrage: Auf Changelog sind wieder alle Admin/Lokalisierer-Links sichtbar. Bitte Code genau prüfen.
- Antwort: Korrigiert. Die Changelog-Sidebar ist jetzt rollenbasiert wie die übrigen Seiten.
- Änderungen:
  - `changelog.html` Sidebar-Links auf Rollenlogik umgestellt:
    - ohne Login: nur öffentliche Links + Persona-Konfiguration + Changelog
    - Lokalisierer: zusätzlich Rollenliste + Lokalisierung
    - Admin: zusätzlich Persona-Liste, Rollenliste, Lokalisierung, Auth-Konfiguration
  - Changelog bleibt für alle lesend zugänglich.

## v0.1.108
- Anfrage: Auf der Seite Persona-Konfiguration verschwindet der Changelog-Link in der Linkleiste.
- Antwort: Korrigiert. Der Changelog-Link ist jetzt auf Persona-Konfiguration unabhängig von der Rolle immer sichtbar.
- Änderungen:
  - `config_personas.html` Sidebar angepasst:
    - Changelog-Link aus Rollen-If-Block herausgezogen
    - dadurch sichtbar für nicht angemeldet, Lokalisierer und Admin

## v0.1.107
- Anfrage: Rechtemodell präzise wie vorgegeben (öffentlich/admin/lokalisierer), inkl. Changelog für alle lesend + Download erlaubt.
- Antwort: Nachgezogen und korrigiert.
- Änderungen:
  - Guard-Matrix finalisiert:
    - Öffentlich: Hauptseite (edit), Guide (read), Persona-Konfiguration (read), Changelog + PDF-Download (read).
    - Admin-only: Auth-Konfiguration, Persona-Liste bearbeiten.
    - Admin oder sprachpassender Lokalisierer: Rollenliste bearbeiten, Lokalisierungstexte bearbeiten.
  - Lokalisierer-Navigation angepasst: nur Rollenliste + Lokalisierung (plus Main/Guide, Changelog).
  - `config-i18n` Sidebar: Changelog-Link für alle sichtbar.
  - Fix in `config_personas.html`: fehlerhafte Apostroph-Escapes in IT/FR-Texten behoben (hatte JS-Logik beeinflusst).

## v0.1.106
- Anfrage: Berechtigungsmodell präzisiert (nicht angemeldet/admin/lokalisierer) inkl. Changelog für alle lesend + Download erlaubt.
- Antwort: Umgesetzt gemäß gewünschter Matrix.
- Änderungen:
  - Zugriffsschutz angepasst:
    - Admin-only: `config-auth`, `config-persona-names`
    - Admin oder sprachpassender Lokalisierer: `config-i18n`, `config-roles`
    - Öffentlich lesend: `guide`, `config-personas`, `changelog`, `download/changelog-pdf`
  - `config-i18n`: Speichern wieder sprachgebunden für Lokalisierer (passendes Sprachpasswort) oder Admin.
  - `config-roles`: Lokalisierer dürfen wieder nur Beschreibungen der autorisierten Sprache ändern; Listenverwaltung bleibt Admin-only.
  - Navigation angepasst:
    - Lokalisierer: nur Rollenliste + Lokalisierung (zusätzlich Main/Guide)
    - Changelog-Link für alle sichtbar (lesend).

## v0.1.105
- Anfrage: Lokalisierer sollen nichts ändern können.
- Antwort: Umgesetzt. Schreibrechte sind jetzt konsequent auf Admin beschränkt.
- Änderungen:
  - POST-Änderungen nur noch für Admin erlaubt auf:
    - Persona-Konfiguration
    - Persona-Liste bearbeiten
    - Rollenliste bearbeiten
    - Lokalisierungstexte bearbeiten
  - Lokalisierer können Seiten weiterhin sehen, aber keine Änderungen speichern.
  - Read-only-Hinweis in Persona-Konfiguration wieder auf "nur für Admin" zurückgestellt (mehrsprachig).

## v0.1.104
- Anfrage: Persona-Konfiguration ist trotz Admin-Login nicht mehr änderbar.
- Antwort: Korrigiert. Die Seite ist jetzt für angemeldete Nutzer wieder editierbar; ohne Login bleibt sie read-only.
- Änderungen:
  - Editier-Logik auf `config_personas` angepasst:
    - `can_edit` gilt für angemeldete Nutzer (Admin oder Lokalisierer).
    - ohne Anmeldung bleibt die Seite read-only.
  - Serverseitige POST-Prüfung angepasst (nur angemeldete Nutzer dürfen speichern).
  - Read-only-Hinweistext entsprechend aktualisiert und in allen Sprachen angepasst.

## v0.1.103
- Anfrage: Der Hinweistext in der Box (z. B. "CSV hochladen oder Testmodus nutzen...") soll auf jeder Seite den jeweils passenden Seitentext zeigen; bitte auf allen Seiten durchziehen.
- Antwort: Umgesetzt. Die Hinweis-Boxen verwenden jetzt seiten-spezifische i18n-Keys statt eines globalen `hint`-Keys.
- Änderungen:
  - Seiten-spezifische Hint-Keys eingeführt:
    - `indexHint` (Hauptseite)
    - `personasHint` (Persona-Konfiguration)
    - `personaNamesHint` (Persona-Liste)
    - `rolesHint` (Rollenliste)
  - Dadurch keine ungewollte Überschreibung des gleichen `hint`-Keys über mehrere Seiten mehr.
  - Bestehende Texte je Sprache beibehalten.

## v0.1.102
- Anfrage: Den Text "Nur lesender Modus: Änderungen sind nur für Admin möglich." für alle Sprachen in roter Schrift darstellen.
- Antwort: Umgesetzt. Der Read-only-Hinweis ist jetzt sprachunabhängig visuell rot hervorgehoben.
- Änderungen:
  - Stil des Read-only-Hinweises in `config_personas.html` angepasst:
    - Textfarbe rot
    - kräftigere rote Umrandung
    - fett dargestellt
  - Gilt automatisch für alle Sprachvarianten des lokalisierten Hinweises.

## v0.1.101
- Anfrage: Auf Persona-Konfiguration erscheinen ohne Anmeldung plötzlich alle Links.
- Antwort: Korrigiert. Die Navigation auf Persona-Konfiguration ist jetzt rollenabhängig wie auf den anderen Seiten.
- Änderungen:
  - `config_personas.html` Sidebar-Links eingeschränkt:
    - ohne Login: nur öffentliche Links + Persona-Konfiguration
    - Lokalisierer: zusätzlich Persona-Liste, Rollenliste, Lokalisierung
    - Admin: alle Admin-Links inkl. Auth-Konfiguration und Changelog

## v0.1.100
- Anfrage: Hinweis "Nur lesender Modus: Änderungen sind nur für Admin möglich." bitte für die jeweiligen Sprachen übersetzen.
- Antwort: Umgesetzt. Der Read-only-Hinweis in Persona-Konfiguration ist jetzt mehrsprachig lokalisiert.
- Änderungen:
  - Hinweistext auf i18n-Key `readonlyMode` umgestellt.
  - Übersetzungen ergänzt für DE/EN/IT/FR/PT/ES/ZH.

## v0.1.99
- Anfrage: Persona-Konfiguration ist für nicht angemeldete Benutzer nicht in der Linkleiste sichtbar.
- Antwort: Korrigiert. Der Link zur Persona-Konfiguration ist jetzt auch ohne Anmeldung in der Navigation sichtbar.
- Änderungen:
  - Navigation auf Hauptseite und Guide angepasst:
    - `Persona-Konfiguration` wird immer angezeigt.
    - Seite bleibt für nicht angemeldete Benutzer read-only.

## v0.1.98
- Anfrage: Persona-Konfiguration soll für nicht angemeldete Benutzer nur lesend angezeigt werden; es darf nichts geändert werden.
- Antwort: Umgesetzt. Die Seite ist jetzt ohne Login sichtbar, aber strikt read-only.
- Änderungen:
  - Zugriffsschutz angepasst: `/config-personas` nicht mehr hart admin-blockiert für GET.
  - Serverseitige Schreibsperre: POST auf `/config-personas` nur für Admin erlaubt.
  - UI-Read-only für nicht angemeldete Benutzer:
    - Hinweisbanner "Nur lesender Modus".
    - Permission-Mode-Auswahl deaktiviert.
    - Drag&Drop/Doppelklick-Entfernen deaktiviert.
    - Speichern-Button deaktiviert.

## v0.1.97
- Anfrage: In Persona-Konfiguration soll "Erklärung anzeigen" auch beim Hover anzeigen und nach rechts verschoben werden.
- Antwort: Umgesetzt. Der Button ist rechts ausgerichtet und zeigt die Erklärung jetzt zusätzlich beim Hover als Tooltip an (Klick öffnet weiterhin den Modal-Dialog).
- Änderungen:
  - `show-desc` Button in Persona-Header mit `margin-left:auto` nach rechts verschoben.
  - Hover-Tooltip ergänzt (`hoverTip`) mit sprachabhängigem Beschreibungstext.
  - Bestehender Klick-Dialog für ausführliche Anzeige bleibt aktiv.

## v0.1.96
- Anfrage: "Rolle:" auch für die einzelnen Sprachen übersetzen.
- Antwort: Umgesetzt. Die Rollenanzeige im Header ist jetzt mehrsprachig.
- Änderungen:
  - Header-Rollenanzeige (`Rolle` + Rollenwert `Admin/Lokalisierer`) auf allen relevanten Seiten i18n-fähig gemacht.
  - Unterstützte Übersetzungen ergänzt für DE/EN/IT/FR/PT/ES/ZH.
  - Anzeige bleibt weiterhin nur sichtbar, wenn angemeldet.

## v0.1.95
- Anfrage: Bei erfolgreichem Login links neben Login/Logout anzeigen, als welche Rolle man angemeldet ist. Wenn nicht angemeldet, keine Anzeige.
- Antwort: Umgesetzt. Im Header wird jetzt bei Anmeldung die aktive Rolle angezeigt (Admin oder Lokalisierer), ohne Anmeldung keine Rollenanzeige.
- Änderungen:
  - Rollenanzeige im Header ergänzt auf allen relevanten Seiten.
  - Darstellung:
    - angemeldet: `Rolle: Admin` oder `Rolle: Lokalisierer` + Logout
    - nicht angemeldet: nur Login, keine Rollenanzeige

## v0.1.94
- Anfrage: Login/Logout bei allen Seiten prüfen.
- Antwort: Umgesetzt. Login/Logout ist jetzt konsistent im Header über alle relevanten Seiten vorhanden.
- Änderungen:
  - Header auf folgenden Seiten vereinheitlicht mit Login/Logout-Link:
    - `changelog.html`
    - `config_auth.html`
    - `config_i18n.html`
    - `config_persona_names.html`
    - `config_personas.html`
    - `config_roles.html`
    - (bereits vorhanden: `index.html`, `guide.html`)
  - Verhalten:
    - angemeldet (`auth_admin` oder `auth_i18n`) -> `Logout`
    - nicht angemeldet -> `Login` (zur Hauptseite/Modal-Flow)

## v0.1.93
- Anfrage: Die Changelog-Seite hat keine Sprachauswahl im Header. Bitte alle Seiten prüfen. Ab jetzt wieder Changelog befüllen.
- Antwort: Umgesetzt. Changelog und Auth-Konfiguration haben jetzt Sprachumschaltung im Header; alle Templates wurden auf vorhandenen Sprachumschalter geprüft.
- Änderungen:
  - `changelog.html`:
    - Sprachauswahl im Header ergänzt (`langSwitch`).
    - Menü-/Download-Labels auf i18n umgestellt (DE/EN/IT/FR/PT/ES/ZH).
  - `config_auth.html`:
    - Sprachauswahl im Header ergänzt (`langSwitch`).
    - Relevante statische Labels i18n-fähig gemacht.
  - Audit über alle Templates durchgeführt:
    - Seiten mit Sprachumschalter: index, guide, config_personas, config_persona_names, config_roles, config_i18n, config_auth, changelog.
    - `login.html` bleibt ohne Sprachumschalter (wird nicht direkt genutzt; `/login` leitet auf Hauptseite).

## v0.1.91
- Anfrage: Persona-Liste bearbeiten und Rollenliste bearbeiten sind für Lokalisierer nicht sichtbar.
- Antwort: Umgesetzt. Die beiden Seiten sind in der Navigation für Lokalisierer jetzt sichtbar.
- Änderungen:
  - Menü auf Hauptseite und Guide für Lokalisierer erweitert um:
    - Persona-Liste bearbeiten
    - Rollenliste bearbeiten
    - Lokalisierungstexte bearbeiten

## v0.1.90
- Anfrage: Lokalisierer sollen in Persona-Liste bearbeiten und Rollenliste bearbeiten ebenfalls arbeiten können, aber nur in der Sprache, zu der das Passwort passt; andere Sprach-Erklärungen nur anzeigen.
- Antwort: Umgesetzt. Lokalisierer haben jetzt Zugriff auf beide Seiten, können dort jedoch ausschließlich die Beschreibung der aktuell autorisierten Sprache bearbeiten.
- Änderungen:
  - Zugriffsschutz erweitert:
    - `/config-roles` und `/config-persona-names` jetzt für Admin **oder** sprachpassenden Lokalisierer.
  - Lokalisierer-Bearbeitung eingeschränkt auf aktive Sprache:
    - Nur die aktive Sprachspalte ist editierbar.
    - Andere Sprachfelder sind read-only/disabled.
    - Rollen-/Persona-Listenverwaltung (Anlegen/Löschen/Umbenennen) bleibt Admin-only.
  - Serverseitige Absicherung ergänzt:
    - Bei Lokalisierer-POST werden ausschließlich Beschreibungen der aktiven Sprache gespeichert.
    - Listenstruktur bleibt unverändert.
  - Sidebars in den betroffenen Seiten nach Rolle angepasst (Admin vs. Lokalisierer).
  - Versehentliche URL-Rewrite-Snippets entfernt (kein Umschreiben auf `/` mehr).

## v0.1.89
- Anfrage: Den Hinweis "Diese Sprache ist aktuell nur lesbar..." bitte auch übersetzen und ggf. in die Seite Edit localization texts aufnehmen.
- Antwort: Umgesetzt. Der Read-only-Hinweis ist jetzt mehrsprachig und wird auf der Seite `Edit localization texts` sprachabhängig angezeigt.
- Änderungen:
  - Hinweistext in `/config-i18n` in i18n-Keys aufgeteilt (`readonlyNotice`, `readonlyNoticeSuffix`).
  - Übersetzungen für DE/EN/IT/FR/PT/ES/ZH ergänzt.
  - Anzeige bleibt dynamisch mit der aktuell gewählten Sprachkennung (z. B. EN/DE).

## v0.1.88
- Anfrage: Beim Lokalisierer werden alle Links angezeigt; es soll nur die Seite Lokalisierungstexte bearbeiten sichtbar sein.
- Antwort: Umgesetzt. Für Lokalisierer wird in der Navigation jetzt nur noch der Link zur Lokalisierungsseite angezeigt.
- Änderungen:
  - Sidebar-Logik auf Hauptseite/Guide getrennt nach Rollen:
    - Admin: alle Admin-Links
    - Lokalisierer: nur `Lokalisierungstexte bearbeiten`
  - Auch in `/config-i18n`-Sidebar sind Admin-Links für Lokalisierer ausgeblendet.

## v0.1.87
- Anfrage: Im Login auswählbar machen, ob Anmeldung als Admin oder Lokalisierer erfolgt. Bei Lokalisierer-Login soll die Seite Lokalisierungstexte bearbeiten sichtbar sein, aber nur die Sprache editierbar sein, für die das Lokalisierer-Passwort gilt.
- Antwort: Umgesetzt. Der Login bietet jetzt Rollenwahl (Admin/Lokalisierer) plus Sprachwahl für Lokalisierer. Die Bearbeitung in `/config-i18n` bleibt sprachgebunden.
- Änderungen:
  - Login-Modal erweitert um Auswahl `Admin` / `Lokalisierer`.
  - Bei Auswahl `Lokalisierer` wird zusätzlich die Zielsprache ausgewählt.
  - Backend-Login prüft rollen- und sprachspezifisch; bei erzwungenem Login-Challenge (geschützte Seite) bleiben Scope/Sprache verbindlich.
  - Session speichert I18N-Berechtigungen pro Sprache; Navigation zeigt i18n-Seite für Lokalisierer-Login weiterhin an.
  - Bereits vorhandene Logik bleibt aktiv: In `/config-i18n` ist nur die per Passwort freigeschaltete Sprache editierbar, andere Sprachen sind read-only.

## v0.1.86
- Anfrage: Für jede Sprache muss ein Passwort vergeben werden können. Ein Inputfeld pro Sprache reicht, Wiederholung ist nicht nötig. In Lokalisierungstexte bearbeiten darf nur editiert werden, wenn das Passwort zur Sprache passt.
- Antwort: Umgesetzt. I18N-Passwörter sind jetzt sprachspezifisch (ein Feld je Sprache) und die Bearbeitung in `/config-i18n` ist nur mit passender Sprach-Anmeldung möglich.
- Änderungen:
  - Auth-Settings auf sprachspezifische I18N-Hashes umgestellt (`i18n_hashes` je Sprache, Migration von altem `i18n_hash` berücksichtigt).
  - `/config-auth` neu aufgebaut:
    - ein Passwortfeld pro Sprache (DE/EN/IT/FR/PT/ES/ZH)
    - kein doppeltes Bestätigungsfeld mehr für Sprachpasswörter.
  - Login-Challenge erweitert um Sprachkontext (`login_lang`).
  - I18N-Login prüft jetzt Passwort gegen die Zielsprache und speichert Sprachberechtigung in der Session.
  - `/config-i18n`:
    - Speichern nur erlaubt, wenn passende Sprachberechtigung vorhanden ist.
    - Ohne passende Sprachberechtigung nur lesbar (Inputs/Save deaktiviert + Hinweis).
  - Nebenbei: irrtümliche URL-Rewrite-Logik in `config_i18n.html` entfernt.

## v0.1.78
- Anfrage: docker-compose.example.yaml kann doch auch raus die ist doch im Deployment Bundle ZIP. Programmdateien als ZIP ist doch auch unnötig. Es reicht doch Deployment Bundle ZIP?
- Antwort: Ja, angepasst. Im Changelog-Webinterface wird jetzt nur noch der Download `Deployment Bundle ZIP` angezeigt.
- Änderungen:
  - Downloadbereich in `changelog.html` auf einen einzigen Link reduziert (`/download/deploy-bundle`).

## v0.1.77
- Anfrage: Aufgabe aus dem deployment Bundle raus. Es muss nur das Programme, die Anleitung und docker Buildfile und yaml drin sein.
- Antwort: Umgesetzt. Das Deployment-Bundle enthält jetzt nur Programmdateien + Deploy-Dateien, ohne `Aufgabe/`.
- Änderungen:
  - `/download/deploy-bundle` erweitert: enthält jetzt Programmdateien (`app/`, `requirements.txt`, optional `README.md`) plus `Dockerfile`, `docker-compose.example.yaml`, `DEPLOY_EN.md`.
  - `Aufgabe/` wird explizit nicht mehr ins Deployment-Bundle aufgenommen.
  - Deploy-Anleitung im Bundle entsprechend angepasst.

## v0.1.76
- Anfrage: Auch alle anderen Buttons so anpassen wie im Changlog.
- Antwort: Umgesetzt. Die Button-Optik wurde über die Templates hinweg auf den Changelog-Linkstil vereinheitlicht.
- Änderungen:
  - Standard-Buttons in allen Seiten auf hellen Link-/Outline-Stil umgestellt (weißer Hintergrund, blauer Text, Rahmen, Hover in hellblau).
  - Danger-Buttons bleiben rot und behalten klaren Warncharakter.

## v0.1.75
- Anfrage: (aktuell, inkl. Version im Dateinamen) kann weg und mach mal die Downloadlinks so schön wie andere Links in der Anwendung und nebeneinander.
- Antwort: Umgesetzt. Der Zusatztext wurde entfernt und die Downloadlinks sind jetzt als gleichartige UI-Links nebeneinander dargestellt.
- Änderungen:
  - Download-Text bei `Programmdateien als ZIP` gekürzt.
  - Downloadbereich auf horizontale Linkbuttons umgestellt (`download-links`, `dl-link`).
  - Styling an Navigations-/UI-Linkstil angeglichen.

## v0.1.74
- Anfrage: Bitte dann build file und docker-compose.example.yaml auch in ein Zip Packen. Dazu noch eine Anleitung in englisch wie man das deployd. Wenn das Änderungen nötig sind bitte auch on the fly aktualisieren.
- Antwort: Umgesetzt. Es gibt jetzt ein Deployment-Bundle-ZIP mit Compose-Beispiel, Dockerfile und englischer Deployment-Anleitung.
- Änderungen:
  - Neue Download-Route: `/download/deploy-bundle`.
  - ZIP-Inhalt:
    - `docker-compose.example.yaml` (aus dem aktuellen Projektstand)
    - `Dockerfile` (aktueller Stand)
    - `DEPLOY_EN.md` (englische Deploy-Anleitung)
  - Dateiname enthält die aktuelle Version: `rolemapper-deploy-bundle-v<version>.zip`.
  - Changelog-Downloadbereich um den neuen Bundle-Link erweitert.

## v0.1.73
- Anfrage: Kannst Du im changlog noch ein Beispiel docker-compose.yaml als Download zur verfügung stellen? Und Die Programmdateien als zip ebenfalls? Das Zip sollte immer aktuell gehalten werden. Gern auch als versionsnummer.zip
- Antwort: Umgesetzt. Im Changelog-Webinterface gibt es jetzt Download-Links für ein Compose-Beispiel und ein stets aktuelles Projekt-ZIP mit Versionsnummer.
- Änderungen:
  - Neue Download-Route: `/download/docker-compose-example` (liefert `docker-compose.example.yaml`).
  - Neue Download-Route: `/download/project-zip` (erstellt ZIP on-the-fly aus aktuellem Projektstand).
  - ZIP-Dateiname enthält die App-Version: `rolemapper-v<version>.zip`.
  - Changelog-Seite um Download-Bereich mit beiden Links erweitert.

## v0.1.72
- Anfrage: Die mehrfarbigkeit ist verschwunden.
- Antwort: Behoben. Die Mehrfarbigkeit ist wieder aktiv.
- Änderungen:
  - Changelog-Renderer korrigiert: Beim Start eines Versionsblocks (`## v...`) wird der Systemblock-Modus zurückgesetzt.
  - Dadurch werden Anfrage/Antwort/Änderungen wieder in ihren jeweiligen Farben dargestellt.

## v0.1.71
- Anfrage: # Rolemapper – Änderungsprotokoll (fortlaufend) / Dieses Dokument hält die Änderungen pro Version fest. bitte von der Box trennen.
- Antwort: Umgesetzt. Die beiden Kopfzeilen stehen jetzt außerhalb der Intro-Box.
- Änderungen:
  - Changelog-Renderer startet die Intro-Box erst ab `## Permanente Systembeschreibung`.
  - Titel + Unterzeile bleiben separat und unboxed sichtbar.

## v0.1.70
- Anfrage: Bitte verschönere auch den Bereich der oberhalb der Versionen sichtbar ist.
- Antwort: Umgesetzt. Der obere Einleitungsbereich wird jetzt in einer eigenen hervorgehobenen Intro-Box dargestellt.
- Änderungen:
  - Neue `intro-box` im Changelog-Webinterface.
  - Renderer startet vor den Versionen automatisch im Intro-Container.
  - Intro-Container wird beim ersten Versionsblock sauber geschlossen.

## v0.1.69
- Anfrage: Prüfe noch mal bitte in der technischen Umsetzung ist bei den eingerückten eine andere Farbe. Und Du kannst gern bei den einzelnen Versionen mit eine schönen Box das besser leserlich machen.
- Antwort: Umgesetzt. Der Technikblock färbt jetzt auch eingerückte Zeilen konsistent, und jede Version wird in einer eigenen Box dargestellt.
- Änderungen:
  - Changelog-Renderer: Systemblock erkennt jetzt eingerückte Bulletpoints per Regex (`^\s*-`).
  - Changelog-Renderer: Versionsabschnitte (`## v...`) werden als visuelle Karten/Boxen gerendert.
  - Neue CSS-Klassen für bessere Lesbarkeit: `version-box`, `version-title`.

## v0.1.68
- Anfrage: ### Technische Umsetzung ... bitte noch mit einer anderen Farbe.
- Antwort: Umgesetzt. Der permanente Technik-/Deployment-Abschnitt ist im Changelog-Webinterface jetzt in eigener Farbe hervorgehoben.
- Änderungen:
  - Neue Darstellungsfarbe für den permanenten Systemblock (lila).
  - Renderer erkennt die Blöcke unter `### Technische Umsetzung` und `### Was für produktives Deployment nötig ist` und markiert deren Unterzeilen entsprechend.

## v0.1.67
- Anfrage: Es ist nur Änderungen orange nicht was geändert wurde. Bitte ändern.
- Antwort: Umgesetzt. Jetzt werden auch die Änderungs-Bulletpoints selbst orange markiert, nicht nur die Überschrift.
- Änderungen:
  - Changelog-Renderer angepasst: alle Zeilen mit `- ` bzw. `  - ` werden als Änderungszeilen orange hervorgehoben.

## v0.1.66
- Anfrage: Kannst Du im Webinterface im changelog die Anfrage, Antwort und Änderung unterschiedlich farbig kennzeichnen?
- Antwort: Ja, umgesetzt. Die drei Typen sind jetzt im Changelog-Webinterface farblich unterscheidbar.
- Änderungen:
  - Changelog-Seite rendert Inhalte zeilenweise statt als statisches `pre`.
  - Farbcodes im Webinterface:
    - Anfrage: blau
    - Antwort: grün
    - Änderungen: orange
  - Sichere HTML-Escaping-Logik beim Rendern integriert.

## v0.1.65
- Anfrage: Beispielrollen einfügen funktioniert nicht, bitte prüfen. Und "Test-Zuordnung erstellen" in "Mapping beginnen" ändern. Achte auf die Mehrsprachigkeit.
- Antwort: Fehler behoben und Beschriftung mehrsprachig angepasst.
- Änderungen:
  - Ursache behoben: JavaScript wurde durch unescaped Apostrophe in FR-Texten unterbrochen (`sec.testTitle`, `btn.fillSample`).
  - `Beispielrollen einfügen` funktioniert wieder.
  - Buttontext `Test-Zuordnung erstellen` wurde in allen Sprachen auf `Mapping beginnen` (bzw. sprachäquivalente Form) geändert.
  - Kleine Korrektur: Dateinamenlabel-Check nutzt jetzt `mapping_file` statt veraltetem `csv_file`.

## v0.1.63
- Anfrage: Kannst Du 2) Externe Authentifizierungsrollen so umbauen, dass in der Textbox beim neu Laden der Seite nicht drin steht und füge einen Button für das Einfügen der Beispielrollen ein.
- Antwort: Umgesetzt. Textbox ist beim Laden leer, und ein Button zum Einfügen der Beispielrollen ist ergänzt.
- Änderungen:
  - Abschnitt 2 (`Externe Authentifizierungsrollen`) startet jetzt mit leerem Textfeld.
  - Neuer Button: `Beispielrollen einfügen` (mehrsprachig).
  - Button füllt das Textfeld mit den bekannten Beispielrollen aus `default_test_roles`.

## v0.1.62
- Anfrage: Nimm bitte den CSV Upload / CSV hochladen raus. Dafür änderst du 2) Test ohne CSV in 2) externe Authentifizierungsrollen um. Achte auf die Mehrsprachigkeit. Es soll in Zukunft nur notwendig sein entweder die mapping.txt zu importieren oder per copy&paste die Rollen in 2) einzufügen. Passe das bitte an.
- Antwort: Umgesetzt. CSV-Upload wurde aus der Hauptlogik entfernt, stattdessen mapping.txt-Import + Rollen per Copy/Paste in Abschnitt 2.
- Änderungen:
  - Neue Aktion `mapping_upload` im Backend mit Parser für `mapping.txt` (SOURCE aus `SOURCE=TARGET`).
  - Abschnitt 1 auf `mapping.txt`-Import umgestellt (Datei-Upload `.txt`).
  - Abschnitt 2 in allen Sprachen auf „externe Authentifizierungsrollen“ umbenannt.
  - Texte/Buttons/Hints auf der Hauptseite mehrsprachig angepasst (DE/EN/IT/FR/PT/ES/ZH).
  - Ladehinweise aktualisiert: kein CSV-Bezug mehr, Fokus auf `mapping.txt` oder Copy/Paste.

## v0.1.61
- Anfrage: "Rollenliste bearbeiten" muss auch eine Erklärungsspalte haben wie in "Persona-Liste bearbeiten". Achte auf die Mehrsprachigkeit!
- Antwort: Umgesetzt. `Rollenliste bearbeiten` hat jetzt eine mehrsprachige Erklärungsspalte wie die Persona-Liste.
- Änderungen:
  - Backend: `role_descriptions.json` eingeführt.
  - Backend: Laden/Speichern mehrsprachiger Rollen-Erklärungen (`de/en/it/fr/pt/es/zh`).
  - Backend: `/config-roles` verarbeitet jetzt pro Zeile `role + description{lang}`.
  - Frontend: `config_roles.html` auf Tabellen-Editor mit Spalten `Rolle | Erklärung | Aktion` umgebaut.
  - Frontend: Für jede Rolle sind Erklärungen je Sprache editierbar (Länderkürzel pro Zeile).
  - Frontend: Suche, Zeile hinzufügen, Löschen mit Rückfrage, A–Z-Sortierung beim Speichern bleiben enthalten.

## v0.1.60
- Anfrage: Kannst Du die Seite "Rollenliste bearbeiten" auch so aufbauen wie "Persona-Liste bearbeiten"?
- Antwort: Ja, umgesetzt. Die Rollenliste wurde auf das gleiche interaktive Listen-Layout umgebaut.
- Änderungen:
  - `Rollenliste bearbeiten` von Textarea auf Zeilen-Editor umgestellt.
  - Funktionen: Suche, neue Zeile hinzufügen, einzelne Zeile löschen (mit Rückfrage), A–Z-Sortierung beim Speichern.
  - `rows_json`-Speicherpfad im Backend ergänzt (Fallback auf altes Textformat bleibt möglich).
  - Navigation + i18n konsistent mit bestehendem UI-Pattern.

## v0.1.59
- Anfrage: Kannst Du die CHANGELOG.md auch in die Anwendung mit einbauen? Das dass auch andere nachvollziehen können.
- Antwort: Ja, umgesetzt. Es gibt jetzt eine eigene Seite `/changelog` in der Anwendung.
- Umsetzung:
  - Neue Route `/changelog` in Flask, liest `Aufgabe/CHANGELOG.md` und zeigt sie in der App an.
  - Neue Seite `changelog.html` erstellt.
  - Link `Changelog` in die Seiten-Navigation aufgenommen.
  - i18n-Navigation um `nav.changelog` ergänzt.

## v0.1.58+log-policy
- Anfrage: Bitte bei Änderungen in der changelog.md auch meine Anfrage an Dich und Deine Antwort mit rein nehmen.
- Antwort: Verstanden. Ab jetzt werden bei neuen Änderungen in der `CHANGELOG.md` zusätzlich die jeweilige Anfrage und die gegebene Antwort mit dokumentiert.

## v0.1.58
- Reihenfolge in der Linkleiste korrigiert (Guide-Seite):
  - `Persona-Liste bearbeiten` vor `Rollenliste bearbeiten`.
- Dadurch kein „Positionswechsel“ der beiden Menüpunkte mehr beim Navigieren.

## v0.1.57
- Linkleisten-Übersetzungen bereinigt (u. a. ES/PT-Konsistenz, fehlende ZH-Einträge).
- Sprachstabilität beim Seitenwechsel verbessert:
  - Menülinks übernehmen aktive Sprache via `?lang=`.
  - Zusätzlich bleibt Cookie/LocalStorage-Sync aktiv.

## v0.1.56
- Key `showDesc` ("Erklärung anzeigen") in i18n-Defaults aufgenommen,
  damit in "Lokalisierungstexte bearbeiten" pflegbar.

## v0.1.55
- In "Persona-Konfiguration" Button "Erklärung anzeigen" neben den Persona-Namen platziert (statt darunter).

## v0.1.54
- In "Persona-Konfiguration" pro Persona Button "Erklärung anzeigen" ergänzt.
- Klick öffnet Modal-Fenster mit Erklärungstext in aktuell gewählter Sprache.
- Lokalisierte Modal-Texte ergänzt (`showDesc`, `close`, `noDesc`).

## v0.1.53
- Hinweistext in "Persona-Liste bearbeiten" in allen Sprachen angepasst:
  - bestehende Persona-Namen nicht editierbar,
  - nur Erklärung editierbar,
  - neue Zeile erlaubt neue Persona.
- Gleiches auch in i18n-Defaults für die Lokalisierungsseite aktualisiert.

## v0.1.52
- "Persona-Liste bearbeiten" auf mehrsprachige Erklärungsstruktur erweitert:
  - pro Persona Zeilen für `de/en/it/fr/pt/es/zh` in der Erklärungsspalte,
  - Länderkürzel vor jeder Zeile,
  - neue Zeilen + löschen + A–Z-Sortierung beibehalten.
- Backend auf strukturierte Persona-Beschreibungen umgestellt (`Dict[persona][lang]`).
- Import aus `Aufgabe/Rollen in DU.xlsx` (A=Persona, C=Erklärung, B ignorieren) mit Initialbefüllung aller Sprachen.

## v0.1.51
- Neue Persona-Listen-Texte als lokalisierbare Keys ergänzt (`persona_names.*`).
- "Persona-Liste bearbeiten" nutzt nun Overrides aus "Lokalisierungstexte bearbeiten".

## v0.1.50
- Lösch-Bestätigungsdialog in "Persona-Liste bearbeiten" für alle Sprachen ergänzt.

## v0.1.49
- In "Persona-Liste bearbeiten": Löschen nur noch nach Rückfrage (Confirm-Dialog).

## v0.1.48
- "Persona-Liste bearbeiten" komplett umgebaut (ähnlich Lokalisierungsseite):
  - Spalten: Persona | Erklärung | Aktion,
  - Suche,
  - neue Zeile hinzufügen,
  - einzelne Zeilen löschen,
  - A–Z-Sortierung,
  - bestehende Persona-Namen read-only,
  - nur Erklärung editierbar.
- Importquelle `Rollen in DU.xlsx` integriert (Tabelle1, Spalte A + C).

## v0.1.47
- Reihenfolge in der Navigation getauscht:
  - `Persona-Liste bearbeiten` vor `Rollenliste bearbeiten`.

## v0.1.46
- Backend-Flashmeldungen (`t()`) um zusätzliche Sprachen erweitert:
  - IT, FR, PT, ES, ZH (neben DE/EN).
- Meldungen wie "Testmodus bereit ..." jetzt sprachabhängig.

## v0.1.45
- "Lokalisierungstexte bearbeiten":
  - Spalte "Beispiel/Testtext" entfernt.
  - Live-Suche nach Key/Text ergänzt.

## v0.1.44
- CSV-Upload-Pfad gehärtet:
  - Header und Zellinhalte werden serverseitig sanitisiert,
  - `<`/`>` neutralisiert, Null-Bytes entfernt.

## v0.1.43
- Zusätzliche Eingabehärtung für:
  - Rollenliste,
  - Persona-Liste,
  - Lokalisierungstexte.
- Speichern als reiner Text, unsichere Zeichen neutralisiert.

## v0.1.42
- Formular-Routen vereinheitlicht.

## v0.1.41
- Überflüssiges `'` am Ende der Insider-Texte entfernt.

## v0.1.40
- Insider-Link repariert (JS-Bruch durch fehlerhafte `insiderText`-Zeilen behoben).

## v0.1.39
- Ghost-Emoji `👻` am Beginn der Insidertexte ergänzt.

## v0.1.38
- Insider-Hint in allen Sprachen auf längere Variante umgestellt.

## v0.1.37
- Deutschen Insidertext auf gewünschte Formulierung gesetzt.

## v0.1.36
- Insider-Begrüßung in allen Sprachen angepasst.

## v0.1.35
- Hinweistext "Insider-Hint ist ausgeschlossen." in Lokalisierungsseite entfernt.

## v0.1.34
- Fehler in Lokalisierungsseite behoben:
  - `I18N_EDITOR_DEFAULTS` auf alle Sprachen erweitert (nicht nur DE/EN).

## v0.1.33
- Sprachpersistenz für `/config-i18n` stabilisiert:
  - Cookie `rolemapper_lang` eingeführt,
  - Priorität: `?lang` → Cookie → DE.

## v0.1.32
- JS-Apostroph-Fehler in `config_i18n.html` behoben (IT/FR),
  damit Sprachlogik wieder korrekt läuft.

## v0.1.31
- Lokalisierungsseite übernimmt Bearbeitungssprache nur noch vom Header-Sprachwähler.
- Interner Sprachselector entfernt.

## v0.1.30
- `config_i18n.html` vollständig lokalisiert (inkl. Linkleiste).
- On-the-fly Sprachwechsel auf der Lokalisierungsseite ergänzt.

## v0.1.29
- Menülink `Lokalisierungstexte bearbeiten` als i18n-Key `nav.i18n` in allen Seiten ergänzt.

## v0.1.28
- `config-i18n` umgebaut:
  - Bearbeitung pro Sprache,
  - pro Key eigene Zeile mit editierbarem Feld,
  - Anleitungstexte (`guide.*`) mit aufgenommen.

## v0.1.27
- Neue Seite `/config-i18n` ergänzt (JSON-basierte Lokalisierungs-Overrides, ohne Insider-Keys).

## v0.1.26
- Insider-Hint-Fehler behoben (französische Apostrophe escaped).

## v0.1.25
- Insider-Hint mehrsprachig gemacht (Titel/Text/Close).

## v0.1.24
- Insidertext auf "Variante 3" + Spaßfaktor gesetzt.

## v0.1.23
- Abstand zwischen `Rolemappe` und klickbarem `r` beseitigt (Wrapper-Lösung).

## v0.1.22
- Insider-Codeabfrage entfernt, direkte Modal-Öffnung wiederhergestellt.

## v0.1.21
- `ORBIS`-Schreibweise korrigiert.
- Insider-Link als letztes `r` im Titel umgesetzt.

## v0.1.20
- Versteckten Insider-Link (`r`) + Modal auf Hauptseite ergänzt.

## v0.1.19
- Italienisch (`IT`) als Sprache ergänzt (nach EN), inkl. Übersetzungen auf allen Hauptseiten.

## v0.1.18
- On-the-fly Menüübersetzung bereinigt, Duplikat-Keys entfernt, ZH ergänzt.

## v0.1.17
- Backend-Flashtexte sprachabhängig gemacht (über `ui_lang`).

## v0.1.16 und früher
- Grundaufbau Rolemapper (Flask), Mapping-Logik, Prefill aus Mapping-TXT,
  Permission-Kompatibilität, responsive Layouts, mehrsprachige UI-Basis,
  Docker-Artefakte und Dateinamensschema `mapping-YYYYMMDD-HHMMSS.txt`.

## Hinweis
- Dieses Changelog wird fortlaufend ergänzt.
- Bei jeder neuen Version bitte oben einen neuen Abschnitt hinzufügen.
