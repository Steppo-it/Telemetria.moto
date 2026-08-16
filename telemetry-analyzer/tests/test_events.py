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

def test_detect_events_merges_multiple_overlapping_curves_into_one_event():
    # una frenata lunga che attraversa due curve ravvicinate deve produrre
    # UN SOLO evento FRENATA_CURVA, non uno per ciascuna coppia sovrapposta
    df = _minimal_filtered_df(
        accel_fwd=[0.0, -0.3, -0.3, -0.3, -0.3, -0.3, -0.3, -0.3, 0.0, 0.0],
        accel_lat=[0.02, 0.02, 0.3, 0.3, 0.02, 0.02, 0.3, 0.3, 0.02, 0.02],
        lean=[1.0, 1.0, 15.0, 15.0, 1.0, 1.0, 15.0, 15.0, 1.0, 1.0],
        heading=[90.0, 90.0, 80.0, 70.0, 65.0, 65.0, 55.0, 45.0, 40.0, 40.0],
    )
    events = detect_events(df)
    combined = [e for e in events if e['event_type'] == 'FRENATA_CURVA']
    assert len(combined) == 1
