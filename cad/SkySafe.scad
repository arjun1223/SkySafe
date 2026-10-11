// SkySafe benchtop wing and fixture. Millimetres throughout.
// Print individual parts, not the assembly. See README.md before loading.

/* [Output] */
part = "assembly"; // [assembly,exploded,spar_section,wing,root_base,root_cap,tip_adapter,cell_spacer,load_hanger,spar_fit_coupon]
show_reference_hardware = true;
show_spars = true;

/* [Printer and wing] */
bed_size = 140;
wing_span = 128;
root_length = 24;
root_chord = 72;
tip_chord = 62;
root_thickness = 8;
rib_pitch = 20;
rib_width = 2.4;
gauge_beam_width = 12;
gauge_beam_thickness = 3.2;
tip_pad_length = 16;

/* [Bamboo spars] */
spar_nominal_diameter = 4;
// Check the coupon; bamboo diameter and printer holes vary.
spar_clearance = 0.4;
spar_y = 18;
spar_wall = 1.2;
spar_blind_end = 2;
spar_grip = 6;

/* [Fasteners] */
m3_clearance = 3.4;
m4_clearance = 4.4;
m4_nut_af = 7.1;
m4_nut_depth = 3.3;
bench_bolt_clearance = 6.6;

/* [Unmeasured bar load cell - CHANGE TO YOUR PART] */
cell_length = 60;
cell_width = 12.7;
cell_height = 12.7;
// Two threaded holes per end, along the cell axis. Defaults are placeholders.
cell_hole_pitch = 10;
cell_end_hole_offset = 5;
cell_bolt_clearance = 4.4;
cell_slot_travel = 4;
cell_standoff = 10;

/* [Hidden] */
$fn = 64;
eps = 0.05;
spar_bore = spar_nominal_diameter + spar_clearance;
spar_outer = spar_bore + 2*spar_wall;
spar_z = spar_outer/2;
tip_z = spar_outer+0.15;
adapter_x = wing_span-tip_pad_length;
adapter_length = 50;
cell_x = wing_span+7;
spacer_length = cell_hole_pitch+16;
spacer_width = max(20, cell_width+6);
fixed_center = cell_x + cell_end_hole_offset + cell_hole_pitch/2;
loaded_center = cell_x+cell_length-cell_end_hole_offset-cell_hole_pitch/2;
base_height = 8;
jaw_height = 8;
wing_assembly_z = base_height+jaw_height;
cap_height = 8;

assert(wing_span <= bed_size-10, "Wing needs 5 mm bed margin per end.");
assert(root_length == 24 && wing_span >= 118, "Default fixture needs a 24 mm root and at least 118 mm span.");
assert(root_chord >= 68 && root_chord <= 76 && tip_chord <= root_chord, "Default jaw supports 68-76 mm root chords.");
assert(root_thickness >= spar_outer+0.8, "Keep a roof above the root spar ports.");
assert(spar_y >= 16 && spar_y <= 20, "Keep channels clear of the board pad and inside the ribs.");
assert(spar_nominal_diameter == 4, "This version is designed around 4 mm bamboo.");
assert(spar_clearance >= 0.1 && spar_clearance <= 0.8, "Use coupon clearances 0.1 to 0.8 mm.");
assert(tip_chord > 2*(spar_y+spar_outer/2+4), "Keep spar walls inside the wing outline.");
assert(cell_length >= 55 && cell_length <= 100, "Recheck adapter/free-end clearance outside 55-100 mm cells.");
assert(cell_hole_pitch >= 8 && cell_hole_pitch <= 14, "Recheck slots/spacer outside this pitch range.");
assert(cell_end_hole_offset >= 3 && cell_end_hole_offset <= 8, "Recheck edge clearance.");
assert(cell_bolt_clearance >= 3.2 && cell_bolt_clearance <= 4.8, "Recheck larger bolts.");
assert(fixed_center+cell_hole_pitch/2+cell_slot_travel/2+cell_bolt_clearance/2 < adapter_x+adapter_length-3,
       "Cell mounting slot too near adapter end.");
assert(cell_x+cell_length/2 >= adapter_x+adapter_length+0.5,
       "Adapter would support the active cell region: redesign before use.");

function chord(x) = root_chord+(tip_chord-root_chord)*max(0,(x-root_length))/(wing_span-root_length);
function rib_profile(c) = [
    [-c/2,0], [c/2,0], [c/2,1.6], [c*0.43,2.6],
    [c*0.34,spar_outer+0.15], [-c*0.34,spar_outer+0.15],
    [-c*0.44,3], [-c/2,1.6]
];

