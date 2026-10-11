"""Native Fusion stand: one new side-printed solid, original clamp cap reused."""
import os
import json
import math
import hashlib
import traceback
import importlib.util
import adsk.core as C
import adsk.fusion as F

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HELPER = os.path.abspath(os.path.join(OUT, '..', 'fusion_14inch', 'SkySafeFusion14', 'SkySafeFusion14.py'))
spec = importlib.util.spec_from_file_location('skysafe_geometry_helpers', HELPER)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
h.OUT = OUT
h.REPORT = R = {
    'status': 'RUNNING', 'parts': [], 'feature_checks': [], 'exports': {},
    'revision': 'laptop-foot-m3-v1', 'new_prints': 1,
    'assembled_dimensions_mm': [130, 110, 42],
    'deck_top_mm': 41, 'foot_thickness_mm': 3,
    'bolt_centers_assembly_mm': [[x,y] for x in (3,20) for y in (-43,43)],
    'bolt_hole_inscribed_diameter_mm': 3.4,
    'print_to_assembly': 'X=x, Y=55-z, Z=y (millimeters)',
    'fasteners': 'Four M3 x 25-30 mm; heads below deck, washers and nuts above reused cap',
    'reused_cap': '../fusion_14inch/root_cap.f3d',
    'limitations': ['No physical load rating or printed fit/strength validation',
                    'Only actual laptop-to-tab contact contributes anchoring force',
                    'No assumption that the full laptop weight loads the tab',
                    'Layout is fixed in sketches; reference wing is not printable wing geometry']
}

def diamond_bolt(comp, x, assembly_y):
    # Print Y is assembly Z. Use the native plane normal rather than assume
    # its orientation; symmetric cutting spans the full 6 mm deck thickness.
    z = 55 - assembly_y
    r = 3.4 / math.sqrt(2)
    normal_y=comp.xZConstructionPlane.geometry.normal.y
    assert abs(normal_y)>0.99
    sk = h.sketch(comp, 'M3 diamond clearance '+str((x,assembly_y)), 'XZ', 38/normal_y)
    h.polygon(sk, [(x-r,38,z),(x,38,z-r),(x+r,38,z),(x,38,z+r)])
    h.extrude(comp, sk, 6.1, 'Support-free M3 bore '+str((x,assembly_y)), h.CUT, symmetric=True)

