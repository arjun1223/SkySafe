"""Run inside Fusion's Scripts manager. No mesh imports or cloud saves.

Creates a NEW document, native components/sketches/extrusions, local archives
and print meshes. Sketch layout coordinates are fixed; named bore diameters
and selected feature thicknesses are driven by user parameters.
"""
import os
import math
import json
import traceback
import hashlib
import adsk
import adsk.core as C
import adsk.fusion as F

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = {"status": "RUNNING", "parts": [], "feature_checks": [], "exports": {},
          "limitations": ["Rectangular bar cells only; reference sensor dimensions unmeasured", "Hot glue attachment has no validated strength or creep performance", "No physical fit/strength validation",
                          "Layout sketch coordinates are fixed; edit sketches or rebuild for layout changes"]}
PARTS = []
PARAMETRIC_CIRCLES = []
PARAMETRIC_DIAMONDS = []

def record():
    with open(os.path.join(OUT, "native_build_report.json"), "w") as f:
        json.dump(REPORT, f, indent=2)

def p(x,y,z=0):
    return C.Point3D.create(x/10,y/10,z/10)

def val(expr):
    return C.ValueInput.createByString(str(expr)+" mm" if isinstance(expr,(int,float)) else expr)

def plane(comp,axis,offset):
    source={"XY":comp.xYConstructionPlane,"YZ":comp.yZConstructionPlane,"XZ":comp.xZConstructionPlane}[axis]
    if abs(offset)<1e-9:
        return source
    inp=comp.constructionPlanes.createInput()
    inp.setByOffset(source,val(offset))
    result=comp.constructionPlanes.add(inp)
    result.name=f"{axis} datum {offset:g} mm"
    result.isLightBulbOn=False
    return result

def sketch(comp,name,axis="XY",offset=0):
    result=comp.sketches.add(plane(comp,axis,offset))
    result.name=name
    return result

def polygon(sk,coords):
    points=[sk.modelToSketchSpace(p(*pt)) for pt in coords]
    for a,b in zip(points,points[1:]+points[:1]):
        sk.sketchCurves.sketchLines.addByTwoPoints(a,b)
    for curve in sk.sketchCurves:
        try:
            curve.isFixed=True
        except RuntimeError:
            # Coincidence/inferred constraints can already fix an adjacent edge.
            pass

def circle(sk,center,diameter,expression=None):
    point=sk.modelToSketchSpace(p(*center))
    curve=sk.sketchCurves.sketchCircles.addByCenterRadius(point,diameter/20)
    if expression:
        curve.centerSketchPoint.isFixed=True
        dim=sk.sketchDimensions.addDiameterDimension(curve,C.Point3D.create(point.x+.4,point.y+.4,0))
        dim.parameter.expression=expression
        PARAMETRIC_CIRCLES.append((curve,expression))
    else:
        curve.isFixed=True
    return curve

def extrude(comp,sk,distance,name,operation,profile=None,symmetric=False):
    if profile is None:
        if sk.profiles.count!=1:
            raise RuntimeError(f"{name}: expected 1 closed profile, found {sk.profiles.count}")
        profile=sk.profiles.item(0)
    inp=comp.features.extrudeFeatures.createInput(profile,operation)
    if symmetric:
        inp.setSymmetricExtent(val(distance),True)
    else:
        inp.setOneSideExtent(F.DistanceExtentDefinition.create(val(distance)),F.ExtentDirections.PositiveExtentDirection)
    if operation==F.FeatureOperations.CutFeatureOperation:
        inp.participantBodies=[b for b in comp.bRepBodies]
    result=comp.features.extrudeFeatures.add(inp)
    result.name=name
    sk.isLightBulbOn=False
    REPORT["phase"]=name
    record()
    return result

NEW=F.FeatureOperations.NewBodyFeatureOperation
JOIN=F.FeatureOperations.JoinFeatureOperation
CUT=F.FeatureOperations.CutFeatureOperation

def box(comp,name,x,y,z,l,w,h,operation=JOIN):
    sk=sketch(comp,name+" sketch",offset=z)
    polygon(sk,[(x,y,z),(x+l,y,z),(x+l,y+w,z),(x,y+w,z)])
    return extrude(comp,sk,h,name,operation)

