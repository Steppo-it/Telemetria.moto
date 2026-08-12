# Telemetria Moto

PWA per telemetria in tempo reale su iPhone durante un giro in moto: piega, beccheggio, accelerazione/frenata in g e m/s², velocità, punteggio di guida, navigatore con percorso evidenziato su Google Maps. Landscape only.

## Setup — chiave Google Maps (obbligatoria per la mappa)

1. Vai su https://console.cloud.google.com/ e crea un progetto (o usane uno esistente)
2. In **API e servizi → Libreria**, abilita:
   - **Maps JavaScript API**
   - **Directions API**
3. In **API e servizi → Credenziali**, crea una **Chiave API**
4. (Consigliato) Limita la chiave: **Restrizioni applicazione → Referrer HTTP** e aggiungi `https://<tuo-utente>.github.io/*`
5. Apri `index.html`, cerca `YOUR_GOOGLE_MAPS_API_KEY` (ultima riga del file) e sostituiscilo con la tua chiave
6. Fai commit/push

Il livello gratuito di Google copre ampiamente un uso personale come questo (soglia mensile di credito inclusa).

## Pubblicazione (GitHub Pages)

Repo pubblico → Settings → Pages → Deploy from a branch → main → / (root). URL risultante: `https://<tuo-utente>.github.io/moto-telemetry/`

## Uso su iPhone

1. Apri l'URL **direttamente in Safari** (non da dentro altre app)
2. Landscape, blocco rotazione disattivato
3. **Calibra** a moto ferma, poi **Avvia**
4. Tocca l'icona 🧭 sulla mappa per impostare una destinazione e vedere il percorso evidenziato
5. A fine giro: **CSV** per esportare i dati

## Note tecniche

- La mappa resta orientata a nord fisso (non ruota con la direzione di marcia): ruotarla via CSS nasconderebbe il logo Google e i Termini, obbligatori per contratto. La freccia arancione ruota invece per indicarti la direzione.
- Piega e beccheggio: la sagoma della moto/rider mostra il valore istantaneo, il "ghost" trasparente mostra il massimo raggiunto durante tutta la sessione (persistente, non svanisce).
- Il picco della forza G invece è a scomparsa (~2,4s) perché è più utile vedere l'ultima frenata/accelerata forte che il massimo dell'intera sessione.
- "Assetto" (indice vibrazioni) resta calcolato internamente per il punteggio di guida ma non è più mostrato come tile separato.
