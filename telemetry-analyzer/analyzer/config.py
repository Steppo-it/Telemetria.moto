"""
Soglie e pesi per l'analisi telemetria. Ogni valore è commentato con la
motivazione — vedi docs/superpowers/specs/2026-08-16-telemetry-analyzer-design.md
(sezioni 1-9) per il ragionamento completo. Tutti i valori qui sono punti di
partenza ragionevoli, non calibrati su dati reali (vedi spec, Ambito).
"""

# --- Timestamp / gap detection (spec sezione 1) ---
GAP_MULT = 2.5                 # gap se dt > 2.5x la mediana di dt osservata nella sessione
DUP_THRESHOLD_S = 0.05         # duplicato se dt < 50ms
IRREGULAR_MAD_K = 3            # irregolare se dt fuori da ±3 MAD dalla mediana locale di dt

# --- Hampel / validazione robusta (spec sezioni 2-4) ---
HAMPEL_WINDOW = 7              # campioni nella finestra mobile centrata (dispari)
Z_CAP = 6                      # z-score robusto che satura la penalità di confidence in W_HAMPEL

# Soglie di velocità di variazione (rate) per segnale — °/s per angoli, g/s per accelerazioni.
# A ~1Hz sono stime grossolane ("variazione nell'ultimo secondo", non una vera derivata
# istantanea): per questo non sono mai usate da sole nella formula di confidence.
MAX_RATE = {
    'lean': 70.0,
    'pitch': 90.0,
    'accel_fwd': 3.0,
    'accel_lat': 3.0,
    'accel_vert': 4.0,
}

# --- Persistenza: spike isolato vs evento reale (spec sezione 2c, riusata anche per
# la distinzione spike/evento-coerente delle accelerazioni, spec sezione 4 — stessa logica) ---
PERSIST_MIN_SAMPLES = 2        # quanti campioni successivi vengono controllati
# frazione della deviazione-dalla-mediana del campione candidato che deve essere
# ancora presente in almeno uno dei campioni successivi perché non sia "isolato"
PERSIST_TOLERANCE = 0.3

# --- Caso pitch estremo + evento verticale (spec sezione 3) ---
PITCH_EXTREME_DEG = 35.0
PITCH_CROSS_ACCEL_VERT_MIN = 0.35   # g netti oltre 1g di gravità

# --- Cross sensor validation (spec sezione 5) ---
BRAKE_ENTER_G = -0.25          # frenata "decisa": oltre il rumore normale di guida in scia/rilascio gas
ACCEL_ENTER_G = 0.25           # simmetrica a BRAKE_ENTER_G, per l'accelerazione
HEADING_CHANGE_MIN_DEG = 8.0   # variazione minima di direzione per considerare "sto girando", oltre il rumore tipico dell'heading GPS a bassa velocità
LEAN_CROSS_ACCEL_LAT_MIN = 0.15  # soglia di accelerazione laterale per considerare una piega "significativa"/una curva reale, non solo rumore in rettilineo
VERT_EVENT_MIN_G = 0.5         # accelerazione verticale netta (oltre 1g di gravità) per un "evento verticale" — buca/dosso, non la normale oscillazione delle sospensioni

# --- Confidence score (spec sezione 6) ---
W_HAMPEL = 40   # peso maggiore: e' l'evidenza statistica primaria (quanto il campione si discosta dalla mediana robusta locale)
W_RATE = 20     # peso minore di W_HAMPEL: la velocita' di variazione a ~1Hz e' un'evidenza piu' rumorosa/indiretta (vedi commento su MAX_RATE)
W_SPIKE = 25    # la persistenza (spec sezione 2c) e' un'evidenza diretta e affidabile — spike isolato vs evento reale e' quasi sempre inequivocabile
W_GAP = 15      # peso minore: un gap temporale rende il campione meno affidabile ma non e' di per se' un'anomalia del segnale stesso
W_CROSS = 25    # bonus, non penalita': se altri sensori confermano lo stesso evento fisico, e' un'evidenza forte quanto la persistenza
NEAR_GAP_WINDOW_S = 3.0        # un campione entro N secondi da un gap è penalizzato

FLAG_GREEN_MIN = 70    # sotto 70/100 la confidence non e' abbastanza alta da fidarsi ciecamente del dato raw
FLAG_YELLOW_MIN = 40   # sotto 40/100 il dato e' considerato probabile errore/outlier (RED), non solo "poco affidabile"

# --- Eventi: isteresi (spec sezione 8) — soglia di uscita meno severa di quella
# di ingresso, per evitare che l'evento "sfarfalli" dentro/fuori intorno alla soglia ---
BRAKE_EXIT_G = -0.10    # meno severa di BRAKE_ENTER_G apposta (isteresi): evita che l'evento frenata "sfarfalli" dentro/fuori intorno alla sola soglia di ingresso
ACCEL_EXIT_G = 0.10     # simmetrica a BRAKE_EXIT_G, stessa logica di isteresi
CURVE_EXIT_G = 0.08     # soglia di uscita piu' bassa di LEAN_CROSS_ACCEL_LAT_MIN: una volta dentro la curva, tollera un calo temporaneo di G laterale senza uscire subito dall'evento

# --- Curve / apex (spec sezione 9) ---
APEX_TOLERANCE_S = 1.5  # finestra temporale entro cui velocita' minima e lean massimo devono coincidere per confermare l'apex — oltre questa soglia l'apex e' dichiarato incerto (APEX UNCERTAIN), non inventato

# --- Replay (spec sezione 10) ---
REPLAY_DECIMATION_S = 2.0  # intervallo minimo tra un frame e il successivo nel replay: mantiene il player fluido su sessioni lunghe senza perdere risoluzione nei dati sottostanti (grafici/CSV restano a piena risoluzione)

SIGNALS = ['lean', 'pitch', 'accel_fwd', 'accel_lat', 'accel_vert']
SIGNAL_COLUMN = {
    'lean': 'lean_deg', 'pitch': 'pitch_deg',
    'accel_fwd': 'accel_fwd_g', 'accel_lat': 'accel_lat_g', 'accel_vert': 'accel_vert_g',
}
