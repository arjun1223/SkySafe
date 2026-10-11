"""Assembly illustrations from the actual exported print meshes.

Hardware envelopes are schematic and explicitly labeled. No CAD is edited.
"""
import os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/skysafe-mpl')
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from mpl_toolkits.mplot3d import proj3d
from matplotlib.colors import LightSource,to_rgba

ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'fusion_14inch/stl'
WHITE='#e4e7e9'; DARK='#42484d'; NEW='#e7a25a'; WOOD='#c8a773'
parts=[]

def add(mesh,color,name):
    parts.append((mesh,color,name)); return mesh

def printed(name,xyz,color=WHITE):
    m=trimesh.load_mesh(OLD/(name+'.stl'),process=True)
    m.apply_translation(xyz); return add(m,color,name)

def box(origin,size,color,name):
    m=trimesh.creation.box(extents=size)
    m.apply_translation(np.array(origin)+np.array(size)/2)
    return add(m,color,name)

def rod(x,y,z,length,radius,color,name):
    m=trimesh.creation.cylinder(radius=radius,height=length,sections=32)
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,1,0]))
    m.apply_translation([x+length/2,y,z]); return add(m,color,name)

def geometry():
    m=trimesh.load_mesh(ROOT/'stl/laptop_foot_stand.stl',process=True)
    m.apply_transform(np.array([[1,0,0,0],[0,0,-1,55],[0,1,0,0],[0,0,0,1]],dtype=float))
    add(m,NEW,'new stand')
    for name,xyz in [('wing_root',(0,0,41)),('wing_middle',(128.2,0,41)),
                     ('wing_tip',(242.4,0,41)),('root_cap',(0,0,51)),
                     ('tip_adapter',(340.4,0,50)),('cell_spacer',(373.4,0,56)),
                     ('load_hanger',(423.4,0,66))]:
        printed(name,xyz,DARK if name=='root_cap' else WHITE)
    for x in (116,230.2):
        for z in (39,43.4): printed('joint_plate',(x,0,z),DARK)
    for y in (-18,18): rod(-6.6,y,45.5,361,2,WOOD,'bamboo')
    box((-233.2,-156.3,3),(221.2,312.6,15.5),'#b0b5bb','laptop envelope')
    box((75,-10,48.2),(22,20,1.6),'#557f9b','IMU envelope')
    box((33,-3,42.8),(10,6,.2),'#c88742','gauge envelope')
    box((368.4,-6.35,77.7),(60,12.7,12.7),'#a0a7ad','load cell envelope')
    # Illustrative M3 fasteners for clamp and the four joint plates.
    for x in (3,20):
        for y in (-43,43):
            b=trimesh.creation.cylinder(radius=1.5,height=30,sections=20)
            b.apply_translation([x,y,50]);add(b,DARK,'root screw')
            for z,r,height in ((33.5,2.8,3),(59.4,3.5,.8),(61,3.1,2.4)):
                b=trimesh.creation.cylinder(radius=r,height=height,sections=6 if r==3.1 else 20)
                b.apply_translation([x,y,z]);add(b,DARK,'root hardware')
    for x in (122,134.2,236.2,248.4):
        b=trimesh.creation.cylinder(radius=2.8,height=2,sections=20)
        b.apply_translation([x,0,46.4]);add(b,DARK,'joint screw')

def scene(ax,subset=None):
    selected=parts if subset is None else [p for p in parts if p[2] in subset]
    triangles=np.concatenate([m.triangles for m,c,n in selected])
    colors=np.concatenate([np.tile(to_rgba(c),(len(m.faces),1)) for m,c,n in selected])
    normal=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    lengths=np.linalg.norm(normal,axis=1)
    valid=lengths>1e-9
    triangles=triangles[valid];colors=colors[valid]
    normal=normal[valid]/lengths[valid,None]
    light=LightSource(azdeg=315,altdeg=48).direction
    colors[:,:3]*=(.75+.25*np.clip((normal*light).sum(axis=1),-1,1))[:,None]
    ax.add_collection3d(Poly3DCollection(triangles,facecolors=colors,edgecolors='none',zsort='average'))
    ax.set_proj_type('ortho'); ax.set_axis_off()

