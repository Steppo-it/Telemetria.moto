# Navigazione turn-by-turn + restyling mappa — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trasformare il navigatore da "disegna solo il percorso" a un'esperienza utilizzabile in marcia (autocomplete, tappe, voce, prossima manovra, distanza/ETA) e restylare la mappa (temi chiaro/scuro coerenti col resto dell'app, percorso con glow, mappa a filo schermo).

**Architecture:** Tutto in `index.html` (nessun build system). Ogni pezzo (autocomplete/tappe, voce, avanzamento tappe/pannello, stile visivo) tocca in modo incrementale le stesse due funzioni esistenti (`navGoBtn` click handler, `navClearBtn` click handler) più `handlePosition()`/`ensureMap()` — i task sono ordinati in modo che ogni commit lasci l'app funzionante.

**Tech Stack:** HTML/CSS/JS vanilla. Google Maps JavaScript API (già in uso) + libreria `places` (nuova, stessa chiave). Web Speech API (`speechSynthesis`, nativa del browser, nessuna dipendenza).

## Global Constraints

- Nessun build system, bundler o package manager: tutto resta in `index.html`.
- Nessuna nuova dipendenza esterna oltre alla libreria `places` di Google Maps (stessa chiave/script già caricato) e alla Web Speech API nativa del browser.
- La Places API va abilitata dall'utente in Google Cloud Console (fuori dal controllo del codice) — se non abilitata, l'autocomplete degrada silenziosamente a input di testo libero (nessun errore bloccante).
- Formato export CSV invariato.
- La mappa resta orientata a nord fisso (nessuna rotazione) — vincolo di attribuzione Google già documentato in CLAUDE.md, non toccato da questo piano.
- Bussola, luoghi predefiniti/preferiti, rerouting automatico: esplicitamente fuori scope.

---

## Riferimento: file di partenza

Tutti i riferimenti sotto si intendono sullo stato di `moto-telemetry/index.html` all'inizio del Task 1 (commit `8fa6f54`). Da Task 2 in poi alcune righe si saranno spostate: se un riferimento a riga non corrisponde più, individua il blocco cercando la stringa indicata invece del numero.

Verifica prima di ogni task: `python3 -m http.server 8000` dentro `moto-telemetry/`, apri `http://localhost:8000/`, DevTools console aperta. Come nel piano precedente, per la logica non visiva si può simulare via console (`window.dispatchEvent(new ...)`), mentre per Autocomplete/Places/DirectionsService reali serve un browser con la chiave configurata — se non disponibile, verifica leggendo attentamente il codice (nessun placeholder, nessun riferimento a variabile non definita) e documentalo nel report.

---

### Task 1: Autocomplete indirizzi + tappe multiple

**Files:**
- Modify: `index.html:793` (script tag Google Maps, aggiunge `libraries=places`)
- Modify: `index.html:296-305` (HTML popover navigatore: aggiunge lista tappe + pulsante)
- Modify: `index.html` CSS (aggiunge `.waypoint-row`, `#addWaypointBtn`)
- Modify: `index.html` blocco riferimenti DOM (cerca `const mapNavBtn = $('mapNavBtn')`)
- Modify: `index.html` `navGoBtn.addEventListener` (cerca `navGoBtn.addEventListener('click'`)

**Interfaces:**
- Consumes: nessuna dipendenza da altri task di questo piano (primo task).
- Produces: array `waypointInputs` (elementi `<input>` delle tappe, in ordine), funzione `createWaypointInput()`, funzione `attachAutocomplete(inputEl)`, funzione `tryAttachDestAutocomplete()`. Task 2/3/4 aggiungeranno righe dentro il callback di successo di `navGoBtn` e dentro `navClearBtn.addEventListener` — entrambi restano gli stessi punti di aggancio.

- [ ] **Step 1: Aggiungi la libreria `places` allo script Google Maps**

Trova:
```html
<script src="https://maps.googleapis.com/maps/api/js?key=AIzaSyBSQER-qCTUsdaoAp0LYanT7Su0sX9OnDk&v=weekly" defer></script>
```

Sostituisci con:
```html
<script src="https://maps.googleapis.com/maps/api/js?key=AIzaSyBSQER-qCTUsdaoAp0LYanT7Su0sX9OnDk&v=weekly&libraries=places" defer></script>
```

- [ ] **Step 2: Aggiungi CSS per le righe tappa**

Trova:
```css
  .settings-input { width:100%; background:var(--hair); border:1px solid var(--panel-edge); border-radius:8px; padding:11px; color:var(--text); font-family:var(--mono); font-size:13px; margin-bottom:10px; }
```

Sostituisci con:
```css
  .settings-input { width:100%; background:var(--hair); border:1px solid var(--panel-edge); border-radius:8px; padding:11px; color:var(--text); font-family:var(--mono); font-size:13px; margin-bottom:10px; }
  .waypoint-row { display:flex; gap:6px; margin-bottom:8px; }
  .waypoint-row .settings-input { margin-bottom:0; }
  .waypoint-remove { flex:0 0 auto; width:34px; border:1px solid var(--panel-edge); background:transparent; color:var(--ink-dim); border-radius:8px; font-size:16px; line-height:1; cursor:pointer; }
  #addWaypointBtn { width:100%; margin-bottom:10px; }
  /* Google Places inietta #pac-container in <body>, fuori dal nostro markup — tema forzato con
     !important perché il foglio di stile di Google usa selettori altrettanto specifici. */
  .pac-container {
    background: var(--bg2) !important; border:1px solid var(--panel-edge) !important;
    border-radius:8px !important; font-family: var(--mono) !important; margin-top:4px !important;
    box-shadow: 0 4px 20px rgba(0,0,0,.4) !important;
  }
  .pac-item { color: var(--ink) !important; border-top-color: var(--hair) !important; padding:8px 10px !important; font-size:12px !important; }
  .pac-item:hover, .pac-item-selected { background: var(--hair) !important; }
  .pac-item-query { color: var(--ink) !important; }
  .pac-matched { color: var(--blue-glow) !important; }
  .pac-icon { display:none !important; }
```

