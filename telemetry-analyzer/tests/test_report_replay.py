from analyzer.loading import load_csv, compute_time_deltas
from analyzer.filtering import build_filtered_dataframe
from analyzer.report.replay import build_replay_figure, render_replay_html, _decimate_indices
from tests.fixtures import make_ride_csv


def _filtered_df(scenario, tmp_path):
    csv_path = tmp_path / 'ride.csv'
    make_ride_csv(csv_path, scenario)
    return build_filtered_dataframe(compute_time_deltas(load_csv(str(csv_path))))

def test_decimate_indices_always_includes_first_and_last(tmp_path):
    df = _filtered_df('normal', tmp_path)
    indices = _decimate_indices(df, decimation_s=2.0)
    assert indices[0] == 0
    assert indices[-1] == len(df) - 1

def test_decimate_indices_reduces_sample_count_for_long_ride(tmp_path):
    df = _filtered_df('normal', tmp_path)  # 20 campioni a 1s
    indices = _decimate_indices(df, decimation_s=5.0)
    assert len(indices) < len(df)

def test_build_replay_figure_has_one_frame_per_decimated_index(tmp_path):
    df = _filtered_df('normal', tmp_path)
    fig, indices = build_replay_figure(df, decimation_s=2.0)
    assert len(fig.frames) == len(indices)

def test_render_replay_html_contains_icons_and_sync_script(tmp_path):
    df = _filtered_df('curve_clear_apex', tmp_path)
    html = render_replay_html(df)
    assert 'lean-icon-group' in html
    assert 'pitch-icon-group' in html
    assert 'plotly_animatingframe' in html
    assert 'replay-map' in html