module bore_z(x,y,d,h,z=-eps) {
    translate([x,y,z]) cylinder(d=d,h=h+2*eps);
}

module slot_z(x,y,travel,d,h,z=-eps) {
    hull() for (dx=[-travel/2,travel/2]) bore_z(x+dx,y,d,h,z);
}

module hex_z(x,y,af,h,z=-eps) {
    translate([x,y,z]) rotate([0,0,30]) cylinder(d=af/cos(30),h=h+eps,$fn=6);
}

module rib(x) {
    // Local polygon x -> global chord, local y -> global height.
    translate([x,0,0]) rotate([90,0,90])
        linear_extrude(height=rib_width) polygon(rib_profile(chord(x+rib_width)-0.4));
}

module wing() {
    difference() {
        union() {
            translate([0,-root_chord/2,0]) cube([root_length,root_chord,root_thickness]);
            // The open ribs keep the bamboo accessible and reduce printed stiffness.
            for (y=[-spar_y,spar_y]) {
                translate([root_length-eps,y,spar_z]) rotate([0,90,0])
                    cylinder(d=spar_outer,h=wing_span-root_length+eps);
                // Flat print foot below each tube, joined into its lower arc.
                translate([root_length-eps,y-2,0]) cube([wing_span-root_length+eps,4,1.2]);
            }
            translate([root_length-eps,-gauge_beam_width/2,0])
                cube([wing_span-root_length+eps,gauge_beam_width,gauge_beam_thickness]);
            for (side=[-1,1]) linear_extrude(height=2.4) polygon([
                [root_length,side*root_chord/2],
                [wing_span,side*tip_chord/2],
                [wing_span,side*(tip_chord/2-3)],
                [root_length,side*(root_chord/2-3)]
            ]);
            for (x=[root_length+4:rib_pitch:wing_span-4]) rib(x);
            // Solid end landing transfers the load into both spars and all ribs.
            translate([wing_span-tip_pad_length,-26,0]) cube([tip_pad_length,52,tip_z]);
            // Flat, generic MPU board pad; strap through its four small slots.
            translate([74,-11,0]) cube([24,22,gauge_beam_thickness]);
        }
        for (y=[-spar_y,spar_y]) translate([-eps,y,spar_z]) rotate([0,90,0])
            cylinder(d=spar_bore,h=wing_span-spar_blind_end+eps);
        // Registration holes in the clamped root, not the strain-gauge beam.
        for (y=[-8,8]) bore_z(8,y,m3_clearance,root_thickness);
        for (x=[wing_span-12,wing_span-4],y=[-10,10]) bore_z(x,y,m3_clearance,tip_z);
        for (x=[78,94],y=[-7,7]) slot_z(x,y,1,2.2,gauge_beam_thickness);
    }
}

module root_base() {
    difference() {
        union() {
            translate([-82,-50,0]) cube([110,100,base_height]);
            translate([-4,-49,base_height]) cube([30,98,jaw_height]);
            for (y=[-8,8]) translate([8,y,base_height+jaw_height-eps]) cylinder(d=3,h=2+eps);
        }
        for (x=[3,20],y=[-43,43]) {
            bore_z(x,y,m4_clearance,base_height+jaw_height);
            hex_z(x,y,m4_nut_af,m4_nut_depth);
        }
        for (y=[-32,32]) slot_z(-58,y,20,bench_bolt_clearance,base_height);
    }
}

module root_cap() {
    difference() {
        translate([-4,-49,0]) cube([30,98,cap_height]);
        for (x=[3,20],y=[-43,43]) bore_z(x,y,m4_clearance,cap_height);
        // Roof chamfers leave the bottom clamping face completely flat.
        for (y=[-49,49]) translate([-5,y,cap_height]) rotate([45,0,0]) cube([32,2,2],center=true);
    }
}

module tip_adapter() {
    difference() {
        translate([0,-16,0]) cube([adapter_length,32,6]);
        for (x=[4,12],y=[-10,10]) bore_z(x,y,m3_clearance,6);
        for (x=[fixed_center-cell_hole_pitch/2,fixed_center+cell_hole_pitch/2])
            slot_z(x-adapter_x,0,cell_slot_travel,cell_bolt_clearance,6);
    }
}

