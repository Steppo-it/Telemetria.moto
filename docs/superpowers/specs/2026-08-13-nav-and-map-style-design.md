# Navigazione turn-by-turn + restyling mappa — design

Data: 2026-08-13

## Ambito

Potenzia il navigatore esistente (icona 🧭, popover con campo destinazione + `DirectionsService`/`DirectionsRenderer`) trasformandolo da "disegna solo la linea del percorso" a un'esperienza di navigazione utilizzabile in marcia: istruzioni vocali, pannello prossima manovra, distanza/ETA, tappe multiple, autocomplete indirizzi. Restyling grafico della mappa (nero puro, strade in risalto, percorso con glow) e mappa a filo schermo sul lato esterno.

Fuori scope (invariato): bussola/rotazione mappa (la mappa resta orientata a nord fisso, per il vincolo sui link di attribuzione Google già documentato in CLAUDE.md), luoghi predefiniti/preferiti salvati, ricalcolo del percorso se si esce dalla rotta (rerouting).

## Prerequisito lato utente

**La Places API va abilitata manualmente su Google Cloud Console** (stesso progetto/chiave già in uso per Maps JavaScript API + Directions API) — passaggio che l'utente esegue autonomamente, il codice la presuppone abilitata. Senza, l'autocomplete non funziona (fallback: il campo resta un input di testo libero, la ricerca via `DirectionsService`/geocoding continua a funzionare come oggi).

## Autocomplete indirizzi

- Aggiunta la libreria `places` allo script tag Google Maps (`&libraries=places`).
- Ogni campo indirizzo (destinazione + eventuali tappe) usa `google.maps.places.Autocomplete` per suggerimenti live mentre si scrive.

## Tappe multiple

- Pulsante "+ Aggiungi tappa" nel popover navigatore: aggiunge dinamicamente un altro campo indirizzo (stesso autocomplete) sopra il campo destinazione finale.
- Ogni tappa ha una "×" per rimuoverla.
- Al click "Vai": tutte le tappe intermedie passano come `waypoints` a `DirectionsService.route()`, l'ultimo campo resta la destinazione finale.

## Istruzioni vocali

- Web Speech API (`speechSynthesis`), lingua italiana (`it-IT`).
- Al click "Vai" (gesture utente reale): annuncio di conferma immediato ("Navigazione avviata verso…") — serve anche a sbloccare la sintesi vocale su iOS Safari per le chiamate programmatiche successive.
- Il percorso restituito da `DirectionsService` viene appiattito in una sequenza continua di step (tutte le `legs[].steps[]` in ordine, con un annuncio extra al passaggio da una tappa all'altra: "Tappa raggiunta").
- Ad ogni fix GPS: calcola la distanza dalla posizione corrente alla fine dello step corrente.
  - Sotto ~150m dalla fine dello step, se non già annunciato per quello step: annuncia l'istruzione (testo dello step, ripulito dall'HTML).
  - Sotto ~30m dalla fine dello step: avanza allo step successivo.
  - Ultimo step completato: annuncia "Sei arrivato a destinazione", termina la navigazione vocale (il percorso disegnato resta visibile finché non si preme "Annulla percorso").
- Toggle 🔊 nel popover navigatore per disattivare la voce (persistito in `localStorage`, stesso pattern di tema/dimensione mappa). Se disattivo, il pannello a schermo e il calcolo di avanzamento restano attivi, solo `speechSynthesis.speak()` non viene chiamato.
- La navigazione (vocale + pannello) è **indipendente dalla registrazione telemetria**: funziona sia con **Avvia** premuto sia senza.

## Pannello prossima manovra (a schermo)

- Nuovo elemento compatto sulla mappa (badge in stile coerente con piega/beccheggio: chevron/icona di manovra + testo breve + distanza), visibile solo quando un percorso è attivo.
- Icona di manovra: mappata dal campo `maneuver` di ogni `DirectionsStep` (`turn-left`/`turn-right`/`straight`/`roundabout-*`/`merge`/ecc.) a un chevron o freccia semplice, stesso linguaggio grafico degli altri gauge.
- Distanza alla manovra: aggiornata ad ogni fix GPS (stessa distanza usata per l'avanzamento vocale).
- Un piccolo indicatore separato vicino all'icona 🧭 mostra **distanza ed ETA rimanenti totali**: somma di `distance`/`duration` degli step non ancora completati (nessuna chiamata API aggiuntiva — solo somma locale sui dati già restituiti dal primo `DirectionsService.route()`; non è un ricalcolo live basato su traffico attuale).

## Restyling grafico mappa

- Nuovo `NIGHT_STYLE`: sfondo **nero puro** (stesso `--bg` dell'HUD), strade bianche/chiare ad alto contrasto, POI/etichette ridotti al minimo per non affollare la vista.
- Percorso disegnato con effetto **glow**: due `Polyline`/`DirectionsRenderer` sovrapposte — una più larga e semi-trasparente (glow) sotto, una nitida sopra, entrambe in blu/ciano (`--blue-glow`).
- `.col-map`: `border-radius` rimosso sui lati esterni (schermo) — la mappa arriva a filo schermo su questi lati; il lato verso l'HUD mantiene la dissolvenza già implementata (invariata).

## Esplicitamente fuori scope

- Bussola/rotazione mappa (nord fisso, invariato — vincolo attribuzione Google).
- Luoghi predefiniti/preferiti salvati.
- Rerouting automatico se si esce dal percorso.
- ETA che tiene conto del traffico in tempo reale (richiederebbe richieste `DirectionsService` ripetute).

## Note di implementazione

- Nessuna nuova dipendenza esterna oltre alla libreria `places` di Google Maps (stessa chiave/script già caricato).
- Riuso della logica di distanza haversine già presente in `handlePosition()` (per `totalDistanceM`) per calcolare le distanze verso gli step del percorso.
- Persistenza toggle voce: nuova chiave `localStorage` (`moto_voice`, `on`/`off`), stesso pattern di `moto_theme`/`moto_map_pct`.
