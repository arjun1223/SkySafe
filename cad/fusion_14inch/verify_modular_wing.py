#!/usr/bin/env python3
"""Check the native/exported 14-inch diamond-hole assembly; no load rating."""
from pathlib import Path
import hashlib
import json
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent

def section(mesh, axis, value):
    normal = np.eye(3)[axis]
    lines = trimesh.intersections.mesh_plane(mesh, normal, normal * value)
    return np.unique(lines.reshape(-1, 3), axis=0)

def main():
    native = json.loads((ROOT / 'native_build_report.json').read_text())
    meshes = json.loads((ROOT / 'verification/mesh_report.json').read_text())
    source_hash = hashlib.sha256((ROOT / 'SkySafeFusion14/SkySafeFusion14.py').read_bytes()).hexdigest()
    assert native['status'].startswith('PASS') and meshes['passed']
    assert source_hash == native['source_sha256'] == meshes['source_sha256']
    assert native['assembled_interference']['passed']
    shapes = {name: trimesh.load_mesh(ROOT / 'stl' / (name + '.stl'), process=True)
              for name in ['wing_root', 'wing_middle', 'wing_tip', 'joint_plate']}
    for name,mesh in shapes.items():
        expected = next(p['sha256'] for p in meshes['parts'] if p['part'] == name+'.stl')
        assert hashlib.sha256((ROOT/'stl'/(name+'.stl')).read_bytes()).hexdigest() == expected
    origins = {'wing_root':0, 'wing_middle':128.2, 'wing_tip':242.4}
    span = max(origins[n] + shapes[n].bounds[1,0] for n in origins)
    assert abs(span-356.4)<.001 and 13 <= span/25.4 <= 15
    bores = []
    r = 4.5 / np.sqrt(2)
    sections = {'wing_root':[10,29,49,69,89,109], 'wing_middle':[16,38,60,82,96],
                'wing_tip':[16,38,60,82,106]}
    for name,xs in sections.items():
        for x in xs:
            yz = section(shapes[name],0,x)[:,1:3]
            for y in [-18,18]:
                center = np.array([y,4.5])
                points = yz[np.abs(np.abs(yz-center).sum(axis=1)-r)<.002]
                assert len(points)>=4,(name,x,y,len(points))
                for delta in [[-r,0],[0,-r],[r,0],[0,r]]:
                    assert np.linalg.norm(points-(center+delta),axis=1).min()<.002,(name,x,y,delta)
                # These four vertices define four 45 degree faces, enclosing a 4.5 mm circle.
                bores.append({'part':name,'local_x_mm':x,'center_yz_mm':[y,4.5],
                              'flat_to_flat_mm':4.5,'diagonal_mm':float(2*r),'roof_angle_deg':45})
    # Verify each bolted landing against the reusable plate hole geometry.
    holes = []
    for name,xs in {'wing_root':[122], 'wing_middle':[6,108], 'wing_tip':[6], 'joint_plate':[6,18.2]}.items():
        xy = section(shapes[name],2,1)[:,:2]
        for x in xs:
            distance = np.linalg.norm(xy-[x,0],axis=1)
            points = xy[(distance>1.6)&(distance<1.8)]
            assert len(points)>12,(name,x,len(points))
            a = np.column_stack([2*points[:,0],2*points[:,1],np.ones(len(points))])
            cx,cy,c = np.linalg.lstsq(a,(points*points).sum(axis=1),rcond=None)[0]
            diameter = float(2*np.sqrt(c+cx*cx+cy*cy))
            assert abs(cx-x)<.02 and abs(cy)<.02 and abs(diameter-3.4)<.02
            holes.append({'part':name,'local_x_mm':x,'diameter_mm':diameter})
    for pairs,start in [([('wing_root',122),('wing_middle',6)],116),
                        ([('wing_middle',108),('wing_tip',6)],230.2)]:
        for (name,x),plate_x in zip(pairs,[6,18.2]):
            assert abs(origins[name]+x-(start+plate_x))<.001
    plate_positions = [xyz for name,xyz in native['assembly_positions_mm'].items() if name.startswith('07 Joint sandwich')]
    expected = [[116,0,14],[116,0,18.4],[230.2,0,14],[230.2,0,18.4]]
    assert len(plate_positions)==4
    for xyz in expected:
        assert any(np.allclose(actual,xyz,atol=.001) for actual in plate_positions),xyz
    gauge = section(shapes['wing_root'],0,40)[:,1:3]
    assert np.allclose(gauge.min(axis=0),[-6,0],atol=.001)
    assert np.allclose(gauge.max(axis=0),[6,1.8],atol=.001)
    landing = section(shapes['wing_middle'],0,110)[:,1:3]
    assert np.allclose(landing.min(axis=0),[-10,0],atol=.001)
    assert np.allclose(landing.max(axis=0),[10,2.4],atol=.001)
    previous = json.loads((ROOT.parent/'fusion/native_build_report.json').read_text())
    unchanged = ['root_cap','tip_adapter','cell_spacer','load_hanger']
    for name in unchanged:
        old = next(p['volume_mm3'] for p in previous['parts'] if p['part']==name)
        new = next(p['volume_mm3'] for p in native['parts'] if p['part']==name)
        assert abs(old-new)<.001,name
    result = {'passed':True,'scope':'Export geometry only; printed fit and bending remain untested',
              'source_sha256':source_hash,'assembled_span_mm':float(span),'assembled_span_inches':float(span/25.4),
              'diamond_sections':bores,'joint_bolt_holes':holes,'plate_positions_mm':plate_positions,
              'gauge_strip_thickness_mm':1.8,'unchanged_parts':unchanged}
    (ROOT/'verification/modular_wing_check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f'PASS: {span:.1f} mm span, {len(bores)} diamond sections, 6 bolt holes, four aligned plates, unchanged mounts')

if __name__=='__main__':
    main()
