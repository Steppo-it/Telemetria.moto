"""Assembla report.html a partire dai frammenti delle altre sezioni (spec sezione 10)."""
from plotly.offline import get_plotlyjs

from analyzer.report.dashboard import build_dashboard_stats, render_dashboard_html
from analyzer.report.charts import render_telemetry_html
from analyzer.report.map_static import build_static_map_html
from analyzer.report.replay import render_replay_html
from analyzer.report.tables import (render_events_section, render_curves_section,
                                     render_sensor_quality_section, _SORT_JS)

_CSS = """
<style>
  body { font-family: -apple-system, sans-serif; background: #0A0E14; color: #E8ECF0; margin: 0; padding: 20px; }
  h1, h2 { border-bottom: 1px solid #1C2128; padding-bottom: 6px; }
  section { margin-bottom: 36px; }
  .dash-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px; }
  .dash-card { background: #12161D; border-radius: 8px; padding: 12px; display: flex; flex-direction: column; }
  .dash-card .label { font-size: 11px; color: #8AA0BE; text-transform: uppercase; }
  .dash-card .value { font-size: 22px; font-weight: 700; }
  table.sortable { border-collapse: collapse; width: 100%; }
  table.sortable th, table.sortable td { border: 1px solid #1C2128; padding: 6px 10px; text-align: left; }
  table.sortable th { cursor: pointer; background: #12161D; }
  .replay-icons { display: flex; gap: 30px; margin-top: 10px; }
  .icon-block { text-align: center; }
  .icon-value { font-size: 20px; font-weight: 700; border: 2px solid transparent; border-radius: 6px; padding: 2px 8px; margin-top: 4px; display: inline-block; }
  .curve-block { background: #12161D; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px; }
</style>
"""


def assemble_report_html(df, events, curves):
    stats = build_dashboard_stats(df, events)
    plotly_js = f'<script>{get_plotlyjs()}</script>'

    sections = [
        render_dashboard_html(stats),
        render_telemetry_html(df),
        f'<section id="map-static"><h2>Percorso (vista statica)</h2>{build_static_map_html(df, events)}</section>',
        render_replay_html(df),
        render_events_section(events),
        render_curves_section(curves),
        render_sensor_quality_section(df),
    ]

    return (
        '<!DOCTYPE html><html lang="it"><head><meta charset="utf-8">'
        f'<title>Report telemetria</title>{_CSS}{plotly_js}</head><body>'
        f'<h1>Report telemetria</h1>{"".join(sections)}{_SORT_JS}</body></html>'
    )
