# Telemetry Analyzer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Costruire `telemetry-analyzer`, un tool Python CLI locale che legge il CSV esportato dalla PWA TELAMETRIA, individua e segnala (senza mai eliminare) errori dei sensori/outlier con un sistema di confidence a tre livelli, rileva eventi e curve, e produce un report HTML navigabile con grafici sincronizzati, mappa statica e replay animato.

**Architecture:** Package Python puro (`analyzer/`), pipeline lineare a moduli indipendenti (loading → validation+fusion → filtering → events/curves → report), ciascuno testabile in isolamento con CSV sintetici. Nessun framework, nessun server: uno script CLI che legge un file e scrive quattro file di output.

**Tech Stack:** Python 3.10+, pandas, numpy, scipy, plotly, folium, pytest.

**Spec:** `docs/superpowers/specs/2026-08-16-telemetry-analyzer-design.md`

## Global Constraints

- Nessuna eliminazione di valori: ogni dato raw resta sempre disponibile, affiancato da `*_filtered`/`*_confidence`/`*_flag`/`*_reason`/`*_status`.
- Nessuna interpolazione automatica nel dataset raw; `filtered_telemetry.csv` ha sempre lo stesso numero di righe del CSV di input (una per fix GPS reale, mai righe fittizie aggiuntive).
- Tutte le soglie/pesi vivono in `analyzer/config.py`, ciascuno commentato con la motivazione — mai un numero magico sparso nel codice.
- Tassonomia dato obbligatoria su ogni valore prodotto: RAW / MEASURED / FILTERED / ESTIMATED / INVALID (mai un numero "inventato" spacciato per misurato).
- Il progetto vive in `moto-telemetry/telemetry-analyzer/`, completamente indipendente dalla PWA (`index.html`) — non lo modifica, non ne dipende, non richiede rete a runtime per l'analisi (solo i tile della mappa statica Folium richiedono connessione quando il report viene aperto).
- Formato di input invariato e non negoziabile: `timestamp,lat,lon,speed_kmh,heading_deg,lean_deg,pitch_deg,accel_fwd_g,accel_lat_g,accel_vert_g,comfort_idx,score`.
- CLI: `python telemetry_analyzer.py file.csv [--outdir DIR] [--config path/to/config.py]` → `report.html`, `filtered_telemetry.csv`, `events.csv`, `curves.csv`.

## File Structure

```
telemetry-analyzer/
  telemetry_analyzer.py          # entrypoint CLI (Task 12)
  requirements.txt                # Task 1
  README.md                       # Task 1
  analyzer/
    __init__.py                   # Task 1
    config.py                     # Task 1 — tutte le soglie/pesi
    loading.py                    # Task 2 — CSV, timestamp, gap/dup/irregular
    validation.py                 # Task 3 — Hampel z, rate, persistenza (per-segnale, riusabile)
    fusion.py                     # Task 4 — regole cross-sensor, caso pitch ambiguo
    filtering.py                  # Task 5 — confidence, colonne filtered/flag/reason/status
    events.py                     # Task 6 — macchina a stati con isteresi
    curves.py                     # Task 7 — segmentazione curve, apex
    report/
      __init__.py                 # Task 8
      dashboard.py                # Task 8 — riepilogo generale
      charts.py                   # Task 8 — grafici Plotly sincronizzati RAW+FILTERED
      map_static.py               # Task 9 — mappa Folium statica
      replay.py                   # Task 10 — replay Plotly + icone SVG piega/beccheggio
      tables.py                   # Task 11 — tabelle eventi/curve + qualità sensori
      assemble.py                 # Task 11 — assembla report.html finale
  tests/
    __init__.py                   # Task 1
    fixtures.py                   # Task 1 — generatore CSV sintetici per gli scenari di test
    test_loading.py               # Task 2
    test_validation.py            # Task 3
    test_fusion.py                # Task 4
    test_filtering.py             # Task 5
    test_events.py                # Task 6
    test_curves.py                # Task 7
    test_report_smoke.py          # Task 12
```

---

### Task 1: Scaffolding, config e fixture di test sintetiche

**Files:**
- Create: `telemetry-analyzer/analyzer/__init__.py`
- Create: `telemetry-analyzer/analyzer/config.py`
- Create: `telemetry-analyzer/tests/__init__.py`
- Create: `telemetry-analyzer/tests/fixtures.py`
- Create: `telemetry-analyzer/requirements.txt`
- Create: `telemetry-analyzer/README.md`
- Test: `telemetry-analyzer/tests/test_fixtures.py`

**Interfaces:**
- Produces: costanti in `analyzer.config` (elencate sotto, nomi esatti usati da tutti i task successivi); `tests.fixtures.make_ride_csv(path, rows, **overrides) -> None` (scrive un CSV con le 12 colonne richieste); `tests.fixtures.build_scenario_rows(scenario_name, start_ts, n=None) -> list[dict]` che ritorna liste di dict (una per riga CSV) per ciascuno scenario: `'normal'`, `'lean_isolated_spike'`, `'accel_coherent_event'`, `'pitch_ambiguous_event'`, `'temporal_gap'`, `'duplicate_timestamp'`, `'curve_clear_apex'`, `'curve_uncertain_apex'`.
- Consumes: nulla (task fondativo).

- [ ] **Step 1: Crea la struttura pacchetto e `requirements.txt`**

```bash
mkdir -p telemetry-analyzer/analyzer/report
mkdir -p telemetry-analyzer/tests/fixtures_output
touch telemetry-analyzer/analyzer/__init__.py
touch telemetry-analyzer/analyzer/report/__init__.py
touch telemetry-analyzer/tests/__init__.py
```

`telemetry-analyzer/requirements.txt`:
```
pandas>=2.0
numpy>=1.24
scipy>=1.10
plotly>=5.18
folium>=0.15
pytest>=7.4
```

- [ ] **Step 2: Scrivi `analyzer/config.py`**

```python
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
```

- [ ] **Step 3: Scrivi `tests/fixtures.py` — generatore di CSV sintetici**

```python
"""Genera CSV di telemetria sintetici per testare la pipeline senza dati reali."""
import csv
from datetime import datetime, timedelta

CSV_COLUMNS = ['timestamp', 'lat', 'lon', 'speed_kmh', 'heading_deg', 'lean_deg',
               'pitch_deg', 'accel_fwd_g', 'accel_lat_g', 'accel_vert_g', 'comfort_idx', 'score']


def _row(ts, lat=45.0, lon=9.0, speed=40.0, heading=90.0, lean=15.0, pitch=0.0,
         accel_fwd=0.05, accel_lat=0.05, accel_vert=0.02, comfort=90.0, score=80.0):
    return {
        'timestamp': ts.isoformat() + 'Z', 'lat': lat, 'lon': lon, 'speed_kmh': speed,
        'heading_deg': heading, 'lean_deg': lean, 'pitch_deg': pitch,
        'accel_fwd_g': accel_fwd, 'accel_lat_g': accel_lat, 'accel_vert_g': accel_vert,
        'comfort_idx': comfort, 'score': score,
    }


def build_scenario_rows(scenario_name, start_ts=None, n=None):
    """Ritorna una lista di dict (righe CSV) per lo scenario richiesto."""
    if start_ts is None:
        start_ts = datetime(2026, 8, 16, 10, 0, 0)
    rows = []

    if scenario_name == 'normal':
        n = n or 20
        for i in range(n):
            rows.append(_row(start_ts + timedelta(seconds=i), lean=15.0 + (i % 3), lon=9.0 + i * 0.0001))

    elif scenario_name == 'lean_isolated_spike':
        # dallo spec: 18, 19, 21, 67, 20, 19 — il 67 è uno spike isolato, non persiste
        leans = [18, 19, 21, 67, 20, 19, 18, 19, 20, 19]
        for i, lean in enumerate(leans):
            rows.append(_row(start_ts + timedelta(seconds=i), lean=float(lean), accel_lat=0.05))

    elif scenario_name == 'accel_coherent_event':
        # dallo spec: 0.1,0.2,1.4,0.2,0.1 = spike; 0.8,1.1,1.4,1.2,0.9 = evento coerente
        fwd_values = [0.1, 0.2, 1.4, 0.2, 0.1, 0.15, 0.8, 1.1, 1.4, 1.2, 0.9, 0.2]
        for i, fwd in enumerate(fwd_values):
            rows.append(_row(start_ts + timedelta(seconds=i), accel_fwd=fwd, speed=40.0 - fwd * 5))

    elif scenario_name == 'pitch_ambiguous_event':
        n = n or 10
        for i in range(n):
            if i == 5:
                rows.append(_row(start_ts + timedelta(seconds=i), pitch=40.0, accel_vert=0.5))
            else:
                rows.append(_row(start_ts + timedelta(seconds=i), pitch=2.0, accel_vert=0.02))

    elif scenario_name == 'temporal_gap':
        n = n or 10
        for i in range(n):
            ts = start_ts + timedelta(seconds=i if i < 5 else i + 15)  # buco di 15s dopo il 5° campione
            rows.append(_row(ts))

    elif scenario_name == 'duplicate_timestamp':
        n = n or 8
        for i in range(n):
            ts = start_ts + timedelta(seconds=i)
            rows.append(_row(ts))
        rows.insert(3, _row(start_ts + timedelta(seconds=2, milliseconds=10)))  # duplicato quasi esatto

    elif scenario_name == 'curve_clear_apex':
        # velocità che scende poi risale, lean che sale poi scende, coincidenti nel tempo.
        # Convenzione PWA: lean positivo = SX. Sterzare a sinistra fa DIMINUIRE l'heading
        # (compass in gradi, senso orario) — per questo heading scende mentre lean è positivo,
        # coerenti tra loro per il controllo "segno lean coerente con Δheading" di fusion.py.
        speeds = [60, 55, 48, 42, 38, 40, 45, 52, 58]
        leans = [5, 15, 28, 38, 40, 36, 24, 12, 5]
        for i, (sp, ln) in enumerate(zip(speeds, leans)):
            fwd = -0.3 if i < 4 else (0.25 if i > 5 else 0.0)
            rows.append(_row(start_ts + timedelta(seconds=i), speed=sp, lean=ln,
                              heading=90.0 - i * 8, accel_lat=0.02 * ln, accel_fwd=fwd))

    elif scenario_name == 'curve_uncertain_apex':
        # velocità minima e lean massimo NON coincidono nel tempo (oltre APEX_TOLERANCE_S).
        # Stessa convenzione heading/lean di 'curve_clear_apex' sopra.
        speeds = [60, 55, 50, 48, 48, 48, 50, 55, 60]
        leans = [5, 10, 15, 18, 20, 35, 20, 10, 5]  # massimo lean molto dopo il minimo di velocità
        for i, (sp, ln) in enumerate(zip(speeds, leans)):
            rows.append(_row(start_ts + timedelta(seconds=i), speed=sp, lean=ln,
                              heading=90.0 - i * 8, accel_lat=0.02 * ln))

    else:
        raise ValueError(f'scenario sconosciuto: {scenario_name}')

    return rows


def make_ride_csv(path, scenario_name='normal', start_ts=None, n=None):
    """Scrive su `path` un CSV valido per lo scenario richiesto."""
    rows = build_scenario_rows(scenario_name, start_ts=start_ts, n=n)
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def make_full_ride_csv(path, start_ts=None):
    """Concatena tutti gli scenari in un'unica sessione realistica per il test di
    integrazione finale (Task 12) — ogni scenario separato da un piccolo tratto 'normal'."""
    if start_ts is None:
        start_ts = datetime(2026, 8, 16, 10, 0, 0)
    all_rows = []
    t = start_ts
    scenarios = ['normal', 'lean_isolated_spike', 'accel_coherent_event',
                 'pitch_ambiguous_event', 'curve_clear_apex', 'curve_uncertain_apex', 'normal']
    for scenario in scenarios:
        rows = build_scenario_rows(scenario, start_ts=t)
        all_rows.extend(rows)
        t = t + timedelta(seconds=len(rows) + 2)
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)
```

- [ ] **Step 4: Scrivi il test delle fixture stesse**

```python
# tests/test_fixtures.py
import csv
from tests.fixtures import build_scenario_rows, CSV_COLUMNS

def test_all_scenarios_produce_valid_rows():
    scenarios = ['normal', 'lean_isolated_spike', 'accel_coherent_event',
                 'pitch_ambiguous_event', 'temporal_gap', 'duplicate_timestamp',
                 'curve_clear_apex', 'curve_uncertain_apex']
    for scenario in scenarios:
        rows = build_scenario_rows(scenario)
        assert len(rows) > 0, f'{scenario} non produce righe'
        for row in rows:
            assert set(row.keys()) == set(CSV_COLUMNS), f'{scenario}: colonne mancanti/extra'

def test_lean_isolated_spike_matches_spec_example():
    rows = build_scenario_rows('lean_isolated_spike')
    leans = [r['lean_deg'] for r in rows[:6]]
    assert leans == [18.0, 19.0, 21.0, 67.0, 20.0, 19.0]
```

- [ ] **Step 5: Esegui i test**

```bash
cd telemetry-analyzer && python -m pytest tests/test_fixtures.py -v
```

Expected: 2 PASS.

- [ ] **Step 6: `README.md` minimale**

```markdown
# telemetry-analyzer

Tool locale per analizzare i CSV di telemetria esportati dalla PWA TELAMETRIA.

## Setup

    pip install -r requirements.txt

## Uso

    python telemetry_analyzer.py percorso/al/file.csv

Genera nella stessa cartella del CSV: `report.html`, `filtered_telemetry.csv`,
`events.csv`, `curves.csv`.

Vedi `docs/superpowers/specs/2026-08-16-telemetry-analyzer-design.md` (nel
repo principale) per la logica di filtraggio/confidence completa.
```

- [ ] **Step 7: Commit**

```bash
git add telemetry-analyzer/
git commit -m "Scaffolding, config e fixture di test sintetiche per telemetry-analyzer"
```

