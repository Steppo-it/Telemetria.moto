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
