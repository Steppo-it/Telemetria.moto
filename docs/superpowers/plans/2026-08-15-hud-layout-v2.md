# HUD layout v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ristrutturare l'HUD in tre colonne (sinistra: piega+G laterale, centro: navigatore+mappa, destra: beccheggio+G longitudinale), con card grandi personalizzabili (scambiabili), un pannello comandi unico, nuovi dati di sessione (timer, top G) e il rebrand TELAMETRIA.

**Architecture:** Tutto in `index.html` (nessun build system). Le 4 card grandi (piega/beccheggio/G laterale/G longitudinale) sono elementi DOM fissi con `data-metric` identificativo, spostati fisicamente tra 4 contenitori "slot" via `appendChild()` per realizzare lo scambio — niente templating dinamico, solo riposizionamento DOM. Un pannello popover generico e riusabile ("picker") serve sia lo scambio delle 4 card grandi sia la scelta dei 2 mini-tile.

**Tech Stack:** HTML/CSS/JS vanilla, nessuna nuova dipendenza.

**Spec:** `docs/superpowers/specs/2026-08-15-hud-layout-v2-design.md`

## Global Constraints

- Nessun build system, bundler o package manager: tutto resta in `index.html`.
- Nessuna nuova dipendenza esterna.
- Formato export CSV invariato (stesse colonne/header).
- Logica sensori (calcolo piega/beccheggio/G, soglie colore, calibrazione) **invariata** — questo piano tocca solo resa visiva, posizionamento, e alcuni nuovi valori di sessione derivati dagli stessi calcoli esistenti.
- Il popover **Navigatore** (indirizzo/tappe/autocomplete) resta un popover separato, invariato nell'apertura (icona 🧭 sulla mappa) — non confluisce nel nuovo pannello comandi, tranne il toggle Voce che si sposta lì (vedi Task 5).
- Restyling grafico della mappa: fuori scope, non toccare `NIGHT_STYLE`/`DAY_STYLE`/`ensureMap`/`updateMap` oltre a quanto strettamente necessario per il nuovo posizionamento.
- La funzionalità "mappa ridimensionabile via drag" (`--map-pct`, `#resizeHandle`) viene **rimossa**: nel nuovo layout a tre colonne fisse non c'è più un rapporto mappa/HUD da trascinare. Conseguenza esplicita e voluta del nuovo layout, non una svista.

---

## Riferimento: file di partenza

Tutti i riferimenti a riga sotto si intendono sullo stato di `moto-telemetry/index.html` all'inizio del Task 1 (commit `8e15353`, 1081 righe). Da Task 2 in poi alcune righe si saranno spostate: se un riferimento a riga non corrisponde più esattamente, individua il blocco cercando la stringa indicata (selettore CSS, id, nome funzione) invece di fidarti del numero.

Verifica per ogni task: `python3 -m http.server 8000` dentro `moto-telemetry/`, apri `http://localhost:8000/`, DevTools console aperta. Per la logica non visiva, simula via console (`window.dispatchEvent(new DeviceOrientationEvent(...))`, `new DeviceMotionEvent(...)`) come nei piani precedenti. Se hai un browser reale/headless disponibile, usalo per una verifica visiva vera; altrimenti hand-trace + controllo sintassi (`node --check` sui blocchi `<script>` estratti, o `new Function(...)`).

---

### Task 1: Layout a tre colonne — scheletro HTML/CSS, rebrand, rimozione resize/vecchie card

**Files:**
- Modify: `index.html` CSS (blocco `.layout`...`.mini-actions-row`, righe 88-227)
- Modify: `index.html` HTML (`.brand`, riga 266; blocco `.layout`...`.col-hud`, righe 271-336)
- Modify: `index.html` JS (rimuove `initResize` IIFE, righe 389-403; rimuove riferimenti DOM a `resizeHandle`/`colMap`)

**Interfaces:**
- Consumes: token tema esistenti (`--ink`, `--ink-dim`, `--hair`, `--bg`, `--bg2`, `--accent`, `--overlay-bg`, `--blue-glow`, `--amber`, `--red`).
- Produces: struttura DOM `#colSideLeft`/`#colCenter`/`#colSideRight`, quattro contenitori slot `#slotLeftTop`/`#slotLeftBottom`/`#slotRightTop`/`#slotRightBottom`, quattro card `#cardLean`/`#cardPitch`/`#cardGLat`/`#cardGLong` (ciascuna con `data-metric` e i suoi id interni), riga mini-tile `#miniSlot1`/`#miniSlot2` con `#miniLabel1`/`#miniVal1`/`#miniLabel2`/`#miniVal2`, zona `.cockpit-void`. Classi CSS `.stat-card`, `.stat-bar-track`, `.stat-bar-fill`, `.stat-bar-ticks`, `.stat-maxrow`, `.stat-swap-btn`. Task 2 userà questi id per la logica dati; Task 6/7 useranno gli slot per lo scambio.

- [ ] **Step 1: Sostituisci il CSS del vecchio layout mappa/HUD con le tre colonne**

Trova (righe 88-156, da `.layout` a `.hud-bottom`):
```css
  .layout { display:flex; flex-direction:row; gap:0; flex:1 1 auto; min-height:0; }

  /* ============ MAP (left, resizable) ============ */
  .col-map {
    flex: 0 0 var(--map-pct); min-width:0; position:relative;
    border-radius:0; overflow:hidden; background: var(--bg2);
  }
  .col-map::after {
    /* bottom:22px (invece di 0) lascia libero l'angolo in basso a destra della mappa, dove
       Google Maps disegna la striscia di attribuzione ("Map data © / Termini / Segnala un
       errore") — deve restare sempre completamente visibile e non velata dalla dissolvenza. */
    content:''; position:absolute; top:0; bottom:22px; right:0; width:70px;
    background: linear-gradient(90deg, transparent, var(--bg) 92%);
    pointer-events:none; z-index:5;
  }
  #gmap { width:100%; height:100%; background: var(--panel); }

  .map-arrow {
    position:absolute; top:50%; left:50%; transform:translate(-50%,-50%) rotate(0deg);
    width:0; height:0; z-index:400; pointer-events:none; transition: transform .2s linear;
    border-left:11px solid transparent; border-right:11px solid transparent; border-bottom:22px solid var(--amber);
    filter: drop-shadow(0 0 7px rgba(255,154,61,.8));
  }
  .map-arrow::after { content:''; position:absolute; left:-11px; top:22px; width:22px; height:8px; background: var(--amber); border-radius:0 0 4px 4px; opacity:.85; }

  .map-badge { position:absolute; top:8px; left:8px; z-index:401; background: var(--overlay-bg); border:1px solid var(--panel-edge); border-radius:7px; padding:4px 8px; font-family: var(--mono); font-size:10px; color: var(--text); box-shadow: 0 0 10px rgba(46,142,255,.15); }
  .map-badge b { color: var(--ink); }
  .map-nav-btn {
    position:absolute; top:8px; right:8px; z-index:401; width:30px; height:30px; border-radius:8px;
    background: var(--overlay-bg); border:1px solid var(--panel-edge); display:flex; align-items:center; justify-content:center;
    font-size:15px; cursor:pointer; box-shadow: 0 0 10px rgba(46,142,255,.15);
  }
  .map-nav-btn.active { background: var(--blue); box-shadow: 0 0 12px rgba(46,142,255,.6); }
  .map-empty { position:absolute; inset:0; z-index:402; display:flex; align-items:center; justify-content:center; background: var(--bg); font-family: var(--mono); font-size:11px; color: var(--muted); text-align:center; padding:10px; }

  .map-recenter-btn {
    position:absolute; bottom:8px; right:8px; z-index:401; width:34px; height:34px; border-radius:50%;
    background: var(--overlay-bg); border:1px solid var(--panel-edge); display:none;
    align-items:center; justify-content:center; font-size:16px; cursor:pointer;
    box-shadow: 0 0 10px rgba(46,142,255,.15);
  }
  .map-recenter-btn.show { display:flex; }

  .nav-panel {
    position:absolute; left:8px; bottom:34px; z-index:401; display:none;
    align-items:center; gap:8px; background: var(--overlay-bg); border:1px solid var(--panel-edge);
    border-radius:9px; padding:6px 10px; max-width: calc(100% - 16px);
  }
  .nav-panel.show { display:flex; }
  .nav-panel-chevron { font-family: var(--mono); font-size:20px; color: var(--accent); flex:0 0 auto; }
  .nav-panel-body { min-width:0; }
  .nav-panel-text { font-family: var(--mono); font-size:11px; color: var(--ink); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:220px; }
  .nav-panel-dist { font-family: var(--mono); font-size:10px; color: var(--ink-dim); margin-top:1px; }

  .route-info {
    position:absolute; top:44px; right:8px; z-index:401; display:none;
    background: var(--overlay-bg); border:1px solid var(--panel-edge); border-radius:7px;
    padding:4px 8px; font-family: var(--mono); font-size:10px; color: var(--ink);
  }
  .route-info.show { display:block; }

  .resize-handle { flex: 0 0 20px; display:flex; align-items:center; justify-content:center; cursor:ew-resize; touch-action:none; position:relative; z-index:5; }
  .resize-handle .grip { width:5px; height:44px; border-radius:3px; background: var(--panel-edge); box-shadow: 0 0 8px rgba(46,142,255,.15); transition: background .15s; }
  .resize-handle:active .grip, .resize-handle.dragging .grip { background: var(--blue); box-shadow: 0 0 12px rgba(46,142,255,.6); }

  /* ============ HUD column (right) ============ */
  .col-hud { flex:1 1 auto; min-width:100px; display:flex; flex-direction:column; gap:5px; min-height:0; }
  .hud-top { flex:1 1 auto; min-height:0; display:flex; flex-direction:column; gap:5px; overflow-y:auto; }
  .hud-bottom { flex:0 0 auto; display:flex; flex-direction:column; gap:7px; }

  /* --- lean + pitch badges + barra G, riga interna a hud-top --- */
  .gauge-cluster { flex:1 1 auto; min-height:0; display:flex; gap:8px; }
  .gauges-col { flex:1 1 auto; display:flex; flex-direction:column; gap:6px; min-width:0; }
  .gauge-badge { display:flex; align-items:center; gap:9px; min-width:0; }
  .lean-badge { flex: 1.5 1 0; }
  .pitch-badge { flex: 1 1 0; }

  .gauge-chevron {
    font-family: var(--mono); line-height:1; color: var(--accent);
    border:1px solid var(--hair); border-radius:6px; padding:5px 9px;
    transition: color .15s, border-color .15s;
  }
  .lean-badge .gauge-chevron { font-size: clamp(26px, 6.5vh, 36px); }
  .pitch-badge .gauge-chevron { font-size: clamp(18px, 4.2vh, 24px); }
  /* soglie colore warn/danger: solo la piega le usa (updateLeanGauge()) — il beccheggio non
     ha mai soglie colore per spec, quindi queste regole sono scoped a .lean-badge invece di
     essere globali, per rispecchiare in CSS un vincolo che finora esisteva solo in JS */
  .lean-badge .gauge-chevron.warn { color: var(--amber); border-color: var(--amber); }
  .lean-badge .gauge-chevron.danger { color: var(--red); border-color: var(--red); }

  .gauge-body { flex:0 0 auto; min-width:0; }
  .gauge-num { font-family: var(--disp); font-weight:800; line-height:1; color: var(--ink); letter-spacing:.5px; }
  .lean-badge .gauge-num { font-size: clamp(34px, 8.5vh, 50px); }
  .pitch-badge .gauge-num { font-size: clamp(20px, 5.2vh, 28px); }
  .lean-badge .gauge-num.warn { color: var(--amber); }
  .lean-badge .gauge-num.danger { color: var(--red); }
  .gauge-sub { font-family: var(--mono); font-size:9.5px; letter-spacing:1.3px; color: var(--ink-dim); margin-top:2px; }

  .gauge-maxrow { margin-left:auto; text-align:right; font-family: var(--mono); font-size:10.5px; color: var(--ink-dim); line-height:1.7; white-space:nowrap; }
  .gauge-maxrow b { color: var(--ink); font-weight:700; font-size:12px; }

  /* --- G force vertical bar --- */
  .gforce-bar {
    width:26px; flex:0 0 auto; align-self:stretch; border-radius:5px; position:relative;
    background: linear-gradient(180deg, var(--blue) 0%, #6FE0B8 26%, var(--hair) 48%, var(--hair) 52%, var(--amber) 74%, var(--red) 100%);
  }
  .gforce-marker {
    position:absolute; left:-4px; right:-4px; height:6px; top:50%; transform: translateY(-50%);
    background: var(--ink); border-radius:3px; box-shadow: 0 0 8px 1px rgba(0,0,0,.55), 0 0 4px var(--bg2);
    opacity:0; transition: opacity .3s, top .12s linear;
  }
  .gforce-val {
    position:absolute; bottom:5px; left:-8px; right:-8px; text-align:center;
    font-family: var(--mono); font-size:9px; font-weight:700; color: var(--ink);
    text-shadow: 0 0 4px var(--bg), 0 0 4px var(--bg);
  }

  /* --- riga compatta velocità + punteggio --- */
  .mini-row { display:flex; gap:16px; border-top:1px solid var(--hair); padding-top:6px; flex:0 0 auto; }
  .mini-item { display:flex; flex-direction:column; }
  .mini-label { font-family: var(--mono); font-size:8px; letter-spacing:1px; color: var(--ink-dim); text-transform:uppercase; }
  .mini-val { font-family: var(--disp); font-size:20px; color: var(--ink); font-weight:700; }
  .mini-unit { font-size:11px; color: var(--ink-dim); margin-left:2px; font-family: var(--mono); font-weight:400; }

  /* ============ big blind-tappable controls (monocromatici) ============ */
  .btn-big {
    appearance:none; border:none; border-radius:12px; padding:14px; font-family: var(--disp); font-weight:700; font-size:16px; letter-spacing:1px;
    display:flex; align-items:center; justify-content:center; gap:6px; cursor:pointer; min-height:56px;
    transition: transform .1s, opacity .2s;
  }
  .btn-big:active { transform: scale(0.97); }
  .btn-big.start, .btn-big.stop { background: var(--ink); color: var(--bg); }
  .btn-big.calib { background:transparent; border:2px solid var(--ink-dim); color: var(--ink); }
  .btn-big[disabled] { opacity:.5; pointer-events:none; }

  .mini-actions-row { display:flex; gap:7px; }
  .btn-mini { appearance:none; border:1px solid var(--hair); background:transparent; color: var(--ink-dim); border-radius:9px; padding:7px 3px; font-family:'Inter',sans-serif; font-weight:500; font-size:10px; display:flex; align-items:center; justify-content:center; text-align:center; gap:3px; flex:1 1 0; min-width:0; cursor:pointer; min-height:38px; }
  .btn-mini:disabled { opacity:.4; }
```

