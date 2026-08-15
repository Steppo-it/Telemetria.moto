# Telemetria Moto — CLAUDE.md

Documento di contesto per Claude Code (o chiunque riprenda il progetto in VS Code). Contiene tutto quello che serve per capire cosa è stato costruito, come, e perché, senza dover rileggere l'intera cronologia della chat originale.

## Cos'è

Una PWA (single-page, single-file) per iPhone che, montata sul cruscotto/manubrio di una moto, mostra e registra in tempo reale: angolo di piega, beccheggio, accelerazione/frenata, velocità GPS, un punteggio di guida calcolato, e una mappa di navigazione con percorso evidenziato. Pensata per essere usata **in marcia**, con telefono fisso su supporto, schermo sempre visibile, landscape only.

L'interfaccia si presenta ("brand") come **TELAMETRIA** — "By TelaStampiamo" in piccolo accanto — nella topbar dell'app (`.brand`). Il nome del progetto/repo resta "Telemetria Moto" (da cui il titolo di questo file e il nome cartella); il rebrand riguarda solo la UI mostrata all'utente, introdotto nel redesign layout v2 (vedi sotto).

Non è un progetto con build system, bundler o package manager: è **un solo file HTML** (`index.html`) con CSS e JS inline, pensato per essere servito staticamente via GitHub Pages. Nessuna dipendenza da installare lato sviluppo.

## Stack tecnico

