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
