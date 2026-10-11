"""Bounded same-force judging window. Results are measured, never scripted."""
from .anomaly_detection import Baseline, Detector
from .config import (DEMO_TARGET_FORCE_N, DEMO_FORCE_TOLERANCE_N,
                     DEMO_HOLD_SECONDS, DEMO_MIN_SAMPLES, DEMO_SETTLE_SECONDS)


class DemoTest:
    def __init__(self):
        self.target = DEMO_TARGET_FORCE_N
        self.reset()

    def reset(self):
        self.phase = 'READY'
        self.samples = []
        self.result = None
        self.message = 'Unload the wing, press ZERO, then start the test.'
        self.baseline = None
        self.start_time = None
        self.source_time = None
        self.source_start = None
        self.coverage = None

    def start(self, baseline, target, connected, pending):
        if not Detector.finite(target) or not 0 < target <= 49:
            raise ValueError('Target must be a positive force no greater than 49 N.')
        if not connected or pending:
            raise ValueError('Wait for live data and completed zero/calibration commands.')
        if not baseline:
            raise ValueError('Establish a healthy baseline first.')
        # Entire target tolerance window must be within the measured range.
        if target-DEMO_FORCE_TOLERANCE_N < baseline['force_min'] or target+DEMO_FORCE_TOLERANCE_N > baseline['force_max']:
            raise ValueError(f'Choose a target whose ±{DEMO_FORCE_TOLERANCE_N:g} N window is inside the healthy load envelope.')
        self.reset()
        self.target = target
        self.baseline = dict(baseline)
        self.phase = 'LOADING'
        self.message = 'Push at the marked loading point and hold near the target.'

    def fail(self, message):
        if self.phase in ('LOADING', 'HOLDING'):
            self.phase = 'INTERRUPTED'
            self.samples = []
            self.message = message

    def add(self, sample, now):
        if self.phase not in ('LOADING', 'HOLDING'):
            return
        rated = sample.get('status') in ('NORMAL', 'WARNING', 'STRUCTURAL ANOMALY')
        if not Detector.finite(sample.get('force_n')) or not sample.get('force_calibrated') or not sample.get('zeroed') or sample.get('status') not in ('NORMAL','WARNING','STRUCTURAL ANOMALY','OUT_OF_RANGE'):
            self.fail('Test interrupted: valid calibrated structural response is required. Reset and retry.')
            return
        if abs(sample['force_n']-self.target) > DEMO_FORCE_TOLERANCE_N:
            self.phase = 'LOADING'; self.samples = []; self.start_time = None; self.source_time = None; self.coverage = None
            self.message = f'Adjust to the target force; keep it within ±{DEMO_FORCE_TOLERANCE_N:g} N.'
            return
        if not rated:
            self.fail('Target response is outside the comparable healthy load envelope. Reset and choose a tested target.')
            return
        # Use only contiguous samples with unchanged sensor coverage and time advancing.
        coverage = sample.get('coverage', ['strain', 'vibration'])
        if self.coverage is not None and coverage != self.coverage:
            self.fail('Sensor coverage or device clock changed. Reset and retry.')
            return
        if self.source_time is not None and sample['time_ms'] <= self.source_time:
            self.fail('Device clock stopped. Reset and retry.')
            return
        self.coverage = list(coverage)
        self.phase = 'HOLDING'
        self.message = 'TARGET REACHED · Hold steady while readings settle and are collected.'
        if self.start_time is None:
            self.start_time = now
            self.source_start = sample["time_ms"]
        self.source_time = sample['time_ms']
        if now-self.start_time >= DEMO_SETTLE_SECONDS:
            self.samples.append(sample)
        self.samples = self.samples[-100:]
        if now-self.start_time < DEMO_HOLD_SECONDS+DEMO_SETTLE_SECONDS or (sample["time_ms"]-self.source_start)/1000 < DEMO_HOLD_SECONDS+DEMO_SETTLE_SECONDS or len(self.samples) < DEMO_MIN_SAMPLES:
            return
        avg = lambda key: sum(s[key] for s in self.samples)/len(self.samples) if all(Detector.finite(s.get(key)) for s in self.samples) else None
        detector = Detector()
        fields = Baseline.__dataclass_fields__
        detector.baseline = Baseline(**{k:v for k,v in self.baseline.items() if k in fields})
        force, strain, vibration, tip = (avg(k) for k in ('force_n','strain_delta','accel_rms','tip_deflection_mm'))
        channels = set(coverage)
        scored = detector.evaluate(force, strain, vibration, tip_deflection_mm=tip,
                                   strain_valid='strain' in channels, vibration_valid='vibration' in channels,
                                   instantaneous=True)
        if scored['health_score'] is None:
            self.fail('Insufficient comparable structural measurements. Reset and retry.')
            return
        self.result = dict(scored, force_n=force, strain_delta=strain, accel_rms=vibration,
                           tip_deflection_mm=tip, samples=len(self.samples), timestamp=sample['timestamp'],
                           simulation=sample.get('simulation',False), target_force_n=self.target)
        self.phase = 'COMPLETE'
        self.message = 'Test complete. Release the wing. Result retained below.'

    def state(self):
        return dict(phase=self.phase, target_force_n=self.target, tolerance_n=DEMO_FORCE_TOLERANCE_N,
                    hold_seconds=DEMO_HOLD_SECONDS, settle_seconds=DEMO_SETTLE_SECONDS, samples=len(self.samples), message=self.message,
                    result=self.result)