- [ ] **Step 3: Aggiungi lista tappe + pulsante nel popover navigatore**

Trova:
```html
  <div class="popover-panel" id="navPanel">
    <div class="popover-title">NAVIGATORE</div>
    <input type="text" id="destInput" class="settings-input" placeholder="Indirizzo o luogo di destinazione..." />
    <div class="mini-actions-row">
      <button class="btn-mini" id="navGoBtn">Vai</button>
      <button class="btn-mini" id="navClearBtn">Annulla percorso</button>
      <button class="btn-mini" id="navCloseBtn">Chiudi</button>
    </div>
    <div class="log-info" id="navInfo"></div>
  </div>
```

Sostituisci con:
```html
  <div class="popover-panel" id="navPanel">
    <div class="popover-title">NAVIGATORE</div>
    <div id="waypointList"></div>
    <button class="btn-mini" id="addWaypointBtn" type="button">+ Aggiungi tappa</button>
    <input type="text" id="destInput" class="settings-input" placeholder="Indirizzo o luogo di destinazione..." />
    <div class="mini-actions-row">
      <button class="btn-mini" id="navGoBtn">Vai</button>
      <button class="btn-mini" id="navClearBtn">Annulla percorso</button>
      <button class="btn-mini" id="navCloseBtn">Chiudi</button>
    </div>
    <div class="log-info" id="navInfo"></div>
  </div>
```

- [ ] **Step 4: Aggiungi i riferimenti DOM**

Trova:
```js
  const mapNavBtn = $('mapNavBtn'), navPanel = $('navPanel'), navBackdrop = $('navBackdrop'), destInput = $('destInput'), navGoBtn = $('navGoBtn'), navClearBtn = $('navClearBtn'), navCloseBtn = $('navCloseBtn'), navInfo = $('navInfo');
```

Sostituisci con:
```js
  const mapNavBtn = $('mapNavBtn'), navPanel = $('navPanel'), navBackdrop = $('navBackdrop'), destInput = $('destInput'), navGoBtn = $('navGoBtn'), navClearBtn = $('navClearBtn'), navCloseBtn = $('navCloseBtn'), navInfo = $('navInfo');
  const waypointList = $('waypointList'), addWaypointBtn = $('addWaypointBtn');
```

- [ ] **Step 5: Aggiungi le funzioni di autocomplete e gestione tappe, prima della sezione popover navigatore**

Trova:
```js
  /* ---------- navigator popover ---------- */
  function openNav(){ navPanel.classList.add('open'); navBackdrop.classList.add('open'); }
```

Sostituisci con:
```js
  /* ---------- navigator popover ---------- */
  let waypointInputs = [];
  let destAutocompleteReady = false;

  function attachAutocomplete(inputEl){
    if (window.google && google.maps && google.maps.places) {
      new google.maps.places.Autocomplete(inputEl, { fields: ['formatted_address', 'geometry'] });
    }
  }
  function tryAttachDestAutocomplete(){
    if (destAutocompleteReady) return;
    attachAutocomplete(destInput);
    if (window.google && google.maps && google.maps.places) destAutocompleteReady = true;
  }
  function createWaypointInput(){
    const row = document.createElement('div');
    row.className = 'waypoint-row';
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'settings-input';
    input.placeholder = 'Tappa intermedia...';
    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'waypoint-remove';
    removeBtn.textContent = '×';
    removeBtn.addEventListener('click', () => {
      waypointList.removeChild(row);
      waypointInputs = waypointInputs.filter(w => w !== input);
    });
    row.appendChild(input);
    row.appendChild(removeBtn);
    waypointList.appendChild(row);
    waypointInputs.push(input);
    attachAutocomplete(input);
  }
  addWaypointBtn.addEventListener('click', createWaypointInput);

  function openNav(){ navPanel.classList.add('open'); navBackdrop.classList.add('open'); tryAttachDestAutocomplete(); }
```

- [ ] **Step 6: Aggiorna `navGoBtn` per includere le tappe nella richiesta di percorso**

Trova:
```js
  navGoBtn.addEventListener('click', () => {
    const dest = destInput.value.trim();
    if (!dest) return;
    if (lastLat === null) { navInfo.textContent = 'Aspetta il segnale GPS.'; return; }
    if (!window.google || !directionsService) { navInfo.textContent = 'Google Maps non caricato — controlla la API key.'; return; }
    navInfo.textContent = 'Calcolo percorso…';
    directionsService.route({
      origin: { lat: lastLat, lng: lastLon },
      destination: dest,
      travelMode: google.maps.TravelMode.DRIVING
    }, (result, status) => {
      if (status === 'OK') {
        directionsRenderer.setDirections(result);
        mapNavBtn.classList.add('active');
        navInfo.textContent = 'Percorso impostato ✓';
        setTimeout(closeNav, 700);
      } else {
        navInfo.textContent = 'Destinazione non trovata (' + status + ')';
      }
    });
  });
```

Sostituisci con:
```js
  navGoBtn.addEventListener('click', () => {
    const dest = destInput.value.trim();
    if (!dest) return;
    if (lastLat === null) { navInfo.textContent = 'Aspetta il segnale GPS.'; return; }
    if (!window.google || !directionsService) { navInfo.textContent = 'Google Maps non caricato — controlla la API key.'; return; }
    const waypoints = waypointInputs
      .map(w => w.value.trim())
      .filter(v => v.length > 0)
      .map(v => ({ location: v, stopover: true }));
    navInfo.textContent = 'Calcolo percorso…';
    directionsService.route({
      origin: { lat: lastLat, lng: lastLon },
      destination: dest,
      waypoints,
      travelMode: google.maps.TravelMode.DRIVING
    }, (result, status) => {
      if (status === 'OK') {
        directionsRenderer.setDirections(result);
        mapNavBtn.classList.add('active');
        navInfo.textContent = 'Percorso impostato ✓';
        setTimeout(closeNav, 700);
      } else {
        navInfo.textContent = 'Destinazione non trovata (' + status + ')';
      }
    });
  });
```

