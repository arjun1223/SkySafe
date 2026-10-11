"""Bounded, nonblocking newline-JSON serial transport; never fits a baseline."""
import json
import math
import serial
from serial.tools import list_ports
from .config import SERIAL_BAUD

STATUSES = {"NORMAL", "WARNING", "STRUCTURAL ANOMALY", "CALIBRATING", "NEEDS_BASELINE",
            "NEEDS_CALIBRATION", "SENSOR_FAULT", "OUT_OF_RANGE", "ZEROING"}
NUMERIC_FIELDS = ("time_ms", "force_n", "strain_raw", "strain_delta", "acceleration",
                  "accel_rms", "vibration_peak")
OPTIONAL_NUMERIC = ("health_score", "expected_strain", "strain_deviation", "anomaly_score",
                    "strain_ratio", "vibration_ratio", "load_raw", "accel_x", "accel_y", "accel_z", "tip_deflection_mm", "distance_mm", "expected_deflection_mm",
                    "deflection_deviation_pct", "strain_deviation_pct", "stiffness_n_per_mm",
                    "baseline_stiffness_n_per_mm", "deflection_ratio")


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def parse_message(line):
    msg = json.loads(line)
    if not isinstance(msg, dict):
        raise ValueError("Expected a JSON object.")
    if msg.get("type") == "ack":
        if not isinstance(msg.get("command"), str) or not isinstance(msg.get("ok"), bool):
            raise ValueError("Malformed command acknowledgement.")
        return msg
    if msg.get("type") != "sample":
        raise ValueError("Unknown serial message type.")
    states = msg.get('sensor_status')
    if states is not None and (not isinstance(states,dict) or any(states.get(k) not in {'ok','disabled','fault','settling','needs_zero'} for k in ('load','strain','vibration','ultrasonic'))):
        raise ValueError('Invalid sensor connection indicators.')
    owners = {'force_n':'load','strain_raw':'strain','strain_delta':'strain','acceleration':'vibration','accel_rms':'vibration','vibration_peak':'vibration'}
    def allowed_null(field):
        return msg.get(field) is None and states is not None and field in owners and states[owners[field]] != 'ok'
    if any(not finite_number(msg.get(field)) and not allowed_null(field) for field in NUMERIC_FIELDS):
        raise ValueError("Missing or nonfinite sensor value.")
    if any(msg.get(f) is not None and not finite_number(msg[f]) for f in OPTIONAL_NUMERIC):
        raise ValueError("Invalid derived measurement.")
    if msg.get("status") not in STATUSES or not isinstance(msg.get("sensors_ok"), bool):
        raise ValueError("Invalid status.")
    if any(not isinstance(msg.get(f), bool) for f in ("force_calibrated", "zeroed", "simulation")):
        raise ValueError("Calibration and simulation flags must be booleans.")
    if msg.get("health_score") is not None and not 0 <= msg["health_score"] <= 100:
        raise ValueError("Invalid health score.")
    state = msg.get("baseline_state")
    if not isinstance(state, dict) or not isinstance(state.get("collecting"), bool):
        raise ValueError("Missing firmware baseline state.")
    if not finite_number(state.get("samples")) or not 0 <= state["samples"] <= 600:
        raise ValueError("Invalid baseline sample count.")
    baseline = state.get("baseline")
    if baseline is not None:
        keys = ("k", "b", "residual_std", "vibration_mean", "vibration_std", "force_min", "force_max", "r_squared", "samples")
        if not isinstance(baseline, dict) or any(not finite_number(baseline.get(k)) for k in keys):
            raise ValueError("Invalid firmware baseline model.")
        if baseline["force_min"] >= baseline["force_max"] or not 0 <= baseline["r_squared"] <= 1.00001:
            raise ValueError("Invalid baseline load range or fit.")
        if any(baseline[k] < 0 for k in ("residual_std", "vibration_std", "vibration_mean")):
            raise ValueError("Baseline noise metrics cannot be negative.")
        for name in ('deflection','vibration_fit'):
            fit = baseline.get(name)
            if fit is not None:
                keys = ('k','b','residual_std','r_squared','samples','force_min','force_max')
                if not isinstance(fit,dict) or any(not finite_number(fit.get(k)) for k in keys) or fit['force_min'] >= fit['force_max'] or fit['residual_std'] < 0 or not 0 <= fit['r_squared'] <= 1.00001:
                    raise ValueError('Invalid optional baseline fit.')
                if name == 'deflection' and fit['k'] <= 0:
                    raise ValueError('Invalid deflection compliance.')
        for flag in ('strain_available','vibration_available'):
            if flag in baseline and not isinstance(baseline[flag],bool):
                raise ValueError('Invalid baseline sensor flag.')
    if states and states['ultrasonic'] != 'ok':
        msg['tip_deflection_mm'] = None
    if states:
        for field,owner in owners.items():
            if states[owner] != 'ok':
                msg[field] = None
    rated = msg["status"] in {"NORMAL", "WARNING", "STRUCTURAL ANOMALY"}
    if rated and (not msg["sensors_ok"] or not msg.get("force_calibrated") or not msg.get("zeroed") or baseline is None or msg.get("health_score") is None):
        raise ValueError("Rated telemetry is missing a valid sensor/calibration/baseline.")
    if rated and states and (states['load'] != 'ok' or not ((states['strain']=='ok' and baseline.get('strain_available',True)) or (states['ultrasonic']=='ok' and finite_number(msg.get('tip_deflection_mm')) and baseline.get('deflection')))):
        raise ValueError('Rated telemetry needs force and a comparable structural sensor.')
    coverage = msg.get('coverage')
    if coverage is None:
        coverage = [name for name,key in (('strain','strain_delta'),('vibration','accel_rms'),('deflection','tip_deflection_mm')) if finite_number(msg.get(key)) and (not states or states['ultrasonic' if name=='deflection' else name]=='ok')]
        msg['coverage'] = coverage
    if not isinstance(coverage,list) or len(coverage)>3 or len(set(str(v) for v in coverage)) != len(coverage) or any(v not in ('strain','vibration','deflection') for v in coverage):
        raise ValueError('Invalid measurement coverage.')
    if rated and not any(name in coverage for name in ('strain','deflection')):
        raise ValueError('Rated telemetry needs structural coverage.')
    for name,key in (('strain','strain_delta'),('vibration','accel_rms'),('deflection','tip_deflection_mm')):
        if name in coverage and not finite_number(msg.get(key)):
            raise ValueError('Measurement coverage contradicts sensor data.')
    if not rated:
        msg["health_score"] = None
    return msg


