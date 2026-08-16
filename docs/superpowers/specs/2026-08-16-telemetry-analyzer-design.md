# Telemetry Analyzer — analizzatore locale Python della telemetria CSV — design

Data: 2026-08-16

## Ambito

Un tool Python **locale, da riga di comando**, indipendente dalla PWA "TELAMETRIA" (nessuna dipendenza reciproca, nessun server, nessuna integrazione live — la PWA gira in un browser su iPhone, che non può eseguire Python). Legge un CSV esportato dalla PWA, produce un'analisi che non si limita a mostrare i dati grezzi ma individua e segnala errori dei sensori, outlier e valori poco plausibili — **senza mai eliminarli**: ogni valore resta disponibile come RAW, affiancato da un valore filtrato, una confidence 0-100, un flag di qualità (GREEN/YELLOW/RED) e un motivo testuale.

**Flusso d'uso**: si guida con la PWA (invariata), a fine giornata si esporta il CSV dal pannello comandi (invariato), poi sul computer si lancia `python telemetry_analyzer.py file.csv`, che genera un report HTML navigabile via browser più tre CSV di dettaglio.

**Fuori scope esplicito**: qualunque modifica alla PWA oltre a quanto già fatto (blocco schermo, già implementato separatamente); qualunque forma di integrazione live/rete tra PWA e analyzer; un'interfaccia grafica desktop (resta CLI + report HTML statico); calibrazione automatica delle soglie su dati reali (le soglie di partenza sono documentate ma non calibrate — vedi sezione Config).

**Posizione nel repo**: `moto-telemetry/telemetry-analyzer/` — sottocartella separata nello stesso repository Git della PWA (per comodità, un solo repo da clonare), ma un progetto Python autonomo: non tocca `index.html`, non viene servito da GitHub Pages (che serve solo ciò che la pagina referenzia), ha il proprio `requirements.txt`/README.

## Formato di input (invariato, definito dalla PWA)

```
timestamp,lat,lon,speed_kmh,heading_deg,lean_deg,pitch_deg,accel_fwd_g,accel_lat_g,accel_vert_g,comfort_idx,score
```

Una riga per ogni fix GPS ricevuto durante la registrazione (~1 Hz nominale, mai garantito). `accel_*`/`comfort_idx`/`score` sono l'ultimo campione `devicemotion` disponibile al momento del fix GPS — l'analyzer li tratta come dati validi già "fusi" dalla PWA, non li ricalcola.

## 1. Gestione del timestamp

- `timestamp` → `pandas.to_datetime`, ordinamento cronologico esplicito (mai assunto).
- `dt_s` = differenza in secondi tra campioni consecutivi.
- Frequenza nominale = **mediana** di `dt_s` sull'intera sessione (non un fisso "1 Hz assunto" — il sistema si adatta alla frequenza reale osservata).
- Classificazione per ogni intervallo:
  - **gap**: `dt_s > GAP_MULT × mediana(dt_s)` (default `GAP_MULT = 2.5`)
  - **duplicato**: `dt_s < DUP_THRESHOLD_S` (default `0.05`)
  - **irregolare**: `dt_s` fuori da `±IRREGULAR_MAD_K × MAD(dt_s)` dalla mediana locale (default `IRREGULAR_MAD_K = 3`)
- Colonne prodotte nel dataset RAW: `dt_s`, `gap_flag`, `dup_flag`, `irregular_flag`. **Nessuna interpolazione automatica nel dataset RAW.**
- `filtered_telemetry.csv` ha **sempre lo stesso numero di righe del CSV di input**, una per fix GPS reale — mai righe aggiuntive. Un gap temporale può essere colmato **solo internamente ed effimeramente**, in memoria, unicamente per non far "vedere" a una finestra mobile (sezioni 2-4) campioni troppo distanti nel tempo come se fossero adiacenti — questi eventuali campioni di continuità non vengono mai scritti in nessun file di output, non hanno una propria riga da nessuna parte, esistono solo durante il calcolo (vedi sezione 11 per la tassonomia `ESTIMATED`, riservata invece a valori dedotti come il "riapertura gas" di sezione 9, non a righe fittizie).

## 2-4. Filtro segnali: lean, pitch, accelerazioni — nucleo comune

Stesso algoritmo di base per `lean_deg`, `pitch_deg`, `accel_fwd_g`, `accel_lat_g`, `accel_vert_g`, applicato indipendentemente per ciascun segnale (soglie diverse, stessa logica):

