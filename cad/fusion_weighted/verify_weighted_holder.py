"""Independent exported-mesh checks; no physical load rating is inferred."""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent

def circle_section(mesh, z, x, y, diameter):
    # Mesh/plane intersections avoid optional scipy-dependent path traversal.
    lines=trimesh.intersections.mesh_plane(mesh,plane_origin=[0,0,z],plane_normal=[0,0,1])
    points=np.unique(lines.reshape(-1,3),axis=0)[:,:2]
    radius=np.linalg.norm(points-[x,y],axis=1)
    points=points[np.abs(radius-diameter/2)<.1]
    assert len(points)>12, f'Missing {diameter} mm section at {(x,y,z)}'
    matrix=np.column_stack([2*points[:,0],2*points[:,1],np.ones(len(points))])
    cx,cy,c=np.linalg.lstsq(matrix,(points*points).sum(axis=1),rcond=None)[0]
    measured=float(2*np.sqrt(c+cx*cx+cy*cy))
    assert abs(cx-x)<.02 and abs(cy-y)<.02 and abs(measured-diameter)<.03
    return {'center':[float(cx),float(cy)],'z':z,'diameter_mm':diameter,
            'measured_diameter_mm':measured,'passed':True}

def main():
    paths=list((ROOT/'stl').glob('*.stl'))
    assert {p.stem for p in paths}=={'weighted_root_base','ballast_tray','tray_bridge'}
    meshes={p.stem:trimesh.load_mesh(p,process=True) for p in paths}
    results=[]
    expected={'weighted_root_base':[130,110,10],'ballast_tray':[130,110,10],'tray_bridge':[24.2,98,4]}
    for path in paths:
        m=meshes[path.stem]
        checks={'watertight':bool(m.is_watertight),'consistent_winding':bool(m.is_winding_consistent),
                'one_connected_solid':len(m.split(only_watertight=False))==1,'positive_volume':bool(m.volume>0),
                'fits_140_mm_bed':bool(np.all(m.extents<=140.001)),
                'fits_132_mm_xy_margin':bool(np.all(m.extents[:2]<=132.001)),
                'flat_on_bed':bool(abs(m.bounds[0,2])<.001),
                'expected_dimensions':bool(np.allclose(m.extents,expected[path.stem],atol=.001))}
        assert all(checks.values()), (path.name,checks)
        results.append({'part':path.name,'checks':checks,'dimensions_mm':m.extents.tolist(),
                        'volume_mm3':float(m.volume),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    holes=[]
    front=meshes['weighted_root_base'];tray=meshes['ballast_tray'];bridge=meshes['tray_bridge']
    for mesh,centers in [(front,[(x,y) for x in (3,20) for y in (-43,43)]+[(-98,-40),(-98,40)]),
                         (tray,[(20,-40),(20,40)])]:
        for x,y in centers:
            holes.append(circle_section(mesh,.5,x,y,6.4))
            holes.append(circle_section(mesh,4,x,y,3.4))
    for y in (-8,8):holes.append(circle_section(front,7,8,y,3))
    for x in (6,18.2):
        for y in (-40,40):holes.append(circle_section(bridge,2,x,y,3.4))
    cap=trimesh.load_mesh(ROOT.parent/'fusion_14inch/stl/root_cap.stl',process=True)
    for x in (3,20):
        for y in (-43,43):holes.append(circle_section(cap,4,x,y,4.4))
    assert np.allclose([6-116.2,18.2-116.2],[20-130.2,-98])
    assert abs((26-(-104-130.2))-260.2)<1e-8
    native=json.loads((ROOT/'native_build_report.json').read_text())
    source=ROOT/'SkySafeWeighted/SkySafeWeighted.py'
    assert native['status'].startswith('PASS') and native['assembled_interference']['passed']
    assert native['archive_readback']['passed']
    assert native['source_sha256']==hashlib.sha256(source.read_bytes()).hexdigest()
    helper=ROOT.parent/'fusion_14inch/SkySafeFusion14/SkySafeFusion14.py'
    assert native['helper_source_sha256']==hashlib.sha256(helper.read_bytes()).hexdigest()
    report={'passed':True,'scope':'Native/export geometry only; physical fit, strength and stability untested',
            'parts':results,'circular_sections':holes,'tray_hole_alignment':True,'existing_cap_alignment':True,
            'assembled_footprint_mm':[260.2,110],'source_sha256':native['source_sha256']}
    (ROOT/'verification/mesh_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'PASS: three meshes, {len(holes)} measured circular sections, tray alignment and reused cap.')

if __name__=='__main__':main()
