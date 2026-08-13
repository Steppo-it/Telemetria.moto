# Telemetria Moto — CLAUDE.md

Documento di contesto per Claude Code (o chiunque riprenda il progetto in VS Code). Contiene tutto quello che serve per capire cosa è stato costruito, come, e perché, senza dover rileggere l'intera cronologia della chat originale.

## Cos'è

Una PWA (single-page, single-file) per iPhone che, montata sul cruscotto/manubrio di una moto, mostra e registra in tempo reale: angolo di piega, beccheggio, accelerazione/frenata, velocità GPS, un punteggio di guida calcolato, e una mappa di navigazione con percorso evidenziato. Pensata per essere usata **in marcia**, con telefono fisso su supporto, schermo sempre visibile, landscape only.

Non è un progetto con build system, bundler o package manager: è **un solo file HTML** (`index.html`) con CSS e JS inline, pensato per essere servito staticamente via GitHub Pages. Nessuna dipendenza da installare lato sviluppo.

## Stack tecnico

- **Nessun framework** — HTML/CSS/JS vanilla, tutto in un file.
- **Google Maps JavaScript API + Directions API** — mappa e calcolo percorso (richiede una API key dell'utente, vedi sotto).
- **Geolocation API** (`navigator.geolocation.watchPosition`) — posizione, velocità, direzione (heading).
- **DeviceOrientationEvent / DeviceMotionEvent** — piega, beccheggio, accelerazione (richiedono permesso esplicito su iOS 13+ via `requestPermission()`, deve partire da un tap diretto dell'utente).
- **localStorage** — persistenza di due preferenze utente: dimensione della mappa (`moto_map_pct`, aggiornata trascinando `#resizeHandle`) e tema chiaro/scuro (`moto_theme`, `dark`/`light`, impostato dal toggle in Impostazioni e riletto anche prima del rendering, in un piccolo `<script>` in `<head>`, per evitare un flash del tema sbagliato). Nota: questo NON è un artifact di Claude.ai, gira su una pagina servita esternamente via GitHub Pages, quindi `localStorage` è pienamente supportato (a differenza degli artifact in claude.ai dove è vietato).
- **Font esterni**: Google Fonts (Orbitron per i numeri grandi/display, JetBrains Mono per i dati, Inter per testo secondario).
- **Hosting**: GitHub Pages (repo pubblico — Pages su repo privati richiede un piano a pagamento).

## Struttura del file

`index.html` (~740 righe) è organizzato in tre blocchi:
1. `<style>` — tutte le variabili CSS in `:root` (colori, font) + layout
2. `<body>` — markup statico di tutti i pannelli/gauge/popover
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
Va sostituito `YOUR_GOOGLE_MAPS_API_KEY` con una chiave reale creata su [Google Cloud Console](https://console.cloud.google.com/), con **Maps JavaScript API** e **Directions API** abilitate sul progetto, **billing attivo** (richiesto anche per restare nel piano gratuito), e idealmente con restrizione **HTTP referrer** limitata al dominio GitHub Pages del progetto (`https://<utente>.github.io/*`) — la chiave finisce in un repo pubblico quindi la restrizione è l'unica vera protezione. Abilita anche la **Places API** sullo stesso progetto/chiave se vuoi l'autocomplete indirizzi nel navigatore (vedi sotto) — senza, i campi indirizzo degradano a testo libero senza errori.

## Deploy

GitHub Pages, repo **pubblico** (Pages su repo privati richiede piano Team/Enterprise). Settings → Pages → Deploy from a branch → `main` → `/ (root)`. `index.html` deve stare nella root del repo (non in una sottocartella) perché GitHub Pages lo serve automaticamente come pagina principale.

## Come si usa (flusso utente reale)

1. Monta il telefono su supporto, landscape, con la sezione inferiore destra dello schermo intenzionalmente **dietro/coperta dal quadro strumenti della moto** (vincolo fisico noto e voluto — vedi sezione Layout).
2. Apri l'URL GitHub Pages **direttamente in Safari** (non dentro webview di altre app — vedi Problemi noti).
3. Tocca **Calibra** a moto ferma e in verticale: azzera l'offset di piega/beccheggio (utile se il supporto non è perfettamente livellato) e resetta la stima di gravità dell'accelerometro.
4. Tocca **Avvia**: richiede i permessi sensori/posizione (se non già concessi), inizia a tracciare GPS e a loggare i dati.
5. Guida. I gauge grandi (piega, G-force, beccheggio) sono pensati per essere leggibili a colpo d'occhio anche a velocità sostenuta.
6. Facoltativo: tocca l'icona 🧭 sulla mappa per impostare una destinazione — disegna il percorso come linea evidenziata.
7. A fine giro: **Ferma** (richiede conferma via `confirm()` nativo, per evitare stop accidentali), poi **CSV** per esportare i dati registrati (scarica un file via Safari, l'utente lo recupera dall'app File).

## Funzionalità implementate

### Sensori e calcolo dati

- **Piega (roll)**: letta da `deviceorientation` (`beta`/`gamma`), **compensata per l'orientamento fisico dello schermo** (`screen.orientation.angle`) tramite la funzione `compensateOrientation()` — necessario perché il telefono può essere montato sia verticale che orizzontale e i valori grezzi del sensore non seguono automaticamente la rotazione dell'interfaccia.
- **Beccheggio (pitch)**: NON più letto da `deviceorientation.beta` (limite noto: gimbal lock/salti discontinui oltre ~90° di inclinazione, vedi sotto). Calcolato invece in `handleMotion()` da `computePitchFromGravity()`, a partire dal vettore di gravità stimato (`gEst`) e compensato per l'orientamento schermo come la piega. `handleOrientation()` (l'handler di `deviceorientation`) si occupa quindi solo di piega/roll.
- **Accelerazione/frenata**: da `devicemotion.accelerationIncludingGravity`, con **filtro passa-basso per stimare e sottrarre la componente di gravità** (tecnica standard tipo "gravity sensor" software, vedi `gEst` e `G_ALPHA = 0.85` nel codice), poi compensata per orientamento schermo (`compensateAccelXY()`). L'asse Y del dispositivo (dopo compensazione) è trattato come longitudinale (avanti/freno), X come laterale, Z come verticale.
- **Indice "Assetto"/comfort**: RMS mobile dell'accelerazione verticale su una finestra di 40 campioni, mappato 0–100. **Stima**, non una misura reale di smorzamento sospensioni (richiederebbe un sensore sulla ruota). Calcolato internamente per il punteggio ma non più mostrato come tile a sé (rimosso su richiesta utente).
- **Punteggio di guida**: tre sotto-punteggi con media mobile esponenziale (`SCORE_ALPHA = 0.03`): fluidità accelerazione/frenata (40%), pulizia in piega — basata sulla velocità angolare del roll (35%), compostezza/comfort verticale (25%).
- **Calibrazione**: il bottone "Calibra" cattura gli ultimi valori grezzi (`lastRawRoll`, `lastRawPitch`, `lastRawAG`) e li usa come nuovo zero (`leanOffset`, `pitchOffset`, reset di `gEst`). I sensori restano "sempre attivi" una volta concessi i permessi — non sono legati al ciclo Avvia/Ferma, che controlla solo GPS + logging (vedi `ensureSensors()` vs `start()`/`stop()`).

### Gauge "badge + chevron" (piega e beccheggio)

Niente più sagoma di moto: ogni gauge è un chevron di verso (▶/◀ per la piega, ▲/▼ per il beccheggio) + numero grande (Orbitron) + sottoetichetta tecnica, monocromatici tranne la piega oltre soglia (ambra 25°/rossa 40° — soglie arbitrarie, non calibrate su dati reali). Il beccheggio non ha soglie colore.

- **Massimi separati per lato/verso**: `maxLeanSx`/`maxLeanDx` per la piega, `maxPitchUp`/`maxPitchDown` per il beccheggio — persistenti per tutta la sessione, si resettano a ogni **Avvia** (`start()`) o manualmente col pulsante **↺ Reset max** (richiede conferma via `confirm()` nativo, per evitare azzeramenti accidentali durante la guida).
- **Convenzione segno**: `rollDeg` negativo = destra (DX), positivo = sinistra (SX) per la piega — verso confermato su strada (era invertito nella prima versione del chevron: `updateLeanGauge()` leggeva il segno di `rollDeg` direttamente, perdendo la correzione `rotate(${-rollDeg}...)` che la vecchia sagoma SVG applicava per lo stesso motivo). Beccheggio: positivo = su (SU). Se il beccheggio risulta invertito su strada, inverti il segno in `computePitchFromGravity()` (cambia `Math.atan2(-comp.y, ...)` in `Math.atan2(comp.y, ...)`).
- **Calcolo beccheggio**: da `computePitchFromGravity()`, basato sul vettore di gravità **grezzo e istantaneo** (`rx`/`ry`/`rz` da `accelerationIncludingGravity`, letto in `handleMotion()`) — **mai** sul vettore filtrato `gEst`, che invece serve solo a stimare la gravità "a riposo" per il calcolo dell'accelerazione lineare. Usare `gEst` per il beccheggio causava un bug osservato su strada: durante un'impennata sostenuta il filtro passa-basso "insegue" la nuova inclinazione trattandola come nuova gravità, facendo scendere il beccheggio verso 0 (per poi ripartire da capo) anche se il telefono restava inclinato. `beta` di `deviceorientation` non viene usato per lo stesso motivo del beccheggio: è un angolo di Eulero e soffre di gimbal lock/salti discontinui (es. ~-350°) durante un'inclinazione estrema.

### G-force (accelerazione/frenata)

Barra **verticale** (`.gforce-bar`) con uno sfondo a **gradiente statico fisso** (blu in alto → verde-acqua → grigio neutro al centro/zero → ambra → rosso in basso) — non si riempie né si svuota, il gradiente è sempre tutto visibile. Un solo marcatore a scomparsa (`#gGhost`) si sposta lungo la barra per indicare il picco recente: sopra il centro in accelerazione, sotto in frenata, con offset dal centro proporzionale a `g` (clampato a ±1g = ±50% di corsa). Mostra il valore solo in **g** (`#gforceVal`, es. "+0.42g") — niente più m/s². Come per gli altri gauge il ghost è "a scomparsa": resta pieno per ~1,4s poi sfuma in ~1s (`makePeakHold(1400, 1000)`) prima di riarmarsi sul valore corrente. Scelta deliberata: per la forza G è più utile vedere "quanto ho appena frenato" che il massimo dell'intera sessione.

Il valore mostrato (testo e posizione del marcatore) è **smussato con una media mobile esponenziale** (`gDisplay`, `G_DISPLAY_ALPHA = 0.12`, calcolata in `handleMotion()`) a partire dal `fwdG` grezzo — solo per la resa visiva, non per il punteggio guida che continua a usare `fwdG` grezzo. Il `fwdG` istantaneo era troppo "scattoso" (rumore accelerometro non filtrato) per essere leggibile a colpo d'occhio in marcia.

### Mappa e navigazione

- **Google Maps JS API**, stile custom **nero puro / bianco puro** (`NIGHT_STYLE`/`DAY_STYLE` nel codice, selezionati da `mapStyleForTheme()`) coerente col sistema di temi chiaro/scuro del resto dell'HUD — cambia dal vivo (`gmap.setOptions({styles:...})`) quando si tocca il toggle Tema in Impostazioni, senza ricaricare la pagina.
- Mappa **orientata a nord fisso** (non ruota con la direzione di marcia). Scelta deliberata e non un compromesso tecnico dimenticato: ruotare l'intera mappa via CSS (come si faceva con la versione precedente basata su Leaflet+OpenStreetMap) nasconderebbe/distorcerebbe il logo Google e il link ai Termini, che Google richiede restino sempre visibili per contratto. La direzione di marcia è invece indicata dalla **freccia arancione che ruota** sopra la mappa fissa.
- **Ridimensionabile via drag**: una maniglia (`#resizeHandle`) tra mappa e colonna HUD, trascinabile con Pointer Events, aggiorna una CSS custom property `--map-pct` in tempo reale. Persistita in `localStorage` (`moto_map_pct`).
- **Pan/zoom manuale + "follow mode"**: `gestureHandling: 'greedy'` (pan/pinch-zoom liberi, senza il suggerimento "usa due dita"). Un flag `mapFollowing` controlla se `updateMap()` ricentra/rizooma automaticamente sul GPS ad ogni fix: diventa `false` quando l'utente trascina la mappa (`dragstart`, scatta solo su interazione reale, mai su `setCenter`/`fitBounds` programmatici) o quando si imposta un percorso (per mostrarlo tutto via `fitBounds`, tappe comprese). Il pulsante 📍 (`#mapRecenterBtn`, appare solo quando `mapFollowing` è `false`) rimette `mapFollowing = true` e ricentra sull'ultima posizione nota. "Annulla percorso" ripristina il follow mode automaticamente.
- **Navigazione**: icona 🧭 apre un popover con campo destinazione + tappe intermedie opzionali (pulsante "+ Aggiungi tappa"), tutti con **autocomplete Google Places** (richiede la Places API abilitata sul progetto Google Cloud dell'utente, sulla stessa chiave — se non abilitata, i campi degradano a testo libero senza errori). Il percorso è disegnato con un effetto **glow**: due `DirectionsRenderer` sovrapposti sulla stessa mappa (`directionsRendererGlow` largo/trasparente sotto, `directionsRenderer` nitido sopra), entrambi aggiornati con lo stesso risultato.
- **Istruzioni vocali**: Web Speech API (`speechSynthesis`, italiano), annuncio ad ogni manovra imminente (~150m prima, una sola volta per step) più un annuncio di conferma al click "Vai" (serve anche a sbloccare la sintesi vocale su iOS Safari per le chiamate successive). Toggle 🔊 nel popover, persistito in `localStorage` (`moto_voice`). La logica di avanzamento (`navSteps`/`navStepIndex`/`updateNavProgress()`) appiattisce tutte le `legs[].steps[]` del risultato Directions in una sequenza unica, con un annuncio extra ("Tappa raggiunta") al passaggio tra una tappa e la successiva.
- **Pannello prossima manovra**: badge compatto sulla mappa (stesso linguaggio grafico chevron dei gauge piega/beccheggio) con icona di manovra, testo istruzione, distanza alla manovra — aggiornato ad ogni fix GPS. Un chip separato vicino a 🧭 mostra distanza/ETA rimanenti (somma locale degli step non ancora completati, nessuna chiamata API aggiuntiva — non tiene conto del traffico in tempo reale).
- **Navigazione indipendente dalla registrazione telemetria**: funziona sia con **Avvia** premuto che senza.
- **Versione precedente (superata)**: prima di Google Maps c'era una minimappa con traccia GPS auto-disegnata (nessuna dipendenza esterna, funzionava offline) e poi una mappa OSM via Leaflet con rotazione CSS heading-up. Entrambe sostituite per limiti funzionali (niente routing reale) o di conformità (rotazione + attribuzione). Se in futuro serve una modalità completamente offline, quell'approccio è il punto di partenza da recuperare (vedi cronologia se necessario, ma il codice attuale non lo contiene più).

### Layout / UX pensata per l'uso in marcia

- **Landscape only**: se il telefono è in portrait, viene mostrato un overlay "ruota il telefono" (`@media (orientation: portrait)`) invece dell'interfaccia.
- **Tre zone funzionali**, vincolo derivato da un caso reale: quando il telefono è montato su alcune moto, la porzione **in basso a destra dello schermo risulta fisicamente coperta dal quadro strumenti**. Quella zona (`.hud-bottom`) contiene quindi i controlli più critici — Avvia/Ferma, Calibra — resi **grandi e ben distanziati apposta per essere premuti "alla cieca"**, per tatto, senza bisogno di vederli. "Impostazioni" e "CSV" sono più piccoli e in fondo, perché vengono usati solo a telefono staccato dal supporto.
- Font monospazio per i dati tecnici, Orbitron per i numeri "hero" (piega, punteggio) — tema "digitale/futuristico", griglia di sfondo sottile in stile blueprint. Sistema di **temi chiaro/scuro** (`:root[data-theme]`, token `--ink`/`--ink-dim`/`--hair`/`--bg`/`--bg2`/`--accent`): **notturno di default**, **diurno attivabile in Impostazioni** (persistito in `localStorage`, vedi sopra). L'interfaccia è **volutamente monocromatica** in entrambi i temi — l'unica UI sempre colorata è la barra G-force (gradiente blu/verde/ambra/rosso fisso); il colore compare altrove solo come segnale di stato: soglie ambra/rossa sulla piega oltre 25°/40° e il puntino di stato rosso lampeggiante durante la registrazione. Sfondo scuro **nero puro** (`--bg: #000000`), non un blu-nero attenuato — risparmio batteria reale su schermi OLED (pixel neri spenti).
- **Padding minimo per `env(safe-area-inset-*)`**: il body riserva solo un margine piatto minimo in alto/basso (2px) e un margine ridotto ai lati (`max(8px, env(...))`) — scelta deliberata per recuperare lo spazio che il sistema riserverebbe altrimenti per notch/home-indicator, che su un contenuto di sfondo come la mappa non serve davvero a proteggere nulla di critico.

## Formato export CSV

Colonne, una riga per ogni fix GPS ricevuto durante una sessione di registrazione:
```
timestamp, lat, lon, speed_kmh, heading_deg, lean_deg, pitch_deg, accel_fwd_g, accel_lat_g, accel_vert_g, comfort_idx, score
```
`accel_fwd_g`/`accel_lat_g`/`accel_vert_g` sono presi dall'ultimo campione `devicemotion` disponibile al momento del fix GPS (i due sensori non sono sincronizzati, GPS aggiorna a ~1Hz, motion molto più spesso — si prende sempre il valore più recente).

## Problemi noti / cose da verificare su strada

1. **Verso del beccheggio non validato** — vedi sopra, correzione di una riga se necessario in `computePitchFromGravity()`.
2. **Apertura da webview integrata** — se l'app viene aperta tramite un link condiviso dentro un'app che usa una webview interna (non Safari "vero"), i permessi di sensori/posizione possono essere negati o limitati anche se il sito è servito in HTTPS. Va sempre aperta da Safari come sito a sé stante.
3. **Soglie del punteggio e dei colori warn/danger** (25°/40° piega, 0.30g accelerazione/frenata, pesi 40/35/25 del punteggio) sono punti di partenza ragionevoli ma arbitrari, non calibrati su dati reali.
4. **Chiave Google Maps esposta lato client** — inevitabile per un'app client-side pura, ma **deve** avere la restrizione HTTP referrer impostata (vedi Setup), altrimenti chiunque trovi la chiave nel repo pubblico può usarla a proprie spese.
5. **Copertura del quadro strumenti**: le dimensioni/posizioni esatte dei bottoni grandi in `.hud-bottom` sono state tarate su un caso reale specifico (foto fornita durante lo sviluppo) ma potrebbero necessitare aggiustamenti fini su altre moto/supporti.
6. **Mappa offline**: con Google Maps, senza connessione dati la mappa non carica (tile scaricati al volo). Il resto dell'app (sensori, GPS, log, export) funziona comunque regolarmente.
7. **Nessun salvataggio persistente delle sessioni**: i dati registrati vivono solo in memoria (`logData` array) fino all'export CSV manuale — chiudere/ricaricare la pagina durante una registrazione perde tutto. Se serve resilienza (es. salvataggio incrementale), andrebbe aggiunto `localStorage`/IndexedDB.

## Possibili sviluppi futuri (non implementati)

- Vista riepilogo post-giro (mappa con traccia percorsa + grafici da CSV) — attualmente il CSV va analizzato altrove (Excel, ecc.).
- Salvataggio incrementale della sessione per resilienza a crash/ricarica.
- Calibrazione assistita con feedback visivo invece di un semplice tap.
- Modalità mappa offline (la vecchia traccia GPS auto-disegnata, o tile scaricati in anticipo).
