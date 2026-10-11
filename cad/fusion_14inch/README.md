# SkySafe 14-inch modular wing — native Fusion 360

The assembled wing is **356.4 mm / 14.03 inches root to tip**, including the solid 24 mm root clamp tongue. It is three connected sections, printed separately on the **140 × 140 × 140 mm bed**. The chord tapers from approximately 72 to 62 mm. This is an open benchtop wing specimen; its self-weight support, elastic range, joint strength and usable loads still require a physical test.

Open `SkySafe_Assembly.f3d` in Fusion using File → Open → Open from my computer. Native sketches and extrusion/join/cut history are included. Individual F3D, STEP and STL files retain their original print positions at Z = 0. The assembly includes reference bamboo and example sensor hardware, which are not printable.

## Exactly what to print for the wood + C-clamp setup

| File in `stl/` | Quantity | Nominal bounding box, mm |
| --- | ---: | --- |
| `wing_root.stl` | 1 | 128 × 72 × 10 |
| `wing_middle.stl` | 1 | 114 × about 68 × 9 |
| `wing_tip.stl` | 1 | 114 × about 65 × 9 |
| `joint_plate.stl` | **4** | 24.2 × 20 × 2 |
| `root_cap.stl` | 1 | 30 × 98 × 8 |
| `tip_adapter.stl` | 1 | 90 × 38 × 6 |
| `cell_spacer.stl` | 1 | 26 × 34 × 21.2 |
| `load_hanger.stl` | 1 | 26 × 34 × 11.2 |

The cap, adapter, pedestal and hanger retain the previous revision's geometry. Reuse those if printed. **Do not print the earlier single-piece `wing.stl` for this version.** `root_base.stl` remains optional and `spar_fit_coupon.stl` now checks diamond holes. The earlier round coupon does not verify the new shape; a quick diamond fit check is recommended before the three wing sections. The base is not needed for the user's wood-and-clamp setup. If using the printed base instead, its jaw/wing/cap stack is now 34 mm; M4 × 45 mm bolts with washers/nuts are a starting choice, subject to actual engagement checks.

Print flat as supplied, millimeters, 100% scale. Match the tested coupon's material; use a 0.4 mm nozzle, 0.2 mm layers, 3 walls, and 5 top + 5 bottom layers. 5–15% infill is a starting option for the wing sections; 15% for the cap and load fixture. The 2 mm joint plates should be solid with these top/bottom layers. Check all narrow strips, ribs and guide walls are continuous in the sliced preview. Leave supports out of the spar bores. Keep print settings unchanged across measurements. Print parts separately or check each plate arrangement and any brim against the available bed.

## Join the three sections

1. Place the root, middle and tip flat on a table, in that order, with their spar bores aligned. The root section has the solid clamp tongue and MPU pad; the tip has the four adapter holes.
2. Leave **0.2 mm between each section**. Assembly coordinates are root X = 0, middle X = 128.2 and tip X = 242.4 mm.
3. Sandwich each seam between **two joint plates**, one below and one above the reinforced center-strip ends. The plates bridge the seam, at global X = 116–140.2 and 230.2–254.4 mm. Their holes align with one hole in each neighboring section. The seam plates are clear of the gauge and bamboo paths.
4. Use **two M3 bolts per seam, four total**, with washers and nuts. The printed stack is 6.4 mm; M3 × 12–16 mm may work depending on the washers and nuts. Check actual thread engagement. Tighten evenly until secure without crushing the layers. The bamboo keeps the sections aligned; inspect joints for movement before every baseline.
5. Fit two straight, intact nominal **4 mm bamboo spars** through **diamond holes measuring 4.5 mm between opposite faces**. The user's 15.4-inch skewers are sufficient. Cut to **361 mm / 14.21 inches**, smooth the ends, support the wing during insertion and stop gently at the closed tip. Approximately 354.4 mm is engaged and 6.6 mm remains exposed at the root. Keep the spars removable; use removable tape keepers on the exposed ends if needed. Do not splice the rods or glue them to the guides.
6. Clamp only the solid 24 mm root to rigid wood, using the cap or a flat pressure-spreading block. Keep the whole bending span, sensors and hanger clear of the bench. Cardboard is only a thin protective pad.

