"""Dashboard generale del report (spec sezione 10, punto 1)."""
import numpy as np

from analyzer import config


def _distance_meters(lat1, lon1, lat2, lon2):
    """Approssimazione equirettangolare — stessa tecnica della PWA (adeguata per
    distanze brevi tra fix consecutivi, non per distanze globali)."""
    d_lon = (lon2 - lon1) * np.cos(np.radians(lat1)) * 111320
    d_lat = (lat2 - lat1) * 110540
    return float(np.hypot(d_lon, d_lat))


def total_distance_m(df):
    lat = df['lat'].to_numpy()
    lon = df['lon'].to_numpy()
    total = 0.0
    for i in range(1, len(lat)):
        total += _distance_meters(lat[i - 1], lon[i - 1], lat[i], lon[i])
    return total


def build_dashboard_stats(df, events):
    n = len(df)
    duration_s = (df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).total_seconds() if n > 1 else 0.0
    red_counts = {s: int((df[f'{s}_flag'] == 'RED').sum()) for s in config.SIGNALS}
    confidence_cols = [f'{s}_confidence' for s in config.SIGNALS]

    return {
        'duration_s': duration_s,
        'distance_km': total_distance_m(df) / 1000.0,
        'speed_max_kmh': float(df['speed_kmh'].max()) if n else 0.0,
        'speed_mean_kmh': float(df['speed_kmh'].mean()) if n else 0.0,
        'brake_max_g': float(df['accel_fwd_filtered'].min()) if n else 0.0,
        'accel_max_g': float(df['accel_fwd_filtered'].max()) if n else 0.0,
        'lat_max_g': float(df['accel_lat_filtered'].abs().max()) if n else 0.0,
        'lean_max_raw': float(df['lean_deg'].abs().max()) if n else 0.0,
        'lean_max_filtered': float(df['lean_filtered'].abs().max()) if n else 0.0,
        'n_events': len(events),
        'n_anomalies_red': sum(red_counts.values()),
        'n_gaps': int(df['gap_flag'].sum()),
        'overall_quality': float(df[confidence_cols].to_numpy().mean()) if n else 0.0,
    }


def render_dashboard_html(stats):
    minutes = int(stats['duration_s'] // 60)
    seconds = int(stats['duration_s'] % 60)
    cards = [
        ('Durata', f"{minutes}:{seconds:02d}"),
        ('Distanza GPS', f"{stats['distance_km']:.1f} km"),
        ('Velocità max', f"{stats['speed_max_kmh']:.0f} km/h"),
        ('Velocità media', f"{stats['speed_mean_kmh']:.0f} km/h"),
        ('Frenata massima', f"{stats['brake_max_g']:.2f} g"),
        ('Accelerazione massima', f"{stats['accel_max_g']:.2f} g"),
        ('Accel. laterale massima', f"{stats['lat_max_g']:.2f} g"),
        ('Lean massimo RAW', f"{stats['lean_max_raw']:.0f}°"),
        ('Lean massimo FILTERED', f"{stats['lean_max_filtered']:.0f}°"),
        ('Eventi rilevati', str(stats['n_events'])),
        ('Anomalie (RED)', str(stats['n_anomalies_red'])),
        ('Gap temporali', str(stats['n_gaps'])),
        ('Qualità sessione', f"{stats['overall_quality']:.0f}/100"),
    ]
    cards_html = ''.join(
        f'<div class="dash-card"><span class="label">{label}</span>'
        f'<span class="value">{value}</span></div>'
        for label, value in cards
    )
    return f'<section id="dashboard"><h2>Dashboard generale</h2><div class="dash-grid">{cards_html}</div></section>'