- [ ] **Step 7: Verifica manuale**

Se hai un browser con la chiave Google configurata: apri il popover 🧭, digita un indirizzo nel campo destinazione — dopo l'apertura del popover dovrebbero comparire suggerimenti live (se la Places API è già abilitata sul tuo progetto; altrimenti l'input resta un campo di testo libero, comportamento atteso). Clicca "+ Aggiungi tappa": deve comparire un nuovo campo con la sua "×" per rimuoverlo. Rimuovilo e verifica che sparisca e non compaia più in `waypointInputs` (controlla in console `waypointInputs.length`).

Se non hai un browser disponibile: rileggi il diff e verifica che non ci siano riferimenti a variabili non definite (`waypointList`, `addWaypointBtn`, `waypointInputs` tutti dichiarati prima dell'uso) e che `node --check` (o l'estrazione JS con `new Function(...)`, come nei task precedenti) non dia errori di sintassi.

- [ ] **Step 8: Commit**

```bash
git add index.html
git commit -m "Aggiunge autocomplete indirizzi e tappe multiple al navigatore"
```

---

### Task 2: Istruzioni vocali (infrastruttura + conferma)

**Files:**
- Modify: `index.html` HTML popover navigatore (aggiunge riga toggle voce)
- Modify: `index.html` blocco riferimenti DOM
- Modify: `index.html` funzioni popover navigatore (aggiunge `speak()`, toggle)
- Modify: `index.html` `navGoBtn.addEventListener` (aggiunge chiamata `speak(...)`)
- Modify: `index.html` `navClearBtn.addEventListener` (aggiunge `speechSynthesis.cancel()`)

**Interfaces:**
- Consumes: `navGoBtn`/`navClearBtn` handler come lasciati dal Task 1.
- Produces: funzione `speak(text)` (chiamabile da qualsiasi punto successivo — Task 3 la userà per gli annunci di manovra), variabile `voiceEnabled`, chiave `localStorage` `moto_voice`.

- [ ] **Step 1: Aggiungi la riga toggle voce nel popover**

Trova:
```html
    <input type="text" id="destInput" class="settings-input" placeholder="Indirizzo o luogo di destinazione..." />
    <div class="mini-actions-row">
      <button class="btn-mini" id="navGoBtn">Vai</button>
```

Sostituisci con:
```html
    <input type="text" id="destInput" class="settings-input" placeholder="Indirizzo o luogo di destinazione..." />
    <div class="settings-row"><span>Voce</span><button class="settings-toggle" id="voiceToggle">Attiva</button></div>
    <div class="mini-actions-row">
      <button class="btn-mini" id="navGoBtn">Vai</button>
```

- [ ] **Step 2: Aggiungi il riferimento DOM**

Trova:
```js
  const waypointList = $('waypointList'), addWaypointBtn = $('addWaypointBtn');
```

Sostituisci con:
```js
  const waypointList = $('waypointList'), addWaypointBtn = $('addWaypointBtn');
  const voiceToggle = $('voiceToggle');
```

- [ ] **Step 3: Aggiungi `speak()` e il toggle, prima della sezione popover navigatore**

Trova:
```js
  /* ---------- navigator popover ---------- */
  let waypointInputs = [];
```

Sostituisci con:
```js
  /* ---------- voce (Web Speech API) ---------- */
  const VOICE_KEY = 'moto_voice';
  let voiceEnabled = (function(){ try { return localStorage.getItem(VOICE_KEY) !== 'off'; } catch(e){ return true; } })();
  function refreshVoiceToggleLabel(){ voiceToggle.textContent = voiceEnabled ? 'Attiva' : 'Disattivata'; }
  voiceToggle.addEventListener('click', () => {
    voiceEnabled = !voiceEnabled;
    try { localStorage.setItem(VOICE_KEY, voiceEnabled ? 'on' : 'off'); } catch(e){}
    refreshVoiceToggleLabel();
  });
  refreshVoiceToggleLabel();

  function speak(text){
    if (!voiceEnabled) return;
    if (!('speechSynthesis' in window)) return;
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = 'it-IT';
    speechSynthesis.speak(utter);
  }

  /* ---------- navigator popover ---------- */
  let waypointInputs = [];
```

- [ ] **Step 4: Aggiungi l'annuncio di conferma in `navGoBtn`**

Trova:
```js
      if (status === 'OK') {
        directionsRenderer.setDirections(result);
        mapNavBtn.classList.add('active');
        navInfo.textContent = 'Percorso impostato ✓';
        setTimeout(closeNav, 700);
```

Sostituisci con:
```js
      if (status === 'OK') {
        directionsRenderer.setDirections(result);
        mapNavBtn.classList.add('active');
        navInfo.textContent = 'Percorso impostato ✓';
        speak('Navigazione avviata verso ' + dest);
        setTimeout(closeNav, 700);
```

- [ ] **Step 5: Ferma la voce quando si annulla il percorso**

Trova:
```js
  navClearBtn.addEventListener('click', () => {
    if (directionsRenderer) directionsRenderer.setDirections({ routes: [] });
    mapNavBtn.classList.remove('active');
    navInfo.textContent = 'Percorso annullato.';
  });
```

Sostituisci con:
```js
  navClearBtn.addEventListener('click', () => {
    if (directionsRenderer) directionsRenderer.setDirections({ routes: [] });
    speechSynthesis.cancel();
    mapNavBtn.classList.remove('active');
    navInfo.textContent = 'Percorso annullato.';
  });
```

- [ ] **Step 6: Verifica manuale**

