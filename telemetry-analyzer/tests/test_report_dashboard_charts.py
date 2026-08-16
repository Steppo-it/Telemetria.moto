from analyzer.loading import load_csv, compute_time_deltas
from analyzer.filtering import build_filtered_dataframe
from analyzer.events import detect_events
from analyzer.report.dashboard import build_dashboard_stats, render_dashboard_html, total_distance_m
from analyzer.report.charts import build_telemetry_figure, render_telemetry_html
from tests.fixtures import make_ride_csv


def _filtered_df(scenario, tmp_path):
    csv_path = tmp_path / 'ride.csv'
    make_ride_csv(csv_path, scenario)
    return build_filtered_dataframe(compute_time_deltas(load_csv(str(csv_path))))

def test_total_distance_m_positive_for_moving_ride(tmp_path):
    df = _filtered_df('normal', tmp_path)
    assert total_distance_m(df) > 0

def test_build_dashboard_stats_has_expected_keys(tmp_path):
    df = _filtered_df('normal', tmp_path)
    events = detect_events(df)
    stats = build_dashboard_stats(df, events)
    for key in ('duration_s', 'distance_km', 'speed_max_kmh', 'lean_max_raw',
                'lean_max_filtered', 'n_anomalies_red', 'n_gaps', 'overall_quality'):
        assert key in stats

def test_render_dashboard_html_contains_labels(tmp_path):
    df = _filtered_df('normal', tmp_path)
    events = detect_events(df)
    stats = build_dashboard_stats(df, events)
    html = render_dashboard_html(stats)
    assert 'Dashboard generale' in html
    assert 'Distanza GPS' in html

def test_build_telemetry_figure_has_one_subplot_title_per_signal(tmp_path):
    df = _filtered_df('lean_isolated_spike', tmp_path)
    fig = build_telemetry_figure(df)
    assert len(fig.layout.annotations) == 6

def test_render_telemetry_html_is_nonempty_div(tmp_path):
    df = _filtered_df('normal', tmp_path)
    html = render_telemetry_html(df)
    assert 'telemetry-charts' in html
    assert len(html) > 100