**a) Punteggio robusto (Hampel)**
- Finestra mobile centrata di `W` campioni (default `W = 7`, dispari).
- `med_i` = mediana della finestra, `MAD_i` = mediana degli scarti assoluti dalla mediana.
- `σ_i = 1.4826 × MAD_i` (1.4826 è la costante standard che rende la MAD uno stimatore consistente della deviazione standard per dati distribuiti normalmente — è la costante usata in letteratura per il filtro di Hampel, non un numero arbitrario).
- `z_i = |x_i - med_i| / σ_i` (se `σ_i ≈ 0`, cioè finestra piattissima, `z_i = 0` se `x_i = med_i`, altrimenti `z_i = +∞`, gestito come RED diretto).

**b) Velocità di variazione fisicamente plausibile**
- `rate_i = |x_i - x_{i-1}| / dt_s`.
- Se `rate_i > MAX_RATE` (per segnale, vedi Config) → `rate_exceeded = True`. **Avvertenza esplicita nello spec**: a ~1 Hz questa è una stima grossolana ("variazione nell'ultimo secondo", non una vera derivata istantanea) — per questo non è mai usata da sola, sempre in combinazione con (a) e (c).

**c) Persistenza (distingue spike isolato da evento reale)**
- Un campione con `z_i` alto è riclassificato da "sospetto" a "evento reale plausibile" se il valore resta elevato (entro `PERSIST_TOLERANCE` dal valore corrente, stesso segno) per almeno `PERSIST_MIN_SAMPLES` campioni successivi (default `2`).
- Se invece il valore rientra al livello base entro 1 campione (torna entro `PERSIST_TOLERANCE` dalla mediana pre-evento), è classificato **spike isolato**.
- Esempio dallo spec originale: `18,19,21,67,20,19` → il `67` non persiste (il campione successivo torna a `20`, vicino alla mediana locale ~19-20) → spike isolato. `0.8,1.1,1.4,1.2,0.9` (accelerazione) → il picco `1.4` è circondato da valori che mantengono ≥40% della sua ampiezza rispetto al basale → evento coerente, non spike.

**d) Corroborazione incrociata** — vedi sezione 5, il bonus/penalità entra nella formula di confidence (sezione 6).

## 3. Caso speciale: pitch estremo + evento verticale

Se `pitch_deg` supera una soglia estrema (`PITCH_EXTREME_DEG`, default `35°`) **e** nello stesso campione (o nei ±1 campioni adiacenti) `|accel_vert_g|` supera `PITCH_CROSS_ACCEL_VERT_MIN` (default `0.35g` oltre 1g di gravità, cioè accelerazione verticale netta): il flag **non** diventa RED diretto. Diventa un flag dedicato `PITCH_AMBIGUOUS_EVENT` = **"POSSIBILE EVENTO REALE + POSSIBILE ERRORE ORIENTAMENTO"**, con `pitch_flag = YELLOW` e confidence abbassata (mai azzerata, mai dichiarata RED con certezza) — perché il dato reale non permette di distinguere le due ipotesi con questo solo sensore.

## 4. Spike isolato vs evento dinamico coerente (accelerazioni)

Per ciascuno dei tre assi (`accel_fwd_g`, `accel_lat_g`, `accel_vert_g`), un campione candidato picco (`|x_i| > ACCEL_PEAK_MIN_G`, default `0.5g` per asse, configurabile) viene classificato:
- **spike isolato**: entrambi i vicini immediati (`i-1`, `i+1`) hanno ampiezza `< SPIKE_NEIGHBOR_RATIO × |x_i|` (default `0.4`, cioè sotto il 40% del picco) → `*_filtered` sostituito con la mediana robusta locale, confidence penalizzata.
- **evento dinamico coerente**: almeno un vicino mantiene ampiezza (stesso segno) `≥ SPIKE_NEIGHBOR_RATIO × |x_i|` → valore mantenuto in `*_filtered` = raw, confidence alta, diventa candidato per il rilevamento eventi (sezione 8).

## 5. Cross sensor validation

Regole applicate per ogni campione/finestra, usate sia per il bonus di confidence sia per il tagging preliminare degli eventi (rifinito poi dalla macchina a stati in sezione 8):

