# HUD layout v2 — sinistra/destra/centro, card personalizzabili — design

Data: 2026-08-15

## Ambito

Ristruttura completa del cruscotto (non della mappa, non del navigatore in sé): passa da "mappa grande + colonna HUD stretta" a un layout a tre zone ispirato a un riferimento fornito dall'utente (dashboard "Telemetry Pro"), con quattro card grandi (piega, beccheggio, G laterale, G longitudinale) posizionate a sinistra/destra della mappa, riorganizzabili dall'utente. Include anche: nuovi dati di sessione mai tracciati finora (timer, top G), un pannello comandi unico che consolida tutti i controlli esistenti, un passaggio di leggibilità/tap-target su tutta la UI, e il rebrand del nome app.

**Fuori scope esplicito**: restyling visivo della mappa (stile attuale nero/bianco puro invariato — rimandato a un intervento futuro), bussola/rotazione mappa (già fuori scope da spec precedenti), qualunque modifica al formato CSV.

## Layout

Tre zone, landscape (invariato: app resta landscape-only):

- **Colonna sinistra** (larghezza fissa, es. ~160px): due card grandi impilate, di default **Piega** (sopra) e **G Laterale** (sotto). Sotto le due card, una mini-riga a due tile: **Sessione** e **Distanza**.
- **Colonna centrale** (spazio rimanente): in alto una **barra navigatore** compatta (sempre presente, non solo quando un percorso è attivo — mostra stato "nessun percorso" quando inattivo), sotto la **mappa** (stile invariato, non toccato in questo intervento).
- **Colonna destra** (stessa larghezza della sinistra): due card grandi impilate, di default **Beccheggio** (sopra) e **G Longitudinale** (sotto). Sotto le due card, una **zona vuota generosa**, non interattiva, riservata alla copertura del quadro strumenti — altezza di partenza generosa (es. ~80px, più del semplice "angolo" di prima), da tarare con un test reale sul mezzo dell'utente non appena possibile.

La barra navigatore in colonna centrale **sostituisce** i due overlay che oggi galleggiano sopra la mappa (pannello "prossima manovra" in basso a sinistra sulla mappa, chip "distanza/ETA" in alto a destra sulla mappa) — stessa logica/dati (`navSteps`, `chevronForManeuver`, `updateNavProgress`, ecc. — invariati), nuova collocazione unica e più prominente.

## Le quattro card grandi

Stile "gauge a barra" ispirato al riferimento fornito, **non** più badge+chevron:

- Etichetta piccola (es. "PIEGA"), numero grande (invariato come ordine di grandezza rispetto all'attuale, non rimpicciolire), sotto-etichetta di segno/verso (es. "SINISTRA"/"DESTRA" per la piega, "SU"/"GIÙ" per il beccheggio — assenti per le due card G, che mostrano solo il segno nel numero).
- Barra orizzontale con riempimento dal centro verso il valore corrente, scala graduata sotto (min/0/max, es. "60 · 0 · 60" per la piega, "-1.5 · 0 · 1.5" per la G laterale).
- Riga finale con il/i valore/i massimo/i di sessione: piega → **MAX SX / MAX DX**, beccheggio → **UP / DOWN** (nomenclatura invariata rispetto a oggi), G laterale → **TOP** (nuovo), G longitudinale → **TOP** (nuovo).
- **Nessun bordo, nessun glow**: le card si distinguono dallo sfondo nero solo per un leggerissimo contrasto di sfondo (stesso principio "monocromatico, niente cornici pesanti" già adottato nel redesign HUD precedente). Colore acceso solo dove già previsto oggi (soglia piega 25°/40°, se applicabile al nuovo stile a barra — la barra e il numero cambiano colore oltre soglia, stesso trigger di oggi).

Le soglie/colori/segno di piega e beccheggio, il calcolo del beccheggio da vettore di gravità grezzo, tutta la logica sensori sottostante: **invariati**. Cambia solo la resa visiva (da chevron+numero a barra graduata+numero) e l'aggiunta delle righe TOP per le due G.

**Nota**: la card "G Laterale" mostra `latG`, un valore già calcolato in `handleMotion()` e già presente nell'export CSV, ma **mai mostrato a schermo finora** — è quindi un dato nuovo per l'utente anche se il calcolo esiste da tempo. La card "G Longitudinale" mostra lo stesso `fwdG` già usato dall'attuale barra G verticale (accelerazione/frenata) — **quella barra verticale viene rimossa/sostituita** da questa card, non affiancata: `updateGforceGauge()`, `.gforce-bar`, `.gforce-marker`, `gDisplay` vengono ripensati come logica della nuova card "G Longitudinale" (stessa media mobile esponenziale già in uso per la fluidità, stesso peak-hold per il marcatore, solo nel nuovo stile a barra orizzontale con scala anziché verticale).

## Nuovi dati di sessione

Non esistevano prima di questo intervento, seguono lo stesso pattern (reset a ogni **Avvia**, persistono fino al prossimo Avvia):

- **Timer di sessione**: `mm:ss` dal momento in cui si preme Avvia. Si ferma (non azzera) su Ferma, mostrando il tempo totale della sessione appena conclusa. Si azzera al prossimo Avvia.
- **Top G laterale** e **Top G longitudinale**: massimo valore assoluto di `latG`/`fwdG` raggiunto in sessione — stesso pattern di `maxLeanSx`/`maxLeanDx`/`maxPitchUp`/`maxPitchDown` già esistenti (variabili di stato aggiornate ad ogni campione `devicemotion`, azzerate in `start()`).

## Personalizzazione (scambio card)

- **Modalità modifica**: toggle nel pannello comandi (vedi sotto). Quando attiva, su ognuna delle 4 card grandi compare un piccolo pulsante **⇄** (nascosto quando la modalità è disattiva).
- Toccando ⇄ su una card si apre un elenco con gli altri 3 tipi di dato disponibili (Piega, Beccheggio, G Laterale, G Longitudinale, esclusi quello già mostrato dalla card toccata). Selezionandone uno, **le due card si scambiano di posto** — il tipo scelto occupa lo slot toccato, il tipo che c'era prima va a occupare lo slot dove si trovava il tipo appena scelto. Sempre tutti e 4 i dati visibili, mai duplicati, mai assenti.
- Stesso meccanismo per i due mini-tile **Sessione/Distanza**: elenco di scelta con **Sessione, Distanza, Velocità, Punteggio guida** (4 opzioni per 2 slot — qui si accetta la possibilità di scegliere lo stesso dato in entrambi gli slot, meno critico che per le 4 card grandi).
- La disposizione scelta (quale dato in quale dei 4 slot grandi + quale dato nei 2 mini-tile) è **persistita in `localStorage`**, stesso pattern delle preferenze già esistenti (`moto_theme`, `moto_map_pct`, `moto_voice`).
- Il tracciamento dei valori (max, top, ecc.) resta legato al **dato**, non allo slot — spostare una card non azzera/altera i suoi massimi.

## Pannello comandi unico

Sostituisce sia l'attuale zona pulsanti fissa in basso (`.hud-bottom`) sia l'attuale popover Impostazioni, consolidando tutto in un solo pannello "a comparsa":

- **Apertura**: linguetta fissa (posizione facilmente individuabile anche senza guardare, es. centrale in basso) sempre visibile, invariata nella funzione di "punto fisso da trovare al tatto" che nel design precedente avevano i pulsanti grandi.
- **Contenuto**: Avvia/Ferma, Calibra, Reset max, CSV, toggle Tema, toggle Voce, toggle **Modalità modifica** (nuovo).
- Il popover **Navigatore** (indirizzo, tappe, autocomplete) resta separato e invariato nell'accesso — icona 🧭 sulla barra di navigazione/mappa, non confluisce nel pannello comandi (flusso di data-entry distinto da un pannello di controlli rapidi).
- Nota di sicurezza già discussa e accettata dall'utente: mettere anche Avvia/Ferma dentro il pannello a comparsa (invece di un pulsante fisso "alla cieca" come nel design precedente) riduce la garanzia di poter fermare la registrazione senza guardare lo schermo. Scelta consapevole dell'utente, non un oversight.

## Leggibilità e tap-target

Passata di revisione applicata a tutta la nuova UI (card, pannello comandi, picker di scambio, barra navigatore), non solo ai numeri dei gauge:

- Numeri principali delle 4 card: dimensione minima paragonabile o superiore agli attuali badge piega/beccheggio (non un downgrade).
- Aree toccabili (pulsante ⇄, voci del picker, pulsanti del pannello comandi) dimensionate per l'uso con guanti/in movimento, non per precisione da mouse — stesso principio già applicato nell'intervento di ingrandimento font della sessione precedente, esteso ora ai nuovi elementi interattivi (picker, ⇄, linguetta del pannello).

## Rebrand

Il nome mostrato in app passa da "TELEMETRIA.MOTO" a **"TELAMETRIA"** (titolo principale) con **"By TelaStampiamo"** in piccolo accanto/sotto, nella topbar. Nessun logo/immagine da integrare (l'utente non ha fornito il file del logo TelaStampiamo) — solo trattamento tipografico.

## Note di implementazione

- Nessuna nuova dipendenza esterna.
- Riuso del sistema di temi/token CSS esistente (`--ink`, `--ink-dim`, `--hair`, `--bg`, `--bg2`, `--accent`, `--blue-glow`, ecc.) — le nuove card e il nuovo pannello comandi si tema-tizzano con gli stessi custom property, nessun nuovo colore hardcoded.
- La logica di calcolo (piega, beccheggio, G, navigazione) è invariata: questo intervento è quasi interamente markup/CSS/stato-di-visualizzazione, con l'eccezione dei 4 nuovi valori di sessione (timer, top G laterale, top G longitudinale) che richiedono nuovo stato e nuovi punti di aggiornamento in `handleMotion()`/`start()`/`stop()`.
- Vincolo fisico "zona cockpit" confermato dall'utente più ampio di quanto assunto in precedenza — l'altezza esatta della zona vuota a destra è una stima di partenza, non un valore definitivo.
