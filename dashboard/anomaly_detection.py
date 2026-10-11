"""Transparent least-squares baseline and experimental response score.

Strain remains ADC counts. A measured strain-gauge factor, bridge excitation,
gain and mechanical calibration are required before reporting microstrain.
"""
import math
from dataclasses import asdict, dataclass
from .config import THRESHOLDS, Thresholds


@dataclass
class Baseline:
    k: float
    b: float
    residual_std: float
    vibration_mean: float
    vibration_std: float
    force_min: float
    force_max: float
    r_squared: float
    samples: int

    strain_available: bool = True
    vibration_available: bool = True
    deflection: dict = None
    vibration_fit: dict = None

    def to_dict(self):
        return asdict(self)


class Detector:
    def __init__(self, thresholds: Thresholds = THRESHOLDS):
        self.thresholds = thresholds
        self.baseline = None
        self.collecting = False
        self.samples = []
        self.smoothed_anomaly = 0.0

    def reset(self):
        self.baseline = None
        self.collecting = False
        self.samples = []
        self.smoothed_anomaly = 0.0

    def start(self):
        self.reset()
        self.collecting = True

    def stop(self):
        if not self.collecting:
            raise ValueError("Start a healthy baseline sweep first.")
        n = len(self.samples)
        cfg = self.thresholds
        if n < cfg.min_samples:
            raise ValueError(f"Need at least {cfg.min_samples} samples; have {n}. Keep sweeping.")
        forces = [s[0] for s in self.samples]
        if max(forces) - min(forces) < cfg.min_force_span:
            raise ValueError(f"Sweep at least {cfg.min_force_span:g} N; constant force cannot establish stiffness.")
        fx = sum(forces) / n
        strain_fit = self.fit([(s[0], s[1]) for s in self.samples if self.finite(s[1])])
        deflection_fit = self.fit([(s[0], s[3]) for s in self.samples if self.finite(s[3])])
        if deflection_fit and deflection_fit['k'] <= 0:
            deflection_fit = None
        if not strain_fit and not deflection_fit:
            raise ValueError("Poor force/response fit. Check sensors and repeat a smooth healthy sweep.")
        vibrations = [s[2] for s in self.samples if self.finite(s[2])]
        vm = sum(vibrations) / len(vibrations) if vibrations else 0
        vs = math.sqrt(sum((v - vm) ** 2 for v in vibrations) / max(1, len(vibrations) - 1))
        available = [f for f in (strain_fit, deflection_fit) if f]
        envelope_min = max(f['force_min'] for f in available)
        envelope_max = min(f['force_max'] for f in available)
        if envelope_max-envelope_min < cfg.min_force_span:
            raise ValueError('Healthy sensor fits need a shared load envelope of at least 4 N.')
        sf = strain_fit or dict(k=0, b=0, residual_std=0, r_squared=0)
        self.baseline = Baseline(sf['k'], sf['b'], sf['residual_std'], vm, vs,
                                 envelope_min, envelope_max, sf['r_squared'], n,
                                 strain_fit is not None, len(vibrations) >= cfg.min_samples,
                                 deflection_fit,
                                 self.fit([(s[0], s[2]) for s in self.samples if self.finite(s[2])], quality=False))
        self.collecting = False
        self.smoothed_anomaly = 0.0
        return self.baseline

    @staticmethod
    def finite(value):
        return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)

    def fit(self, pairs, quality=True):
        n = len(pairs)
        cfg = self.thresholds
        if n < cfg.min_samples or max(x for x, _ in pairs) - min(x for x, _ in pairs) < cfg.min_force_span:
            return None
        fx = sum(x for x, _ in pairs) / n
        sy = sum(y for _, y in pairs) / n
        xx = sum((x - fx) ** 2 for x, _ in pairs)
        xy = sum((x - fx) * (y - sy) for x, y in pairs)
        yy = sum((y - sy) ** 2 for _, y in pairs)
        k = xy / xx
        sse = max(0, yy - xy * xy / xx)
        r2 = 1 - sse / yy if yy > 1e-9 else 0
        if quality and (abs(k) < 1e-6 or r2 < cfg.min_r_squared):
            return None
        return dict(k=k, b=sy-k*fx, residual_std=math.sqrt(sse/max(1,n-2)),
                    r_squared=r2, samples=n, force_min=min(x for x,_ in pairs),
                    force_max=max(x for x,_ in pairs))

    def rebase(self, force_shift=0, strain_shift=0, deflection_shift=0):
        """Translate offsets without changing the measured healthy response slopes."""
        b = self.baseline
        if b:
            b.b += b.k * force_shift + strain_shift
            b.force_min -= force_shift
            b.force_max -= force_shift
            for fit, shift in ((b.deflection, deflection_shift), (b.vibration_fit, 0)):
                if fit:
                    fit['b'] += fit['k'] * force_shift + shift
                    fit['force_min'] -= force_shift
                    fit['force_max'] -= force_shift
        self.smoothed_anomaly = 0

    def evaluate(self, force, strain, vibration, *, valid=True, calibrated=True,
                 tip_deflection_mm=None, strain_valid=True, vibration_valid=True, instantaneous=False):
        result = dict(expected_strain=None, strain_deviation=None, strain_deviation_pct=None,
                      expected_deflection_mm=None, deflection_deviation_pct=None,
                      stiffness_n_per_mm=None, baseline_stiffness_n_per_mm=None,
                      health_score=None, anomaly_score=None, strain_ratio=None,
                      vibration_ratio=None, deflection_ratio=None, coverage=[], status="NEEDS_BASELINE")
        # Explicit secondary flags permit loss of a sensor; legacy callers still reject NaN.
        strain = strain if strain_valid and self.finite(strain) else None
        vibration = vibration if vibration_valid and self.finite(vibration) else None
        if not valid or not self.finite(force) or (strain_valid and strain is None) or (vibration_valid and vibration is None):
            result['status'] = 'SENSOR_FAULT'
            return result
        if not calibrated:
            result['status'] = 'NEEDS_CALIBRATION'
            return result
        tip = tip_deflection_mm if self.finite(tip_deflection_mm) else None
        if self.collecting:
            if strain is not None or tip is not None:
                if len(self.samples) < self.thresholds.max_baseline_samples:
                    self.samples.append((force, strain, vibration, tip))
            result['status'] = 'CALIBRATING'
            return result
        b = self.baseline
        if b is None:
            return result
        cfg = self.thresholds
        if b.strain_available and strain is not None:
            result['expected_strain'] = b.k*force+b.b
            result['strain_deviation'] = abs(strain-result['expected_strain'])
        if not b.force_min-cfg.range_margin <= force <= b.force_max+cfg.range_margin:
            result['status'] = 'OUT_OF_RANGE'
            return result
        ratios = []
        if b.strain_available and strain is not None:
            expected = b.k*force+b.b
            deviation = abs(strain-expected)
            tolerance = max(cfg.strain_floor,cfg.noise_multiplier*b.residual_std)+cfg.strain_relative_tolerance*abs(expected)
            ratio = deviation/tolerance
            result.update(expected_strain=expected, strain_deviation=deviation,
                          strain_deviation_pct=100*(strain-expected)/abs(expected) if abs(expected)>cfg.strain_floor else None,
                          strain_ratio=ratio)
            ratios.append((ratio, cfg.strain_weight)); result['coverage'].append('strain')
        if b.deflection:
            fit = b.deflection
            result['baseline_stiffness_n_per_mm'] = 1/fit['k']
            if tip is not None and fit['force_min']-cfg.range_margin <= force <= fit['force_max']+cfg.range_margin:
                expected = fit['k']*force+fit['b']
                ratio = abs(tip-expected)/(max(cfg.deflection_floor,cfg.noise_multiplier*fit['residual_std'])+cfg.deflection_relative_tolerance*abs(expected))
                displacement = tip-fit['b']
                result.update(expected_deflection_mm=expected, deflection_ratio=ratio,
                              deflection_deviation_pct=100*(tip-expected)/abs(expected) if abs(expected)>cfg.deflection_floor else None,
                              stiffness_n_per_mm=force/displacement if displacement>cfg.deflection_floor and force>0 else None)
                ratios.append((ratio,cfg.strain_weight)); result['coverage'].append('deflection')
        if not ratios:
            result['status'] = 'SENSOR_FAULT'
            return result
        if b.vibration_available and vibration is not None:
            # Keep the existing pooled RMS score; expose force-conditioned RMS as an additional fit.
            ratio = abs(vibration-b.vibration_mean)/max(cfg.vibration_floor,cfg.noise_multiplier*b.vibration_std)
            result['vibration_ratio'] = ratio
            ratios.append((ratio,1-cfg.strain_weight)); result['coverage'].append('vibration')
        raw = 50*sum(min(r,2)*w for r,w in ratios)/sum(w for _,w in ratios)
        if instantaneous:
            score = raw
        else:
            self.smoothed_anomaly += cfg.smoothing_alpha*(raw-self.smoothed_anomaly)
            score = self.smoothed_anomaly
        status = 'STRUCTURAL ANOMALY' if score>=cfg.anomaly_score else 'WARNING' if score>=cfg.warning_score else 'NORMAL'
        result.update(health_score=round(100-score), anomaly_score=score, status=status)
        return result

    def state(self):
        return dict(collecting=self.collecting, samples=len(self.samples),
                    capacity=self.thresholds.max_baseline_samples,
                    baseline=self.baseline.to_dict() if self.baseline else None)