Sostituisci con:
```css
  .layout { display:flex; flex-direction:row; gap:6px; flex:1 1 auto; min-height:0; }

  /* ============ colonne laterali (piega+Glat a sx, beccheggio+Glong a dx) ============ */
  .col-side { flex:0 0 168px; display:flex; flex-direction:column; gap:6px; min-height:0; }

  .stat-card {
    flex:1 1 0; min-height:0; background: var(--bg2); border-radius:9px; padding:8px 10px;
    display:flex; flex-direction:column; justify-content:center; position:relative;
  }
  .stat-card-label { font-family: var(--mono); font-size:9px; letter-spacing:1.3px; color: var(--ink-dim); text-transform:uppercase; }
  .stat-card-num { font-family: var(--disp); font-weight:800; line-height:1; color: var(--ink); letter-spacing:.5px; font-size: clamp(30px, 8.5vh, 52px); margin:3px 0; }
  .stat-card-num.warn { color: var(--amber); }
  .stat-card-num.danger { color: var(--red); }
  .stat-card-sub { font-family: var(--mono); font-size:10px; letter-spacing:1px; color: var(--accent); margin-bottom:4px; }
  .stat-card-sub.warn { color: var(--amber); }
  .stat-card-sub.danger { color: var(--red); }

  .stat-bar-track { position:relative; height:8px; border-radius:4px; background: var(--hair); margin:2px 0 3px; }
  .stat-bar-fill { position:absolute; top:0; bottom:0; border-radius:4px; background: var(--blue-glow); }
  .stat-bar-ticks { display:flex; justify-content:space-between; font-family: var(--mono); font-size:8px; color: var(--ink-dim); }

  .stat-maxrow { display:flex; justify-content:space-between; font-family: var(--mono); font-size:9px; color: var(--ink-dim); margin-top:5px; }
  .stat-maxrow b { color: var(--ink); font-weight:700; }

  .stat-swap-btn {
    position:absolute; top:4px; right:4px; width:30px; height:30px; border-radius:7px;
    background: var(--hair); color: var(--accent); font-family: var(--mono); font-size:14px;
    display:none; align-items:center; justify-content:center; cursor:pointer; z-index:2;
  }
  .app.edit-mode .stat-swap-btn { display:flex; }

  .cockpit-void { flex:0 0 80px; border-radius:9px; pointer-events:none; }

  /* --- mini-riga personalizzabile (default Sessione/Distanza), solo in fondo alla colonna sx --- */
  .mini-row { display:flex; gap:6px; flex:0 0 40px; }
  .mini-item {
    flex:1 1 0; background: var(--bg2); border-radius:8px; display:flex; flex-direction:column;
    align-items:center; justify-content:center; position:relative; min-width:0;
  }
  .mini-label { font-family: var(--mono); font-size:7.5px; letter-spacing:1px; color: var(--ink-dim); text-transform:uppercase; }
  .mini-val { font-family: var(--disp); font-size:16px; color: var(--ink); font-weight:700; }
  .mini-item .stat-swap-btn { top:2px; right:2px; width:26px; height:26px; font-size:11px; }

  /* ============ colonna centrale: barra navigatore + mappa ============ */
  .col-center { flex:1 1 auto; min-width:0; display:flex; flex-direction:column; gap:6px; }

  .col-map { flex:1 1 auto; min-width:0; position:relative; border-radius:9px; overflow:hidden; background: var(--bg2); }
  #gmap { width:100%; height:100%; background: var(--panel); }

  .map-arrow {
    position:absolute; top:50%; left:50%; transform:translate(-50%,-50%) rotate(0deg);
    width:0; height:0; z-index:400; pointer-events:none; transition: transform .2s linear;
    border-left:11px solid transparent; border-right:11px solid transparent; border-bottom:22px solid var(--amber);
    filter: drop-shadow(0 0 7px rgba(255,154,61,.8));
  }
  .map-arrow::after { content:''; position:absolute; left:-11px; top:22px; width:22px; height:8px; background: var(--amber); border-radius:0 0 4px 4px; opacity:.85; }

  .map-nav-btn {
    position:absolute; top:8px; right:8px; z-index:401; width:30px; height:30px; border-radius:8px;
    background: var(--overlay-bg); border:1px solid var(--panel-edge); display:flex; align-items:center; justify-content:center;
    font-size:15px; cursor:pointer; box-shadow: 0 0 10px rgba(46,142,255,.15);
  }
  .map-nav-btn.active { background: var(--blue); box-shadow: 0 0 12px rgba(46,142,255,.6); }
  .map-empty { position:absolute; inset:0; z-index:402; display:flex; align-items:center; justify-content:center; background: var(--bg); font-family: var(--mono); font-size:11px; color: var(--muted); text-align:center; padding:10px; }

  .map-recenter-btn {
    position:absolute; bottom:8px; right:8px; z-index:401; width:34px; height:34px; border-radius:50%;
    background: var(--overlay-bg); border:1px solid var(--panel-edge); display:none;
    align-items:center; justify-content:center; font-size:16px; cursor:pointer;
    box-shadow: 0 0 10px rgba(46,142,255,.15);
  }
  .map-recenter-btn.show { display:flex; }

  .nav-topbar {
    flex:0 0 30px; display:flex; align-items:center; justify-content:center; gap:10px;
    background: var(--bg2); border-radius:9px; padding:0 12px;
  }
  .nav-topbar-chevron { font-family: var(--mono); font-size:16px; color: var(--accent); flex:0 0 auto; }
  .nav-topbar-text { font-family: var(--mono); font-size:11px; color: var(--ink); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .nav-topbar-text b { color: var(--blue-glow); }
  .nav-topbar-dist { font-family: var(--mono); font-size:10px; color: var(--ink-dim); }
  .nav-topbar-eta { font-family: var(--mono); font-size:9px; color: var(--ink-dim); margin-left:auto; flex:0 0 auto; }
  .nav-topbar.idle .nav-topbar-text { color: var(--ink-dim); }

  /* ============ pulsanti (invariati nello stile, li sposta il Task 5 nel pannello comandi) ============ */
  .btn-big {
    appearance:none; border:none; border-radius:12px; padding:14px; font-family: var(--disp); font-weight:700; font-size:16px; letter-spacing:1px;
    display:flex; align-items:center; justify-content:center; gap:6px; cursor:pointer; min-height:56px;
    transition: transform .1s, opacity .2s;
  }
  .btn-big:active { transform: scale(0.97); }
  .btn-big.start, .btn-big.stop { background: var(--ink); color: var(--bg); }
  .btn-big.calib { background:transparent; border:2px solid var(--ink-dim); color: var(--ink); }
  .btn-big[disabled] { opacity:.5; pointer-events:none; }

  .mini-actions-row { display:flex; gap:7px; }
  .btn-mini { appearance:none; border:1px solid var(--hair); background:transparent; color: var(--ink-dim); border-radius:9px; padding:7px 3px; font-family:'Inter',sans-serif; font-weight:500; font-size:10px; display:flex; align-items:center; justify-content:center; text-align:center; gap:3px; flex:1 1 0; min-width:0; cursor:pointer; min-height:38px; }
  .btn-mini:disabled { opacity:.4; }
```