---

### Task 2: `loading.py` — CSV, timestamp, gap/dup/irregular

**Files:**
- Create: `telemetry-analyzer/analyzer/loading.py`
- Test: `telemetry-analyzer/tests/test_loading.py`

**Interfaces:**
- Consumes: `analyzer.config.GAP_MULT`, `DUP_THRESHOLD_S`, `IRREGULAR_MAD_K`; `tests.fixtures.make_ride_csv`.
- Produces: `load_csv(path: str) -> pandas.DataFrame` (colonne originali + `timestamp` come `datetime64`, ordinato); `compute_time_deltas(df: pandas.DataFrame) -> pandas.DataFrame` (aggiunge `dt_s`, `gap_flag`, `dup_flag`, `irregular_flag`). Entrambe usate da `filtering.py` (Task 5) e dal CLI (Task 12).

- [ ] **Step 1: Scrivi i test**

```python
# tests/test_loading.py
import pandas as pd
from analyzer.loading import load_csv, compute_time_deltas
from tests.fixtures import make_ride_csv

def test_load_csv_parses_timestamp(tmp_path):
    csv_path = tmp_path / 'ride.csv'
    make_ride_csv(csv_path, 'normal')
    df = load_csv(str(csv_path))
    assert pd.api.types.is_datetime64_any_dtype(df['timestamp'])
    assert len(df) == 20

def test_load_csv_raises_on_missing_columns(tmp_path):
    csv_path = tmp_path / 'bad.csv'
    csv_path.write_text('a,b,c\n1,2,3\n')
    try:
        load_csv(str(csv_path))
        assert False, 'doveva sollevare ValueError'
    except ValueError as e:
        assert 'colonne' in str(e)

def test_compute_time_deltas_normal_session_no_flags(tmp_path):
    csv_path = tmp_path / 'ride.csv'
    make_ride_csv(csv_path, 'normal')
    df = compute_time_deltas(load_csv(str(csv_path)))
    assert not df['gap_flag'].any()
    assert not df['dup_flag'].any()
    assert not df['irregular_flag'].any()
    assert abs(df['dt_s'].median() - 1.0) < 0.01

def test_compute_time_deltas_detects_gap(tmp_path):
    csv_path = tmp_path / 'ride.csv'
    make_ride_csv(csv_path, 'temporal_gap')
    df = compute_time_deltas(load_csv(str(csv_path)))
    assert df['gap_flag'].sum() == 1

def test_compute_time_deltas_detects_duplicate(tmp_path):
    csv_path = tmp_path / 'ride.csv'
    make_ride_csv(csv_path, 'duplicate_timestamp')
    df = compute_time_deltas(load_csv(str(csv_path)))
    assert df['dup_flag'].sum() >= 1

def test_row_count_preserved(tmp_path):
    csv_path = tmp_path / 'ride.csv'
    make_ride_csv(csv_path, 'normal')
    raw = load_csv(str(csv_path))
    enriched = compute_time_deltas(raw)
    assert len(enriched) == len(raw)
```

- [ ] **Step 2: Verifica che i test falliscano**

```bash
cd telemetry-analyzer && python -m pytest tests/test_loading.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'analyzer.loading'`.

- [ ] **Step 3: Scrivi `analyzer/loading.py`**

```python
"""Caricamento CSV e gestione timestamp (spec sezione 1)."""
import numpy as np
import pandas as pd

from analyzer import config

REQUIRED_COLUMNS = ['timestamp', 'lat', 'lon', 'speed_kmh', 'heading_deg', 'lean_deg',
                     'pitch_deg', 'accel_fwd_g', 'accel_lat_g', 'accel_vert_g',
                     'comfort_idx', 'score']


def load_csv(path):
    """Legge il CSV, valida le colonne richieste, converte timestamp e ordina
    cronologicamente (mai assunto già ordinato)."""
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f'CSV privo delle colonne richieste: {missing}')
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df


def compute_time_deltas(df):
    """Aggiunge dt_s (secondi dal campione precedente) e i flag gap/dup/irregular.
    La frequenza nominale è la MEDIANA di dt_s osservata, non un fisso 1Hz assunto."""
    dt = df['timestamp'].diff().dt.total_seconds()
    median_dt = dt.median(skipna=True)
    if pd.isna(median_dt) or median_dt <= 0:
        median_dt = 1.0  # sessione troppo corta per stimare una frequenza: fallback neutro

    abs_dev = (dt - median_dt).abs()
    mad_dt = abs_dev.median(skipna=True)
    sigma_dt = 1.4826 * mad_dt if pd.notna(mad_dt) and mad_dt > 0 else 0.0

    gap_flag = (dt > (config.GAP_MULT * median_dt)).fillna(False)
    dup_flag = (dt < config.DUP_THRESHOLD_S).fillna(False)
    if sigma_dt > 0:
        irregular_flag = (abs_dev > (config.IRREGULAR_MAD_K * sigma_dt)).fillna(False)
    else:
        irregular_flag = pd.Series(False, index=df.index)

    out = df.copy()
    out['dt_s'] = dt
    out['gap_flag'] = gap_flag
    out['dup_flag'] = dup_flag
    out['irregular_flag'] = irregular_flag
    return out
```

- [ ] **Step 4: Esegui i test**

```bash
cd telemetry-analyzer && python -m pytest tests/test_loading.py -v
```

Expected: 6 PASS.

- [ ] **Step 5: Commit**

```bash
git add telemetry-analyzer/analyzer/loading.py telemetry-analyzer/tests/test_loading.py
git commit -m "Aggiunge caricamento CSV e rilevamento gap/duplicati/timestamp irregolari"
```

---

### Task 3: `validation.py` — Hampel z-score, rate-of-change, persistenza

**Files:**
- Create: `telemetry-analyzer/analyzer/validation.py`
- Test: `telemetry-analyzer/tests/test_validation.py`

