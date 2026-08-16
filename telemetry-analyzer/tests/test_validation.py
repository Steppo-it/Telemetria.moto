import pandas as pd
from analyzer.validation import hampel_z, rate_of_change, detect_isolated_spike, score_signal
from analyzer import config

def test_hampel_z_flags_isolated_spike_from_spec_example():
    # 18, 19, 21, 67, 20, 19 — il 67 deve avere z alto, gli altri z basso
    leans = pd.Series([18.0, 19.0, 21.0, 67.0, 20.0, 19.0, 18.0, 19.0, 20.0, 19.0])
    z, med = hampel_z(leans, window=7)
    assert z.iloc[3] > 5.0
    assert z.iloc[0] < 2.0
    assert z.iloc[5] < 2.0

def test_rate_of_change_detects_fast_transition():
    leans = pd.Series([18.0, 19.0, 90.0])
    dt_s = pd.Series([1.0, 1.0, 1.0])
    rate, exceeded = rate_of_change(leans, dt_s, max_rate=config.MAX_RATE['lean'])
    assert exceeded.iloc[2]
    assert not exceeded.iloc[1]

def test_detect_isolated_spike_matches_lean_example():
    leans = pd.Series([18.0, 19.0, 21.0, 67.0, 20.0, 19.0, 18.0, 19.0, 20.0, 19.0])
    _, med = hampel_z(leans, window=7)
    isolated = detect_isolated_spike(leans, med)
    assert isolated.iloc[3] == True

def test_detect_isolated_spike_matches_accel_coherent_example():
    # 0.1,0.2,1.4,0.2,0.1 (spike) seguito da 0.8,1.1,1.4,1.2,0.9 (evento coerente)
    fwd = pd.Series([0.1, 0.2, 1.4, 0.2, 0.1, 0.15, 0.8, 1.1, 1.4, 1.2, 0.9, 0.2])
    _, med = hampel_z(fwd, window=7)
    isolated = detect_isolated_spike(fwd, med)
    assert isolated.iloc[2] == True    # il picco 1.4 isolato è uno spike
    assert isolated.iloc[8] == False   # il picco 1.4 nell'evento coerente non lo è

def test_score_signal_returns_all_expected_series():
    leans = pd.Series([18.0, 19.0, 21.0, 67.0, 20.0, 19.0, 18.0, 19.0, 20.0, 19.0])
    dt_s = pd.Series([None, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
    result = score_signal(leans, dt_s, 'lean')
    for key in ('z', 'median', 'rate', 'rate_exceeded', 'isolated_spike'):
        assert key in result
        assert len(result[key]) == len(leans)
    assert result['isolated_spike'].iloc[3] == True
