"""Mappa statica Folium, colorata per velocità (spec sezione 10, punto 3a)."""
import folium
import numpy as np


def _speed_to_color(speed, speed_min, speed_max):
    """Gradiente blu (lento) -> verde -> giallo -> rosso (veloce), a 3 tratti lineari.
    Restituisce un grigio neutro se `speed` non è un numero finito (es. GPS che non
    riporta la velocità per quel fix) — non deve mai apparire come "il più veloce"."""
    if not np.isfinite(speed):
        return '#808080'
    if speed_max <= speed_min:
        ratio = 0.0
    else:
        ratio = (speed - speed_min) / (speed_max - speed_min)
    ratio = max(0.0, min(1.0, ratio))
    if ratio < 0.5:
        t = ratio / 0.5
        r, g, b = int(255 * t), int(100 + 155 * t), int(255 * (1 - t))
    else:
        t = (ratio - 0.5) / 0.5
        r, g, b = 255, int(255 * (1 - t)), 0
    return f'#{r:02x}{g:02x}{b:02x}'


_EVENT_ICONS = {
    'FRENATA': 'stop', 'ACCELERAZIONE': 'forward', 'CURVA': 'refresh',
    'FRENATA_CURVA': 'exclamation-triangle', 'EVENTO_VERTICALE': 'warning-sign',
    'ANOMALIA_SENSORE': 'question-sign',
}


def build_static_map_html(df, events):
    df = df.dropna(subset=['lat', 'lon']).reset_index(drop=True)
    if len(df) == 0:
        return '<p>Nessun dato GPS valido per la mappa.</p>'

    lat0, lon0 = float(df['lat'].iloc[0]), float(df['lon'].iloc[0])
    fmap = folium.Map(location=[lat0, lon0], zoom_start=15, tiles='OpenStreetMap')

    speed_min = float(df['speed_kmh'].min())
    speed_max = float(df['speed_kmh'].max())
    lats, lons, speeds = df['lat'].to_numpy(), df['lon'].to_numpy(), df['speed_kmh'].to_numpy()
    for i in range(len(df) - 1):
        color = _speed_to_color((speeds[i] + speeds[i + 1]) / 2, speed_min, speed_max)
        folium.PolyLine([(lats[i], lons[i]), (lats[i + 1], lons[i + 1])],
                         color=color, weight=4, opacity=0.85).add_to(fmap)

    for event in events:
        window = df[(df['timestamp'] >= event['t_start']) & (df['timestamp'] <= event['t_end'])]
        if len(window) == 0:
            continue
        mid = window.iloc[len(window) // 2]
        folium.Marker(
            [mid['lat'], mid['lon']],
            popup=f"{event['event_type']} — {event['duration_s']:.1f}s, confidence {event['confidence']:.0f}",
            icon=folium.Icon(icon=_EVENT_ICONS.get(event['event_type'], 'info-sign'), color='darkred'),
        ).add_to(fmap)

    return fmap._repr_html_()