def poly_xy(comp,name,coords,height,operation=JOIN,z=0):
    sk=sketch(comp,name+" sketch",offset=z)
    polygon(sk,[(x,y,z) for x,y in coords])
    return extrude(comp,sk,height,name,operation)

def hole_z(comp,name,x,y,diameter,height,expression=None,z=-.05):
    sk=sketch(comp,name+" sketch",offset=z)
    circle(sk,(x,y,z),diameter,expression)
    return extrude(comp,sk,height+.1,name,CUT)

def cylinder_x(comp,name,x,y,z,diameter,length,operation,expression=None):
    sk=sketch(comp,name+" sketch","YZ",x)
    circle(sk,(x,y,z),diameter,expression)
    return extrude(comp,sk,length,name,operation)

def diamond_x(comp,name,x,y,z,flat_width,length,operation,expression=None):
    sk=sketch(comp,name+" sketch","YZ",x)
    r=flat_width/math.sqrt(2)
    coords=[(x,y-r,z),(x,y,z-r),(x,y+r,z),(x,y,z+r)]
    if not expression:
        polygon(sk,coords)
    else:
        points=[sk.sketchPoints.add(sk.modelToSketchSpace(p(*pt))) for pt in coords]
        for a,b in zip(points,points[1:]+points[:1]):
            sk.sketchCurves.sketchLines.addByTwoPoints(a,b)
        diag1=sk.sketchCurves.sketchLines.addByTwoPoints(points[0],points[2])
        diag2=sk.sketchCurves.sketchLines.addByTwoPoints(points[1],points[3])
        diag1.isConstruction=True
        diag2.isConstruction=True
        for line in [diag1,diag2]:
            a=line.startSketchPoint.geometry
            b=line.endSketchPoint.geometry
            try:
                if abs(a.x-b.x)>abs(a.y-b.y): sk.geometricConstraints.addHorizontal(line)
                else: sk.geometricConstraints.addVertical(line)
            except RuntimeError:
                pass # Fusion can infer the same axis constraint on line creation.
        center=sk.sketchPoints.add(sk.modelToSketchSpace(p(x,y,z)))
        center.isFixed=True
        sk.geometricConstraints.addMidPoint(center,diag1)
        sk.geometricConstraints.addMidPoint(center,diag2)
        sk.geometricConstraints.addEqual(diag1,diag2)
        dim=sk.sketchDimensions.addDistanceDimension(points[1],points[3],F.DimensionOrientations.AlignedDimensionOrientation,C.Point3D.create(.6,.6,0))
        dim.parameter.expression=expression+" * sqrt(2)"
        PARAMETRIC_DIAMONDS.append(diag1)
    return extrude(comp,sk,length,name,operation)

def slot(comp,name,x,y,travel,diameter,height,z=-.05):
    sk=sketch(comp,name+" sketch",offset=z)
    r=diameter/2
    a=x-travel/2
    b=x+travel/2
    at=lambda x,y:sk.modelToSketchSpace(p(x,y,z))
    sk.sketchCurves.sketchArcs.addByThreePoints(at(a,y-r),at(a-r,y),at(a,y+r))
    sk.sketchCurves.sketchLines.addByTwoPoints(at(a,y+r),at(b,y+r))
    sk.sketchCurves.sketchArcs.addByThreePoints(at(b,y+r),at(b+r,y),at(b,y-r))
    sk.sketchCurves.sketchLines.addByTwoPoints(at(b,y-r),at(a,y-r))
    for curve in sk.sketchCurves:
        try:
            curve.isFixed=True
        except RuntimeError:
            pass
    return extrude(comp,sk,height+.1,name,CUT)

def component(root,key,name):
    occ=root.occurrences.addNewComponent(C.Matrix3D.create())
    comp=occ.component
    comp.name=name
    comp.attributes.add("SkySafe","print_key",key)
    PARTS.append((key,occ,comp))
    return comp