module cell_block(hanger=false) {
    difference() {
        translate([-spacer_length/2,-spacer_width/2,0]) cube([spacer_length,spacer_width,cell_standoff]);
        for (x=[-cell_hole_pitch/2,cell_hole_pitch/2]) bore_z(x,0,cell_bolt_clearance,cell_standoff);
        if(hanger) translate([0,-spacer_width/2-eps,cell_standoff/2]) rotate([-90,0,0])
            cylinder(d=3.5,h=spacer_width+2*eps);
    }
}

module spar_fit_coupon() {
    diameters=[4.1,4.3,4.4,4.5,4.7];
    difference() {
        cube([24,60,8]);
        for (i=[0:len(diameters)-1]) {
            translate([-eps,6+i*12,3.5]) rotate([0,90,0]) cylinder(d=diameters[i],h=24+2*eps);
            translate([12,6+i*12,7.4]) linear_extrude(height=1)
                text(str(diameters[i]),size=3,halign="center",valign="center",font="Liberation Sans");
        }
    }
}

module reference_cell() {
    // VISUAL PLACEHOLDER ONLY. Threaded holes are schematic clear bores.
    difference() {
        translate([cell_x,-cell_width/2,0]) cube([cell_length,cell_width,cell_height]);
        for (x=[fixed_center-cell_hole_pitch/2,fixed_center+cell_hole_pitch/2,
                loaded_center-cell_hole_pitch/2,loaded_center+cell_hole_pitch/2])
            bore_z(x,0,cell_bolt_clearance,cell_height);
        // Schematic active region: its dimensions are not a sensor specification.
        for (x=[cell_x+cell_length/2-5,cell_x+cell_length/2+5])
            translate([x,-cell_width/2-eps,cell_height/2]) rotate([-90,0,0]) cylinder(d=6,h=cell_width+2*eps);
    }
}

module assembly(explode=0) {
    color("#45494d") root_base();
    color("#d8dcde") translate([0,0,wing_assembly_z+explode*12]) wing();
    color("#45494d") translate([0,0,wing_assembly_z+root_thickness+explode*40]) root_cap();
    color("#7d858c") translate([adapter_x,0,wing_assembly_z+tip_z+explode*30]) tip_adapter();
    color("#525b61") translate([fixed_center,0,wing_assembly_z+tip_z+6+explode*45]) cell_block();
    color("#525b61") translate([loaded_center,0,wing_assembly_z+tip_z+6+explode*45]) cell_block(true);
    if(show_spars) color("#c3a36c") for(y=[-spar_y,spar_y])
        translate([-spar_grip,y,wing_assembly_z+spar_z+explode*12]) rotate([0,90,0])
            cylinder(d=spar_nominal_diameter,h=wing_span-spar_blind_end+spar_grip);
    if(show_reference_hardware) {
        color("#b1b8bf") translate([0,0,wing_assembly_z+tip_z+6+cell_standoff+explode*60]) reference_cell();
        // Board and gauge are visual envelopes, not mounting specifications.
        color("#3a6656") translate([75,-10,wing_assembly_z+gauge_beam_thickness+explode*22]) cube([22,20,1.6]);
        color("#c18b4c") translate([33,-3,wing_assembly_z+gauge_beam_thickness+explode*12]) cube([10,6,0.2]);
        if(explode==0) {
            color("#6d7075") translate([loaded_center,0,-35]) cylinder(d=1.5,h=wing_assembly_z+tip_z+6+cell_standoff/2+35);
            color("#999da1") translate([loaded_center,0,-40]) cylinder(d=25,h=5);
        }
    }
}

if(part=="assembly") assembly();
else if(part=="exploded") assembly(1);
else if(part=="spar_section") {
    color("#d8dcde") difference() {
        wing();
        translate([-eps,-root_chord,spar_z]) cube([wing_span+2*eps,2*root_chord,20]);
    }
    color("#c3a36c") for(y=[-spar_y,spar_y]) translate([-spar_grip,y,spar_z]) rotate([0,90,0])
        cylinder(d=spar_nominal_diameter,h=wing_span-spar_blind_end+spar_grip);
}
else if(part=="wing") color("#d8dcde") wing();
else if(part=="root_base") color("#45494d") root_base();
else if(part=="root_cap") color("#45494d") root_cap();
else if(part=="tip_adapter") color("#7d858c") tip_adapter();
else if(part=="cell_spacer") color("#525b61") cell_block();
else if(part=="load_hanger") color("#525b61") cell_block(true);
else if(part=="spar_fit_coupon") color("#d8dcde") spar_fit_coupon();
else assert(false,str("Unknown part: ",part));
