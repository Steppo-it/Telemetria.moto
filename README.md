# Telemetria Moto

Piccola PWA per visualizzare e registrare la telemetria di un giro in moto direttamente da iPhone: piega, beccheggio, accelerazione/frenata, indice di vibrazione/assetto, punteggio di guida. Landscape only.

## Come pubblicarla (GitHub Pages)

1. Crea un repo pubblico su GitHub (es. `moto-telemetry`)
2. Carica il contenuto di questa cartella (in particolare `index.html` deve stare nella root del repo)
3. Vai su **Settings → Pages**
4. In "Source" scegli **Deploy from a branch**, branch **main**, cartella **/ (root)**
5. Salva e aspetta 1-2 minuti: l'URL sarà tipo `https://<tuo-utente>.github.io/moto-telemetry/`

## Come usarla su iPhone

1. Apri l'URL sopra **direttamente in Safari** (non da dentro altre app)
2. Ruota il telefono in orizzontale — l'interfaccia è ottimizzata solo per landscape
3. Tocca **Avvia** e concedi i permessi per movimento/orientamento e posizione quando richiesti
4. A fine giro tocca **CSV** per esportare i dati registrati

### Per usarla come una vera app (icona in home)

1. Apri l'URL in Safari
2. Tocca l'icona di condivisione → **Aggiungi a Home**
3. Da quel momento la apri dall'icona, a schermo intero, senza barra Safari

## Note tecniche

- Piega e beccheggio vengono compensati automaticamente in base all'orientamento fisico dello schermo (`screen.orientation.angle`), quindi restano corretti sia con telefono montato verticale che orizzontale.
- L'indice "Vibrazione/Assetto" è una stima basata sull'accelerazione verticale dello chassis (RMS mobile), non una misura di laboratorio dello smorzamento reale delle sospensioni.
- Il GPS richiede un contesto sicuro (HTTPS) — per questo va ospitato (GitHub Pages va benissimo) e non aperto da file locale.
