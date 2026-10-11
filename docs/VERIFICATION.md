# Completed verification

## Second HX711 strain-bridge bring-up — October 11, 2026

Enabled the hardware strain bridge on DT/GPIO25 and SCK/GPIO26 in `Config.h`, preserving load GPIO32/33 and MPU I²C21/22. The actual ESP32 build passed at 331,248 bytes flash and 25,764 bytes global RAM. Upload at 115200 baud completed with flash hash verification. All 56 tests pass.

An initial real capture had 72 fresh strain frames from 4,267,759 to 4,293,131 ADC counts. A subsequent approximately 90.6-second capture contained 453 valid strain frames from 4,254,108 to 4,366,870 counts, below the firmware's ±8,388,000 saturation cutoff. Load and MPU channels also reported fresh data. The serial parser discarded one additional invalid line during the latter capture; the larger pre-existing startup discard count is retained in `strain_bridge_bringup.json`. The raw bridge output drifted, so a stable baseline or mechanical strain response has not been established. Calibration flags reset on firmware restart.

Developer mode now includes a raw strain count and separate graph before zeroing. The live browser displayed the physical strain value and LOAD/STRAIN/MPU `OK` indicators, reported no browser errors/warnings, and returned to its hidden state when switched off. Evidence: `strain-bridge-live.png` and `strain_bridge_bringup.json`. These readings establish ADC communication/range, not correct gauge bonding, microstrain calibration, force calibration, or structural health. Bond the gauge, secure its leads, and validate repeatable response before collecting a healthy baseline.

## Developer load-cell diagnostics — October 11, 2026

Added an optional Developer mode panel, hidden on page load, with physical raw ADC readings/graph, a local unloaded comparison reference, and a guided 12-second unloaded/press/release check. Its decisions require several readings above idle noise, accept either polarity, and report failure to return or insufficient/interrupted data. Exact zero over at least five seconds is labeled suspected stuck output; it is not treated as structural health. Known-mass calibration converts grams to newtons and remains an acknowledged ESP32 command. Missing physical readings and suspected stuck-zero output block both calibration buttons in the UI. New CSV files retain `load_raw` before force calibration. Hardware-mode startup now waits for an unplugged serial device instead of exiting.

The 56 existing Python/C++/serial tests pass, including an explicit raw-count CSV round trip. `node tests/test_load_cell_check.cjs` verifies both polarities, idle noise, isolated-spike rejection, absent response, incomplete return, insufficient samples, stuck-zero duration, disconnect/device restart and repeated-sample handling. JavaScript syntax checks pass. The in-app browser confirmed the panel is initially hidden, opens with its toggle, hides again on refresh, converts 129.1 g to 1.2660 N, and blocks check/calibration without live data. No browser warnings/errors were reported; preview: `developer-mode.png`.

The browser check occurred with the physical ESP32 unplugged. Guided response decisions were tested with fixtures, not a new real force calibration. Earlier real load-cell response and the subsequent stuck-zero readings are recorded in the separate `load_cell_*_check.json` evidence files. No calibrated force or structural health was established by this update.

Verified on October 10, 2026. All measurements below are **simulated**, not results from a printed or instrumented wing.

## Software checks

- **30 tests passed** with `python -m unittest discover -s tests -v`; no skipped tests on this machine.
- Native C++ compilation and execution of the exact firmware `ResponseModel.h` agrees with Python baseline parameters and the normal/anomaly/recovery status and score sequence.
- Real pyserial was tested over a POSIX virtual serial pair, including command writes. Fragmented JSON, oversized lines, malformed/nonfinite values and stream recovery were checked.
- Healthy-baseline quality, constant force rejection, too few samples, negative gauge polarity, score thresholds, out-of-range loads, source separation, command ACK/timeouts, CSV runs/downloads and sensor freshness were exercised.
- CSV provenance and metadata were verified. An additional UI recording created a separate 42-sample simulated run.
- Python sources compile successfully.

## Accelerated demo results

`python -m tests.verify_demo` collects a healthy baseline and saves one complete load cycle for each specimen condition.

| Property | Verified result |
| --- | --- |
| Healthy baseline samples | 170 |
| Healthy response slope | 80.0133 counts/N |
| Healthy intercept | −0.0053 counts |
| Fit R² | 0.999771 |
| Baseline force range | 0.9827–13.0155 N |
| Healthy recorded samples | 160 |
| Healthy health score | 96–99; NORMAL throughout |
| Reduced-stiffness recorded samples | 160 |
| Reduced-stiffness health score | 0–50; WARNING at low load, STRUCTURAL ANOMALY at higher load |

