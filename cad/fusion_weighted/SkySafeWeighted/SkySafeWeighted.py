"""Native Fusion holder revision; exports three new printable designs.

Reuses the original CAD helpers and root-cap geometry. Existing wing and
sensor parts are not rebuilt or changed. Ballast is separate, unmodeled mass.
"""
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
h.REPORT = {
    'status': 'RUNNING', 'parts': [], 'feature_checks': [], 'exports': {},
    'scope': 'Native geometry; printed strength, tipping and sliding must be checked physically',
    'revision': 'weighted-m3-v1',
    'assembled_footprint_mm': [260.2, 110],
    'front_support_x_mm': 26,
    'nominal_loading_x_mm': 423.4,
    'rear_tray_weight_center_x_mm': -176.0,
    'reused_cap': '../fusion_14inch/root_cap.f3d',
    'root_fasteners': 'Four M3 x 30 mm, heads recessed underneath; washers/nuts above cap',
    'tray_fasteners': 'Four M3 x 12-30 mm, heads recessed underneath; washers/nuts above bridge',
    'limitations': ['No physical load rating', 'Ballast mass, position and table friction unmeasured',
                    'Support-free counterbore roofs need slicer/print inspection',
                    'Reference wing envelope is not a replacement wing']
}
R = h.REPORT

def bolt_hole(comp, name, x, y):
    h.hole_z(comp, name+' clearance', x, y, 3.4, 6, 'm3Clearance')
    h.hole_z(comp, name+' recessed head', x, y, 6.4, 3.3, 'm3HeadClearance')

def native_component(root, key, name):
    return h.component(root, key, name)

