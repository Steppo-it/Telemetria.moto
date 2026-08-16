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
    # format='ISO8601' gestisce timestamp ISO 8601 con precisione mista (con/senza
    # microsecondi, come generati da datetime.isoformat()) nella stessa colonna —
    # pd.to_datetime senza format esplicito inferisce il formato dai primi valori e
    # solleva ValueError se un valore successivo ha precisione diversa.
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601')
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