(Nota: `.mini-actions-row`/`.btn-mini`/`.btn-big` restano definiti qui — li userà ancora il Task 5 per il nuovo pannello comandi, anche se `.hud-bottom`/`.hud-top`/`.col-hud` come contenitori spariscono da questo task in poi.)

- [ ] **Step 2: Rebrand della topbar**

Trova:
```html
      <div class="brand">TELEMETRIA<span>.MOTO</span></div>
```

Sostituisci con:
```html
      <div class="brand">TELAMETRIA<span style="font-size:8px; letter-spacing:.5px; margin-left:6px; vertical-align:middle;">By TelaStampiamo</span></div>
```

- [ ] **Step 3: Sostituisci l'intero blocco `.layout` con le tre colonne**

Trova (righe 271-336, dall'apertura `<div class="layout">` alla chiusura di `.col-hud`):
```html
    <div class="layout">

      <div class="col-map" id="colMap">
        <div id="gmap"></div>
        <div class="map-arrow" id="mapArrow"></div>
        <div class="map-badge"><b id="distVal">0.0</b> km</div>
        <div class="map-nav-btn" id="mapNavBtn">🧭</div>
        <div class="map-recenter-btn" id="mapRecenterBtn">📍</div>
        <div class="route-info" id="routeInfoEl"></div>
        <div class="nav-panel" id="navPanelEl">
          <div class="nav-panel-chevron" id="navPanelChevron">▲</div>
          <div class="nav-panel-body">
            <div class="nav-panel-text" id="navPanelText"></div>
            <div class="nav-panel-dist" id="navPanelDist"></div>
          </div>
        </div>
        <div class="map-empty" id="mapEmpty">In attesa di segnale GPS…</div>
      </div>

      <div class="resize-handle" id="resizeHandle"><div class="grip"></div></div>

      <div class="col-hud">
        <div class="hud-top">
          <div class="gauge-cluster">
            <div class="gauges-col">
              <div class="gauge-badge lean-badge">
                <div class="gauge-chevron" id="leanChevron">–</div>
                <div class="gauge-body">
                  <div class="gauge-num" id="leanNumBig">--°</div>
                  <div class="gauge-sub" id="leanSub">PIEGA</div>
                </div>
                <div class="gauge-maxrow">SX <b id="leanMaxSx">--°</b><br>DX <b id="leanMaxDx">--°</b></div>
              </div>
              <div class="gauge-badge pitch-badge">
                <div class="gauge-chevron" id="pitchChevron">–</div>
                <div class="gauge-body">
                  <div class="gauge-num" id="pitchNumBig">--°</div>
                  <div class="gauge-sub" id="pitchSub">BECCHEGGIO</div>
                </div>
                <div class="gauge-maxrow">GIÙ <b id="pitchMaxDown">--°</b><br>SU <b id="pitchMaxUp">--°</b></div>
              </div>
            </div>
            <div class="gforce-bar">
              <div class="gforce-marker" id="gGhost"></div>
              <div class="gforce-val" id="gforceVal">0.00g</div>
            </div>
          </div>

          <div class="mini-row">
            <div class="mini-item"><span class="mini-label">Velocità</span><span class="mini-val" id="speedVal">--<span class="mini-unit">km/h</span></span></div>
            <div class="mini-item"><span class="mini-label">Guida</span><span class="mini-val" id="scoreNum">--</span></div>
          </div>
        </div>

        <div class="hud-bottom">
          <button class="btn-big start" id="mainBtn">Avvia</button>
          <button class="btn-big calib" id="calibBtn">Calibra</button>
          <div class="mini-actions-row">
            <button class="btn-mini" id="resetMaxBtn">↺ Reset max</button>
            <button class="btn-mini" id="settingsBtn">⚙ Impostazioni</button>
            <button class="btn-mini" id="exportBtn" disabled>⭳ CSV</button>
          </div>
          <div class="log-info" id="logInfo"></div>
        </div>
      </div>
    </div>
```

Sostituisci con:
```html
    <div class="layout">

      <div class="col-side left" id="colSideLeft">
        <div class="slot" id="slotLeftTop"></div>
        <div class="slot" id="slotLeftBottom"></div>
        <div class="mini-row">
          <div class="mini-item" id="miniSlot1">
            <div class="stat-swap-btn" data-mini-slot="slot1">⇄</div>
            <span class="mini-label" id="miniLabel1">Sessione</span>
            <span class="mini-val" id="miniVal1">00:00</span>
          </div>
          <div class="mini-item" id="miniSlot2">
            <div class="stat-swap-btn" data-mini-slot="slot2">⇄</div>
            <span class="mini-label" id="miniLabel2">Distanza</span>
            <span class="mini-val" id="miniVal2">0.0km</span>
          </div>
        </div>
      </div>

      <div class="col-center">
        <div class="nav-topbar idle" id="navTopbar">
          <div class="nav-topbar-chevron" id="navTopbarChevron">–</div>
          <div class="nav-topbar-text" id="navTopbarText">Nessun percorso impostato</div>
          <div class="nav-topbar-dist" id="navTopbarDist"></div>
          <div class="nav-topbar-eta" id="navTopbarEta"></div>
        </div>
        <div class="col-map" id="colMap">
          <div id="gmap"></div>
          <div class="map-arrow" id="mapArrow"></div>
          <div class="map-nav-btn" id="mapNavBtn">🧭</div>
          <div class="map-recenter-btn" id="mapRecenterBtn">📍</div>
          <div class="map-empty" id="mapEmpty">In attesa di segnale GPS…</div>
        </div>
      </div>

      <div class="col-side right" id="colSideRight">
        <div class="slot" id="slotRightTop"></div>
        <div class="slot" id="slotRightBottom"></div>
        <div class="cockpit-void"></div>
      </div>
    </div>

    <div id="cardLean" class="stat-card" data-metric="lean">
      <div class="stat-swap-btn" data-metric="lean">⇄</div>
      <div class="stat-card-label">Piega</div>
      <div class="stat-card-num" id="leanNumBig">--°</div>
      <div class="stat-card-sub" id="leanSub">–</div>
      <div class="stat-bar-track"><div class="stat-bar-fill" id="leanBarFill" style="left:50%; width:0%"></div></div>
      <div class="stat-bar-ticks"><span>60</span><span>0</span><span>60</span></div>
      <div class="stat-maxrow"><span>MAX SX <b id="leanMaxSx">--°</b></span><span>MAX DX <b id="leanMaxDx">--°</b></span></div>
    </div>
    <div id="cardPitch" class="stat-card" data-metric="pitch">
      <div class="stat-swap-btn" data-metric="pitch">⇄</div>
      <div class="stat-card-label">Beccheggio</div>
      <div class="stat-card-num" id="pitchNumBig">--°</div>
      <div class="stat-card-sub" id="pitchSub">–</div>
      <div class="stat-bar-track"><div class="stat-bar-fill" id="pitchBarFill" style="left:50%; width:0%"></div></div>
      <div class="stat-bar-ticks"><span>45</span><span>0</span><span>45</span></div>
      <div class="stat-maxrow"><span>UP <b id="pitchMaxUp">--°</b></span><span>DOWN <b id="pitchMaxDown">--°</b></span></div>
    </div>
    <div id="cardGLat" class="stat-card" data-metric="gLat">
      <div class="stat-swap-btn" data-metric="gLat">⇄</div>
      <div class="stat-card-label">G Laterale</div>
      <div class="stat-card-num" id="gLatNumBig">0.00g</div>
      <div class="stat-bar-track"><div class="stat-bar-fill" id="gLatBarFill" style="left:50%; width:0%"></div></div>
      <div class="stat-bar-ticks"><span>-1.5</span><span>0</span><span>1.5</span></div>
      <div class="stat-maxrow"><span>TOP <b id="gLatTop">0.00g</b></span></div>
    </div>
    <div id="cardGLong" class="stat-card" data-metric="gLong">
      <div class="stat-swap-btn" data-metric="gLong">⇄</div>
      <div class="stat-card-label">G Longitudinale</div>
      <div class="stat-card-num" id="gLongNumBig">0.00g</div>
      <div class="stat-bar-track"><div class="stat-bar-fill" id="gLongBarFill" style="left:50%; width:0%"></div></div>
      <div class="stat-bar-ticks"><span>-1</span><span>0</span><span>1</span></div>
      <div class="stat-maxrow"><span>TOP <b id="gLongTop">0.00g</b></span></div>
    </div>

    <div class="hud-bottom-placeholder" style="display:none">
      <button class="btn-big start" id="mainBtn">Avvia</button>
      <button class="btn-big calib" id="calibBtn">Calibra</button>
      <button class="btn-mini" id="resetMaxBtn">↺ Reset max</button>
      <button class="btn-mini" id="exportBtn" disabled>⭳ CSV</button>
      <div class="log-info" id="logInfo"></div>
    </div>
```

(Le 4 card `#cardLean`/`#cardPitch`/`#cardGLat`/`#cardGLong` vengono create **fuori** dagli slot, come "magazzino": lo Step 5 di questo task le sposta negli slot corretti via JS. `#mainBtn`/`#calibBtn`/`#resetMaxBtn`/`#exportBtn`/`#logInfo` restano temporaneamente in un contenitore nascosto — il Task 5 li sposterà nel nuovo pannello comandi e rimuoverà questo placeholder; per ora bastano per non rompere il JS esistente che li referenzia.)

- [ ] **Step 4: Rimuovi i riferimenti DOM non più validi e aggiungi quelli nuovi**

Trova:
```js
  const distVal = $('distVal'), mapEmpty = $('mapEmpty'), mapArrow = $('mapArrow');
  const colMap = $('colMap'), resizeHandle = $('resizeHandle');
```

Sostituisci con:
```js
  const mapEmpty = $('mapEmpty'), mapArrow = $('mapArrow');
  const colMap = $('colMap');
  const slotLeftTop = $('slotLeftTop'), slotLeftBottom = $('slotLeftBottom'), slotRightTop = $('slotRightTop'), slotRightBottom = $('slotRightBottom');
  const cardLean = $('cardLean'), cardPitch = $('cardPitch'), cardGLat = $('cardGLat'), cardGLong = $('cardGLong');
```

- [ ] **Step 5: Rimuovi l'IIFE di ridimensionamento mappa e applica l'assegnazione di default delle card agli slot**

Trova:
```js
  const clamp = (v,lo,hi) => Math.max(lo, Math.min(hi, v));
  const root = document.documentElement;

  /* ---------- resizable map (drag handle) ---------- */
  (function initResize(){
    let saved = null;
    try { saved = localStorage.getItem('moto_map_pct'); } catch(e){}
    if (saved) root.style.setProperty('--map-pct', saved + '%');
    let dragging = false, startX = 0, startPct = parseFloat(saved || 60);
    const layoutEl = document.querySelector('.layout');
    function onDown(e){ dragging = true; startX = e.clientX; startPct = parseFloat(getComputedStyle(root).getPropertyValue('--map-pct')) || 60; resizeHandle.classList.add('dragging'); resizeHandle.setPointerCapture(e.pointerId); }
    function onMove(e){ if (!dragging) return; const dx = e.clientX - startX; const w = layoutEl.clientWidth || 1; let pct = clamp(startPct + (dx / w * 100), 32, 82); root.style.setProperty('--map-pct', pct.toFixed(1) + '%'); }
    function onUp(){ if (!dragging) return; dragging = false; resizeHandle.classList.remove('dragging'); const pct = getComputedStyle(root).getPropertyValue('--map-pct'); try { localStorage.setItem('moto_map_pct', parseFloat(pct)); } catch(e){} if (gmap) setTimeout(() => google.maps.event.trigger(gmap, 'resize'), 200); }
    resizeHandle.addEventListener('pointerdown', onDown);
    resizeHandle.addEventListener('pointermove', onMove);
    resizeHandle.addEventListener('pointerup', onUp);
    resizeHandle.addEventListener('pointercancel', onUp);
  })();
```

Sostituisci con:
```js
  const clamp = (v,lo,hi) => Math.max(lo, Math.min(hi, v));
  const root = document.documentElement;

  /* ---------- assegnazione card grandi agli slot (default; lo scambio arriva nel Task 6) ---------- */
  const CARD_METRICS = ['lean', 'pitch', 'gLat', 'gLong'];
  const CARD_EL = { lean: cardLean, pitch: cardPitch, gLat: cardGLat, gLong: cardGLong };
  const SLOT_EL = { leftTop: slotLeftTop, leftBottom: slotLeftBottom, rightTop: slotRightTop, rightBottom: slotRightBottom };
  const SLOT_KEYS = ['leftTop', 'leftBottom', 'rightTop', 'rightBottom'];
  let cardLayout = { leftTop: 'lean', leftBottom: 'gLat', rightTop: 'pitch', rightBottom: 'gLong' };
  function applyCardLayout(){
    SLOT_KEYS.forEach(slotKey => { SLOT_EL[slotKey].appendChild(CARD_EL[cardLayout[slotKey]]); });
  }
  applyCardLayout();
```

- [ ] **Step 6: Verifica manuale**

Ricarica `http://localhost:8000/`. Console: nessun errore. Il layout deve mostrare tre colonne: sinistra con due card (segnaposto "--°", vuote di dati veri finché non arriva il Task 2) più la mini-riga Sessione/Distanza, centro con la barra navigatore ("Nessun percorso impostato") sopra la mappa, destra con due card più la zona vuota del cockpit in basso. Il topbar deve leggere "TELAMETRIA" con "By TelaStampiamo" piccolo accanto. Non deve più esserci una maniglia di ridimensionamento tra mappa e colonne.

In console: `document.getElementById('cardLean').parentElement.id` deve restituire `"slotLeftTop"`; `document.getElementById('cardGLat').parentElement.id` deve restituire `"slotLeftBottom"`; `document.getElementById('cardPitch').parentElement.id` deve restituire `"slotRightTop"`; `document.getElementById('cardGLong').parentElement.id` deve restituire `"slotRightBottom"`.

- [ ] **Step 7: Commit**

```bash
git add index.html
git commit -m "Ristruttura il layout HUD in tre colonne (sx/centro/dx), rebrand TELAMETRIA"
```

---

### Task 2: Dati live per le 4 card — piega, beccheggio, G laterale, G longitudinale

**Files:**
- Modify: `index.html` JS (`updateLeanGauge`, `updatePitchGauge`, `updateGforceGauge`→sostituita da due nuove funzioni, `handleMotion`, `start()`, `resetMaxBtn` handler)
- Modify: `index.html` CSS (rimuove il vecchio meccanismo di peak-hold del G-force, non più usato)

**Interfaces:**
- Consumes: `cardLean`/`cardPitch`/`cardGLat`/`cardGLong` e i loro id interni (Task 1). `compensateAccelXY`, `computePitchFromGravity`, `handleMotion` (esistenti, invariati nella logica di calcolo).
- Produces: `maxGLat`, `maxGLong` (nuove variabili di stato, stesso pattern reset-su-Avvia di `maxLeanSx`/ecc.). Funzioni `updateLeanGauge(rollDeg)`/`updatePitchGauge(pitchDeg)` riscritte per il nuovo markup a barra (stessa firma). Nuove funzioni `updateGLatGauge(latG)`/`updateGLongGauge(fwdG)`. Rimosse: `makePeakHold`, `gPeak`, `gDisplay`, `G_DISPLAY_ALPHA` (il fading "ghost" è sostituito dalla riga TOP persistente — vedi spec).

- [ ] **Step 1: Rimuovi il CSS del vecchio marcatore G-force (ora sostituito dalla riga TOP nelle card)**

Trova:
```css
  .stat-bar-ticks { display:flex; justify-content:space-between; font-family: var(--mono); font-size:8px; color: var(--ink-dim); }

  .stat-maxrow { display:flex; justify-content:space-between; font-family: var(--mono); font-size:9px; color: var(--ink-dim); margin-top:5px; }
  .stat-maxrow b { color: var(--ink); font-weight:700; }
```

Nessuna modifica necessaria qui — questo step esiste solo per confermare che il Task 1 non ha lasciato regole CSS del vecchio `.gforce-marker`/`.gforce-val` (già rimosse nel Task 1 Step 1). Salta a Step 2.

- [ ] **Step 2: Riscrivi `updateLeanGauge` per il nuovo markup a barra**

Trova:
```js
  // rollDeg negativo = destra (DX), positivo = sinistra (SX) — verso confermato su strada
  // (era invertito: rollDeg>=0 veniva letto come DX finché non si è visto che la freccia
  // puntava dal lato sbagliato; la vecchia sagoma SVG applicava già rotate(${-rollDeg}...)
  // per lo stesso motivo, correzione persa quando è stata sostituita dal chevron).
  function updateLeanGauge(rollDeg){
    const abs = Math.abs(rollDeg);
    const isDx = rollDeg < 0;
    leanNumBig.textContent = abs.toFixed(0) + '°';
    leanChevron.textContent = isDx ? '▶' : '◀';
    leanSub.textContent = 'PIEGA · ' + (isDx ? 'DX' : 'SX');

    leanNumBig.classList.remove('warn','danger');
    leanChevron.classList.remove('warn','danger');
    if (abs > 40) { leanNumBig.classList.add('danger'); leanChevron.classList.add('danger'); }
    else if (abs > 25) { leanNumBig.classList.add('warn'); leanChevron.classList.add('warn'); }

    if (isDx) { if (abs > maxLeanDx) maxLeanDx = abs; }
    else { if (abs > maxLeanSx) maxLeanSx = abs; }
    leanMaxDxEl.textContent = maxLeanDx.toFixed(0) + '°';
    leanMaxSxEl.textContent = maxLeanSx.toFixed(0) + '°';
  }
```

Sostituisci con:
```js
  // Riempie una barra centrata sullo zero: valore positivo verso destra, negativo verso
  // sinistra dello 0 grafico, scala fissa ±maxScale. Riusata da tutte e 4 le card.
  function setBarFill(fillEl, value, maxScale){
    const pct = clamp(Math.abs(value) / maxScale * 50, 0, 50);
    if (value >= 0) { fillEl.style.left = '50%'; fillEl.style.width = pct + '%'; }
    else { fillEl.style.left = (50 - pct) + '%'; fillEl.style.width = pct + '%'; }
  }

  // rollDeg negativo = destra (DX), positivo = sinistra (SX) — verso confermato su strada
  // (era invertito: rollDeg>=0 veniva letto come DX finché non si è visto che la freccia
  // puntava dal lato sbagliato; la vecchia sagoma SVG applicava già rotate(${-rollDeg}...)
  // per lo stesso motivo, correzione persa quando è stata sostituita dal chevron).
  function updateLeanGauge(rollDeg){
    const abs = Math.abs(rollDeg);
    const isDx = rollDeg < 0;
    leanNumBig.textContent = abs.toFixed(0) + '°';
    leanSub.textContent = isDx ? 'DESTRA' : 'SINISTRA';
    // barra: positivo = destra (a specchio rispetto al segno di rollDeg, che è negativo per DX)
    setBarFill(leanBarFill, isDx ? abs : -abs, 60);

    leanNumBig.classList.remove('warn','danger');
    leanSub.classList.remove('warn','danger');
    if (abs > 40) { leanNumBig.classList.add('danger'); leanSub.classList.add('danger'); }
    else if (abs > 25) { leanNumBig.classList.add('warn'); leanSub.classList.add('warn'); }

    if (isDx) { if (abs > maxLeanDx) maxLeanDx = abs; }
    else { if (abs > maxLeanSx) maxLeanSx = abs; }
    leanMaxDxEl.textContent = maxLeanDx.toFixed(0) + '°';
    leanMaxSxEl.textContent = maxLeanSx.toFixed(0) + '°';
  }
```

- [ ] **Step 3: Riscrivi `updatePitchGauge` per il nuovo markup a barra**

Trova:
```js
  function updatePitchGauge(pitchDeg){
    const abs = Math.abs(pitchDeg);
    pitchNumBig.textContent = abs.toFixed(0) + '°';
    pitchChevron.textContent = pitchDeg >= 0 ? '▲' : '▼';
    pitchSub.textContent = 'BECCH. · ' + (pitchDeg >= 0 ? 'SU' : 'GIÙ');

    if (pitchDeg >= 0) { if (pitchDeg > maxPitchUp) maxPitchUp = pitchDeg; }
    else { if (-pitchDeg > maxPitchDown) maxPitchDown = -pitchDeg; }
    pitchMaxUpEl.textContent = maxPitchUp.toFixed(0) + '°';
    pitchMaxDownEl.textContent = maxPitchDown.toFixed(0) + '°';
  }
```

Sostituisci con:
```js
  function updatePitchGauge(pitchDeg){
    const abs = Math.abs(pitchDeg);
    pitchNumBig.textContent = abs.toFixed(0) + '°';
    pitchSub.textContent = pitchDeg >= 0 ? 'SU' : 'GIÙ';
    setBarFill(pitchBarFill, pitchDeg, 45);

    if (pitchDeg >= 0) { if (pitchDeg > maxPitchUp) maxPitchUp = pitchDeg; }
    else { if (-pitchDeg > maxPitchDown) maxPitchDown = -pitchDeg; }
    pitchMaxUpEl.textContent = maxPitchUp.toFixed(0) + '°';
    pitchMaxDownEl.textContent = maxPitchDown.toFixed(0) + '°';
  }
```

- [ ] **Step 4: Aggiungi i riferimenti DOM per le nuove card e rimuovi quelli del vecchio G-force verticale**

Trova:
```js
  const leanChevron = $('leanChevron'), leanNumBig = $('leanNumBig'), leanSub = $('leanSub');
  const leanMaxSxEl = $('leanMaxSx'), leanMaxDxEl = $('leanMaxDx');
  const pitchChevron = $('pitchChevron'), pitchNumBig = $('pitchNumBig'), pitchSub = $('pitchSub');
  const pitchMaxUpEl = $('pitchMaxUp'), pitchMaxDownEl = $('pitchMaxDown');
  const speedVal = $('speedVal');
  const gforceVal = $('gforceVal'), gGhost = $('gGhost');
```

Sostituisci con:
```js
  const leanNumBig = $('leanNumBig'), leanSub = $('leanSub'), leanBarFill = $('leanBarFill');
  const leanMaxSxEl = $('leanMaxSx'), leanMaxDxEl = $('leanMaxDx');
  const pitchNumBig = $('pitchNumBig'), pitchSub = $('pitchSub'), pitchBarFill = $('pitchBarFill');
  const pitchMaxUpEl = $('pitchMaxUp'), pitchMaxDownEl = $('pitchMaxDown');
  const gLatNumBig = $('gLatNumBig'), gLatBarFill = $('gLatBarFill'), gLatTopEl = $('gLatTop');
  const gLongNumBig = $('gLongNumBig'), gLongBarFill = $('gLongBarFill'), gLongTopEl = $('gLongTop');
```

(`speedVal` viene rimosso qui perché il Task 3 lo re-introduce come parte del sistema mini-tile, con un id diverso — non serve più come const fisso a questo punto del piano.)

- [ ] **Step 5: Sostituisci lo stato del vecchio G-force con `maxGLat`/`maxGLong` e le nuove funzioni gauge**

Trova:
```js
  /* generic short-lived peak-hold-with-decay ("ghost"), used only for G-force */
  function makePeakHold(holdMs, fadeMs){
    let peak = 0, sign = 1, peakTime = performance.now();
    return function(value, now){
      const abs = Math.abs(value);
      if (abs >= peak) { peak = abs; sign = value < 0 ? -1 : 1; peakTime = now; }
      const age = now - peakTime;
      let opacity;
      if (age < holdMs) opacity = 1;
      else if (age < holdMs + fadeMs) opacity = 1 - (age - holdMs) / fadeMs;
      else { opacity = 0; peak = abs; peakTime = now; sign = value < 0 ? -1 : 1; }
      return { peak, sign, opacity };
    };
  }
  const gPeak = makePeakHold(1400, 1000);
  // Valore G smussato (EMA) solo per la barra/testo — separato dal fwdG grezzo usato per il
  // punteggio, così la lettura visiva è fluida senza cambiare la sensibilità del punteggio guida.
  let gDisplay = 0;
  const G_DISPLAY_ALPHA = 0.12;

  let recording = false, sensorsActive = false;
  let currentLean = 0, currentPitch = 0;
  let lastRawRoll = 0, lastRawPitch = 0;
  let leanOffset = 0, pitchOffset = 0;
  let maxLeanSx = 0, maxLeanDx = 0, maxPitchUp = 0, maxPitchDown = 0;
```

Sostituisci con:
```js
  // Valori G smussati (EMA) solo per barra/testo — separati dai grezzi fwdG/latG usati per il
  // punteggio, così la lettura visiva è fluida senza cambiare la sensibilità del punteggio guida.
  let gLongDisplay = 0, gLatDisplay = 0;
  const G_DISPLAY_ALPHA = 0.12;

  let recording = false, sensorsActive = false;
  let currentLean = 0, currentPitch = 0;
  let lastRawRoll = 0, lastRawPitch = 0;
  let leanOffset = 0, pitchOffset = 0;
  let maxLeanSx = 0, maxLeanDx = 0, maxPitchUp = 0, maxPitchDown = 0, maxGLat = 0, maxGLong = 0;
```

- [ ] **Step 6: Sostituisci `updateGforceGauge` con `updateGLatGauge`/`updateGLongGauge`**

Trova:
```js
  function updateGforceGauge(gSmooth, now){
    gforceVal.textContent = (gSmooth >= 0 ? '+' : '') + gSmooth.toFixed(2) + 'g';

    const gp = gPeak(gSmooth, now);
    const pct = clamp(gp.peak / 1.0 * 50, 0, 50);
    gGhost.style.top = (gp.sign >= 0 ? (50 - pct) : (50 + pct)) + '%';
    gGhost.style.opacity = gp.opacity;
  }
```

Sostituisci con:
```js
  function updateGLatGauge(gSmooth){
    gLatNumBig.textContent = (gSmooth >= 0 ? '+' : '') + gSmooth.toFixed(2) + 'g';
    setBarFill(gLatBarFill, gSmooth, 1.5);
    if (Math.abs(gSmooth) > maxGLat) { maxGLat = Math.abs(gSmooth); gLatTopEl.textContent = maxGLat.toFixed(2) + 'g'; }
  }

  function updateGLongGauge(gSmooth){
    gLongNumBig.textContent = (gSmooth >= 0 ? '+' : '') + gSmooth.toFixed(2) + 'g';
    setBarFill(gLongBarFill, gSmooth, 1.0);
    if (Math.abs(gSmooth) > maxGLong) { maxGLong = Math.abs(gSmooth); gLongTopEl.textContent = maxGLong.toFixed(2) + 'g'; }
  }
```

- [ ] **Step 7: Aggiorna `handleMotion` per alimentare entrambe le nuove card G**

Trova:
```js
    const fwdG = linear.y / 9.81, latG = linear.x / 9.81, vertG = linear.z / 9.81;
    gDisplay += (fwdG - gDisplay) * G_DISPLAY_ALPHA;
    updateGforceGauge(gDisplay, performance.now());
```

Sostituisci con:
```js
    const fwdG = linear.y / 9.81, latG = linear.x / 9.81, vertG = linear.z / 9.81;
    gLongDisplay += (fwdG - gLongDisplay) * G_DISPLAY_ALPHA;
    gLatDisplay += (latG - gLatDisplay) * G_DISPLAY_ALPHA;
    updateGLongGauge(gLongDisplay);
    updateGLatGauge(gLatDisplay);
```

- [ ] **Step 8: Reset di `maxGLat`/`maxGLong` in `start()` e in "Reset max"**

Trova:
```js
    maxLeanSx = 0; maxLeanDx = 0; maxPitchUp = 0; maxPitchDown = 0;
    gDisplay = 0;
    vertBuf = [];
```

Sostituisci con:
```js
    maxLeanSx = 0; maxLeanDx = 0; maxPitchUp = 0; maxPitchDown = 0; maxGLat = 0; maxGLong = 0;
    gLongDisplay = 0; gLatDisplay = 0;
    gLatTopEl.textContent = '0.00g'; gLongTopEl.textContent = '0.00g';
    vertBuf = [];
```

Trova:
```js
  resetMaxBtn.addEventListener('click', () => {
    if (!confirm('Azzerare i valori massimi di piega e beccheggio raggiunti finora?')) return;
    maxLeanSx = 0; maxLeanDx = 0; maxPitchUp = 0; maxPitchDown = 0;
    leanMaxSxEl.textContent = '--°'; leanMaxDxEl.textContent = '--°';
    pitchMaxUpEl.textContent = '--°'; pitchMaxDownEl.textContent = '--°';
  });
```

Sostituisci con:
```js
  resetMaxBtn.addEventListener('click', () => {
    if (!confirm('Azzerare i valori massimi di piega, beccheggio e G raggiunti finora?')) return;
    maxLeanSx = 0; maxLeanDx = 0; maxPitchUp = 0; maxPitchDown = 0; maxGLat = 0; maxGLong = 0;
    leanMaxSxEl.textContent = '--°'; leanMaxDxEl.textContent = '--°';
    pitchMaxUpEl.textContent = '--°'; pitchMaxDownEl.textContent = '--°';
    gLatTopEl.textContent = '0.00g'; gLongTopEl.textContent = '0.00g';
  });
```

- [ ] **Step 9: Verifica manuale**

Ricarica la pagina. Console: nessun errore (in particolare nessun riferimento a `leanChevron`/`pitchChevron`/`gforceVal`/`gGhost`/`gPeak`/`gDisplay` rimasto orfano — cercali con `grep -n "leanChevron\|pitchChevron\|gforceVal\|gGhost\b\|gPeak\|gDisplay\b" index.html`, non devono comparire risultati).

Simula in console:
```js
window.dispatchEvent(new DeviceOrientationEvent('deviceorientation', {beta: 5, gamma: -30, absolute: false}));
```
Atteso: `document.getElementById('leanNumBig').textContent === '30°'`, `document.getElementById('leanSub').textContent === 'DESTRA'` (gamma negativo → rollDeg negativo → DX), `document.getElementById('leanBarFill').style.left` deve essere `'50%'` e `.width` circa `'25%'` (30/60*50).

Per la G laterale, dopo aver lasciato assestare il filtro di gravità (come nei piani precedenti), un campione con accelerazione laterale deve far salire sia `gLatNumBig` che `gLatTop` (il TOP non deve mai scendere anche se il valore corrente poi cala).

- [ ] **Step 10: Commit**

```bash
git add index.html
git commit -m "Ridisegna piega/beccheggio a barra e aggiunge le card G laterale/longitudinale"
```

---

### Task 3: Timer di sessione + mini-riga Sessione/Distanza

**Files:**
- Modify: `index.html` JS (nuovo timer di sessione, `handlePosition`, `start()`, `stop()`, riferimenti DOM)

**Interfaces:**
- Consumes: `miniVal1`/`miniVal2`/`miniLabel1`/`miniLabel2` (Task 1). `recording`, `totalDistanceM` (esistenti).
- Produces: `sessionStartTime`, `sessionIntervalId`, funzione `formatSessionTime(ms)`, variabili `lastKmh`, `lastScore` (nuove, servono anche al Task 7 per il sistema di scelta mini-tile). Per ora la mini-riga mostra sempre e solo Sessione/Distanza (il Task 7 aggiunge la possibilità di scegliere altro).

- [ ] **Step 1: Aggiungi i riferimenti DOM per la mini-riga**

Trova:
```js
  const gLatNumBig = $('gLatNumBig'), gLatBarFill = $('gLatBarFill'), gLatTopEl = $('gLatTop');
  const gLongNumBig = $('gLongNumBig'), gLongBarFill = $('gLongBarFill'), gLongTopEl = $('gLongTop');
```

Sostituisci con:
```js
  const gLatNumBig = $('gLatNumBig'), gLatBarFill = $('gLatBarFill'), gLatTopEl = $('gLatTop');
  const gLongNumBig = $('gLongNumBig'), gLongBarFill = $('gLongBarFill'), gLongTopEl = $('gLongTop');
  const miniVal1 = $('miniVal1'), miniVal2 = $('miniVal2');
```

- [ ] **Step 2: Aggiungi lo stato del timer di sessione e `lastKmh`/`lastScore`, prima di `handlePosition`**

Trova:
```js
  function handlePosition(pos){
```

Sostituisci con:
```js
  let sessionStartTime = null, sessionIntervalId = null;
  let lastKmh = null, lastScore = 0;

  function formatSessionTime(ms){
    const totalS = Math.floor(ms / 1000);
    const mm = Math.floor(totalS / 60).toString().padStart(2, '0');
    const ss = (totalS % 60).toString().padStart(2, '0');
    return mm + ':' + ss;
  }
  function refreshMiniTiles(){
    miniVal1.textContent = miniTileValueText('slot1');
    miniVal2.textContent = miniTileValueText('slot2');
  }
  // Task 3: la mini-riga mostra sempre Sessione (posizione 1) e Distanza (posizione 2).
  // Il Task 7 sostituisce questa funzione con una versione che legge la scelta dell'utente.
  function miniTileValueText(slotKey){
    if (slotKey === 'slot1') return sessionStartTime !== null ? formatSessionTime(Date.now() - sessionStartTime) : '00:00';
    return (totalDistanceM / 1000).toFixed(1) + 'km';
  }

  function handlePosition(pos){
```

- [ ] **Step 3: Aggiorna `handlePosition` per tracciare `lastKmh` e rinfrescare le mini-tile**

Trova:
```js
  function handlePosition(pos){
    const kmh = pos.coords.speed !== null && pos.coords.speed >= 0 ? (pos.coords.speed * 3.6) : null;
    speedVal.innerHTML = (kmh !== null ? kmh.toFixed(0) : '--') + '<span class="mini-unit">km/h</span>';
```

Sostituisci con:
```js
  function handlePosition(pos){
    const kmh = pos.coords.speed !== null && pos.coords.speed >= 0 ? (pos.coords.speed * 3.6) : null;
    lastKmh = kmh;
```

- [ ] **Step 4: Aggiorna la mini-riga ad ogni fix GPS (distanza) e chiama `refreshMiniTiles()`**

Trova:
```js
    lastLat = pos.coords.latitude; lastLon = pos.coords.longitude;
    distVal.textContent = (totalDistanceM / 1000).toFixed(1);

    updateMap(lastLat, lastLon, kmh, heading);
    updateNavProgress(lastLat, lastLon);
```

Sostituisci con:
```js
    lastLat = pos.coords.latitude; lastLon = pos.coords.longitude;
    refreshMiniTiles();

    updateMap(lastLat, lastLon, kmh, heading);
    updateNavProgress(lastLat, lastLon);
```

- [ ] **Step 5: Aggiorna `renderScore` per tracciare `lastScore` e rinfrescare le mini-tile**

Trova:
```js
  function renderScore(overall){
    scoreNum.textContent = overall.toFixed(0);
  }
```

Sostituisci con:
```js
  function renderScore(overall){
    lastScore = overall;
    refreshMiniTiles();
  }
```

- [ ] **Step 6: Avvia il timer di sessione in `start()`**

Trova:
```js
    recording = true;
    logData = [];
    maxLeanSx = 0; maxLeanDx = 0; maxPitchUp = 0; maxPitchDown = 0; maxGLat = 0; maxGLong = 0;
    gLongDisplay = 0; gLatDisplay = 0;
    gLatTopEl.textContent = '0.00g'; gLongTopEl.textContent = '0.00g';
    vertBuf = [];
    subAccel = 100; subLean = 100; subComfort = 100;
    totalDistanceM = 0; lastLat = null; lastLon = null;
    distVal.textContent = '0.0';
    setStatus(true, 'REGISTRA');
```

Sostituisci con:
```js
    recording = true;
    logData = [];
    maxLeanSx = 0; maxLeanDx = 0; maxPitchUp = 0; maxPitchDown = 0; maxGLat = 0; maxGLong = 0;
    gLongDisplay = 0; gLatDisplay = 0;
    gLatTopEl.textContent = '0.00g'; gLongTopEl.textContent = '0.00g';
    vertBuf = [];
    subAccel = 100; subLean = 100; subComfort = 100;
    totalDistanceM = 0; lastLat = null; lastLon = null;
    sessionStartTime = Date.now();
    if (sessionIntervalId !== null) clearInterval(sessionIntervalId);
    sessionIntervalId = setInterval(refreshMiniTiles, 1000);
    refreshMiniTiles();
    setStatus(true, 'REGISTRA');
```

- [ ] **Step 7: Ferma il timer di sessione in `stop()` (il valore resta visibile, congelato)**

Trova:
```js
  function stop(){
    recording = false;
    stopGpsIfIdle();
    setStatus(false, 'FERMO');
```

Sostituisci con:
```js
  function stop(){
    recording = false;
    if (sessionIntervalId !== null) { clearInterval(sessionIntervalId); sessionIntervalId = null; }
    stopGpsIfIdle();
    setStatus(false, 'FERMO');
```

- [ ] **Step 8: Verifica manuale**

Ricarica la pagina. Console: `document.getElementById('miniVal1').textContent` deve leggere `'00:00'` inizialmente, `document.getElementById('miniVal2').textContent` deve leggere `'0.0km'`. Simulando l'avvio (`start()` richiede permessi sensori reali per completare, ma puoi comunque osservare `sessionStartTime`/`sessionIntervalId` diventare non-null se hai un browser reale disponibile). Hand-trace: `formatSessionTime(65000)` deve restituire `'01:05'`.

- [ ] **Step 9: Commit**

```bash
git add index.html
git commit -m "Aggiunge timer di sessione e collega la mini-riga Sessione/Distanza ai dati reali"
```

---

### Task 4: Barra navigatore centrale (consolida gli overlay sulla mappa)

**Files:**
- Modify: `index.html` JS (`updateNavPanel`, `updateRouteInfo`, `startNavigation`, `stopNavigation`, riferimenti DOM)

**Interfaces:**
- Consumes: `navTopbarChevron`/`navTopbarText`/`navTopbarDist`/`navTopbarEta`/`navTopbar` (Task 1). `navSteps`/`navStepIndex`/`chevronForManeuver` (esistenti, invariati).
- Produces: nessuna nuova interfaccia per task successivi — questo task è terminale per la parte navigazione.

- [ ] **Step 1: Sostituisci i riferimenti DOM del vecchio pannello/chip con quelli della barra unica**

Trova:
```js
  const navPanelEl = $('navPanelEl'), navPanelChevron = $('navPanelChevron'), navPanelText = $('navPanelText'), navPanelDist = $('navPanelDist');
  const routeInfoEl = $('routeInfoEl');
```

Sostituisci con:
```js
  const navTopbar = $('navTopbar'), navTopbarChevron = $('navTopbarChevron'), navTopbarText = $('navTopbarText'), navTopbarDist = $('navTopbarDist'), navTopbarEta = $('navTopbarEta');
```

- [ ] **Step 2: Aggiorna `startNavigation`/`stopNavigation` per la nuova barra**

Trova:
```js
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
    stopGpsIfIdle();
  }
```

Sostituisci con:
```js
    navStepIndex = 0;
    navAnnounced = false;
    navActive = true;
    navTopbar.classList.remove('idle');
    updateNavPanel();
    updateRouteInfo();
  }

  function stopNavigation(){
    navActive = false;
    navSteps = [];
    navStepIndex = 0;
    navTopbar.classList.add('idle');
    navTopbarText.textContent = 'Nessun percorso impostato';
    navTopbarChevron.textContent = '–';
    navTopbarDist.textContent = '';
    navTopbarEta.textContent = '';
    stopGpsIfIdle();
  }
```

- [ ] **Step 3: Aggiorna `updateNavPanel`/`updateRouteInfo` per scrivere nella barra unica**

Trova:
```js
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
```

Sostituisci con:
```js
  function updateNavPanel(){
    if (!navActive || navStepIndex >= navSteps.length) return;
    const step = navSteps[navStepIndex];
    navTopbarChevron.textContent = chevronForManeuver(step.maneuver);
    navTopbarText.innerHTML = '<b>' + step.instructionText + '</b>';
  }

  function updateRouteInfo(){
    if (!navActive) return;
    let remM = 0, remS = 0;
    for (let i = navStepIndex; i < navSteps.length; i++) { remM += navSteps[i].distanceM; remS += navSteps[i].durationS; }
    navTopbarDist.textContent = (remM / 1000).toFixed(1) + ' km';
    const etaDate = new Date(Date.now() + remS * 1000);
    navTopbarEta.textContent = 'ETA ' + etaDate.getHours().toString().padStart(2,'0') + ':' + etaDate.getMinutes().toString().padStart(2,'0');
  }
```

- [ ] **Step 4: Aggiorna `updateNavProgress` per mostrare la distanza alla manovra nella barra**

Trova:
```js
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
```

Sostituisci con:
```js
  function updateNavProgress(lat, lon){
    if (!navActive || navStepIndex >= navSteps.length) return;
    const step = navSteps[navStepIndex];
    const dist = distanceMeters(lat, lon, step.endLat, step.endLon);
    const distText = dist >= 1000 ? (dist / 1000).toFixed(1) + ' km' : Math.round(dist) + ' m';
    navTopbarText.innerHTML = 'Tra <b>' + distText + '</b> · ' + step.instructionText;

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
        navTopbarText.textContent = 'Arrivato a destinazione';
        navTopbarDist.textContent = ''; navTopbarEta.textContent = '';
        updateRouteInfo();
        return;
      }
      updateNavPanel();
    }
    updateRouteInfo();
  }
```

(Nota: `updateNavProgress` ora scrive direttamente `navTopbarText` con distanza+istruzione combinate — più informativo della vecchia coppia separata pannello/chip. `updateNavPanel()` resta comunque usata al cambio di step, per aggiornare subito chevron+testo prima che arrivi il prossimo fix GPS con la distanza aggiornata.)

- [ ] **Step 5: Verifica manuale**

Ricarica la pagina. La barra navigatore in alto al centro deve mostrare "Nessun percorso impostato" all'avvio. Con un percorso finto (stesso approccio hand-trace del piano di navigazione precedente — un oggetto `DirectionsResult` costruito a mano passato a `startNavigation()`), verifica che `navTopbarChevron`/`navTopbarText` si aggiornino e che `navTopbar` perda la classe `idle`. Chiamando `stopNavigation()`, la barra deve tornare a "Nessun percorso impostato" con classe `idle` ripristinata.

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "Consolida gli overlay di navigazione in un'unica barra centrale sopra la mappa"
```

---

### Task 5: Pannello comandi unico

**Files:**
- Modify: `index.html` HTML (rimuove il placeholder nascosto del Task 1, aggiunge il nuovo pannello; sposta il toggle Voce dal popover Navigatore)
- Modify: `index.html` CSS (linguetta fissa `.control-handle`)
- Modify: `index.html` JS (apertura/chiusura pannello, rimuove il vecchio popover Impostazioni)

**Interfaces:**
- Consumes: `mainBtn`/`calibBtn`/`resetMaxBtn`/`exportBtn`/`logInfo`/`themeToggle`/`voiceToggle` (esistenti, stessa logica invariata — solo la posizione nel DOM cambia).
- Produces: `#controlPanel`/`#controlBackdrop`/`#controlHandle`, toggle `#editModeToggle` (usato dal Task 6, ancora senza effetto in questo task — aggiunge solo la classe `edit-mode` su `.app`, che il CSS del Task 1 già interpreta per mostrare gli `⇄`).

- [ ] **Step 1: Aggiungi la linguetta fissa del pannello comandi al CSS**

Trova:
```css
  .cockpit-void { flex:0 0 80px; border-radius:9px; pointer-events:none; }
```

Sostituisci con:
```css
  .cockpit-void { flex:0 0 80px; border-radius:9px; pointer-events:none; }

  .control-handle {
    position:fixed; bottom:0; left:50%; transform:translateX(-50%); z-index:899;
    width:64px; height:22px; background: var(--bg2); border:1px solid var(--panel-edge);
    border-bottom:none; border-radius:10px 10px 0 0; display:flex; align-items:center; justify-content:center;
    cursor:pointer;
  }
  .control-handle .grip { width:28px; height:4px; border-radius:2px; background: var(--ink-dim); }
```

- [ ] **Step 2: Sostituisci il placeholder nascosto del Task 1 e il vecchio popover Impostazioni col nuovo pannello comandi**

Trova:
```html
    <div class="hud-bottom-placeholder" style="display:none">
      <button class="btn-big start" id="mainBtn">Avvia</button>
      <button class="btn-big calib" id="calibBtn">Calibra</button>
      <button class="btn-mini" id="resetMaxBtn">↺ Reset max</button>
      <button class="btn-mini" id="exportBtn" disabled>⭳ CSV</button>
      <div class="log-info" id="logInfo"></div>
    </div>
```

Sostituisci con:
```html
    <div class="control-handle" id="controlHandle"><div class="grip"></div></div>
    <div class="popover-backdrop" id="controlBackdrop"></div>
    <div class="popover-panel" id="controlPanel">
      <div class="popover-title">COMANDI</div>
      <button class="btn-big start" id="mainBtn">Avvia</button>
      <button class="btn-big calib" id="calibBtn">Calibra</button>
      <div class="mini-actions-row" style="margin-top:7px">
        <button class="btn-mini" id="resetMaxBtn">↺ Reset max</button>
        <button class="btn-mini" id="exportBtn" disabled>⭳ CSV</button>
      </div>
      <div class="log-info" id="logInfo"></div>
      <div class="settings-row"><span>Tema</span><button class="settings-toggle" id="themeToggle">Notturno</button></div>
      <div class="settings-row"><span>Voce navigatore</span><button class="settings-toggle" id="voiceToggle">Attiva</button></div>
      <div class="settings-row"><span>Modalità modifica</span><button class="settings-toggle" id="editModeToggle">Disattiva</button></div>
      <div class="settings-row"><span>Chiudi</span><button class="settings-toggle" id="controlClose">OK</button></div>
    </div>
```

- [ ] **Step 3: Rimuovi il vecchio popover Impostazioni e la riga Voce dal popover Navigatore**

Trova:
```html
  <div class="popover-backdrop" id="settingsBackdrop"></div>
  <div class="popover-panel" id="settingsPanel">
    <div class="popover-title">IMPOSTAZIONI</div>
    <div class="settings-row"><span>Tema</span><button class="settings-toggle" id="themeToggle">Notturno</button></div>
    <div class="settings-row"><span>Chiudi</span><button class="settings-toggle" id="settingsClose">OK</button></div>
  </div>

  <div class="popover-backdrop" id="navBackdrop"></div>
  <div class="popover-panel" id="navPanel">
    <div class="popover-title">NAVIGATORE</div>
    <div id="waypointList"></div>
    <button class="btn-mini" id="addWaypointBtn" type="button">+ Aggiungi tappa</button>
    <input type="text" id="destInput" class="settings-input" placeholder="Indirizzo o luogo di destinazione..." />
    <div class="settings-row"><span>Voce</span><button class="settings-toggle" id="voiceToggle">Attiva</button></div>
    <div class="mini-actions-row">
```

Sostituisci con:
```html
  <div class="popover-backdrop" id="navBackdrop"></div>
  <div class="popover-panel" id="navPanel">
    <div class="popover-title">NAVIGATORE</div>
    <div id="waypointList"></div>
    <button class="btn-mini" id="addWaypointBtn" type="button">+ Aggiungi tappa</button>
    <input type="text" id="destInput" class="settings-input" placeholder="Indirizzo o luogo di destinazione..." />
    <div class="mini-actions-row">
```

- [ ] **Step 4: Aggiorna i riferimenti DOM e la logica di apertura/chiusura del pannello comandi**

Trova:
```js
  const settingsBtn = $('settingsBtn'), settingsPanel = $('settingsPanel'), settingsBackdrop = $('settingsBackdrop'), settingsClose = $('settingsClose');
  const themeToggle = $('themeToggle');
```

Sostituisci con:
```js
  const controlHandle = $('controlHandle'), controlPanel = $('controlPanel'), controlBackdrop = $('controlBackdrop'), controlClose = $('controlClose');
  const themeToggle = $('themeToggle'), editModeToggle = $('editModeToggle');
  const appEl = document.querySelector('.app');
```

Trova:
```js
  /* ---------- settings popover ---------- */
  settingsBtn.addEventListener('click', () => { settingsPanel.classList.add('open'); settingsBackdrop.classList.add('open'); });
  settingsClose.addEventListener('click', closeSettings);
  settingsBackdrop.addEventListener('click', closeSettings);
  function closeSettings(){ settingsPanel.classList.remove('open'); settingsBackdrop.classList.remove('open'); }
```

Sostituisci con:
```js
  /* ---------- pannello comandi ---------- */
  controlHandle.addEventListener('click', () => { controlPanel.classList.add('open'); controlBackdrop.classList.add('open'); });
  controlClose.addEventListener('click', closeControlPanel);
  controlBackdrop.addEventListener('click', closeControlPanel);
  function closeControlPanel(){ controlPanel.classList.remove('open'); controlBackdrop.classList.remove('open'); }

  let editMode = false;
  function refreshEditModeLabel(){ editModeToggle.textContent = editMode ? 'Attiva' : 'Disattiva'; }
  editModeToggle.addEventListener('click', () => {
    editMode = !editMode;
    appEl.classList.toggle('edit-mode', editMode);
    refreshEditModeLabel();
  });
  refreshEditModeLabel();
```

- [ ] **Step 5: Verifica manuale**

Ricarica la pagina. Console: nessun errore, in particolare nessun riferimento a `settingsBtn`/`settingsPanel`/`settingsBackdrop`/`settingsClose` rimasto (`grep -n "settingsBtn\|settingsPanel\|settingsBackdrop\|settingsClose" index.html` non deve dare risultati). Tocca la linguetta in basso al centro: deve aprirsi il pannello con Avvia/Calibra/Reset max/CSV/Tema/Voce navigatore/Modalità modifica/Chiudi. Il popover Navigatore (icona 🧭) non deve più avere la riga Voce (si trova solo nel pannello comandi ora). Attivando "Modalità modifica" dal pannello, l'elemento `<div class="app">` deve guadagnare la classe `edit-mode` (verificabile con `document.querySelector('.app').className`) — gli `⇄` sulle card (CSS del Task 1) devono diventare visibili.

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "Consolida i controlli in un pannello comandi unico apribile da una linguetta fissa"
```

---

### Task 6: Scambio delle 4 card grandi ("modalità modifica")

**Files:**
- Modify: `index.html` HTML (aggiunge il popover "picker" condiviso)
- Modify: `index.html` JS (logica di scambio, persistenza layout)

**Interfaces:**
- Consumes: `CARD_METRICS`/`CARD_EL`/`SLOT_EL`/`SLOT_KEYS`/`cardLayout`/`applyCardLayout` (Task 1). Classe `edit-mode` su `.app` e i pulsanti `.stat-swap-btn[data-metric]` dentro ciascuna card (Task 1 HTML).
- Produces: `openPicker(title, options, onPick)` (funzione generica, riusata dal Task 7 per il picker delle mini-tile), persistenza `localStorage` chiave `moto_card_layout`.

- [ ] **Step 1: Aggiungi il popover "picker" condiviso, subito dopo il popover Navigatore**

Trova:
```html
    <div class="log-info" id="navInfo"></div>
  </div>

<script>
```

Sostituisci con:
```html
    <div class="log-info" id="navInfo"></div>
  </div>

  <div class="popover-backdrop" id="pickerBackdrop"></div>
  <div class="popover-panel" id="pickerPanel">
    <div class="popover-title" id="pickerTitle">SCEGLI</div>
    <div id="pickerList" style="display:flex; flex-direction:column; gap:7px;"></div>
    <div class="settings-row"><span>Annulla</span><button class="settings-toggle" id="pickerClose">OK</button></div>
  </div>

<script>
```

- [ ] **Step 2: Aggiungi i riferimenti DOM e la funzione generica `openPicker`/`closePicker`**

Trova:
```js
  const clamp = (v,lo,hi) => Math.max(lo, Math.min(hi, v));
  const root = document.documentElement;
```

Sostituisci con:
```js
  const clamp = (v,lo,hi) => Math.max(lo, Math.min(hi, v));
  const root = document.documentElement;

  /* ---------- picker generico (riusato per scambio card grandi e scelta mini-tile) ---------- */
  const pickerBackdrop = $('pickerBackdrop'), pickerPanel = $('pickerPanel'), pickerTitle = $('pickerTitle'), pickerList = $('pickerList'), pickerClose = $('pickerClose');
  function openPicker(title, options, onPick){
    pickerTitle.textContent = title;
    pickerList.innerHTML = '';
    options.forEach(opt => {
      const btn = document.createElement('button');
      btn.className = 'btn-mini';
      btn.style.width = '100%';
      btn.textContent = opt.label;
      btn.addEventListener('click', () => { onPick(opt.key); closePicker(); });
      pickerList.appendChild(btn);
    });
    pickerPanel.classList.add('open');
    pickerBackdrop.classList.add('open');
  }
  function closePicker(){ pickerPanel.classList.remove('open'); pickerBackdrop.classList.remove('open'); }
  pickerClose.addEventListener('click', closePicker);
  pickerBackdrop.addEventListener('click', closePicker);
```

- [ ] **Step 3: Aggiungi persistenza e logica di scambio, subito dopo `applyCardLayout()`**

Trova:
```js
  function applyCardLayout(){
    SLOT_KEYS.forEach(slotKey => { SLOT_EL[slotKey].appendChild(CARD_EL[cardLayout[slotKey]]); });
  }
  applyCardLayout();
```

Sostituisci con:
```js
  function applyCardLayout(){
    SLOT_KEYS.forEach(slotKey => { SLOT_EL[slotKey].appendChild(CARD_EL[cardLayout[slotKey]]); });
  }
  function saveCardLayout(){
    try { localStorage.setItem('moto_card_layout', JSON.stringify(cardLayout)); } catch(e){}
  }
  function loadCardLayout(){
    let saved = null;
    try { saved = JSON.parse(localStorage.getItem('moto_card_layout')); } catch(e){}
    // valida: deve avere esattamente le 4 chiavi slot, ognuna con uno dei 4 metric, tutti distinti
    if (saved && SLOT_KEYS.every(k => CARD_METRICS.includes(saved[k]))
        && new Set(SLOT_KEYS.map(k => saved[k])).size === 4) {
      cardLayout = saved;
    }
  }
  function findSlotForMetric(metric){ return SLOT_KEYS.find(k => cardLayout[k] === metric); }
  function swapCardInto(slotKey, newMetric){
    const oldMetric = cardLayout[slotKey];
    if (oldMetric === newMetric) return;
    const otherSlotKey = findSlotForMetric(newMetric);
    cardLayout[slotKey] = newMetric;
    cardLayout[otherSlotKey] = oldMetric;
    applyCardLayout();
    saveCardLayout();
  }
  const CARD_LABELS = { lean: 'Piega', pitch: 'Beccheggio', gLat: 'G Laterale', gLong: 'G Longitudinale' };
  document.querySelectorAll('.stat-card > .stat-swap-btn[data-metric]').forEach(btn => {
    const metric = btn.getAttribute('data-metric');
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const options = CARD_METRICS.filter(m => m !== metric).map(m => ({ key: m, label: CARD_LABELS[m] }));
      openPicker('Scambia "' + CARD_LABELS[metric] + '" con', options, (chosen) => {
        swapCardInto(findSlotForMetric(metric), chosen);
      });
    });
  });
  loadCardLayout();
  applyCardLayout();