Full values and output filenames are in `data/verification_report.json`. Receipt timestamps reflect the accelerated test execution; `time_ms` records simulated elapsed time. This is a development test, not physical validation.

## Actual ESP32 compilation

Used the existing Arduino IDE toolchain with temporary library/config/build directories; no firmware was flashed and no user's Arduino settings were changed.

| Build | Result |
| --- | --- |
| Simulation mode | Compiled: 295,151 bytes flash, 23,420 bytes global RAM |
| Hardware mode | Compiled: 320,312 bytes flash, 24,876 bytes global RAM |

Toolchain: Arduino CLI 1.5.1, Espressif Arduino-ESP32 3.3.12, `esp32:esp32:esp32` generic ESP32 Dev Module compile target. This is a compile target only; the physical board and GPIOs remain unspecified.

Hardware libraries tested: bogde **HX711 Arduino Library 0.7.5**, **Adafruit MPU6050 2.2.9**, **Adafruit BusIO 1.17.4**, **Adafruit Unified Sensor 1.1.15**. Additional library-manager example dependencies were installed only in the temporary verification directory.

For a CLI hardware compile, use `--build-property 'compiler.cpp.extra_flags=-DSIMULATION_MODE=0'` or change `Config.h`. Replacing `build.extra_flags` can remove ESP32 core definitions and cause misleading dependency errors.

## Browser verification

The local Flask application served successfully. Checked both the desktop 1440 px layout and the narrow approximately 390 px in-app view.

- All four Plotly charts rendered with local JavaScript.
- Healthy baseline sweep completed and plotted the fitted line.
- Reduced stiffness changed the same-load response and produced a structural anomaly.
- White and black themes rendered correctly; theme selection persisted after reload.
- CSV recording and stopping worked through the interface.
- Automatic/manual load controls, unloaded zeroing, and loss of rating outside the calibrated force envelope worked.
- No JavaScript errors or warnings appeared in the inspected browser logs.
- Evidence images: `dashboard-light.png` and `dashboard-dark.png`.

The application's bound address is loopback; remote hosting is not part of the deliverable.

## CAD geometry checks

The subsequent CAD pass targets the user's **140 × 140 × 140 mm** build volume and **4 mm bamboo spars**. Seven individual binary STL exports passed watertightness, consistent winding, positive volume, one connected solid, flat placement at Z = 0, build-volume fit, and 5 mm XY bed-margin checks. The wing is 128 × 72 × 8 mm; two 4.4 mm nominal channels accept the 4 mm spars after a physical fit-coupon check.

OpenSCAD 2026.06.12 exports completed without warnings. The mesh checks used trimesh 5.1.1, numpy 2.2.6 and networkx 3.4.2 in a temporary environment, separate from the dashboard. Assembly, exploded, wing, spar-section and coupon previews were rendered for inspection. Final source/STL hashes and individual checks are saved in `cad/verification/mesh_report.json`.

CAD checks validate exported geometry, not printed fit, strength, skewer variation, load-cell compatibility or predicted strain response. The load-cell shape/hole pattern is a documented, adjustable placeholder pending actual dimensions. The complete assembly is larger than the printer volume; only the separately printed parts must fit.

## Still requires assembled hardware

Sensor wiring, board-specific GPIO selection, strain-gauge bonding, bridge electrical balance, noise measurements, known-load force calibration, physical excitation repeatability, LEDs/buzzer behavior on actual pins, and firmware upload/run on the actual ESP32. Compile success does not validate those physical properties.

## Native Fusion 360 verification

The primary CAD was rebuilt and executed in the installed Fusion application. `cad/fusion/native_build_report.json` reports PASS. Seven printable components each contain one native solid, zero mesh bodies and healthy sketch/extrusion history. The two spar channels followed the clearance parameter to 4.4 mm and back to the user-selected 4.5 mm before export. The reopened archive retained the 4.5 mm bore parameter. The MPU pad was raised to clear the rib tops.

The assembled components and reference hardware passed Fusion interference analysis with coincident faces excluded: zero overlapping solid volumes. The saved assembly F3D was reopened in Fusion; all seven printable components retained sketches and features, with native timeline items in the current document (the exact count is recorded in the build report). The live workspace was visually inspected; the desktop capture is retained locally. Fusion's rendered view is `cad/fusion/previews/fusion_assembly.png`.