- **Nessun framework** — HTML/CSS/JS vanilla, tutto in un file.
- **Google Maps JavaScript API + Directions API** — mappa e calcolo percorso (richiede una API key dell'utente, vedi sotto).
- **Geolocation API** (`navigator.geolocation.watchPosition`) — posizione, velocità, direzione (heading).
- **DeviceOrientationEvent / DeviceMotionEvent** — piega, beccheggio, accelerazione (richiedono permesso esplicito su iOS 13+ via `requestPermission()`, deve partire da un tap diretto dell'utente).
- **localStorage** — persistenza di quattro preferenze utente: tema chiaro/scuro (`moto_theme`, `dark`/`light`, impostato dal toggle **Tema** nel pannello comandi unico — vedi sotto — e riletto anche prima del rendering, in un piccolo `<script>` in `<head>`, per evitare un flash del tema sbagliato), voce navigatore attiva/disattiva (`moto_voice`, vedi sezione Mappa e navigazione), disposizione delle 4 card grandi (`moto_card_layout`) e scelta dei 2 mini-tile (`moto_mini_layout`) — questi ultimi due introdotti dal redesign layout v2, vedi sezione Layout. La vecchia preferenza `moto_map_pct` (dimensione mappa via drag) **non esiste più**: il ridimensionamento mappa è stato rimosso deliberatamente in quel redesign, vedi sezione Layout. Nota: questo NON è un artifact di Claude.ai, gira su una pagina servita esternamente via GitHub Pages, quindi `localStorage` è pienamente supportato (a differenza degli artifact in claude.ai dove è vietato).
- **Font esterni**: Google Fonts (Orbitron per i numeri grandi/display, JetBrains Mono per i dati, Inter per testo secondario).
- **Hosting**: GitHub Pages (repo pubblico — Pages su repo privati richiede un piano a pagamento).

## Struttura del file

`index.html` (~1200 righe) è organizzato in tre blocchi:
1. `<style>` — tutte le variabili CSS in `:root` (colori, font) + layout
2. `<body>` — markup statico di tutti i pannelli/card/popover
3. `<script>` — un'unica IIFE con tutta la logica, più il tag `<script>` di Google Maps in fondo alla pagina (con `defer`, carica dopo lo script principale ma prima che l'utente possa interagire)

Non ci sono altri file JS/CSS esterni al progetto oltre a Leaflet (rimosso) → ora solo Google Maps via CDN ufficiale Google.

## Setup per sviluppo locale

Non serve build. Per sviluppare:
1. Apri `index.html` in un editor
2. Per testare nel browser desktop: un semplice server statico basta (`python3 -m http.server` nella cartella, poi apri `localhost:8000`). **Attenzione**: sensori (DeviceOrientation/Motion) e spesso anche GPS ad alta precisione richiedono un contesto reale su dispositivo mobile — il desktop è utile solo per verificare che non ci siano errori JS e che la mappa carichi.
3. Per testare su iPhone davvero: serve HTTPS (Safari blocca Geolocation su `http://` e su `file://`). In sviluppo, il modo più comodo resta pushare su GitHub Pages e aprire l'URL pubblico da Safari — non da webview integrate in altre app (bug noto, vedi sotto).

## Setup chiave Google Maps (obbligatorio)

La mappa **non funziona** senza una chiave valida. Nel file, in fondo, c'è:
```html
<script src="https://maps.googleapis.com/maps/api/js?key=YOUR_GOOGLE_MAPS_API_KEY&v=weekly&libraries=places" defer></script>
```
Va sostituito `YOUR_GOOGLE_MAPS_API_KEY` con una chiave reale creata su [Google Cloud Console](https://console.cloud.google.com/), con **Maps JavaScript API** e **Directions API** abilitate sul progetto, **billing attivo** (richiesto anche per restare nel piano gratuito), e idealmente con restrizione **HTTP referrer** limitata al dominio GitHub Pages del progetto (`https://<utente>.github.io/*`) — la chiave finisce in un repo pubblico quindi la restrizione è l'unica vera protezione. Abilita anche la **Places API** (⚠️ non "Places API (New)": sono due prodotti Google distinti — il widget usato nel codice, `google.maps.places.Autocomplete`, richiede la Places API "legacy". Abilitare per sbaglio solo quella "(New)" causa un `ApiTargetBlockedMapError` in console e il popup "Questa pagina non carica correttamente Google Maps" — già successo una volta, vedi HANDOFF.md) sullo stesso progetto/chiave se vuoi l'autocomplete indirizzi nel navigatore (vedi sotto) — senza, i campi indirizzo degradano a testo libero senza errori.

## Deploy

GitHub Pages, repo **pubblico** (Pages su repo privati richiede piano Team/Enterprise). Settings → Pages → Deploy from a branch → `main` → `/ (root)`. `index.html` deve stare nella root del repo (non in una sottocartella) perché GitHub Pages lo serve automaticamente come pagina principale.

## Come si usa (flusso utente reale)

1. Monta il telefono su supporto, landscape, con la sezione inferiore destra dello schermo intenzionalmente **dietro/coperta dal quadro strumenti della moto** (vincolo fisico noto e voluto — vedi sezione Layout, zona `.cockpit-void`).
2. Apri l'URL GitHub Pages **direttamente in Safari** (non dentro webview di altre app — vedi Problemi noti).
3. Tocca la linguetta fissa in basso al centro (`#controlHandle`) per aprire il **pannello comandi**, poi **Calibra** a moto ferma e in verticale: azzera l'offset di piega/beccheggio (utile se il supporto non è perfettamente livellato) e resetta la stima di gravità dell'accelerometro.
4. Tocca **Avvia** nel pannello comandi: richiede i permessi sensori/posizione (se non già concessi), inizia a tracciare GPS e a loggare i dati, avvia il timer di sessione.
5. Guida. Le quattro card a barra (piega, beccheggio, G laterale, G longitudinale) nelle due colonne laterali sono pensate per essere lette a colpo d'occhio anche a velocità sostenuta.
6. Facoltativo: tocca l'icona 🧭 sulla mappa per impostare una destinazione — disegna il percorso come linea evidenziata e attiva la barra navigatore sopra la mappa (manovra, distanza, ETA).
7. A fine giro: apri il pannello comandi, tocca **Ferma** (richiede conferma via `confirm()` nativo, per evitare stop accidentali), poi **CSV** per esportare i dati registrati (scarica un file via Safari, l'utente lo recupera dall'app File).

## Funzionalità implementate

### Sensori e calcolo dati

- **Piega (roll)**: letta da `deviceorientation` (`beta`/`gamma`), **compensata per l'orientamento fisico dello schermo** (`screen.orientation.angle`) tramite la funzione `compensateOrientation()` — necessario perché il telefono può essere montato sia verticale che orizzontale e i valori grezzi del sensore non seguono automaticamente la rotazione dell'interfaccia.
- **Beccheggio (pitch)**: NON più letto da `deviceorientation.beta` (limite noto: gimbal lock/salti discontinui oltre ~90° di inclinazione, vedi sotto). Calcolato invece in `handleMotion()` da `computePitchFromGravity()`, a partire dal vettore di gravità grezzo e istantaneo (non dal filtrato `gEst`, vedi sotto) e compensato per l'orientamento schermo come la piega. `handleOrientation()` (l'handler di `deviceorientation`) si occupa quindi solo di piega/roll.
- **Accelerazione/frenata**: da `devicemotion.accelerationIncludingGravity`, con **filtro passa-basso per stimare e sottrarre la componente di gravità** (tecnica standard tipo "gravity sensor" software, vedi `gEst` e `G_ALPHA = 0.85` nel codice), poi compensata per orientamento schermo (`compensateAccelXY()`). L'asse Y del dispositivo (dopo compensazione) è trattato come longitudinale (avanti/freno, `fwdG`), X come laterale (`latG`), Z come verticale (`vertG`).
- **Indice "Assetto"/comfort**: RMS mobile dell'accelerazione verticale su una finestra di 40 campioni (`vertBuf`/`VERT_BUF_LEN`), mappato 0–100. **Stima**, non una misura reale di smorzamento sospensioni (richiederebbe un sensore sulla ruota). Calcolato internamente per il punteggio ma non mostrato come tile a sé (rimosso su richiesta utente prima del redesign v2, ancora così dopo).
- **Punteggio di guida**: tre sotto-punteggi con media mobile esponenziale (`SCORE_ALPHA = 0.03`): fluidità accelerazione/frenata (40%), pulizia in piega — basata sulla velocità angolare del roll (35%), compostezza/comfort verticale (25%). Disponibile come mini-tile "Punteggio guida" (vedi sezione Layout).
- **Calibrazione**: il bottone "Calibra" (ora nel pannello comandi) cattura gli ultimi valori grezzi (`lastRawRoll`, `lastRawPitch`, `lastRawAG`) e li usa come nuovo zero (`leanOffset`, `pitchOffset`, reset di `gEst`). I sensori restano "sempre attivi" una volta concessi i permessi — non sono legati al ciclo Avvia/Ferma, che controlla solo GPS + logging (vedi `ensureSensors()` vs `start()`/`stop()`). Questo comportamento ha un effetto collaterale sul timer di sessione, vedi sezione Layout e Problemi noti.

### Card a barra: piega, beccheggio, G laterale, G longitudinale

Il vecchio design "badge + chevron" (piega/beccheggio) e la vecchia barra G-force verticale unica sono stati sostituiti dal redesign layout v2 con **quattro card identiche nello stile** (`.stat-card`, id `#cardLean`/`#cardPitch`/`#cardGLat`/`#cardGLong`), ciascuna composta da:
- un'etichetta (`.stat-card-label`: Piega / Beccheggio / G Laterale / G Longitudinale);
- un numero grande in Orbitron (`.stat-card-num`);
- per piega e beccheggio, una sottoetichetta tecnica di verso (`.stat-card-sub`: SINISTRA/DESTRA per la piega, SU/GIÙ per il beccheggio) — le due card G non hanno sottoetichetta, solo il valore firmato nel numero;
- una **barra orizzontale centrata sullo zero** (`.stat-bar-track`/`.stat-bar-fill`), riempita da `setBarFill(fillEl, value, maxScale)` — funzione unica condivisa dalle 4 card: valore positivo estende la barra a destra dello zero grafico, negativo a sinistra, su una scala fissa per card (±60° piega, ±45° beccheggio, ±1.5g G laterale, ±1.0g G longitudinale);
- tacche min/0/max sotto la barra (`.stat-bar-ticks`);
- una riga di massimi (`.stat-maxrow`): MAX SX/MAX DX per la piega, UP/DOWN per il beccheggio, un singolo TOP (valore assoluto) per ciascuna delle due card G.

Tutte e 4 sono **monocromatiche** tranne la card Piega oltre soglia (ambra 25°/rossa 40° su numero e sottoetichetta — soglie arbitrarie, non calibrate su dati reali); il beccheggio e le due G non hanno soglie colore.

- **Massimi separati per lato/verso**: `maxLeanSx`/`maxLeanDx` (piega), `maxPitchUp`/`maxPitchDown` (beccheggio), `maxGLat`/`maxGLong` (G, valore assoluto) — persistenti per tutta la sessione, si resettano a ogni **Avvia** (`start()`) o manualmente col pulsante **↺ Reset max** nel pannello comandi (richiede conferma via `confirm()` nativo).
- **Convenzione segno piega**: `rollDeg` negativo = destra (DX), positivo = sinistra (SX) — verso confermato su strada (era invertito nella prima versione del chevron, correzione persa e poi ripristinata, vedi commento in `updateLeanGauge()`).
- **Convenzione segno beccheggio**: positivo = su (SU). Se risulta invertito su strada, invertire il segno in `computePitchFromGravity()` (cambia `Math.atan2(-comp.y, ...)` in `Math.atan2(comp.y, ...)`).
- **Calcolo beccheggio**: da `computePitchFromGravity()`, basato sul vettore di gravità **grezzo e istantaneo** (`rx`/`ry`/`rz` da `accelerationIncludingGravity`, letto in `handleMotion()`) — **mai** sul vettore filtrato `gEst`, che serve solo a stimare la gravità "a riposo" per il calcolo dell'accelerazione lineare. Usare `gEst` per il beccheggio causava un bug osservato su strada: durante un'impennata sostenuta il filtro passa-basso "insegue" la nuova inclinazione trattandola come nuova gravità, facendo scendere il beccheggio verso 0 (per poi ripartire da capo) anche se il telefono restava inclinato. `beta` di `deviceorientation` non viene usato per lo stesso motivo: è un angolo di Eulero e soffre di gimbal lock/salti discontinui (es. ~-350°) durante un'inclinazione estrema. Per costruzione l'output di `computePitchFromGravity()` è matematicamente limitato a (-90°, 90°]: oltre i 90° reali il valore letto satura vicino a ±90° invece di continuare oltre (trade-off accettato).
- **G laterale/longitudinale — valore mostrato smussato**: il testo e la posizione della barra sono calcolati con una **media mobile esponenziale** separata per asse (`gLatDisplay`/`gLongDisplay`, `G_DISPLAY_ALPHA = 0.12`, aggiornata in `handleMotion()`) a partire da `latG`/`fwdG` grezzi — solo per la resa visiva, non per il punteggio guida che continua a usare i valori grezzi. I valori istantanei erano troppo "scattosi" (rumore accelerometro non filtrato) per essere leggibili a colpo d'occhio in marcia. A differenza del vecchio ghost "a scomparsa" (`makePeakHold`), qui non c'è comportamento a tempo: la barra segue sempre il valore EMA corrente, solo il TOP di sessione resta fisso finché non lo si azzera.

### Mappa e navigazione

- **Google Maps JS API**, stile custom **nero puro / bianco puro** (`NIGHT_STYLE`/`DAY_STYLE` nel codice, selezionati da `mapStyleForTheme()`) coerente col sistema di temi chiaro/scuro del resto dell'HUD — cambia dal vivo (`gmap.setOptions({styles:...})`) quando si tocca il toggle **Tema** nel pannello comandi, senza ricaricare la pagina.
- Mappa **orientata a nord fisso** (non ruota con la direzione di marcia). Scelta deliberata e non un compromesso tecnico dimenticato: ruotare l'intera mappa via CSS (come si faceva con la versione precedente basata su Leaflet+OpenStreetMap) nasconderebbe/distorcerebbe il logo Google e il link ai Termini, che Google richiede restino sempre visibili per contratto. La direzione di marcia è invece indicata dalla **freccia arancione che ruota** sopra la mappa fissa.
- **Ridimensionamento mappa via drag: rimosso.** Nella v1 del layout esisteva una maniglia (`#resizeHandle`) trascinabile tra mappa e colonna HUD, che aggiornava una CSS custom property `--map-pct` (persistita in `moto_map_pct`) in tempo reale. Il redesign layout v2 lo ha eliminato **deliberatamente** — vincolo esplicito del piano di redesign, non una regressione: la mappa ora occupa sempre tutto lo spazio verticale disponibile nella colonna centrale (`.col-map { flex:1 1 auto }`), mentre le due colonne laterali hanno larghezza fissa (168px, `.col-side { flex:0 0 168px }`). La custom property CSS `--map-pct` è rimasta dichiarata (inutilizzata, valore fisso `60%`) in `:root` — codice morto innocuo, nessun selettore CSS né riga JS la referenzia più.
- **Pan/zoom manuale + "follow mode"**: `gestureHandling: 'greedy'` (pan/pinch-zoom liberi, senza il suggerimento "usa due dita"). Un flag `mapFollowing` controlla se `updateMap()` ricentra/rizooma automaticamente sul GPS ad ogni fix: diventa `false` quando l'utente trascina la mappa (`dragstart`, scatta solo su interazione reale, mai su `setCenter`/`fitBounds` programmatici) o quando si imposta un percorso (per mostrarlo tutto via `fitBounds`, tappe comprese). Il pulsante 📍 (`#mapRecenterBtn`, appare solo quando `mapFollowing` è `false`) rimette `mapFollowing = true` e ricentra sull'ultima posizione nota. "Annulla percorso" ripristina il follow mode automaticamente. Questi due pulsanti (🧭 `#mapNavBtn` e 📍 `#mapRecenterBtn`) restano **overlay flottanti sopra la mappa stessa** — non sono stati toccati dal consolidamento della barra navigatore (vedi punto sotto), che riguarda solo le informazioni di avanzamento percorso.
- **Navigazione**: icona 🧭 apre un popover (`#navPanel`) con campo destinazione + tappe intermedie opzionali (pulsante "+ Aggiungi tappa"), tutti con **autocomplete Google Places** (richiede la Places API abilitata sul progetto Google Cloud dell'utente, sulla stessa chiave — se non abilitata, i campi degradano a testo libero senza errori). Il percorso è disegnato con un effetto **glow**: due `DirectionsRenderer` sovrapposti sulla stessa mappa (`directionsRendererGlow` largo/trasparente sotto, `directionsRenderer` nitido sopra), entrambi aggiornati con lo stesso risultato.
- **Istruzioni vocali**: Web Speech API (`speechSynthesis`, italiano), annuncio ad ogni manovra imminente (~150m prima, una sola volta per step) più un annuncio di conferma al click "Vai" (serve anche a sbloccare la sintesi vocale su iOS Safari per le chiamate successive). Toggle **Voce navigatore** ora nel pannello comandi (`#voiceToggle`), persistito in `localStorage` (`moto_voice`). La logica di avanzamento (`navSteps`/`navStepIndex`/`updateNavProgress()`) appiattisce tutte le `legs[].steps[]` del risultato Directions in una sequenza unica, con un annuncio extra ("Tappa raggiunta") al passaggio tra una tappa e la successiva.
- **Barra navigatore centrale** (`.nav-topbar`, `#navTopbar`, sopra la mappa nella colonna centrale, sempre visibile): sostituisce i vecchi overlay flottanti "pannello prossima manovra" + chip distanza/ETA che stavano sopra la mappa. In un'unica riga mostra: un chevron di manovra (`#navTopbarChevron`, ▶/◀/▲, mappato da `MANEUVER_CHEVRON` in base a `step.maneuver`), il testo istruzione (`#navTopbarText`, con la distanza alla prossima manovra in grassetto quando c'è un percorso attivo, es. "Tra **250 m** · Gira a destra su Via Roma"), la distanza residua totale del percorso (`#navTopbarDist`) e l'ETA (`#navTopbarEta`) — tutti aggiornati ad ogni fix GPS da `updateNavProgress()`/`updateRouteInfo()` (somma locale degli step non ancora completati, nessuna chiamata API aggiuntiva, non tiene conto del traffico in tempo reale). Senza percorso impostato la barra è in stato inattivo (classe `.nav-topbar.idle`, testo attenuato) con "Nessun percorso impostato".
- **Navigazione indipendente dalla registrazione telemetria**: funziona sia con **Avvia** premuto che senza.
- **Versione precedente (superata)**: prima di Google Maps c'era una minimappa con traccia GPS auto-disegnata (nessuna dipendenza esterna, funzionava offline) e poi una mappa OSM via Leaflet con rotazione CSS heading-up. Entrambe sostituite per limiti funzionali (niente routing reale) o di conformità (rotazione + attribuzione). Se in futuro serve una modalità completamente offline, quell'approccio è il punto di partenza da recuperare (vedi cronologia se necessario, ma il codice attuale non lo contiene più).

### Layout a tre colonne

Il layout HUD è stato ridisegnato in tre colonne fisse-elastiche (`.layout`, `display:flex; flex-direction:row`):

- **Colonna sinistra** (`.col-side.left`, `#colSideLeft`, 168px fissi): dall'alto, gli slot `#slotLeftTop` e `#slotLeftBottom` — di default contengono rispettivamente la card **Piega** e la card **G Laterale** — poi in fondo la mini-riga (`.mini-row`, due riquadri `#miniSlot1`/`#miniSlot2`, default **Sessione**/**Distanza**, vedi sotto).
- **Colonna centrale** (`.col-center`, flessibile, `flex:1 1 auto`): la barra navigatore (`.nav-topbar`) sopra la mappa (`.col-map`/`#gmap`), che occupa tutto lo spazio verticale restante.
- **Colonna destra** (`.col-side.right`, `#colSideRight`, 168px fissi): gli slot `#slotRightTop` e `#slotRightBottom` — di default contengono la card **Beccheggio** e la card **G Longitudinale** — poi in fondo `.cockpit-void`: una zona vuota (80px di altezza fissa, `pointer-events:none`, nessun contenuto), che rimpiazza la vecchia `.hud-bottom` come rappresentazione della porzione dello schermo fisicamente coperta dal quadro strumenti su alcune moto (vedi vincolo fisico sotto e Problemi noti). A differenza della vecchia `.hud-bottom`, in quella zona non ci sono più controlli critici da premere "alla cieca": sono stati spostati nel pannello comandi unico (vedi sotto), raggiungibile dalla linguetta fissa in basso al centro, fuori dalla zona coperta.
- **Landscape only**: invariato — se il telefono è in portrait, overlay "ruota il telefono" (`@media (orientation: portrait)`) al posto dell'interfaccia.

### Personalizzazione layout: scambio card e scelta mini-tile

- **Modalità modifica**: toggle "Modalità modifica" nel pannello comandi (`#editModeToggle`, Attiva/Disattiva). Quando attiva, aggiunge la classe `edit-mode` a `.app`, che rende visibili i pulsanti ⇄ (`.stat-swap-btn`, altrimenti `display:none`) su ciascuna delle 4 card grandi e sui 2 mini-tile. Il toggle stesso **non è persistito** (torna sempre "Disattiva" al refresh della pagina); solo il risultato delle scelte fatte in modalità modifica lo è.
- **Scambio delle 4 card grandi** (`cardLayout`, chiavi `leftTop`/`leftBottom`/`rightTop`/`rightBottom`, valori `lean`/`pitch`/`gLat`/`gLong`): tap su ⇄ di una card apre un picker generico (`openPicker()`, condiviso anche coi mini-tile) con le altre 3 metriche disponibili; scegliendone una, `swapCardInto()` **scambia le due posizioni** — è una permutazione stretta a 4 elementi, ogni metrica occupa sempre esattamente uno dei 4 slot, mai duplicata e mai assente. Lo scambio riappende gli elementi DOM reali nei nuovi slot (`applyCardLayout()`) e persiste in `localStorage` (`moto_card_layout`). `loadCardLayout()` valida il JSON salvato all'avvio: deve avere tutte e 4 le chiavi slot, ciascuna con uno dei 4 metric-id validi, tutti e 4 distinti (`Set` di dimensione 4) — altrimenti il salvataggio viene ignorato e si usa il default (`leftTop: lean, leftBottom: gLat, rightTop: pitch, rightBottom: gLong`).
- **Scelta dei 2 mini-tile** (`miniLayout`, chiavi `slot1`/`slot2`, valori tra `session`/`distance`/`speed`/`score`, `MINI_METRICS`): a differenza delle card grandi, è una **scelta libera 2-di-4, non una permutazione**. Tap su ⇄ di un riquadro apre lo stesso picker generico con **tutte e 4** le metriche (Sessione/Distanza/Velocità/Punteggio guida, `MINI_LABELS`), senza escludere quella già mostrata nell'altro riquadro — è quindi possibile (anche se poco utile) avere la stessa metrica in entrambi. Persistita in `localStorage` (`moto_mini_layout`); `loadMiniLayout()` valida solo che entrambi i valori salvati appartengano a `MINI_METRICS`, nessun controllo di unicità.
- Le due mini-tile mostrano `miniMetricValueText()` per la metrica assegnata al proprio slot: **Sessione** (mm:ss dall'ultimo Avvia, vedi sotto), **Distanza** (km, una cifra decimale, da `totalDistanceM`), **Velocità** (km/h, da `lastKmh`/GPS), **Punteggio guida** (`lastScore`, lo stesso punteggio calcolato per il punteggio complessivo di guida).

### Timer di sessione

- `sessionStartTime` viene impostato a `Date.now()` a ogni **Avvia** (`start()`) e la mini-tile "Sessione" si aggiorna una volta al secondo tramite `sessionIntervalId` (`setInterval(refreshMiniTiles, 1000)`) finché la registrazione è attiva. **Ferma** (`stop()`) ferma solo l'intervallo (`clearInterval`) — **non azzera `sessionStartTime`** — e il prossimo **Avvia** lo riporta a 00:00 assegnandogli un nuovo `Date.now()`.
- **Caveat scoperto durante lo smoke test del Task 8** (non presente nella descrizione originale del piano di redesign, non corretto in questo task perché fuori scope — solo documentazione/verifica, nessuna modifica funzionale): poiché i sensori restano "sempre attivi" indipendentemente da Avvia/Ferma (vedi sezione Sensori sopra), ogni evento `devicemotion` richiama comunque `handleMotion()` → `renderScore()` → `refreshMiniTiles()`, che ricalcola il tempo trascorso da `sessionStartTime` **anche a registrazione ferma**. Su un iPhone reale, dove `devicemotion` continua a scattare ad alta frequenza indipendentemente da Avvia/Ferma, il valore mostrato in "Sessione" **non resta effettivamente congelato** dopo **Ferma** come ci si aspetterebbe — continua silenziosamente ad avanzare finché non si preme di nuovo **Avvia**. L'apparenza di un valore "congelato" si osserva solo in assenza di eventi di movimento continui (tipicamente: test desktop senza sensore accelerometro reale) — verificato in questo task iniettando manualmente un evento `devicemotion` sintetico dopo **Ferma** in un browser headless: il tempo mostrato è avanzato comunque, da 00:02 a 00:04 con un solo evento iniettato dopo ~1.2s di attesa. "Distanza" (`totalDistanceM`) condivide lo stesso meccanismo/limite: viene accumulata in `handlePosition()` a ogni fix GPS senza controllare `recording`, quindi può a sua volta continuare a crescere dopo **Ferma** se il GPS resta attivo (es. navigazione in corso, `navActive`).

### Pannello comandi unico

Sostituisce sia i vecchi pulsanti fissi in `.hud-bottom` sia il popover "Impostazioni" separato della v1 del layout. Una linguetta fissa in basso al centro dello schermo (`#controlHandle`, 64×22px, sempre in primo piano, `z-index:899`) apre/chiude — al tap — un unico pannello a comparsa dal basso (`#controlPanel`, stesso pattern popover di `#navPanel`/`#pickerPanel`: backdrop semi-trasparente `#controlBackdrop` + pannello ancorato in basso) con tutti gli 8 controlli, in quest'ordine:
1. **Avvia/Ferma** (`#mainBtn`)
2. **Calibra** (`#calibBtn`)
3. **↺ Reset max** (`#resetMaxBtn`) e **⭳ CSV** (`#exportBtn`), affiancati
4. area di stato testuale (`#logInfo`)
5. **Tema** (`#themeToggle`, Notturno/Diurno)
6. **Voce navigatore** (`#voiceToggle`, Attiva/Disattivata)
7. **Modalità modifica** (`#editModeToggle`, Attiva/Disattiva — abilita lo scambio card/mini-tile, vedi sopra)
8. **Chiudi** (`#controlClose`)

Il pannello comandi resta indipendente dal navigatore (`#navPanel`) e dal picker di scambio (`#pickerPanel`), che restano popover separati con lo stesso linguaggio grafico.

### Layout / UX pensata per l'uso in marcia

- **Landscape only**: se il telefono è in portrait, viene mostrato un overlay "ruota il telefono" (`@media (orientation: portrait)`) invece dell'interfaccia.
- **Vincolo fisico del quadro strumenti**: quando il telefono è montato su alcune moto, la porzione **in basso a destra dello schermo risulta fisicamente coperta dal quadro strumenti**. Nel redesign layout v2 questo vincolo è rappresentato dalla zona `.cockpit-void` in fondo alla colonna destra (vedi sopra) invece che dalla vecchia `.hud-bottom` con i pulsanti grandi — i controlli critici (Avvia/Ferma, Calibra) sono ora nel pannello comandi unico, raggiungibile dalla linguetta fissa in basso al centro dello schermo, che resta sempre fuori dalla zona coperta indipendentemente dal modello di moto/supporto.
- Font monospazio per i dati tecnici, Orbitron per i numeri "hero" (piega, beccheggio, G, punteggio) — tema "digitale/futuristico", griglia di sfondo sottile in stile blueprint. Sistema di **temi chiaro/scuro** (`:root[data-theme]`, token `--ink`/`--ink-dim`/`--hair`/`--bg`/`--bg2`/`--accent`): **notturno di default**, **diurno attivabile dal pannello comandi** (persistito in `localStorage`, vedi sopra). L'interfaccia è **volutamente monocromatica** in entrambi i temi; il colore compare solo come segnale di stato: soglie ambra/rossa sulla card Piega oltre 25°/40°, il puntino di stato rosso lampeggiante durante la registrazione, e la freccia arancione di direzione sulla mappa.
- Sfondo scuro **nero puro** (`--bg: #000000`), non un blu-nero attenuato — risparmio batteria reale su schermi OLED (pixel neri spenti).
- **Padding minimo per `env(safe-area-inset-*)`**: il body riserva solo un margine piatto minimo in alto/basso (2px) e un margine ridotto ai lati (`max(8px, env(...))`) — scelta deliberata per recuperare lo spazio che il sistema riserverebbe altrimenti per notch/home-indicator, che su un contenuto di sfondo come la mappa non serve davvero a proteggere nulla di critico.

## Formato export CSV

Colonne, una riga per ogni fix GPS ricevuto durante una sessione di registrazione:
```
timestamp, lat, lon, speed_kmh, heading_deg, lean_deg, pitch_deg, accel_fwd_g, accel_lat_g, accel_vert_g, comfort_idx, score
```
`accel_fwd_g`/`accel_lat_g`/`accel_vert_g` sono presi dall'ultimo campione `devicemotion` disponibile al momento del fix GPS (i due sensori non sono sincronizzati, GPS aggiorna a ~1Hz, motion molto più spesso — si prende sempre il valore più recente). **Questo formato è rimasto un vincolo esplicito del piano di redesign layout v2** (nessuna modifica alle colonne, all'ordine o ai nomi): verificato byte-per-byte identico tra la stringa header nel codice sorgente attuale e quella presente prima dell'inizio del redesign (commit `31c1331`).

## Problemi noti / cose da verificare su strada

1. **Verso del beccheggio non validato** — vedi sopra, correzione di una riga se necessario in `computePitchFromGravity()`.
2. **Apertura da webview integrata** — se l'app viene aperta tramite un link condiviso dentro un'app che usa una webview interna (non Safari "vero"), i permessi di sensori/posizione possono essere negati o limitati anche se il sito è servito in HTTPS. Va sempre aperta da Safari come sito a sé stante.
3. **Soglie del punteggio e dei colori warn/danger** (25°/40° piega, pesi 40/35/25 del punteggio) sono punti di partenza ragionevoli ma arbitrari, non calibrati su dati reali.
4. **Chiave Google Maps esposta lato client** — inevitabile per un'app client-side pura, ma **deve** avere la restrizione HTTP referrer impostata (vedi Setup), altrimenti chiunque trovi la chiave nel repo pubblico può usarla a proprie spese.
5. **Copertura del quadro strumenti**: le dimensioni esatte della zona `.cockpit-void` (80px di altezza, valore CSS fisso) sono una stima non validata su un dispositivo reale montato in moto — stessa categoria di caveat della vecchia nota sulle dimensioni di `.hud-bottom` nella v1 del layout, ora applicata alla nuova colonna destra. Da verificare/aggiustare su strada.
6. **Mappa offline**: con Google Maps, senza connessione dati la mappa non carica (tile scaricati al volo). Il resto dell'app (sensori, GPS, log, export) funziona comunque regolarmente.
7. **Nessun salvataggio persistente delle sessioni**: i dati registrati vivono solo in memoria (`logData` array) fino all'export CSV manuale — chiudere/ricaricare la pagina durante una registrazione perde tutto. Se serve resilienza (es. salvataggio incrementale), andrebbe aggiunto `localStorage`/IndexedDB.
8. **Bug cosmetico preesistente in `updateNavProgress()` (non introdotto né corretto dal redesign v2)**: quando si raggiunge la destinazione, il ramo di arrivo imposta `navTopbarText` a "Arrivato a destinazione" e svuota `navTopbarDist`/`navTopbarEta`, ma chiama subito dopo `updateRouteInfo()` — che, non trovando più step residui, li riscrive immediatamente a "0.0 km" e all'ora corrente invece di lasciarli vuoti. Effetto solo visivo (i due campi tornano popolati con valori non significativi anziché restare vuoti), individuato durante la review del redesign layout v2 ma lasciato "parcheggiato" perché preesistente all'app originale e fuori scope per questo piano.
9. **Timer di sessione non realmente "congelato" dopo Ferma su un dispositivo reale** — vedi sezione "Timer di sessione" sopra: la mini-tile Sessione (ed eventualmente Distanza) continua ad avanzare dopo **Ferma** finché i sensori/GPS restano attivi e generano eventi, cosa che avviene sempre su un iPhone reale con permessi già concessi. Scoperto durante lo smoke test del Task 8 (redesign layout v2), non corretto in questo task perché fuori scope (solo documentazione/verifica). Da valutare come possibile intervento futuro: azzerare esplicitamente `sessionStartTime`/congelare il valore mostrato in `stop()`.

## Possibili sviluppi futuri (non implementati)

- Vista riepilogo post-giro (mappa con traccia percorsa + grafici da CSV) — attualmente il CSV va analizzato altrove (Excel, ecc.).
- Salvataggio incrementale della sessione per resilienza a crash/ricarica.
- Calibrazione assistita con feedback visivo invece di un semplice tap.
- Modalità mappa offline (la vecchia traccia GPS auto-disegnata, o tile scaricati in anticipo).
- Correggere il congelamento reale del timer di sessione (e della distanza) dopo **Ferma** (vedi Problemi noti, punto 9).
