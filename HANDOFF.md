# Handoff — Telemetria Moto

Data: 2026-08-13
Ultimo commit su `main`: `089beb6`
Stato: tutto pushato su GitHub, repo pubblico, deploy automatico via GitHub Pages.

Questo documento riassume il lavoro fatto in questa sessione, in ordine cronologico, e cosa resta aperto. Per il dettaglio tecnico di come funziona l'app oggi, la fonte di verità è **CLAUDE.md** (sempre tenuto aggiornato ad ogni intervento). Per il "perché" delle scelte di design, vedi i documenti in `docs/superpowers/specs/` e `docs/superpowers/plans/`.

## 1. Punto di partenza

App esistente: PWA single-file (`index.html`, HTML/CSS/JS vanilla, nessun build system) che mostra piega, beccheggio, accelerazione/frenata, velocità, punteggio guida e una mappa Google Maps con navigazione base, pensata per essere montata sul cruscotto della moto. Repo locale e GitHub non erano allineati (commit divergenti); primo intervento della sessione è stato sincronizzarli, includendo la chiave Google Maps già presente online.

## 2. Redesign del cruscotto (HUD)

- Spec: `docs/superpowers/specs/2026-08-13-hud-redesign-design.md`
- Piano: `docs/superpowers/plans/2026-08-13-hud-redesign.md`
- Commit chiave: `be5a143`…`7c8f59d` (poi hotfix in `8fa6f54`)

Cosa è cambiato, deciso passo passo con un giro di brainstorming (incluso un companion visivo nel browser per confrontare mockup):

- **Sistema di temi**: notturno di default, diurno attivabile in Impostazioni, persistito in `localStorage`.
- **Piega e beccheggio**: non più la vecchia sagoma SVG della moto, ma badge con chevron di verso (◀▶ / ▲▼) + numero grande + **Max separati per lato**: Max Sx/Dx per la piega, Max Up/Down per il beccheggio.
- **Forza G**: barra verticale (non più orizzontale) con gradiente fisso, marcatore a scomparsa.
- **Riga compatta** velocità/punteggio guida, pulsanti monocromatici, dissolvenza tra mappa e HUD invece di un bordo netto.
- **UI complessivamente monocromatica**: colore solo su barra G (sempre) e piega oltre soglia 25°/40° (segnale di sicurezza).

Una revisione finale su tutto il branch (fatta da un subagent con un modello più capace) ha trovato e corretto: CLAUDE.md che si contraddiceva sulla fonte del beccheggio, tema chiaro illeggibile in alcuni punti fuori dall'HUD, dissolvenza mappa che rischiava di coprire i link di attribuzione Google.

### 2.1 Bug scoperti dopo il redesign, corretti direttamente (commit `8fa6f54`)

Testando l'app vera, sono emersi tre problemi non colti dalle review:

1. **Freccia piega al contrario**: il verso del chevron/Max Sx-Dx era invertito rispetto alla realtà (bug di regressione: la vecchia sagoma SVG applicava una correzione di segno che si è persa passando al chevron). Corretto in `updateLeanGauge()`.
2. **Beccheggio che saliva, scendeva a 0, ripartiva**: causa reale trovata — il calcolo usava il vettore di gravità *filtrato* (`gEst`, pensato per un altro scopo: stimare la gravità "a riposo" per l'accelerazione lineare), che durante un'inclinazione sostenuta (impennata) finiva per "inseguire" la nuova inclinazione trattandola come nuova gravità. Corretto usando il vettore *grezzo e istantaneo* in `computePitchFromGravity()`.
3. **Forza G poco leggibile e "scattosa"**: aggiunta una media mobile esponenziale (`gDisplay`, solo per la resa visiva, non per il punteggio) + barra più larga/marcatore più visibile.

Nello stesso giro: font ingranditi ovunque nell'HUD (erano illeggibili in marcia), sfondo passato a **nero puro** (risparmio batteria OLED), padding ai bordi ridotto (recupera lo spazio riservato a notch/home-indicator, non serve a niente su un contenuto di sfondo come la mappa), nuovo pulsante **"Reset max"** (con conferma) per azzerare i picchi di piega/beccheggio, e **"Ferma"** ora richiede conferma prima di interrompere la registrazione.

## 3. Navigazione turn-by-turn + restyling mappa

- Spec: `docs/superpowers/specs/2026-08-13-nav-and-map-style-design.md`
- Piano: `docs/superpowers/plans/2026-08-13-nav-and-map-style.md`
- Commit chiave: `a8699b9`…`5eb7def` (poi estensione in `089beb6`)

Anche qui: brainstorming breve (audio in moto via interfono Bluetooth, Places API sì/no, tappe multiple sì/no, dettaglio istruzioni a schermo) → spec → piano a 5 task eseguiti da subagent con revisione ad ogni passo → revisione finale sul branch intero → un giro di fix.

- **Autocomplete indirizzi + tappe multiple**: Google Places Autocomplete sul campo destinazione e su ogni tappa aggiunta ("+ Aggiungi tappa"). Richiede che l'utente abbia abilitato la **Places API** sulla propria chiave Google Cloud (fuori dal controllo del codice — se non abilitata, i campi degradano a testo libero senza errori).
- **Istruzioni vocali**: Web Speech API in italiano, annuncio ~150m prima di ogni manovra + conferma al tap su "Vai" (serve anche a sbloccare l'audio su iOS). Toggle 🔊 on/off persistito.
- **Pannello prossima manovra**: badge compatto sulla mappa (stesso linguaggio grafico dei gauge) con icona/testo/distanza, più un chip separato con distanza/ETA rimanenti (somma locale degli step, non tiene conto del traffico).
- **Restyling mappa**: temi notturno (nero puro) / diurno (bianco puro) coerenti con l'HUD, cambiano dal vivo col toggle Tema; percorso disegnato con effetto glow (due `DirectionsRenderer` sovrapposti); mappa senza arrotondamento sui lati esterni (arriva a filo schermo).
- **Pan/zoom + follow mode** (aggiunto dopo, su richiesta esplicita): la mappa ora si può trascinare/zoomare liberamente (`gestureHandling:'greedy'`). Un flag `mapFollowing` controlla se la mappa si ricentra da sola sul GPS: si disattiva quando l'utente trascina la mappa o quando si imposta un percorso (che viene mostrato per intero via `fitBounds`, tappe comprese); un pulsante 📍 in basso a destra rimette la mappa in modalità "segui la mia posizione".

La revisione finale sul branch intero (eseguendo davvero il codice unito in un ambiente jsdom, non solo leggendolo) ha trovato e corretto: il pannello prossima manovra copriva il logo Google (vincolo di attribuzione già documentato), la navigazione **non** era davvero indipendente dalla registrazione telemetria come dichiarato nella spec/CLAUDE.md (il GPS partiva solo con "Avvia" — corretto con un pattern a conteggio di riferimenti, `ensureGps()`/`stopGpsIfIdle()`, condiviso tra registrazione e navigazione), e il chevron del pannello non seguiva il sistema di temi (illeggibile sulla mappa bianca diurna).

## 4. Problemi noti / aperti

1. **⚠️ Non risolto — errore "questa pagina non riesce a caricare Google Maps"**: segnalato dall'utente dopo aver abilitato la Places API. Causa più probabile: le **restrizioni API sulla chiave** in Google Cloud Console ora includono solo Places API e non più Maps JavaScript API / Directions API (va controllato in Console → Credenziali → la chiave → "Restrizioni API": devono esserci tutte e tre). Seconda causa possibile: fatturazione non attiva sul progetto. **Da verificare con l'utente prima di considerare chiusa la feature navigazione** — senza la mappa funzionante, autocomplete/percorso/glow non sono testabili.
2. **Trip-odometro (`distVal`, il badge "X.X km" sulla mappa) può incrementare durante una sessione di sola navigazione, senza aver premuto Avvia.** Bug reale ma di severità bassa, introdotto dal fix del punto GPS-indipendente sopra: `handlePosition()` non ha un guard `if (recording)` sul blocco che aggiorna l'odometro (solo il logging CSV ce l'ha). Si autocorregge non appena si preme Avvia (l'odometro si azzera). **Nessun impatto sui dati esportati** (CSV resta corretto). Non ancora corretto — decisione presa in sede di revisione: non bloccante, da sistemare quando comodo (basta aggiungere lo stesso guard `if (recording)` già usato per `logData.push`).
3. **Effetto glow del percorso mai verificato visivamente su un dispositivo reale.** Il codice è corretto (renderer "glow" creato prima di quello nitido, per lo stacking di default di Google Maps), ma nessun agente in questa sessione aveva un browser con mappa funzionante per confermarlo a occhio. Da controllare la prima volta che si vede una mappa reale con un percorso impostato.
4. **Verso del beccheggio (SU/GIÙ) non validato su strada.** Il calcolo è stato riscritto (vedi punto 2.1) ma il segno esatto va confermato in un'impennata reale. Se risulta invertito, un'unica riga da cambiare in `computePitchFromGravity()` (documentato lì con un commento).
5. **Verso della piega (SX/DX)**: questo invece è stato confermato/corretto sulla base del feedback reale dell'utente in questa sessione (punto 2.1) — non è un problema aperto, riportato qui solo per completezza rispetto al punto 4.

## 5. Dove guardare

- `index.html` — tutto il codice (HTML/CSS/JS in un unico file).
- `CLAUDE.md` — documentazione tecnica dettagliata e sempre aggiornata: leggerlo per capire *come* funziona qualsiasi parte del codice prima di modificarla.
- `README.md` — istruzioni di pubblicazione/uso rivolte all'utente finale.
- `docs/superpowers/specs/` — i due documenti di design (HUD, navigazione/mappa) con le decisioni prese e perché.
- `docs/superpowers/plans/` — i due piani di implementazione task-by-task usati per eseguire il lavoro via subagent.

## 6. Come continuare

Priorità consigliata:
1. Risolvere il caricamento di Google Maps (punto 4.1) — blocca la verifica di tutta la feature navigazione.
2. Una volta che la mappa carica: validare a occhio glow del percorso, leggibilità mappa diurna, posizione del pannello prossima manovra rispetto al logo Google, comportamento del follow-mode/pulsante 📍.
3. Un giro di guida reale per validare: verso del beccheggio (punto 4.4), soglie di colore piega (25°/40°, mai calibrate su dati reali), e in generale la leggibilità dell'HUD alla luce del sole/in movimento.
4. Il fix minore del punto 4.2 (odometro durante navigazione), quando comodo.
