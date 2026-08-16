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
BRAKE_ENTER_G = -0.25
ACCEL_ENTER_G = 0.25
HEADING_CHANGE_MIN_DEG = 8.0
LEAN_CROSS_ACCEL_LAT_MIN = 0.15
VERT_EVENT_MIN_G = 0.5

# --- Confidence score (spec sezione 6) ---
W_HAMPEL = 40
W_RATE = 20
W_SPIKE = 25
W_GAP = 15
W_CROSS = 25
NEAR_GAP_WINDOW_S = 3.0        # un campione entro N secondi da un gap è penalizzato

FLAG_GREEN_MIN = 70
FLAG_YELLOW_MIN = 40

# --- Eventi: isteresi (spec sezione 8) — soglia di uscita meno severa di quella
# di ingresso, per evitare che l'evento "sfarfalli" dentro/fuori intorno alla soglia ---
BRAKE_EXIT_G = -0.10
ACCEL_EXIT_G = 0.10
CURVE_EXIT_G = 0.08

# --- Curve / apex (spec sezione 9) ---
APEX_TOLERANCE_S = 1.5

# --- Replay (spec sezione 10) ---
REPLAY_DECIMATION_S = 2.0

SIGNALS = ['lean', 'pitch', 'accel_fwd', 'accel_lat', 'accel_vert']
SIGNAL_COLUMN = {
    'lean': 'lean_deg', 'pitch': 'pitch_deg',
    'accel_fwd': 'accel_fwd_g', 'accel_lat': 'accel_lat_g', 'accel_vert': 'accel_vert_g',
}