The seven Fusion STL exports independently passed the same mesh checks as the earlier OpenSCAD pass: watertight, consistent winding, positive volume, one connected solid, flat on Z = 0, 140 mm build-volume fit and 130 mm XY fit for bed margin. `cad/fusion/verification/mesh_report.json` records source and mesh hashes; `last_check.txt` preserves the check output. Both native and mesh reports match the final native builder source hash. Native F3D, STEP and STL exports exist for all seven parts.

These checks do not establish physical fit, safe load limits or sensor response. The current glue mount needs the actual bar shape, non-sensing end regions and clearance checked; matching the sensor's mounting threads is no longer required.

### Hot-glue mount revision

Replaced the sensor-specific hole pattern with two raised 10 × 24 mm end pads, each with three 0.5 mm deep glue grooves and optional zip-tie return slots. The fixed pedestal attaches to a 90 × 38 mm rail plate; the loaded hanger remains separate, with 10 mm nominal clearance above that plate. The illustrated force lever arm changed from 161 to 171 mm. The reference cell has no assumed screw holes.

The current native build and archive readback pass, every extrusion is healthy, and the illustrated assembly has zero overlapping solid volumes. All seven revised STL files pass the independent geometry checks. The three changed print parts are `tip_adapter`, `cell_spacer` and `load_hanger`; the wing, root base, root cap and spar coupon do not require replacement.

The mounting scheme targets rectangular bar cells only. Hot-glue bonding strength, creep, repeatability and actual sensor fit remain untested. Geometry verification does not establish a sensor-force calibration or load rating. The previous bolt-mount package is preserved as `SkySafe-Fusion360-bolt-mount.zip`.

## User-selected bamboo fit update

The user reported that the printed coupon’s 4.5 mm hole fit best. The native Fusion model was rebuilt with 0.5 mm diametral clearance, exported, and reopened successfully. All seven mesh checks passed again. An independent section of the wing STL at X = 10 mm measured both polygonal bores at approximately 4.493 mm, within 0.02 mm of the 4.5 mm modeled diameter; results and the wing file hash are recorded in `cad/fusion/verification/spar_bore_check.json`. This confirms export geometry; full-length skewer insertion and flexibility still require physical checks.

## Flexible wing revision — short guides

The continuous spar tubes and edge rails are replaced by five short guides per spar and a 12 × 1.8 mm continuous gauge strip. Root and tip shoulders taper into the strip; mating dimensions for the clamp, tip adapter and MPU remain unchanged. The wing remains one connected print, with 4.5 mm bores. This design is intended to reduce continuous plastic reinforcement while using intact bamboo for support. It has no physically established self-weight sag, elastic range, fatigue life or load rating.

Run the native builder in Fusion, then `cad/fusion/verify_meshes.py` and `cad/fusion/verify_flex_wing.py`. The latter samples the root, five guide stations and tip to check both bores (14 sections), and two open bays to verify the 1.8 mm strip and absence of continuous tubes/rails. The source/native/mesh hashes must match. The previous complete Fusion model is preserved as `SkySafe-Fusion360-continuous-tubes.zip`.

The flexible-wing build completed in Fusion and reopened with 415 native timeline items. All seven printable components retained one native solid and healthy features; assembled interference found no volumetric overlaps. Both independent geometry checks passed. The other six part volumes match the previous complete native model, so the existing clamp and load-mount prints remain compatible. The wing’s full-solid CAD volume changed from approximately 32,350 to 27,837 mm³; this is not a slicer mass or stiffness prediction.

## 14-inch modular wing with diamond holes

The latest native Fusion revision is in `cad/fusion_14inch/`. It has 356.4 mm (14.03-inch) root-to-tip span, three bed-sized sections and four reused seam-plate instances. The selected 4.5 mm spar fit now describes the distance between opposite diamond faces, not a circular diameter. All six native passage sketches have driving dimensions; the build checks 4.4 mm and restores 4.5 mm before export.

The native build, reopened archive, feature health and assembly-interference checks passed. All ten distinct STL designs passed the independent mesh verifier. `verify_modular_wing.py` passed 32 diamond cross-sections, aligned seam bolts and all four plate positions, retained gauge-strip thickness and unchanged cap/load-mount volumes. Files are native sketches/solid features, with no mesh imports.

The larger wing uses two 361 mm intact 4 mm spars; the user reported 15.4-inch skewers, which are long enough before cutting. Root tongue height is 10 mm, tip landing 9 mm, spar center height 4.5 mm and guide diameter 9 mm to preserve wall thickness around the diamond corners. The joints are outside the root gauge area. The example loading lever arm is 399.4 mm. Full-assembly printed fit, sag, joint stability, elastic range and physical sensor response remain untested; the old round-hole coupon does not verify the diamond-hole print. No software code or physical load rating changed.


