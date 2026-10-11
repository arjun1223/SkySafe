# Weighted root holder — M3 fasteners, 140 mm printer

This revision replaces the clamp base with a weighted stand for the existing
356.4 mm wing. The wing sections, joints, spars and sensor mounts are unchanged.
Reuse the printed `root_cap` from `fusion_14inch`. All new features are native
Fusion sketches and solid extrusions; run `SkySafeWeighted` in Fusion to export.
The builder creates a new document and preserves the previous CAD files.

## Print exactly these three new parts

| STL | Quantity | Dimensions, mm | Purpose |
| --- | ---: | --- | --- |
| `weighted_root_base.stl` | 1 | 130 × 110 × 10 | Lower wing root mount and front tray |
| `ballast_tray.stl` | 1 | 130 × 110 × 10 | Rear weight tray |
| `tray_bridge.stl` | 1 | 24.2 × 98 × 4 | Upper connection between the two plates |

Print flat as exported, millimeters, 100% scale, 0.2 mm layers, 4 walls,
5 top and 5 bottom layers. Start with 30% infill for both large plates; print
the bridge solid. Supports off: inspect the short bridges above the 6.4 mm
underside bolt-head pockets in the slicer. Keep those pockets clear. The
existing cap does not need reprinting. These settings are starting choices,
not a strength or load certification.

## Hardware and assembly

- Four **M3 × 30 mm** screws for the root, four M3 nuts and four washers.
- Four additional **M3 × 12–30 mm** screws for the tray joint, four nuts and
  four washers. Shorter screws keep the joint tidier; the joint accepts the
  user's 30 mm screws because their excess length projects upward.
- Root-cap washers must cover its existing **4.4 mm holes**; normal M3 washers
  with approximately 7 mm outer diameter do this. Check your actual washers.
- Screw heads must fit **6.4 mm diameter × approximately 3.35 mm deep** pockets.
  Inspect the actual hardware: heads must sit fully above the bottom plane.

1. Put both large plates flat on the table, with their open ends facing each
   other. Align the two pairs of holes, leaving a hairline 0.2 mm seam gap.
2. Put the wide bridge **on top** of that joint. Insert four screws **up from
   underneath**. Their heads sit in the underside recesses; washers and nuts
   go above the bridge. Tighten gently and evenly. The bottoms must remain flat.
3. Seat only the wing's solid 24 mm root on the front base. Its two original
   locating holes fit the base pins. Reuse the root cap on top.
4. Insert four M3 × 30 mm screws **up from underneath**, then put washers and
   nuts above the cap. The excess screw length stays above the cap rather
   than pressing on the table. Leave the bending span free beyond the cap.
5. Place the base at the table edge with **both plates fully supported** and
   the wing extending beyond the edge. The support's front edge is 2 mm past
   the solid wing-root tongue. Keep the wing and tip hardware clear of the table.
6. Put books or a secure bag of rice/sand over the rear tray's recessed cross.
   Keep the weight centered across the width. Strap or tape the weight to the
   tray if it shifts; the small tray lips do not secure a tall stack of books.
   Use a thin nonslip mat under the whole stand, checking that no bolt head
   protrudes. Avoid using a laptop as ballast.

The assembled base is **260.2 × 110 mm**. The tray's marked weight center is
202 mm behind the front support edge. The nominal load-cell pushing point is
397.4 mm in front of that edge; its actual position depends on your bar cell.

## Weight and tipping: calculated examples, not a tested load rating

Downward force at the wing tip creates a tipping moment. Ballast behind the
front edge supplies the opposing moment. Ignoring wing/fixture self-weight,
the static balance condition is `mass_kg × 9.80665 × rear_distance_m >
force_N × front_distance_m`. This follows the zero-net-torque condition for
[static equilibrium](https://openstax.org/books/university-physics-volume-1/pages/12-1-conditions-for-static-equilibrium).

At the nominal geometry, **10 N requires approximately 2.01 kg just to balance**.
That leaves no reserve for wing/fixture weight, weight positioning, hand motion,
sliding or print flexibility. A preliminary **2× applied-load moment allowance**
requires approximately **4.01 kg for 10 N**, again before accounting for the
wing/fixture's own forward moment. This allowance is an engineering starting
choice, not an established safety factor or permission to push the wing to 10 N.

| Ballast centered at the rear cross | Applied force equivalent at 2× moment allowance, ignoring rig self-weight |
| ---: | ---: |
| 1 kg | 2.49 N |
| 2 kg | 4.98 N |
| 3 kg | 7.48 N |
| 4 kg | 9.97 N |

Start with a very small push and release. Check that the root stays fixed, the
rear of the stand never lifts, the ballast does not move, the seam remains
rigid and the stand does not slide. Any base motion invalidates a stiffness
comparison. No physical load limit for this stand or wing has been established.
Choose the dashboard target and baseline range only after repeatable bench
checks. Its default 10 N target is not a physical instruction.

## Native files and verification

`SkySafe_Weighted_Holder.f3d` contains the holder assembly, the reused cap and a
clearly named reference root/wing-span envelope. Print only the three named STL
files above; the reference envelope is not a replacement wing. Individual F3D
and STEP files contain each new part at its print position. The source reopens
the saved archive, checks native history and tests assembly interference.

Run `verify_weighted_holder.py` with numpy, trimesh and networkx to check export
geometry, print-bed fit, bolt diameters/recesses, root pin positions and cap
alignment. Geometry checks do not establish physical strength or stability.

The native Fusion build completed and its archive reopened with 131 timeline
items. Each new part has one native solid, editable sketches and no mesh
bodies. Assembly interference found no overlapping solid volumes. All three
STLs passed independent geometry checks, including 26 measured circular
sections, recessed head pockets, existing cap alignment and tray-bridge hole
alignment. Printed fit, stiffness, friction and tipping remain untested.