def callout(fig,ax,point,at,title,detail='',align='left'):
    q=proj3d.proj_transform(*point,ax.get_proj())
    xy=fig.transFigure.inverted().transform(ax.transData.transform(q[:2]))
    label=title+('\n'+detail if detail else '')
    ax.annotate(label,xy=xy,xycoords=fig.transFigure,xytext=at,textcoords=fig.transFigure,
                ha=align,va='center',fontsize=12,color='#30373d',linespacing=1.55,
                arrowprops=dict(arrowstyle='-',color='#6c747b',linewidth=1.1,
                                connectionstyle='angle3,angleA=0,angleB=90'),
                bbox=dict(facecolor='white',edgecolor='none',pad=4),annotation_clip=False)

def overview():
    fig=plt.figure(figsize=(16,9),facecolor='white')
    ax=fig.add_axes([.01,.13,.98,.78],projection='3d')
    scene(ax);ax.set_xlim(-255,455);ax.set_ylim(-165,165);ax.set_zlim(0,130)
    ax.set_box_aspect((710,330,130));ax.view_init(elev=31,azim=-65)
    fig.text(.045,.95,'SkySafe — your parts assembled',fontsize=22,weight='medium',color='#20262b')
    fig.text(.045,.91,'Printed geometry from your actual files · electronics and laptop shown schematically',fontsize=11,color='#687179')
    fig.canvas.draw()
    callout(fig,ax,(-130,-40,18),(.06,.65),'14-inch laptop','Rear tab slides underneath')
    callout(fig,ax,(-30,-55,20),(.12,.28),'NEW: one-piece stand','Reuse your existing top cap')
    callout(fig,ax,(80,0,49),(.43,.76),'MPU6050','Secure flat to the printed landing')
    callout(fig,ax,(38,0,43),(.31,.36),'BF350 strain gauge','Bond lengthwise just past the clamp')
    callout(fig,ax,(134,0,46),(.47,.25),'Your three wing sections','Four joint plates + two bamboo spars')
    callout(fig,ax,(405,0,84),(.77,.72),'5 kg load cell','Glue only the two end pads')
    callout(fig,ax,(423.4,-17,71),(.78,.27),'Free hanger','Keep clear of the adapter below')
    fig.text(.045,.075,'Already printed: wing root / middle / tip • 4 joint plates • clamp cap • tip adapter • fixed pedestal • free hanger',fontsize=11,color='#434b52')
    fig.text(.045,.035,'Orange stand is the only new print. ESP32 + HX711 stay beside the rig with slack wires. No force or anchoring rating is implied.',fontsize=11,color='#687179')
    fig.savefig(ROOT/'previews/your_parts_assembly.png',dpi=130)
    plt.close(fig)

def tip_detail():
    fig=plt.figure(figsize=(12,8),facecolor='white')
    ax=fig.add_axes([0,.1,1,.82],projection='3d')
    scene(ax,{'wing_tip','tip_adapter','cell_spacer','load_hanger','load cell envelope','bamboo'})
    ax.set_xlim(315,445);ax.set_ylim(-45,45);ax.set_zlim(35,105)
    ax.set_box_aspect((130,90,70));ax.view_init(elev=22,azim=-70)
    fig.text(.04,.95,'Tip mounting detail',fontsize=21,weight='medium',color='#20262b')
    fig.text(.04,.90,'Slide the fixed pedestal on its rails to suit your actual cell. Sensor size shown is illustrative.',fontsize=11,color='#687179')
    fig.canvas.draw()
    callout(fig,ax,(374,0,78),(.07,.72),'Fixed cell end','Thin hot glue bond on raised pad')
    callout(fig,ax,(403,0,84),(.59,.79),'Sensing section','No glue or printed support underneath')
    callout(fig,ax,(423,-17,70),(.74,.31),'Free hanger','Load goes here; keep the air gap')
    callout(fig,ax,(385,-19,52),(.08,.22),'Tip adapter','Bolts onto the wing tip')
    fig.text(.04,.04,'Keep the wire exit clear. Secure the fixed pedestal to the adapter; the free hanger moves with the other cell end.',fontsize=11,color='#687179')
    fig.savefig(ROOT/'previews/tip_mount_detail.png',dpi=130)
    plt.close(fig)

if __name__=='__main__':
    geometry();overview();tip_detail()
    print('Rendered actual print meshes: assembly overview and tip detail.')