## Judging and optional deflection update — October 10, 2026

- **55 tests passed, zero skipped**, including the original 30 checks.
- Preserved original C++/Python strain/vibration score parity and accelerated simulation results (healthy 96–99, reduced stiffness 0–50 for the verified synthetic cycle).
- Added tests for measured deflection compliance/stiffness, same-force healthy/altered results, disabled/failed tip sensing, failure of each secondary sensor, missing-force refusal, poor-fit rejection, median filtering, signed offset translation, bounded judging windows, unload-to-target flow, brief target hits, duplicate clocks, backlogged data, held result/reset, target validation and extended CSV fields.
- Reconnection with dropped command ACKs was exercised using a failed transport followed by a working one. Real pyserial framing/commands were exercised over a POSIX virtual serial pair. The test writer runs concurrently because the larger JSON frame exceeds the macOS virtual-terminal buffer; reads/command receipts are bounded to avoid hanging verification.
- A native harness executes the actual `.ino` simulation code with the optional distance channel enabled. Its emitted JSON is parsed by the production parser. ZERO distance reference, healthy baseline, healthy/altered response, strain/MPU failure with deflection-only scoring, missing load-cell refusal, DEMO_ZERO baseline retention, recovery and frame-size/baud budget pass. The stub clock and synthetic inputs do not verify physical GPIO/echo timing.
- ESP32 generic Dev Module builds pass with `SKYSAFE_ULTRASONIC=1`: simulation **301,843 bytes flash / 23,780 bytes global RAM**; hardware **329,880 bytes flash / 25,748 bytes global RAM**, using the previously documented ESP32 3.3.12 toolchain/libraries. No firmware was flashed.
- Central serial baud is now 230400 on both sides, with a 4096-byte UART transmit buffer. Full enhanced frames remain within the 4096-byte parser bound and the nominal 10 Hz serial throughput budget in the native harness.

Physical wiring, ECHO level conversion, reflector alignment, unloaded-distance stability, acoustic noise, force calibration, elastic load limit and sensor accuracy still require the assembled rig. The default 10 N target is for simulation and does not establish a safe physical load.


### Final browser evidence

The live local dashboard was exercised through its real UI in white and black themes, with wide and narrow browser views. All six local Plotly graphs rendered; inspected browser logs contained no JavaScript errors or warnings. The narrow view had no horizontal overflow. CSV recording/stopping produced a 532-row simulated run containing optional deflection, sensor coverage and a held result in its JSON metadata.

At the same approximately 10.10 N simulated force, the held healthy result was 8.1 mm deflection / 1.25 N/mm stiffness / 99 health / NORMAL. The altered result was 14.2 mm / 0.72 N/mm / 12 health / STRUCTURAL ANOMALY, with +54.8% strain deviation. These values came from the synthetic sensor stream and baseline; they are not physical wing results or fixed UI examples.

Evidence: `judge-healthy-light.png`, `judge-anomaly-dark.png`, `judge-mobile-dark.png`. DEMO_ZERO retained the fitted baseline, and the unloaded-to-target judge flow completed. Additional parity checks cover the optional deflection model and partial sensor availability; USB identity matching prefers the same device rather than a different board.

## First physical load-cell connection — October 11

Uploaded and verified on the actual ESP32-D0WD-V3, with HX711 DT on D32 and SCK on D33, powered from 3V3. The secondary sensors are disabled until connected. The full firmware produced 29 valid hardware samples in a six-second capture, with the load channel reporting `ok` and simulation false. The dashboard is connected to USB hardware. Zero and force calibration have not been performed; physical loading, mounting, strain, vibration and tip displacement remain unverified.

This board/CP2102 and Mac corrupted 230400-baud data even with short diagnostic frames. 115200-baud diagnostic and full-firmware captures produced valid JSON. The centralized rate is now 115200 baud and telemetry is 5 Hz; acquisition stays 100 Hz. Judge averaging holds for two seconds after settling, retaining the eight-sample minimum. The full-frame bandwidth check and all 55 tests pass with these settings. These results supersede the earlier baud/telemetry settings above.

## Physical IMU connection — October 11

