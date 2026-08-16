"""Tabelle eventi/curve e sezione qualità sensori (spec sezione 10, punti 4-6)."""
from analyzer import config


def _sortable_table_html(table_id, headers, rows):
    thead = ''.join(f'<th onclick="sortTable(\'{table_id}\', {i})">{h}</th>' for i, h in enumerate(headers))
    tbody = ''.join('<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>' for row in rows)
    return f'<table id="{table_id}" class="sortable"><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>'


_SORT_JS = """
<script>
function sortTable(tableId, col) {
  var table = document.getElementById(tableId);
  var rows = Array.from(table.tBodies[0].rows);
  var asc = table.dataset.sortCol != col || table.dataset.sortDir !== 'asc';
  rows.sort(function(a, b) {
    var av = a.cells[col].textContent, bv = b.cells[col].textContent;
    var an = parseFloat(av), bn = parseFloat(bv);
    var cmp = (!isNaN(an) && !isNaN(bn)) ? (an - bn) : av.localeCompare(bv);
    return asc ? cmp : -cmp;
  });
  rows.forEach(function(r) { table.tBodies[0].appendChild(r); });
  table.dataset.sortCol = col;
  table.dataset.sortDir = asc ? 'asc' : 'desc';
}
</script>
"""


def render_events_section(events):
    headers = ['Tipo', 'Inizio', 'Durata (s)', 'V iniziale', 'V finale', 'V max',
               'Lean max', 'Accel long. max', 'Accel lat. max', 'Accel vert. max', 'Confidence']
    rows = [
        [e['event_type'], e['t_start'].strftime('%H:%M:%S'), f"{e['duration_s']:.1f}",
         f"{e['v_start']:.0f}", f"{e['v_end']:.0f}", f"{e['v_max']:.0f}", f"{e['lean_max']:.0f}",
         f"{e['accel_fwd_max']:.2f}", f"{e['accel_lat_max']:.2f}", f"{e['accel_vert_max']:.2f}",
         f"{e['confidence']:.0f}"]
        for e in events
    ]
    table = _sortable_table_html('events-table', headers, rows)
    return f'<section id="events"><h2>Eventi rilevati</h2>{table}</section>'


def render_curves_section(curves):
    if not curves:
        return '<section id="curves"><h2>Curve</h2><p>Nessuna curva rilevata.</p></section>'
    blocks = []
    for i, c in enumerate(curves, start=1):
        apex_text = (c['apex_time'].strftime('%H:%M:%S') if c['apex_status'] == 'CONFIRMED' else 'APEX UNCERTAIN')
        blocks.append(
            f'<div class="curve-block"><h3>Curva {i} — {c["t_start"].strftime("%H:%M:%S")} '
            f'({c["duration_s"]:.1f}s)</h3><ul>'
            f'<li>Velocità: {c["v_entry"]:.0f} → {c["v_min"]:.0f} (min) → {c["v_exit"]:.0f} km/h</li>'
            f'<li>Lean massimo attendibile: {c["lean_max_filtered"]:.0f}° '
            f'(confidence {c["lean_max_confidence"]:.0f})</li>'
            f'<li>Accelerazione laterale massima: {c["accel_lat_max_filtered"]:.2f}g</li>'
            f'<li>Frenata in ingresso: {"sì" if c["braking_detected"] else "no"} '
            f'(min {c["accel_fwd_min_entry"]:.2f}g)</li>'
            f'<li>Apex: {apex_text}</li>'
            f'<li>Riapertura gas rilevata: {"sì (stimata)" if c["throttle_reopening_detected"] else "no"}</li>'
            f'</ul></div>'
        )
    return f'<section id="curves"><h2>Curve</h2>{"".join(blocks)}</section>'


def render_sensor_quality_section(df):
    n = len(df)
    rows = []
    worst_signal, worst_red_pct = None, -1.0
    for signal in config.SIGNALS:
        flags = df[f'{signal}_flag']
        green_pct = 100.0 * (flags == 'GREEN').sum() / n if n else 0.0
        yellow_pct = 100.0 * (flags == 'YELLOW').sum() / n if n else 0.0
        red_pct = 100.0 * (flags == 'RED').sum() / n if n else 0.0
        mean_conf = float(df[f'{signal}_confidence'].mean()) if n else 0.0
        if red_pct > worst_red_pct:
            worst_red_pct, worst_signal = red_pct, signal
        rows.append([signal, f'{green_pct:.0f}%', f'{yellow_pct:.0f}%', f'{red_pct:.0f}%', f'{mean_conf:.0f}'])

    headers = ['Segnale', '% GREEN', '% YELLOW', '% RED', 'Confidence media']
    table = _sortable_table_html('quality-table', headers, rows)
    n_gaps = int(df['gap_flag'].sum())
    return (f'<section id="sensor-quality"><h2>Qualità sensori</h2>'
            f'<p>Gap temporali rilevati: {n_gaps}. Sensore più problematico: '
            f'<b>{worst_signal}</b> ({worst_red_pct:.0f}% RED).</p>{table}</section>')