```

(`applyCardLayout()` viene chiamata due volte in sequenza qui — una volta con il layout di default, subito dopo `loadCardLayout()` con l'eventuale layout salvato: è voluto, la seconda chiamata è quella che conta se c'era un salvataggio, la prima esisteva già dal Task 1 e resta innocua.)

- [ ] **Step 4: Verifica manuale**

Ricarica la pagina. Attiva "Modalità modifica" dal pannello comandi. Tocca ⇄ sulla card in alto a sinistra (Piega di default): deve aprirsi un picker con "Beccheggio", "G Laterale", "G Longitudinale". Scegli "Beccheggio": la card Piega e la card Beccheggio devono scambiarsi di posto (verifica `document.getElementById('cardPitch').parentElement.id === 'slotLeftTop'` e `document.getElementById('cardLean').parentElement.id === 'slotRightTop'`). Ricarica la pagina: la disposizione scambiata deve persistere (letta da `localStorage.getItem('moto_card_layout')`).

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "Aggiunge lo scambio delle 4 card grandi in modalità modifica, persistito"
```

---

### Task 7: Scelta dei mini-tile (Sessione/Distanza/Velocità/Punteggio)

**Files:**
- Modify: `index.html` JS (`miniTileValueText`, persistenza `miniLayout`, gestori dei pulsanti ⇄ delle mini-tile)

