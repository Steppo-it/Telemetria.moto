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
