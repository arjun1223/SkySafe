"""Exercise the real IMU adapter against a controllable I2C transport."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ImuTests(unittest.TestCase):
    def test_acceleration_units_and_sensor_failure(self):
        compiler = shutil.which('c++')
        if not compiler:
            self.skipTest('Native C++ compiler unavailable')
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / 'imu'
            subprocess.run([compiler, '-std=c++11', '-Wall', '-Wextra',
                            '-I', str(ROOT / 'tests/imu_stub'),
                            '-I', str(ROOT / 'tests/arduino_stub'),
                            str(ROOT / 'tests/imu_runner.cpp'), '-o', str(binary)],
                           check=True, capture_output=True, text=True)
            subprocess.run([str(binary)], check=True, timeout=10)
