import pandas as pd
from analyzer.fusion import (
    circular_diff_deg, heading_change_window, detect_braking, detect_accelerating,
    detect_curve, detect_vertical_event, detect_pitch_ambiguous, cross_sensor_corroboration,
)
from tests.fixtures import build_scenario_rows
import pandas as pd


def _df_from_scenario(name):
    rows = build_scenario_rows(name)
    df = pd.DataFrame(rows)
    return df


def test_circular_diff_handles_wraparound():
    heading = pd.Series([350.0, 355.0, 5.0, 10.0])
    diff = circular_diff_deg(heading)
    assert abs(diff.iloc[2] - 10.0) < 0.01  # 355 -> 5 e' +10, non -350

def test_detect_braking_true_when_speed_drops_and_decel():
    df = _df_from_scenario('curve_clear_apex')
    braking = detect_braking(df['accel_fwd_g'], df['speed_kmh'])
    assert braking.iloc[2] or braking.iloc[3]  # decelerazione in ingresso curva

def test_detect_curve_true_during_curve_scenario():
    df = _df_from_scenario('curve_clear_apex')
    curve = detect_curve(df['heading_deg'], df['accel_lat_g'], df['lean_deg'])
    assert curve.iloc[3] or curve.iloc[4]  # vicino all'apice, lean alto e heading in variazione

def test_detect_curve_false_on_straight_line():
    df = _df_from_scenario('normal')
    curve = detect_curve(df['heading_deg'], df['accel_lat_g'], df['lean_deg'])
    assert not curve.any()

def test_detect_pitch_ambiguous_flags_extreme_plus_vertical():
    df = _df_from_scenario('pitch_ambiguous_event')
    ambiguous = detect_pitch_ambiguous(df['pitch_deg'], df['accel_vert_g'])
    assert ambiguous.iloc[5] == True
    assert ambiguous.iloc[0] == False

def test_cross_sensor_corroboration_returns_all_signal_keys():
    df = _df_from_scenario('curve_clear_apex')
    result = cross_sensor_corroboration(df)
    for key in ('lean', 'pitch', 'accel_fwd', 'accel_lat', 'accel_vert'):
        assert key in result
        assert len(result[key]) == len(df)

def test_cross_sensor_corroboration_lean_true_during_curve():
    df = _df_from_scenario('curve_clear_apex')
    result = cross_sensor_corroboration(df)
    assert result['lean'].iloc[3] or result['lean'].iloc[4]