def engraved_label(comp,diameter,y):
    # Small straight-segment numerals avoid font-dependent text profiles.
    segments={"a":(0,2.7,1.8,.3),"b":(1.5,1.65,.3,.9),"c":(1.5,.45,.3,.9),
              "d":(0,0,1.8,.3),"e":(0,.45,.3,.9),"f":(0,1.65,.3,.9),"g":(0,1.35,1.8,.3)}
    digits={"1":"bc","3":"abgcd","4":"fgbc","5":"afgcd","7":"abc"}
    for index,char in enumerate(f"{diameter:.1f}"):
        if char==".":
            box(comp,f"Label {diameter:.1f} dot",8+index*2.5,y-1.5,9.4,.35,.35,1,CUT)
        else:
            for segment in digits[char]:
                x0,y0,w,h=segments[segment]
                box(comp,f"Label {diameter:.1f} digit {index} {segment}",8+index*2.5+x0,y-1.5+y0,9.4,w,h,1,CUT)

def appearance(design,name,rgb):
    for lib in C.Application.get().materialLibraries:
        try:
            source=lib.appearances.itemByName("Plastic - Matte (White)")
        except RuntimeError:
            continue
        if source:
            app=design.appearances.addByCopy(source,name)
            color=C.ColorProperty.cast(app.appearanceProperties.itemById("opaque_albedo"))
            if color:
                color.value=C.Color.create(*rgb,255)
            return app
    return None

def check_features(design):
    errors=[]
    for comp in design.allComponents:
        for feat in comp.features.extrudeFeatures:
            okay=feat.healthState==F.FeatureHealthStates.HealthyFeatureHealthState
            REPORT["feature_checks"].append({"component":comp.name,"feature":feat.name,"healthy":okay,
                                              "message":feat.errorOrWarningMessage})
            if not okay:
                errors.append(feat.name)
    if errors:
        raise RuntimeError("Nonhealthy native features: "+", ".join(errors))

def camera(app,path,target,eye,extent):
    cam=app.activeViewport.camera
    cam.cameraType=C.CameraTypes.OrthographicCameraType
    cam.target=p(*target)
    cam.eye=p(*eye)
    cam.upVector=C.Vector3D.create(0,0,1)
    cam.isFitView=False
    cam.viewExtents=extent
    app.activeViewport.camera=cam
    app.activeViewport.refresh()
    adsk.doEvents()
    if not app.activeViewport.saveAsImageFile(path,1600,1000):
        raise RuntimeError("Fusion preview export failed")

