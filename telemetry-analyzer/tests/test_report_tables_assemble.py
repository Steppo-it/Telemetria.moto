# tests/test_report_tables_assemble.py
from analyzer.loading import load_csv, compute_time_deltas
from analyzer.filtering import build_filtered_dataframe
from analyzer.events import detect_events
from analyzer.curves import detect_curves
from analyzer.report.tables import render_events_section, render_curves_section, render_sensor_quality_section
from analyzer.report.assemble import assemble_report_html
from tests.fixtures import make_ride_csv


def _pipeline(scenario, tmp_path):
    csv_path = tmp_path / 'ride.csv'
    make_ride_csv(csv_path, scenario)
    df = build_filtered_dataframe(compute_time_deltas(load_csv(str(csv_path))))
    events = detect_events(df)
    curves = detect_curves(df, events)
    return df, events, curves

def test_render_events_section_has_sortable_table(tmp_path):
    df, events, curves = _pipeline('accel_coherent_event', tmp_path)
    html = render_events_section(events)
    assert 'events-table' in html

def test_render_curves_section_shows_apex_uncertain(tmp_path):
    df, events, curves = _pipeline('curve_uncertain_apex', tmp_path)
    html = render_curves_section(curves)
    assert 'APEX UNCERTAIN' in html

def test_render_curves_section_handles_no_curves(tmp_path):
    df, events, curves = _pipeline('accel_coherent_event', tmp_path)
    html = render_curves_section(curves)
    assert 'Nessuna curva rilevata' in html

def test_render_sensor_quality_section_identifies_worst_signal(tmp_path):
    df, events, curves = _pipeline('lean_isolated_spike', tmp_path)
    html = render_sensor_quality_section(df)
    assert 'Sensore più problematico' in html
    assert 'lean' in html

def test_assemble_report_html_is_valid_document(tmp_path):
    df, events, curves = _pipeline('normal', tmp_path)
    html = assemble_report_html(df, events, curves)
    assert html.startswith('<!DOCTYPE html>')
    assert '<title>Report telemetria</title>' in html
    assert 'Dashboard generale' in html
    assert 'Replay percorso' in html
