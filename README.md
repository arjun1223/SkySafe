# SkySafe

**Current print design:** [14.03-inch modular wing in Fusion](cad/fusion_14inch/README.md), with three sections, diamond spar holes and four seam plates. Use those wing files for the larger version.

**Current holder:** [single-print laptop-foot stand](cad/fusion_laptop_stand/README.md). [Complete wiring and sensor placement](docs/HARDWARE_WIRING.md). Native Fusion F3D, STEP, STL, rebuild scripts, and assembly renders are included. Older CAD variants are retained for reference.

A benchtop aircraft-wing structural response monitor for a hackathon. An ESP32 reads applied force, foil-gauge bridge output, and acceleration. A local Python dashboard compares the measured response with a known-healthy force/strain baseline.

**Experimental prototype. Not a flight system or a certified damage-detection algorithm.** The score describes agreement with a baseline; it does not certify structural integrity. No AI/ML is used.

## Developer mode: test the load cell yourself

Refresh the dashboard and enable **Developer mode** underneath the page title. It is off on every page load; hiding it restores the normal judging view. Select **ESP32 · USB serial** and connect the physical board. No force calibration or structural baseline is needed to view the raw ADC reading and graph.

The panel also shows **Raw strain bridge** and its own graph before ZERO, so the second HX711 can be checked independently of force calibration. Fresh values inside the ADC range establish communication only; the bonded gauge must still show a repeatable response to wing bending.

Click **Start 12-second response check** with the hanger unloaded. Follow the on-screen prompts: leave it unloaded for 3 seconds, gently press the free hanger for 6 seconds, then release for 3 seconds. Keep the root secured and the hanger clear of the wing, table, and platform. The panel reports sustained response and return toward the unloaded reference, or explains missing data, no response, and suspected output stuck at zero. It does not assign structural health or certify the mounting. Both raw-response directions are accepted. One isolated spike cannot pass the check. Thresholds are in `dashboard/static/load-cell-check.js`.

**Capture unloaded reference** only sets a local raw-count comparison; it does not send ZERO. For force calibration, keep the wing in its final supported position, remove the weight and use **Zero sensors**. Hang a known mass solely from the free hanger, enter the total mass including bag/string in grams, and choose **Calibrate known mass**. The result still comes from the ESP32 acknowledgement. Calibration controls are blocked when physical data is unavailable or raw output is suspected stuck at zero. CSV records now include `load_raw`, including before force calibration.

Verify the response-check decisions without hardware with `node tests/test_load_cell_check.cjs`. The hardware startup command also waits for an unplugged ESP32 to reconnect instead of exiting or falling back to simulation.

## Judge test and optional tip deflection

The new **DEMO TEST** panel performs a measured comparison at the same load. Its retained result is separate from the live metrics; releasing the wing does not erase the judged measurement. It uses transparent baseline comparison, with no AI/ML and no certified aircraft-analysis claim.

**Laptop rehearsal:** optionally enable **Simulate optional tip sensor**, run the healthy 17-second baseline sweep, click **Unload wing · 0 N**, then the DEMO TEST **ZERO**. Wait for sensors to settle, press **Start test**, and set the manual force slider to the target. Hold steady until the result appears. Repeat with **Reduced stiffness**, using the same target and original healthy baseline. Simulation remains clearly labeled.

**Physical judging:** first zero/calibrate force and establish a known-healthy sweep at the exact marked loading point you will use for judging. Then unload, press DEMO TEST **ZERO**, press **Start test**, and put a **PRESS HERE** tape label on the **load cell’s free hanger** and manually apply force there. Pushing another part of the wing can bypass the cell. Choose a target whose tolerance window lies inside the measured baseline envelope and your physically tested elastic range. **10 N is a configurable simulation default, not a load rating for the bamboo wing.**

The target window defaults to ±0.5 N. The test waits 0.7 seconds for filtering to settle, then averages approximately one second of contiguous data (at least eight samples). It resets the hold if force leaves the window, and interrupts on stale telemetry, a changed baseline, device restart, failed force measurement or changed sensor coverage. **Reset test** clears the held result while preserving setup and baseline. DEMO TEST **ZERO** translates the existing baseline offsets, retaining measured slopes; the original setup **Zero sensors** still clears the baseline. Unload before either zero.