def run(context):
    app=C.Application.get()
    ui=app.userInterface
    try:
        PARTS.clear()
        PARAMETRIC_CIRCLES.clear()
        PARAMETRIC_DIAMONDS.clear()
        REPORT.update(status="RUNNING",parts=[],feature_checks=[],exports={})
        for sub in ("stl","step","previews"):
            os.makedirs(os.path.join(OUT,sub),exist_ok=True)
        record()
        doc=app.documents.add(C.DocumentTypes.FusionDesignDocumentType)
        doc.name="SkySafe - 14 inch modular bamboo wing"
        design=F.Design.cast(app.activeProduct)
        design.designType=F.DesignTypes.ParametricDesignType
        design.unitsManager.distanceDisplayUnits=F.DistanceUnits.MillimeterDistanceUnits
        root=design.rootComponent
        for name,expr,comment in [
            ("sparDiameter","4 mm","Nominal bamboo diameter; choose clearance with fit coupon"),
            ("sparClearance","0.5 mm","Diametral clearance; 4.5 mm coupon fit selected by user"),
            ("sparBore","sparDiameter + sparClearance","Flat-to-flat width of all six native diamond passages"),
            ("m3Clearance","3.4 mm","Root registration and tip adapter holes"),
            ("m4Clearance","4.4 mm","Root clamp bolt holes"),
            ("rootThickness","10 mm","Root tongue extrusion; reposition cap if changed"),
            ("gaugeBeamThickness","1.8 mm","Root gauge zone; physical response needs testing"),
            ("spanStripThickness","2.4 mm","Middle, tip and reinforced joint-end thickness"),
            ("mpuPadThickness","7.2 mm","Raised pad clears the 6.95 mm rib tops")]:
            design.userParameters.add(name,val(expr),"mm",comment)
        # Three flat-printable sections; two bolted butt joints are outside the gauge zone.
        lengths={"wing_root":128.0,"wing_middle":114.0,"wing_tip":114.0}
        origins={"wing_root":0.0,"wing_middle":128.2,"wing_tip":242.4}
        for key in lengths:
            length=lengths[key]
            part=component(root,key,{"wing_root":"01A Wing root - gauge and MPU", "wing_middle":"01B Wing middle", "wing_tip":"01C Wing tip - load adapter"}[key])
            strip_start=23.95 if key=="wing_root" else 0
            box(part,"Continuous connecting strip",strip_start,-6,0,length-strip_start,12,"gaugeBeamThickness" if key=="wing_root" else "spanStripThickness",NEW)
            if key=="wing_root":
                box(part,"Root tongue",0,-36,0,24,72,"rootThickness")
                box(part,"Reinforced strip beyond gauge",48,-6,0,80,12,"spanStripThickness")
                sk=sketch(part,"Root gauge shoulder sketch","XZ")
                polygon(sk,[(23.95,0,0),(32,0,0),(32,0,1.8),(23.95,0,4)])
                extrude(part,sk,12,"Root tapered gauge shoulder",JOIN,symmetric=True)
                rib_x=(28,48,68,88,108)
            else:
                rib_x=(16,38,60,82,96) if key=="wing_middle" else (16,38,60,82)
            for x in rib_x:
                global_x=origins[key]+x
                chord=72-10*global_x/356.4
                yz=[(-chord/2,0),(chord/2,0),(chord/2,1.6),(.43*chord,2.6),(.34*chord,6.95),(-.34*chord,6.95),(-.44*chord,3),(-chord/2,1.6)]
                sk=sketch(part,f"Rib at {x} mm sketch","YZ",x)
                polygon(sk,[(x,y,z) for y,z in yz])
                extrude(part,sk,2.4,f"Rib at {x} mm",JOIN)
                for side,y in (("front",-18),("rear",18)):
                    cylinder_x(part,f"{side} short guide at {x} mm",x-2,y,4.5,9,6,JOIN)
                    box(part,f"{side} guide foot at {x} mm",x-2,y-3.3,0,6,6.6,1.4)
            # Each seam has reinforced flat ends sandwiched by separate plates.
            joint_ends=[]
            if key!="wing_root": joint_ends.append((0,6))
            if key!="wing_tip": joint_ends.append((length-12,length-6))
            for begin,bolt_x in joint_ends:
                box(part,f"Joint landing at {begin}",begin,-10,0,12,20,"spanStripThickness")
                hole_z(part,f"Joint bolt at {bolt_x}",bolt_x,0,3.4,2.4,"m3Clearance")
            if key=="wing_root":
                box(part,"MPU strap landing",74,-11,0,24,22,"mpuPadThickness")
                for y in (-8,8): hole_z(part,f"Root registration {y}",8,y,3.4,10,"m3Clearance")
                for x in (78,94):
                    for y in (-7,7): slot(part,f"Board tie {x} {y}",x,y,1,2.2,7.2)
            if key=="wing_tip":
                box(part,"Tip adapter landing",98,-26,0,16,52,9)
                sk=sketch(part,"Tip strip shoulder sketch","XZ")
                polygon(sk,[(90,0,0),(98.05,0,0),(98.05,0,9),(90,0,2.4)])
                extrude(part,sk,12,"Tip tapered strip shoulder",JOIN,symmetric=True)
                for x in (102,110):
                    for y in (-10,10): hole_z(part,f"Tip bolt {x} {y}",x,y,3.4,9,"m3Clearance")
            for side,y in (("front",-18),("rear",18)):
                diamond_x(part,side+" diamond bamboo passage",-.05,y,4.5,4.5,length-1.95 if key=="wing_tip" else length+.1,CUT,"sparBore")
        plate=component(root,"joint_plate","07 Joint sandwich plate - print FOUR")
        box(plate,"Flat joint plate",0,-10,0,24.2,20,2,NEW)
        for x in (6,18.2): hole_z(plate,f"Seam bolt {x}",x,0,3.4,2,"m3Clearance")

        base=component(root,"root_base","02 Root base - bench clamp")
        box(base,"Bench mounting plate",-82,-50,0,110,100,8,NEW)
        box(base,"Lower root jaw",-4,-49,8,30,98,8)
        for y in (-8,8):
            sk=sketch(base,f"Root pin {y} sketch",offset=15.95)
            circle(sk,(8,y,15.95),3)
            extrude(base,sk,2.05,f"Root pin {y}",JOIN)
        for x in (3,20):
            for y in (-43,43):
                hole_z(base,f"Jaw bolt {x} {y}",x,y,4.4,16,"m4Clearance")
                r=7.1/(2*math.cos(math.pi/6))
                poly_xy(base,f"Nut pocket {x} {y}",[(x+r*math.cos(math.radians(30+60*i)),y+r*math.sin(math.radians(30+60*i))) for i in range(6)],3.35,CUT,-.05)
        for y in (-32,32):
            slot(base,f"Bench slot {y}",-58,y,20,6.6,8)

        cap=component(root,"root_cap","03 Root cap")
        box(cap,"Upper root jaw",-4,-49,0,30,98,8,NEW)
        for x in (3,20):
            for y in (-43,43):
                hole_z(cap,f"Cap bolt {x} {y}",x,y,4.4,8,"m4Clearance")

        adapter=component(root,"tip_adapter","04 Tip adapter - adjustable glue mount rails")
        box(adapter,"Adapter plate",0,-19,0,90,38,6,NEW)
        for x in (4,12):
            for y in (-10,10):
                hole_z(adapter,f"Wing adapter bolt {x} {y}",x,y,3.4,6,"m3Clearance")
        for y in (-11,11):
            slot(adapter,f"Fixed mount sliding rail {y}",50,y,52,3.4,6)
        for key,name in (("cell_spacer","05 Fixed end glue pedestal"),("load_hanger","06 Free end glue hanger")):
            comp=component(root,key,name)
            height=20 if key=="cell_spacer" else 10
            box(comp,"Glue carrier body",-13,-17,0,26,34,height,NEW)
            box(comp,"END ONLY 10x24 glue landing",-5,-12,height-.05,10,24,1.25)
            for x in (-3,0,3):
                box(comp,f"Shallow glue key groove {x}",x-.4,-10,height+.7,.8,20,.6,CUT)
            for y in (-13.5,13.5):
                slot(comp,f"Optional tie return slot {y}",0,y,2,2.4,height)
            if key=="cell_spacer":
                # These secure the printed pedestal to its rails, never the sensor.
                for x in (-9,9):
                    for y in (-11,11):
                        hole_z(comp,f"Pedestal rail bolt {x} {y}",x,y,3.4,height,"m3Clearance")
            if key=="load_hanger":
                sk=sketch(comp,"Transverse cord hole sketch","XZ")
                circle(sk,(0,0,5),3.5)
                extrude(comp,sk,34.1,"Transverse cord hole",CUT,symmetric=True)

        coupon=component(root,"spar_fit_coupon","07 Spar fit coupon - 4.1 4.3 4.4 4.5 4.7")
        box(coupon,"Fit block",0,0,0,24,60,10,NEW)
        for i,d in enumerate((4.1,4.3,4.4,4.5,4.7)):
            diamond_x(coupon,f"Diamond {d:.1f} mm flat-width fit bore",-.05,6+12*i,4.5,d,24.1,CUT)
            engraved_label(coupon,d,6+12*i)

        design.computeAll()
        # Verify the diameter expression edits real geometry in both passages.
        trial=[]
        clearance=design.userParameters.itemByName("sparClearance")
        for expr,expected in (("0.4 mm",4.4),("0.5 mm",4.5)):
            clearance.expression=expr
            design.computeAll()
            values=[round(line.startSketchPoint.geometry.distanceTo(line.endSketchPoint.geometry)*10/math.sqrt(2),6) for line in PARAMETRIC_DIAMONDS]
            assert len(values)==6 and all(abs(d-expected)<1e-5 for d in values),(expr,values)
            trial.append({"clearance":expr,"measured_channel_diameters_mm":values})
        REPORT["spar_parameter_trial"]=trial
        REPORT["selected_spar_bore_mm"]=4.5
        REPORT["modular_wing"]={"revision":"14inch-three-section-v1","assembled_span_mm":356.4,
            "assembled_span_inches":356.4/25.4,"section_lengths_mm":lengths,"section_origins_x_mm":origins,
            "joint_gap_mm":0.2,"joint_plate_dimensions_mm":[24.2,20,2],"joint_plate_quantity":4,
            "joint_plate_origins_x_mm":[116.0,230.2],"joint_bolt_global_x_mm":[122,134.2,236.2,248.4],
            "gauge_flat_region_mm":[32,48,12,1.8],"other_span_strip_thickness_mm":2.4,
            "spar_bore_flat_to_flat_mm":4.5,"spar_bore_shape":"diamond","spar_center_height_mm":4.5,"guide_outer_diameter_mm":9,"spar_cut_length_mm":361,"continuous_spars_required":True,
            "force_lever_arm_mm":399.4,"physical_self_weight_and_elastic_range_verified":False}
        check_features(design)
        styles={"light":appearance(design,"SkySafe white",(211,216,219)),"dark":appearance(design,"SkySafe graphite",(62,67,71)),
                "wood":appearance(design,"SkySafe bamboo reference",(193,157,91))}
        exporter=design.exportManager
        for key,occ,comp in PARTS:
            if comp.bRepBodies.count!=1 or comp.meshBodies.count:
                raise RuntimeError(key+": expected exactly one native solid and no meshes")
            body=comp.bRepBodies.item(0)
            body.name=key+" - printable solid"
            if styles["dark" if key in ("root_base","root_cap") else "light"]:
                body.appearance=styles["dark" if key in ("root_base","root_cap") else "light"]
            bb=body.boundingBox
            size=[(getattr(bb.maxPoint,a)-getattr(bb.minPoint,a))*10 for a in ("x","y","z")]
            assert body.isSolid and all(d<=140.001 for d in size) and all(d<=132.001 for d in size[:2])
            assert abs(bb.minPoint.z)<1e-6
            REPORT["parts"].append({"part":key,"native_solids":1,"mesh_bodies":0,"dimensions_mm":size,
                                   "volume_mm3":body.volume*1000,"sketches":comp.sketches.count,
                                   "extrude_features":comp.features.extrudeFeatures.count})
            stl=exporter.createSTLExportOptions(body,os.path.join(OUT,"stl",key+".stl"))
            stl.unitType=F.DistanceUnits.MillimeterDistanceUnits
            stl.meshRefinement=F.MeshRefinementSettings.MeshRefinementHigh
            assert exporter.execute(stl)
            assert exporter.execute(exporter.createSTEPExportOptions(os.path.join(OUT,"step",key+".step"),comp))
            assert exporter.execute(exporter.createFusionArchiveExportOptions(os.path.join(OUT,key+".f3d"),comp))
        # Export a native print layout before positioning the assembled occurrences.
        print_layout=exporter.createFusionArchiveExportOptions(os.path.join(OUT,"SkySafe_PrintParts.f3d"))
        assert exporter.execute(print_layout)
        positions={"wing_root":(0,0,16),"wing_middle":(128.2,0,16),"wing_tip":(242.4,0,16),
            "root_base":(0,0,0),"root_cap":(0,0,26),"tip_adapter":(340.4,0,25),
            "cell_spacer":(373.4,0,31),"load_hanger":(423.4,0,41),"spar_fit_coupon":(-65,85,0),
            "joint_plate":(116,0,14)}
        for key,occ,comp in PARTS:
            matrix=C.Matrix3D.create()
            matrix.translation=C.Vector3D.create(*(x/10 for x in positions[key]))
            occ.isGrounded=False
            occ.isGroundToParent=False
            occ.transform2=matrix
            if key=="spar_fit_coupon":
                occ.isLightBulbOn=False
        # Reuse the same native plate component for the other three seam plates.
        for xyz in [(116,0,18.4),(230.2,0,14),(230.2,0,18.4)]:
            matrix=C.Matrix3D.create()
            matrix.translation=C.Vector3D.create(*(v/10 for v in xyz))
            extra=root.occurrences.addExistingComponent(plate,C.Matrix3D.create())
            extra.isGrounded=False
            extra.isGroundToParent=False
            extra.transform2=matrix
        if design.snapshots.hasPendingSnapshot:
            design.snapshots.add()
        # Separate reference-only component, natively modeled but never in print exports.
        ref=root.occurrences.addNewComponent(C.Matrix3D.create()).component
        ref.name="REFERENCE ONLY - bamboo, example bar cell, sensor envelopes"
        # Half a millimeter is reserved for glue at each isolated end landing.
        box(ref,"EXAMPLE 60mm bar cell - no assumed screw pattern",368.4,-6.35,52.7,60,12.7,12.7,NEW)
        REPORT["glue_mount"]={"landing_mm":[10,24],"groove_depth_mm":0.5,
                              "reference_glue_gap_mm":0.5,"reference_cell_mm":[60,12.7,12.7],
                              "reference_free_middle_length_mm":40,"hanger_plate_clearance_mm":10,
                              "sensor_screws_required":False,"force_lever_arm_mm":399.4}
        for y in (-18,18):
            feat=cylinder_x(ref,f"4mm bamboo reference {y}",-6.6,y,20.5,4,361,NEW)
            if styles["wood"]:
                feat.bodies.item(0).appearance=styles["wood"]
        box(ref,"MPU board envelope",75,-10,23.2,22,20,1.6,NEW)
        box(ref,"Gauge backing envelope",33,-3,17.8,10,6,.2,NEW)
        # Hide all construction/sketch geometry for a clear handoff.
        for comp in design.allComponents:
            comp.isOriginFolderLightBulbOn=False
            comp.isSketchFolderLightBulbOn=False
            comp.isConstructionFolderLightBulbOn=False
        design.computeAll()
        entities=C.ObjectCollection.create()
        REPORT["assembly_positions_mm"]={occ.name:[x*10 for x in occ.transform2.translation.asArray()] for occ in root.occurrences}
        for occ in root.occurrences:
            tag=occ.component.attributes.itemByName("SkySafe","print_key")
            if not tag or tag.value!="spar_fit_coupon":
                entities.add(occ)
        interference=design.analyzeInterference(design.createInterferenceInput(entities))
        assert interference is not None
        overlaps=[{"volume_mm3":result.interferenceBody.volume*1000,
                   "entity_one":getattr(result.entityOne,"name",str(result.entityOne)),
                   "entity_two":getattr(result.entityTwo,"name",str(result.entityTwo))} for result in interference
                  if result.interferenceBody and result.interferenceBody.volume>1e-7]
        REPORT["assembled_interference"]={"coincident_faces_excluded":True,"overlaps":overlaps,"passed":not overlaps}
        record()
        assert not overlaps,"Assembly contains overlapping solid volumes"
        assembly=os.path.join(OUT,"SkySafe_Assembly.f3d")
        assert exporter.execute(exporter.createFusionArchiveExportOptions(assembly))
        assert exporter.execute(exporter.createSTEPExportOptions(os.path.join(OUT,"SkySafe_Assembly.step")))
        REPORT["exports"]={"assembly_f3d":assembly,"print_parts_f3d":os.path.join(OUT,"SkySafe_PrintParts.f3d"),
                           "separate_parts":10,"stl_parts":10,"step_parts":10}
        REPORT["source_sha256"]=hashlib.sha256(open(__file__,"rb").read()).hexdigest()
        # Reopen the local archive to verify the deliverable retains native history.
        reopened=app.importManager.importToNewDocument(app.importManager.createFusionArchiveImportOptions(assembly))
        assert reopened
        design=F.Design.cast(app.activeProduct)
        design.computeAll()
        assert abs(design.userParameters.itemByName("sparBore").value*10-4.5)<1e-5
        assert abs(design.userParameters.itemByName("gaugeBeamThickness").value*10-1.8)<1e-5
        checks=[]
        for comp in design.allComponents:
            if comp.attributes.itemByName("SkySafe","print_key"):
                checks.append({"component":comp.name,"solids":comp.bRepBodies.count,"meshes":comp.meshBodies.count,
                               "sketches":comp.sketches.count,"features":comp.features.extrudeFeatures.count})
                assert comp.bRepBodies.count==1 and comp.meshBodies.count==0 and comp.sketches.count>0
        assert len(checks)==10 and design.timeline.count>0
        REPORT["archive_readback"]={"passed":True,"timeline_items":design.timeline.count,"parts":checks}
        check_features(design)
        camera(app,os.path.join(OUT,"previews","fusion_assembly.png"),(180,0,17),(540,-560,410),55)
        REPORT["status"]="PASS - native solids and feature history; physical validation pending"
        record()
        ui.messageBox("SkySafe 14-inch Fusion build complete. Native F3D, STEP, STL and verification files saved in:\n"+OUT)
    except:
        REPORT["status"]="ERROR"
        REPORT["error"]=traceback.format_exc()
        record()
        ui.messageBox("SkySafe build stopped:\n"+REPORT["error"])
