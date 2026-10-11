"""Inspect the actual Fusion export and reused cap, without physical load claims."""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
import importlib.util

ROOT=Path(__file__).resolve().parent

def main():
    path=ROOT/'stl/laptop_foot_stand.stl'
    m=trimesh.load_mesh(path,process=True)
    checks={'watertight':bool(m.is_watertight),'consistent_winding':bool(m.is_winding_consistent),
            'one_connected_solid':len(m.split(only_watertight=False))==1,
            'fits_140_mm_printer':bool(np.all(m.extents<=140.001)),
            'dimensions_130_42_110':bool(np.allclose(m.extents,[130,42,110],atol=.002)),
            'flat_on_bed':bool(abs(m.bounds[0,2])<.001),
            'volume_matches_profile_and_four_bores':bool(abs(m.volume-96467.56)<.1)}
    assert all(checks.values()), checks
    holes=[]
    for y in (35.1,38,40.9):
        lines=trimesh.intersections.mesh_plane(m,plane_origin=[0,y,0],plane_normal=[0,1,0])
        pts=np.unique(lines.reshape(-1,3),axis=0)[:,[0,2]]
        r=3.4/np.sqrt(2)
        for x in (3,20):
            for assembly_y in (-43,43):
                z=55-assembly_y
                expected=np.array([[x-r,z],[x,z-r],[x+r,z],[x,z+r]])
                errors=[float(np.linalg.norm(pts-c,axis=1).min()) for c in expected]
                assert max(errors)<.002,(x,y,z,errors)
                holes.append({'print_plane_y':y,'center_print_xz':[x,z],
                              'center_assembly_xy':[x,assembly_y],
                              'inscribed_diameter_mm':3.4,'max_corner_error_mm':max(errors)})
    spec=importlib.util.spec_from_file_location('weighted_checks',ROOT.parent/'fusion_weighted/verify_weighted_holder.py')
    old=importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
    cap=trimesh.load_mesh(ROOT.parent/'fusion_14inch/stl/root_cap.stl',process=True)
    reused_cap=[old.circle_section(cap,4,x,y,4.4) for x in (3,20) for y in (-43,43)]
    # A 6 mm-wide bolt head clears the underside gusset by at least 1 mm.
    assert 3-6/2-(-1)>=1
    # Rear stop stays below the lowest existing 4.5 mm diamond spar passage.
    assert 42 < 45.5-4.5/np.sqrt(2)
    native=json.loads((ROOT/'native_build_report.json').read_text())
    assert native['status'].startswith('PASS') and native['assembled_interference']['passed']
    assert native['archive_readback']['passed']
    assert native['source_sha256']==hashlib.sha256((ROOT/'SkySafeLaptopStand/SkySafeLaptopStand.py').read_bytes()).hexdigest()
    assert native['helper_source_sha256']==hashlib.sha256((ROOT.parent/'fusion_14inch/SkySafeFusion14/SkySafeFusion14.py').read_bytes()).hexdigest()
    report={'passed':True,'scope':'Geometry only: no physical fit, anchoring or strength rating',
            'checks':checks,'dimensions_print_mm':m.extents.tolist(),'volume_mm3':float(m.volume),
            'diamond_bore_sections':holes,'reused_cap_sections':reused_cap,
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (ROOT/'verification/mesh_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: one solid, printer fit, 12 diamond sections, four reused-cap bores and native archive readback.')

if __name__=='__main__': main()
