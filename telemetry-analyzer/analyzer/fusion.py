"""Cross sensor validation (spec sezione 5) e caso pitch estremo + evento
verticale (spec sezione 3)."""
import numpy as np
import pandas as pd

from analyzer import config


def circular_diff_deg(heading_deg):
    """Differenza firmata tra campioni consecutivi di heading, in (-180, 180],
    gestendo correttamente il passaggio 359->0 (non e' un salto di -359)."""
    raw = heading_deg.diff()
    wrapped = (raw + 180) % 360 - 180
    return wrapped


def heading_change_window(heading_deg, window_samples=5):
    """Somma mobile di |Δheading| — proxy di "quanto si sta girando" nell'ultimo
    tratto, robusta al wraparound grazie a circular_diff_deg."""
    step = circular_diff_deg(heading_deg).fillna(0.0)
    return step.abs().rolling(window_samples, center=True, min_periods=1).sum()


def _speed_trend(speed_kmh, window_samples=3):
    return speed_kmh.diff(window_samples)


def detect_braking(accel_fwd_g, speed_kmh):
    """Frenata: velocita' in calo su una finestra breve E decelerazione oltre soglia."""
    trend = _speed_trend(speed_kmh)
    return (trend < 0).fillna(False) & (accel_fwd_g <= config.BRAKE_ENTER_G)


def detect_accelerating(accel_fwd_g, speed_kmh):
    """Accelerazione: velocita' in aumento E accelerazione positiva oltre soglia."""
    trend = _speed_trend(speed_kmh)
    return (trend > 0).fillna(False) & (accel_fwd_g >= config.ACCEL_ENTER_G)


def detect_curve(heading_deg, accel_lat_g, lean_deg):
    """Curva: heading cambia oltre soglia, accelerazione laterale significativa,
    segno del lean coerente con la direzione del cambio di heading. Convenzione:
    lean positivo = SX, heading in CALO = sterzata a sinistra (senso orario del
    compass) — le due cose devono avere lo stesso segno atteso."""
    change = heading_change_window(heading_deg)
    lat_significant = accel_lat_g.abs() >= config.LEAN_CROSS_ACCEL_LAT_MIN
    step = circular_diff_deg(heading_deg).fillna(0.0)
    # media mobile del passo di heading per un segno piu' stabile del solo ultimo campione
    step_trend = step.rolling(5, center=True, min_periods=1).mean()
    expected_lean_sign = -np.sign(step_trend)  # heading in calo (sx) -> lean atteso positivo
    actual_lean_sign = np.sign(lean_deg)
    sign_consistent = (
        (expected_lean_sign == actual_lean_sign)
        | (step_trend.abs() < 0.5)
        | (lean_deg.abs() < 2.0)
    )
    return (change >= config.HEADING_CHANGE_MIN_DEG) & lat_significant & sign_consistent


def detect_vertical_event(accel_vert_g):
    """Evento verticale (buca/dosso): accelerazione verticale netta oltre soglia."""
    return accel_vert_g.abs() >= config.VERT_EVENT_MIN_G


def detect_pitch_ambiguous(pitch_deg, accel_vert_g):
    """Pitch estremo isolato E coincidente (±1 campione) con un forte evento
    verticale: non e' classificabile con certezza come errore ne' come evento
    reale (spec sezione 3) — mai RED diretto, sempre un flag dedicato."""
    extreme = pitch_deg.abs() >= config.PITCH_EXTREME_DEG
    vertical = accel_vert_g.abs() >= config.PITCH_CROSS_ACCEL_VERT_MIN
    vertical_nearby = vertical | vertical.shift(1).fillna(False) | vertical.shift(-1).fillna(False)
    return extreme & vertical_nearby


def cross_sensor_corroboration(df):
    """Per ciascun segnale, un booleano per campione: e' corroborato da altri
    sensori in quel punto? Alimenta il bonus W_CROSS della confidence (Task 5)."""
    braking = detect_braking(df['accel_fwd_g'], df['speed_kmh'])
    accelerating = detect_accelerating(df['accel_fwd_g'], df['speed_kmh'])
    curve = detect_curve(df['heading_deg'], df['accel_lat_g'], df['lean_deg'])
    vertical = detect_vertical_event(df['accel_vert_g'])

    return {
        'lean': curve,
        'pitch': vertical,
        'accel_fwd': braking | accelerating,
        'accel_lat': curve,
        'accel_vert': vertical,
    }
