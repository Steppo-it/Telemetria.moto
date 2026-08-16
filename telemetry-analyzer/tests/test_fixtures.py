# tests/test_fixtures.py
import csv
from tests.fixtures import build_scenario_rows, CSV_COLUMNS

def test_all_scenarios_produce_valid_rows():
    scenarios = ['normal', 'lean_isolated_spike', 'accel_coherent_event',
                 'pitch_ambiguous_event', 'temporal_gap', 'duplicate_timestamp',
                 'curve_clear_apex', 'curve_uncertain_apex']
    for scenario in scenarios:
        rows = build_scenario_rows(scenario)
        assert len(rows) > 0, f'{scenario} non produce righe'
        for row in rows:
            assert set(row.keys()) == set(CSV_COLUMNS), f'{scenario}: colonne mancanti/extra'

def test_lean_isolated_spike_matches_spec_example():
    rows = build_scenario_rows('lean_isolated_spike')
    leans = [r['lean_deg'] for r in rows[:6]]
    assert leans == [18.0, 19.0, 21.0, 67.0, 20.0, 19.0]
