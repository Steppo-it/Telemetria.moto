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

def test_filter_signal_marks_entirely_missing_column_as_invalid():
    n = 10
    start = pd.Timestamp('2026-08-16T10:00:00Z')
    df = pd.DataFrame({
        'timestamp': [start + pd.Timedelta(seconds=i) for i in range(n)],
        'lat': [45.0] * n, 'lon': [9.0 + i * 0.0001 for i in range(n)],
        'speed_kmh': [40.0] * n, 'heading_deg': [90.0] * n,
        'lean_deg': [15.0] * n, 'pitch_deg': [0.0] * n,
        'accel_fwd_g': [float('nan')] * n,  # sensore mai disponibile in tutta la sessione
        'accel_lat_g': [0.05] * n, 'accel_vert_g': [0.02] * n,
        'comfort_idx': [90.0] * n, 'score': [80.0] * n,
    })
    df = compute_time_deltas(df)
    out = build_filtered_dataframe(df)
    assert (out['accel_fwd_flag'] == 'RED').all()
    assert (out['accel_fwd_status'] == 'INVALID').all()
    assert (out['accel_fwd_confidence'] == 0.0).all()
    assert out['accel_fwd_filtered'].isna().all()
    # gli altri segnali, con dati validi, NON devono essere influenzati
    assert (out['accel_lat_flag'] == 'GREEN').all()

def test_filter_signal_marks_isolated_missing_sample_as_invalid():
    n = 10
    start = pd.Timestamp('2026-08-16T10:00:00Z')
    lean_values = [15.0] * n
    lean_values[5] = float('nan')  # un solo campione mancante, non l'intera colonna
    df = pd.DataFrame({
        'timestamp': [start + pd.Timedelta(seconds=i) for i in range(n)],
        'lat': [45.0] * n, 'lon': [9.0 + i * 0.0001 for i in range(n)],
        'speed_kmh': [40.0] * n, 'heading_deg': [90.0] * n,
        'lean_deg': lean_values, 'pitch_deg': [0.0] * n,
        'accel_fwd_g': [0.05] * n, 'accel_lat_g': [0.05] * n, 'accel_vert_g': [0.02] * n,
        'comfort_idx': [90.0] * n, 'score': [80.0] * n,
    })
    df = compute_time_deltas(df)
    out = build_filtered_dataframe(df)
    assert out['lean_status'].iloc[5] == 'INVALID'
    assert out['lean_flag'].iloc[5] == 'RED'
    assert pd.isna(out['lean_filtered'].iloc[5])
    # i campioni intorno, con dati validi, restano GREEN (non contaminati dal vicino NaN)
    assert out['lean_status'].iloc[0] == 'MEASURED'
    assert out['lean_status'].iloc[9] == 'MEASURED'
