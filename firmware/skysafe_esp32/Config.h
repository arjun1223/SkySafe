#pragma once

// ========================= USER CONFIGURATION =========================
// Compile-time laptop-independent virtual sensors. No sensor libraries needed
// while true. Arduino ESP32 core is needed in either mode.
#ifndef SIMULATION_MODE
#define SIMULATION_MODE 0
#endif

#ifndef SKYSAFE_ULTRASONIC
#define SKYSAFE_ULTRASONIC 0
#endif

namespace Config {
// ---- GPIO ASSIGNMENTS: verified load wiring and newly connected MPU6050 ----
// -1 means UNASSIGNED, not a proposed pin. Avoid flash/USB/boot-strapping pins
// and verify input/output capabilities against your particular board pinout.
constexpr int LOAD_DOUT = 32;  // HX711 DT -> ESP32 D32
constexpr int LOAD_SCK = 33;   // HX711 SCK -> ESP32 D33
constexpr int STRAIN_DOUT = 25; // Second HX711 DT -> ESP32 D25; enable after bridge wiring.
constexpr int STRAIN_SCK = 26;  // Second HX711 SCK -> ESP32 D26.
constexpr bool LOAD_ENABLED = true;
#if SIMULATION_MODE
constexpr bool STRAIN_ENABLED = true;
constexpr bool MPU_ENABLED = true;
#else
// Second HX711 quarter bridge: DT -> D25, SCK -> D26.
constexpr bool STRAIN_ENABLED = true;
constexpr bool MPU_ENABLED = true;
#endif
constexpr bool ULTRASONIC_ENABLED = SKYSAFE_ULTRASONIC;  // Set macro above to 1 to enable.
constexpr int ULTRASONIC_TRIG = -1;
constexpr int ULTRASONIC_ECHO = -1;  // Standard HC-SR04 ECHO needs 5V -> 3.3V level conversion.
constexpr int I2C_SDA = 21; // MPU6050 SDA -> ESP32 D21
constexpr int I2C_SCL = 22; // MPU6050 SCL -> ESP32 D22; AD0 -> common GND.
constexpr int GREEN_LED = -1;
constexpr int YELLOW_LED = -1;
constexpr int RED_LED = -1;
constexpr int BUZZER = -1;  // Optional ACTIVE buzzer; use a driver if needed.
constexpr bool LED_ACTIVE_HIGH = true;
constexpr bool BUZZER_ENABLED = false;
constexpr unsigned char MPU_ADDRESS = 0x68;
constexpr unsigned long IMU_I2C_HZ = 400000;
constexpr bool IMU_ALLOW_COMPAT_ID_70 = true; // This MPU6050-labeled module reports WHO_AM_I 0x70.
constexpr unsigned char IMU_COMPAT_SAMPLE_DIVIDER = 9; // 1 kHz / (9 + 1) = 100 Hz.
constexpr unsigned char IMU_COMPAT_FILTER = 4; // Documented 20 Hz accel low-pass filter.
constexpr unsigned char IMU_ACCEL_RANGE_REGISTER = 0x08; // +/-4 g; keep scale below synchronized.
constexpr double IMU_COUNTS_PER_G = 8192.0;
constexpr double STANDARD_GRAVITY = 9.80665;

// ---- ACQUISITION / CALIBRATION ----
constexpr unsigned long SERIAL_BAUD = 115200; // Verified on this ESP32/CP2102 and Mac.
constexpr unsigned long ACCEL_PERIOD_MS = 10;      // 100 Hz
constexpr unsigned long TELEMETRY_PERIOD_MS = 200; // 5 Hz; fits full JSON at 115200 baud.
constexpr unsigned long HX_STALE_MS = 500;        // supports HX711 at 10 SPS
constexpr unsigned long CAPTURE_TIMEOUT_MS = 5000;
constexpr int ZERO_CALIBRATION_SAMPLES = 20;
constexpr int VIBRATION_WINDOW = 100;
constexpr double GRAVITY_FILTER_ALPHA = 0.02;
constexpr double MAX_KNOWN_FORCE_N = 49.0;

// ---- OPTIONAL TIP DISTANCE ----
constexpr unsigned long ULTRASONIC_PERIOD_MS = 70;
constexpr unsigned long ULTRASONIC_TIMEOUT_US = 7000;
constexpr unsigned long ULTRASONIC_STALE_MS = 400;
constexpr double ULTRASONIC_MIN_MM = 20;
constexpr double ULTRASONIC_MAX_MM = 1000;
constexpr double SOUND_MM_PER_US = 0.343;
constexpr double DISTANCE_FILTER_ALPHA = 0.35;
constexpr int DISTANCE_MEDIAN_SAMPLES = 5;
constexpr double SIM_HEALTHY_COMPLIANCE = 0.8;
constexpr double SIM_ALTERED_COMPLIANCE = 1.4;
constexpr double DEFLECTION_FLOOR_MM = 3.0;
constexpr double DEFLECTION_RELATIVE_TOLERANCE = 0.15;

// ---- EXPERIMENTAL THRESHOLDS: mirror dashboard/config.py when changing ----
constexpr int MIN_BASELINE_SAMPLES = 60;
constexpr int MAX_BASELINE_SAMPLES = 600;
constexpr double MIN_FORCE_SPAN_N = 4.0;
constexpr double MIN_R_SQUARED = 0.90;
constexpr double STRAIN_FLOOR_COUNTS = 50.0;
constexpr double STRAIN_RELATIVE_TOLERANCE = 0.10;
constexpr double NOISE_MULTIPLIER = 3.0;
constexpr double VIBRATION_FLOOR = 0.10;  // m/s²
constexpr double STRAIN_WEIGHT = 0.80;
constexpr double WARNING_SCORE = 25.0;
constexpr double ANOMALY_SCORE = 55.0;
constexpr double SCORE_SMOOTHING_ALPHA = 0.25;
constexpr double RANGE_MARGIN_N = 0.5;
}