**Interfaces:**
- Consumes: `openPicker`/`closePicker` (Task 6). `miniLabel1`/`miniLabel2` (Task 1, non ancora referenziati come const). `lastKmh`/`lastScore`/`sessionStartTime`/`totalDistanceM` (Task 3).
- Produces: nessuna nuova interfaccia per task successivi — ultimo pezzo funzionale del piano prima dell'integrazione finale.

- [ ] **Step 1: Aggiungi i riferimenti DOM per le etichette delle mini-tile**

Trova:
```js
  const miniVal1 = $('miniVal1'), miniVal2 = $('miniVal2');
```

Sostituisci con:
```js
  const miniVal1 = $('miniVal1'), miniVal2 = $('miniVal2');
  const miniLabel1 = $('miniLabel1'), miniLabel2 = $('miniLabel2');
```

- [ ] **Step 2: Sostituisci `miniTileValueText` (placeholder del Task 3) con la versione data-driven, e aggiungi la persistenza**

Trova:
```js
  // Task 3: la mini-riga mostra sempre Sessione (posizione 1) e Distanza (posizione 2).
  // Il Task 7 sostituisce questa funzione con una versione che legge la scelta dell'utente.
  function miniTileValueText(slotKey){
    if (slotKey === 'slot1') return sessionStartTime !== null ? formatSessionTime(Date.now() - sessionStartTime) : '00:00';
    return (totalDistanceM / 1000).toFixed(1) + 'km';
  }
```

