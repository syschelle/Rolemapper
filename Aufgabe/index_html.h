// index_html.h
#pragma once

// Favicon (base64-encoded)
const char FAVICON_ICO_BASE64[] PROGMEM = 
"AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAAAQAAAAAAAAAAAAAAAAA"
"AAAAAAD///8Af39/AFhYWAAgICAATU1NAH5+fgBQUFAAZGRkADY2NgB9fX0ARUVFAFlZWQA/Pz8A"
"bm5uAERERABra2sAenp6AEpKSgA7OzsAioqKAFtbWwBVVVUAISEhADAwMAD+/v4AAAAAAAAAAAAA"
"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAAAACAAIAAgACAgICAAIAAgICAgACA"
"AICAgIAAgACAgICAAIAAgICAgACAAICAgIAAgACAgICAAIAAgICAgACAAICAgIAAgACAgICAAIAA"
"gICAgACAAICAgIAAgACAgICAAIAAgICAgACAAICAgIAAgACAgICAAIAAgICAgACAAICAgIAAgAAA"
"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD//wAA"
"//8AAP//AAD//wAA//8AAP//AAD//wAA";

// ------- i18n: manifest + Sprachen (separat, eigene Routen) -------
static const char I18N_MANIFEST[] PROGMEM = R"json(
{
  "default": "de",
  "languages": [
    { "code": "de", "name": "Deutsch", "dir": "ltr", "file": "de" },
    { "code": "en", "name": "English", "dir": "ltr", "file": "en" }
  ]
}
)json";

static const char I18N_DE[] PROGMEM = R"json(
{
  "app.title": "Mein Webfrontend",
  "settings.themeLight": "Hell",
  "settings.themeDark": "Dunkel",
  "status.title": "Status",
  "status.ok": "System läuft normal ✅"
}
)json";

static const char I18N_EN[] PROGMEM = R"json(
{
  "app.title": "My Web Frontend",
  "settings.themeLight": "Light",
  "settings.themeDark": "Dark",
  "status.title": "Status",
  "status.ok": "System is running ✅"
}
)json";

const char* htmlPage = R"rawliteral(
<!DOCTYPE html>
<html lang="en">
<meta name="viewport" content="width=device-width, initial-scale=1">
<head>
  <title>%CONTROLLERNAME%</title>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="/style.css">
</head>
<body>
  <header class="header">
    <button class="hamburger" id="hamburgerBtn" data-i18n="a11y.menu" data-i18n-attr="aria-label" aria-label="Menü öffnen/schließen" aria-expanded="false" aria-controls="sidebar">☰</button>
    <div class="title" data-i18n="app.title">%CONTROLLERNAME%</div>
    <span id="unsavedHint" class="dirty-hint" hidden data-i18n="settings.unsaved"></span>
    <div class='grow-info'>%CURRENTGROW%<BR>%CURRENTPHASE%</div>
    <div id="grow-line" data-i18n-key="info.growLine"></div>
    <div class="datetime">
      <div id="headerDate"></div>
      <div id="headerTime"></div>
    </div>
