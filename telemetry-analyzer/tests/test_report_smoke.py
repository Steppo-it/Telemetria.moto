# tests/test_report_smoke.py
import os
import subprocess
import sys

import pandas as pd

from tests.fixtures import make_full_ride_csv


def test_cli_end_to_end_produces_all_outputs(tmp_path):
    csv_path = tmp_path / 'full_ride.csv'
    make_full_ride_csv(csv_path)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    result = subprocess.run(
        [sys.executable, os.path.join(project_root, 'telemetry_analyzer.py'),
         str(csv_path), '--outdir', str(tmp_path)],
        capture_output=True, text=True, cwd=project_root,
    )
    assert result.returncode == 0, result.stderr

    report_path = tmp_path / 'report.html'
    filtered_path = tmp_path / 'filtered_telemetry.csv'
    events_path = tmp_path / 'events.csv'
    curves_path = tmp_path / 'curves.csv'
    for path in (report_path, filtered_path, events_path, curves_path):
        assert path.exists(), f'{path} non generato'

    report_html = report_path.read_text(encoding='utf-8')
    assert '<!DOCTYPE html>' in report_html
    assert 'Dashboard generale' in report_html
    assert 'lean-icon-group' in report_html

    filtered_df = pd.read_csv(filtered_path)
    original_df = pd.read_csv(csv_path)
    assert len(filtered_df) == len(original_df)
    for signal in ('lean', 'pitch', 'accel_fwd', 'accel_lat', 'accel_vert'):
        assert f'{signal}_filtered' in filtered_df.columns
        assert f'{signal}_status' in filtered_df.columns

    events_df = pd.read_csv(events_path)
    curves_df = pd.read_csv(curves_path)
    assert 'event_type' in events_df.columns
    assert 'apex_status' in curves_df.columns


def test_cli_accepts_custom_config_override(tmp_path):
    csv_path = tmp_path / 'ride.csv'
    make_full_ride_csv(csv_path)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    custom_config_path = tmp_path / 'custom_config.py'
    custom_config_path.write_text('FLAG_GREEN_MIN = 99\nFLAG_YELLOW_MIN = 90\n')

    result = subprocess.run(
        [sys.executable, os.path.join(project_root, 'telemetry_analyzer.py'),
         str(csv_path), '--outdir', str(tmp_path), '--config', str(custom_config_path)],
        capture_output=True, text=True, cwd=project_root,
    )
    assert result.returncode == 0, result.stderr
    assert 'FLAG_GREEN_MIN' in result.stdout
    filtered_df = pd.read_csv(tmp_path / 'filtered_telemetry.csv')
    assert 'lean_flag' in filtered_df.columns