**Interfaces:**
- Consumes: `analyzer.config.HAMPEL_WINDOW`, `MAX_RATE`, `PERSIST_MIN_SAMPLES`, `PERSIST_TOLERANCE`.
- Produces: `hampel_z(series: pd.Series, window: int = None) -> tuple[pd.Series, pd.Series]` (z, mediana locale); `rate_of_change(series, dt_s, max_rate) -> tuple[pd.Series, pd.Series]` (rate, exceeded); `detect_isolated_spike(series, med, min_samples=None, tolerance=None) -> pd.Series[bool]`; `score_signal(series: pd.Series, dt_s: pd.Series, signal_key: str) -> dict` con chiavi `'z'`, `'median'`, `'rate'`, `'rate_exceeded'`, `'isolated_spike'` (tutti `pd.Series` allineati all'indice di `series`). Usato da `filtering.py` (Task 5) per ciascuno dei 5 segnali in `config.SIGNALS`.

- [ ] **Step 1: Scrivi i test**

```python
# tests/test_validation.py
import pandas as pd
from analyzer.validation import hampel_z, rate_of_change, detect_isolated_spike, score_signal
from analyzer import config

def test_hampel_z_flags_isolated_spike_from_spec_example():
    # 18, 19, 21, 67, 20, 19 — il 67 deve avere z alto, gli altri z basso
    leans = pd.Series([18.0, 19.0, 21.0, 67.0, 20.0, 19.0, 18.0, 19.0, 20.0, 19.0])
    z, med = hampel_z(leans, window=7)
    assert z.iloc[3] > 5.0
    assert z.iloc[0] < 2.0
    assert z.iloc[5] < 2.0

def test_rate_of_change_detects_fast_transition():
    leans = pd.Series([18.0, 19.0, 90.0])
    dt_s = pd.Series([1.0, 1.0, 1.0])
    rate, exceeded = rate_of_change(leans, dt_s, max_rate=config.MAX_RATE['lean'])
    assert exceeded.iloc[2]
    assert not exceeded.iloc[1]

def test_detect_isolated_spike_matches_lean_example():
    leans = pd.Series([18.0, 19.0, 21.0, 67.0, 20.0, 19.0, 18.0, 19.0, 20.0, 19.0])
    _, med = hampel_z(leans, window=7)
    isolated = detect_isolated_spike(leans, med)
    assert isolated.iloc[3] == True

def test_detect_isolated_spike_matches_accel_coherent_example():
    # 0.1,0.2,1.4,0.2,0.1 (spike) seguito da 0.8,1.1,1.4,1.2,0.9 (evento coerente)
    fwd = pd.Series([0.1, 0.2, 1.4, 0.2, 0.1, 0.15, 0.8, 1.1, 1.4, 1.2, 0.9, 0.2])
    _, med = hampel_z(fwd, window=7)
    isolated = detect_isolated_spike(fwd, med)
    assert isolated.iloc[2] == True    # il picco 1.4 isolato è uno spike
    assert isolated.iloc[8] == False   # il picco 1.4 nell'evento coerente non lo è

def test_score_signal_returns_all_expected_series():
    leans = pd.Series([18.0, 19.0, 21.0, 67.0, 20.0, 19.0, 18.0, 19.0, 20.0, 19.0])
    dt_s = pd.Series([None, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
    result = score_signal(leans, dt_s, 'lean')
    for key in ('z', 'median', 'rate', 'rate_exceeded', 'isolated_spike'):
        assert key in result
        assert len(result[key]) == len(leans)
    assert result['isolated_spike'].iloc[3] == True
```

- [ ] **Step 2: Verifica che i test falliscano**

```bash
cd telemetry-analyzer && python -m pytest tests/test_validation.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'analyzer.validation'`.

- [ ] **Step 3: Scrivi `analyzer/validation.py`**

```python
"""Punteggio robusto per-segnale: Hampel z-score, rate-of-change, persistenza
(spec sezioni 2-4). Stessa logica applicata indipendentemente a ciascuno dei 5 segnali —
la persistenza qui è anche il criterio "spike isolato vs evento coerente" usato per le
accelerazioni (spec sezione 4): è la stessa distinzione, applicata uniformemente."""
import numpy as np
import pandas as pd

from analyzer import config


def rolling_median_mad(series, window):
    med = series.rolling(window, center=True, min_periods=1).median()
    mad = (series - med).abs().rolling(window, center=True, min_periods=1).median()
    return med, mad


def hampel_z(series, window=None):
    """z = |x - mediana_locale| / (1.4826 * MAD_locale). 1.4826 rende la MAD uno
    stimatore consistente della deviazione standard per dati gaussiani — costante
    standard del filtro di Hampel, non un valore arbitrario."""
    window = window or config.HAMPEL_WINDOW
    med, mad = rolling_median_mad(series, window)
    sigma = 1.4826 * mad
    dev = (series - med).abs()
    z = pd.Series(0.0, index=series.index)
    has_sigma = sigma > 0
    z[has_sigma] = dev[has_sigma] / sigma[has_sigma]
    # finestra piattissima (MAD=0) ma il campione si discosta comunque dalla mediana:
    # deviazione "infinita" in termini robusti, non un errore numerico da ignorare
    flat_but_deviant = (~has_sigma) & (dev > 1e-9)
    z[flat_but_deviant] = np.inf
    return z, med


def rate_of_change(series, dt_s, max_rate):
    """Rate = |Δvalore| / Δt. A ~1Hz è una stima grossolana (variazione nell'ultimo
    secondo, non una vera derivata istantanea) — mai usata da sola (spec sezione 2b)."""
    delta = series.diff().abs()
    dt_safe = dt_s.replace(0, np.nan)
    rate = (delta / dt_safe).fillna(0.0)
    exceeded = rate > max_rate
    return rate, exceeded


def detect_isolated_spike(series, med, min_samples=None, tolerance=None):
    """Un campione è "spike isolato" se la sua deviazione dalla mediana locale non
    persiste (entro `tolerance` della propria ampiezza) in almeno uno dei
    `min_samples` campioni successivi (spec sezione 2c)."""
    min_samples = min_samples if min_samples is not None else config.PERSIST_MIN_SAMPLES
    tolerance = tolerance if tolerance is not None else config.PERSIST_TOLERANCE
    n = len(series)
    dev = (series - med).abs()
    values = dev.to_numpy()
    isolated = pd.Series(False, index=series.index)
    result = isolated.to_numpy()
    for i in range(n):
        dev_i = values[i]
        if not np.isfinite(dev_i) or dev_i <= 1e-9:
            continue  # non è un candidato outlier, "persistenza" non si applica
        persists = False
        for k in range(1, min_samples + 1):
            j = i + k
            if j >= n:
                break
            if values[j] >= tolerance * dev_i:
                persists = True
                break
        result[i] = not persists
    return pd.Series(result, index=series.index)


def score_signal(series, dt_s, signal_key):
    """Combina Hampel z, rate-of-change e persistenza per un segnale. `signal_key`
    è una chiave di `config.SIGNALS` ('lean', 'pitch', 'accel_fwd', 'accel_lat',
    'accel_vert'), usata per selezionare la soglia di rate in `config.MAX_RATE`."""
    z, med = hampel_z(series)
    rate, rate_exceeded = rate_of_change(series, dt_s, config.MAX_RATE[signal_key])
    isolated_spike = detect_isolated_spike(series, med)
    return {
        'z': z, 'median': med, 'rate': rate,
        'rate_exceeded': rate_exceeded, 'isolated_spike': isolated_spike,
    }
```

- [ ] **Step 4: Esegui i test**

```bash
cd telemetry-analyzer && python -m pytest tests/test_validation.py -v
```

Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add telemetry-analyzer/analyzer/validation.py telemetry-analyzer/tests/test_validation.py
git commit -m "Aggiunge validazione robusta per-segnale (Hampel z-score, rate, persistenza)"
```

---

### Task 4: `fusion.py` — regole cross-sensor e caso pitch ambiguo

**Files:**
- Create: `telemetry-analyzer/analyzer/fusion.py`
- Test: `telemetry-analyzer/tests/test_fusion.py`

**Interfaces:**
- Consumes: `analyzer.config.BRAKE_ENTER_G`, `ACCEL_ENTER_G`, `HEADING_CHANGE_MIN_DEG`, `LEAN_CROSS_ACCEL_LAT_MIN`, `VERT_EVENT_MIN_G`, `PITCH_EXTREME_DEG`, `PITCH_CROSS_ACCEL_VERT_MIN`.
- Produces: `circular_diff_deg(heading_deg: pd.Series) -> pd.Series` (differenza firmata consecutiva, gestisce il wraparound 0-360°); `heading_change_window(heading_deg, window_samples=5) -> pd.Series` (somma mobile di |Δheading|); `detect_braking(accel_fwd_g, speed_kmh) -> pd.Series[bool]`; `detect_accelerating(accel_fwd_g, speed_kmh) -> pd.Series[bool]`; `detect_curve(heading_deg, accel_lat_g, lean_deg) -> pd.Series[bool]`; `detect_vertical_event(accel_vert_g) -> pd.Series[bool]`; `detect_pitch_ambiguous(pitch_deg, accel_vert_g) -> pd.Series[bool]`; `cross_sensor_corroboration(df: pd.DataFrame) -> dict[str, pd.Series[bool]]` con chiavi `'lean'`, `'pitch'`, `'accel_fwd'`, `'accel_lat'`, `'accel_vert'` (booleano per campione: quel segnale è corroborato da altri sensori in quel punto). `df` deve avere le colonne `heading_deg`, `accel_lat_g`, `lean_deg`, `speed_kmh`, `accel_fwd_g`, `pitch_deg`, `accel_vert_g`. Usato da `filtering.py` (Task 5) per il termine `W_CROSS` della confidence e da `events.py` (Task 6) come base per la macchina a stati.

- [ ] **Step 1: Scrivi i test**

```python
# tests/test_fusion.py
import pandas as pd
from analyzer.fusion import (
    circular_diff_deg, heading_change_window, detect_braking, detect_accelerating,
    detect_curve, detect_vertical_event, detect_pitch_ambiguous, cross_sensor_corroboration,
)
from tests.fixtures import build_scenario_rows
import pandas as pd


def _df_from_scenario(name):
    rows = build_scenario_rows(name)
    df = pd.DataFrame(rows)
    return df


def test_circular_diff_handles_wraparound():
    heading = pd.Series([350.0, 355.0, 5.0, 10.0])
    diff = circular_diff_deg(heading)
    assert abs(diff.iloc[2] - 10.0) < 0.01  # 355 -> 5 e' +10, non -350

def test_detect_braking_true_when_speed_drops_and_decel():
    df = _df_from_scenario('curve_clear_apex')
    braking = detect_braking(df['accel_fwd_g'], df['speed_kmh'])
    assert braking.iloc[2] or braking.iloc[3]  # decelerazione in ingresso curva

def test_detect_curve_true_during_curve_scenario():
    df = _df_from_scenario('curve_clear_apex')
    curve = detect_curve(df['heading_deg'], df['accel_lat_g'], df['lean_deg'])
    assert curve.iloc[3] or curve.iloc[4]  # vicino all'apice, lean alto e heading in variazione

def test_detect_curve_false_on_straight_line():
    df = _df_from_scenario('normal')
    curve = detect_curve(df['heading_deg'], df['accel_lat_g'], df['lean_deg'])
    assert not curve.any()

def test_detect_pitch_ambiguous_flags_extreme_plus_vertical():
    df = _df_from_scenario('pitch_ambiguous_event')
    ambiguous = detect_pitch_ambiguous(df['pitch_deg'], df['accel_vert_g'])
    assert ambiguous.iloc[5] == True
    assert ambiguous.iloc[0] == False

def test_cross_sensor_corroboration_returns_all_signal_keys():
    df = _df_from_scenario('curve_clear_apex')
    result = cross_sensor_corroboration(df)
    for key in ('lean', 'pitch', 'accel_fwd', 'accel_lat', 'accel_vert'):
        assert key in result
        assert len(result[key]) == len(df)

def test_cross_sensor_corroboration_lean_true_during_curve():
    df = _df_from_scenario('curve_clear_apex')
    result = cross_sensor_corroboration(df)
    assert result['lean'].iloc[3] or result['lean'].iloc[4]
```

- [ ] **Step 2: Verifica che i test falliscano**

```bash
cd telemetry-analyzer && python -m pytest tests/test_fusion.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'analyzer.fusion'`.

- [ ] **Step 3: Scrivi `analyzer/fusion.py`**

```python
"""Cross sensor validation (spec sezione 5) e caso pitch estremo + evento
verticale (spec sezione 3)."""
import numpy as np
import pandas as pd

from analyzer import config


def circular_diff_deg(heading_deg):
    """Differenza firmata tra campioni consecutivi di heading, in (-180, 180],
    gestendo correttamente il passaggio 359->0 (non e' un salto di -359)."""
    raw = heading_deg.diff()
    wrapped = (raw + 180) % 360 - 180
    return wrapped


def heading_change_window(heading_deg, window_samples=5):
    """Somma mobile di |Δheading| — proxy di "quanto si sta girando" nell'ultimo
    tratto, robusta al wraparound grazie a circular_diff_deg."""
    step = circular_diff_deg(heading_deg).fillna(0.0)
    return step.abs().rolling(window_samples, center=True, min_periods=1).sum()


def _speed_trend(speed_kmh, window_samples=3):
    return speed_kmh.diff(window_samples)


def detect_braking(accel_fwd_g, speed_kmh):
    """Frenata: velocita' in calo su una finestra breve E decelerazione oltre soglia."""
    trend = _speed_trend(speed_kmh)
    return (trend < 0).fillna(False) & (accel_fwd_g <= config.BRAKE_ENTER_G)


def detect_accelerating(accel_fwd_g, speed_kmh):
    """Accelerazione: velocita' in aumento E accelerazione positiva oltre soglia."""
    trend = _speed_trend(speed_kmh)
    return (trend > 0).fillna(False) & (accel_fwd_g >= config.ACCEL_ENTER_G)


def detect_curve(heading_deg, accel_lat_g, lean_deg):
    """Curva: heading cambia oltre soglia, accelerazione laterale significativa,
    segno del lean coerente con la direzione del cambio di heading. Convenzione:
    lean positivo = SX, heading in CALO = sterzata a sinistra (senso orario del
    compass) — le due cose devono avere lo stesso segno atteso."""
    change = heading_change_window(heading_deg)
    lat_significant = accel_lat_g.abs() >= config.LEAN_CROSS_ACCEL_LAT_MIN
    step = circular_diff_deg(heading_deg).fillna(0.0)
    # media mobile del passo di heading per un segno piu' stabile del solo ultimo campione
    step_trend = step.rolling(5, center=True, min_periods=1).mean()
    expected_lean_sign = -np.sign(step_trend)  # heading in calo (sx) -> lean atteso positivo
    actual_lean_sign = np.sign(lean_deg)
    sign_consistent = (
        (expected_lean_sign == actual_lean_sign)
        | (step_trend.abs() < 0.5)
        | (lean_deg.abs() < 2.0)
    )
    return (change >= config.HEADING_CHANGE_MIN_DEG) & lat_significant & sign_consistent


def detect_vertical_event(accel_vert_g):
    """Evento verticale (buca/dosso): accelerazione verticale netta oltre soglia."""
    return accel_vert_g.abs() >= config.VERT_EVENT_MIN_G


def detect_pitch_ambiguous(pitch_deg, accel_vert_g):
    """Pitch estremo isolato E coincidente (±1 campione) con un forte evento
    verticale: non e' classificabile con certezza come errore ne' come evento
    reale (spec sezione 3) — mai RED diretto, sempre un flag dedicato."""
    extreme = pitch_deg.abs() >= config.PITCH_EXTREME_DEG
    vertical = accel_vert_g.abs() >= config.PITCH_CROSS_ACCEL_VERT_MIN
    vertical_nearby = vertical | vertical.shift(1).fillna(False) | vertical.shift(-1).fillna(False)
    return extreme & vertical_nearby


def cross_sensor_corroboration(df):
    """Per ciascun segnale, un booleano per campione: e' corroborato da altri
    sensori in quel punto? Alimenta il bonus W_CROSS della confidence (Task 5)."""
    braking = detect_braking(df['accel_fwd_g'], df['speed_kmh'])
    accelerating = detect_accelerating(df['accel_fwd_g'], df['speed_kmh'])
    curve = detect_curve(df['heading_deg'], df['accel_lat_g'], df['lean_deg'])
    vertical = detect_vertical_event(df['accel_vert_g'])

    return {
        'lean': curve,
        'pitch': vertical,
        'accel_fwd': braking | accelerating,
        'accel_lat': curve,
        'accel_vert': vertical,
    }
```

- [ ] **Step 4: Esegui i test**

```bash
cd telemetry-analyzer && python -m pytest tests/test_fusion.py -v
```

Expected: 7 PASS. Se `test_detect_curve_true_during_curve_scenario` fallisce, verifica il segno di `heading`/`lean_deg` nella fixture `curve_clear_apex` (`tests/fixtures.py`, Task 1) — devono essere coerenti con la convenzione descritta nel docstring di `detect_curve`.

- [ ] **Step 5: Commit**

```bash
git add telemetry-analyzer/analyzer/fusion.py telemetry-analyzer/tests/test_fusion.py
git commit -m "Aggiunge le regole cross-sensor e il caso pitch ambiguo"
```

---

### Task 5: `filtering.py` — confidence, colonne filtrate, orchestrazione dei 5 segnali

**Files:**
- Create: `telemetry-analyzer/analyzer/filtering.py`
- Test: `telemetry-analyzer/tests/test_filtering.py`

**Interfaces:**
- Consumes: `analyzer.config.{Z_CAP,W_HAMPEL,W_RATE,W_SPIKE,W_GAP,W_CROSS,FLAG_GREEN_MIN,FLAG_YELLOW_MIN,NEAR_GAP_WINDOW_S,SIGNALS,SIGNAL_COLUMN}`; `analyzer.validation.score_signal`; `analyzer.fusion.cross_sensor_corroboration`, `detect_pitch_ambiguous`; `analyzer.loading.{load_csv,compute_time_deltas}`.
- Produces: `compute_confidence(z, rate_exceeded, isolated_spike, near_gap, cross_corroborated) -> float` (0-100); `build_reason(...) -> str`; `filter_signal(df, signal_key, dt_s, near_gap, corroborated) -> dict` con chiavi `'filtered'`, `'confidence'`, `'flag'`, `'reason'`, `'status'` (tutti `pd.Series`); `build_filtered_dataframe(df: pd.DataFrame) -> pd.DataFrame` — richiede che `df` abbia già `dt_s`/`gap_flag`/`dup_flag`/`irregular_flag` (output di `loading.compute_time_deltas`), ritorna una copia con 25 colonne aggiuntive (5 segnali × `{filtered,confidence,flag,reason,status}`), **stesso numero di righe di `df`**. Usato dal CLI (Task 12) per scrivere `filtered_telemetry.csv`, e da `events.py`/`curves.py` (Task 6-7) che leggono le colonne `*_filtered`.

- [ ] **Step 1: Scrivi i test**

```python
# tests/test_filtering.py
import pandas as pd
from analyzer.filtering import compute_confidence, build_filtered_dataframe
from analyzer.loading import compute_time_deltas
from analyzer import config
from tests.fixtures import build_scenario_rows


def _enriched_df(scenario):
    rows = build_scenario_rows(scenario)
    df = pd.DataFrame(rows)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return compute_time_deltas(df)


def test_compute_confidence_clean_sample_is_high():
    conf = compute_confidence(z=0.2, rate_exceeded=False, isolated_spike=False,
                               near_gap=False, cross_corroborated=False)
    assert conf >= config.FLAG_GREEN_MIN

def test_compute_confidence_isolated_spike_is_low():
    conf = compute_confidence(z=10.0, rate_exceeded=True, isolated_spike=True,
                               near_gap=False, cross_corroborated=False)
    assert conf < config.FLAG_YELLOW_MIN

def test_compute_confidence_cross_corroboration_raises_score():
    low = compute_confidence(z=8.0, rate_exceeded=False, isolated_spike=False,
                              near_gap=False, cross_corroborated=False)
    high = compute_confidence(z=8.0, rate_exceeded=False, isolated_spike=False,
                               near_gap=False, cross_corroborated=True)
    assert high > low

def test_build_filtered_dataframe_preserves_row_count():
    df = _enriched_df('lean_isolated_spike')
    out = build_filtered_dataframe(df)
    assert len(out) == len(df)

def test_build_filtered_dataframe_has_all_columns():
    df = _enriched_df('normal')
    out = build_filtered_dataframe(df)
    for signal in config.SIGNALS:
        for suffix in ('filtered', 'confidence', 'flag', 'reason', 'status'):
            assert f'{signal}_{suffix}' in out.columns

def test_build_filtered_dataframe_isolated_spike_gets_red_and_replaced_value():
    df = _enriched_df('lean_isolated_spike')
    out = build_filtered_dataframe(df)
    assert out['lean_flag'].iloc[3] == 'RED'
    assert out['lean_status'].iloc[3] == 'FILTERED'
    assert abs(out['lean_filtered'].iloc[3] - 67.0) > 5.0  # sostituito, non più il raw

def test_build_filtered_dataframe_green_sample_keeps_raw_value():
    df = _enriched_df('normal')
    out = build_filtered_dataframe(df)
    assert out['lean_flag'].iloc[5] == 'GREEN'
    assert out['lean_filtered'].iloc[5] == out['lean_deg'].iloc[5]
    assert out['lean_status'].iloc[5] == 'MEASURED'

def test_build_filtered_dataframe_pitch_ambiguous_keeps_raw_and_is_yellow():
    df = _enriched_df('pitch_ambiguous_event')
    out = build_filtered_dataframe(df)
    assert out['pitch_flag'].iloc[5] == 'YELLOW'
    assert out['pitch_filtered'].iloc[5] == out['pitch_deg'].iloc[5]
    assert 'POSSIBILE EVENTO REALE' in out['pitch_reason'].iloc[5]
```

- [ ] **Step 2: Verifica che i test falliscano**

```bash
cd telemetry-analyzer && python -m pytest tests/test_filtering.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'analyzer.filtering'`.

- [ ] **Step 3: Scrivi `analyzer/filtering.py`**

```python
"""Confidence score e colonne filtrate (spec sezioni 6-7, 11)."""
import numpy as np
import pandas as pd

from analyzer import config, validation, fusion


def _flag_from_confidence(confidence):
    if confidence >= config.FLAG_GREEN_MIN:
        return 'GREEN'
    if confidence >= config.FLAG_YELLOW_MIN:
        return 'YELLOW'
    return 'RED'


def _near_gap_mask(df, window_s):
    """Un campione e' "vicino a un gap" se dista, in tempo, meno di `window_s`
    secondi da un campione la cui transizione e' stata marcata gap_flag=True
    (spec sezione 6, NEAR_GAP_WINDOW_S)."""
    gap_indices = df.index[df['gap_flag'].fillna(False)]
    near = pd.Series(False, index=df.index)
    if len(gap_indices) == 0:
        return near
    timestamps = df['timestamp']
    for gi in gap_indices:
        gap_ts = timestamps.loc[gi]
        close = (timestamps - gap_ts).abs().dt.total_seconds() <= window_s
        near = near | close
    return near


def compute_confidence(z, rate_exceeded, isolated_spike, near_gap, cross_corroborated):
    """Spec sezione 6. z puo' essere np.inf (finestra piatta ma campione deviante):
    in quel caso il termine Hampel satura al massimo (z_term=1.0)."""
    z_term = 1.0 if not np.isfinite(z) else min(z, config.Z_CAP) / config.Z_CAP
    confidence = 100.0
    confidence -= config.W_HAMPEL * z_term
    confidence -= config.W_RATE * (1.0 if rate_exceeded else 0.0)
    confidence -= config.W_SPIKE * (1.0 if isolated_spike else 0.0)
    confidence -= config.W_GAP * (1.0 if near_gap else 0.0)
    confidence += config.W_CROSS * (1.0 if cross_corroborated else 0.0)
    return float(np.clip(confidence, 0.0, 100.0))


def build_reason(z, rate_exceeded, isolated_spike, near_gap, cross_corroborated, pitch_ambiguous=False):
    if pitch_ambiguous:
        return ('POSSIBILE EVENTO REALE + POSSIBILE ERRORE ORIENTAMENTO '
                '(pitch estremo coincidente con un forte evento verticale)')
    parts = []
    if not np.isfinite(z):
        parts.append('deviazione robusta massima (finestra locale piatta ma campione deviante)')
    elif z > config.Z_CAP:
        parts.append(f'z={z:.1f} oltre soglia robusta')
    elif z > 2.0:
        parts.append(f'z={z:.1f} moderatamente elevato')
    if rate_exceeded:
        parts.append('velocità di variazione oltre soglia')
    if isolated_spike:
        parts.append('pattern spike isolato (non persiste nei campioni successivi)')
    if near_gap:
        parts.append('vicino a un gap temporale')
    if cross_corroborated:
        parts.append('corroborato da altri sensori')
    return '; '.join(parts) if parts else 'nessuna anomalia rilevata'


def filter_signal(df, signal_key, dt_s, near_gap, corroborated):
    column = config.SIGNAL_COLUMN[signal_key]
    series = df[column]
    scored = validation.score_signal(series, dt_s, signal_key)

    n = len(series)
    pitch_ambiguous_mask = (
        fusion.detect_pitch_ambiguous(df['pitch_deg'], df['accel_vert_g']).to_numpy()
        if signal_key == 'pitch' else np.zeros(n, dtype=bool)
    )

    z_arr = scored['z'].to_numpy()
    med_arr = scored['median'].to_numpy()
    rate_exceeded_arr = scored['rate_exceeded'].to_numpy()
    isolated_spike_arr = scored['isolated_spike'].to_numpy()
    near_gap_arr = near_gap.to_numpy()
    corroborated_arr = corroborated.to_numpy()
    raw_arr = series.to_numpy()

    filtered = np.empty(n)
    confidence = np.empty(n)
    flag = np.empty(n, dtype=object)
    reason = np.empty(n, dtype=object)
    status = np.empty(n, dtype=object)

    for i in range(n):
        is_ambiguous = bool(pitch_ambiguous_mask[i])
        z_i = z_arr[i]
        rate_i = bool(rate_exceeded_arr[i])
        spike_i = bool(isolated_spike_arr[i])
        gap_i = bool(near_gap_arr[i])
        cross_i = bool(corroborated_arr[i]) or is_ambiguous

        conf_i = compute_confidence(z_i, rate_i, spike_i, gap_i, cross_i)
        reason_i = build_reason(z_i, rate_i, spike_i, gap_i, cross_i, pitch_ambiguous=is_ambiguous)

        if is_ambiguous:
            # spec sezione 3: mai RED diretto, mai eliminato — sempre YELLOW, valore
            # raw mantenuto (non sostituito), confidence abbassata ma non azzerata
            flag_i = 'YELLOW'
            conf_i = min(conf_i, config.FLAG_YELLOW_MIN + 15.0)
            filtered_i = raw_arr[i]
            status_i = 'MEASURED'
        else:
            flag_i = _flag_from_confidence(conf_i)
            if flag_i == 'GREEN':
                filtered_i = raw_arr[i]
                status_i = 'MEASURED'
            elif pd.isna(med_arr[i]):
                # caso limite, praticamente irraggiungibile con min_periods=1: nessuna
                # stima robusta disponibile, non si inventa un valore
                filtered_i = raw_arr[i]
                status_i = 'INVALID'
            else:
                filtered_i = med_arr[i]
                status_i = 'FILTERED'

        filtered[i] = filtered_i
        confidence[i] = conf_i
        flag[i] = flag_i
        reason[i] = reason_i
        status[i] = status_i

    return {
        'filtered': pd.Series(filtered, index=df.index),
        'confidence': pd.Series(confidence, index=df.index),
        'flag': pd.Series(flag, index=df.index),
        'reason': pd.Series(reason, index=df.index),
        'status': pd.Series(status, index=df.index),
    }


def build_filtered_dataframe(df):
    """`df` deve gia' avere dt_s/gap_flag/dup_flag/irregular_flag (da
    loading.compute_time_deltas). Ritorna una copia di `df` con 25 colonne
    aggiuntive (5 segnali x 5 metriche), stesso numero di righe di `df`."""
    out = df.copy()
    dt_s = df['dt_s']
    near_gap = _near_gap_mask(df, config.NEAR_GAP_WINDOW_S)
    corroboration = fusion.cross_sensor_corroboration(df)

    for signal_key in config.SIGNALS:
        result = filter_signal(df, signal_key, dt_s, near_gap, corroboration[signal_key])
        out[f'{signal_key}_filtered'] = result['filtered']
        out[f'{signal_key}_confidence'] = result['confidence']
        out[f'{signal_key}_flag'] = result['flag']
        out[f'{signal_key}_reason'] = result['reason']
        out[f'{signal_key}_status'] = result['status']

    return out
```

- [ ] **Step 4: Esegui i test**

```bash
cd telemetry-analyzer && python -m pytest tests/test_filtering.py -v
```

Expected: 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add telemetry-analyzer/analyzer/filtering.py telemetry-analyzer/tests/test_filtering.py
git commit -m "Aggiunge la formula di confidence e l'orchestrazione dei 5 segnali filtrati"
```

---

### Task 6: `events.py` — macchina a stati con isteresi

**Files:**
- Create: `telemetry-analyzer/analyzer/events.py`
- Test: `telemetry-analyzer/tests/test_events.py`

**Interfaces:**
- Consumes: `analyzer.config.{BRAKE_ENTER_G,BRAKE_EXIT_G,ACCEL_ENTER_G,ACCEL_EXIT_G,CURVE_EXIT_G,VERT_EVENT_MIN_G,LEAN_CROSS_ACCEL_LAT_MIN,SIGNALS}`; `analyzer.fusion.detect_curve`; colonne `*_filtered`/`*_flag`/`*_confidence` prodotte da `filtering.build_filtered_dataframe` (Task 5).
- Produces: `hysteresis_runs(enter_mask, exit_mask) -> list[tuple[int,int]]` (indici inclusivi start/end di ogni run); `detect_events(df: pd.DataFrame) -> list[dict]`, un dict per evento con chiavi `t_start,t_end,duration_s,v_start,v_end,v_max,lean_max,accel_fwd_max,accel_lat_max,accel_vert_max,confidence,event_type` (`event_type` ∈ `{'FRENATA','ACCELERAZIONE','CURVA','EVENTO_VERTICALE','FRENATA_CURVA','ANOMALIA_SENSORE'}`); `events_to_dataframe(events: list[dict]) -> pd.DataFrame`. Usato da `curves.py` (Task 7, filtra sugli eventi `'CURVA'`/`'FRENATA_CURVA'`) e dal CLI (Task 12) per scrivere `events.csv`.

- [ ] **Step 1: Scrivi i test**

```python
# tests/test_events.py
import pandas as pd
from datetime import datetime, timedelta
from analyzer.events import hysteresis_runs, detect_events, events_to_dataframe
from analyzer import config


def _minimal_filtered_df(accel_fwd, accel_lat=None, accel_vert=None, lean=None,
                          speed=None, heading=None):
    n = len(accel_fwd)
    start = datetime(2026, 8, 16, 10, 0, 0)
    accel_lat = accel_lat or [0.02] * n
    accel_vert = accel_vert or [0.02] * n
    lean = lean or [1.0] * n
    speed = speed or [40.0] * n
    heading = heading or [90.0] * n
    df = pd.DataFrame({
        'timestamp': [start + timedelta(seconds=i) for i in range(n)],
        'speed_kmh': speed,
        'heading_deg': heading,
        'accel_fwd_filtered': accel_fwd,
        'accel_lat_filtered': accel_lat,
        'accel_vert_filtered': accel_vert,
        'lean_filtered': lean,
    })
    for signal in config.SIGNALS:
        df[f'{signal}_confidence'] = 90.0
        df[f'{signal}_flag'] = 'GREEN'
    return df


def test_hysteresis_runs_single_run():
    enter = [False, True, True, False, False]
    exitm = [False, True, True, True, False]
    assert hysteresis_runs(enter, exitm) == [(1, 3)]

def test_hysteresis_runs_no_flapping_within_exit_band():
    enter = [False, True, False, False, False]
    exitm = [False, True, True, True, False]
    assert hysteresis_runs(enter, exitm) == [(1, 3)]

def test_detect_events_finds_braking():
    df = _minimal_filtered_df(accel_fwd=[0.0, -0.3, -0.35, -0.2, 0.0, 0.0])
    events = detect_events(df)
    braking = [e for e in events if e['event_type'] == 'FRENATA']
    assert len(braking) == 1
    assert braking[0]['accel_fwd_max'] >= 0.3

def test_detect_events_finds_acceleration():
    df = _minimal_filtered_df(accel_fwd=[0.0, 0.3, 0.35, 0.2, 0.0])
    events = detect_events(df)
    accelerating = [e for e in events if e['event_type'] == 'ACCELERAZIONE']
    assert len(accelerating) == 1

def test_detect_events_merges_braking_and_curve_overlap():
    df = _minimal_filtered_df(
        accel_fwd=[0.0, -0.3, -0.3, 0.0, 0.0],
        accel_lat=[0.02, 0.3, 0.3, 0.02, 0.02],
        lean=[1.0, 15.0, 15.0, 1.0, 1.0],
        heading=[90.0, 80.0, 70.0, 65.0, 65.0],  # heading in calo -> coerente con lean SX (positivo)
    )
    events = detect_events(df)
    combined = [e for e in events if e['event_type'] == 'FRENATA_CURVA']
    solo_brake = [e for e in events if e['event_type'] == 'FRENATA']
    solo_curve = [e for e in events if e['event_type'] == 'CURVA']
    assert len(combined) == 1
    assert len(solo_brake) == 0
    assert len(solo_curve) == 0

def test_detect_events_finds_sensor_anomaly():
    df = _minimal_filtered_df(accel_fwd=[0.0] * 5)
    df.loc[2, 'lean_flag'] = 'RED'
    df.loc[2, 'pitch_flag'] = 'RED'
    events = detect_events(df)
    anomalies = [e for e in events if e['event_type'] == 'ANOMALIA_SENSORE']
    assert len(anomalies) == 1

def test_events_to_dataframe_empty_list_has_expected_columns():
    out = events_to_dataframe([])
    assert 'event_type' in out.columns
    assert len(out) == 0
```

- [ ] **Step 2: Verifica che i test falliscano**

```bash
cd telemetry-analyzer && python -m pytest tests/test_events.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'analyzer.events'`.

- [ ] **Step 3: Scrivi `analyzer/events.py`**

```python
"""Riconoscimento eventi con macchina a stati a isteresi (spec sezione 8)."""
import numpy as np
import pandas as pd

from analyzer import config, fusion


def hysteresis_runs(enter_mask, exit_mask):
    """`enter_mask` (piu' severa) e `exit_mask` (meno severa), stessa lunghezza.
    Un run inizia dove enter_mask e' True, continua finche' exit_mask resta True
    nei campioni successivi, termina al primo campione dove anche exit_mask e'
    False. Ritorna [(start_idx, end_idx), ...] indici inclusivi. Evita che un
    evento "sfarfalli" dentro/fuori intorno alla sola soglia di ingresso."""
    enter = np.asarray(enter_mask, dtype=bool)
    exitm = np.asarray(exit_mask, dtype=bool)
    n = len(enter)
    runs = []
    i = 0
    while i < n:
        if enter[i]:
            start = i
            j = i
            while j + 1 < n and exitm[j + 1]:
                j += 1
            runs.append((start, j))
            i = j + 1
        else:
            i += 1
    return runs


def _event_stats(df, start, end, event_type, confidence_columns):
    window = df.iloc[start:end + 1]
    confidences = pd.concat([window[c] for c in confidence_columns])
    return {
        't_start': window['timestamp'].iloc[0],
        't_end': window['timestamp'].iloc[-1],
        'duration_s': (window['timestamp'].iloc[-1] - window['timestamp'].iloc[0]).total_seconds(),
        'v_start': float(window['speed_kmh'].iloc[0]),
        'v_end': float(window['speed_kmh'].iloc[-1]),
        'v_max': float(window['speed_kmh'].max()),
        'lean_max': float(window['lean_filtered'].abs().max()),
        'accel_fwd_max': float(window['accel_fwd_filtered'].abs().max()),
        'accel_lat_max': float(window['accel_lat_filtered'].abs().max()),
        'accel_vert_max': float(window['accel_vert_filtered'].abs().max()),
        'confidence': float(confidences.mean()) if len(confidences) else 0.0,
        'event_type': event_type,
    }


def detect_events(df):
    """`df` deve avere le colonne *_filtered/*_flag/*_confidence (output di
    filtering.build_filtered_dataframe) piu' `heading_deg`/`speed_kmh`/`timestamp`
    dal CSV originale. Ritorna una lista di dict (vedi _event_stats)."""
    fwd = df['accel_fwd_filtered']
    lat = df['accel_lat_filtered']
    vert = df['accel_vert_filtered']

    brake_enter = (fwd <= config.BRAKE_ENTER_G).to_numpy()
    brake_exit = (fwd <= config.BRAKE_EXIT_G).to_numpy()
    accel_enter = (fwd >= config.ACCEL_ENTER_G).to_numpy()
    accel_exit = (fwd >= config.ACCEL_EXIT_G).to_numpy()
    # ingresso curva: condizione "Curva" completa di spec sezione 5 (heading + accel_lat
    # + segno lean coerente) sui segnali FILTRATI — uscita solo su accel_lat sotto soglia,
    # per non richiedere che l'heading continui a cambiare per tutta la durata della curva
    curve_enter = fusion.detect_curve(df['heading_deg'], lat, df['lean_filtered']).to_numpy()
    curve_exit = (lat.abs() >= config.CURVE_EXIT_G).to_numpy()
    vert_enter = (vert.abs() >= config.VERT_EVENT_MIN_G).to_numpy()

    brake_runs = [(s, e, 'FRENATA') for s, e in hysteresis_runs(brake_enter, brake_exit)]
    accel_runs = [(s, e, 'ACCELERAZIONE') for s, e in hysteresis_runs(accel_enter, accel_exit)]
    curve_runs = [(s, e, 'CURVA') for s, e in hysteresis_runs(curve_enter, curve_exit)]
    vert_runs = [(s, e, 'EVENTO_VERTICALE') for s, e in hysteresis_runs(vert_enter, vert_enter)]

    # frenata + curva combinata: overlap temporale, tag composito, non doppio conteggio
    combined = []
    used_brake, used_curve = set(), set()
    for bi, (bs, be, _) in enumerate(brake_runs):
        for ci, (cs, ce, _) in enumerate(curve_runs):
            if bs <= ce and cs <= be:
                combined.append((min(bs, cs), max(be, ce), 'FRENATA_CURVA'))
                used_brake.add(bi)
                used_curve.add(ci)
    brake_runs = [r for i, r in enumerate(brake_runs) if i not in used_brake]
    curve_runs = [r for i, r in enumerate(curve_runs) if i not in used_curve]

    dynamic_runs = brake_runs + accel_runs + curve_runs + vert_runs + combined
    events = [
        _event_stats(df, s, e, t, ['accel_fwd_confidence', 'accel_lat_confidence',
                                    'accel_vert_confidence', 'lean_confidence'])
        for s, e, t in dynamic_runs
    ]

    # anomalia sensore: >=2 segnali RED sullo stesso campione (spec sezione 8)
    red_count = sum((df[f'{s}_flag'] == 'RED').astype(int) for s in config.SIGNALS)
    anomaly_mask = (red_count >= 2).to_numpy()
    for s, e in hysteresis_runs(anomaly_mask, anomaly_mask):
        events.append(_event_stats(df, s, e, 'ANOMALIA_SENSORE',
                                    [f'{sig}_confidence' for sig in config.SIGNALS]))

    events.sort(key=lambda ev: ev['t_start'])
    return events


def events_to_dataframe(events):
    columns = ['t_start', 't_end', 'duration_s', 'v_start', 'v_end', 'v_max', 'lean_max',
               'accel_fwd_max', 'accel_lat_max', 'accel_vert_max', 'confidence', 'event_type']
    if not events:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(events)[columns]
```

- [ ] **Step 4: Esegui i test**

```bash
cd telemetry-analyzer && python -m pytest tests/test_events.py -v
```

Expected: 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add telemetry-analyzer/analyzer/events.py telemetry-analyzer/tests/test_events.py
git commit -m "Aggiunge il riconoscimento eventi con macchina a stati a isteresi"
```

---

### Task 7: `curves.py` — segmentazione curve e logica apex

**Files:**
- Create: `telemetry-analyzer/analyzer/curves.py`
- Test: `telemetry-analyzer/tests/test_curves.py`

**Interfaces:**
- Consumes: `analyzer.config.{APEX_TOLERANCE_S,BRAKE_ENTER_G,ACCEL_ENTER_G}`; output di `events.detect_events` (Task 6); colonne `*_filtered`/`*_confidence` di `filtering.build_filtered_dataframe` (Task 5).
- Produces: `segment_curve(df: pd.DataFrame, start_idx: int, end_idx: int) -> dict` con chiavi `t_start,t_end,duration_s,v_entry,v_min,v_exit,lean_max_filtered,lean_max_confidence,accel_lat_max_filtered,accel_fwd_min_entry,braking_detected,turn_in_time,apex_status,apex_time,throttle_reopening_detected` (`apex_status` ∈ `{'CONFIRMED','UNCERTAIN'}`, `apex_time` è `None` quando `UNCERTAIN`); `detect_curves(df, events: list[dict]) -> list[dict]` (filtra `events` sui tipi `'CURVA'`/`'FRENATA_CURVA'`); `curves_to_dataframe(curves: list[dict]) -> pd.DataFrame`. Usato dal CLI (Task 12) per scrivere `curves.csv`.

- [ ] **Step 1: Scrivi i test**

```python
# tests/test_curves.py
import pandas as pd
from analyzer.loading import load_csv, compute_time_deltas
from analyzer.filtering import build_filtered_dataframe
from analyzer.events import detect_events
from analyzer.curves import detect_curves, curves_to_dataframe
from tests.fixtures import make_ride_csv


def _filtered_df_and_events(scenario, tmp_path):
    csv_path = tmp_path / 'ride.csv'
    make_ride_csv(csv_path, scenario)
    df = build_filtered_dataframe(compute_time_deltas(load_csv(str(csv_path))))
    events = detect_events(df)
    return df, events

def test_detect_curves_clear_apex_is_confirmed(tmp_path):
    df, events = _filtered_df_and_events('curve_clear_apex', tmp_path)
    curves = detect_curves(df, events)
    assert len(curves) >= 1
    assert any(c['apex_status'] == 'CONFIRMED' for c in curves)

def test_detect_curves_uncertain_apex_is_flagged(tmp_path):
    df, events = _filtered_df_and_events('curve_uncertain_apex', tmp_path)
    curves = detect_curves(df, events)
    assert len(curves) >= 1
    assert any(c['apex_status'] == 'UNCERTAIN' for c in curves)
    uncertain = [c for c in curves if c['apex_status'] == 'UNCERTAIN'][0]
    assert uncertain['apex_time'] is None

def test_detect_curves_reports_v_min_and_v_entry(tmp_path):
    df, events = _filtered_df_and_events('curve_clear_apex', tmp_path)
    curves = detect_curves(df, events)
    curve = curves[0]
    assert curve['v_min'] <= curve['v_entry']

def test_detect_curves_ignores_non_curve_events(tmp_path):
    df, events = _filtered_df_and_events('accel_coherent_event', tmp_path)
    curves = detect_curves(df, events)
    assert curves == []

def test_curves_to_dataframe_empty_list_has_expected_columns():
    out = curves_to_dataframe([])
    assert 'apex_status' in out.columns
    assert len(out) == 0
```

- [ ] **Step 2: Verifica che i test falliscano**

```bash
cd telemetry-analyzer && python -m pytest tests/test_curves.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'analyzer.curves'`.

- [ ] **Step 3: Scrivi `analyzer/curves.py`**

```python
"""Segmentazione delle curve in fasi e logica apex (spec sezione 9)."""
import numpy as np
import pandas as pd

from analyzer import config


def _row_index_for_time(df, ts):
    return int((df['timestamp'] - ts).abs().to_numpy().argmin())


def segment_curve(df, start_idx, end_idx):
    """Segmenta una finestra di curva (indici inclusivi in `df`) nelle fasi
    ENTRY/BRAKING/TURN-IN/APEX/EXIT. Non inventa un apex se velocita' minima e
    lean massimo non coincidono entro APEX_TOLERANCE_S (spec sezione 9)."""
    window = df.iloc[start_idx:end_idx + 1].reset_index(drop=True)
    n = len(window)

    speed = window['speed_kmh']
    lean_abs = window['lean_filtered'].abs()
    fwd = window['accel_fwd_filtered']

    v_min_pos = int(speed.to_numpy().argmin())
    lean_max_pos = int(lean_abs.to_numpy().argmax())

    t_min_speed = window['timestamp'].iloc[v_min_pos]
    t_max_lean = window['timestamp'].iloc[lean_max_pos]
    gap_s = abs((t_max_lean - t_min_speed).total_seconds())

    if gap_s <= config.APEX_TOLERANCE_S:
        apex_status = 'CONFIRMED'
        apex_pos = v_min_pos
        apex_time = window['timestamp'].iloc[apex_pos]
    else:
        apex_status = 'UNCERTAIN'
        apex_pos = None
        apex_time = None

    # TURN-IN: massima |d(lean)/dt| nella fase di ingresso (prima dell'apex, o del
    # minimo di velocita' se l'apex e' incerto — comunque un riferimento utile)
    entry_end = max(apex_pos if apex_pos is not None else v_min_pos, 1)
    lean_signed_entry = window['lean_filtered'].iloc[:entry_end + 1]
    dt_entry = window['timestamp'].diff().dt.total_seconds().iloc[:entry_end + 1]
    lean_rate = (lean_signed_entry.diff().abs() / dt_entry.replace(0, np.nan)).fillna(0.0)
    turn_in_pos = int(lean_rate.iloc[1:].to_numpy().argmax()) + 1 if len(lean_rate) > 1 else 0

    braking_detected = bool((fwd.iloc[:entry_end + 1] <= config.BRAKE_ENTER_G).any())
    accel_fwd_min_entry = float(fwd.iloc[:entry_end + 1].min())

    # riapertura gas: sempre un'inferenza (mai un fatto misurato direttamente) —
    # primo campione dopo l'apex/minimo velocita' in cui accel_fwd torna positivo
    exit_start = apex_pos if apex_pos is not None else v_min_pos
    throttle_reopening = False
    if exit_start < n - 1:
        after = fwd.iloc[exit_start + 1:]
        throttle_reopening = bool((after >= config.ACCEL_ENTER_G).any())

    return {
        't_start': window['timestamp'].iloc[0],
        't_end': window['timestamp'].iloc[-1],
        'duration_s': (window['timestamp'].iloc[-1] - window['timestamp'].iloc[0]).total_seconds(),
        'v_entry': float(speed.iloc[0]),
        'v_min': float(speed.min()),
        'v_exit': float(speed.iloc[-1]),
        'lean_max_filtered': float(lean_abs.max()),
        'lean_max_confidence': float(window['lean_confidence'].iloc[lean_max_pos]),
        'accel_lat_max_filtered': float(window['accel_lat_filtered'].abs().max()),
        'accel_fwd_min_entry': accel_fwd_min_entry,
        'braking_detected': braking_detected,
        'turn_in_time': window['timestamp'].iloc[turn_in_pos],
        'apex_status': apex_status,
        'apex_time': apex_time,
        'throttle_reopening_detected': throttle_reopening,
    }


def detect_curves(df, events):
    """Processa solo gli eventi di tipo 'CURVA'/'FRENATA_CURVA' da `events`
    (output di events.detect_events). Ritorna una lista di dict (segment_curve)."""
    curves = []
    for event in events:
        if event['event_type'] not in ('CURVA', 'FRENATA_CURVA'):
            continue
        start_idx = _row_index_for_time(df, event['t_start'])
        end_idx = _row_index_for_time(df, event['t_end'])
        curves.append(segment_curve(df, start_idx, end_idx))
    return curves


def curves_to_dataframe(curves):
    columns = ['t_start', 't_end', 'duration_s', 'v_entry', 'v_min', 'v_exit',
               'lean_max_filtered', 'lean_max_confidence', 'accel_lat_max_filtered',
               'accel_fwd_min_entry', 'braking_detected', 'turn_in_time',
               'apex_status', 'apex_time', 'throttle_reopening_detected']
    if not curves:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(curves)[columns]
```

- [ ] **Step 4: Esegui i test**

```bash
cd telemetry-analyzer && python -m pytest tests/test_curves.py -v
```

Expected: 5 PASS. Se `test_detect_curves_clear_apex_is_confirmed` o `..._uncertain_apex_is_flagged` non trovano nessuna curva, verifica con un breakpoint/stampa che `detect_events` produca almeno un evento `'CURVA'`/`'FRENATA_CURVA'` per quella fixture prima di sospettare `curves.py` — il problema più probabile è nella condizione di ingresso curva di `events.py` (Task 6), non qui.

- [ ] **Step 5: Commit**

```bash
git add telemetry-analyzer/analyzer/curves.py telemetry-analyzer/tests/test_curves.py
git commit -m "Aggiunge la segmentazione delle curve con logica apex CONFIRMED/UNCERTAIN"
```

---

### Task 8: `report/dashboard.py` + `report/charts.py` — riepilogo e grafici sincronizzati

**Files:**
- Create: `telemetry-analyzer/analyzer/report/dashboard.py`
- Create: `telemetry-analyzer/analyzer/report/charts.py`
- Test: `telemetry-analyzer/tests/test_report_dashboard_charts.py`

**Interfaces:**
- Consumes: `analyzer.config.SIGNALS`; output di `filtering.build_filtered_dataframe` (Task 5) e `events.detect_events` (Task 6).
- Produces: `dashboard.total_distance_m(df) -> float`; `dashboard.build_dashboard_stats(df, events: list[dict]) -> dict`; `dashboard.render_dashboard_html(stats: dict) -> str`; `charts.build_telemetry_figure(df) -> plotly.graph_objects.Figure`; `charts.render_telemetry_html(df) -> str` (frammento `<div>`, `include_plotlyjs=False` — il bundle Plotly viene incluso una sola volta dall'assemblaggio finale, Task 11). Usati da `report/assemble.py` (Task 11).

- [ ] **Step 1: Scrivi i test**

```python
# tests/test_report_dashboard_charts.py
from analyzer.loading import load_csv, compute_time_deltas
from analyzer.filtering import build_filtered_dataframe
from analyzer.events import detect_events
from analyzer.report.dashboard import build_dashboard_stats, render_dashboard_html, total_distance_m
from analyzer.report.charts import build_telemetry_figure, render_telemetry_html
from tests.fixtures import make_ride_csv


def _filtered_df(scenario, tmp_path):
    csv_path = tmp_path / 'ride.csv'
    make_ride_csv(csv_path, scenario)
    return build_filtered_dataframe(compute_time_deltas(load_csv(str(csv_path))))

def test_total_distance_m_positive_for_moving_ride(tmp_path):
    df = _filtered_df('normal', tmp_path)
    assert total_distance_m(df) > 0

def test_build_dashboard_stats_has_expected_keys(tmp_path):
    df = _filtered_df('normal', tmp_path)
    events = detect_events(df)
    stats = build_dashboard_stats(df, events)
    for key in ('duration_s', 'distance_km', 'speed_max_kmh', 'lean_max_raw',
                'lean_max_filtered', 'n_anomalies_red', 'n_gaps', 'overall_quality'):
        assert key in stats

def test_render_dashboard_html_contains_labels(tmp_path):
    df = _filtered_df('normal', tmp_path)
    events = detect_events(df)
    stats = build_dashboard_stats(df, events)
    html = render_dashboard_html(stats)
    assert 'Dashboard generale' in html
    assert 'Distanza GPS' in html

def test_build_telemetry_figure_has_one_subplot_title_per_signal(tmp_path):
    df = _filtered_df('lean_isolated_spike', tmp_path)
    fig = build_telemetry_figure(df)
    assert len(fig.layout.annotations) == 6

def test_render_telemetry_html_is_nonempty_div(tmp_path):
    df = _filtered_df('normal', tmp_path)
    html = render_telemetry_html(df)
    assert 'telemetry-charts' in html
    assert len(html) > 100
```

- [ ] **Step 2: Verifica che i test falliscano**

```bash
cd telemetry-analyzer && python -m pytest tests/test_report_dashboard_charts.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'analyzer.report.dashboard'`.

- [ ] **Step 3: Scrivi `analyzer/report/dashboard.py`**

```python
"""Dashboard generale del report (spec sezione 10, punto 1)."""
import numpy as np

from analyzer import config


def _distance_meters(lat1, lon1, lat2, lon2):
    """Approssimazione equirettangolare — stessa tecnica della PWA (adeguata per
    distanze brevi tra fix consecutivi, non per distanze globali)."""
    d_lon = (lon2 - lon1) * np.cos(np.radians(lat1)) * 111320
    d_lat = (lat2 - lat1) * 110540
    return float(np.hypot(d_lon, d_lat))


def total_distance_m(df):
    lat = df['lat'].to_numpy()
    lon = df['lon'].to_numpy()
    total = 0.0
    for i in range(1, len(lat)):
        total += _distance_meters(lat[i - 1], lon[i - 1], lat[i], lon[i])
    return total


def build_dashboard_stats(df, events):
    n = len(df)
    duration_s = (df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).total_seconds() if n > 1 else 0.0
    red_counts = {s: int((df[f'{s}_flag'] == 'RED').sum()) for s in config.SIGNALS}
    confidence_cols = [f'{s}_confidence' for s in config.SIGNALS]

    return {
        'duration_s': duration_s,
        'distance_km': total_distance_m(df) / 1000.0,
        'speed_max_kmh': float(df['speed_kmh'].max()) if n else 0.0,
        'speed_mean_kmh': float(df['speed_kmh'].mean()) if n else 0.0,
        'brake_max_g': float(df['accel_fwd_filtered'].min()) if n else 0.0,
        'accel_max_g': float(df['accel_fwd_filtered'].max()) if n else 0.0,
        'lat_max_g': float(df['accel_lat_filtered'].abs().max()) if n else 0.0,
        'lean_max_raw': float(df['lean_deg'].abs().max()) if n else 0.0,
        'lean_max_filtered': float(df['lean_filtered'].abs().max()) if n else 0.0,
        'n_events': len(events),
        'n_anomalies_red': sum(red_counts.values()),
        'n_gaps': int(df['gap_flag'].sum()),
        'overall_quality': float(df[confidence_cols].to_numpy().mean()) if n else 0.0,
    }


def render_dashboard_html(stats):
    minutes = int(stats['duration_s'] // 60)
    seconds = int(stats['duration_s'] % 60)
    cards = [
        ('Durata', f"{minutes}:{seconds:02d}"),
        ('Distanza GPS', f"{stats['distance_km']:.1f} km"),
        ('Velocità max', f"{stats['speed_max_kmh']:.0f} km/h"),
        ('Velocità media', f"{stats['speed_mean_kmh']:.0f} km/h"),
        ('Frenata massima', f"{stats['brake_max_g']:.2f} g"),
        ('Accelerazione massima', f"{stats['accel_max_g']:.2f} g"),
        ('Accel. laterale massima', f"{stats['lat_max_g']:.2f} g"),
        ('Lean massimo RAW', f"{stats['lean_max_raw']:.0f}°"),
        ('Lean massimo FILTERED', f"{stats['lean_max_filtered']:.0f}°"),
        ('Eventi rilevati', str(stats['n_events'])),
        ('Anomalie (RED)', str(stats['n_anomalies_red'])),
        ('Gap temporali', str(stats['n_gaps'])),
        ('Qualità sessione', f"{stats['overall_quality']:.0f}/100"),
    ]
    cards_html = ''.join(
        f'<div class="dash-card"><span class="label">{label}</span>'
        f'<span class="value">{value}</span></div>'
        for label, value in cards
    )
    return f'<section id="dashboard"><h2>Dashboard generale</h2><div class="dash-grid">{cards_html}</div></section>'
```

- [ ] **Step 4: Scrivi `analyzer/report/charts.py`**

```python
"""Grafici Plotly sincronizzati RAW+FILTERED per i 5 segnali (spec sezione 10, punto 2)."""
import plotly.graph_objects as go
from plotly.subplots import make_subplots

CHART_SPECS = [
    ('speed_kmh', None, 'Velocità (km/h)'),
    ('lean_deg', 'lean_filtered', 'Piega (°)'),
    ('pitch_deg', 'pitch_filtered', 'Beccheggio (°)'),
    ('accel_fwd_g', 'accel_fwd_filtered', 'Accel. longitudinale (g)'),
    ('accel_lat_g', 'accel_lat_filtered', 'Accel. laterale (g)'),
    ('accel_vert_g', 'accel_vert_filtered', 'Accel. verticale (g)'),
]


def build_telemetry_figure(df):
    fig = make_subplots(rows=len(CHART_SPECS), cols=1, shared_xaxes=True,
                         subplot_titles=[t for _, _, t in CHART_SPECS], vertical_spacing=0.04)
    x = df['timestamp']
    for row, (raw_col, filtered_col, title) in enumerate(CHART_SPECS, start=1):
        fig.add_trace(go.Scatter(x=x, y=df[raw_col], name=f'{title} (RAW)',
                                  line=dict(dash='dot', width=1), opacity=0.5), row=row, col=1)
        if filtered_col:
            fig.add_trace(go.Scatter(x=x, y=df[filtered_col], name=f'{title} (FILTERED)',
                                      line=dict(width=2)), row=row, col=1)
            signal_key = filtered_col.replace('_filtered', '')
            outliers = df[df[f'{signal_key}_flag'] == 'RED']
            if len(outliers):
                fig.add_trace(go.Scatter(x=outliers['timestamp'], y=outliers[raw_col], mode='markers',
                                          marker=dict(color='red', size=7, symbol='x'),
                                          name=f'{title} outlier'), row=row, col=1)
    fig.update_layout(height=220 * len(CHART_SPECS), showlegend=False,
                       title='Telemetria nel tempo (RAW tratteggiato, FILTERED pieno, outlier evidenziati)')
    return fig


def render_telemetry_html(df):
    fig = build_telemetry_figure(df)
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id='telemetry-charts')
```

- [ ] **Step 5: Esegui i test**

```bash
cd telemetry-analyzer && python -m pytest tests/test_report_dashboard_charts.py -v
```

Expected: 5 PASS.

- [ ] **Step 6: Commit**

```bash
git add telemetry-analyzer/analyzer/report/dashboard.py telemetry-analyzer/analyzer/report/charts.py telemetry-analyzer/tests/test_report_dashboard_charts.py
git commit -m "Aggiunge dashboard generale e grafici telemetria sincronizzati RAW+FILTERED"
```

---

### Task 9: `report/map_static.py` — mappa Folium statica colorata per velocità

**Files:**
- Create: `telemetry-analyzer/analyzer/report/map_static.py`
- Test: `telemetry-analyzer/tests/test_report_map_static.py`

**Interfaces:**
- Consumes: output di `filtering.build_filtered_dataframe` (Task 5), `events.detect_events` (Task 6).
- Produces: `_speed_to_color(speed: float, speed_min: float, speed_max: float) -> str` (hex); `build_static_map_html(df, events: list[dict]) -> str` (HTML Folium embeddabile). Usato da `report/assemble.py` (Task 11).

- [ ] **Step 1: Scrivi i test**

```python
# tests/test_report_map_static.py
from analyzer.loading import load_csv, compute_time_deltas
from analyzer.filtering import build_filtered_dataframe
from analyzer.events import detect_events
from analyzer.report.map_static import build_static_map_html, _speed_to_color
from tests.fixtures import make_ride_csv

def test_speed_to_color_returns_hex():
    color = _speed_to_color(50, 0, 100)
    assert color.startswith('#')
    assert len(color) == 7

def test_speed_to_color_handles_flat_range():
    color = _speed_to_color(50, 50, 50)
    assert color.startswith('#')

def test_build_static_map_html_contains_map_markup(tmp_path):
    csv_path = tmp_path / 'ride.csv'
    make_ride_csv(csv_path, 'curve_clear_apex')
    df = build_filtered_dataframe(compute_time_deltas(load_csv(str(csv_path))))
    events = detect_events(df)
    html = build_static_map_html(df, events)
    assert 'leaflet' in html.lower()
    assert len(html) > 500
```

- [ ] **Step 2: Verifica che i test falliscano**

```bash
cd telemetry-analyzer && python -m pytest tests/test_report_map_static.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'analyzer.report.map_static'`.

- [ ] **Step 3: Scrivi `analyzer/report/map_static.py`**

```python
"""Mappa statica Folium, colorata per velocità (spec sezione 10, punto 3a)."""
import folium


def _speed_to_color(speed, speed_min, speed_max):
    """Gradiente blu (lento) -> verde -> giallo -> rosso (veloce), a 3 tratti lineari."""
    if speed_max <= speed_min:
        ratio = 0.0
    else:
        ratio = (speed - speed_min) / (speed_max - speed_min)
    ratio = max(0.0, min(1.0, ratio))
    if ratio < 0.5:
        t = ratio / 0.5
        r, g, b = int(255 * t), int(100 + 155 * t), int(255 * (1 - t))
    else:
        t = (ratio - 0.5) / 0.5
        r, g, b = 255, int(255 * (1 - t)), 0
    return f'#{r:02x}{g:02x}{b:02x}'


_EVENT_ICONS = {
    'FRENATA': 'stop', 'ACCELERAZIONE': 'forward', 'CURVA': 'refresh',
    'FRENATA_CURVA': 'exclamation-triangle', 'EVENTO_VERTICALE': 'warning-sign',
    'ANOMALIA_SENSORE': 'question-sign',
}


def build_static_map_html(df, events):
    lat0, lon0 = float(df['lat'].iloc[0]), float(df['lon'].iloc[0])
    fmap = folium.Map(location=[lat0, lon0], zoom_start=15, tiles='OpenStreetMap')

    speed_min = float(df['speed_kmh'].min())
    speed_max = float(df['speed_kmh'].max())
    lats, lons, speeds = df['lat'].to_numpy(), df['lon'].to_numpy(), df['speed_kmh'].to_numpy()
    for i in range(len(df) - 1):
        color = _speed_to_color((speeds[i] + speeds[i + 1]) / 2, speed_min, speed_max)
        folium.PolyLine([(lats[i], lons[i]), (lats[i + 1], lons[i + 1])],
                         color=color, weight=4, opacity=0.85).add_to(fmap)

    for event in events:
        window = df[(df['timestamp'] >= event['t_start']) & (df['timestamp'] <= event['t_end'])]
        if len(window) == 0:
            continue
        mid = window.iloc[len(window) // 2]
        folium.Marker(
            [mid['lat'], mid['lon']],
            popup=f"{event['event_type']} — {event['duration_s']:.1f}s, confidence {event['confidence']:.0f}",
            icon=folium.Icon(icon=_EVENT_ICONS.get(event['event_type'], 'info-sign'), color='darkred'),
        ).add_to(fmap)

    return fmap._repr_html_()
```

- [ ] **Step 4: Esegui i test**

```bash
cd telemetry-analyzer && python -m pytest tests/test_report_map_static.py -v
```

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add telemetry-analyzer/analyzer/report/map_static.py telemetry-analyzer/tests/test_report_map_static.py
git commit -m "Aggiunge la mappa statica Folium colorata per velocità con marker eventi"
```

---

### Task 10: `report/replay.py` — replay Plotly sincronizzato + icone SVG piega/beccheggio

**Files:**
- Create: `telemetry-analyzer/analyzer/report/replay.py`
- Test: `telemetry-analyzer/tests/test_report_replay.py`

**Interfaces:**
- Consumes: `analyzer.config.REPLAY_DECIMATION_S`; output di `filtering.build_filtered_dataframe` (Task 5).
- Produces: `_decimate_indices(df, decimation_s) -> list[int]`; `build_replay_figure(df, decimation_s=None) -> tuple[plotly.graph_objects.Figure, list[int]]`; `render_replay_html(df, div_id='replay-map') -> str` (frammento completo: mappa + slider + icone SVG + script di sincronizzazione). Usato da `report/assemble.py` (Task 11).

**Nota importante**: la sincronizzazione JS tra lo slider Plotly e le icone SVG (evento `plotly_animatingframe`/`plotly_sliderchange`) non è verificabile con `pytest` da sola — i test qui controllano solo che l'HTML/JS prodotto contenga i pezzi attesi (struttura, id, nomi funzione). **Il comportamento dal vivo va controllato aprendo `report.html` in un vero browser** (verrà fatto nel test di integrazione finale del Task 12 e ribadito lì).

- [ ] **Step 1: Scrivi i test**

```python
# tests/test_report_replay.py
from analyzer.loading import load_csv, compute_time_deltas
from analyzer.filtering import build_filtered_dataframe
from analyzer.report.replay import build_replay_figure, render_replay_html, _decimate_indices
from tests.fixtures import make_ride_csv


def _filtered_df(scenario, tmp_path):
    csv_path = tmp_path / 'ride.csv'
    make_ride_csv(csv_path, scenario)
    return build_filtered_dataframe(compute_time_deltas(load_csv(str(csv_path))))

def test_decimate_indices_always_includes_first_and_last(tmp_path):
    df = _filtered_df('normal', tmp_path)
    indices = _decimate_indices(df, decimation_s=2.0)
    assert indices[0] == 0
    assert indices[-1] == len(df) - 1

def test_decimate_indices_reduces_sample_count_for_long_ride(tmp_path):
    df = _filtered_df('normal', tmp_path)  # 20 campioni a 1s
    indices = _decimate_indices(df, decimation_s=5.0)
    assert len(indices) < len(df)

def test_build_replay_figure_has_one_frame_per_decimated_index(tmp_path):
    df = _filtered_df('normal', tmp_path)
    fig, indices = build_replay_figure(df, decimation_s=2.0)
    assert len(fig.frames) == len(indices)

def test_render_replay_html_contains_icons_and_sync_script(tmp_path):
    df = _filtered_df('curve_clear_apex', tmp_path)
    html = render_replay_html(df)
    assert 'lean-icon-group' in html
    assert 'pitch-icon-group' in html
    assert 'plotly_animatingframe' in html
    assert 'replay-map' in html
```

- [ ] **Step 2: Verifica che i test falliscano**

```bash
cd telemetry-analyzer && python -m pytest tests/test_report_replay.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'analyzer.report.replay'`.

- [ ] **Step 3: Scrivi `analyzer/report/replay.py`**

```python
"""Replay Plotly sincronizzato con slider + icone SVG piega/beccheggio (spec sezione 10, punto 3b)."""
import json

import plotly.graph_objects as go

from analyzer import config


def _decimate_indices(df, decimation_s):
    """Ritorna gli indici di riga da usare come frame del replay, mantenendo un
    intervallo minimo `decimation_s` tra un frame e il successivo (spec: sessioni
    lunghe restano fluide, i dati sottostanti restano a piena risoluzione altrove)."""
    n = len(df)
    if n == 0:
        return []
    indices = [0]
    last_ts = df['timestamp'].iloc[0]
    for i in range(1, n):
        if (df['timestamp'].iloc[i] - last_ts).total_seconds() >= decimation_s:
            indices.append(i)
            last_ts = df['timestamp'].iloc[i]
    if indices[-1] != n - 1:
        indices.append(n - 1)
    return indices


def build_replay_figure(df, decimation_s=None):
    decimation_s = decimation_s if decimation_s is not None else config.REPLAY_DECIMATION_S
    indices = _decimate_indices(df, decimation_s)

    fig = go.Figure()
    fig.add_trace(go.Scattermapbox(lat=df['lat'], lon=df['lon'], mode='lines',
                                    line=dict(width=3, color='#1f77b4'), name='Percorso'))
    fig.add_trace(go.Scattermapbox(lat=[df['lat'].iloc[indices[0]]], lon=[df['lon'].iloc[indices[0]]],
                                    mode='markers', marker=dict(size=14, color='orange'), name='Posizione'))

    frames = [
        go.Frame(name=str(idx), traces=[0, 1], data=[
            go.Scattermapbox(lat=df['lat'], lon=df['lon']),
            go.Scattermapbox(lat=[df['lat'].iloc[idx]], lon=[df['lon'].iloc[idx]]),
        ])
        for idx in indices
    ]
    fig.frames = frames

    steps = [
        dict(method='animate', label=df['timestamp'].iloc[idx].strftime('%H:%M:%S'),
             args=[[str(idx)], dict(mode='immediate', frame=dict(duration=0, redraw=True),
                                     transition=dict(duration=0))])
        for idx in indices
    ]

    fig.update_layout(
        mapbox=dict(style='open-street-map', zoom=14,
                     center=dict(lat=float(df['lat'].mean()), lon=float(df['lon'].mean()))),
        height=520, margin=dict(l=0, r=0, t=30, b=0),
        sliders=[dict(active=0, steps=steps, currentvalue=dict(prefix='Tempo: '))],
        updatemenus=[dict(type='buttons', buttons=[
            dict(label='▶ Play', method='animate',
                 args=[None, dict(frame=dict(duration=300, redraw=True), fromcurrent=True)]),
            dict(label='⏸ Pausa', method='animate', args=[[None], dict(mode='immediate')]),
        ])],
    )
    return fig, indices


def _replay_frame_payload(df, indices):
    """Dati per-frame per la sincronizzazione JS — valori FILTERED, mai raw, con
    il proprio flag di qualità (spec sezione 10, punto 3b)."""
    payload = {}
    for idx in indices:
        row = df.iloc[idx]
        payload[str(idx)] = {
            'lean': round(float(row['lean_filtered']), 1), 'lean_flag': row['lean_flag'],
            'pitch': round(float(row['pitch_filtered']), 1), 'pitch_flag': row['pitch_flag'],
        }
    return payload


_ICON_SVG = """
<div class="replay-icons">
  <div class="icon-block">
    <div class="icon-label">Piega</div>
    <svg viewBox="0 0 100 100" width="90" height="90">
      <g id="lean-icon-group" transform="rotate(0 50 50)">
        <rect x="20" y="45" width="60" height="10" rx="5" fill="#5CC8FF"/>
        <circle cx="30" cy="70" r="10" fill="#1C2128"/>
        <circle cx="70" cy="70" r="10" fill="#1C2128"/>
      </g>
    </svg>
    <div id="lean-value" class="icon-value">0°</div>
  </div>
  <div class="icon-block">
    <div class="icon-label">Beccheggio</div>
    <svg viewBox="0 0 100 100" width="90" height="90">
      <g id="pitch-icon-group" transform="rotate(0 50 50)">
        <rect x="15" y="45" width="70" height="10" rx="5" fill="#5CC8FF"/>
        <polygon points="85,45 100,50 85,55" fill="#5CC8FF"/>
      </g>
    </svg>
    <div id="pitch-value" class="icon-value">0°</div>
  </div>
</div>
"""

_SYNC_JS = """
<script>
(function() {{
  var replayData = {payload_json};
  function updateIcons(frameName) {{
    var d = replayData[frameName];
    if (!d) return;
    document.getElementById('lean-icon-group').setAttribute('transform', 'rotate(' + (-d.lean) + ' 50 50)');
    document.getElementById('pitch-icon-group').setAttribute('transform', 'rotate(' + (-d.pitch) + ' 50 50)');
    var leanValue = document.getElementById('lean-value');
    var pitchValue = document.getElementById('pitch-value');
    leanValue.textContent = d.lean.toFixed(0) + '°';
    pitchValue.textContent = d.pitch.toFixed(0) + '°';
    leanValue.style.borderColor = d.lean_flag === 'YELLOW' ? '#FFB020' : (d.lean_flag === 'RED' ? '#FF4040' : 'transparent');
    pitchValue.style.borderColor = d.pitch_flag === 'YELLOW' ? '#FFB020' : (d.pitch_flag === 'RED' ? '#FF4040' : 'transparent');
  }}
  var graphDiv = document.getElementById('{div_id}');
  if (graphDiv) {{
    graphDiv.on('plotly_animatingframe', function(e) {{ updateIcons(e.name); }});
    graphDiv.on('plotly_sliderchange', function(e) {{
      var step = graphDiv.layout.sliders[0].steps[e.slider.active];
      if (step) updateIcons(step.args[0][0]);
    }});
    updateIcons('{first_idx}');
  }}
}})();
</script>
"""


def render_replay_html(df, div_id='replay-map'):
    fig, indices = build_replay_figure(df)
    map_html = fig.to_html(full_html=False, include_plotlyjs=False, div_id=div_id)
    payload = _replay_frame_payload(df, indices)
    sync_js = _SYNC_JS.format(payload_json=json.dumps(payload), div_id=div_id, first_idx=indices[0])
    return f'<section id="replay"><h2>Replay percorso</h2>{map_html}{_ICON_SVG}{sync_js}</section>'
```

- [ ] **Step 4: Esegui i test**

```bash
cd telemetry-analyzer && python -m pytest tests/test_report_replay.py -v
```

Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add telemetry-analyzer/analyzer/report/replay.py telemetry-analyzer/tests/test_report_replay.py
git commit -m "Aggiunge il replay Plotly sincronizzato con le icone SVG piega/beccheggio"
```

---

### Task 11: `report/tables.py` + `report/assemble.py` — tabelle, qualità sensori, HTML finale

**Files:**
- Create: `telemetry-analyzer/analyzer/report/tables.py`
- Create: `telemetry-analyzer/analyzer/report/assemble.py`
- Test: `telemetry-analyzer/tests/test_report_tables_assemble.py`

**Interfaces:**
- Consumes: `analyzer.config.SIGNALS`; `report.dashboard.{build_dashboard_stats,render_dashboard_html}`; `report.charts.render_telemetry_html`; `report.map_static.build_static_map_html`; `report.replay.render_replay_html` (Task 8-10); output di `events.detect_events`/`curves.detect_curves`.
- Produces: `tables.render_events_section(events: list[dict]) -> str`; `tables.render_curves_section(curves: list[dict]) -> str`; `tables.render_sensor_quality_section(df) -> str`; `tables._SORT_JS` (stringa, script di ordinamento tabelle, riusato da `assemble.py`); `assemble.assemble_report_html(df, events: list[dict], curves: list[dict]) -> str` (documento HTML completo). Usato dal CLI (Task 12).

- [ ] **Step 1: Scrivi i test**

```python
# tests/test_report_tables_assemble.py
from analyzer.loading import load_csv, compute_time_deltas
from analyzer.filtering import build_filtered_dataframe
from analyzer.events import detect_events
from analyzer.curves import detect_curves
from analyzer.report.tables import render_events_section, render_curves_section, render_sensor_quality_section
from analyzer.report.assemble import assemble_report_html
from tests.fixtures import make_ride_csv


def _pipeline(scenario, tmp_path):
    csv_path = tmp_path / 'ride.csv'
    make_ride_csv(csv_path, scenario)
    df = build_filtered_dataframe(compute_time_deltas(load_csv(str(csv_path))))
    events = detect_events(df)
    curves = detect_curves(df, events)
    return df, events, curves

def test_render_events_section_has_sortable_table(tmp_path):
    df, events, curves = _pipeline('accel_coherent_event', tmp_path)
    html = render_events_section(events)
    assert 'events-table' in html

def test_render_curves_section_shows_apex_uncertain(tmp_path):
    df, events, curves = _pipeline('curve_uncertain_apex', tmp_path)
    html = render_curves_section(curves)
    assert 'APEX UNCERTAIN' in html

def test_render_curves_section_handles_no_curves(tmp_path):
    df, events, curves = _pipeline('accel_coherent_event', tmp_path)
    html = render_curves_section(curves)
    assert 'Nessuna curva rilevata' in html

def test_render_sensor_quality_section_identifies_worst_signal(tmp_path):
    df, events, curves = _pipeline('lean_isolated_spike', tmp_path)
    html = render_sensor_quality_section(df)
    assert 'Sensore più problematico' in html
    assert 'lean' in html

def test_assemble_report_html_is_valid_document(tmp_path):
    df, events, curves = _pipeline('normal', tmp_path)
    html = assemble_report_html(df, events, curves)
    assert html.startswith('<!DOCTYPE html>')
    assert '<title>Report telemetria</title>' in html
    assert 'Dashboard generale' in html
    assert 'Replay percorso' in html
```

- [ ] **Step 2: Verifica che i test falliscano**

```bash
cd telemetry-analyzer && python -m pytest tests/test_report_tables_assemble.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'analyzer.report.tables'`.

- [ ] **Step 3: Scrivi `analyzer/report/tables.py`**

```python
"""Tabelle eventi/curve e sezione qualità sensori (spec sezione 10, punti 4-6)."""
from analyzer import config


def _sortable_table_html(table_id, headers, rows):
    thead = ''.join(f'<th onclick="sortTable(\'{table_id}\', {i})">{h}</th>' for i, h in enumerate(headers))
    tbody = ''.join('<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>' for row in rows)
    return f'<table id="{table_id}" class="sortable"><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>'


_SORT_JS = """
<script>
function sortTable(tableId, col) {
  var table = document.getElementById(tableId);
  var rows = Array.from(table.tBodies[0].rows);
  var asc = table.dataset.sortCol != col || table.dataset.sortDir !== 'asc';
  rows.sort(function(a, b) {
    var av = a.cells[col].textContent, bv = b.cells[col].textContent;
    var an = parseFloat(av), bn = parseFloat(bv);
    var cmp = (!isNaN(an) && !isNaN(bn)) ? (an - bn) : av.localeCompare(bv);
    return asc ? cmp : -cmp;
  });
  rows.forEach(function(r) { table.tBodies[0].appendChild(r); });
  table.dataset.sortCol = col;
  table.dataset.sortDir = asc ? 'asc' : 'desc';
}
</script>
"""


def render_events_section(events):
    headers = ['Tipo', 'Inizio', 'Durata (s)', 'V iniziale', 'V finale', 'V max',
               'Lean max', 'Accel long. max', 'Accel lat. max', 'Accel vert. max', 'Confidence']
    rows = [
        [e['event_type'], e['t_start'].strftime('%H:%M:%S'), f"{e['duration_s']:.1f}",
         f"{e['v_start']:.0f}", f"{e['v_end']:.0f}", f"{e['v_max']:.0f}", f"{e['lean_max']:.0f}",
         f"{e['accel_fwd_max']:.2f}", f"{e['accel_lat_max']:.2f}", f"{e['accel_vert_max']:.2f}",
         f"{e['confidence']:.0f}"]
        for e in events
    ]
    table = _sortable_table_html('events-table', headers, rows)
    return f'<section id="events"><h2>Eventi rilevati</h2>{table}</section>'


def render_curves_section(curves):
    if not curves:
        return '<section id="curves"><h2>Curve</h2><p>Nessuna curva rilevata.</p></section>'
    blocks = []
    for i, c in enumerate(curves, start=1):
        apex_text = (c['apex_time'].strftime('%H:%M:%S') if c['apex_status'] == 'CONFIRMED' else 'APEX UNCERTAIN')
        blocks.append(
            f'<div class="curve-block"><h3>Curva {i} — {c["t_start"].strftime("%H:%M:%S")} '
            f'({c["duration_s"]:.1f}s)</h3><ul>'
            f'<li>Velocità: {c["v_entry"]:.0f} → {c["v_min"]:.0f} (min) → {c["v_exit"]:.0f} km/h</li>'
            f'<li>Lean massimo attendibile: {c["lean_max_filtered"]:.0f}° '
            f'(confidence {c["lean_max_confidence"]:.0f})</li>'
            f'<li>Accelerazione laterale massima: {c["accel_lat_max_filtered"]:.2f}g</li>'
            f'<li>Frenata in ingresso: {"sì" if c["braking_detected"] else "no"} '
            f'(min {c["accel_fwd_min_entry"]:.2f}g)</li>'
            f'<li>Apex: {apex_text}</li>'
            f'<li>Riapertura gas rilevata: {"sì (stimata)" if c["throttle_reopening_detected"] else "no"}</li>'
            f'</ul></div>'
        )
    return f'<section id="curves"><h2>Curve</h2>{"".join(blocks)}</section>'


def render_sensor_quality_section(df):
    n = len(df)
    rows = []
    worst_signal, worst_red_pct = None, -1.0
    for signal in config.SIGNALS:
        flags = df[f'{signal}_flag']
        green_pct = 100.0 * (flags == 'GREEN').sum() / n if n else 0.0
        yellow_pct = 100.0 * (flags == 'YELLOW').sum() / n if n else 0.0
        red_pct = 100.0 * (flags == 'RED').sum() / n if n else 0.0
        mean_conf = float(df[f'{signal}_confidence'].mean()) if n else 0.0
        if red_pct > worst_red_pct:
            worst_red_pct, worst_signal = red_pct, signal
        rows.append([signal, f'{green_pct:.0f}%', f'{yellow_pct:.0f}%', f'{red_pct:.0f}%', f'{mean_conf:.0f}'])

    headers = ['Segnale', '% GREEN', '% YELLOW', '% RED', 'Confidence media']
    table = _sortable_table_html('quality-table', headers, rows)
    n_gaps = int(df['gap_flag'].sum())
    return (f'<section id="sensor-quality"><h2>Qualità sensori</h2>'
            f'<p>Gap temporali rilevati: {n_gaps}. Sensore più problematico: '
            f'<b>{worst_signal}</b> ({worst_red_pct:.0f}% RED).</p>{table}</section>')
```

- [ ] **Step 4: Scrivi `analyzer/report/assemble.py`**

```python
"""Assembla report.html a partire dai frammenti delle altre sezioni (spec sezione 10)."""
import plotly.io as pio

from analyzer.report.dashboard import build_dashboard_stats, render_dashboard_html
from analyzer.report.charts import render_telemetry_html
from analyzer.report.map_static import build_static_map_html
from analyzer.report.replay import render_replay_html
from analyzer.report.tables import (render_events_section, render_curves_section,
                                     render_sensor_quality_section, _SORT_JS)

_CSS = """
<style>
  body { font-family: -apple-system, sans-serif; background: #0A0E14; color: #E8ECF0; margin: 0; padding: 20px; }
  h1, h2 { border-bottom: 1px solid #1C2128; padding-bottom: 6px; }
  section { margin-bottom: 36px; }
  .dash-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px; }
  .dash-card { background: #12161D; border-radius: 8px; padding: 12px; display: flex; flex-direction: column; }
  .dash-card .label { font-size: 11px; color: #8AA0BE; text-transform: uppercase; }
  .dash-card .value { font-size: 22px; font-weight: 700; }
  table.sortable { border-collapse: collapse; width: 100%; }
  table.sortable th, table.sortable td { border: 1px solid #1C2128; padding: 6px 10px; text-align: left; }
  table.sortable th { cursor: pointer; background: #12161D; }
  .replay-icons { display: flex; gap: 30px; margin-top: 10px; }
  .icon-block { text-align: center; }
  .icon-value { font-size: 20px; font-weight: 700; border: 2px solid transparent; border-radius: 6px; padding: 2px 8px; margin-top: 4px; display: inline-block; }
  .curve-block { background: #12161D; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px; }
</style>
"""


def assemble_report_html(df, events, curves):
    stats = build_dashboard_stats(df, events)
    plotly_js = f'<script>{pio.get_plotlyjs()}</script>'

    sections = [
        render_dashboard_html(stats),
        render_telemetry_html(df),
        f'<section id="map-static"><h2>Percorso (vista statica)</h2>{build_static_map_html(df, events)}</section>',
        render_replay_html(df),
        render_events_section(events),
        render_curves_section(curves),
        render_sensor_quality_section(df),
    ]

    return (
        '<!DOCTYPE html><html lang="it"><head><meta charset="utf-8">'
        f'<title>Report telemetria</title>{_CSS}{plotly_js}</head><body>'
        f'<h1>Report telemetria</h1>{"".join(sections)}{_SORT_JS}</body></html>'
    )
```

- [ ] **Step 5: Esegui i test**

```bash
cd telemetry-analyzer && python -m pytest tests/test_report_tables_assemble.py -v
```

Expected: 5 PASS.

- [ ] **Step 6: Commit**

```bash
git add telemetry-analyzer/analyzer/report/tables.py telemetry-analyzer/analyzer/report/assemble.py telemetry-analyzer/tests/test_report_tables_assemble.py
git commit -m "Aggiunge tabelle eventi/curve, qualità sensori, e assembla il report.html finale"
```

---

### Task 12: CLI entrypoint e test di integrazione end-to-end

**Files:**
- Create: `telemetry-analyzer/telemetry_analyzer.py`
- Test: `telemetry-analyzer/tests/test_report_smoke.py`

**Interfaces:**
- Consumes: tutto il pacchetto `analyzer` (Task 1-11); `tests.fixtures.make_full_ride_csv` (Task 1, concatena tutti gli scenari in una sessione realistica).
- Produces: script eseguibile `telemetry_analyzer.py` — nessuna interfaccia Python consumata da altri task (è l'ultimo).

- [ ] **Step 1: Scrivi `telemetry_analyzer.py`**

```python
#!/usr/bin/env python3
"""CLI: python telemetry_analyzer.py file.csv [--outdir DIR]"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analyzer.loading import load_csv, compute_time_deltas
from analyzer.filtering import build_filtered_dataframe
from analyzer.events import detect_events, events_to_dataframe
from analyzer.curves import detect_curves, curves_to_dataframe
from analyzer.report.assemble import assemble_report_html


def main():
    parser = argparse.ArgumentParser(description='Analizza un CSV di telemetria TELAMETRIA.')
    parser.add_argument('csv_path', help='Percorso al CSV esportato dalla PWA')
    parser.add_argument('--outdir', default=None, help='Cartella di output (default: stessa del CSV)')
    args = parser.parse_args()

    outdir = args.outdir or os.path.dirname(os.path.abspath(args.csv_path)) or '.'
    os.makedirs(outdir, exist_ok=True)

    print(f'Carico {args.csv_path}...')
    df = compute_time_deltas(load_csv(args.csv_path))

    print('Filtro i segnali (Hampel, cross-sensor, confidence)...')
    filtered_df = build_filtered_dataframe(df)

    print('Rilevo eventi...')
    events = detect_events(filtered_df)

    print('Rilevo curve...')
    curves = detect_curves(filtered_df, events)

    filtered_csv_path = os.path.join(outdir, 'filtered_telemetry.csv')
    events_csv_path = os.path.join(outdir, 'events.csv')
    curves_csv_path = os.path.join(outdir, 'curves.csv')
    report_path = os.path.join(outdir, 'report.html')

    filtered_df.to_csv(filtered_csv_path, index=False)
    events_to_dataframe(events).to_csv(events_csv_path, index=False)
    curves_to_dataframe(curves).to_csv(curves_csv_path, index=False)

    print('Genero il report HTML...')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(assemble_report_html(filtered_df, events, curves))

    print(f'Fatto. Output in {outdir}:')
    for path in (report_path, filtered_csv_path, events_csv_path, curves_csv_path):
        print(f'  - {path}')


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Scrivi il test di integrazione end-to-end**

```python
# tests/test_report_smoke.py
import os
import subprocess
import sys

import pandas as pd

from tests.fixtures import make_full_ride_csv


def test_cli_end_to_end_produces_all_outputs(tmp_path):
    csv_path = tmp_path / 'full_ride.csv'
    make_full_ride_csv(csv_path)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    result = subprocess.run(
        [sys.executable, os.path.join(project_root, 'telemetry_analyzer.py'),
         str(csv_path), '--outdir', str(tmp_path)],
        capture_output=True, text=True, cwd=project_root,
    )
    assert result.returncode == 0, result.stderr

    report_path = tmp_path / 'report.html'
    filtered_path = tmp_path / 'filtered_telemetry.csv'
    events_path = tmp_path / 'events.csv'
    curves_path = tmp_path / 'curves.csv'
    for path in (report_path, filtered_path, events_path, curves_path):
        assert path.exists(), f'{path} non generato'

    report_html = report_path.read_text(encoding='utf-8')
    assert '<!DOCTYPE html>' in report_html
    assert 'Dashboard generale' in report_html
    assert 'lean-icon-group' in report_html

    filtered_df = pd.read_csv(filtered_path)
    original_df = pd.read_csv(csv_path)
    assert len(filtered_df) == len(original_df)
    for signal in ('lean', 'pitch', 'accel_fwd', 'accel_lat', 'accel_vert'):
        assert f'{signal}_filtered' in filtered_df.columns
        assert f'{signal}_status' in filtered_df.columns

    events_df = pd.read_csv(events_path)
    curves_df = pd.read_csv(curves_path)
    assert 'event_type' in events_df.columns
    assert 'apex_status' in curves_df.columns
```

- [ ] **Step 3: Esegui il test**

```bash
cd telemetry-analyzer && python -m pytest tests/test_report_smoke.py -v
```

Expected: 1 PASS.

- [ ] **Step 4: Esegui l'intera suite per assicurarti che nulla si sia rotto**

```bash
cd telemetry-analyzer && python -m pytest -v
```

Expected: tutti i test di tutti i Task 1-12 passano (circa 55 test).

- [ ] **Step 5: Verifica manuale in un browser reale**

```bash
cd telemetry-analyzer
python telemetry_analyzer.py /percorso/a/un/csv/di/prova.csv
open report.html   # macOS; su altri sistemi: apri il file manualmente nel browser
```

Controlla ad occhio: le sezioni dashboard/telemetria/mappa statica/replay/eventi/curve/qualità sensori sono tutte presenti; i grafici RAW+FILTERED si sovrappongono leggibilmente; trascinando lo slider del replay, il marker si muove sulla mappa **e** le due icone piega/beccheggio ruotano e il numero cambia (questo è il pezzo che i test automatici non possono verificare, per i limiti di `plotly_sliderchange`/`plotly_animatingframe` discussi nel Task 10); le tabelle eventi/curve sono ordinabili cliccando le intestazioni.

- [ ] **Step 6: Commit**

```bash
git add telemetry-analyzer/telemetry_analyzer.py telemetry-analyzer/tests/test_report_smoke.py
git commit -m "Aggiunge il CLI entrypoint e il test di integrazione end-to-end"
```