Sostituisci con:
```js
  const MINI_METRICS = ['session', 'distance', 'speed', 'score'];
  const MINI_LABELS = { session: 'Sessione', distance: 'Distanza', speed: 'Velocità', score: 'Punteggio guida' };
  let miniLayout = { slot1: 'session', slot2: 'distance' };
  function saveMiniLayout(){
    try { localStorage.setItem('moto_mini_layout', JSON.stringify(miniLayout)); } catch(e){}
  }
  function loadMiniLayout(){
    let saved = null;
    try { saved = JSON.parse(localStorage.getItem('moto_mini_layout')); } catch(e){}
    if (saved && MINI_METRICS.includes(saved.slot1) && MINI_METRICS.includes(saved.slot2)) miniLayout = saved;
  }
  function miniMetricValueText(metric){
    if (metric === 'session') return sessionStartTime !== null ? formatSessionTime(Date.now() - sessionStartTime) : '00:00';
    if (metric === 'distance') return (totalDistanceM / 1000).toFixed(1) + 'km';
    if (metric === 'speed') return (lastKmh !== null ? lastKmh.toFixed(0) : '--') + 'km/h';
    if (metric === 'score') return lastScore.toFixed(0);
    return '--';
  }
  function miniTileValueText(slotKey){ return miniMetricValueText(miniLayout[slotKey]); }
  function applyMiniLabels(){
    miniLabel1.textContent = MINI_LABELS[miniLayout.slot1];
    miniLabel2.textContent = MINI_LABELS[miniLayout.slot2];
  }
```

