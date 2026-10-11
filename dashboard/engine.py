"""One source owner and sample pipeline. Firmware owns scoring in serial mode."""
import threading
import time
from collections import deque
from dataclasses import asdict
from datetime import datetime, timezone
from .anomaly_detection import Detector
from .demo_test import DemoTest
from .config import SAMPLE_HZ, TELEMETRY_HZ, HISTORY_SIZE, STALE_SECONDS, THRESHOLDS, RECONNECT_SECONDS, FORCE_ALARM_N, VIBRATION_ALARM_M_S2
from .data_logging import RunLogger
from .serial_reader import SerialReader
from .simulator import Simulator


class Engine:
    def __init__(self, data_dir=None):
        self.lock = threading.RLock()
        self.simulator = Simulator()
        self.detector = Detector()
        self.logger = RunLogger(data_dir) if data_dir is not None else RunLogger()
        self.source = "demo"
        self.reader = None
        self.serial_port = None
        self.serial_identity = None
        self.reconnect_at = 0
        self.device_time = None
        self.demo_test = DemoTest()
        self.latest = None
        self.history = deque(maxlen=HISTORY_SIZE)
        self.sequence = 0
        self.last_received = 0
        self.connection_error = None
        self.last_command = None
        self.pending = None
        self.auto_baseline_end = None
        self.serial_state = dict(collecting=False, samples=0, capacity=600, baseline=None)
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self._loop, daemon=True, name="skysafe-sensors")
            self.thread.start()

    def close(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=3)
        with self.lock:
            if self.reader:
                self.reader.close()
            self.logger.stop()

    def _drop_reader(self):
        if self.reader:
            try:
                self.reader.close()
            except Exception:
                pass
        self.reader = None
        self.last_received = 0
        self.reconnect_at = time.monotonic()+RECONNECT_SECONDS

    def _loop(self):
        tick = 0
        deadline = time.monotonic()
        while not self.stop_event.is_set():
            try:
                with self.lock:
                    if self.source == "demo":
                        sample = self.simulator.sample()
                        tick += 1
                        if tick % (SAMPLE_HZ // TELEMETRY_HZ) == 0:
                            sample.update(self.detector.evaluate(sample["force_n"], sample["strain_delta"],
                                                                sample["accel_rms"], valid=sample["sensors_ok"],
                                                                tip_deflection_mm=sample.get("tip_deflection_mm")))
                            self._ingest(sample)
                        if self.auto_baseline_end and self.simulator.time >= self.auto_baseline_end:
                            self.auto_baseline_end = None
                            try:
                                self.detector.stop()
                                self.last_command = dict(ok=True, message="Healthy baseline ready. Switch to reduced stiffness to compare.")
                            except ValueError as exc:
                                self.last_command = dict(ok=False, message=str(exc))
                    elif self.reader is None and self.serial_port and time.monotonic() >= self.reconnect_at:
                        self.reconnect_at = time.monotonic()+RECONNECT_SECONDS
                        candidate = SerialReader.resolve_port(self.serial_port,self.serial_identity)
                        if isinstance(candidate,str):
                            self.serial_port = candidate
                        self.reader = SerialReader(self.serial_port)
                    elif self.reader:
                        for message in self.reader.read():
                            if message.get("type") == "ack":
                                if message["command"] == "BOOT":
                                    self.demo_test.fail("ESP32 restarted. Re-zero, calibrate and collect a healthy baseline.")
                                    self.history.clear()
                                    self.latest = None
                                    self.last_received = 0
                                    self.serial_state = dict(collecting=False, samples=0, capacity=600, baseline=None)
                                    self.device_time = None
                                    if self.pending:
                                        self.last_command = dict(ok=False,message='ESP32 restarted before acknowledging the command. Retry after live telemetry returns.')
                                        self.pending = None
                                if self.pending and message["command"] == self.pending["command"]:
                                    self.last_command = message
                                    self.pending = None
                            else:
                                if self.device_time is not None and message['time_ms'] == self.device_time:
                                    self.demo_test.fail('Repeated device timestamp. Reset and retry with live samples.')
                                    continue
                                if self.device_time is not None and message['time_ms'] < self.device_time:
                                    self.demo_test.fail("Device restarted. Reset and retry after calibration.")
                                    self.history.clear()
                                self.device_time = message['time_ms']
                                self.serial_state = message["baseline_state"]
                                self._ingest(message)
                        if self.pending and time.monotonic() > self.pending["deadline"]:
                            self.last_command = dict(ok=False, message="ESP32 command timed out; check serial cable and firmware.")
                            self.pending = None
            except Exception as exc:
                with self.lock:
                    self.connection_error = str(exc)
                    self.demo_test.fail("Connection lost. Reset and retry after reconnection.")
                    self.reconnect_at = time.monotonic()+RECONNECT_SECONDS
                    if self.source == "serial" and self.reader:
                        self._drop_reader()
                    if self.pending:
                        self.last_command = dict(ok=False, message="Serial connection failed before command acknowledgement.")
                        self.pending = None
            with self.lock:
                if self.source == 'serial' and self.last_received and time.monotonic()-self.last_received > STALE_SECONDS:
                    self.demo_test.fail('Telemetry lost. Reset and retry after reconnection.')
                    if self.reader:
                        self._drop_reader()
                        self.reconnect_at = time.monotonic()+RECONNECT_SECONDS
            deadline += 1 / SAMPLE_HZ
            now = time.monotonic()
            if deadline < now - .1:
                deadline = now
            self.stop_event.wait(max(0, deadline - now))

    def _ingest(self, sample):
        self.sequence += 1
        sample = dict(sample, seq=self.sequence, source=self.source, timestamp=datetime.now(timezone.utc).isoformat())
        if self.demo_test.phase in ('LOADING','HOLDING') and self.baseline_state()['baseline'] != self.demo_test.baseline:
            self.demo_test.fail('Healthy baseline changed during the test. Reset and retry.')
        self.demo_test.add(sample, time.monotonic())
        sample['demo_test_state'] = self.demo_test.phase
        sample['demo_target_force_n'] = self.demo_test.target
        self.latest = sample
        self.history.append(sample)
        self.last_received = time.monotonic()
        self.connection_error = None
        self.logger.write(sample)

    def switch_source(self, source, port=None):
        with self.lock:
            if self.logger.handle:
                raise ValueError("Stop recording before changing the data source.")
            if source not in ("demo", "serial"):
                raise ValueError("Source must be demo or serial.")
            if source == "serial" and not port:
                raise ValueError("Choose the ESP32 serial port.")
            new_reader = SerialReader(port) if source == "serial" else None
            if self.reader:
                self.reader.close()
            self.reader = new_reader
            self.source = source
            self.serial_port = port if source == 'serial' else None
            identity = SerialReader.identity(port) if source == 'serial' else None
            self.serial_identity = identity if isinstance(identity,dict) else None
            self.device_time = None
            self.demo_test.reset()
            self.latest = None
            self.history.clear()
            self.last_received = 0
            self.pending = None
            self.last_command = None
            self.connection_error = None
            self.serial_state = dict(collecting=False, samples=0, capacity=600, baseline=None)
            self.detector.reset()
            self.auto_baseline_end = None
            self.simulator = Simulator()

    def command(self, command, force=None):
        with self.lock:
            allowed = {"ZERO", "CALIBRATE", "BASELINE_START", "BASELINE_STOP", "RESET_BASELINE", "SIM_NORMAL", "SIM_ANOMALY", "DEMO_ZERO"}
            if command not in allowed:
                raise ValueError("Unknown command.")
            if force is not None:
                try:
                    force = float(force)
                except (ValueError, TypeError):
                    raise ValueError("Known force must be a number.")
                if not 0 < force <= 49:
                    raise ValueError("Known force must be positive and no more than 49 N (5 kg cell).")
            if command == "CALIBRATE" and force is None:
                raise ValueError("CALIBRATE needs a known force in newtons, e.g. CALIBRATE 9.80665.")
            if command in ('ZERO', 'DEMO_ZERO', 'CALIBRATE', 'BASELINE_START', 'RESET_BASELINE'):
                self.demo_test.reset()
            if self.source == "serial":
                if command == "DEMO_ZERO" and self.serial_state["collecting"]:
                    raise ValueError("Finish the baseline before demo zero.")
                if not self.reader or not self.last_received or time.monotonic() - self.last_received > STALE_SECONDS:
                    raise ValueError("Wait for live ESP32 telemetry before sending commands.")
                if self.pending:
                    raise ValueError("Wait for the ESP32 to acknowledge the pending command.")
                self.reader.send(command + (f" {force:.6f}" if command == "CALIBRATE" else ""))
                self.pending = dict(command=command, deadline=time.monotonic() + 12)
                self.last_command = dict(ok=True, message=f"{command} sent; waiting for ESP32 acknowledgement.")
                return self.last_command
            if command == 'DEMO_ZERO':
                if self.detector.collecting:
                    raise ValueError('Finish the healthy baseline before a demo zero.')
                self.simulator.zero()
                self.detector.rebase()
            elif command == "ZERO":
                self.simulator.zero()
                self.detector.reset()
                self.auto_baseline_end = None
            elif command == "CALIBRATE":
                raise ValueError("Demo force is already calibrated. CALIBRATE is for the physical load cell.")
            elif command == "BASELINE_START":
                if self.simulator.mode != "NORMAL":
                    raise ValueError("Select Healthy wing before establishing its baseline.")
                if not self.simulator.window.ready:
                    raise ValueError("Wait one second for the vibration window to settle.")
                self.detector.start()
                self.auto_baseline_end = None
            elif command == "BASELINE_STOP":
                self.detector.stop()
                self.auto_baseline_end = None
            elif command == "RESET_BASELINE":
                self.detector.reset()
                self.auto_baseline_end = None
            else:
                self.simulator.mode = command.removeprefix("SIM_")
            self.last_command = dict(ok=True, message=f"{command} completed.")
            return self.last_command

    def demo_control(self, mode=None, auto_force=None, force=None, prepare=False, ultrasonic=None):
        with self.lock:
            if self.source != "demo":
                raise ValueError("Laptop demo controls require Demo mode.")
            if ultrasonic is not None:
                if not isinstance(ultrasonic, bool):
                    raise ValueError('Ultrasonic simulation must be true or false.')
                if self.detector.collecting or self.demo_test.phase in ('LOADING','HOLDING'):
                    raise ValueError('Finish or reset the active capture before changing sensor configuration.')
                self.simulator.ultrasonic_enabled = ultrasonic
            if mode is not None and mode not in ("NORMAL", "ANOMALY"):
                raise ValueError("Mode must be NORMAL or ANOMALY.")
            if mode == "ANOMALY" and self.detector.collecting:
                raise ValueError("Finish or reset the healthy baseline before switching to reduced stiffness.")
            if force is not None:
                try:
                    force = float(force)
                except (TypeError, ValueError):
                    raise ValueError("Force must be a number.")
                if not 0 <= force <= 16:
                    raise ValueError("Demo force must be between 0 and 16 N.")
            if auto_force is not None and not isinstance(auto_force, bool):
                raise ValueError("Automatic sweep must be true or false.")
            if mode is not None:
                self.simulator.mode = mode
            if auto_force is not None:
                self.simulator.auto_force = auto_force
            if force is not None:
                self.simulator.manual_force = force
            if prepare:
                self.demo_test.reset()
                if not self.simulator.window.ready:
                    raise ValueError("Wait one second for the vibration window to settle.")
                self.simulator.mode = "NORMAL"
                self.simulator.auto_force = False
                self.simulator.manual_force = 0
                self.simulator.zero()
                self.simulator.auto_force = True
                self.detector.start()
                self.auto_baseline_end = self.simulator.time + 17
            return dict(ok=True, message="Healthy 17-second sweep started." if prepare else "Demo conditions updated.")

    def test_control(self, action, target=None):
        with self.lock:
            if action == 'reset':
                self.demo_test.reset()
            elif action == 'zero':
                return self.command('DEMO_ZERO')
            elif action == 'start':
                if self.baseline_state()['collecting']:
                    raise ValueError('Finish the healthy baseline first.')
                if not self.latest or not self.latest.get('zeroed') or not self.latest.get('force_calibrated'):
                    raise ValueError('ZERO and calibrate force before starting a demo test.')
                if self.latest.get('status') not in ('NORMAL','WARNING','STRUCTURAL ANOMALY','OUT_OF_RANGE'):
                    raise ValueError('Wait for sensors to settle and a comparable structural response.')
                target = self.demo_test.target if target is None else target
                self.demo_test.start(self.baseline_state()['baseline'], target,
                                     bool(self.last_received and time.monotonic()-self.last_received <= STALE_SECONDS), self.pending)
            else:
                raise ValueError('Unknown demo test action.')
            return dict(ok=True, message=self.demo_test.message)

    def start_run(self, name):
        with self.lock:
            self.logger.start(name, dict(source=self.source, thresholds=asdict(THRESHOLDS), baseline_at_start=self.baseline_state(), demo_test=self.demo_test.state(), serial_port=self.serial_port))
            return self.logger.state()

    def stop_run(self):
        with self.lock:
            self.logger.stop(dict(baseline_at_stop=self.baseline_state(), demo_test=self.demo_test.state()))
            return self.logger.state()

    def baseline_state(self):
        return self.detector.state() if self.source == "demo" else self.serial_state

    def snapshot(self, after=0):
        with self.lock:
            age = time.monotonic() - self.last_received if self.last_received else None
            stale = age is None or age > STALE_SECONDS
            latest = dict(self.latest) if self.latest else None
            if stale and latest:
                latest.update(status="SENSOR_FAULT", health_score=None)
            if stale:
                self.demo_test.fail("No live telemetry. Reset and retry after reconnection.")
            return dict(demo_test=self.demo_test.state(), source=self.source, latest=latest, history=[s for s in self.history if s["seq"] > after],
                        alarm_limits=dict(force_n=FORCE_ALARM_N, vibration_m_s2=VIBRATION_ALARM_M_S2),
                        baseline_state=self.baseline_state(), thresholds=asdict(THRESHOLDS),
                        connection=dict(connected=not stale, age_seconds=age, error=self.connection_error,
                                        invalid_lines=self.reader.errors if self.reader else 0),
                        demo=dict(mode=self.simulator.mode, auto_force=self.simulator.auto_force,
                                  force=self.simulator.manual_force, ultrasonic=self.simulator.ultrasonic_enabled, preparing=self.auto_baseline_end is not None),
                        pending=self.pending["command"] if self.pending else None, last_command=self.last_command,
                        recording=self.logger.state())