The user identifies the blue module as MPU6050. SDA is D21, SCL D22, VCC 3V3, and GND/AD0 share ESP32 ground. The read-only `IMU_CHECK` serial diagnostic found an acknowledgement at 0x68 and WHO_AM_I 0x70. The original Adafruit MPU6050 initialization rejects that identity. The adapter preserves the original 0x68 initialization and explicitly permits the observed 0x70 register profile through a centralized flag; this is not authentication of a chip model. Unknown identities remain rejected. Initialization verifies the selected ±4 g range and awake state; short or failed acceleration reads invalidate the channel rather than emitting stale data.

The firmware compiled (331,244 bytes flash / 25,764 bytes global RAM), uploaded at 115200 baud, and passed flash hash verification. A seven-second USB capture produced 34 actual hardware frames, with both load and vibration channels reporting `ok`. The last acceleration vector was (9.06325, -0.016759, -4.07134) m/s², magnitude approximately 9.94 m/s², with gravity-removed RMS 0.0176 m/s². This establishes stationary sensor communication and plausible scale, not calibrated vibration accuracy or mounted wing behavior. Force remains unzeroed and uncalibrated; strain and ultrasonic channels remain disabled.

All 56 software tests pass. The added native test exercises the real adapter with controlled I2C transport: positive/negative 1 g conversion, byte order, signed limits, both identity paths, refusal of unknown IDs, failed range configuration, incomplete reads, bus loss and reinitialization. Physical motion response and the assembled wing still need verification.

The user subsequently tilted the loose IMU board. Actual dashboard history recorded acceleration changes across all three axes and a gravity-removed RMS peak of 6.739327 m/s², returning to approximately 0.025 m/s² after settling. Both load and vibration channels report `ok` at the peak and after settling. This verifies response to hand motion; the peak is not a calibrated wing vibration measurement. Evidence: `imu_motion_check.json`.

## Weighted M3 holder — October 11

The user has M3 screws up to 30 mm and requested a rear weight area instead of a table clamp. The native Fusion revision in `cad/fusion_weighted` adds three print parts: a 130 × 110 × 10 mm root base, a 130 × 110 × 10 mm ballast tray and a 24.2 × 98 × 4 mm splice. The existing root cap and all wing/sensor parts are reused. Root support height is reduced to 6 mm, making the root/cap stack 24 mm. Bolt heads are recessed underneath and nuts sit above the cap/bridge, so excess shaft length does not rock the stand on the table. The cap's existing 4.4 mm holes need M3 washers that cover them.

Fusion built and exported all three new parts as native F3D, STEP and STL, reopened the assembly with 131 native timeline items, and found no overlapping assembled solids. Each new part contains one native solid and sketches, with zero mesh bodies. Independent export checks passed watertightness, winding, connectedness, volume, flat-bed placement, 140 mm bed fit (130 mm maximum XY), 26 circular sections for holes/recesses/pins, old cap alignment and tray joint alignment. The native build report and mesh report agree with final source/helper hashes.

The assembled footprint is 260.2 × 110 mm. The marked ballast center is 202 mm behind its front support edge; the nominal force point is 397.4 mm ahead. Static calculations are recorded separately in `verification/stability_estimate.json` and exclude rig self-weight, friction, dynamics and print strength. Neither these calculations nor geometry checks establish a physical loading limit. The ballast attachment, base motion, printed fit, seam rigidity and tipping must be tested with the real wing. No sensor software changed in this CAD revision.

## Raised laptop-foot holder — October 11

The requested stand with a tab under a 14-inch laptop is a separate native Fusion variant in `cad/fusion_laptop_stand`. It requires one new print and reuses the old cap and all wing/sensor parts. Its working footprint is 130 × 110 mm, deck height 41 mm, rear tab thickness 3 mm. The side-oriented STL measures 130 × 42 × 110 mm and has four 3.4 mm-inscribed diamond M3 bores. Four M3 × 25–30 mm screws pass upward through the 24 mm deck/root/cap stack; washers cover the reused cap's larger 4.4 mm holes. The short rear stop clears the existing spar passages.

Fusion exported native F3D, STEP and STL, reopened the assembly with 44 timeline items, checked feature health and found no overlapping assembled solids. Independent mesh checks passed watertightness, winding, one connected solid, exact profile-minus-bores volume, flat-bed placement, printer fit, 12 diamond-bore sections and four original cap bore sections. Source/helper hashes match the build report. Physical fit, laptop contact, sliding, tipping and strength remain untested. Only actual laptop reaction on the tab contributes anchoring force; the full laptop weight is not assumed. The 10 N software example is not a validated load for this holder. No sensor software changed.