def run(context):
    app=C.Application.get(); ui=app.userInterface
    try:
        for folder in ('stl','step','previews','verification'):
            os.makedirs(os.path.join(OUT,folder),exist_ok=True)
        h.PARTS.clear(); h.PARAMETRIC_CIRCLES.clear(); h.PARAMETRIC_DIAMONDS.clear()
        doc=app.documents.add(C.DocumentTypes.FusionDesignDocumentType)
        doc.name='SkySafe laptop foot stand - ONE new print'
        design=F.Design.cast(app.activeProduct)
        design.designType=F.DesignTypes.ParametricDesignType
        root=design.rootComponent
        design.userParameters.add('standWidth',C.ValueInput.createByString('110 mm'),'mm','Width along the wing chord')
        stand=h.component(root,'laptop_foot_stand','01 Laptop foot stand - PRINT ONE as exported')
        # Sketch X,Y are assembly X,Z. Extrusion is sideways across its width.
        # The whole stand sits on its side in the STL: no table-roof bridging.
        outline=[(-104,0),(26,0),(26,3),(-4,3),(-4,32),(-1,35),
                 (26,35),(26,41),(0,41),(0,42),(-1,42),
                 (-1,41),(-12,41),(-12,3),(-104,3)]
        h.poly_xy(stand,'Table deck, back wall, gusset and thin laptop foot',outline,'standWidth',h.NEW)
        for x in (3,20):
            for y in (-43,43): diamond_bolt(stand,x,y)
        cap=h.component(root,'REUSE_root_cap','02 Existing clamp cap - REUSE; do not print again')
        h.box(cap,'Original cap',-4,-49,0,30,98,8,h.NEW)
        for x in (3,20):
            for y in (-43,43): h.hole_z(cap,'Original cap clearance '+str((x,y)),x,y,4.4,8)
        h.check_features(design)
        assert stand.bRepBodies.count==1 and stand.meshBodies.count==0
        body=stand.bRepBodies.item(0); body.name='One native stand solid'
        bb=body.boundingBox
        dims=[(getattr(bb.maxPoint,a)-getattr(bb.minPoint,a))*10 for a in ('x','y','z')]
        assert body.isSolid and abs(bb.minPoint.z)<1e-7 and all(v<=132.001 for v in dims)
        R['parts'].append({'part':'laptop_foot_stand','dimensions_mm':dims,
                           'volume_mm3':body.volume*1000,'sketches':stand.sketches.count,
                           'native_solids':1,'mesh_bodies':0})
        export=design.exportManager
        stl=export.createSTLExportOptions(body,os.path.join(OUT,'stl','laptop_foot_stand.stl'))
        stl.unitType=F.DistanceUnits.MillimeterDistanceUnits
        stl.meshRefinement=F.MeshRefinementSettings.MeshRefinementHigh
        assert export.execute(stl)
        assert export.execute(export.createSTEPExportOptions(os.path.join(OUT,'step','laptop_foot_stand.step'),stand))
        assert export.execute(export.createFusionArchiveExportOptions(os.path.join(OUT,'laptop_foot_stand.f3d'),stand))
        for key,occ,comp in h.PARTS:
            transform=C.Matrix3D.create()
            if key=='laptop_foot_stand':
                transform.setToRotation(math.pi/2,C.Vector3D.create(1,0,0),C.Point3D.create(0,0,0))
                transform.translation=C.Vector3D.create(0,5.5,0)
            else:
                transform.translation=C.Vector3D.create(0,0,5.1)
            occ.isGrounded=False; occ.isGroundToParent=False; occ.transform2=transform
        if design.snapshots.hasPendingSnapshot: design.snapshots.add()
        ref_occ=root.occurrences.addNewComponent(C.Matrix3D.create())
        ref=ref_occ.component; ref.name='REFERENCE ONLY - existing wing root and bending span'
        h.box(ref,'Existing 24 x 72 x 10 mm root envelope',0,-36,41,24,72,10,h.NEW)
        for y in (-18,18): h.diamond_x(ref,'Existing skewer exit '+str(y),-.05,y,45.5,4.5,24.1,h.CUT)
        h.box(ref,'Unloaded wing center envelope',24,-6,41,332.4,12,1.8,h.JOIN)
        entities=C.ObjectCollection.create()
        for _,occ,_ in h.PARTS: entities.add(occ)
        entities.add(ref_occ)
        results=design.analyzeInterference(design.createInterferenceInput(entities))
        overlaps=[r.interferenceBody.volume*1000 for r in results if r.interferenceBody and r.interferenceBody.volume>1e-7]
        R['assembled_interference']={'passed':not overlaps,'overlap_volumes_mm3':overlaps}
        assert not overlaps,'Assembled components overlap'
        for comp in design.allComponents:
            comp.isOriginFolderLightBulbOn=False; comp.isSketchFolderLightBulbOn=False
            comp.isConstructionFolderLightBulbOn=False
        assembly=os.path.join(OUT,'SkySafe_Laptop_Stand.f3d')
        assert export.execute(export.createFusionArchiveExportOptions(assembly))
        assert export.execute(export.createSTEPExportOptions(os.path.join(OUT,'SkySafe_Laptop_Stand.step')))
        R['source_sha256']=hashlib.sha256(open(__file__,'rb').read()).hexdigest()
        R['helper_source_sha256']=hashlib.sha256(open(HELPER,'rb').read()).hexdigest()
        assert app.importManager.importToNewDocument(app.importManager.createFusionArchiveImportOptions(assembly))
        design=F.Design.cast(app.activeProduct); design.computeAll()
        assert design.timeline.count>0
        R['archive_readback']={'passed':True,'timeline_items':design.timeline.count,'components':[]}
        for comp in design.allComponents:
            tag=comp.attributes.itemByName('SkySafe','print_key')
            if tag:
                assert comp.bRepBodies.count==1 and comp.meshBodies.count==0 and comp.sketches.count>0
                R['archive_readback']['components'].append({'part':tag.value,'sketches':comp.sketches.count,
                    'solids':comp.bRepBodies.count,'meshes':comp.meshBodies.count})
        assert len(R['archive_readback']['components'])==2
        h.check_features(design)
        h.camera(app,os.path.join(OUT,'previews','stand_close.png'),(-30,0,25),(165,-220,160),23)
        h.camera(app,os.path.join(OUT,'previews','stand_with_wing.png'),(110,0,25),(340,-480,340),65)
        R['exports']={'assembly_f3d':assembly,'stl_parts':1,'step_parts':1}
        R['status']='PASS - native history and geometry; physical validation pending'
        h.record()
        ui.messageBox('Laptop stand exported: ONE new print. Reuse the existing cap.\n'+OUT)
    except:
        R['status']='ERROR'; R['error']=traceback.format_exc(); h.record()
        ui.messageBox('Laptop stand build stopped:\n'+R['error'])
