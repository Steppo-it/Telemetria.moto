# Redesign del cruscotto (HUD) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ridisegnare il cruscotto (piega, beccheggio, accelerazione/frenata, velocità, punteggio) di `index.html` secondo lo spec approvato, senza toccare la mappa.

**Architecture:** App single-file (`index.html`, HTML/CSS/JS vanilla in un'unica IIFE, nessun build system). Ogni task modifica direttamente questo file. Non esiste framework di test: la verifica di ogni task è manuale via browser (server statico locale + DevTools console), inclusa la simulazione di eventi sensore sintetici (`deviceorientation`/`devicemotion`) per verificare la logica senza un dispositivo reale.

**Tech Stack:** HTML/CSS/JS vanilla, font Orbitron/JetBrains Mono già caricati via Google Fonts, nessuna nuova dipendenza.

## Global Constraints

- Nessun build system, bundler o package manager: tutto resta in `index.html`. (spec: Ambito)
- Nessuna nuova dipendenza esterna da caricare (font, librerie): il numero digitale usa **Orbitron**, già presente. (spec: Note di implementazione)
- La mappa (`#gmap`, `NIGHT_STYLE`, resize handle, navigazione) resta **invariata** — nessun task tocca la logica Google Maps. (spec: Ambito)
- Formato export CSV **invariato** (stesse colonne header). (spec: Esplicitamente fuori scope)
- Zona pulsanti in basso (`.hud-bottom`, posizione/dimensioni "alla cieca") **invariata**. (spec: Esplicitamente fuori scope)
- Il beccheggio **non** riceve soglie colore (resta sempre monocromatico). (spec: Colori)

---

## Riferimento: file di partenza

Tutti i riferimenti a numeri di riga sotto si intendono sullo stato di `moto-telemetry/index.html` **all'inizio del Task 1** (commit `b648338`, 742 righe). Da Task 2 in poi, alcune righe si saranno spostate a causa dei task precedenti: quando un riferimento a riga non corrisponde più esattamente, individua il blocco cercando la stringa indicata (selettore CSS o nome funzione) invece di fidarti ciecamente del numero.

Prima di ogni task, verifica il server locale: da dentro `moto-telemetry/`, `python3 -m http.server 8000` e apri `http://localhost:8000/` in un browser desktop (Chrome/Safari — sensori/GPS reali non servono per questi task, si simulano da console). Tieni la DevTools console aperta per controllare che non compaiano errori JS.

---

### Task 1: Sistema di temi (notturno di default, diurno attivabile)

**Files:**
- Modify: `index.html:10-25` (blocco `:root`)
- Modify: `index.html:1-8` (aggiunge script inline anti-flash nel `<head>`)
- Modify: `index.html` popover Impostazioni (cerca `<div class="popover-title">IMPOSTAZIONI</div>`, oggi intorno alla riga 299)
- Modify: `index.html` blocco `const $ = id => ...` (cerca `const settingsBtn = $('settingsBtn')`, oggi riga 332) e area dopo l'inizializzazione popover (cerca `function closeSettings(){`, oggi righe 358)

**Interfaces:**
- Produces: attributo `data-theme` su `<html>` (`"dark"` o `"light"`), chiave `localStorage` `moto_theme`, variabili CSS `--ink`, `--ink-dim`, `--hair`, `--accent`, `--bg`, `--bg2` (oltre alle esistenti `--blue`, `--blue-dim`, `--blue-glow`, `--amber`, `--red`, `--green`, `--mono`, `--disp`, `--map-pct`). Gli alias legacy `--panel`, `--panel-edge`, `--text`, `--muted` restano definiti (puntano ai nuovi token) così il resto della UI non toccata in questo piano (popover, badge mappa) resta coerente col tema senza modifiche.
- Consumes: nessuna dipendenza da task precedenti (primo task).

- [ ] **Step 1: Sostituisci il blocco `:root` con i nuovi token di tema**

Trova (righe 10-25):
```css
  :root{
    --map-pct: 60%;
    --bg: #050A14;
    --panel: #0A1526;
    --panel-edge: #17283F;
    --blue: #2E8EFF;
    --blue-dim: #1C5FB8;
    --blue-glow: #5CC8FF;
    --amber: #FF9A3D;
    --red: #FF4436;
    --green: #35D48A;
    --text: #E7F0FF;
    --muted: #5C7699;
    --mono: 'JetBrains Mono', 'SF Mono', Menlo, monospace;
    --disp: 'Orbitron', 'Bebas Neue', sans-serif;
  }
```

Sostituisci con:
```css
  :root{
    --map-pct: 60%;
    --ink: #E8ECF0;
    --ink-dim: #5C6A7D;
    --hair: #1C2128;
    --accent: #8AA0BE;
    --bg: #0B0D10;
    --bg2: #0F1216;
    --blue: #2E8EFF;
    --blue-dim: #1C5FB8;
    --blue-glow: #5CC8FF;
    --amber: #FF9A3D;
    --red: #FF4436;
    --green: #35D48A;
    /* alias legacy: mantengono coerente col tema il resto della UI non toccata in questo piano (mappa, popover) */
    --panel: var(--bg2);
    --panel-edge: var(--hair);
    --text: var(--ink);
    --muted: var(--ink-dim);
    --mono: 'JetBrains Mono', 'SF Mono', Menlo, monospace;
    --disp: 'Orbitron', 'Bebas Neue', sans-serif;
  }
  :root[data-theme="light"]{
    --ink: #1B2430;
    --ink-dim: #7A8699;
    --hair: #DCE2EA;
    --accent: #3D4C63;
    --bg: #F4F6F9;
    --bg2: #FFFFFF;
  }
```

- [ ] **Step 2: Aggiungi lo script anti-flash nel `<head>`, prima del blocco `<style>`**

Trova (righe 1-9):
```html
<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>Telemetria Moto — Prova</title>
<style>
```

Sostituisci con:
```html
<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>Telemetria Moto — Prova</title>
<script>
(function(){
  try {
    var t = localStorage.getItem('moto_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', t);
  } catch(e) {}
})();
</script>
<style>
```

(Va eseguito prima del CSS per evitare un flash del tema sbagliato al caricamento.)

- [ ] **Step 3: Aggiungi il toggle tema nel popover Impostazioni**

Trova:
```html
  <div class="popover-panel" id="settingsPanel">
    <div class="popover-title">IMPOSTAZIONI</div>
    <div class="settings-row"><span>Chiudi</span><button class="settings-toggle" id="settingsClose">OK</button></div>
  </div>
```

Sostituisci con:
```html
  <div class="popover-panel" id="settingsPanel">
    <div class="popover-title">IMPOSTAZIONI</div>
    <div class="settings-row"><span>Tema</span><button class="settings-toggle" id="themeToggle">Notturno</button></div>
    <div class="settings-row"><span>Chiudi</span><button class="settings-toggle" id="settingsClose">OK</button></div>
  </div>
```

- [ ] **Step 4: Aggiungi la logica JS del toggle**

Trova nel blocco dei riferimenti DOM:
```js
  const settingsBtn = $('settingsBtn'), settingsPanel = $('settingsPanel'), settingsBackdrop = $('settingsBackdrop'), settingsClose = $('settingsClose');
```

Sostituisci con:
```js
  const settingsBtn = $('settingsBtn'), settingsPanel = $('settingsPanel'), settingsBackdrop = $('settingsBackdrop'), settingsClose = $('settingsClose');
  const themeToggle = $('themeToggle');
```

Poi, subito dopo la funzione `closeSettings(){...}` esistente:
```js
  function closeSettings(){ settingsPanel.classList.remove('open'); settingsBackdrop.classList.remove('open'); }
```

Aggiungi:
```js
  function currentTheme(){ return document.documentElement.getAttribute('data-theme') || 'dark'; }
  function refreshThemeToggleLabel(){ themeToggle.textContent = currentTheme() === 'dark' ? 'Notturno' : 'Diurno'; }
  themeToggle.addEventListener('click', () => {
    const next = currentTheme() === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try { localStorage.setItem('moto_theme', next); } catch(e){}
    refreshThemeToggleLabel();
  });
  refreshThemeToggleLabel();
```

- [ ] **Step 5: Verifica manuale**

Avvia `python3 -m http.server 8000` dentro `moto-telemetry/`, apri `http://localhost:8000/`.
- Console DevTools: nessun errore.
- Sfondo app deve essere quasi nero (tema notturno di default).
- Tocca l'icona ⚙ (Impostazioni), poi il pulsante "Tema": lo sfondo dell'app deve diventare chiaro (quasi bianco) e il pulsante deve ora leggere "Diurno".
- In console: `localStorage.getItem('moto_theme')` deve restituire `"light"`.
- Ricarica la pagina (F5): il tema chiaro deve persistere (niente flash nero prima).
- Rimetti il tema su "Notturno" prima di procedere col task successivo (comodo per confrontare con lo screenshot del design, non obbligatorio).

- [ ] **Step 6: Commit**

```bash
cd moto-telemetry
git add index.html
git commit -m "Aggiunge sistema di temi notturno/diurno all'HUD"
```

---

### Task 2: Cluster gauge — piega, beccheggio, barra G verticale

Questo task riscrive insieme piega, beccheggio e barra G perché condividono lo stesso contenitore (`.hud-top`, che passa da colonna a riga) — separarli lascerebbe uno stato intermedio non funzionante (JS che punta a elementi DOM rimossi).

**Files:**
- Modify: `index.html:96-130` (CSS `.hud-top`/`.hud-bottom`/`.gauge-card`/gforce)
- Modify: `index.html:205-271` (HTML lean-card, gforce-card, pitch-card)
- Modify: `index.html:317-333` (riferimenti DOM)
- Modify: `index.html:432-521` (stato + `updateLeanGauge`/`updatePitchGauge`/`updateGforceGauge`/`handleOrientation`/`handleMotion` — solo le righe che toccano piega/beccheggio/G, non l'intera funzione)
- Modify: `index.html:680-707` (`start()`, reset dei nuovi massimi)

**Interfaces:**
- Consumes: `--ink`, `--ink-dim`, `--hair`, `--accent`, `--amber`, `--red`, `--blue`, `--mono`, `--disp` (da Task 1). `compensateOrientation()`, `compensateAccelXY()`, `getScreenAngle()`, `makePeakHold()` (già esistenti, invariati).
- Produces: DOM ids `leanChevron`, `leanNumBig`, `leanSub`, `leanMaxSx`, `leanMaxDx`, `pitchChevron`, `pitchNumBig`, `pitchSub`, `pitchMaxUp`, `pitchMaxDown`, `gforceVal`, `gGhost` (quest'ultimo id riusato, stessa funzione peak-hold di prima). Variabili di stato `maxLeanSx`, `maxLeanDx`, `maxPitchUp`, `maxPitchDown` (sostituiscono `maxLean`/`maxPitch`). Funzioni `updateLeanGauge(rollDeg)`, `updatePitchGauge(pitchDeg)`, `updateGforceGauge(fwdG, now)` (stessa firma di prima, corpo riscritto). Il Task 4 (fix beccheggio) si aspetta di trovare `updatePitchGauge(currentPitch)` chiamata da un punto che può spostare, e i quattro id `pitchMax*`/`pitchChevron`/`pitchSub` già presenti.

- [ ] **Step 1: Sostituisci il CSS del cluster gauge**

Trova il blocco (righe 95-130, da `.col-hud` a `.gforce-ghost`):
```css
  /* ============ HUD column (right) ============ */
  .col-hud { flex:1 1 auto; min-width:100px; display:flex; flex-direction:column; gap:5px; min-height:0; }
  .hud-top { flex:1 1 auto; min-height:0; display:flex; flex-direction:column; gap:5px; overflow-y:auto; }
  .hud-bottom { flex:0 0 auto; display:flex; flex-direction:column; gap:7px; }

  /* --- shared gauge card (lean + pitch) --- */
  .gauge-card { background: var(--panel); border:1px solid var(--panel-edge); border-radius:10px; padding:5px 7px; display:flex; align-items:center; gap:7px; box-shadow: 0 0 0 1px rgba(46,142,255,.04) inset; }
  .lean-card { flex: 5 1 0; min-height:110px; }
  .pitch-card { flex: 3 1 0; min-height:78px; }
  .gauge-svg-wrap { flex:0 0 auto; height:100%; aspect-ratio:1/1; max-width:50%; }
  .gauge-svg-wrap svg { width:100%; height:100%; display:block; }
  .gauge-readout { flex:1 1 auto; display:flex; flex-direction:column; align-items:center; justify-content:center; min-width:0; }
  .gauge-num { font-family: var(--disp); font-weight:800; line-height:1; color: var(--blue-glow); text-shadow: 0 0 14px rgba(92,200,255,.6); }
  .lean-card .gauge-num { font-size: clamp(24px, 6vh, 44px); }
  .pitch-card .gauge-num { font-size: clamp(18px, 4vh, 30px); }
  .gauge-num.warn { color: var(--amber); text-shadow: 0 0 14px rgba(255,154,61,.5); }
  .gauge-num.danger { color: var(--red); text-shadow: 0 0 14px rgba(255,68,54,.6); }
  .gauge-label { font-family: var(--mono); font-size:8px; letter-spacing:1.5px; color: var(--muted); margin-top:1px; }
  .gauge-max { font-family: var(--mono); font-size:10px; color: var(--blue-dim); margin-top:3px; letter-spacing:.5px; }
  .gauge-max b { color: var(--blue-glow); font-size:12px; }

  /* --- G force meter --- */
  .gforce-card { flex:0 0 auto; background: var(--panel); border:1px solid var(--panel-edge); border-radius:10px; padding:7px 10px; box-shadow: 0 0 0 1px rgba(46,142,255,.04) inset; }
  .gforce-top { display:flex; justify-content:space-between; align-items:baseline; }
  .gforce-title { font-family: var(--mono); font-size:8px; letter-spacing:1px; color: var(--muted); text-transform:uppercase; }
  .gforce-vals { text-align:right; }
  .gforce-val { font-family: var(--disp); font-weight:800; font-size:24px; line-height:1; }
  .gforce-val.accel { color: var(--blue-glow); }
  .gforce-val.brake { color: var(--red); }
  .gforce-sub { font-family: var(--mono); font-size:9.5px; color: var(--muted); margin-top:1px; }
  .gforce-bar-track { position:relative; height:10px; border-radius:5px; background:#0F1D30; margin-top:6px; overflow:visible; }
  .gforce-bar-mid { position:absolute; left:50%; top:-2px; bottom:-2px; width:1px; background: var(--panel-edge); }
  .gforce-bar-fill { position:absolute; top:0; bottom:0; border-radius:5px; transition: width .1s linear; }
  .gforce-bar-fill.accel { left:50%; background: linear-gradient(90deg, var(--blue-dim), var(--blue-glow)); }
  .gforce-bar-fill.brake { right:50%; background: linear-gradient(270deg, #B8221A, var(--red)); }
  .gforce-ghost { position:absolute; top:-3px; width:2.5px; height:16px; border-radius:2px; background:#fff; box-shadow: 0 0 6px rgba(255,255,255,.7); opacity:0; }
```

Sostituisci con:
```css
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
  .lean-badge .gauge-chevron { font-size: clamp(20px, 5vh, 28px); }
  .pitch-badge .gauge-chevron { font-size: clamp(14px, 3.2vh, 18px); }
  .gauge-chevron.warn { color: var(--amber); border-color: var(--amber); }
  .gauge-chevron.danger { color: var(--red); border-color: var(--red); }

  .gauge-body { flex:0 0 auto; min-width:0; }
  .gauge-num { font-family: var(--disp); font-weight:800; line-height:1; color: var(--ink); letter-spacing:.5px; }
  .lean-badge .gauge-num { font-size: clamp(26px, 6.6vh, 38px); }
  .pitch-badge .gauge-num { font-size: clamp(16px, 4vh, 22px); }
  .gauge-num.warn { color: var(--amber); }
  .gauge-num.danger { color: var(--red); }
  .gauge-sub { font-family: var(--mono); font-size:7.5px; letter-spacing:1.3px; color: var(--ink-dim); margin-top:1px; }

  .gauge-maxrow { margin-left:auto; text-align:right; font-family: var(--mono); font-size:7.5px; color: var(--ink-dim); line-height:1.6; white-space:nowrap; }
  .gauge-maxrow b { color: var(--ink); font-weight:600; }

  /* --- G force vertical bar --- */
  .gforce-bar {
    width:20px; flex:0 0 auto; align-self:stretch; border-radius:4px; position:relative;
    background: linear-gradient(180deg, var(--blue) 0%, #6FE0B8 26%, var(--hair) 48%, var(--hair) 52%, var(--amber) 74%, var(--red) 100%);
  }
  .gforce-marker {
    position:absolute; left:-3px; right:-3px; height:4px; top:50%; transform: translateY(-50%);
    background: var(--ink); border-radius:2px; box-shadow: 0 0 6px rgba(0,0,0,.4); opacity:0; transition: opacity .2s;
  }
  .gforce-val { position:absolute; bottom:4px; left:0; right:0; text-align:center; font-family: var(--mono); font-size:7px; font-weight:700; color: var(--ink); }
```

- [ ] **Step 2: Sostituisci l'HTML di lean-card / gforce-card / pitch-card**

Trova il blocco (righe 205-271, dall'apertura `<div class="hud-top">` fino alla chiusura del `pitch-card`):
```html
        <div class="hud-top">

          <div class="gauge-card lean-card">
            <div class="gauge-svg-wrap">
              <svg viewBox="0 0 160 160" id="leanSvg">
                <line x1="10" y1="140" x2="150" y2="140" stroke="#17283F" stroke-width="2"/>
                <g id="bikeGhost" opacity="0">
                  <path d="M80,55 C68,70 66,95 72,132 L88,132 C94,95 92,70 80,55 Z" fill="rgba(92,200,255,.32)"/>
                  <ellipse cx="80" cy="65" rx="20" ry="6" fill="rgba(92,200,255,.32)"/>
                  <circle cx="80" cy="45" r="11" fill="rgba(92,200,255,.32)"/>
                  <rect x="74" y="130" width="12" height="10" rx="2" fill="rgba(92,200,255,.32)"/>
                </g>
                <g id="bikeLive">
                  <path d="M80,55 C68,70 66,95 72,132 L88,132 C94,95 92,70 80,55 Z" fill="var(--blue-glow)"/>
                  <ellipse cx="80" cy="65" rx="20" ry="6" fill="var(--blue-glow)"/>
                  <circle cx="80" cy="45" r="11" fill="var(--blue-glow)"/>
                  <rect x="74" y="130" width="12" height="10" rx="2" fill="var(--blue-glow)"/>
                </g>
              </svg>
            </div>
            <div class="gauge-readout">
              <div class="gauge-num" id="leanNumBig">--°</div>
              <div class="gauge-label">PIEGA</div>
              <div class="gauge-max">MAX <b id="leanMaxVal">--°</b></div>
            </div>
          </div>

          <div class="gforce-card">
            <div class="gforce-top">
              <div class="gforce-title">Accelerazione / Frenata</div>
              <div class="gforce-vals">
                <div class="gforce-val" id="gforceVal">0.00g</div>
                <div class="gforce-sub" id="gforceSubMs">0.0 m/s²</div>
              </div>
            </div>
            <div class="gforce-bar-track">
              <div class="gforce-bar-mid"></div>
              <div class="gforce-bar-fill accel" id="gBarAccel" style="width:0%"></div>
              <div class="gforce-bar-fill brake" id="gBarBrake" style="width:0%"></div>
              <div class="gforce-ghost" id="gGhost"></div>
            </div>
          </div>

          <div class="gauge-card pitch-card">
            <div class="gauge-svg-wrap">
              <svg viewBox="0 0 160 160" id="pitchSvg">
                <line x1="10" y1="120" x2="150" y2="120" stroke="#17283F" stroke-width="2"/>
                <g id="pitchGhost" opacity="0">
                  <circle cx="40" cy="110" r="13" fill="rgba(92,200,255,.32)"/>
                  <circle cx="120" cy="110" r="13" fill="rgba(92,200,255,.32)"/>
                  <path d="M40,100 C50,75 70,68 90,68 C105,68 115,80 120,100 L120,105 L40,105 Z" fill="rgba(92,200,255,.32)"/>
                  <circle cx="95" cy="58" r="9" fill="rgba(92,200,255,.32)"/>
                </g>
                <g id="pitchLive">
                  <circle cx="40" cy="110" r="13" fill="var(--blue-glow)"/>
                  <circle cx="120" cy="110" r="13" fill="var(--blue-glow)"/>
                  <path d="M40,100 C50,75 70,68 90,68 C105,68 115,80 120,100 L120,105 L40,105 Z" fill="var(--blue-glow)"/>
                  <circle cx="95" cy="58" r="9" fill="var(--blue-glow)"/>
                </g>
              </svg>
            </div>
            <div class="gauge-readout">
              <div class="gauge-num" id="pitchNumBig">--°</div>
              <div class="gauge-label">BECCHEGGIO</div>
              <div class="gauge-max">MAX <b id="pitchMaxVal">--°</b></div>
            </div>
          </div>
```

Sostituisci con:
```html
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
                <div class="gauge-maxrow">DOWN <b id="pitchMaxDown">--°</b><br>UP <b id="pitchMaxUp">--°</b></div>
              </div>
            </div>
            <div class="gforce-bar">
              <div class="gforce-marker" id="gGhost"></div>
              <div class="gforce-val" id="gforceVal">0.00g</div>
            </div>
          </div>
```

`.hud-top` resta `flex-direction:column` (invariato) — `.gauge-cluster` è solo una riga interna per piega+beccheggio+barra G. Le righe `<div class="grid">...` e `<div class="score-card">...` restano subito dopo, come figlie di `.hud-top`, invariate per ora — le tocca il Task 3 — e continuano a impilarsi correttamente sotto `.gauge-cluster` senza bisogno di ulteriori modifiche di layout.

- [ ] **Step 3: Aggiorna i riferimenti DOM in JS**

Trova (righe 318-323):
```js
  const leanNumBig = $('leanNumBig'), leanMaxVal = $('leanMaxVal');
  const pitchNumBig = $('pitchNumBig'), pitchMaxVal = $('pitchMaxVal');
  const bikeLive = $('bikeLive'), bikeGhost = $('bikeGhost');
  const pitchLive = $('pitchLive'), pitchGhost = $('pitchGhost');
  const speedVal = $('speedVal'), maxSpeedVal = $('maxSpeedVal');
  const gforceVal = $('gforceVal'), gforceSubMs = $('gforceSubMs'), gBarAccel = $('gBarAccel'), gBarBrake = $('gBarBrake'), gGhost = $('gGhost');
```

Sostituisci con:
```js
  const leanChevron = $('leanChevron'), leanNumBig = $('leanNumBig'), leanSub = $('leanSub');
  const leanMaxSxEl = $('leanMaxSx'), leanMaxDxEl = $('leanMaxDx');
  const pitchChevron = $('pitchChevron'), pitchNumBig = $('pitchNumBig'), pitchSub = $('pitchSub');
  const pitchMaxUpEl = $('pitchMaxUp'), pitchMaxDownEl = $('pitchMaxDown');
  const speedVal = $('speedVal'), maxSpeedVal = $('maxSpeedVal');
  const gforceVal = $('gforceVal'), gGhost = $('gGhost');
```

(`maxSpeedVal` resta per ora — lo rimuove il Task 3.)

- [ ] **Step 4: Sostituisci le variabili di stato dei massimi**

Trova (riga 436):
```js
  let maxLean = 0, maxPitch = 0, maxSpeedKmh = 0;
```

Sostituisci con:
```js
  let maxLeanSx = 0, maxLeanDx = 0, maxPitchUp = 0, maxPitchDown = 0, maxSpeedKmh = 0;
```

- [ ] **Step 5: Riscrivi `updateLeanGauge` e `updatePitchGauge`**

Trova (righe 459-482):
```js
  // NOTE: sign flipped here (-rollDeg) to correct the inverted lean direction
  function updateLeanGauge(rollDeg){
    leanNumBig.textContent = Math.abs(rollDeg).toFixed(0) + '°';
    leanNumBig.classList.remove('warn','danger');
    const abs = Math.abs(rollDeg);
    if (abs > 40) leanNumBig.classList.add('danger'); else if (abs > 25) leanNumBig.classList.add('warn');

    bikeLive.setAttribute('transform', `rotate(${-rollDeg} 80 140)`);

    if (Math.abs(rollDeg) > Math.abs(maxLean)) maxLean = rollDeg;
    leanMaxVal.textContent = Math.abs(maxLean).toFixed(0) + '°';
    bikeGhost.setAttribute('transform', `rotate(${-maxLean} 80 140)`);
    bikeGhost.style.opacity = Math.abs(maxLean) > 0.5 ? 0.85 : 0;
  }

  function updatePitchGauge(pitchDeg){
    pitchNumBig.textContent = Math.abs(pitchDeg).toFixed(0) + '°';
    pitchLive.setAttribute('transform', `rotate(${pitchDeg} 80 105)`);

    if (Math.abs(pitchDeg) > Math.abs(maxPitch)) maxPitch = pitchDeg;
    pitchMaxVal.textContent = Math.abs(maxPitch).toFixed(0) + '°';
    pitchGhost.setAttribute('transform', `rotate(${maxPitch} 80 105)`);
    pitchGhost.style.opacity = Math.abs(maxPitch) > 0.5 ? 0.85 : 0;
  }
```

Sostituisci con:
```js
  // Positivo = destra (DX) per la piega, su (SU) per il beccheggio — convenzione già
  // validata su strada per la piega (vedi CLAUDE.md); il beccheggio va confermato.
  function updateLeanGauge(rollDeg){
    const abs = Math.abs(rollDeg);
    leanNumBig.textContent = abs.toFixed(0) + '°';
    leanChevron.textContent = rollDeg >= 0 ? '▶' : '◀';
    leanSub.textContent = 'PIEGA · ' + (rollDeg >= 0 ? 'DX' : 'SX');

    leanNumBig.classList.remove('warn','danger');
    leanChevron.classList.remove('warn','danger');
    if (abs > 40) { leanNumBig.classList.add('danger'); leanChevron.classList.add('danger'); }
    else if (abs > 25) { leanNumBig.classList.add('warn'); leanChevron.classList.add('warn'); }

    if (rollDeg >= 0) { if (rollDeg > maxLeanDx) maxLeanDx = rollDeg; }
    else { if (-rollDeg > maxLeanSx) maxLeanSx = -rollDeg; }
    leanMaxDxEl.textContent = maxLeanDx.toFixed(0) + '°';
    leanMaxSxEl.textContent = maxLeanSx.toFixed(0) + '°';
  }

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

- [ ] **Step 6: Riscrivi `updateGforceGauge`**

Trova (righe 507-521):
```js
  function updateGforceGauge(fwdG, now){
    gforceVal.textContent = (fwdG >= 0 ? '+' : '') + fwdG.toFixed(2) + 'g';
    gforceVal.classList.remove('accel','brake');
    gforceVal.classList.add(fwdG >= 0 ? 'accel' : 'brake');
    gforceSubMs.textContent = (fwdG * 9.80665 >= 0 ? '+' : '') + (fwdG * 9.80665).toFixed(2) + ' m/s²';

    const pct = clamp(Math.abs(fwdG) / 1.0 * 50, 0, 50);
    if (fwdG >= 0) { gBarAccel.style.width = pct + '%'; gBarBrake.style.width = '0%'; }
    else { gBarBrake.style.width = pct + '%'; gBarAccel.style.width = '0%'; }

    const gp = gPeak(fwdG, now);
    const ghostPct = clamp(gp.peak / 1.0 * 50, 0, 50);
    gGhost.style.left = gp.sign >= 0 ? `calc(50% + ${ghostPct}%)` : `calc(50% - ${ghostPct}%)`;
    gGhost.style.opacity = gp.opacity;
  }
```

Sostituisci con:
```js
  function updateGforceGauge(fwdG, now){
    gforceVal.textContent = (fwdG >= 0 ? '+' : '') + fwdG.toFixed(2) + 'g';

    const gp = gPeak(fwdG, now);
    const pct = clamp(gp.peak / 1.0 * 50, 0, 50);
    gGhost.style.top = (gp.sign >= 0 ? (50 - pct) : (50 + pct)) + '%';
    gGhost.style.opacity = gp.opacity;
  }
```

(Il centro barra = 0g, il marcatore si muove verso l'alto — colore blu/accelerazione — in accelerazione, verso il basso — colore rosso/frenata — in frenata, mantenendo lo stesso comportamento di picco a scomparsa di `makePeakHold()`, invariato.)

- [ ] **Step 7: Aggiorna il reset in `start()`**

Trova (riga 693):
```js
    maxLean = 0; maxPitch = 0; maxSpeedKmh = 0;
```

Sostituisci con:
```js
    maxLeanSx = 0; maxLeanDx = 0; maxPitchUp = 0; maxPitchDown = 0; maxSpeedKmh = 0;
```

- [ ] **Step 8: Verifica manuale — layout e piega/beccheggio**

Ricarica `http://localhost:8000/`. Console: nessun errore. Il cluster gauge deve mostrare due badge (piega grande sopra, beccheggio più piccolo sotto) affiancati a destra da una barra verticale sfumata blu→rosso, tutto senza cornici pesanti.

In console, simula un sensore di orientamento:
```js
window.dispatchEvent(new DeviceOrientationEvent('deviceorientation', {beta: 5, gamma: 30, absolute: false}));
```
Atteso: `document.getElementById('leanNumBig').textContent === '30°'`, `document.getElementById('leanChevron').textContent === '▶'`, `document.getElementById('leanSub').textContent === 'PIEGA · DX'`, `document.getElementById('leanMaxDx').textContent === '30°'`, `document.getElementById('pitchNumBig').textContent === '5°'`, `document.getElementById('pitchChevron').textContent === '▲'`.

Ora un valore negativo:
```js
window.dispatchEvent(new DeviceOrientationEvent('deviceorientation', {beta: -8, gamma: -22, absolute: false}));
```
Atteso: `leanChevron` torna `'◀'`, `leanSub` diventa `'PIEGA · SX'`, `document.getElementById('leanMaxSx').textContent === '22°'`, e **`leanMaxDx` resta `'30°'`** (il massimo destro precedente non deve azzerarsi).

Valore oltre soglia danger:
```js
window.dispatchEvent(new DeviceOrientationEvent('deviceorientation', {beta: 0, gamma: 45, absolute: false}));
```
Atteso: sia `leanNumBig` che `leanChevron` hanno la classe CSS `danger` (colore rosso) — verifica con `document.getElementById('leanNumBig').className`.

- [ ] **Step 9: Verifica manuale — barra G**

Prima lascia che il filtro di gravità si assesti a riposo:
```js
for (let i=0;i<15;i++){ window.dispatchEvent(new DeviceMotionEvent('devicemotion', {accelerationIncludingGravity:{x:0,y:0,z:9.81}})); }
```
Poi un campione con accelerazione in avanti:
```js
window.dispatchEvent(new DeviceMotionEvent('devicemotion', {accelerationIncludingGravity:{x:0,y:12.8,z:9.81}}));
document.getElementById('gforceVal').textContent // atteso: valore positivo tipo "+0.3x g"
document.getElementById('gGhost').style.top // atteso: percentuale < 50% (marcatore sopra il centro)
document.getElementById('gGhost').style.opacity // atteso: "1"
```

- [ ] **Step 10: Commit**

```bash
git add index.html
git commit -m "Ridisegna piega/beccheggio come badge con chevron e barra G verticale"
```

---

### Task 3: Riga compatta velocità/punteggio, pulsanti monocromatici, divisorio a dissolvenza

**Files:**
- Modify: `index.html:132-164` (CSS `.grid`/`.tile`/`.score-card`/pulsanti)
- Modify: `index.html:65-70` (CSS `.col-map`, rimuove bordo, aggiunge dissolvenza)
- Modify: `index.html:273-292` (HTML `.grid`/`.score-card`/pulsanti, invariati nella struttura pulsanti ma cambia il resto)
- Modify: `index.html:326-329` (riferimenti DOM ora inutilizzati)
- Modify: `index.html` `renderScore()` (cerca `function renderScore(`) e `handlePosition()` (cerca `function handlePosition(`) e `start()` (cerca `maxSpeedVal.innerHTML`)

**Interfaces:**
- Consumes: `--ink`, `--ink-dim`, `--hair`, `--bg` (Task 1); `speedVal`, `scoreNum` DOM refs (esistenti, riusati senza modifiche di firma).
- Produces: classe `.mini-row` (contenitore velocità+punteggio). Rimuove `maxSpeedVal`, `maxSpeedKmh`, `valAccel`, `valLean`, `valComfort` (nessun task successivo dipende da questi).

- [ ] **Step 1: Sostituisci il CSS di tile/score-card con la riga compatta, e monocromatizza i pulsanti**

Trova (righe 132-164):
```css
  /* --- compact tiles + score --- */
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:5px; flex:0 0 auto; }
  .tile { background: var(--panel); border:1px solid var(--panel-edge); border-radius:8px; padding:4px 7px; }
  .tile-label { font-family: var(--mono); font-size:7px; letter-spacing:1px; color: var(--muted); text-transform:uppercase; }
  .tile-val { font-family: var(--mono); font-size:14px; font-weight:600; color: var(--text); }
  .tile-unit { font-size:8.5px; color: var(--muted); margin-left:2px; }

  .score-card { flex:0 0 auto; background: var(--panel); border:1px solid var(--panel-edge); border-radius:9px; padding:5px 9px; box-shadow: 0 0 0 1px rgba(46,142,255,.04) inset; }
  .score-top { display:flex; align-items:baseline; justify-content:space-between; }
  .score-title { font-family: var(--mono); font-size:7.5px; letter-spacing:1px; color: var(--muted); text-transform:uppercase; }
  .score-num { font-family: var(--disp); font-weight:700; font-size:16px; color: var(--green); }
  .score-num.mid { color: var(--amber); }
  .score-num.low { color: var(--red); }
  .subrow-compact { display:flex; justify-content:space-between; font-family: var(--mono); font-size:7.5px; color: var(--muted); margin-top:2px; }
  .subrow-compact b { color: var(--text); }

  /* ============ big blind-tappable controls ============ */
  .btn-big {
    appearance:none; border:none; border-radius:12px; padding:14px; font-family: var(--disp); font-weight:700; font-size:16px; letter-spacing:1px;
    display:flex; align-items:center; justify-content:center; gap:6px; cursor:pointer; min-height:56px;
    transition: transform .1s, opacity .2s;
  }
  .btn-big:active { transform: scale(0.97); }
  .btn-big.start { background: linear-gradient(135deg, var(--blue-glow), var(--blue-dim)); color:#041020; box-shadow: 0 0 16px rgba(46,142,255,.45); }
  .btn-big.stop { background: linear-gradient(135deg, var(--red), #B8221A); color:#1A0303; box-shadow: 0 0 16px rgba(255,68,54,.4); }
  .btn-big.calib { background: rgba(46,142,255,.1); border:2px solid var(--blue-dim); color: var(--blue-glow); }
  .btn-big[disabled] { opacity:.5; pointer-events:none; }

  .mini-actions-row { display:flex; gap:7px; }
  .btn-mini { appearance:none; border:1px solid var(--panel-edge); background: var(--panel); color: var(--muted); border-radius:9px; padding:8px; font-family:'Inter',sans-serif; font-weight:500; font-size:10.5px; display:flex; align-items:center; justify-content:center; gap:4px; flex:1 1 0; cursor:pointer; min-height:38px; }
  .btn-mini:disabled { opacity:.4; }
```

Sostituisci con:
```css
  /* --- riga compatta velocità + punteggio --- */
  .mini-row { display:flex; gap:16px; border-top:1px solid var(--hair); padding-top:6px; flex:0 0 auto; }
  .mini-item { display:flex; flex-direction:column; }
  .mini-label { font-family: var(--mono); font-size:6.5px; letter-spacing:1px; color: var(--ink-dim); text-transform:uppercase; }
  .mini-val { font-family: var(--disp); font-size:15px; color: var(--ink); font-weight:700; }
  .mini-unit { font-size:9px; color: var(--ink-dim); margin-left:2px; font-family: var(--mono); font-weight:400; }

  /* ============ big blind-tappable controls (monocromatici) ============ */
  .btn-big {
    appearance:none; border:none; border-radius:12px; padding:14px; font-family: var(--disp); font-weight:700; font-size:16px; letter-spacing:1px;
    display:flex; align-items:center; justify-content:center; gap:6px; cursor:pointer; min-height:56px;
    transition: transform .1s, opacity .2s;
  }
  .btn-big:active { transform: scale(0.97); }
  .btn-big.start, .btn-big.stop { background: var(--ink); color: var(--bg); }
  .btn-big.calib { background:transparent; border:2px solid var(--hair); color: var(--ink); }
  .btn-big[disabled] { opacity:.5; pointer-events:none; }

  .mini-actions-row { display:flex; gap:7px; }
  .btn-mini { appearance:none; border:1px solid var(--hair); background:transparent; color: var(--ink-dim); border-radius:9px; padding:8px; font-family:'Inter',sans-serif; font-weight:500; font-size:10.5px; display:flex; align-items:center; justify-content:center; gap:4px; flex:1 1 0; cursor:pointer; min-height:38px; }
  .btn-mini:disabled { opacity:.4; }
```

- [ ] **Step 2: Rimuovi bordo/ombra dalla mappa e aggiungi la dissolvenza**

Trova (righe 66-70):
```css
  .col-map {
    flex: 0 0 var(--map-pct); min-width:0; position:relative;
    border-radius:12px; overflow:hidden; background: var(--panel); border:1px solid var(--panel-edge);
    box-shadow: 0 0 0 1px rgba(46,142,255,.06) inset, 0 0 22px rgba(46,142,255,.08);
  }
```

Sostituisci con:
```css
  .col-map {
    flex: 0 0 var(--map-pct); min-width:0; position:relative;
    border-radius:12px; overflow:hidden; background: var(--bg2);
  }
  .col-map::after {
    content:''; position:absolute; top:0; bottom:0; right:0; width:70px;
    background: linear-gradient(90deg, transparent, var(--bg) 92%);
    pointer-events:none; z-index:5;
  }
```

- [ ] **Step 3: Sostituisci l'HTML di `.grid`/`.score-card` con `.mini-row`**

Trova:
```html
          <div class="grid">
            <div class="tile"><div class="tile-label">Velocità</div><div class="tile-val" id="speedVal">--<span class="tile-unit">km/h</span></div></div>
            <div class="tile"><div class="tile-label">Vel. max</div><div class="tile-val" id="maxSpeedVal">--<span class="tile-unit">km/h</span></div></div>
          </div>

          <div class="score-card">
            <div class="score-top"><div class="score-title">Guida</div><div class="score-num" id="scoreNum">--</div></div>
            <div class="subrow-compact"><span>Fr/Ac <b id="valAccel">--</b></span><span>Pg <b id="valLean">--</b></span><span>Cp <b id="valComfort">--</b></span></div>
          </div>
        </div>
```

Sostituisci con:
```html
          <div class="mini-row">
            <div class="mini-item"><span class="mini-label">Velocità</span><span class="mini-val" id="speedVal">--<span class="mini-unit">km/h</span></span></div>
            <div class="mini-item"><span class="mini-label">Guida</span><span class="mini-val" id="scoreNum">--</span></div>
          </div>
        </div>
```

- [ ] **Step 4: Rimuovi i riferimenti DOM non più usati**

Trova (righe 326-329, come rimasti dopo il Task 2):
```js
  const speedVal = $('speedVal'), maxSpeedVal = $('maxSpeedVal');
  const mainBtn = $('mainBtn'), exportBtn = $('exportBtn'), calibBtn = $('calibBtn');
  const statusDot = $('statusDot'), statusText = $('statusText');
  const logInfo = $('logInfo');
  const permNote = $('permNote');
  const scoreNum = $('scoreNum');
  const valAccel = $('valAccel'), valLean = $('valLean'), valComfort = $('valComfort');
```

Sostituisci con:
```js
  const speedVal = $('speedVal');
  const mainBtn = $('mainBtn'), exportBtn = $('exportBtn'), calibBtn = $('calibBtn');
  const statusDot = $('statusDot'), statusText = $('statusText');
  const logInfo = $('logInfo');
  const permNote = $('permNote');
  const scoreNum = $('scoreNum');
```

- [ ] **Step 5: Rimuovi `maxSpeedKmh`/`maxSpeedVal` da `handlePosition()`**

Trova dentro `handlePosition(pos)`:
```js
    const kmh = pos.coords.speed !== null && pos.coords.speed >= 0 ? (pos.coords.speed * 3.6) : null;
    speedVal.innerHTML = (kmh !== null ? kmh.toFixed(0) : '--') + '<span class="tile-unit">km/h</span>';
    if (kmh !== null && kmh > maxSpeedKmh) { maxSpeedKmh = kmh; maxSpeedVal.innerHTML = maxSpeedKmh.toFixed(0) + '<span class="tile-unit">km/h</span>'; }
```

Sostituisci con:
```js
    const kmh = pos.coords.speed !== null && pos.coords.speed >= 0 ? (pos.coords.speed * 3.6) : null;
    speedVal.innerHTML = (kmh !== null ? kmh.toFixed(0) : '--') + '<span class="mini-unit">km/h</span>';
```

- [ ] **Step 6: Rimuovi `maxSpeedKmh` dallo stato e dal reset in `start()`**

Trova (dopo il Task 2, riga con):
```js
  let maxLeanSx = 0, maxLeanDx = 0, maxPitchUp = 0, maxPitchDown = 0, maxSpeedKmh = 0;
```

Sostituisci con:
```js
  let maxLeanSx = 0, maxLeanDx = 0, maxPitchUp = 0, maxPitchDown = 0;
```

Trova dentro `start()`:
```js
    maxLeanSx = 0; maxLeanDx = 0; maxPitchUp = 0; maxPitchDown = 0; maxSpeedKmh = 0;
    vertBuf = [];
    subAccel = 100; subLean = 100; subComfort = 100;
    totalDistanceM = 0; lastLat = null; lastLon = null;
    distVal.textContent = '0.0';
    maxSpeedVal.innerHTML = '--<span class="tile-unit">km/h</span>';
    setStatus(true, 'REGISTRA');
```

Sostituisci con:
```js
    maxLeanSx = 0; maxLeanDx = 0; maxPitchUp = 0; maxPitchDown = 0;
    vertBuf = [];
    subAccel = 100; subLean = 100; subComfort = 100;
    totalDistanceM = 0; lastLat = null; lastLon = null;
    distVal.textContent = '0.0';
    setStatus(true, 'REGISTRA');
```

- [ ] **Step 7: Rimuovi l'assegnazione a `valAccel`/`valLean`/`valComfort` in `renderScore()`**

Trova:
```js
  function renderScore(overall, a, l, c){
    scoreNum.textContent = overall.toFixed(0);
    scoreNum.classList.remove('mid','low');
    if (overall < 55) scoreNum.classList.add('low'); else if (overall < 78) scoreNum.classList.add('mid');
    valAccel.textContent = a.toFixed(0); valLean.textContent = l.toFixed(0); valComfort.textContent = c.toFixed(0);
  }
```

Sostituisci con:
```js
  function renderScore(overall, a, l, c){
    scoreNum.textContent = overall.toFixed(0);
    scoreNum.classList.remove('mid','low');
    if (overall < 55) scoreNum.classList.add('low'); else if (overall < 78) scoreNum.classList.add('mid');
  }
```

(I parametri `a`, `l`, `c` restano nella firma per non toccare il punto di chiamata in `handleMotion()` — sono semplicemente inutilizzati nel corpo, cosa accettabile qui perché la firma è condivisa con la logica di calcolo dei sotto-punteggi che resta invariata.)

- [ ] **Step 8: Verifica manuale**

Ricarica la pagina. Console: nessun errore (in particolare nessun `Cannot read properties of null` legato a `maxSpeedVal`/`valAccel`/`valLean`/`valComfort`).
- La mappa non deve più avere un bordo visibile; il lato destro della mappa deve sfumare verso lo sfondo invece di avere una linea netta.
- Sotto i due badge deve comparire una riga sottile con "Velocità" e "Guida", separata da un filo sottile sopra.
- I pulsanti "Avvia" e "Calibra" non devono più avere il colore blu acceso: devono essere monocromatici (chiaro su sfondo scuro nel tema notturno).
- Tocca ⚙ → Tema per verificare che anche la nuova riga compatta e i pulsanti seguano il tema chiaro.

- [ ] **Step 9: Commit**

```bash
git add index.html
git commit -m "Compatta velocità/punteggio, monocromatizza pulsanti, aggiunge dissolvenza mappa/HUD"
```

---

### Task 4: Fix calcolo beccheggio (bug impennata)

**Files:**
- Modify: `index.html` `handleOrientation()` (cerca `function handleOrientation(e){`)
- Modify: `index.html` `handleMotion()` (cerca `function handleMotion(e){`)
- Modify: `index.html` handler `calibBtn` (cerca `calibBtn.addEventListener`)

**Interfaces:**
- Consumes: `gEst` (vettore di gravità stimato, già calcolato in `handleMotion` prima di questo task), `compensateAccelXY()`, `getScreenAngle()`, `updatePitchGauge()` (Task 2), `lastRawPitch`/`pitchOffset` (già esistenti).
- Produces: nuova funzione `computePitchFromGravity(gx, gy, gz, angle)`. `currentPitch` continua a esistere con lo stesso nome/uso (letto da `window.__latestTelemetry` per il CSV e da `updatePitchGauge`), ma da ora calcolato in `handleMotion` invece che in `handleOrientation`.

- [ ] **Step 1: Aggiungi `computePitchFromGravity` accanto alle altre funzioni di compensazione**

Trova:
```js
  function compensateAccelXY(x, y, angle){
    switch (((angle % 360) + 360) % 360) {
      case 90:  return { x: -y, y: x };
      case 270: return { x: y,  y: -x };
      case 180: return { x: -x, y: -y };
      default:  return { x: x,  y: y };
    }
  }
```

Aggiungi subito dopo:
```js
  // Beccheggio dal vettore di gravità stimato (gEst) invece che da deviceorientation.beta:
  // beta è un angolo di Eulero e soffre di gimbal lock/salti oltre ~90° di inclinazione
  // (es. durante un'impennata, beta può saltare a valori come ~-350°). atan2 su due
  // componenti del vettore di gravità resta continuo su tutto l'intervallo, senza quel salto.
  function computePitchFromGravity(gx, gy, gz, angle){
    const comp = compensateAccelXY(gx, gy, angle);
    const rad = Math.atan2(-comp.y, Math.sqrt(comp.x * comp.x + gz * gz));
    return rad * 180 / Math.PI;
  }
```

- [ ] **Step 2: Rimuovi il calcolo del beccheggio da `handleOrientation`**

Trova:
```js
  function handleOrientation(e){
    if (e.gamma === null) return;
    if (typeof e.webkitCompassHeading === 'number' && !isNaN(e.webkitCompassHeading)) compassHeading = e.webkitCompassHeading;
    const angle = getScreenAngle();
    const comp = compensateOrientation(e.beta || 0, e.gamma, angle);
    lastRawRoll = comp.roll; lastRawPitch = comp.pitch;
    currentLean = comp.roll - leanOffset;
    currentPitch = comp.pitch - pitchOffset;
    updateLeanGauge(currentLean);
    updatePitchGauge(currentPitch);

    const now = performance.now();
```

Sostituisci con:
```js
  function handleOrientation(e){
    if (e.gamma === null) return;
    if (typeof e.webkitCompassHeading === 'number' && !isNaN(e.webkitCompassHeading)) compassHeading = e.webkitCompassHeading;
    const angle = getScreenAngle();
    const comp = compensateOrientation(e.beta || 0, e.gamma, angle);
    lastRawRoll = comp.roll;
    currentLean = comp.roll - leanOffset;
    updateLeanGauge(currentLean);
    // il beccheggio (currentPitch) è calcolato in handleMotion() da computePitchFromGravity()

    const now = performance.now();
```

- [ ] **Step 3: Calcola il beccheggio in `handleMotion`, subito dopo l'aggiornamento di `gEst`**

Trova:
```js
    gEst.x = G_ALPHA * gEst.x + (1 - G_ALPHA) * rx;
    gEst.y = G_ALPHA * gEst.y + (1 - G_ALPHA) * ry;
    gEst.z = G_ALPHA * gEst.z + (1 - G_ALPHA) * rz;
    const lx = rx - gEst.x, ly = ry - gEst.y, lz = rz - gEst.z;

    const angle = getScreenAngle();
    const comp = compensateAccelXY(lx, ly, angle);
```

Sostituisci con:
```js
    gEst.x = G_ALPHA * gEst.x + (1 - G_ALPHA) * rx;
    gEst.y = G_ALPHA * gEst.y + (1 - G_ALPHA) * ry;
    gEst.z = G_ALPHA * gEst.z + (1 - G_ALPHA) * rz;
    const lx = rx - gEst.x, ly = ry - gEst.y, lz = rz - gEst.z;

    const angle = getScreenAngle();

    lastRawPitch = computePitchFromGravity(gEst.x, gEst.y, gEst.z, angle);
    currentPitch = lastRawPitch - pitchOffset;
    updatePitchGauge(currentPitch);

    const comp = compensateAccelXY(lx, ly, angle);
```

(La riga `calibBtn.addEventListener` non richiede modifiche: legge già `lastRawPitch`, che ora viene semplicemente popolato da `handleMotion` invece che da `handleOrientation` — stesso nome, stesso comportamento di calibrazione.)

- [ ] **Step 4: Verifica manuale — continuità durante un'inclinazione estrema**

Nessun dispositivo reale può simulare un'impennata in fase di sviluppo: la verifica qui accerta che il **calcolo** non produca il salto discontinuo, non che il segno sia quello "giusto" su strada (va confermato in un secondo momento, vedi nota sotto).

In console, porta prima il vettore di gravità a riposo:
```js
for (let i=0;i<15;i++){ window.dispatchEvent(new DeviceMotionEvent('devicemotion', {accelerationIncludingGravity:{x:0,y:0,z:9.81}})); }
document.getElementById('pitchNumBig').textContent // atteso: "0°" o vicino
```
Poi simula un'inclinazione estesa in avanti (oltre i 90° equivalenti — telefono quasi capovolto sull'asse longitudinale, come durante un'impennata):
```js
for (let i=0;i<15;i++){ window.dispatchEvent(new DeviceMotionEvent('devicemotion', {accelerationIncludingGravity:{x:0,y:9.7,z:-2.0}})); }
document.getElementById('pitchNumBig').textContent // atteso: un valore ragionevole (es. tra 60° e 100°), MAI qualcosa vicino a 350°
```
Se il verso (SU/GIÙ) risulta invertito rispetto alla realtà quando lo provi su strada, inverti il segno in `computePitchFromGravity` cambiando `Math.atan2(-comp.y, ...)` in `Math.atan2(comp.y, ...)` — stessa modifica di una riga già documentata in passato per la piega.

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "Calcola il beccheggio dal vettore di gravità per evitare il salto durante un'impennata"
```

---

### Task 5: Aggiornamento CLAUDE.md e verifica finale

**Files:**
- Modify: `moto-telemetry/CLAUDE.md`

**Interfaces:**
- Consumes: nessuna (task di sola documentazione + verifica, nessuna modifica funzionale a `index.html`).

- [ ] **Step 1: Aggiorna la sezione "Gauge" e "Problemi noti" in CLAUDE.md**

Trova la sezione (cerca `### Gauge "in stile moto" (piega e beccheggio)`):
```markdown
### Gauge "in stile moto" (piega e beccheggio)

Entrambi condividono la stessa logica e lo stesso pattern visivo:
- Una sagoma SVG stilizzata (moto+rider vista da dietro per la piega, vista laterale per il beccheggio) che ruota in tempo reale attorno a un pivot, proporzionalmente all'angolo corrente.
- Un numero grande (font Orbitron) con il valore assoluto in gradi, colorato blu/ambra/rosso sopra soglia (25°/40° per la piega — soglie arbitrarie, punto di partenza da tarare in base al feedback reale).
- Un "ghost": sagoma semi-trasparente **persistente per tutta la sessione** che mostra il valore massimo raggiunto (non svanisce — comportamento diverso dal picco della forza G, vedi sotto). Si resetta a ogni **Avvia**.
- **Nota importante sul verso**: il segno di rotazione della piega è stato corretto una volta (era invertito rispetto alla realtà) cambiando `rotate(${rollDeg}...)` in `rotate(${-rollDeg}...)` in `updateLeanGauge()`. Il beccheggio non è stato ancora validato su strada — se risulta invertito, stessa modifica di una riga in `updatePitchGauge()`.
```

Sostituisci con:
```markdown
### Gauge "badge + chevron" (piega e beccheggio)

Niente più sagoma di moto: ogni gauge è un chevron di verso (▶/◀ per la piega, ▲/▼ per il beccheggio) + numero grande (Orbitron) + sottoetichetta tecnica, monocromatici tranne la piega oltre soglia (ambra 25°/rossa 40° — soglie arbitrarie, non calibrate su dati reali). Il beccheggio non ha soglie colore.

- **Massimi separati per lato/verso**: `maxLeanSx`/`maxLeanDx` per la piega, `maxPitchUp`/`maxPitchDown` per il beccheggio — persistenti per tutta la sessione, si resettano a ogni **Avvia** (`start()`), aggiornati in `updateLeanGauge()`/`updatePitchGauge()`.
- **Convenzione segno**: positivo = destra (DX) per la piega — già validata su strada — e su (SU) per il beccheggio. Se il beccheggio risulta invertito su strada, inverti il segno in `computePitchFromGravity()` (cambia `Math.atan2(-comp.y, ...)` in `Math.atan2(comp.y, ...)`).
- **Calcolo beccheggio**: da `computePitchFromGravity()`, basato sul vettore di gravità stimato (`gEst`, calcolato in `handleMotion()`) invece che su `deviceorientation.beta` — `beta` è un angolo di Eulero e soffre di gimbal lock/salti discontinui (es. ~-350°) durante un'inclinazione estrema come un'impennata. Non validato su una vera impennata (nessun modo di testarlo senza un dispositivo reale in marcia).
```

Trova anche (nella sezione "Problemi noti"):
```markdown
1. **Verso del beccheggio non validato** — vedi sopra, correzione di una riga se necessario in `updatePitchGauge()`.
```

Sostituisci con:
```markdown
1. **Verso del beccheggio non validato** — vedi sopra, correzione di una riga se necessario in `computePitchFromGravity()`.
```

- [ ] **Step 2: Smoke test manuale completo**

Con `python3 -m http.server 8000` attivo, apri `http://localhost:8000/` e verifica in sequenza (console DevTools sempre aperta, zero errori attesi in ogni punto):

1. Il tema di default è notturno; ⚙ → Tema alterna a diurno e persiste dopo un reload.
2. Il layout mostra piega grande in alto, beccheggio più piccolo sotto, barra G verticale sfumata a destra, riga velocità/guida sotto, pulsanti in basso — nessuna cornice pesante, mappa che sfuma verso il bordo destro.
3. Simulando eventi come nei Task 2 e 4 (`dispatchEvent` di `deviceorientation`/`devicemotion`), i numeri, i chevron, le soglie colore e i quattro massimi separati si aggiornano correttamente.
4. Tocca **Avvia** (concede/nega permessi sensori — su desktop senza sensori l'app resta comunque utilizzabile, verifica solo che non lanci eccezioni), poi **Ferma**: lo stato passa a "punti pronti", il pulsante **CSV** si abilita.
5. Tocca **CSV**: si scarica un file, apri il file e verifica che l'header sia invariato (`timestamp,lat,lon,speed_kmh,heading_deg,lean_deg,pitch_deg,accel_fwd_g,accel_lat_g,accel_vert_g,comfort_idx,score`).
6. Tocca **Calibra**: nessun errore in console.
7. Trascina la maniglia di resize tra mappa e HUD: la mappa si ridimensiona, la dissolvenza resta coerente ai nuovi bordi.

- [ ] **Step 3: Commit finale**

```bash
git add CLAUDE.md
git commit -m "Aggiorna CLAUDE.md per il nuovo design del cruscotto"
```

Il branch locale sarà ora alcuni commit avanti rispetto a `origin/main` — il push va confermato esplicitamente con l'utente (non farlo automaticamente).