In console: `speak('Prova voce')` deve produrre audio (o quantomeno non lanciare errori — su desktop senza voci installate potrebbe non produrre suono ma non deve eccepire). Tocca il toggle "Voce" nel popover: deve alternare tra "Attiva"/"Disattivata" e persistere (`localStorage.getItem('moto_voice')`). Con voce disattivata, `speak('test')` non deve chiamare `speechSynthesis.speak` (verificabile mettendo un breakpoint o controllando che non parta audio).

- [ ] **Step 7: Commit**

```bash
git add index.html
git commit -m "Aggiunge istruzioni vocali (Web Speech API) con toggle attiva/disattiva"
```

---

### Task 3: Avanzamento tappe, pannello prossima manovra, distanza/ETA

**Files:**
- Modify: `index.html` HTML (`.col-map`: aggiunge pannello prossima manovra + chip distanza/ETA)
- Modify: `index.html` CSS (nuove classi `.nav-panel`, `.route-info`)
- Modify: `index.html` blocco riferimenti DOM
- Modify: `index.html` `handlePosition()` (refactor distanza in helper + chiamata avanzamento nav)
- Modify: `index.html` `navGoBtn.addEventListener` (aggiunge `startNavigation(result)`)
- Modify: `index.html` `navClearBtn.addEventListener` (aggiunge `stopNavigation()`)

