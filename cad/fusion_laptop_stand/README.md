# Raised laptop-foot stand — one new print

Print **only `stl/laptop_foot_stand.stl`**. Reuse the existing printed root cap, wing, joints and sensor mounts. The stand replaces the old root base; the rear ballast tray and tray bridge are not needed for this variant.

The 130 × 110 mm assembled base has a 41 mm-high clamp deck and a 3 mm-thick rear tab. The tab extends 92 mm behind the support wall, to slide underneath the laptop's front edge. It has no laptop-specific socket or connector. The native model is made in Fusion with sketches and extrusions; its assembly archive includes an illustrative wing envelope, not new wing print geometry.

## Print settings

- PLA; 0.20 mm layers; 30% infill.
- Four walls/perimeters; five top and five bottom layers.
- Supports off. **Keep the STL's supplied orientation**, lying on the stand's side. Print dimensions are 130 × 42 mm on the bed and 110 mm tall.
- A 3 mm brim fits inside a 140 mm bed. Check the slicer's usable area and any reserved area before printing.
- The four horizontal M3 holes have 45° diamond roofs. Inspect layer preview for continuous walls and correctly bridged/supported bore roofs before starting. The upper surfaces of the bores rise at 45° in this orientation. Do not rotate it upright into its working orientation for printing.

## Assembly

1. Place the stand upright on a firm, flat table. The large thin tab points away from the wing, toward the laptop.
2. Place the wing's solid root tongue on the raised deck, with its rear end against the short stop. Both skewers extend toward the wing. The old locating-pin sockets are unused; the stop and tightened cap locate this version.
3. Put the existing cap on top. Insert **four M3 × 25–30 mm screws upward from underneath the raised deck**. Fit M3 washers over the cap's larger 4.4 mm holes, then nuts above. The clamped stack is 6 + 10 + 8 = 24 mm, plus washers/nuts. Tighten evenly and only enough to prevent slipping; do not crush the printed parts.
4. Protect the laptop's contact surface with one thin layer of tape. Slide the rear tab under a solid area of the front edge. Keep it clear of vents, ports and rubber feet. Confirm the laptop actually bears on the tab: a tab floating in the gap beneath the case provides no hold-down force. Use books or other ballast on the tab if contact is poor.
5. Attach the already printed sensor mounts as previously planned. Keep the load cell's sensing section free to flex and wires slack enough for wing motion.

## Check before a demonstration

Start with very gentle load at the actual sensor/loading point while someone steadies the base. Check for sliding, lifting, loose cap, root movement and cracking. Increase only while the entire stand stays planted. Stop if it moves. No physical force rating is established; **the dashboard's example 10 N target is not a validated load for this holder**.

Only the laptop's actual reaction on the tab resists lifting; the full laptop mass must not be assumed to act there. The relevant nominal front pivot is x = 26 mm, while the prior loading point is x = 423.4 mm (397.4 mm lever). The contact position and supported fraction of laptop weight are unknown until inspected on the real setup. A rigid stand is needed for repeatable baseline measurements, so repeat ZERO and healthy baseline after mounting or ballast changes.

## Native files and verification

`SkySafe_Laptop_Stand.f3d` is the assembled native model. `laptop_foot_stand.f3d` is the stand in its print orientation. STEP files are also included. `SkySafeLaptopStand/` contains the rebuild script and manifest; the adjacent original `fusion_14inch/SkySafeFusion14/` helper is needed when rebuilding.

`native_build_report.json` records feature health, one native printable solid, printer dimensions, assembled interference and archive reopening. `verification/mesh_report.json` checks the actual STL, diamond-hole sections and alignment to the existing cap. These are geometry checks, not physical strength or anchoring tests.
