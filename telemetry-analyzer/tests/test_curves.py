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