**Interfaces:**
- Consumes: `speak()` (Task 2). `directionsRenderer`/`directionsService` (esistenti). `lastLat`/`lastLon` (esistenti, aggiornati in `handlePosition`).
- Produces: funzione `distanceMeters(lat1, lon1, lat2, lon2)` (usata anche per l'odometro esistente), funzioni `startNavigation(result)`, `stopNavigation()`, `updateNavProgress(lat, lon)`. Task 4 non dipende da queste funzioni ma aggiunge una riga a `navGoBtn`/`navClearBtn` accanto a quelle create qui.

- [ ] **Step 1: Aggiungi il pannello prossima manovra e il chip distanza/ETA nell'HTML della mappa**

Trova:
```html
        <div class="map-nav-btn" id="mapNavBtn">🧭</div>
        <div class="map-empty" id="mapEmpty">In attesa di segnale GPS…</div>
```

Sostituisci con:
```html
        <div class="map-nav-btn" id="mapNavBtn">🧭</div>
        <div class="route-info" id="routeInfoEl"></div>
        <div class="nav-panel" id="navPanelEl">
          <div class="nav-panel-chevron" id="navPanelChevron">▲</div>
          <div class="nav-panel-body">
            <div class="nav-panel-text" id="navPanelText"></div>
            <div class="nav-panel-dist" id="navPanelDist"></div>
          </div>
        </div>
        <div class="map-empty" id="mapEmpty">In attesa di segnale GPS…</div>
```

- [ ] **Step 2: Aggiungi il CSS**

Trova:
```css
  .map-empty { position:absolute; inset:0; z-index:402; display:flex; align-items:center; justify-content:center; background: var(--bg); font-family: var(--mono); font-size:11px; color: var(--muted); text-align:center; padding:10px; }
```

Sostituisci con:
```css
  .map-empty { position:absolute; inset:0; z-index:402; display:flex; align-items:center; justify-content:center; background: var(--bg); font-family: var(--mono); font-size:11px; color: var(--muted); text-align:center; padding:10px; }

  .nav-panel {
    position:absolute; left:8px; bottom:8px; z-index:401; display:none;
    align-items:center; gap:8px; background: var(--overlay-bg); border:1px solid var(--panel-edge);
    border-radius:9px; padding:6px 10px; max-width: calc(100% - 16px);
  }
  .nav-panel.show { display:flex; }
  .nav-panel-chevron { font-family: var(--mono); font-size:20px; color: var(--blue-glow); flex:0 0 auto; }
  .nav-panel-body { min-width:0; }
  .nav-panel-text { font-family: var(--mono); font-size:11px; color: var(--ink); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:220px; }
  .nav-panel-dist { font-family: var(--mono); font-size:10px; color: var(--ink-dim); margin-top:1px; }

  .route-info {
    position:absolute; top:44px; right:8px; z-index:401; display:none;
    background: var(--overlay-bg); border:1px solid var(--panel-edge); border-radius:7px;
    padding:4px 8px; font-family: var(--mono); font-size:10px; color: var(--ink);
  }
  .route-info.show { display:block; }
```

- [ ] **Step 3: Aggiungi i riferimenti DOM**

Trova:
```js
  const voiceToggle = $('voiceToggle');
```

Sostituisci con:
```js
  const voiceToggle = $('voiceToggle');
  const navPanelEl = $('navPanelEl'), navPanelChevron = $('navPanelChevron'), navPanelText = $('navPanelText'), navPanelDist = $('navPanelDist');
  const routeInfoEl = $('routeInfoEl');
```

- [ ] **Step 4: Estrai `distanceMeters()` come funzione riusabile**

Trova:
```js
  function handlePosition(pos){
    const kmh = pos.coords.speed !== null && pos.coords.speed >= 0 ? (pos.coords.speed * 3.6) : null;
    speedVal.innerHTML = (kmh !== null ? kmh.toFixed(0) : '--') + '<span class="mini-unit">km/h</span>';

    let heading = null;
    if (pos.coords.heading !== null && pos.coords.heading !== undefined && !isNaN(pos.coords.heading) && (kmh === null || kmh > 5)) heading = pos.coords.heading;
    else if (compassHeading !== null) heading = compassHeading;
    else heading = lastHeading;

    if (lastLat !== null && lastLon !== null) {
      const dLon = (pos.coords.longitude - lastLon) * Math.cos(lastLat * Math.PI / 180) * 111320;
      const dLat = (pos.coords.latitude - lastLat) * 110540;
      const d = Math.hypot(dLon, dLat);
      if (d > 0.5) totalDistanceM += d;
    }
    lastLat = pos.coords.latitude; lastLon = pos.coords.longitude;
    distVal.textContent = (totalDistanceM / 1000).toFixed(1);

    updateMap(lastLat, lastLon, kmh, heading);
```

Sostituisci con:
```js
  // Approssimazione equirettangolare, adeguata per le distanze brevi che ci servono qui
  // (odometro di sessione, avanzamento tappe di navigazione) — non per distanze globali.
  function distanceMeters(lat1, lon1, lat2, lon2){
    const dLon = (lon2 - lon1) * Math.cos(lat1 * Math.PI / 180) * 111320;
    const dLat = (lat2 - lat1) * 110540;
    return Math.hypot(dLon, dLat);
  }

  function handlePosition(pos){
    const kmh = pos.coords.speed !== null && pos.coords.speed >= 0 ? (pos.coords.speed * 3.6) : null;
    speedVal.innerHTML = (kmh !== null ? kmh.toFixed(0) : '--') + '<span class="mini-unit">km/h</span>';

    let heading = null;
    if (pos.coords.heading !== null && pos.coords.heading !== undefined && !isNaN(pos.coords.heading) && (kmh === null || kmh > 5)) heading = pos.coords.heading;
    else if (compassHeading !== null) heading = compassHeading;
    else heading = lastHeading;

    if (lastLat !== null && lastLon !== null) {
      const d = distanceMeters(lastLat, lastLon, pos.coords.latitude, pos.coords.longitude);
      if (d > 0.5) totalDistanceM += d;
    }
    lastLat = pos.coords.latitude; lastLon = pos.coords.longitude;
    distVal.textContent = (totalDistanceM / 1000).toFixed(1);

    updateMap(lastLat, lastLon, kmh, heading);
    updateNavProgress(lastLat, lastLon);
```

- [ ] **Step 5: Aggiungi lo stato e le funzioni di navigazione, prima della sezione popover navigatore**

Trova:
```js
  /* ---------- voce (Web Speech API) ---------- */
```

Sostituisci con:
```js
  /* ---------- avanzamento navigazione (tappe, pannello, distanza/ETA) ---------- */
  let navSteps = [];
  let navStepIndex = 0;
  let navAnnounced = false;
  let navActive = false;

  function stripHtml(html){
    const div = document.createElement('div');
    div.innerHTML = html;
    return div.textContent || div.innerText || '';
  }

  const MANEUVER_CHEVRON = {
    'turn-left': '◀', 'turn-slight-left': '◀', 'turn-sharp-left': '◀', 'uturn-left': '◀',
    'turn-right': '▶', 'turn-slight-right': '▶', 'turn-sharp-right': '▶', 'uturn-right': '▶',
    'roundabout-left': '◀', 'roundabout-right': '▶',
    'merge': '▲', 'fork-left': '◀', 'fork-right': '▶', 'ramp-left': '◀', 'ramp-right': '▶',
    'straight': '▲'
  };
  function chevronForManeuver(maneuver){ return MANEUVER_CHEVRON[maneuver] || '▲'; }

  function startNavigation(result){
    navSteps = [];
    const legs = result.routes[0].legs;
    legs.forEach((leg, legIdx) => {
      leg.steps.forEach((step, stepIdx) => {
        navSteps.push({
          instructionText: stripHtml(step.instructions),
          maneuver: step.maneuver || 'straight',
          endLat: step.end_location.lat(), endLon: step.end_location.lng(),
          distanceM: step.distance ? step.distance.value : 0,
          durationS: step.duration ? step.duration.value : 0,
          isLegEnd: legIdx < legs.length - 1 && stepIdx === leg.steps.length - 1
        });
      });
    });
    navStepIndex = 0;
    navAnnounced = false;
    navActive = true;
    navPanelEl.classList.add('show');
    routeInfoEl.classList.add('show');
    updateNavPanel();
    updateRouteInfo();
  }

  function stopNavigation(){
    navActive = false;
    navSteps = [];
    navStepIndex = 0;
    navPanelEl.classList.remove('show');
    routeInfoEl.classList.remove('show');
  }

  function updateNavPanel(){
    if (!navActive || navStepIndex >= navSteps.length) return;
    const step = navSteps[navStepIndex];
    navPanelChevron.textContent = chevronForManeuver(step.maneuver);
    navPanelText.textContent = step.instructionText;
  }

  function updateRouteInfo(){
    if (!navActive) return;
    let remM = 0, remS = 0;
    for (let i = navStepIndex; i < navSteps.length; i++) { remM += navSteps[i].distanceM; remS += navSteps[i].durationS; }
    routeInfoEl.textContent = (remM / 1000).toFixed(1) + ' km · ' + Math.round(remS / 60) + ' min';
  }

  function updateNavProgress(lat, lon){
    if (!navActive || navStepIndex >= navSteps.length) return;
    const step = navSteps[navStepIndex];
    const dist = distanceMeters(lat, lon, step.endLat, step.endLon);
    navPanelDist.textContent = dist >= 1000 ? (dist / 1000).toFixed(1) + ' km' : Math.round(dist) + ' m';

    if (!navAnnounced && dist < 150) {
      speak(step.instructionText);
      navAnnounced = true;
    }
    if (dist < 30) {
      if (step.isLegEnd) speak('Tappa raggiunta.');
      navStepIndex++;
      navAnnounced = false;
      if (navStepIndex >= navSteps.length) {
        speak('Sei arrivato a destinazione.');
        navPanelText.textContent = 'Arrivato';
        navPanelDist.textContent = '';
        updateRouteInfo();
        return;
      }
      updateNavPanel();
    }
    updateRouteInfo();
  }

  /* ---------- voce (Web Speech API) ---------- */
```

- [ ] **Step 6: Avvia l'avanzamento quando parte la navigazione**

Trova:
```js
        navInfo.textContent = 'Percorso impostato ✓';
        speak('Navigazione avviata verso ' + dest);
        setTimeout(closeNav, 700);
```

Sostituisci con:
```js
        navInfo.textContent = 'Percorso impostato ✓';
        startNavigation(result);
        speak('Navigazione avviata verso ' + dest);
        setTimeout(closeNav, 700);
```

- [ ] **Step 7: Ferma l'avanzamento quando si annulla il percorso**

Trova:
```js
  navClearBtn.addEventListener('click', () => {
    if (directionsRenderer) directionsRenderer.setDirections({ routes: [] });
    speechSynthesis.cancel();
    mapNavBtn.classList.remove('active');
    navInfo.textContent = 'Percorso annullato.';
  });
```

Sostituisci con:
```js
  navClearBtn.addEventListener('click', () => {
    if (directionsRenderer) directionsRenderer.setDirections({ routes: [] });
    stopNavigation();
    speechSynthesis.cancel();
    mapNavBtn.classList.remove('active');
    navInfo.textContent = 'Percorso annullato.';
  });
```

- [ ] **Step 8: Verifica manuale (hand-trace, senza bisogno di un vero percorso Google)**

In console, costruisci un risultato finto e chiama `startNavigation()` direttamente per verificare la logica di avanzamento senza dover calcolare un vero percorso:
```js
const fakeResult = {
  routes: [{ legs: [{
    steps: [
      { instructions: 'Svolta a <b>destra</b> su Via Roma', maneuver: 'turn-right',
        end_location: { lat: () => 45.0, lng: () => 9.0 },
        distance: { value: 500 }, duration: { value: 60 } },
      { instructions: 'Prosegui dritto', maneuver: 'straight',
        end_location: { lat: () => 45.001, lng: () => 9.001 },
        distance: { value: 300 }, duration: { value: 40 } }
    ]
  }] }]
};
startNavigation(fakeResult);
document.getElementById('navPanelText').textContent // atteso: "Svolta a destra su Via Roma" (senza tag HTML)
document.getElementById('navPanelChevron').textContent // atteso: "▶"
document.getElementById('routeInfoEl').textContent // atteso: "0.8 km · 2 min" (800m/100s totali)
updateNavProgress(45.0, 9.0); // arrivo esatto al primo step
document.getElementById('navPanelText').textContent // atteso: "Prosegui dritto" (è avanzato al secondo step)
```

- [ ] **Step 9: Commit**

```bash
git add index.html
git commit -m "Aggiunge avanzamento tappe, pannello prossima manovra e distanza/ETA"
```

---

### Task 4: Restyling grafico mappa (temi chiaro/scuro, percorso con glow, mappa a filo schermo)

**Files:**
- Modify: `index.html` CSS (`.col-map` bordo, `NIGHT_STYLE`)
- Modify: `index.html` `ensureMap()` (nuovo `DAY_STYLE`, funzione di selezione stile, secondo `DirectionsRenderer` per il glow)
- Modify: `index.html` gestore click `themeToggle` (applica lo stile mappa al cambio tema)
- Modify: `index.html` state vars (aggiunge `directionsRendererGlow`)
- Modify: `index.html` `navGoBtn.addEventListener` (disegna anche sul renderer glow)
- Modify: `index.html` `navClearBtn.addEventListener` (pulisce anche il renderer glow)

**Interfaces:**
- Consumes: `directionsRenderer`/`ensureMap()` (esistenti). `navGoBtn`/`navClearBtn` come lasciati dal Task 3.
- Produces: `DAY_STYLE`, `mapStyleForTheme()`, `directionsRendererGlow`. Nessun task successivo in questo piano dipende da queste.

- [ ] **Step 1: Mappa a filo schermo — rimuovi l'arrotondamento sui lati esterni**

Trova:
```css
  .col-map {
    flex: 0 0 var(--map-pct); min-width:0; position:relative;
    border-radius:12px; overflow:hidden; background: var(--bg2);
  }
```

Sostituisci con:
```css
  .col-map {
    flex: 0 0 var(--map-pct); min-width:0; position:relative;
    border-radius:0; overflow:hidden; background: var(--bg2);
  }
```

- [ ] **Step 2: Sostituisci `NIGHT_STYLE` (nero puro, strade in risalto) e aggiungi `DAY_STYLE`**

Trova:
```js
  // dark "ghost" map style — muted roads/labels, bright accents left to the route line
  const NIGHT_STYLE = [
    { elementType: "geometry", stylers: [{ color: "#0A1526" }] },
    { elementType: "labels.text.fill", stylers: [{ color: "#5C7699" }] },
    { elementType: "labels.text.stroke", stylers: [{ color: "#050A14" }] },
    { featureType: "administrative", elementType: "geometry", stylers: [{ color: "#17283F" }] },
    { featureType: "poi", stylers: [{ visibility: "off" }] },
    { featureType: "road", elementType: "geometry", stylers: [{ color: "#17283F" }] },
    { featureType: "road", elementType: "geometry.stroke", stylers: [{ color: "#0A1526" }] },
    { featureType: "road.highway", elementType: "geometry", stylers: [{ color: "#1C3050" }] },
    { featureType: "road.highway", elementType: "geometry.stroke", stylers: [{ color: "#0A1526" }] },
    { featureType: "transit", stylers: [{ visibility: "off" }] },
    { featureType: "water", elementType: "geometry", stylers: [{ color: "#08111E" }] }
  ];
```

Sostituisci con:
```js
  // Notturno: nero puro (stesso --bg dell'HUD), strade chiare ben in risalto sul nero.
  const NIGHT_STYLE = [
    { elementType: "geometry", stylers: [{ color: "#000000" }] },
    { elementType: "labels.text.fill", stylers: [{ color: "#5C6A7D" }] },
    { elementType: "labels.text.stroke", stylers: [{ color: "#000000" }] },
    { featureType: "administrative", elementType: "geometry", stylers: [{ color: "#1C2128" }] },
    { featureType: "poi", stylers: [{ visibility: "off" }] },
    { featureType: "road", elementType: "geometry", stylers: [{ color: "#E8ECF0" }] },
    { featureType: "road", elementType: "geometry.stroke", stylers: [{ color: "#000000" }] },
    { featureType: "road.highway", elementType: "geometry", stylers: [{ color: "#FFFFFF" }] },
    { featureType: "road.highway", elementType: "geometry.stroke", stylers: [{ color: "#000000" }] },
    { featureType: "transit", stylers: [{ visibility: "off" }] },
    { featureType: "water", elementType: "geometry", stylers: [{ color: "#0A0E14" }] }
  ];
  // Diurno: bianco puro, strade scure ben in risalto sul bianco — stesso principio invertito.
  const DAY_STYLE = [
    { elementType: "geometry", stylers: [{ color: "#FFFFFF" }] },
    { elementType: "labels.text.fill", stylers: [{ color: "#3D4C63" }] },
    { elementType: "labels.text.stroke", stylers: [{ color: "#FFFFFF" }] },
    { featureType: "administrative", elementType: "geometry", stylers: [{ color: "#DCE2EA" }] },
    { featureType: "poi", stylers: [{ visibility: "off" }] },
    { featureType: "road", elementType: "geometry", stylers: [{ color: "#1B2430" }] },
    { featureType: "road", elementType: "geometry.stroke", stylers: [{ color: "#FFFFFF" }] },
    { featureType: "road.highway", elementType: "geometry", stylers: [{ color: "#000000" }] },
    { featureType: "road.highway", elementType: "geometry.stroke", stylers: [{ color: "#FFFFFF" }] },
    { featureType: "transit", stylers: [{ visibility: "off" }] },
    { featureType: "water", elementType: "geometry", stylers: [{ color: "#DCE2EA" }] }
  ];
  function mapStyleForTheme(){
    return document.documentElement.getAttribute('data-theme') === 'light' ? DAY_STYLE : NIGHT_STYLE;
  }
```

- [ ] **Step 3: Aggiungi lo stato per il renderer "glow" del percorso**

Trova:
```js
  let gmap = null, directionsService = null, directionsRenderer = null;
```

Sostituisci con:
```js
  let gmap = null, directionsService = null, directionsRenderer = null, directionsRendererGlow = null;
```

- [ ] **Step 4: Applica lo stile in base al tema e crea il renderer glow in `ensureMap()`**

Trova:
```js
  function ensureMap(lat, lon){
    if (gmap || !window.google) return;
    mapEmpty.style.display = 'none';
    gmap = new google.maps.Map(document.getElementById('gmap'), {
      center: { lat, lng: lon }, zoom: 17, styles: NIGHT_STYLE,
      disableDefaultUI: true, gestureHandling: 'none', clickableIcons: false
    });
    directionsService = new google.maps.DirectionsService();
    directionsRenderer = new google.maps.DirectionsRenderer({
      map: gmap, suppressMarkers: true, preserveViewport: true,
      polylineOptions: { strokeColor: '#5CC8FF', strokeOpacity: 0.95, strokeWeight: 6 }
    });
  }
```

Sostituisci con:
```js
  function ensureMap(lat, lon){
    if (gmap || !window.google) return;
    mapEmpty.style.display = 'none';
    gmap = new google.maps.Map(document.getElementById('gmap'), {
      center: { lat, lng: lon }, zoom: 17, styles: mapStyleForTheme(),
      disableDefaultUI: true, gestureHandling: 'none', clickableIcons: false
    });
    directionsService = new google.maps.DirectionsService();
    // Renderer "glow": traccia larga e semi-trasparente sotto quella nitida, stesso colore —
    // due DirectionsRenderer sulla stessa mappa, entrambi aggiornati con lo stesso risultato.
    directionsRendererGlow = new google.maps.DirectionsRenderer({
      map: gmap, suppressMarkers: true, preserveViewport: true,
      polylineOptions: { strokeColor: '#5CC8FF', strokeOpacity: 0.35, strokeWeight: 14 }
    });
    directionsRenderer = new google.maps.DirectionsRenderer({
      map: gmap, suppressMarkers: true, preserveViewport: true,
      polylineOptions: { strokeColor: '#5CC8FF', strokeOpacity: 0.95, strokeWeight: 6 }
    });
  }
```

- [ ] **Step 5: Aggiorna lo stile mappa quando cambia il tema**

Trova (cerca il gestore click del toggle tema, aggiunto nel piano del redesign HUD):
```js
  themeToggle.addEventListener('click', () => {
    const next = currentTheme() === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try { localStorage.setItem('moto_theme', next); } catch(e){}
    refreshThemeToggleLabel();
  });
```

Sostituisci con:
```js
  themeToggle.addEventListener('click', () => {
    const next = currentTheme() === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try { localStorage.setItem('moto_theme', next); } catch(e){}
    refreshThemeToggleLabel();
    if (gmap) gmap.setOptions({ styles: mapStyleForTheme() });
  });
```

- [ ] **Step 6: Disegna il percorso anche sul renderer glow**

Trova:
```js
      if (status === 'OK') {
        directionsRenderer.setDirections(result);
        mapNavBtn.classList.add('active');
```

Sostituisci con:
```js
      if (status === 'OK') {
        directionsRenderer.setDirections(result);
        directionsRendererGlow.setDirections(result);
        mapNavBtn.classList.add('active');
```

- [ ] **Step 7: Pulisci anche il renderer glow quando si annulla il percorso**

Trova:
```js
  navClearBtn.addEventListener('click', () => {
    if (directionsRenderer) directionsRenderer.setDirections({ routes: [] });
    stopNavigation();
```

Sostituisci con:
```js
  navClearBtn.addEventListener('click', () => {
    if (directionsRenderer) directionsRenderer.setDirections({ routes: [] });
    if (directionsRendererGlow) directionsRendererGlow.setDirections({ routes: [] });
    stopNavigation();
```

- [ ] **Step 8: Verifica manuale**

Se hai un browser con la chiave configurata: apri l'app, verifica che la mappa (una volta caricata, richiede GPS) sia nera con strade chiare in risalto. Tocca ⚙ → Tema per passare al diurno: la mappa deve diventare bianca con strade scure, senza dover ricaricare la pagina. Imposta un percorso: la linea deve avere un alone/glow visibile attorno alla traccia nitida centrale. Verifica che il lato sinistro/esterno della mappa non abbia più angoli arrotondati e arrivi fino al bordo dello schermo.

Se non hai un browser disponibile: verifica leggendo il codice che `mapStyleForTheme()` sia chiamata sia in `ensureMap()` che nel gestore `themeToggle`, che `directionsRendererGlow` sia dichiarato prima di ogni uso, e che `node --check`/estrazione JS non dia errori.

- [ ] **Step 9: Commit**

```bash
git add index.html
git commit -m "Restyla la mappa: temi chiaro/scuro coerenti con l'HUD, percorso con glow, filo schermo"
```

---

### Task 5: Aggiornamento CLAUDE.md e verifica finale

**Files:**
- Modify: `moto-telemetry/CLAUDE.md`

**Interfaces:**
- Consumes: nessuna (documentazione + verifica, nessuna modifica funzionale a `index.html`).

- [ ] **Step 1: Aggiorna la sezione "Mappa e navigazione" in CLAUDE.md**

Trova (cerca `### Mappa e navigazione`) il paragrafo sulla navigazione:
```markdown
- **Navigazione**: icona 🧭 apre un popover con un campo di testo libero (nessun autocomplete/Places, solo geocoding diretto via `DirectionsService`, che accetta stringhe di indirizzo). Il percorso viene disegnato come polyline blu luminosa (`DirectionsRenderer` con `polylineOptions` custom, `suppressMarkers:true`).
```

Sostituisci con:
```markdown
- **Navigazione**: icona 🧭 apre un popover con campo destinazione + tappe intermedie opzionali (pulsante "+ Aggiungi tappa"), tutti con **autocomplete Google Places** (richiede la Places API abilitata sul progetto Google Cloud dell'utente, sulla stessa chiave — se non abilitata, i campi degradano a testo libero senza errori). Il percorso è disegnato con un effetto **glow**: due `DirectionsRenderer` sovrapposti sulla stessa mappa (`directionsRendererGlow` largo/trasparente sotto, `directionsRenderer` nitido sopra), entrambi aggiornati con lo stesso risultato.
- **Istruzioni vocali**: Web Speech API (`speechSynthesis`, italiano), annuncio ad ogni manovra imminente (~150m prima, una sola volta per step) più un annuncio di conferma al click "Vai" (serve anche a sbloccare la sintesi vocale su iOS Safari per le chiamate successive). Toggle 🔊 nel popover, persistito in `localStorage` (`moto_voice`). La logica di avanzamento (`navSteps`/`navStepIndex`/`updateNavProgress()`) appiattisce tutte le `legs[].steps[]` del risultato Directions in una sequenza unica, con un annuncio extra ("Tappa raggiunta") al passaggio tra una tappa e la successiva.
- **Pannello prossima manovra**: badge compatto sulla mappa (stesso linguaggio grafico chevron dei gauge piega/beccheggio) con icona di manovra, testo istruzione, distanza alla manovra — aggiornato ad ogni fix GPS. Un chip separato vicino a 🧭 mostra distanza/ETA rimanenti (somma locale degli step non ancora completati, nessuna chiamata API aggiuntiva — non tiene conto del traffico in tempo reale).
- **Navigazione indipendente dalla registrazione telemetria**: funziona sia con **Avvia** premuto che senza.
```

- [ ] **Step 2: Aggiorna la nota sullo stile mappa**

Trova (nella stessa sezione, il primo punto):
```markdown
- **Google Maps JS API**, stile custom scuro/blu (array `NIGHT_STYLE` nel codice) per un effetto "notturno/ghost" coerente col resto del tema.
```

Sostituisci con:
```markdown
- **Google Maps JS API**, stile custom **nero puro / bianco puro** (`NIGHT_STYLE`/`DAY_STYLE` nel codice, selezionati da `mapStyleForTheme()`) coerente col sistema di temi chiaro/scuro del resto dell'HUD — cambia dal vivo (`gmap.setOptions({styles:...})`) quando si tocca il toggle Tema in Impostazioni, senza ricaricare la pagina.
```

- [ ] **Step 3: Smoke test manuale completo**

Con `python3 -m http.server 8000` attivo:
1. Console: nessun errore al caricamento.
2. Apri 🧭: la lista tappe è vuota, "+ Aggiungi tappa" crea/rimuove campi correttamente (`waypointInputs.length` coerente).
3. Se hai una chiave Google con Places abilitata: digita un indirizzo, verifica i suggerimenti; imposta una destinazione con una tappa; verifica che parta un annuncio vocale di conferma, che compaia il pannello prossima manovra in basso a sinistra sulla mappa e il chip distanza/ETA vicino a 🧭.
4. Tocca ⚙ → Tema: la mappa cambia colore dal vivo (nero↔bianco, strade coerenti), il resto dell'HUD segue come già verificato nel piano precedente.
5. "Annulla percorso": pannello prossima manovra e chip distanza/ETA spariscono, la voce si interrompe, entrambe le polyline (glow + nitida) si puliscono.
6. Verifica CSV: esporta un file, controlla che l'header sia invariato (nessuna nuova colonna) — la navigazione non tocca il logging telemetria.

- [ ] **Step 4: Commit finale**

```bash
git add CLAUDE.md
git commit -m "Aggiorna CLAUDE.md per navigazione turn-by-turn e restyling mappa"
```
