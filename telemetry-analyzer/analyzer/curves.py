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