| Evento | Condizione |
|---|---|
| Frenata | `speed_kmh` in calo su finestra breve **e** `accel_fwd_filtered ≤ BRAKE_ENTER_G` (default `-0.25g`) |
| Accelerazione | `speed_kmh` in aumento **e** `accel_fwd_filtered ≥ ACCEL_ENTER_G` (default `+0.25g`) |
| Curva | `|Δheading_deg|` su finestra `≥ HEADING_CHANGE_MIN_DEG` (default `8°`) **e** `|accel_lat_filtered| ≥ LEAN_CROSS_ACCEL_LAT_MIN` (default `0.15g`) **e** segno di `lean_filtered` coerente con la direzione del cambio di heading |
| Evento verticale | `|accel_vert_filtered|` netto `≥ VERT_EVENT_MIN_G` (default `0.5g`) su 1-2 campioni |

Quando una di queste condizioni è vera, il segnale corrispondente (lean per la curva, pitch/lean per l'evento verticale, accel_fwd per frenata/accelerazione) riceve il bonus `W_CROSS` nella formula di confidence (sezione 6) **solo per quel campione/finestra** — non retroattivamente su tutta la sessione.

## 6. Confidence score (0-100)

Stessa formula per tutti i segnali filtrati, pesi in `config.py`, ciascuno commentato con la motivazione:

```python
confidence_i = 100
  - W_HAMPEL * clamp(z_i / Z_CAP, 0, 1)   # distanza dalla mediana robusta locale
  - W_RATE   * (1 if rate_exceeded else 0)
  - W_SPIKE  * (1 if isolated_spike else 0)
  - W_GAP    * (1 if near_gap else 0)     # campione entro N secondi da un gap temporale
  + W_CROSS  * (1 if cross_corroborated else 0)
confidence_i = clamp(confidence_i, 0, 100)
```

Default (`config.py`, tutti motivati inline nel codice):
- `W_HAMPEL = 40`, `Z_CAP = 6` (uno z-score robusto ≥6 satura la penalità massima — valore convenzionale, ben oltre la soglia classica di 3 usata per marcare un outlier in un filtro di Hampel standard, scelto qui più permissivo perché la penalità è solo una componente tra più evidenze, non l'unico giudice)
- `W_RATE = 20`
- `W_SPIKE = 25`
- `W_GAP = 15`
- `W_CROSS = 25`

Soglie flag (`config.py`):
- **GREEN**: `confidence ≥ 70`
- **YELLOW**: `40 ≤ confidence < 70`
- **RED**: `confidence < 40`

## 7. Colonne del dataset filtrato

Per ciascuno dei 5 segnali (`lean`, `pitch`, `accel_fwd`, `accel_lat`, `accel_vert`), aggiunte a `filtered_telemetry.csv` accanto alla colonna raw originale:

- `{segnale}_filtered` — valore raw se `flag = GREEN`; mediana robusta locale se `YELLOW`/`RED`. **Mai un valore che non derivi direttamente dai dati della sessione stessa** (nessuna interpolazione da modelli esterni).
- `{segnale}_confidence` — 0-100.
- `{segnale}_flag` — `GREEN`/`YELLOW`/`RED` (più `PITCH_AMBIGUOUS_EVENT` come variante di YELLOW per il pitch, sezione 3).
- `{segnale}_reason` — stringa leggibile (es. `"z=8.2 oltre soglia, spike isolato, nessuna corroborazione incrociata"`).
- `{segnale}_status` — tassonomia (sezione 11): `RAW`/`MEASURED`/`FILTERED`/`ESTIMATED`/`INVALID`.

## 8. Riconoscimento eventi

Macchina a stati con **isteresi** (soglia di ingresso più severa della soglia di uscita, per evitare "sfarfallio" tra dentro/fuori evento) applicata sui segnali `*_filtered`, per ciascun tipo:

- **Frenata**: entra se `accel_fwd_filtered ≤ BRAKE_ENTER_G` (`-0.25g`), resta finché `accel_fwd_filtered ≤ BRAKE_EXIT_G` (`-0.10g`, meno severa).
- **Accelerazione**: simmetrica, `ACCEL_ENTER_G`/`ACCEL_EXIT_G` (`+0.25g`/`+0.10g`).
- **Curva**: entra se condizione "Curva" di sezione 5 vera, resta finché `|accel_lat_filtered|` scende sotto `CURVE_EXIT_G` (`0.08g`).
- **Evento verticale (buca/dosso)**: entra se condizione "Evento verticale" di sezione 5 vera; per natura ha durata breve (1-3 campioni), niente isteresi necessaria oltre un minimo di 1 campione sopra soglia.
- **Frenata + curva combinata**: overlap temporale tra un evento Frenata e un evento Curva → tag composito, non doppio conteggio.
- **Anomalia sensore**: finestra con `flag = RED` su ≥2 segnali contemporaneamente, non spiegata da nessuna corroborazione incrociata — evento a sé, distinto dagli eventi dinamici, riportato nella sezione qualità sensori più che nella tabella eventi principale.

Per ogni evento: `t_start`, `t_end`, `duration_s`, `v_start`, `v_end`, `v_max`, `lean_max` (con la sua confidence), `accel_fwd_max`, `accel_lat_max`, `accel_vert_max`, `confidence` (aggregata: media pesata delle confidence dei campioni coinvolti), `event_type`.

## 9. Analisi delle curve

Per ogni evento **Curva** (sezione 8), tentativo di segmentazione in fasi:

- **ENTRY**: inizio finestra curva (dove `|Δheading|` inizia a salire / `lean_filtered` inizia a salire sopra il basale).
- **BRAKING**: se un evento Frenata (sezione 8) si sovrappone alla prima parte della finestra curva.
- **TURN-IN**: campione con `max(|d(lean_filtered)/dt|)` nella fase di ingresso.
- **APEX**: campione di velocità minima locale nella finestra curva. Designazione **confermata** solo se questo campione è entro `APEX_TOLERANCE_S` (default `1.5s`) da un massimo locale di `lean_filtered`. Se le due condizioni non coincidono entro tolleranza, l'apex **non viene inventato**: `apex_status = "APEX UNCERTAIN"`, nessun timestamp di apex riportato come certo.
- **EXIT**: dopo l'apex (o dopo il punto di velocità minima se apex incerto), quando `lean_filtered` torna verso il basale **e/o** `accel_fwd_filtered` torna positivo (riapertura gas dedotta, non misurata direttamente — sempre etichettata come inferenza, `status = ESTIMATED`, mai come fatto misurato).

Statistiche per curva: `v_entry`, `v_min`, `v_exit`, `lean_max_filtered` (+ confidence), `accel_lat_max_filtered`, `accel_fwd_min_filtered` durante la fase di frenata in ingresso (se presente), `throttle_reopening_detected` (booleano), `duration_s`, `apex_status` (`CONFIRMED`/`UNCERTAIN`).

## 10. Report HTML

File singolo `report.html`, autonomo (Plotly imbottigliato inline via `include_plotlyjs='inline'` o CDN a scelta in config — default inline per garantire funzionamento offline, coerente col vincolo "completamente in locale"), sezioni:

1. **Dashboard generale**: durata, distanza GPS (da lat/lon consecutivi, calcolo equirettangolare come già fa la PWA), velocità max/media, frenata massima, accelerazione massima, accelerazione laterale massima, lean massimo RAW vs FILTERED (evidenzia quanto il filtraggio ha corretto), numero anomalie (RED), numero gap, qualità complessiva sessione (media pesata delle confidence su tutti i segnali).
2. **Sezione telemetria**: grafici Plotly sincronizzati nel tempo (subplot verticali con asse X condiviso) per `speed`, `lean`, `pitch`, `accel_fwd`, `accel_lat`, `accel_vert` — RAW e FILTERED sovrapposti sullo stesso grafico (RAW tratteggiato/attenuato, FILTERED pieno), outlier (RED) evidenziati con marker distinti.
3. **Sezione mappa — due viste**:
   - **Vista statica (Folium)**: percorso su mappa OSM, colorato per velocità (gradiente), marker sugli eventi principali (frenate forti, curve, eventi verticali).
   - **Vista replay sincronizzato (Plotly, `frames` + slider)**: marker che avanza lungo il percorso GPS in sincronia con uno slider temporale; la stessa interazione muove anche una linea verticale "sei qui" sui grafici della sezione telemetria. Per rides lunghe, i frame del replay sono **decimati** (default: un frame ogni `REPLAY_DECIMATION_S = 2` secondi, configurabile) per mantenere il file HTML leggero e il player fluido — i dati sottostanti (grafici statici, CSV filtrati) restano sempre a piena risoluzione, la decimazione riguarda solo la fluidità dell'animazione.
   - **Indicatori grafici stato moto durante il replay**: due icone SVG inline accanto al replay, aggiornate ad ogni frame da un piccolo script JS che ascolta gli eventi dello slider Plotly (`plotly_sliderchange` / `plotly_animatingframe`) e legge il campione corrispondente dal dataset (embeddato come JSON nella pagina):
     - **Silhouette moto vista da dietro**, ruotata via CSS (`transform: rotate({lean_filtered}deg)`) per mostrare l'inclinazione in tempo reale, con il valore numerico (`{lean_filtered}°`) accanto — stesso principio dei gauge a barra della PWA (numero grande + indicazione visiva), non serve replicarne lo stile grafico esatto ma lo spirito (leggibilità a colpo d'occhio).
     - **Silhouette moto vista di lato**, ruotata secondo `pitch_filtered`, stesso principio, valore numerico accanto.
     - Entrambe usano il valore **filtrato**, mai il raw, e mostrano anche il flag qualità del campione corrente (es. bordo giallo se `YELLOW`) così l'utente vede quando un valore mostrato nel replay è meno affidabile.
4. **Sezione eventi**: tabella ordinabile (colonne = tutti i campi di sezione 8) — implementata con una piccola utility JS di ordinamento tabella inline (nessuna libreria esterna, per restare "completamente locale" senza dipendenze da CDN oltre a Plotly).
5. **Sezione curve**: elenco dettagliato, un blocco per curva con le statistiche di sezione 9, `apex_status` sempre visibile.
6. **Sezione sensor quality**: per ciascuno dei 5 segnali, % GREEN/YELLOW/RED, numero di gap, confidence media; evidenzia il "sensore più problematico" della sessione (quello con la % di RED più alta).

## 11. Tassonomia dei dati

Ogni valore prodotto dall'analyzer porta uno `status` esplicito, mai ambiguo:

- **RAW**: esattamente come letto dal CSV, nessuna elaborazione.
- **MEASURED**: uguale a RAW, ma esplicitamente validato `GREEN` (alta confidence — "affidabile come misurato").
- **FILTERED**: valore sostituito da una stima robusta locale (mediana della finestra) perché il raw era `YELLOW`/`RED`.
- **ESTIMATED**: valore non misurato direttamente ma dedotto per inferenza incrociata (es. riapertura gas in una curva, o un campione generato solo per continuità di calcolo interno su un gap — mai esportato come se fosse un fix GPS reale).
- **INVALID**: non determinabile con confidence sufficiente in alcun modo. Riportato esplicitamente come **"dato non determinabile"** nel report — mai un numero indovinato.

## 12. Tecnologie e struttura

Python 3, librerie: `pandas`, `numpy`, `scipy` (per il calcolo di mediane/MAD robuste su finestre mobili), `plotly`, `folium`. Nessuna dipendenza da rete a runtime lato analisi (report imbottigliato, `include_plotlyjs='inline'`); i tile della mappa Folium/OSM richiedono connessione solo per la vista mappa statica quando il report viene aperto in un browser — stesso tipo di vincolo già accettato dalla PWA per Google Maps, non un downgrade rispetto ad essa.

Struttura modulare:
```
telemetry-analyzer/
  telemetry_analyzer.py       # entrypoint CLI
  analyzer/
    __init__.py
    config.py                 # tutte le soglie/pesi, ciascuno commentato col perché
    loading.py                 # parsing CSV, timestamp, gap/dup/irregular detection
    validation.py              # Hampel/rate/persistenza per segnale
    filtering.py               # formula confidence, colonne *_filtered/*_flag/*_reason/*_status
    fusion.py                   # regole cross-sensor (sezione 5), tagging eventi candidati
    events.py                   # macchina a stati con isteresi, tabella eventi
    curves.py                   # segmentazione curve, logica apex, tabella curve
    report.py                   # dashboard, grafici Plotly, mappa Folium, replay sincronizzato + icone SVG
  requirements.txt
  README.md
```

**CLI**: `python telemetry_analyzer.py file.csv [--outdir DIR] [--config path/to/config.py]`. Output di default nella stessa cartella del CSV di input (o `--outdir` se specificato): `report.html`, `filtered_telemetry.csv`, `events.csv`, `curves.csv`.

## Nota sul "collegamento interno" nella PWA

Discusso ma non incluso in questo piano: un rimando testuale nella PWA (vicino al pulsante CSV) che ricordi "analizza questo file con telemetry-analyzer sul tuo computer" — puramente informativo, nessuna integrazione funzionale possibile (il telefono non esegue Python). Rimandato a un intervento futuro separato, dopo che questo tool esiste ed è verificato.
