from analyzer.loading import load_csv, compute_time_deltas
from analyzer.filtering import build_filtered_dataframe
from analyzer.events import detect_events
from analyzer.report.map_static import build_static_map_html, _speed_to_color
from tests.fixtures import make_ride_csv


def test_speed_to_color_returns_hex():
    color = _speed_to_color(50, 0, 100)
    assert color.startswith('#')
    assert len(color) == 7


def test_speed_to_color_handles_flat_range():
    color = _speed_to_color(50, 50, 50)
    assert color.startswith('#')


def test_build_static_map_html_contains_map_markup(tmp_path):
    csv_path = tmp_path / 'ride.csv'
    make_ride_csv(csv_path, 'curve_clear_apex')
    df = build_filtered_dataframe(compute_time_deltas(load_csv(str(csv_path))))
    events = detect_events(df)
    html = build_static_map_html(df, events)
    assert 'leaflet' in html.lower()
    assert len(html) > 500
