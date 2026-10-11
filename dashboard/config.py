"""Editable experimental thresholds; mirrored in firmware/Config.h."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Thresholds:
    min_samples: int = 60
    min_force_span: float = 4.0
    min_r_squared: float = 0.90
    max_baseline_samples: int = 600
    strain_floor: float = 50.0  # HX711 counts, NOT microstrain
    strain_relative_tolerance: float = 0.10
    noise_multiplier: float = 3.0
    vibration_floor: float = 0.10  # m/s²
    strain_weight: float = 0.80
    warning_score: float = 25.0
    anomaly_score: float = 55.0
    smoothing_alpha: float = 0.25
    deflection_floor: float = 3.0  # mm; HC-SR04 is not a sub-mm instrument
    deflection_relative_tolerance: float = 0.15
    range_margin: float = 0.5  # N beyond calibrated load envelope


THRESHOLDS = Thresholds()
SAMPLE_HZ = 100
TELEMETRY_HZ = 5
SERIAL_BAUD = 115200
STALE_SECONDS = 2.0
HISTORY_SIZE = 600

# Judge-test settings. 10 N is a simulation default, NOT a safe physical load rating.
DEMO_TARGET_FORCE_N = 10.0
DEMO_FORCE_TOLERANCE_N = 0.5
DEMO_HOLD_SECONDS = 2.0  # Enough real samples at the verified 5 Hz USB telemetry rate.
DEMO_MIN_SAMPLES = 8
RECONNECT_SECONDS = 2.0
ULTRASONIC_ENABLED = False  # Laptop simulation; hardware flag lives in Config.h.
# Independent live alarms; do not change structural scoring or baseline quality.
FORCE_ALARM_N = 0.75
VIBRATION_ALARM_M_S2 = 6.0  # Gravity-removed vibration RMS, not absolute gravity.
SIM_HEALTHY_COMPLIANCE_MM_PER_N = 0.8
SIM_ALTERED_COMPLIANCE_MM_PER_N = 1.4
DISTANCE_FILTER_ALPHA = 0.35
DISTANCE_MEDIAN_SAMPLES = 5
DISTANCE_MIN_MM = 20.0
DISTANCE_MAX_MM = 1000.0
DISTANCE_PERIOD_SECONDS = 0.07
DEMO_SETTLE_SECONDS = 0.7  # Let filtered distance settle before averaging at target.
