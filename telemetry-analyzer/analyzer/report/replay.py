"""Replay Plotly sincronizzato con slider + icone SVG piega/beccheggio (spec sezione 10, punto 3b)."""
import json

import plotly.graph_objects as go

from analyzer import config


def _decimate_indices(df, decimation_s):
    """Ritorna gli indici di riga da usare come frame del replay, mantenendo un
    intervallo minimo `decimation_s` tra un frame e il successivo (spec: sessioni
    lunghe restano fluide, i dati sottostanti restano a piena risoluzione altrove)."""
    n = len(df)
    if n == 0:
        return []
    indices = [0]
    last_ts = df['timestamp'].iloc[0]
    for i in range(1, n):
        if (df['timestamp'].iloc[i] - last_ts).total_seconds() >= decimation_s:
            indices.append(i)
            last_ts = df['timestamp'].iloc[i]
    if indices[-1] != n - 1:
        indices.append(n - 1)
    return indices


def build_replay_figure(df, decimation_s=None):
    decimation_s = decimation_s if decimation_s is not None else config.REPLAY_DECIMATION_S
    indices = _decimate_indices(df, decimation_s)

    fig = go.Figure()
    fig.add_trace(go.Scattermapbox(lat=df['lat'], lon=df['lon'], mode='lines',
                                    line=dict(width=3, color='#1f77b4'), name='Percorso'))
    fig.add_trace(go.Scattermapbox(lat=[df['lat'].iloc[indices[0]]], lon=[df['lon'].iloc[indices[0]]],
                                    mode='markers', marker=dict(size=14, color='orange'), name='Posizione'))

    frames = [
        go.Frame(name=str(idx), traces=[0, 1], data=[
            go.Scattermapbox(lat=df['lat'], lon=df['lon']),
            go.Scattermapbox(lat=[df['lat'].iloc[idx]], lon=[df['lon'].iloc[idx]]),
        ])
        for idx in indices
    ]
    fig.frames = frames

    steps = [
        dict(method='animate', label=df['timestamp'].iloc[idx].strftime('%H:%M:%S'),
             args=[[str(idx)], dict(mode='immediate', frame=dict(duration=0, redraw=True),
                                     transition=dict(duration=0))])
        for idx in indices
    ]

    fig.update_layout(
        mapbox=dict(style='open-street-map', zoom=14,
                     center=dict(lat=float(df['lat'].mean()), lon=float(df['lon'].mean()))),
        height=520, margin=dict(l=0, r=0, t=30, b=0),
        sliders=[dict(active=0, steps=steps, currentvalue=dict(prefix='Tempo: '))],
        updatemenus=[dict(type='buttons', buttons=[
            dict(label='▶ Play', method='animate',
                 args=[None, dict(frame=dict(duration=300, redraw=True), fromcurrent=True)]),
            dict(label='⏸ Pausa', method='animate', args=[[None], dict(mode='immediate')]),
        ])],
    )
    return fig, indices


def _replay_frame_payload(df, indices):
    """Dati per-frame per la sincronizzazione JS — valori FILTERED, mai raw, con
    il proprio flag di qualità (spec sezione 10, punto 3b)."""
    payload = {}
    for idx in indices:
        row = df.iloc[idx]
        payload[str(idx)] = {
            'lean': round(float(row['lean_filtered']), 1), 'lean_flag': row['lean_flag'],
            'pitch': round(float(row['pitch_filtered']), 1), 'pitch_flag': row['pitch_flag'],
        }
    return payload


_ICON_SVG = """
<div class="replay-icons">
  <div class="icon-block">
    <div class="icon-label">Piega</div>
    <svg viewBox="0 0 100 100" width="90" height="90">
      <g id="lean-icon-group" transform="rotate(0 50 50)">
        <rect x="20" y="45" width="60" height="10" rx="5" fill="#5CC8FF"/>
        <circle cx="30" cy="70" r="10" fill="#1C2128"/>
        <circle cx="70" cy="70" r="10" fill="#1C2128"/>
      </g>
    </svg>
    <div id="lean-value" class="icon-value">0°</div>
  </div>
  <div class="icon-block">
    <div class="icon-label">Beccheggio</div>
    <svg viewBox="0 0 100 100" width="90" height="90">
      <g id="pitch-icon-group" transform="rotate(0 50 50)">
        <rect x="15" y="45" width="70" height="10" rx="5" fill="#5CC8FF"/>
        <polygon points="85,45 100,50 85,55" fill="#5CC8FF"/>
      </g>
    </svg>
    <div id="pitch-value" class="icon-value">0°</div>
  </div>
</div>
"""

_SYNC_JS = """
<script>
(function() {{
  var replayData = {payload_json};
  function updateIcons(frameName) {{
    var d = replayData[frameName];
    if (!d) return;
    document.getElementById('lean-icon-group').setAttribute('transform', 'rotate(' + (-d.lean) + ' 50 50)');
    document.getElementById('pitch-icon-group').setAttribute('transform', 'rotate(' + (-d.pitch) + ' 50 50)');
    var leanValue = document.getElementById('lean-value');
    var pitchValue = document.getElementById('pitch-value');
    leanValue.textContent = d.lean.toFixed(0) + '°';
    pitchValue.textContent = d.pitch.toFixed(0) + '°';
    leanValue.style.borderColor = d.lean_flag === 'YELLOW' ? '#FFB020' : (d.lean_flag === 'RED' ? '#FF4040' : 'transparent');
    pitchValue.style.borderColor = d.pitch_flag === 'YELLOW' ? '#FFB020' : (d.pitch_flag === 'RED' ? '#FF4040' : 'transparent');
  }}
  var graphDiv = document.getElementById('{div_id}');
  if (graphDiv) {{
    graphDiv.on('plotly_animatingframe', function(e) {{ updateIcons(e.name); }});
    graphDiv.on('plotly_sliderchange', function(e) {{
      var step = graphDiv.layout.sliders[0].steps[e.slider.active];
      if (step) updateIcons(step.args[0][0]);
    }});
    updateIcons('{first_idx}');
  }}
}})();
</script>
"""


def render_replay_html(df, div_id='replay-map'):
    fig, indices = build_replay_figure(df)
    map_html = fig.to_html(full_html=False, include_plotlyjs=False, div_id=div_id)
    payload = _replay_frame_payload(df, indices)
    sync_js = _SYNC_JS.format(payload_json=json.dumps(payload), div_id=div_id, first_idx=indices[0])
    return f'<section id="replay"><h2>Replay percorso</h2>{map_html}{_ICON_SVG}{sync_js}</section>'