</header>
  <div class="layout">
    <nav class="sidebar" id="sidebar">
      <a class="navlink" data-page="status"   data-i18n="nav.status">Status</a>
      <a class="navlink" data-page="diary"   data-i18n="nav.diary">Grow Diary</a>
      <a class="navlink" data-page="runsettings" data-i18n="nav.runsetting">Betriebseinstellungen</a>
      <a class="navlink" data-page="shelly" data-i18n="nav.shelly">Shelly Einstellungen</a>
      <a class="navlink" data-page="settings" data-i18n="nav.settings">Systemeinstellungen</a>
      <a class="navlink" data-page="message" data-i18n="nav.message">Push-Einstellungen</a>
      <a class="navlink" data-page="logging" data-i18n="nav.logging">Systemprotokoll</a>
      <a class="navlink" data-page="vars" data-i18n="nav.vars">Variablen</a>
      <a class="navlink" data-page="factory" data-i18n="nav.factory">Werkseinstellungen</a>
    </nav>

  <div class="overlay" id="overlay"></div>

  <main class="content" id="content">

    <!-- status section -->
    <section id="status" class="page active card">
      <h1 data-i18n="status.title">Status</h1>
      <!-- Letztes Update direkt unter dem Statustext -->
      <p class="last-update">
        <span data-i18n="status.updated">Letztes Update:</span>
        <span id="capturedSpan">--</span>
      </p>
      <p style="margin-top:10px">
        <a class="btn danger" href="/download/history" data-i18n="status.download">CSV herunterladen</a>
        <a class="btn danger" href="/deletelog" data-i18n="status.delete">CSV löschen</a>
      </p>
      
      <div class="spacer"></div>
      <h2 data-i18n="status.currentValues">aktuelle Werte</h2>
      <!-- 3 values side by side -->
      <div class="metrics-row">
        <div class="metric">
          <div class="twoinone-label">
            <div class="metric-label" data-i18n="status.temperature">Temperatur</div>
            <div class="metric-value">
              <span id="tempSpan">–</span><span class="unit">°C</span>
            </div>
          </div>
          <div class="spacer"></div>
          <div class="metric-sub">
            <div class="twoinone-label">
              <span data-i18n="status.targetTemp">Soll</span>
              <div class="metric-value">
                <span id="targetTempStatus">%TARGETTEMPERATURE%</span> <span class="unit">°C</span>
              </div>
            </div>
          </div>
          <div class="spacer"></div>
          <div class="metric-submetric">
            <div class="twoinone-label">
              <div class="metric-label">%DS18B20NAME%</div>
              <div class="metric-value">
                <span id="waterTempSpan">%WATERTEMPERATURE%</span><span class="unit">°C</span>
            </div>
          </div>
        </div>
        </div>

        <div class="metric">
          <div class="twoinone-label">
            <div class="metric-label" data-i18n="status.humidity">Luftfeuchte</div>
            <div class="metric-value">
              <span id="humSpan">–</span><span class="unit">%</span>
            </div>
          </div>
        </div>

        <div class="metric">
          <div class="twoinone-label">
            <div class="metric-label" data-i18n="status.lastvpd">VPD</div>
            <div class="metric-value">
              <span id="vpdSpan">–</span><span class="unit">kPa</span>
            </div>
          </div>
          <div class="spacer"></div>
          <div class="metric-sub">
            <div class="twoinone-label">
              <span data-i18n="status.targetVpd">Soll</span>
              <div class="metric-value">
                <span id="targetVpdStatus">%TARGETVPD%</span> <span class="unit">kPa</span>
              </div>
            </div>
          </div>
          <div class="spacer"></div>
          <div class="metric-sub">
            <div class="twoinone-label">
              <span data-i18n="runsetting.offsetLeafTemperature">Offset Blatttemperatur:</span>
              <div class="metric-value">
                <span id="leafTempStatus">%LEAFTEMPERATURE%</span> <span class="unit">°C</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="spacer"></div>
      <div class="history-head">
        <h2 data-i18n="status.history">Verlauf (letzte Stunde)</h2>
        <button class="btn" type="button" onclick="updateHistoryCharts(true)" data-i18n="status.refresh">Aktualisieren</button>
      </div>
      <div class="history-grid">
        <!-- Temperatur -->
        <div class="chart-card">
          <div class="chart-title" data-i18n="status.temperature">Temperatur</div>
          <canvas id="chartTemp" height="110"></canvas>
          <div class="chart-foot">
            <span>Min:</span> <span id="chartTempMin">–</span>
            <span class="sep">·</span>
            <span>Avg:</span> <span id="chartTempAvg">–</span>
            <span class="sep">·</span>
            <span>Max:</span> <span id="chartTempMax">–</span>
            <span class="unit">°C</span>
          </div>
        </div>

        <!-- Luftfeuchte -->
        <div class="chart-card">
          <div class="chart-title" data-i18n="status.humidity">Luftfeuchte</div>
          <canvas id="chartHum" height="110"></canvas>
          <div class="chart-foot">
            <span>Min:</span> <span id="chartHumMin">–</span>
            <span class="sep">·</span>
            <span>Avg:</span> <span id="chartHumAvg">–</span>
            <span class="sep">·</span>
            <span>Max:</span> <span id="chartHumMax">–</span>
            <span class="unit">%</span>
          </div>
        </div>

        <!-- VPD -->
        <div class="chart-card">
          <div class="chart-title">VPD</div>
          <canvas id="chartVpd" height="110"></canvas>
          <div class="chart-foot">
            <span>Min:</span> <span id="chartVpdMin">–</span>
            <span class="sep">·</span>
            <span>Avg:</span> <span id="chartVpdAvg">–</span>
            <span class="sep">·</span>
            <span>Max:</span> <span id="chartVpdMax">–</span>
            <span class="unit">kPa</span>
          </div>
        </div>

        <!-- %DS18B20NAME% -->
        <div class="chart-card" id="chartWaterCard">
          <div class="chart-title">%DS18B20NAME%</div>
          <canvas id="chartWater" height="110"></canvas>
          <div class="chart-foot">
            <span>Min:</span> <span id="chartWaterMin">–</span>
            <span class="sep">·</span>
            <span>Avg:</span> <span id="chartWaterAvg">–</span>
            <span class="sep">·</span>
            <span>Max:</span> <span id="chartWaterMax">–</span>
            <span class="unit">°C</span>
          </div>
        </div>
      </div>

    <h2 data-i18n="status.relayIrrigation">Bewässerungssteuerung</h2>
    <div class="relay-row" id="pumpRow">
      <div class="relay-card" data-relay="6">
        <div class="relay-title"  data-i18n="status.irrigationPump1">Pumpe 1</div>
        <div class="relay-status" id="relay-Status6"></div>
        <div class="spacer"></div>
        <button class="primary" data-i18n="status.relayOn" onclick="onForTenSec(6)">Toggle</button>
      </div>
      <div class="relay-card" data-relay="7">
        <div class="relay-title" data-i18n="status.irrigationPump2">Pumpe 2</div>
        <div class="relay-status" id="relay-Status7"></div>
        <div class="spacer"></div>
        <button class="primary" data-i18n="status.relayOn" onclick="onForTenSec(7)">Toggle</button>
      </div>
      <div class="relay-card" data-relay="8">
        <div class="relay-title" data-i18n="status.irrigationPump3">Pumpe 3</div>
        <div class="relay-status" id="relay-Status8"></div>
        <div class="spacer"></div>
        <button class="primary" data-i18n="status.relayOn" onclick="onForTenSec(8)">Toggle</button>
      </div>
      <div class="relay-card" data-relay="watering">
        <div class="relay-title" data-i18n="status.watering">Bewässerung</div>
        <div class="metric-value">
          <span id="irrigationSpan"  >-</span><span class="unit" data-i18n="status.wateringLeft"> verbleibend</span>
        </div>
        <div class="metric-value">
          <span class="unit" data-i18n="status.endIn" >Ende in </span><span id="irTimeLeftSpan"  ></span>
        </div> 
        <div class="spacermini"></div>
        <button class="primary" onclick="startWatering()">Toggle</button>
      </div>
      <div class="relay-card" data-relay="TankFilling">
        <div class="relay-title" data-i18n="status.tank">Tank Füllung</div>
        <div class="metric-value">
          <span id="tankLevelSpan" >–</span><span class="unit" >&nbsp;%</span>
        </div>
        <div class="metric-value">
          <span id="tankCMDistanceSpan" >–</span><span class="unit" >&nbsp;cm</span>
        </div>
        <div class="spacermini"></div>
        <button class="primary" data-i18n="status.pingTank" onclick="pingTank()">Ping</button>
      </div>
    </div>

    <div class="spacer"></div>
    <h2 data-i18n="status.relayControl">Relais Steuerung</h2>
    <div class="relay-row" id="relayRow">
      <div class="relay-card" data-relay="1">
        <div class="relay-title">%RELAYNAMES1%</div>
        <div class="relay-status" id="relay-Status1"></div>
        <div class="spacer"></div>
        <button class="primary" data-i18n="status.toggleRelay" onclick="toggleRelay(1)">Toggle</button>
      </div>
      <div class="relay-card" data-relay="2">
        <div class="relay-title">%RELAYNAMES2%</div>
        <div class="relay-status" id="relay-Status2"></div>
        <div class="spacer"></div>
        <button class="primary" data-i18n="status.toggleRelay" onclick="toggleRelay(2)">Toggle</button>
      </div>
      <div class="relay-card" data-relay="3">
        <div class="relay-title">%RELAYNAMES3%</div>
        <div class="relay-status" id="relay-Status3"></div>
        <div class="spacer"></div>
        <button class="primary" data-i18n="status.toggleRelay" onclick="toggleRelay(3)">Toggle</button>
      </div>
      <div class="relay-card" data-relay="4">
        <div class="relay-title">%RELAYNAMES4%</div>
        <div class="relay-status" id="relay-Status4"></div>
        <div class="spacer"></div>
        <button class="primary" data-i18n="status.toggleRelay" onclick="toggleRelay(4)">Toggle</button>
      </div>
      <div class="relay-card" data-relay="5">
        <div class="relay-title">%RELAYNAMES5%</div>
        <div class="relay-status" id="relay-Status5"></div>
        <div class="spacer"></div>
        <button class="primary" data-i18n="status.toggleRelay" onclick="toggleRelay(5)">Toggle</button>
      </div>
    </div>

    <div class="spacer"></div>
    <h2 data-i18n="status.shellyControl">Shelly Steuerung</h2>
    <div class="relay-row" id="relayRow">
      <div class="relay-card" data-relay="shellyMainSw">
        <div class="relay-title" data-i18n="status.shellyMainSw">Hauptschalter</div>
        <div id="shelly-main-switch-state" class="shelly-status shelly-off"></div>
        <div class="info" id="shellyMainInfo">—</div>
        <button class="primary" data-i18n="status.toggleRelay" onclick="toggleShellyRelay('mainSw')">Toggle</button>
      </div>
      <div class="relay-card" data-relay="shellyLight">
        <div class="relay-title" data-i18n="status.shellyLight">Grow Licht</div>
        <div id="shelly-light-switch-state" class="shelly-status shelly-off"></div>
        <div class="info" id="shellyLightInfo">—</div>
        <button class="primary" data-i18n="status.toggleRelay" onclick="toggleShellyRelay('light')">Toggle</button>
      </div>
      <div class="relay-card" data-relay="shellyHeater">
        <div class="relay-title" data-i18n="status.shellyHeater">Heizung</div>
        <div id="shelly-heater-state" class="shelly-status shelly-off"></div>
        <div class="info" id="shellyHeaterInfo">—</div>
        <button class="primary" data-i18n="status.toggleRelay" onclick="toggleShellyRelay('heater')">Toggle</button>
      </div>
      <div class="relay-card" data-relay="shellyHumidifier">
        <div class="relay-title" data-i18n="status.shellyHumidifier">Luftbefeuchter</div>
        <div id="shelly-humidifier-state" class="shelly-status shelly-off"></div>
        <div class="info" id="shellyHumidifierInfo">—</div>
        <button class="primary" data-i18n="status.toggleRelay" onclick="toggleShellyRelay('humidifier')">Toggle</button>
      </div>
      <div class="relay-card" data-relay="shellyFan">
        <div class="relay-title" data-i18n="status.shellyFan">Ventilator</div>
        <div id="shelly-fan-state" class="shelly-status shelly-off"></div>
        <div class="info" id="shellyFanInfo">—</div>
        <button class="primary" data-i18n="status.toggleRelay" onclick="toggleShellyRelay('fan')">Toggle</button>
      </div>
    </div>
    </section>
    
    <!-- diary section -->
    <section id="diary" class="page card">
      <h1 data-i18n="diary.title">Grow Diary</h1>

      <div class="diary-grid">
        <div class="diary-kpi">
          <div class="diary-kpi-title" data-i18n="diary.total">Total grow</div>
          <div class="diary-kpi-val">
            <span id="diaryGrowDay">–</span>
            <span class="unit" data-i18n="diary.day">Day</span>
            &nbsp;•&nbsp;
            <span id="diaryGrowWeek">–</span>
            <span class="unit" data-i18n="diary.week">Week</span>
          </div>
        </div>

        <div class="diary-kpi">
          <div class="diary-kpi-title" data-i18n="diary.phase">Phase</div>
          <div class="diary-kpi-val">
            <span id="diaryPhaseName">–</span>
            &nbsp;•&nbsp;
            <span id="diaryPhaseDay">–</span>
            <span class="unit" data-i18n="diary.day">Day</span>
            &nbsp;•&nbsp;
            <span id="diaryPhaseWeek">–</span>
            <span class="unit" data-i18n="diary.week">Week</span>
          </div>
        </div>
      </div>

      <div class="spacer"></div>

      <div class="form-group">
        <label for="diaryNote" data-i18n="diary.note">Note (max 400 characters)</label>
        <textarea id="diaryNote" maxlength="400" rows="4" placeholder="..." data-i18n-attr="placeholder" data-i18n="diary.note.ph"></textarea>
        <div class="diary-foot">
          <span id="diaryCount">0/400</span>
          <span id="diaryStatus" class="muted"> </span>
        </div>
      </div>

      <div class="btn-row">
        <button type="button" class="btn primary" id="diarySaveBtn" data-i18n="diary.save">Save entry</button>
        <a class="btn danger" href="/api/diary.csv" id="diaryDownloadBtn" data-i18n="diary.download">Download CSV</a>
        <button type="button" class="btn danger" id="diaryClearBtn" data-i18n="diary.clear">Clear diary</button>
      </div>

      <div id="diaryList" class="diary-list"></div>
    </section>
    
    <!-- shellysettings section -->
    <form action="/saveshellysettings" method="POST">
    <section id="shelly" class="page card">
      <h1 data-i18n="shelly.title">Shelly Einstellungen</h1>
      <h2 data-i18n="status.shellyDevices">Shelly Geräte</h2>
      <div class="form-group">
        <label for="shellyIP" data-i18n="shelly.shellyIPMainSw">Shelly IP Adresse für Hauptschalter:</label>
        <div class="twoinone-label">
          <input name="webShellyMainIP" id="shellyMainSwIP" class="control-sm" type="text" inputmode="decimal" value="%SHELLYMAINIP%">
          <select name="webShellyMainGen" id="shellyMainSwGen" class="control-sm control-xs">
            <option value="1" %SHMAINSWKIND1%>Gen1</option>
            <option value="2" %SHMAINSWKIND2%>Gen2</option>
            <option value="3" %SHMAINSWKIND3%>Gen3</option>
          </select>
        </div>
      </div>

      <div class="form-group">
        <label for="shellyIP" data-i18n="shelly.shellyIPLight">Shelly IP Adresse für Pflanzlicht:</label>
        <div class="twoinone-label">
          <input name="webShellyLightIP" id="shellyLightIP" class="control-sm" type="text" inputmode="decimal" value="%SHELLYLIGHTIP%">
          <select name="webShellyLightGen" id="shellyLightGen" class="control-sm control-xs">
            <option value="1" %SHLIGHTKIND1%>Gen1</option>
            <option value="2" %SHLIGHTKIND2%>Gen2</option>
            <option value="3" %SHLIGHTKIND3%>Gen3</option>
          </select>
          <select id="shellyLightOnTime"></select>
          <select id="shellyLightDayHours"></select>
          <input id="shellyLightOffTime" type="text" readonly value="—">
        </div>
      </div>

      <div class="form-group">
        <label for="shellyIP" data-i18n="shelly.shellyIPHeater">Shelly IP Adresse für Heizung:</label>
        <div class="twoinone-label">
          <input name="webShellyHeatIP" id="shellyHeatIP" class="control-sm" type="text" inputmode="decimal" value="%SHELLYHEATERIP%">
          <select name="webShellyHeatGen" id="shellyHeaterGen" class="control-sm control-xs">
            <option value="1" %SHHEATKIND1%>Gen1</option>
            <option value="2" %SHHEATKIND2%>Gen2</option>
            <option value="3" %SHHEATKIND3%>Gen3</option>
          </select>
        </div>
      </div>

      <div class="form-group">
        <label for="shellyIPHumidity" data-i18n="shelly.shellyIPHumidity">Shelly IP Adresse für Luftbefeuchter:</label>
        <div class="twoinone-label">
          <input name="webShellyHumIP" id="shellyHumidifierIP" class="control-sm" type="text" inputmode="decimal" value="%SHELLYHUMIDIFIERIP%">
          <select name="webShellyHumGen" id="shellyHumidifierGen" class="control-sm control-xs">
            <option value="1" %SHHUMIDKIND1%>Gen1</option>
            <option value="2" %SHHUMIDKIND2%>Gen2</option>
            <option value="3" %SHHUMIDKIND3%>Gen3</option>
          </select>
        </div>
      </div>

      <div class="form-group">
        <label for="shIPFan" data-i18n="shelly.shellyIPFan">Shelly IP Adresse für Ventilator:</label>
        <div class="twoinone-label">
          <input name="webShellyFanIP" id="shellyFanIP" class="control-sm" type="text" inputmode="decimal" value="%SHELLYFANIP%">
          <select name="webShellyFanGen" id="shellyFanGen" class="control-sm control-xs">
            <option value="1" %SHFANKIND1%>Gen1</option>
            <option value="2" %SHFANKIND2%>Gen2</option>
            <option value="3" %SHFANKIND3%>Gen3</option>
          </select>
        </div>
      </div>

      <h2 data-i18n="status.shellyAuth">Shelly Authentifizierung</h2>
      <div class="form-group">
        <label for="shellyUsername" data-i18n="shelly.shellyAuthUser">Shelly Benutzername:</label>
        <input name="webShellyUsername" id="shellyUsername" class="control-sm" type="text" value="%SHUSER%">
      </div>

      <div class="form-group">
        <label for="shellyPassword" data-i18n="shelly.shellyAuthPassword">Shelly Passwort:</label>
        <input name="webShellyPassword" id="shellyPassword" class="control-sm" type="password" value="%SHPASSWORD%">
      </div>
      
      <div class="spacer"></div>
        <button class="primary" id="saveshellysettingsBtn" data-i18n="settings.save">Speichern</button>
    </section>
    </form>

    <!-- runsettings section -->
    <form action="/saverunsettings" method="POST">
    <section id="runsettings" class="page card">
      <h1 data-i18n="runsetting.title">Betriebseinstellungen</h1>

      <div class="form-group">
        <div class="tile-right-settings">
          <div class="form-group">
            <label for="webGrowStart" data-i18n="runsetting.startGrow">Start Grow Date:</label>
            <input id="webGrowStart" name="webGrowStart" type="date" style="width: 170px;" value="%GROWSTARTDATE%">
          </div>
          <div class="form-group">
            <label for="webFloweringStart" data-i18n="runsetting.startFlower">Start Flowering Date:</label>
            <input id="webFloweringStart" name="webFloweringStart" type="date" style="width: 170px;" value="%GROWFLOWERDATE%">
          </div>
          <div class="form-group">
            <label for="webDryingStart" data-i18n="runsetting.startDry">Start Drying Date:</label>
            <input id="webDryingStart" name="webDryingStart" type="date" style="width: 170px;" value="%GROWDRAYINGDATE%">
          </div>
        </div>

        <div class="form-group">
        <label for="phaseSelect" data-i18n="runsetting.phase">Phase:</label>
        <select id="phaseSelect" style="width: 170px;" name="webCurrentPhase">
          <option value="1" %PHASE1_SEL% data-i18n="runsetting.phase.grow">Wuchs</option>
          <option value="2" %PHASE2_SEL% data-i18n="runsetting.phase.flower">Blüte</option>
          <option value="3" %PHASE3_SEL% data-i18n="runsetting.phase.dry">Trocknung</option>
        </select>
        </div>

      <div class="form-group">
        <label for="webLightOnTime" data-i18n="runsetting.lightOnTime">Einschaltzeit Pflanzlicht:</label>
        <input type="time" id="webLightOnTime" name="webLightOnTime" style="width: 170px;" value="%LIGHTONTIME%">
      </div>

      <div class="form-group">
        <label for="webLightDayHours" data-i18n="runsetting.lightDayHours">Tagzeit (Stunden):</label>
        <select id="webLightDayHours" name="webLightDayHours" style="width: 80px;" data-selected="%LIGHTDAYHOURS%">
          <option value="1">1</option>
          <option value="2">2</option>
          <option value="3">3</option>
          <option value="4">4</option>
          <option value="5">5</option>
          <option value="6">6</option>
          <option value="7">7</option>
          <option value="8">8</option>
          <option value="9">9</option>
          <option value="10">10</option>
          <option value="11">11</option>
          <option value="12">12</option>
          <option value="13">13</option>
          <option value="14">14</option>
          <option value="15">15</option>
          <option value="16">16</option>
          <option value="17">17</option>
          <option value="18">18</option>
          <option value="19">19</option>
          <option value="20">20</option>
        </select>
        <span class="muted" id="lightRatioSpan" style="margin-left:10px;">—</span>
      </div>


      <div class="form-group">
        <label for="targetTemp" data-i18n="runsetting.targetTemp">Soll-Temperatur:</label>
        <input name="webTargetTemp" id="webTargetTemp" style="width: 65px;" type="number" step="0.5" min="18" max="30" value="%TARGETTEMPERATURE%">&nbsp;°C
      </div>

      <div class="form-group">
        <label for="leafTemp" data-i18n="runsetting.offsetLeafTemperature">Offset Blatttemperatur:</label>
        <input name="webOffsetLeafTemp" id="webOffsetLeafTemp" style="width: 65px;" type="number" step="0.1" min="-3.0" max="0.0" value="%LEAFTEMPERATURE%">&nbsp;°C
      </div>

      <div class="form-group">
        <label for="targetVPD" data-i18n="runsetting.targetVPD">Soll-VPD:</label>
        <input name="webTargetVPD" id="webTargetVPD" style="width: 65px;" type="number" step="0.1" min="0.5" max="1.5" value="%TARGETVPD%">&nbsp;kPa
      </div>

      <h2 data-i18n="runsetting.wateringSettings">Bewässerungseinstellung</h2>

      <div class="form-group">
        <label for="timePerTask" data-i18n="runsetting.timePerTask">Bewässerungszeit pro Task:</label>
        <input name="webTimePerTask" id="webTimePerTask" style="width: 65px;" type="number" step="1" min="1" max="30" value="%TIMEPERTASK%">&nbsp;s&nbsp;(min 1s, max 30s, step 1s)
      </div>

      <div class="form-group">
        <label for="betweenTasks" data-i18n="runsetting.betweenTasks">Pause zwischen Bewässerungen:</label>
        <input name="webBetweenTasks" id="webBetweenTasks" style="width: 65px;" type="number" step="1" min="1" max="10" value="%BETWEENTASKS%">&nbsp;Min&nbsp;(min 1Min, max 10Min, step 1Min)
      </div>

      <div class="form-group">
        <label for="amountOfWater" data-i18n="runsetting.amountOfWater">Wassermenge nach 10 Sekunden:</label>
        <input name="webAmountOfWater" id="webAmountOfWater" style="width: 65px;" type="number" step="5" min="10" max="100" value="%AMOUNTOFWATER%">&nbsp;ml&nbsp;(min 10ml, max 100ml, step 5ml)
      </div>

      <div class="form-group">
        <label for="Irrigation" data-i18n="runsetting.irrigation">Gesamte Bewässerungsmenge:</label>
        <input name="webIrrigation" id="webIrrigation" style="width: 65px;" type="number" step="10" min="100" max="3000" value="%IRRIGATION%">&nbsp;ml&nbsp;(min 100ml, max 3000ml, step 10ml)
      </div>

      <div class="form-group">
        <label for="minTank">min. Tank:</label>
        <input name="webMinTank" id="webMinTank" style="width: 65px;" type="number" value="%MINTANK%">&nbsp;cm
      </div>
      
      <div class="form-group">
        <label for="maxTank">max. Tank:</label>
        <input name="webMaxTank" id="webMaxTank" style="width: 65px;" type="number" value="%MAXTANK%">&nbsp;cm
      </div>

      <div class="spacer"></div>
      <button class="primary" id="saverunsettingsBtn" data-i18n="settings.save">Speichern</button>
      </form>

        <!-- ESP32 Relay Scheduling -->
        <div class="relay-sched">
          <h2 class="relay-sched-title" data-i18n="runsetting.relayScheduling">ESP32 Relay Scheduling</h2>
          <p class="relay-sched-hint" data-i18n="runsetting.relay.minutesHint">
            Minutenformat: <b>0–59</b> (Minute innerhalb der Stunde).
          </p>

          <div class="relay-sched-list">

            <!-- ESP Relay 1 -->
            <div class="relay-sched-row">
              <div class="relay-sched-name">
                <div class="relay-sched-name-label" data-i18n="runsettings.espSchedRelay">Relay</div>
                <div class="relay-sched-name-value">%RELAYNAMES1%</div>
              </div>

              <div class="sched-field chk">
                <label class="inline-checkbox">
                  <input id="espRelay1Enabled" name="espRelay1Enabled" type="checkbox" %ESPRELAY1_ENABLED_CHECKED%>
                  <span data-i18n="runsetting.relay.enabledShort">Enabled</span>
                </label>
              </div>

              <div class="sched-field chk">
                <label class="inline-checkbox">
                  <input id="espRelay1IfLightOn" name="espRelay1IfLightOn" type="checkbox" %ESPRELAY1_IFLIGHTON_CHECKED%>
                  <span data-i18n="runsetting.relay.ifLightOn">wenn Licht an</span>
                </label>
              </div>

              <div class="sched-field minute">
                <label for="espRelay1OnMin" data-i18n="runsetting.relay.onMinute">Einschaltminute</label>
                <input id="espRelay1OnMin" name="espRelay1OnMin" type="number" min="0" max="59" step="1" value="%ESPRELAY1_ONMIN%">
              </div>

              <div class="sched-field minute">
                <label for="espRelay1OffMin" data-i18n="runsetting.relay.offMinute">Ausschaltminute</label>
                <input id="espRelay1OffMin" name="espRelay1OffMin" type="number" min="0" max="59" step="1" value="%ESPRELAY1_OFFMIN%">
              </div>
            </div>

            <!-- ESP Relay 2 -->
            <div class="relay-sched-row">
              <div class="relay-sched-name">
                <div class="relay-sched-name-label" data-i18n="runsettings.espSchedRelay">Relay</div>
                <div class="relay-sched-name-value">%RELAYNAMES2%</div>
              </div>

              <div class="sched-field chk">
                <label class="inline-checkbox">
                  <input id="espRelay2Enabled" name="espRelay2Enabled" type="checkbox" %ESPRELAY2_ENABLED_CHECKED%>
                  <span data-i18n="runsetting.relay.enabledShort">Enabled</span>
                </label>
              </div>

              <div class="sched-field chk">
                <label class="inline-checkbox">
                  <input id="espRelay2IfLightOn" name="espRelay2IfLightOn" type="checkbox" %ESPRELAY2_IFLIGHTON_CHECKED%>
                  <span data-i18n="runsetting.relay.ifLightOn">wenn Licht an</span>
                </label>
              </div>

              <div class="sched-field minute">
                <label for="espRelay2OnMin" data-i18n="runsetting.relay.onMinute">Einschaltminute</label>
                <input id="espRelay2OnMin" name="espRelay2OnMin" type="number" min="0" max="59" step="1" value="%ESPRELAY2_ONMIN%">
              </div>

              <div class="sched-field minute">
                <label for="espRelay2OffMin" data-i18n="runsetting.relay.offMinute">Ausschaltminute</label>
                <input id="espRelay2OffMin" name="espRelay2OffMin" type="number" min="0" max="59" step="1" value="%ESPRELAY2_OFFMIN%">
              </div>
            </div>

            <!-- ESP Relay 3 -->
            <div class="relay-sched-row">
              <div class="relay-sched-name">
                <div class="relay-sched-name-label" data-i18n="runsettings.espSchedRelay">Relay</div>
                <div class="relay-sched-name-value">%RELAYNAMES3%</div>
              </div>

              <div class="sched-field chk">
                <label class="inline-checkbox">
                  <input id="espRelay3Enabled" name="espRelay3Enabled" type="checkbox" %ESPRELAY3_ENABLED_CHECKED%>
                  <span data-i18n="runsetting.relay.enabledShort">Enabled</span>
                </label>
              </div>

              <div class="sched-field chk">
                <label class="inline-checkbox">
                  <input id="espRelay3IfLightOn" name="espRelay3IfLightOn" type="checkbox" %ESPRELAY3_IFLIGHTON_CHECKED%>
                  <span data-i18n="runsetting.relay.ifLightOn">wenn Licht an</span>
                </label>
              </div>

              <div class="sched-field minute">
                <label for="espRelay3OnMin" data-i18n="runsetting.relay.onMinute">Einschaltminute</label>
                <input id="espRelay3OnMin" name="espRelay3OnMin" type="number" min="0" max="59" step="1" value="%ESPRELAY3_ONMIN%">
              </div>

              <div class="sched-field minute">
                <label for="espRelay3OffMin" data-i18n="runsetting.relay.offMinute">Ausschaltminute</label>
                <input id="espRelay3OffMin" name="espRelay3OffMin" type="number" min="0" max="59" step="1" value="%ESPRELAY3_OFFMIN%">
              </div>
            </div>

            <!-- ESP Relay 4 -->
            <div class="relay-sched-row">
              <div class="relay-sched-name">
                <div class="relay-sched-name-label" data-i18n="runsettings.espSchedRelay">Relay</div>
                <div class="relay-sched-name-value">%RELAYNAMES4%</div>
              </div>

              <div class="sched-field chk">
                <label class="inline-checkbox">
                  <input id="espRelay4Enabled" name="espRelay4Enabled" type="checkbox" %ESPRELAY4_ENABLED_CHECKED%>
                  <span data-i18n="runsetting.relay.enabledShort">Enabled</span>
                </label>
              </div>

              <div class="sched-field chk">
                <label class="inline-checkbox">
                  <input id="espRelay4IfLightOn" name="espRelay4IfLightOn" type="checkbox" %ESPRELAY4_IFLIGHTON_CHECKED%>
                  <span data-i18n="runsetting.relay.ifLightOn">wenn Licht an</span>
                </label>
              </div>

              <div class="sched-field minute">
                <label for="espRelay4OnMin" data-i18n="runsetting.relay.onMinute">Einschaltminute</label>
                <input id="espRelay4OnMin" name="espRelay4OnMin" type="number" min="0" max="59" step="1" value="%ESPRELAY4_ONMIN%">
              </div>

              <div class="sched-field minute">
                <label for="espRelay4OffMin" data-i18n="runsetting.relay.offMinute">Ausschaltminute</label>
                <input id="espRelay4OffMin" name="espRelay4OffMin" type="number" min="0" max="59" step="1" value="%ESPRELAY4_OFFMIN%">
              </div>
            </div>

            <!-- ESP Relay 5 -->
            <div class="relay-sched-row">
              <div class="relay-sched-name">
                <div class="relay-sched-name-label" data-i18n="runsettings.espSchedRelay">Relay</div>
                <div class="relay-sched-name-value">%RELAYNAMES5%</div>
              </div>

              <div class="sched-field chk">
                <label class="inline-checkbox">
                  <input id="espRelay5Enabled" name="espRelay5Enabled" type="checkbox" %ESPRELAY5_ENABLED_CHECKED%>
                  <span data-i18n="runsetting.relay.enabledShort">Enabled</span>
                </label>
              </div>

              <div class="sched-field chk">
                <label class="inline-checkbox">
                  <input id="espRelay5IfLightOn" name="espRelay5IfLightOn" type="checkbox" %ESPRELAY5_IFLIGHTON_CHECKED%>
                  <span data-i18n="runsetting.relay.ifLightOn">wenn Licht an</span>
                </label>
              </div>

              <div class="sched-field minute">
                <label for="espRelay5OnMin" data-i18n="runsetting.relay.onMinute">Einschaltminute</label>
                <input id="espRelay5OnMin" name="espRelay5OnMin" type="number" min="0" max="59" step="1" value="%ESPRELAY5_ONMIN%">
              </div>

              <div class="sched-field minute">
                <label for="espRelay5OffMin" data-i18n="runsetting.relay.offMinute">Ausschaltminute</label>
                <input id="espRelay5OffMin" name="espRelay5OffMin" type="number" min="0" max="59" step="1" value="%ESPRELAY5_OFFMIN%">
              </div>
            </div>

          </div>
        </div>

        <div class="spacer"></div>
        <button class="primary" id="saverunsettingsBtn" data-i18n="settings.save">Speichern</button>
    </section>

    <!-- setting section -->
    <form action="/savesettings" method="POST">
      <section id="settings" class="page card">
        <h1 data-i18n="settings.title">Systemeinstellungen</h1>

        <div class="form-group">
          <label class="inline-checkbox">
            <input type="checkbox" name="webDebug" %DBG_CHECKED%>
            <span data-i18n="settings.debugEnabled">Debug aktivieren</span>
          </label>
        </div>

        <div class="form-group">
          <label for="webBoxName" data-i18n="settings.boxName">Boxname:</label>
          <input name="webBoxName" id="webBoxName" type="text" data-i18n="settings.boxName.ph" data-i18n-attr="placeholder" style="width: 320px;" value="%CONTROLLERNAME%">
        </div>

        <div class="form-group">
          <label for="webNTPServer" data-i18n="settings.ntpserver">NTP-Server:</label>
          <input name="webNTPServer" id="webNTPServer" type="text" data-i18n="settings.ntpserver.ph" data-i18n-attr="placeholder" style="width: 250px;" value="%NTPSERVER%">
        </div>

        <div class="form-group">
          <div class="label-inline">
            <label for="webTimeZoneInfo" data-i18n="settings.timeZoneInfo">Zeitzone:</label>
            &nbsp;<a href="https://github.com/nayarsystems/posix_tz_db/blob/master/zones.json" target="_blank" rel="noopener noreferrer">🌐</a>
          </div>
          <input name="webTimeZoneInfo" id="webTimeZoneInfo" type="text" data-i18n="settings.timeZoneInfo.ph" data-i18n-attr="placeholder" style="width: 350px;" value="%TZINFO%">
        </div>

        <div class="form-group">
          <label for="language" data-i18n="settings.language">Sprache:</label>
          <select name="webLanguage" id="language" style="width: 100px;">
            <!-- Optionen vermutlich per JS/i18n gefüllt -->
          </select>
        </div>

        <div class="form-group">
          <label for="theme" data-i18n="settings.theme">Theme:</label>
          <select name="webTheme" id="theme" style="width: 100px;">
            <option value="light" data-i18n="settings.themeLight">Hell</option>
            <option value="dark"  data-i18n="settings.themeDark">Dunkel</option>
          </select>
        </div>

        <div class="form-group">
          <label for="dateFormat" data-i18n="settings.dateFormat">Datumsformat:</label>
          <select name="webDateFormat" id="dateFormat" style="width: 140px;">
            <option value="YYYY-MM-DD" data-i18n="settings.df_ymd">YYYY-MM-DD</option>
            <option value="DD.MM.YYYY" data-i18n="settings.df_dmy">DD.MM.YYYY</option>
          </select>
        </div>

        <div class="form-group">
          <label for="timeFormat" data-i18n="settings.timeFormat">Zeitformat:</label>
          <select name="webTimeFormat" id="timeFormat" style="width: 100px;">
            <option value="24" data-i18n="settings.tf_HHmm">24h</option>
            <option value="12" data-i18n="settings.tf_hhmma">12h AM/PM</option>
          </select>
        </div>

        <div class="form-group">
          <label for="tempUnit" data-i18n="settings.tempUnit">Temperatur-Einheit:</label>
          <select name="webTempUnit" id="tempUnit" style="width: 140px;">
            <option value="C" data-i18n="settings.celsius">°C (Celsius)</option>
            <option value="F" data-i18n="settings.fahrenheit">°F (Fahrenheit)</option>
          </select>
        </div>

        <h2 data-i18n="settings.DS18B20">DS18B20 Sensor</h2>        
        <div class="form-group checkbox">
          <label class="inline-checkbox">
           <input type="checkbox" name="webDS18B20Enable" id="webDS18B20Enable" %DS18B20ENABLE%>
           <span data-i18n="settings.enabled">aktivieren</span>
          </label>
        </div>

        <div class="form-group">
          <input name="webDS18B20Name" id="webDS18B20Name" type="text" data-i18n="settings.DS18B20Name.ph" data-i18n-attr="placeholder" style="width: 250px;" maxlength="400" value="%DS18B20NAME%">
        </div>

        <h2 data-i18n="settings.relaySettings">Relais Einstellungen</h2>
        <div class="form-group">
          <label for="webRelay1" data-i18n="settings.relay1">Relay 1:</label>
          <input name="webRelayName1" id="webRelayName1" type="text" data-i18n="settings.relay1.ph" data-i18n-attr="placeholder" style="width: 120px;" maxlength="400" value="%RELAYNAMES1%">
        </div>

        <div class="form-group">
          <label for="webRelay2" data-i18n="settings.relay2">Relay 2:</label>
          <input name="webRelayName2" id="webRelayName2" type="text" data-i18n="settings.relay2.ph" data-i18n-attr="placeholder" style="width: 120px;" maxlength="400" value="%RELAYNAMES2%">
        </div>

        <div class="form-group">
          <label for="webRelay3" data-i18n="settings.relay3">Relay 3:</label>
          <input name="webRelayName3" id="webRelayName3" type="text" data-i18n="settings.relay3.ph" data-i18n-attr="placeholder" style="width: 120px;" maxlength="400" value="%RELAYNAMES3%">
        </div>

        <div class="form-group">
          <label for="webRelay4" data-i18n="settings.relay4">Relay 4:</label>
          <input name="webRelayName4" id="webRelayName4" type="text" data-i18n="settings.relay4.ph" data-i18n-attr="placeholder" style="width: 120px;" maxlength="400" value="%RELAYNAMES4%">
        </div>

        <div class="form-group">
          <label for="webRelay5" data-i18n="settings.relay5">Relay 5:</label>
          <input name="webRelayName5" id="webRelayName5" type="text" data-i18n="settings.relay5.ph" data-i18n-attr="placeholder" style="width: 120px;" maxlength="400" value="%RELAYNAMES5%">
        </div>

        <button class="primary" id="saveSettingsBtn" data-i18n="settings.save">Speichern</button>
      </section>
    </form>

    <!-- runsettings section -->
    <form action="/savemessagesettings" method="POST">
    <section id="message" class="page card">
      <h1 data-i18n="message.title">Nachrichteneinstellungen</h1>

      <h2 data-i18n="message.pushoverSettings">Pushover Einstellungen</h2>

      <div class="form-group checkbox">
        <label class="inline-checkbox">
         <input type="checkbox" name="webPushoverEnabled" id="webPushoverEnabled" %PUSHOVERENABLED%>
         <span data-i18n="message.enabled">aktivieren</span>
        </label>
      </div>

      <div class="form-group">
        <label for="webPushoverUserKey" data-i18n="message.pushoverUserKey">Pushover Benutzer:</label>
        <input name="webPushoverUserKey" id="webPushoverUserKey" type="text" data-i18n="message.pushoverUserKey.ph" data-i18n-attr="placeholder" style="width: 320px;" value="%PUSHOVERUSERKEY%">
      </div>

      <div class="form-group">
        <label for="webPushoverAppKey" data-i18n="message.pushoverAppKey">Pushover Token:</label>
        <input name="webPushoverAppKey" id="webPushoverAppKey" type="text" data-i18n="message.pushoverAppKey.ph" data-i18n-attr="placeholder" style="width: 320px;" value="%PUSHOVERAPPKEY%">
      </div>

      <div class="form-group">
        <label for="webPushoverDevice" data-i18n="message.pushoverDevice">Pushover Gerät:</label>
        <input name="webPushoverDevice" id="webPushoverDevice" type="text" data-i18n="message.pushoverDevice.ph" data-i18n-attr="placeholder" style="width: 320px;" value="%PUSHOVERDEVICE%">
      </div>

      <h2 data-i18n="message.gotifySettings">Gotify Einstellungen</h2>

      <div class="form-group checkbox">
        <label class="inline-checkbox">
         <input type="checkbox" name="webGotifyEnabled" id="webGotifyEnabled" %GOTIFYENABLED%>
         <span data-i18n="message.enabled">aktivieren</span>
        </label>
      </div>

      <div class="form-group">
        <label for="webGotifyURL" data-i18n="message.gotifyURL">Gotify URL:</label>
        <input name="webGotifyURL" id="webGotifyURL" type="text" data-i18n="message.gotifyUrl.ph" data-i18n-attr="placeholder" style="width: 320px;" value="%GOTIFYURL%">
      </div>

      <div class="form-group">
        <label for="webGotifyToken" data-i18n="message.gotifyToken">Gotify Token:</label>
        <input name="webGotifyToken" id="webGotifyToken" type="text" data-i18n="message.gotifyToken.ph" data-i18n-attr="placeholder" style="width: 320px;" value="%GOTIFYTOKEN%">
      </div>

      <button class="primary" id="saveMessageBtn" data-i18n="settings.save">Speichern</button>
    </section>
    </form>
    

    <!-- system log section -->
    <section id="logging" class="page card">
      <h1 data-i18n="logging.title">Systemprotokoll</h1>
      <div class="weblog-card">
        <div class="weblog-head">
          <strong>System-Log</strong>
          <div class="weblog-actions">
            <a class="btn" href="/download/log">CSV/TXT Download</a>
            <button class="btn" id="toggleScrollBtn" type="button">AutoScroll: ON</button>
            <button class="btn" id="clearLogBtn" type="button" title="Log löschen">Clear</button>
          </div>
        </div>
        <pre id="weblog" class="weblog" aria-live="polite" aria-label="Laufende Logausgabe">…</pre>
      </div>
    </section>

    <!-- variables/state section -->
    <section id="vars" class="page card">
      <h1 data-i18n="vars.title" data-i18n="vars.variables">Variablen</h1>
      <p class="hint" data-i18n="vars.hint" data-i18n="vars.debugHint">Debug-Ansicht: alle registrierten Werte (automatisch aus /api/state). Tokens/Passwörter werden maskiert.</p>

      <div class="vars-toolbar">
        <input id="varsSearch" class="input" type="search" placeholder="Search…" aria-label="Search variables">
        <button class="btn" id="varsRefreshBtn" type="button">Refresh</button>
      </div>

      <div id="varsMeta" class="vars-meta">--</div>

      <div class="table-wrap">
        <table class="vars-table" id="varsTable" aria-label="Variables table">
          <thead>
            <tr><th>Key</th><th>Value</th></tr>
          </thead>
          <tbody id="varsTbody">
            <tr><td colspan="2">—</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- factory reset section -->
    <section id="factory" class="page card">
      <form action="/factory-reset" method="post" id="factoryResetForm">
        <h1 data-i18n="factory.title">Werkseinstellungen</h1>
        <input type="hidden" name="confirm" value="1">
        <button class="primary" id="factoryResetBtn" type="submit" data-i18n="factory.reset">factory reset</button>
      </form>
    </section>
  </main>
  </div>
  
 <script src="/script.js"></script>
