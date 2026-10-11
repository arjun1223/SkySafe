# Hardware wiring and sensor placement

Disconnect USB before changing wiring. The configured board is a classic ESP32; D25 means GPIO25, for example. Sensor ground connections share ESP32 GND, and the three modules share 3V3.

| Module | VCC | GND | Data | Clock | Other |
| --- | --- | --- | --- | --- | --- |
| Load-cell HX711 | 3V3 | Common ground | DT/DOUT → D32 | SCK/CLK → D33 | Bar cell connects below |
| Strain-gauge HX711 | 3V3 | Common ground | DT/DOUT → D25 | SCK/CLK → D26 | Resistor bridge connects below |
| MPU6050 | 3V3 | Common ground | SDA → D21 | SCL → D22 | AD0 → common ground; INT/XDA/XCL unused |

## Load cell to first HX711

For the supplied four-wire bar cell: red → E+, black → E−, green → A+, white → A−. Green is a signal wire, not ground. Check the supplier's mapping if using another cell. Leave B+/B− unused.

Keep the metal center flexure clear. Mount one end on the tall fixed support and the other on the free hanger, which must not rest on the platform. Apply the measured load to the free hanger. See [mount instructions](../cad/fusion_14inch/MOUNT_INSTRUCTIONS.md).

## Foil gauge to second HX711

Use one intact BF350 nominal 350 Ω gauge and three separate nominal 350 Ω resistor arms, R1–R3. Each arm can be 330 Ω + 10 Ω + 10 Ω in series. Measure the arms disconnected and unpowered; matching and stable connections matter.

| HX711 terminal | Junction connections |
| --- | --- |
| E+ | One end of R1 and one end of R2 |
| A+ | Other end of R1 and one gauge lead |
| A− | Other end of R2 and one end of R3 |
| E− | Other end of R3 and other gauge lead |

Either gauge lead can be used at A+. Leave B+/B− unused. The foil gauge does not connect directly to an ESP32 pin.

Bond the gauge on the thin flat center strip between the spars, 32–48 mm from the clamped root end toward the tip. Align its sensing grid along the wing span. The smooth backing contacts the wing; the solder pads face outward. Use a thin adhesive bond and follow its cure time. Ordinary CA is a prototype substitute for dedicated strain-gauge adhesive. Keep hot glue away from the sensing patch; use small dabs farther away to anchor slack leads. Never pull the gauge by its wires or reuse a torn solder pad.

## Where to mount electronics

- ESP32 and strain HX711: stationary root stand, USB port accessible.
- Load HX711: tip platform beside the fixed load-cell support, clear of the hanger and flexure.
- IMU: firmly attached to the moving tip platform, component side outward.

Insulate exposed contacts. Leave slack at joints and around the gauge so wire motion does not load its pads or restrict wing motion.

## First checks

Reconnect USB, select ESP32 USB serial in the dashboard, and enable Developer mode to inspect fresh raw load/strain readings. Let the unloaded rig settle before ZERO. Calibrate force using a known mass applied only through the free hanger. Firmware restarts clear calibration and baseline.

Check a gentle, repeatable bend and release before collecting a healthy baseline. Raw ADC communication alone does not prove a valid bond or calibrated strain. Bring-up recorded a strain response followed by drift; a damaged gauge pad requires replacement before further validation. Set the demo target and baseline thresholds to the physically tested range. The default 10 N simulation target is not a rating for the wing or stand.

Ultrasonic measurement is optional and disabled by default. Its separate 5 V/ECHO level-shifting instructions are in the [main README](../README.md#optional-hc-sr04). All enable flags and hardware pins are centralized in `firmware/skysafe_esp32/Config.h`.
