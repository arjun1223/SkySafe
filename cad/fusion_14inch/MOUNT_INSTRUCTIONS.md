# SkySafe rectangular bar load-cell mounting

## Hot-glue end mount

The sensor screw pattern is removed. `cell_spacer.f3d` is now a **fixed glue pedestal** and `load_hanger.f3d` a **free-end glue hanger**. Each has a raised **10 × 24 mm landing**, three **0.5 mm deep glue-key grooves**, and two optional zip-tie return slots. The tall fixed pedestal attaches to two long rails on the tip adapter. Four M3 bolts secure the printed pedestal to those rails; they do not thread into the sensor. A small prototype can instead glue that pedestal-to-plate joint on its solid contact areas, with the same unvalidated attachment limitations.

Use a rectangular bar cell with flat, non-sensing end regions that fit the landings. Up to 24 mm bar width fits fully on the pad; the tie slots sit outside it. Place glue **only at the two end pads**. Leave the cell's active middle, strain-gauge covering and wire exit clear. Route any backup tie around that same end and its own carrier; never tie the free carrier to the adapter plate.

For the illustrated 60 × 12.7 × 12.7 mm example, the pads are 50 mm apart, leaving 40 mm between their inner edges. A nominal 0.5 mm glue-film gap is shown. The free hanger's underside sits **10 mm above the adapter plate**, so the extended plate does not directly carry the hanging load. Keep a visible air gap after gluing and during every test; contact would bypass the sensor. Do not glue the cell's middle or free carrier to the plate.

Different rectangular bar lengths can use the same parts: align the fixed pad with one end, and reposition the free hanger under the other end in Fusion and physically. The example loaded-end center is X = 195 mm, giving a **171 mm force lever arm** from the root clamp exit. Nominal 40–100 mm bar layouts are possible, but actual end-region geometry and wire clearance still need checking; this is not a universal mount for disc, button, S-type or four-corner sensors.

Let the glue cool, inspect the attachment, then tare and calibrate the fully assembled fixture. Hot-glue strength, slip and creep have not been validated; use small bench loads, inspect before every run, and establish a fresh baseline after any remounting. Confirm repeated known-load readings before using the mount for stiffness comparisons. A sensor's 5 kg rating does not rate the glue or print.

See [printing and assembly guide](../README.md) for hardware, mounting, gauge placement and comparison experiments. These geometry checks do not establish printed fit, gauge sensitivity or a load rating.


The 14-inch wing uses a 9 mm tip landing and a 6 mm adapter plate. Use four M3 × 20–25 mm bolts with washers/nuts and check actual thread engagement. The fixed pedestal uses optional M3 × 35 mm bolts or a prototype glue bond to the rails.
