"""Repeatable 100 Hz virtual sensors. Damage does not change applied force."""
import math
import random
from collections import deque
from .config import (SAMPLE_HZ, ULTRASONIC_ENABLED, SIM_HEALTHY_COMPLIANCE_MM_PER_N,
                     SIM_ALTERED_COMPLIANCE_MM_PER_N, DISTANCE_PERIOD_SECONDS)
from .ultrasonic import DistanceFilter


class VibrationWindow:
    """Gravity removed by a low-pass vector estimate; 1 s high-pass RMS/peak."""
    def __init__(self):
        self.gravity = None
        self.values = deque(maxlen=SAMPLE_HZ)

    def reset(self):
        self.gravity = None
        self.values.clear()

    def add(self, xyz):
        if self.gravity is None:
            self.gravity = list(xyz)
        alpha = 0.02
        self.gravity = [g + alpha * (a - g) for a, g in zip(xyz, self.gravity)]
        dynamic = math.sqrt(sum((a - g) ** 2 for a, g in zip(xyz, self.gravity)))
        self.values.append(dynamic)
        rms = math.sqrt(sum(v * v for v in self.values) / len(self.values))
        return dynamic, rms, max(self.values)

    @property
    def ready(self):
        return len(self.values) == SAMPLE_HZ


class Simulator:
    def __init__(self, seed=42):
        self.random = random.Random(seed)
        self.distance_random = random.Random(seed+1)
        self.ultrasonic_enabled = ULTRASONIC_ENABLED
        self.distance_zero = 150.0
        self.distance_filter = DistanceFilter()
        self.last_distance_time = -1
        self.time = 0.0
        self.mode = "NORMAL"
        self.auto_force = True
        self.manual_force = 0.0
        self.strain_offset = 50000.0
        self.load_offset = 100000.0
        self.window = VibrationWindow()

    @property
    def force(self):
        return 7 + 6 * math.sin(2 * math.pi * self.time / 16) if self.auto_force else self.manual_force

    def zero(self):
        if abs(self.force) > 0.25:
            raise ValueError("Unload the simulated wing first: disable automatic sweep and set force to 0 N.")
        self.strain_offset = 50000.0
        self.load_offset = 100000.0
        self.window.reset()
        self.distance_zero = 150.0
        self.distance_filter = DistanceFilter()

    def sample(self, dt=1 / SAMPLE_HZ):
        self.time += dt
        force = self.force
        damage = self.mode == "ANOMALY"
        slope = 124.0 if damage else 80.0
        # ADC quantization and independent electrical / mechanical noise.
        load_raw = round(100000 + force * 10000 + self.random.gauss(0, 90))
        strain_raw = round(50000 + slope * force + self.random.gauss(0, 5))
        amplitude = (0.70 if damage else 0.16) + 0.002 * force
        frequency = 7 if damage else 11
        x = amplitude * math.sin(2 * math.pi * frequency * self.time) + self.random.gauss(0, .018)
        y = .035 * math.sin(2 * math.pi * 4 * self.time) + self.random.gauss(0, .008)
        z = 9.80665 + self.random.gauss(0, .01)
        acceleration, rms, peak = self.window.add((x, y, z))
        if self.ultrasonic_enabled and self.time-self.last_distance_time >= DISTANCE_PERIOD_SECONDS:
            self.last_distance_time = self.time
            compliance = SIM_ALTERED_COMPLIANCE_MM_PER_N if damage else SIM_HEALTHY_COMPLIANCE_MM_PER_N
            self.distance_filter.add(150-force*compliance+self.distance_random.gauss(0,.25))
        tip_ready = self.ultrasonic_enabled and self.distance_filter.ready
        return dict(time_ms=round(self.time * 1000), force_n=(load_raw - self.load_offset) / 10000,
                    load_raw=load_raw, strain_raw=strain_raw, strain_delta=strain_raw - self.strain_offset,
                    acceleration=acceleration, accel_rms=rms, vibration_peak=peak,
                    accel_x=x, accel_y=y, accel_z=z, sensors_ok=self.window.ready,
                    distance_mm=self.distance_filter.value if tip_ready else None,
                    tip_deflection_mm=self.distance_zero-self.distance_filter.value if tip_ready else None,
                    sensor_status={"load": "ok", "strain": "ok", "vibration": "ok" if self.window.ready else "settling", "ultrasonic": "ok" if tip_ready else "settling" if self.ultrasonic_enabled else "disabled"},
                    force_calibrated=True, zeroed=True, simulation=True, simulation_mode=self.mode)
