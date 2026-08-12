# Redesign del cruscotto (HUD) — design

Data: 2026-08-13

## Ambito

Questo intervento riguarda **solo il cruscotto** (piega, beccheggio, accelerazione/frenata, velocità, punteggio guida) dentro `index.html`. La mappa resta **invariata**: stesso stile "need for speed" scuro/blu, stessa proporzione di default e ridimensionamento via drag, stessa assenza di bussola/rotazione/ricerca avanzata. Bussola, rotazione mappa e ricerca con suggerimenti/preferiti/luoghi predefiniti sono un progetto separato, con un proprio spec futuro.

Sono inclusi in questo intervento anche due elementi tecnici emersi durante la progettazione, non solo estetici:
1. Fix del bug del beccheggio che salta a valori assurdi (~-350°) durante un'impennata.
2. Tracciamento separato dei picchi per lato/verso (Max Sx / Max Dx per la piega, Max Up / Max Down per il beccheggio) invece di un singolo massimo assoluto.

## Layout

- **Mappa**: invariata, stessa proporzione di default (`--map-pct`), stesso resize handle via drag.
- **Colonna HUD**, dall'alto in basso:
  1. **Piega** (badge grande, ~1.5x lo spazio verticale rispetto al beccheggio)
  2. **Beccheggio** (badge più piccolo, ~1x)
  3. Riga compatta **Velocità** / **Punteggio guida**, senza box/bordo, separata dai gauge sopra da un sottile filo divisorio
  4. Zona pulsanti (**Avvia/Ferma**, **Calibra** grandi e "alla cieca"; **Impostazioni**/**CSV** piccoli) — invariata, resta nella porzione in basso a destra fisicamente coperta dal quadro strumenti della moto (vincolo noto, vedi CLAUDE.md esistente)
- **Barra G** (accelerazione/frenata): striscia verticale sul **bordo destro esterno** della colonna HUD, per tutta l'altezza dell'area piega+beccheggio. Non occupa larghezza dei gauge principali.
- **Divisorio mappa/HUD**: non più una linea netta — la mappa **sfuma in dissolvenza** verso il colore di sfondo sul lato rivolto agli indicatori (gradiente, non bordo).
- **Nessun pannello con bordo/box visibile**: l'intero HUD è a superficie piatta, senza cornici separate per ciascun elemento. L'unico filo sottile (hairline) ammesso è quello sopra la riga velocità/punteggio, per leggibilità.

## Gauge piega e beccheggio — stile "badge + chevron"

Niente più sagoma/illustrazione di moto. Ogni gauge è composto da:
- Un **chevron** (◀/▶ per la piega, ▲/▼ per il beccheggio) che indica il verso a colpo d'occhio, senza dover leggere il segno del numero.
- Un **numero grande** in font Orbitron (già caricato in app, nessuna nuova dipendenza) con il valore assoluto in gradi.
- Una **sottoetichetta** tecnica (es. "PIEGA · DX", "BECCH. · GIÙ").
- Due **valori di picco separati**, persistenti per tutta la sessione (si azzerano a ogni "Avvia"):
  - Piega: **MAX SX** e **MAX DX**
  - Beccheggio: **MAX UP** e **MAX DOWN**

  Questo sostituisce il vecchio `maxLean`/`maxPitch` con segno singolo: servono quattro variabili di stato (`maxLeanSx`, `maxLeanDx`, `maxPitchUp`, `maxPitchDown`), ciascuna aggiornata confrontando solo i campioni con il segno/verso corrispondente.

**Animazione/vivacità**: chevron e numero si aggiornano in tempo reale ad ogni campione sensore (stesso ritmo di oggi), quindi restano "vivi" senza bisogno di un'animazione decorativa a parte — il requisito di visibilità/dinamicità della UI è soddisfatto dall'aggiornamento live, non da un effetto cosmetico aggiuntivo.

## Barra G (accelerazione/frenata)

- Orientamento verticale, centro = 0g.
- Si riempie **verso l'alto** (colore "accelerazione") in accelerazione, **verso il basso** (colore "frenata") in frenata — metafora "su = vai, giù = freni".
- Mantiene il comportamento attuale del marcatore di picco a scomparsa (bianco, hold ~1.4s + fade ~1s, poi si riarma sul valore corrente) — stessa logica di `makePeakHold()` già presente nel codice, solo riorientata in verticale.
- Mostra il valore numerico in **g** vicino alla barra. La seconda unità in m/s² (presente oggi nella barra orizzontale) viene **rimossa** per mancanza di spazio nella striscia verticale stretta.

## Colori — monocromatico, con due eccezioni

- **Tema notturno di default** (sfondo quasi nero, testo chiaro), con **tema diurno** attivabile da Impostazioni (sfondo chiaro, testo scuro) — stessa struttura, palette invertita.
- **Tutta la UI è monocromatica** (usa solo i toni "ink"/"ink-dim" del tema attivo), **tranne**:
  1. **Barra G**: resta sempre a gradiente colorato pieno (rosso in frenata → neutro al centro → blu in accelerazione), in entrambi i temi.
  2. **Piega**: resta monocromatica in condizioni normali, ma chevron e numero diventano **ambra oltre 25°** e **rossi oltre 40°** — non è decorazione ma segnale di sicurezza, l'unica eccezione al monocromatico oltre alla barra G.
  Il **beccheggio non ha soglie colore** (resta sempre monocromatico, nessuna richiesta in tal senso).

## Fix calcolo beccheggio (bug impennata)

Il salto a ~-350° durante un'impennata è un limite noto dell'angolo `beta` di `DeviceOrientationEvent` (gimbal lock/wrap oltre ±90° di inclinazione). Il beccheggio verrà ricalcolato usando il vettore di gravità già stimato per il filtro dell'accelerazione (`gEst`, aggiornato ad ogni evento `devicemotion`), tramite arcotangente a due argomenti — matematicamente privo di quel salto discontinuo.

- La calibrazione (bottone "Calibra") continua a funzionare allo stesso modo: cattura il valore corrente come nuovo zero.
- Il calcolo si sposta (o si duplica in modo condiviso) da `handleOrientation` a `handleMotion`, dato che ora dipende dal vettore di gravità stimato dall'accelerometro invece che da `beta`.
- **Non è possibile validare il fix su una vera impennata durante lo sviluppo** — va testato su strada, nello stesso spirito della nota già presente in CLAUDE.md sul verso del beccheggio non validato.

## Esplicitamente fuori scope

- Bussola, rotazione mappa, ricerca con suggerimenti/preferiti/luoghi predefiniti (prossimo spec separato).
- Modifiche al formato di export CSV.
- Nuove soglie colore per il beccheggio.
- Modifiche alla zona pulsanti "alla cieca" in basso (posizione/dimensioni invariate).

## Note di implementazione

- Font numerico: **Orbitron**, già importato in `index.html` — nessuna nuova dipendenza da caricare.
- Il layout attuale (`col-map` / `resize-handle` / `col-hud`) resta come scheletro; cambiano soprattutto gli stili dei componenti dentro `col-hud` e la G-force bar (da orizzontale a verticale, riposizionata).
- Tema chiaro/scuro: nuova preferenza persistita in `localStorage` (stesso pattern già usato per `moto_map_pct`), toggle esposto nel popover "Impostazioni" esistente.