### Optional HC-SR04

In `firmware/skysafe_esp32/Config.h`, set `SKYSAFE_ULTRASONIC` to `1` and assign `ULTRASONIC_TRIG` / `ULTRASONIC_ECHO`. It defaults to disabled. `LOAD_ENABLED`, `STRAIN_ENABLED`, and `MPU_ENABLED` independently control the other channels. The laptop-only simulation flag and all judging settings are in `dashboard/config.py`.

Place the sensor beneath a flat reflector on the wing tip, with the beam clear of hands, the desk and other ribs. Leave more than the sensor’s approximately 20 mm minimum range at maximum intended downward deflection. The normal HC-SR04 uses **5 V power**; use a common ground and **level-shift ECHO before the ESP32 input**. A resistor divider can use ECHO → 2.2 kΩ → ESP32 input node → 3.3 kΩ → ground (approximately 3.0 V at a 5 V echo). Do not directly connect a standard 5 V ECHO to an ESP32 GPIO. Check the exact module/board variant. [HC-SR04 datasheet](https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf), [ESP32 datasheet](https://documentation.espressif.com/esp32_datasheet_en.html).

The firmware triggers every 70 ms, captures echo edges without waiting for the echo pulse, rejects distances outside 20–1000 mm, and applies a five-reading median followed by an exponential filter (alpha 0.35). ZERO captures the unloaded distance; CALIBRATE does not replace that reference. `tip_deflection_mm = unloaded_distance_mm - current_distance_mm`. Disabled, stale or un-zeroed readings are `null`, never fabricated zero measurements. HC-SR04 is not a sub-millimeter instrument; the default comparison noise floor is 3 mm and must be tuned from your assembled rig.

Healthy force/deflection regression gives compliance `c` in mm/N; **experimental stiffness = 1/c**, in N/mm. Live/test secant stiffness uses force divided by deflection above the fitted intercept and is hidden near zero displacement. The force/deflection chart shows the healthy fit and observations; a separate timeline shows displacement. A poor or flat deflection fit is excluded. At least one reliable structural fit (strain or deflection) is required. Strain remains ADC counts, not calibrated microstrain.

Available strain and deflection departures each receive structural weight 0.8; available vibration departure receives weight 0.2. Weights are normalized across channels actually used. The original strain/vibration-only score is unchanged. Missing secondary channels are displayed as unavailable and the remaining channels are named beside the score. A score with limited coverage describes only those available measurements. The healthy baseline also stores force/strain, force/deflection and force/RMS regressions, plus noise and sample counts. Use consistent fixture and excitation.

### USB reliability and records

Upload the updated firmware and use **115200 baud** on both sides (centralized in both configuration files). This ESP32/CP2102 and Mac produced corrupted data at 230400 baud, even with short diagnostic frames; 115200 produced clean HX711 readings. Full dashboard telemetry now runs at **5 Hz**, with a 4096-byte UART transmit buffer so 100 Hz acquisition can continue while a frame is transmitted. The judge averages a two-second hold after settling, providing enough samples at this rate. Existing telemetry schemas remain accepted when optional fields are absent.

A failed or silent USB stream is unrated after two seconds. The dashboard retries every two seconds, preferring the same USB serial number/VID/PID if the port name changes. It never silently switches to simulation, replays commands, restores a physical baseline after reboot, or generates readings during serial silence. Recalibrate after a reboot. If no USB serial identity is available, it retries the selected port; choose the new port manually if its name changes.

CSV now includes `tip_deflection_mm`, expected displacement, signed strain/deflection deviations, experimental stiffness, sensor states, scoring coverage, target force and demo-test phase. Run metadata retains the baseline and the judged result at stop. Missing measurements remain empty cells. The entire laptop demonstration works offline, including local Plotly charts.

## Run it now — no hardware

Requires Python 3.10 or newer. From this directory:

On this Mac, double-click **Launch SkySafe.command** in Finder to start the dashboard. Keep its Terminal window open and visit **http://127.0.0.1:5050**. The launcher installs dependencies in a local virtual environment on first use; this workspace is already set up. Manual setup on any supported platform:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m dashboard.app
```

Open **http://127.0.0.1:5050**. The application starts in laptop **Demo mode**. Plotly is served locally from the installed Python package; no CDN, remote fonts or internet connection is needed after installation. `requirements-lock.txt` contains the dependency versions used for verification.

Windows PowerShell activation: `.venv\Scripts\Activate.ps1`. To change the web port: `python -m dashboard.app --port 5051`.

The dashboard has a white default theme and a black dark theme. The mechanical switches and primary button adapt Uiverse components; source files, credits, and license notices are included in `docs/uiverse/` and `THIRD_PARTY_NOTICES.md`. Theme preference is saved in your browser.

## A judging demo in about a minute

1. Keep **Demo mode** selected. Wait one second for the vibration window to settle.
2. Click **Run healthy baseline sweep**. This selects the healthy virtual wing, zeroes the simulated sensors unloaded, and collects a 17-second automatic load sweep. Health is unrated while collecting.
3. Once **Baseline ready** appears, observe the healthy line and current points overlapping on **Force vs. strain**, with a score typically around 96–99.
4. Name the run `healthy-wing`, click **Record CSV**, observe a load cycle, then **Stop & save**.
5. Click **Reduced stiffness**. The applied force waveform remains the same, while strain response and vibration change. Current points move above the healthy response. Health falls; higher loads typically show **STRUCTURAL ANOMALY**, while low loads can show **WARNING** because the strain difference is smaller.
6. Record a separate `reduced-stiffness-wing` run. Download both CSVs from the run list.
7. Switch back to **Healthy wing** to see recovery without changing the original baseline.

For a direct comparison at the same load, turn off **Automatic load sweep** and set the slider to **8 N** before switching wing conditions. To use **Zero sensors** manually in demo mode, click **Unload wing · 0 N** first. Zeroing invalidates the old baseline.

## Repository structure

```text
SkySafe/
├── firmware/skysafe_esp32/
│   ├── skysafe_esp32.ino       # Acquisition, serial commands, LEDs, buzzer
│   ├── Config.h                # All GPIOs, simulation flag, editable thresholds
│   └── ResponseModel.h         # Portable least-squares model and scoring
├── dashboard/
│   ├── app.py                  # Flask local API and page
│   ├── engine.py               # Source ownership, acquisition thread, run state
│   ├── serial_reader.py        # Nonblocking, bounded JSON serial transport
│   ├── simulator.py            # Virtual sensors, gravity removal, RMS/peak
│   ├── anomaly_detection.py    # Python counterpart of firmware scoring
│   ├── config.py               # Editable laptop demo thresholds
│   ├── data_logging.py         # Separate CSV and metadata per run
│   ├── templates/index.html
│   └── static/                 # Interface, theme, live Plotly plots
├── tests/                      # Behavior tests and accelerated demo verification
├── cad/                        # 140 mm printer, 4 mm bamboo spars, STLs and fixture
├── docs/                       # Verification notes, screenshots, Uiverse sources
├── data/                       # Generated CSVs and run metadata (git-ignored)
├── requirements.txt
├── requirements-lock.txt
└── README.md
```

The native **Fusion 360** CAD is in **[cad/fusion/README.md](cad/fusion/README.md)**, with assembly and individual F3D files, STEP and print STLs. The **[printing guide](cad/README.md)** covers: an editable open-rib wing with two removable 4 mm bamboo spars, root clamp, adjustable bar-cell adapter with grooved hot-glue end pads, free hanger and fit coupon. All seven printable parts fit a 140 × 140 × 140 mm build volume. The current Fusion wing uses short 4.5 mm bamboo guides, selected from the printed fit coupon, and a 1.8 mm continuous gauge strip with tapered shoulders for greater flexibility. Its resting sag and elastic load range still require a physical check. The sensor mount accepts differing screw patterns on rectangular bar cells through isolated glue pads; check the actual end regions and clearances before bonding. See the CAD guide for the prototype glue limitations.

## Hardware architecture

```text
Applied wing load → 5 kg load cell → HX711 #1 ──┐
Wing surface strain → quarter bridge → HX711 #2 ├→ ESP32 → USB serial → laptop dashboard
Wing motion → MPU6050 → I²C ────────────────────┘     └→ green/yellow/red LEDs + optional active buzzer
```

| Component | Role | Software units |
| --- | --- | --- |
| 5 kg load cell + HX711 #1 | Applied force | N after known-load calibration |
| BF350-3AA, 350 Ω + HX711 #2 | Change in local strain response | Raw ADC counts and zero-referenced counts |
| MPU6050 | Acceleration and dynamic response | m/s²; gravity-removed magnitude, RMS and peak |
| LEDs | Normal / warning / anomaly | GPIO outputs configured in one section |
| Active buzzer, optional | Pulsed alert for severe structural response change | Off unless enabled and assigned |

The gauge must be bonded to a suitable wing surface near the high-bending region, with its sensitive axis aligned to the intended strain direction. The load cell must measure the force actually transmitted to the wing. Keep clamp, loading position, sensor mass and sensor attachment consistent between baseline and test.

### Quarter Wheatstone bridge

Three fixed arms are nominally **350 Ω**, each built from **330 Ω + 10 Ω + 10 Ω in series**. The fourth arm is the BF350-3AA foil gauge.

The second HX711 is assigned **DT → D25**, **SCK → D26**, **VCC → 3V3**, and **GND → common ground**. Its strain flag is now enabled for bridge bring-up. If the bridge is not installed, set `STRAIN_ENABLED = false` in the hardware section of `Config.h`. Its E+/E− power the bridge; A+/A− connect to the two bridge midpoints shown below.

```text
                 HX711 E+ (bridge excitation)
                         │
             ┌───────────┴───────────┐
             │                       │
        R1 = 350 Ω              R2 = 350 Ω
        fixed series arm         fixed series arm
             │                       │
           A+                       A−
             │                       │
        gauge = 350 Ω           R3 = 350 Ω
                                fixed series arm
             │                       │
             └───────────┬───────────┘
                         │
                 HX711 E− (excitation return)
```

This is one valid arm arrangement; swapping the differential sense wires changes sign. The baseline fit accepts either sign. Bridge matching, gauge attachment, lead resistance, temperature drift and HX711 saturation must be checked on the assembled circuit. Software ZERO removes a measured offset; it cannot correct an electrically saturated or incorrectly wired bridge. Verify module supply and ESP32 logic-level compatibility, and use a common reference ground.

Strain is deliberately **not reported as microstrain**. Converting ADC counts to microstrain requires validated bridge excitation, HX711 gain/transfer function, gauge factor and bridge response. Force calibration does not perform that conversion.

## Connect the ESP32 later

1. Open `firmware/skysafe_esp32/skysafe_esp32.ino` in Arduino IDE.
2. Install the **esp32 by Espressif Systems** board package and select your actual ESP32 board. [Official installation guide](https://docs.espressif.com/projects/arduino-esp32/en/latest/installing.html).
3. The current `Config.h` defaults to **real hardware** (`SIMULATION_MODE = 0`), with load HX711 DT connected to **D32**, SCK to **D33**, VCC to **3V3**, and GND to **GND**. The second, strain HX711 is enabled on **D25/D26**; disable `STRAIN_ENABLED` if its bridge is absent. The MPU6050 is enabled: SDA to **D21**, SCL to **D22**, VCC to **3V3**, and both GND and AD0 to common ground. For virtual ESP32 sensor tests, set `SIMULATION_MODE` to `1`; that mode enables the simulated MVP channels. Laptop-only simulation remains available independently.
4. For real sensors, install **HX711 Arduino Library by Bogdan Necula / Andreas Motl** (bogde, tested 0.7.5), **Adafruit MPU6050** (tested 2.2.9), **Adafruit Unified Sensor**, and **Adafruit BusIO**. Do not substitute the differently named Rob Tillaart HX711 library. [HX711 source](https://github.com/bogde/HX711), [MPU6050 source](https://github.com/adafruit/Adafruit_MPU6050).
5. Assign GPIOs for **each additional enabled sensor** in `Config.h`, then enable its flag in the hardware section. Other pins remain `-1`, meaning unassigned. Assign optional LED/buzzer pins there too. Use suitable LED resistors and a buzzer driver if required by your components. `MPU_ADDRESS` defaults to `0x68`; change it if AD0 selects `0x69`. With only the load cell wired, force can be zeroed/calibrated, but structural health remains unrated until a structural-response sensor is added.
6. Upload the sketch, close the Arduino Serial Monitor so it releases the port, and select **ESP32 · USB serial** in the dashboard. Choose the port and click **Connect**. Allow startup and reset time before sending commands.

You can also launch directly into serial mode:

```sh
python -m dashboard.app --serial /dev/cu.usbserial-YOUR_DEVICE
# Windows example:
python -m dashboard.app --serial COM5
```

Baud rate is **115200**. In USB mode the **ESP32 owns calibration, baseline and scoring**. The dashboard displays that telemetry and sends commands; it does not independently refit a competing baseline. This keeps the laptop status and hardware LEDs consistent. Switching sources clears chart history and requires stopping any active recording. There is no silent switch to fake data on a serial fault.

### Physical calibration procedure

1. Power on, check both HX711 streams and MPU6050. Hardware mode begins **NEEDS_CALIBRATION** with no health score.
2. With the wing fully unloaded and still, click **Zero sensors** / send `ZERO`. Firmware averages **20 fresh load-cell samples**, about two seconds at 10 SPS, and independently averages available strain/distance readings. Wait for the acknowledgement and another second for the vibration window to settle.
3. Apply a steady **known force** through the load path. Enter its value in **newtons** and click **Calibrate force** / send `CALIBRATE 9.80665` for a 1 kg gravitational load. The force scale is `(mean_loaded_counts − unloaded_offset) / known_force_n`. Signed factors are supported. Bare `CALIBRATE` returns instructions rather than assuming a weight.
4. Return to the known-healthy specimen. Click **Start baseline**, smoothly sweep the intended load envelope, and click **Stop baseline** after at least 60 valid samples (12 s at 5 Hz) and at least 4 N of force span. Cover the **full range you will test**; 4 N is a minimum fit requirement, not an instruction to test outside the baseline envelope.
5. Baseline stopping succeeds only with an adequate linear fit (default R² ≥ 0.90). A rejected stop keeps collection active so you can continue or reset it. Collection is bounded to 600 samples (60 s); if full, reset and start again.
6. Compare tests at matching load, fixture, excitation and sensor settings. Record healthy and reduced-stiffness specimens separately.

Setup ZERO and CALIBRATE invalidate the previous baseline. Calibration and baseline are kept **in RAM only**: after reboot, zero/calibrate and establish the baseline again. Run metadata records the baseline for offline comparison; it is not automatically restored into a new physical setup.

## Serial protocol

Send newline-terminated ASCII commands. The UI waits for the ESP32's acknowledgement rather than assuming success. Only one UI command is outstanding at a time; timeout is 12 s.

| Command | Behavior |
| --- | --- |
| `DEMO_ZERO` | Unloaded demo zero; translate offsets while retaining healthy response slopes |
| `ZERO` | Average unloaded offsets; reset baseline and gravity window |
| `CALIBRATE <known_force_n>` | Average a steady known load; update signed counts/N; reset baseline |
| `BASELINE_START` | Start a new healthy response sweep |
| `BASELINE_STOP` | Validate and store fit, or explain rejection |
| `RESET_BASELINE` | Clear fit; no health score until a new baseline |
| `SIM_NORMAL` / `SIM_ANOMALY` | Switch virtual wing condition at the same applied load |
| `SIM_FORCE <0..16>` | Firmware simulator: set manual applied force in N |
| `SIM_AUTO` | Firmware simulator: resume automatic sweep |

Firmware simulation setup example: `SIM_FORCE 0`, `ZERO` (wait for ACK), `SIM_NORMAL`, `SIM_AUTO`, `BASELINE_START`, wait a complete load cycle, `BASELINE_STOP`. Then `SIM_ANOMALY`. Simulation-only commands are rejected in real-sensor builds. A damaged virtual wing cannot be recorded as the healthy baseline.

Every transmitted line is JSON. Commands return:

```json
{"type":"ack","command":"BASELINE_STOP","ok":true,"message":"Healthy baseline ready."}
```

Telemetry contains the requested fields plus validity, baseline state and model parameters:

```json
{
  "type": "sample",
  "time_ms": 12345,
  "force_n": 8.2,
  "load_raw": 182000,
  "strain_raw": 50656,
  "strain_delta": 656,
  "acceleration": 0.13,
  "accel_rms": 0.126,
  "vibration_peak": 0.19,
  "expected_strain": 655.9,
  "strain_deviation": 0.1,
  "health_score": 98,
  "status": "NORMAL"
}
```

The example is shortened; actual firmware includes `sensors_ok`, `force_calibrated`, `zeroed`, `simulation`, `simulation_mode`, component ratios, and `baseline_state`. An unavailable score is JSON `null`, not a manufactured 100. Input lines are bounded to 4 KiB on the laptop, nonfinite/malformed telemetry is rejected, and freshness is checked separately from command ACKs. Serial boot noise is safely discarded. A stalled stream is unrated after two seconds.

## Measurements and anomaly equations

Accelerometer acquisition is nominally **100 Hz**. Firmware HX711 reads are nonblocking and independently refreshed; 10 SPS or 80 SPS modules are supported. Telemetry and score updates are **5 Hz**. The MPU6050 path uses ±4 g and 21 Hz low-pass filtering. This user's MPU6050-labeled board reports `WHO_AM_I = 0x70`; the explicit `IMU_ALLOW_COMPAT_ID_70` configuration permits its documented compatible register profile, with ±4 g and 20 Hz filtering. `imu_identity` reports the observed identity without authenticating the label. Range readback and every acceleration burst are checked; incomplete reads invalidate the sensor. Other unknown identities are rejected. I²C availability, ADC rail saturation and stale HX711 data are checked. A missing load cell or all comparable structural sensors prevents a NORMAL rating. Secondary sensors can drop out independently; the dashboard shows the remaining scoring coverage.

For each accelerometer axis, a slow gravity estimate is updated:

```text
g_axis ← g_axis + 0.02 × (a_axis − g_axis)
dynamic_magnitude = sqrt(Σ (a_axis − g_axis)²)
acceleration = current dynamic_magnitude
accel_rms = sqrt(mean(dynamic_magnitude²)) over the latest 100 samples
vibration_peak = max(dynamic_magnitude) over that same window
```

The one-second window must fill before scoring. These are time-domain motion metrics, not a modal-frequency identification algorithm. Movements and orientation changes can affect them.

Fit healthy samples using ordinary least squares:

```text
y = strain_delta (ADC counts), x = force_n
k = Σ((x − mean_x)(y − mean_y)) / Σ((x − mean_x)²)
b = mean_y − k × mean_x
expected_strain = k × current_force + b
strain_deviation = abs(measured_strain_delta − expected_strain)
residual_std = sqrt(Σ healthy residual² / (n − 2))
```

`k` is a response slope in **counts/N**, not a direct stiffness in N/m. A higher absolute slope can indicate a more flexible response under a consistent setup, but sensor gain and placement affect it.

Default normalized tolerances and score:

```text
strain_tolerance = max(50 counts, 3 × residual_std) + 0.10 × abs(expected_strain)
vibration_tolerance = max(0.10 m/s², 3 × healthy_vibration_std)
strain_ratio = strain_deviation / strain_tolerance
vibration_ratio = abs(current_rms − healthy_rms_mean) / vibration_tolerance
raw_anomaly = 50 × (0.80 × min(strain_ratio, 2) + 0.20 × min(vibration_ratio, 2))
smoothed_anomaly ← smoothed_anomaly + 0.25 × (raw_anomaly − smoothed_anomaly)
health_score = round(100 − smoothed_anomaly)
```

| Smoothed anomaly | Structural status | Output |
| --- | --- | --- |
| < 25 | NORMAL | Green LED |
| ≥ 25 and < 55 | WARNING | Yellow LED |
| ≥ 55 | STRUCTURAL ANOMALY | Red LED; optional pulsed buzzer |
| No valid setup/baseline or sensor fault | Unrated setup/fault status | No green; yellow blinks |
| Force outside baseline min/max ±0.5 N | OUT_OF_RANGE, unrated | Yellow blinks |

Additional statuses are `NEEDS_CALIBRATION`, `NEEDS_BASELINE`, `CALIBRATING`, `ZEROING`, and `SENSOR_FAULT`. These are deliberately distinct from NORMAL.

All laptop demo thresholds are in `dashboard/config.py`; firmware thresholds are mirrored in `firmware/skysafe_esp32/Config.h`. **Keep both sets synchronized when tuning.** A native C++/Python parity test verifies baseline/scoring agreement with the supplied settings. Scoring resets when a new baseline is created, and EMA smoothing introduces a short response delay.

## Simulation behavior

Both laptop and firmware simulators provide:

- A 1–13 N sinusoidal force sweep with a 16-second cycle, or manually held force.
- Healthy slope of approximately **80 counts/N**, low vibration and electrical/mechanical noise.
- Reduced-stiffness slope of approximately **124 counts/N**, larger vibration amplitude and a changed excitation frequency.
- The same force signal when switching specimen condition; damage does not increase the applied load.

The simulated excitation frequency is a demonstration parameter, not a prediction of a real wing's resonant frequency. Noise and metrics are plausible development inputs; the actual sensor scales and thresholds must be measured on your bench.

## Data logging

Click **Record CSV** to begin a named run, and **Stop & save** to finish. Every run gets a unique UTC timestamp + sanitized name + random suffix. Data is flushed on each row. A companion JSON file stores source, baseline, thresholds and run times. Runs remain separate and are available for download in the dashboard.

Requested columns are present, plus useful provenance:

```text
timestamp,time_ms,source,simulation_mode,force,strain,strain_delta,
acceleration,vibration_metric,vibration_peak,expected_strain,strain_deviation,
health_score,status,sensors_ok,force_calibrated,tip_deflection_mm,
expected_deflection_mm,deflection_deviation_pct,strain_deviation_pct,
stiffness_n_per_mm,baseline_stiffness_n_per_mm,coverage,sensor_status,
demo_test_state,demo_target_force_n
```

`strain` is raw bridge ADC output; `strain_delta` and `expected_strain` are both zero-referenced counts. `vibration_metric` is RMS in m/s². UTC `timestamp` is laptop receipt time; `time_ms` is device/simulator elapsed time. Unrated results are empty CSV cells. Real firmware sensor faults are logged with validity flags; host-only serial silence does not fabricate samples.

## Verify without physical hardware

```sh
python -m unittest discover -s tests -v
python -m tests.verify_demo
```

The suite covers baseline quality/rejection, zeroing, normal/warning/anomaly/recovery, load-envelope limits, invalid data, CSV separation, source changes, real pyserial over a virtual serial pair, live acquisition, API validation and native C++ model parity. A native C++ compiler enables the parity check; it is skipped if none is installed. The accelerated demo writes two explicitly simulated CSVs and `data/verification_report.json`.

See `docs/VERIFICATION.md` for the completed checks and tested toolchain. Actual wiring, sensor bonding, force calibration, USB uploads and physical loading still require the assembled hardware.

## Limits and practical troubleshooting

- This prototype detects changes in measured response. It cannot locate damage or distinguish every cause: clamp slip, load-position changes, temperature, gauge debonding and cable movement can all change measurements.
- Baseline fit quality and force coverage are required. Avoid extrapolation and keep specimens/fixtures and excitation comparable.
- A poorly matched quarter bridge can exceed the HX711 input range before zeroing. Check raw counts, bridge wiring and resistor matching on the bench.
- Vibration scoring uses pooled healthy RMS statistics; the force/RMS regression is also retained in baseline metadata. Repeat the same excitation procedure; a tap during one test and quiet loading during another is not a controlled comparison.
- No baseline or force scale survives an ESP32 reboot. Re-establish the physical setup before scoring again.
- If serial is unavailable, check the selected port, cable, device permissions and whether Arduino Serial Monitor has it open. Missing telemetry shows an unrated fault, not fallback simulated health.
- If the web port is occupied, use `--port 5051`. The server binds to loopback for this single-user local prototype. It is not configured for public hosting.
- OLED output is not implemented; LEDs and the laptop dashboard are supported. All optional buzzer behavior is disabled by default.
