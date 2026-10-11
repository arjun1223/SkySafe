import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
COLUMNS = ["timestamp", "time_ms", "source", "simulation_mode", "force", "strain", "strain_delta",
           "acceleration", "vibration_metric", "vibration_peak", "expected_strain", "strain_deviation",
           "health_score", "status", "sensors_ok", "force_calibrated", "tip_deflection_mm",
           "expected_deflection_mm", "deflection_deviation_pct", "strain_deviation_pct",
           "stiffness_n_per_mm", "baseline_stiffness_n_per_mm", "coverage", "sensor_status",
           "demo_test_state", "demo_target_force_n", "load_raw"]


class RunLogger:
    def __init__(self, directory=DATA_DIR):
        self.directory = Path(directory)
        self.handle = None
        self.filename = None
        self.rows = 0

    def start(self, name, metadata):
        if self.handle:
            raise ValueError("Stop the current recording first.")
        name = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(name)).strip("-")[:48] or "wing-test"
        now = datetime.now(timezone.utc)
        self.filename = f"{now:%Y%m%dT%H%M%SZ}_{name}_{uuid4().hex[:8]}.csv"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.handle = (self.directory / self.filename).open("x", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.handle, fieldnames=COLUMNS)
        self.writer.writeheader()
        self.handle.flush()
        self.rows = 0
        self.metadata = {**metadata, "started_at": now.isoformat(), "name": name, "filename": self.filename}
        self._save_metadata()

    def _save_metadata(self):
        (self.directory / self.filename).with_suffix(".json").write_text(
            json.dumps(self.metadata, indent=2, allow_nan=False), encoding="utf-8")

    def write(self, sample):
        if not self.handle:
            return
        row = {key: sample.get(key) for key in COLUMNS}
        row.update(force=sample["force_n"], strain=sample["strain_raw"], vibration_metric=sample["accel_rms"])
        for key in ("coverage", "sensor_status"):
            row[key] = json.dumps(sample.get(key), allow_nan=False)
        self.writer.writerow(row)
        self.handle.flush()
        self.rows += 1

    def stop(self, metadata=None):
        if self.handle:
            self.handle.close()
            self.handle = None
            self.metadata.update(stopped_at=datetime.now(timezone.utc).isoformat(), rows=self.rows)
            if metadata:
                self.metadata.update(metadata)
            self._save_metadata()
        return self.filename

    def state(self):
        return dict(active=self.handle is not None, filename=self.filename, rows=self.rows)

    def files(self):
        return [dict(name=p.name, bytes=p.stat().st_size) for p in sorted(self.directory.glob("*.csv"), reverse=True)]
