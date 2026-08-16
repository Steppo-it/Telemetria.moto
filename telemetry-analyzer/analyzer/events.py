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