class SerialReader:
    def __init__(self, port):
        self.port = serial.Serial(port, SERIAL_BAUD, timeout=0, write_timeout=1)
        self.buffer = bytearray()
        self.discard_line = False
        self.errors = 0

    @staticmethod
    def ports():
        return [dict(device=p.device, description=p.description) for p in list_ports.comports()]

    @staticmethod
    def identity(port):
        for p in list_ports.comports():
            if p.device == port and p.serial_number:
                return dict(serial_number=p.serial_number, vid=p.vid, pid=p.pid)
        return None

    @staticmethod
    def resolve_port(port, identity):
        if identity:
            matches=[p.device for p in list_ports.comports() if p.serial_number==identity['serial_number'] and p.vid==identity['vid'] and p.pid==identity['pid']]
            if len(matches)==1:
                return matches[0]
        return port

    def send(self, command):
        self.port.write((command + "\n").encode("ascii"))

    def read(self):
        chunk = self.port.read(min(self.port.in_waiting, 16384))
        messages = []
        for byte in chunk:
            if byte == 10:
                if not self.discard_line and self.buffer:
                    try:
                        messages.append(parse_message(self.buffer.decode("utf-8")))
                    except (ValueError, UnicodeError, OverflowError):
                        self.errors += 1
                self.buffer.clear()
                self.discard_line = False
            elif not self.discard_line:
                self.buffer.append(byte)
                if len(self.buffer) > 4096:
                    self.buffer.clear()
                    self.discard_line = True
                    self.errors += 1
        return messages

    def close(self):
        self.port.close()