- [ ] **Step 3: Collega i pulsanti ⇄ delle mini-tile al picker, e carica la disposizione salvata**

Trova (nell'area dove il Task 6 ha aggiunto `loadCardLayout(); applyCardLayout();`):
```js
  loadCardLayout();
  applyCardLayout();
```

Sostituisci con:
```js
  loadCardLayout();
  applyCardLayout();

  document.querySelectorAll('.mini-item > .stat-swap-btn[data-mini-slot]').forEach(btn => {
    const slotKey = btn.getAttribute('data-mini-slot');
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const options = MINI_METRICS.map(m => ({ key: m, label: MINI_LABELS[m] }));
      openPicker('Mostra in questo riquadro', options, (chosen) => {
        miniLayout[slotKey] = chosen;
        applyMiniLabels();
        refreshMiniTiles();
        saveMiniLayout();
      });
    });
  });
  loadMiniLayout();
  applyMiniLabels();
  refreshMiniTiles();
```

- [ ] **Step 4: Verifica manuale**

Ricarica la pagina. Con "Modalità modifica" attiva, tocca ⇄ sulla prima mini-tile (Sessione): deve aprirsi un picker con Sessione/Distanza/Velocità/Punteggio guida. Scegli "Velocità": l'etichetta deve diventare "Velocità" e il valore deve leggere `--km/h` (nessun fix GPS ancora in questa sessione di test) o il valore reale se hai un browser con GPS disponibile. Ricarica la pagina: la scelta deve persistere. Verifica anche che scegliere lo stesso dato in entrambi gli slot sia permesso (nessun blocco/errore).

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "Aggiunge la scelta personalizzabile per i due mini-tile (Sessione/Distanza/Velocità/Punteggio)"
```

---

### Task 8: Aggiornamento CLAUDE.md e verifica finale

**Files:**
- Modify: `moto-telemetry/CLAUDE.md`

**Interfaces:**
- Consumes: nessuna (documentazione + verifica, nessuna modifica funzionale a `index.html`).

- [ ] **Step 1: Riscrivi le sezioni di CLAUDE.md che descrivono il vecchio layout**

Apri `CLAUDE.md` e aggiorna (cercando i riferimenti esistenti a "colonna HUD", "gauge badge chevron", "barra G verticale", "mappa ridimensionabile", "Impostazioni" come popover separato) per riflettere: layout a tre colonne, card a barra con scambio, pannello comandi unico, timer di sessione, top G laterale/longitudinale, barra navigatore centrale, rebrand TELAMETRIA, rimozione del ridimensionamento mappa via drag. Usa lo stesso stile di documentazione già presente nel file (sezioni per argomento, riferimenti a nomi di funzione/variabile reali).

- [ ] **Step 2: Smoke test manuale completo**

Con `python3 -m http.server 8000` attivo:
1. Console: nessun errore al caricamento.
2. Layout: tre colonne, TELAMETRIA in alto, barra navigatore "Nessun percorso impostato", mappa centrale, 4 card a barra (Piega/G Laterale a sx, Beccheggio/G Longitudinale a dx), mini-riga Sessione/Distanza, zona vuota cockpit a destra in basso.
3. Linguetta in basso al centro apre il pannello comandi con tutti gli 8 controlli (Avvia/Calibra/Reset max/CSV/Tema/Voce/Modalità modifica/Chiudi).
4. Modalità modifica: scambio delle 4 card funziona e persiste dopo reload; scelta dei 2 mini-tile funziona e persiste dopo reload.
5. Tema: toccando il toggle, sia le card che la mappa che il pannello comandi cambiano correttamente (nessun elemento rimasto con colori hardcoded del tema scuro).
6. Avvia/Ferma: il timer di sessione parte da 00:00, avanza, si ferma su Ferma (valore congelato, non azzerato) e riparte da 00:00 al prossimo Avvia.
7. CSV: esporta un file, verifica che l'header sia byte-per-byte invariato rispetto a prima di questo piano (`timestamp,lat,lon,speed_kmh,heading_deg,lean_deg,pitch_deg,accel_fwd_g,accel_lat_g,accel_vert_g,comfort_idx,score`).
8. Navigatore: apri 🧭, imposta un percorso (se hai una chiave con Places attiva) — la barra centrale deve aggiornarsi con manovra/distanza/ETA, non più i vecchi overlay sulla mappa.

- [ ] **Step 3: Commit finale**

```bash
git add CLAUDE.md
git commit -m "Aggiorna CLAUDE.md per il layout HUD v2 (tre colonne, card personalizzabili, pannello comandi unico)"
```