The center strip is continuous within each section. It remains **1.8 mm thick in the root gauge zone**, and is **2.4 mm thick farther out**. Joints are locally reinforced and held by the plates rather than loose hinges. Each diamond encloses a 4.5 mm circle (6.364 mm corner-to-corner), so the round 4 mm bamboo clears its four faces. The holes share a center height of 4.5 mm; the larger 9 mm outer guides and 10 mm root keep material above and below the corners. The roof faces are 45° to the bed, intended for printing without internal supports. The new diamond shape still needs a physical fit check. The printed spar guides are short; bamboo remains exposed between the ribs. No structural skin is included.

## Sensors and load mount

The strain gauge stays lengthwise along X at approximately X = 33–43 mm, Y = 0. Its flat region is X = 32–48 mm, 12 mm wide and 1.8 mm thick. Check the actual gauge backing fits. The MPU pad remains at X = 74–98 mm. Route slack wires and strain-relieve them near the root.

The four unchanged load-mount parts use the same hardware and end-only hot-glue assembly as the smaller version; see [mount instructions](MOUNT_INSTRUCTIONS.md). Four M3 × 20–25 mm bolts with washers/nuts join the 9 mm tip landing to the 6 mm adapter; check actual thread engagement. Four optional M3 bolts or a prototype glue bond hold the pedestal to the sliding adapter rails. Glue a compatible rectangular bar cell only at its non-sensing ends. Keep the active middle and wire exit clear. Never glue the free hanger to the adapter, and keep a visible gap beneath it under load. Unknown sensor geometry must be checked against the actual cell.

The example force line is at **X = 423.4 mm**, so its lever arm from the root clamp exit is **399.4 mm**. Repositioning a different cell changes this distance. A load rating on the sensor does not rate the wing, joints or glue bonds.

## Before measuring

Start with both intact spars and all sensor hardware fitted. Support the tip until clamped and assembled. Observe resting sag, then apply a very small load gradually, remove it and confirm the wing returns. Stop for permanent bending, cracks, slipping joints, excessive sag or an attachment touching the plate. The longer span changes the response; do not reuse a baseline from the smaller wing or assume its load range transfers. No numerical safe load is established.

After checking the physical setup, tare/calibrate and collect a fresh healthy baseline. Keep clamp, seam bolts, hardware and wire placement the same for spars-out comparisons. Unload completely and support the tip before removing a spar. If the rod does not withdraw smoothly, stop rather than forcing it through misaligned guides. The simulator's load sweep and minimum baseline force span are software defaults, not physical loading instructions. If they exceed the tested specimen range, configuration must be adjusted consistently from actual measurements.

## Rebuild and verification

Add `SkySafeFusion14/` through Fusion's Scripts and Add-Ins → + → Script or add-in from device, then Run `SkySafeFusion14`. It creates a new document, with local F3D/STEP/STL exports. Coordinates are fixed in named sketches; bore diameter and selected thicknesses use user parameters. A thickness edit also needs mating-plate placement changes; do not scale an STL to change hole fit.

`native_build_report.json` records native-solid counts, feature health, archive reopening, assembly interference, selected bores and dimensions. Run `verify_meshes.py` and `verify_modular_wing.py` using numpy/trimesh/networkx for independent exported geometry checks. They do not establish stiffness, physical fit or safe load.

## Completed geometry verification

Native Fusion build passed: ten distinct printable native solids, healthy extrusion features, zero assembly overlap, reopened native archive with feature history, and six parameter-driven diamond passages checked at 4.4 mm then restored to 4.5 mm. Independent mesh checks passed for all ten designs: connected watertight solids, consistent winding, positive volume, flat Z = 0 and fit inside the 140 mm build volume. The modular check passed for 356.4 mm assembled span, 32 diamond-hole sections, six mating bolt-hole positions, four correctly positioned seam plates, unchanged cap/load-mount parts, and the 1.8 mm gauge strip. These are geometry checks; printing and bending are untested.