def run(context):
    app=C.Application.get();ui=app.userInterface
    try:
        for folder in ('stl', 'step', 'previews', 'verification'):
            os.makedirs(os.path.join(OUT, folder), exist_ok=True)
        h.PARTS.clear();h.PARAMETRIC_CIRCLES.clear()
        doc=app.documents.add(C.DocumentTypes.FusionDesignDocumentType)
        doc.name='SkySafe weighted holder - M3 - native'
        design=F.Design.cast(app.activeProduct)
        design.designType=F.DesignTypes.ParametricDesignType
        root=design.rootComponent
        for name,expression,unit in (
            ('m3Clearance','3.4 mm','mm'), ('m3HeadClearance','6.4 mm','mm'),
            ('standFloor','6 mm','mm'), ('bridgeThickness','4 mm','mm')):
            design.userParameters.add(name,C.ValueInput.createByString(expression),unit,'Weighted stand')

        front=native_component(root,'weighted_root_base','01 Weighted root base - PRINT ONE')
        h.box(front,'Flat root support floor',-104,-55,0,130,110,'standFloor',h.NEW)
        # Keep rear tray walls away from the old root cap and the skewer exits.
        for y in (-55,52):
            h.box(front,'Front tray side lip '+str(y),-104,y,5.95,70,3,4.05)
        for y in (-8,8):
            sk=h.sketch(front,'Original root locating pin '+str(y),offset=5.95)
            h.circle(sk,(8,y,5.95),3)
            h.extrude(front,sk,2.05,'Root locating pin '+str(y),h.JOIN)
        for x in (3,20):
            for y in (-43,43):bolt_hole(front,'Root bolt '+str((x,y)),x,y)
        for y in (-40,40):bolt_hole(front,'Tray joint front bolt '+str(y),-98,y)

        tray=native_component(root,'ballast_tray','02 Rear ballast tray - PRINT ONE')
        # Local print coordinates; assembled translation below is -130.2 mm.
        h.box(tray,'Rear tray floor',-104,-55,0,130,110,'standFloor',h.NEW)
        h.box(tray,'Rear weight stop',-104,-55,5.95,3,110,4.05)
        for y in (-55,52):h.box(tray,'Rear tray side lip '+str(y),-104,y,5.95,130,3,4.05)
        for y in (-40,40):bolt_hole(tray,'Tray joint rear bolt '+str(y),20,y)
        # Shallow center marker: recessed so a book/bag rests on a flat floor.
        h.box(tray,'Weight center line X',-46.3,-10,5.6,1,20,.5,h.CUT)
        h.box(tray,'Weight center line Y',-55.8,-.5,5.6,20,1,.5,h.CUT)

        bridge=native_component(root,'tray_bridge','03 Tray joint bridge - PRINT ONE')
        h.box(bridge,'Wide upper splice',0,-49,0,24.2,98,'bridgeThickness',h.NEW)
        for x in (6,18.2):
            for y in (-40,40):h.hole_z(bridge,'Tray splice hole '+str((x,y)),x,y,3.4,4,'m3Clearance')

        # Exact previous cap, modeled natively as reuse reference, not a new print.
        cap=native_component(root,'REUSE_root_cap','04 Existing root cap - REUSE')
        h.box(cap,'Original upper root jaw',-4,-49,0,30,98,8,h.NEW)
        for x in (3,20):
            for y in (-43,43):h.hole_z(cap,'Original M4 clearance '+str((x,y)),x,y,4.4,8)

        h.check_features(design)
        export=design.exportManager
        printable=[(key,occ,comp) for key,occ,comp in h.PARTS if not key.startswith('REUSE')]
        for key,occ,comp in printable:
            assert comp.bRepBodies.count==1 and comp.meshBodies.count==0
            body=comp.bRepBodies.item(0);body.name=key+' native printable solid'
            bb=body.boundingBox
            dimensions=[(getattr(bb.maxPoint,a)-getattr(bb.minPoint,a))*10 for a in ('x','y','z')]
            assert body.isSolid and all(v<=132.001 for v in dimensions[:2]) and dimensions[2]<=140
            assert abs(bb.minPoint.z)<1e-7
            R['parts'].append({'part':key,'native_solids':1,'mesh_bodies':0,'dimensions_mm':dimensions,
                               'volume_mm3':body.volume*1000,'sketches':comp.sketches.count})
            stl=export.createSTLExportOptions(body,os.path.join(OUT,'stl',key+'.stl'))
            stl.unitType=F.DistanceUnits.MillimeterDistanceUnits
            stl.meshRefinement=F.MeshRefinementSettings.MeshRefinementHigh
            assert export.execute(stl)
            assert export.execute(export.createSTEPExportOptions(os.path.join(OUT,'step',key+'.step'),comp))
            assert export.execute(export.createFusionArchiveExportOptions(os.path.join(OUT,key+'.f3d'),comp))
        positions={'weighted_root_base':(0,0,0),'ballast_tray':(-130.2,0,0),
                   'tray_bridge':(-116.2,0,6),'REUSE_root_cap':(0,0,16)}
        for key,occ,comp in h.PARTS:
            transform=C.Matrix3D.create()
            transform.translation=C.Vector3D.create(*(v/10 for v in positions[key]))
            occ.isGrounded=False;occ.isGroundToParent=False;occ.transform2=transform
        if design.snapshots.hasPendingSnapshot:design.snapshots.add()

        ref_occ=root.occurrences.addNewComponent(C.Matrix3D.create())
        ref=ref_occ.component
        ref.name='REFERENCE ONLY - root tongue and unloaded wing span'
        h.box(ref,'Existing root tongue envelope',0,-36,6,24,72,10,h.NEW)
        for y in (-8,8):h.hole_z(ref,'Original pin socket '+str(y),8,y,3.4,2.1,z=5.95)
        for y in (-18,18):h.diamond_x(ref,'Root bamboo passage '+str(y),-.05,y,10.5,4.5,24.1,h.CUT)
        h.box(ref,'Existing wing bending span envelope',24,-6,6,332.4,12,1.8,h.JOIN)
        entities=C.ObjectCollection.create()
        for _,occ,_ in h.PARTS:entities.add(occ)
        entities.add(ref_occ)
        result=design.analyzeInterference(design.createInterferenceInput(entities))
        overlaps=[{'volume_mm3':r.interferenceBody.volume*1000,
                   'one':getattr(r.entityOne,'name',''),'two':getattr(r.entityTwo,'name','')}
                  for r in result if r.interferenceBody and r.interferenceBody.volume>1e-7]
        R['assembled_interference']={'passed':not overlaps,'overlaps':overlaps}
        assert not overlaps,'Holder contains overlapping assembled solids'
        for comp in design.allComponents:
            comp.isOriginFolderLightBulbOn=False;comp.isSketchFolderLightBulbOn=False
            comp.isConstructionFolderLightBulbOn=False
        assembly=os.path.join(OUT,'SkySafe_Weighted_Holder.f3d')
        assert export.execute(export.createFusionArchiveExportOptions(assembly))
        assert export.execute(export.createSTEPExportOptions(os.path.join(OUT,'SkySafe_Weighted_Holder.step')))
        R['source_sha256']=hashlib.sha256(open(__file__,'rb').read()).hexdigest()
        R['helper_source_sha256']=hashlib.sha256(open(HELPER,'rb').read()).hexdigest()
        reopened=app.importManager.importToNewDocument(app.importManager.createFusionArchiveImportOptions(assembly))
        assert reopened
        design=F.Design.cast(app.activeProduct);design.computeAll()
        assert design.timeline.count>0
        R['archive_readback']={'passed':True,'timeline_items':design.timeline.count,
                              'components':[]}
        for comp in design.allComponents:
            tag=comp.attributes.itemByName('SkySafe','print_key')
            if tag:
                assert comp.bRepBodies.count==1 and comp.meshBodies.count==0 and comp.sketches.count>0
                R['archive_readback']['components'].append({'part':tag.value,'sketches':comp.sketches.count,
                                                          'solids':comp.bRepBodies.count,'meshes':comp.meshBodies.count})
        assert len(R['archive_readback']['components'])==4
        h.check_features(design)
        h.camera(app,os.path.join(OUT,'previews','weighted_assembly.png'),(-20,0,15),(260,-390,320),65)
        R['exports']={'assembly_f3d':assembly,'stl_parts':3,'step_parts':3}
        R['status']='PASS - native history and geometry; physical validation pending'
        h.record()
        ui.messageBox('Weighted SkySafe holder exported. Print the THREE new STL files; reuse your root cap.\n'+OUT)
    except:
        R['status']='ERROR';R['error']=traceback.format_exc();h.record()
        ui.messageBox('Weighted holder build stopped:\n'+R['error'])