</body>
</html>
)rawliteral";

const char* apPage = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <title>%CONTENTCONTROLLERNAME%</title>
  <meta charset="UTF-8">
  <link rel="stylesheet" href="/style.css">
</head>
<body>
  <header class="header">
    <button class="hamburger" id="hamburgerBtn" data-i18n="a11y.menu" data-i18n-attr="aria-label" aria-label="Menü öffnen/schließen" aria-expanded="false" aria-controls="sidebar">☰</button>
    <div class="title" data-i18n="app.title">%CONTENTCONTROLLERNAME%</div>
    </div>
  </header>
  <div class="layout">
    <nav class="sidebar" id="sidebar">
      <a class="navlink" data-page="settings"   data-i18n="nav.wifisettings">WIFI Setting</a>
    </nav>

  <div class="overlay" id="overlay"></div>

    <main class="content" id="content">
      <section id="status" class="page active card">
        <form action="/save" method="post">
          <h1 data-i18n="settings.title">WIFI Setting</h1>
          <label for="ssid">WIFI SSID:</label>
          <input type="text" id="ssid" name="ssid" required><br><br>
          <label for="password">WIFI Passwort:</label>
          <input type="password" id="password" name="password" required><br><br>
          <button class="primary" id="saveBtn" data-i18n="settings.save">save & reboot</button>
        </form>
      </section>
      <section id="status" class="page active card">
        <form action="/factory-reset" method="post" id="factoryResetForm">
          <h1 data-i18n="settings.title">Factory Reset</h1>
          <input type="hidden" name="confirm" value="1">
          <button class="primary" id="factoryResetBtn" type="submit" data-i18n="settings.factoryreset.button">factory reset</button>
        </form>
      </section>
    </main>
  </div>
  
 <script src="/script.js"></script>
</body>
</html>
)rawliteral";