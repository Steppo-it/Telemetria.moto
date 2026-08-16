"""Grafici Plotly sincronizzati RAW+FILTERED per i 5 segnali (spec sezione 10, punto 2)."""
import plotly.graph_objects as go
from plotly.subplots import make_subplots

CHART_SPECS = [
    ('speed_kmh', None, 'Velocità (km/h)'),
    ('lean_deg', 'lean_filtered', 'Piega (°)'),
    ('pitch_deg', 'pitch_filtered', 'Beccheggio (°)'),
    ('accel_fwd_g', 'accel_fwd_filtered', 'Accel. longitudinale (g)'),
    ('accel_lat_g', 'accel_lat_filtered', 'Accel. laterale (g)'),
    ('accel_vert_g', 'accel_vert_filtered', 'Accel. verticale (g)'),
]


def build_telemetry_figure(df):
    fig = make_subplots(rows=len(CHART_SPECS), cols=1, shared_xaxes=True,
                         subplot_titles=[t for _, _, t in CHART_SPECS], vertical_spacing=0.04)
    x = df['timestamp']
    for row, (raw_col, filtered_col, title) in enumerate(CHART_SPECS, start=1):
        fig.add_trace(go.Scatter(x=x, y=df[raw_col], name=f'{title} (RAW)',
                                  line=dict(dash='dot', width=1), opacity=0.5), row=row, col=1)
        if filtered_col:
            fig.add_trace(go.Scatter(x=x, y=df[filtered_col], name=f'{title} (FILTERED)',
                                      line=dict(width=2)), row=row, col=1)
            signal_key = filtered_col.replace('_filtered', '')
            outliers = df[df[f'{signal_key}_flag'] == 'RED']
            if len(outliers):
                fig.add_trace(go.Scatter(x=outliers['timestamp'], y=outliers[raw_col], mode='markers',
                                          marker=dict(color='red', size=7, symbol='x'),
                                          name=f'{title} outlier'), row=row, col=1)
    fig.update_layout(height=220 * len(CHART_SPECS), showlegend=False,
                       title='Telemetria nel tempo (RAW tratteggiato, FILTERED pieno, outlier evidenziati)')
    return fig


def render_telemetry_html(df):
    fig = build_telemetry_figure(df)
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id='telemetry-charts')
