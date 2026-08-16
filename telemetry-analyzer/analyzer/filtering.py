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
