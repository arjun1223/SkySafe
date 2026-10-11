# SkySafe — native Fusion 360 CAD

Open **`SkySafe_Assembly.f3d`** in Fusion with **File → Open → Open from my computer**. This is a native model made with sketches and extrusion/join/cut features. The seven printable components have editable history, named features and no imported mesh bodies. The assembly also includes separate reference geometry for the bamboo, provisional load cell, board and gauge.

## Files to use

- `SkySafe_Assembly.f3d`: positioned assembly and reference hardware. Assembly placement is static; no articulated joints or structural analysis are provided.
- `SkySafe_PrintParts.f3d`: the seven printable components at their original modeling origins. They overlap; this is a component collection, not a shared slicer plate. Isolate one component at a time.
- Individual part `.f3d` files: each part's native model at Z = 0. Use these for editing and re-exporting a printable part.
- `stl/*.stl`: seven separate meshes in millimeters, flat on Z = 0. Print each separately on the 140 × 140 × 140 mm printer.
- `step/*.step`: individual solid exports; `SkySafe_Assembly.step` is the positioned assembly.
- `native_build_report.json`: feature health, native solid counts, print bounds, spar-parameter trial, assembled interference and archive readback.
- `verification/mesh_report.json`: independent STL geometry checks with file hashes.
- `previews/fusion_assembly.png`: Fusion's rendered assembly view.

## Bamboo and editing

The current **short-guide wing** remains one printable piece. Five 6 mm long guides per spar replace the continuous plastic tubes; there are no continuous leading/trailing edge rails. A 12 mm wide, **1.8 mm thick continuous strip** connects the ribs and carries the gauge. Tapered shoulders connect it to the rigid root and tip. The root tongue, clamp interfaces, tip bolt pattern, MPU pad, 4.5 mm spar fit and all other printed parts retain their mating dimensions.

Use **both intact bamboo spars** for initial assembly. Support the tip while inserting them through the separated guides. Do not glue the spars, gauge strip or exposed bays. This reduces the continuous plastic reinforcement so the bamboo can contribute more of the support; it does not establish a tested elastic range or guarantee a level wing under sensor weight. Check the fully assembled fixture's resting shape, then apply small incremental loads and confirm it returns when unloaded. Excessive sag, clamp movement, permanent bending or cracks require adjustment before collecting a baseline.

Two nominal **4 mm bamboo skewers** use **4.5 mm bores**, selected by the user from the printed fit coupon. The coupon's horizontal holes are 4.1, 4.3, 4.4, 4.5 and 4.7 mm, labeled with engraved numerals. Use the same material, orientation and slicer settings as the tested coupon. Skewer length is **132 mm**: 126 mm inside and 6 mm exposed at the root.

In **Modify → Change Parameters**, `sparDiameter` and `sparClearance` drive `sparBore` in both channel sketches. Clearance is **0.5 mm**. Both channels are checked at 4.4 mm, then restored to **4.5 mm before export**; the reopened native archive also checks the selected bore parameter. M3/M4 round clearances use user parameters. Sensor mounting screws are no longer required. The 7.2 mm MPU pad clears the 6.95 mm ribs.

Layout coordinates, sensor mounting slots, the coupon bores, tapered shoulder coordinates and assembly positions are fixed. Edit the named sketches or rebuild for layout changes. Changing gauge-strip thickness also requires editing both shoulder sketches and the gauge reference height. Changing other extrusion thicknesses requires repositioning their mating components. Export the wing from its individual file in the original print orientation; do not scale the entire mesh to change hole clearance.

## Hot-glue end mount

The sensor screw pattern is removed. `cell_spacer.f3d` is now a **fixed glue pedestal** and `load_hanger.f3d` a **free-end glue hanger**. Each has a raised **10 × 24 mm landing**, three **0.5 mm deep glue-key grooves**, and two optional zip-tie return slots. The tall fixed pedestal attaches to two long rails on the tip adapter. Four M3 bolts secure the printed pedestal to those rails; they do not thread into the sensor. A small prototype can instead glue that pedestal-to-plate joint on its solid contact areas, with the same unvalidated attachment limitations.

Use a rectangular bar cell with flat, non-sensing end regions that fit the landings. Up to 24 mm bar width fits fully on the pad; the tie slots sit outside it. Place glue **only at the two end pads**. Leave the cell's active middle, strain-gauge covering and wire exit clear. Route any backup tie around that same end and its own carrier; never tie the free carrier to the adapter plate.

For the illustrated 60 × 12.7 × 12.7 mm example, the pads are 50 mm apart, leaving 40 mm between their inner edges. A nominal 0.5 mm glue-film gap is shown. The free hanger's underside sits **10 mm above the adapter plate**, so the extended plate does not directly carry the hanging load. Keep a visible air gap after gluing and during every test; contact would bypass the sensor. Do not glue the cell's middle or free carrier to the plate.

Different rectangular bar lengths can use the same parts: align the fixed pad with one end, and reposition the free hanger under the other end in Fusion and physically. The example loaded-end center is X = 195 mm, giving a **171 mm force lever arm** from the root clamp exit. Nominal 40–100 mm bar layouts are possible, but actual end-region geometry and wire clearance still need checking; this is not a universal mount for disc, button, S-type or four-corner sensors.

Let the glue cool, inspect the attachment, then tare and calibrate the fully assembled fixture. Hot-glue strength, slip and creep have not been validated; use small bench loads, inspect before every run, and establish a fresh baseline after any remounting. Confirm repeated known-load readings before using the mount for stiffness comparisons. A sensor's 5 kg rating does not rate the glue or print.

See [printing and assembly guide](../README.md) for hardware, mounting, gauge placement and comparison experiments. These geometry checks do not establish printed fit, gauge sensitivity or a load rating.

## Rebuild

Open Fusion's **Scripts and Add-Ins** (`Shift+S`), add the `SkySafeFusion` folder from this directory as a script from your device, and run **SkySafeFusion**. The script creates a new document and exports locally; it leaves other documents intact. It also reopens the exported archive to check that native sketches and feature history survive. Follow Autodesk's [script runner instructions](https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/files/SLD-MANAGE-SCRIPTS-ADD-INS.htm).

Independent mesh checks require Python packages `numpy`, `trimesh` and `networkx`; run `verify_meshes.py` from this directory. Those dependencies are separate from the software dashboard.

Then run `verify_flex_wing.py` to check 14 bore sections and two open bays directly in the exported wing STL. These checks verify the 4.5 mm guides, 1.8 mm strip and removed continuous tubes/edge rails, not bending performance. The previous complete model is preserved in `SkySafe-Fusion360-continuous-tubes.zip` beside the project directory.
