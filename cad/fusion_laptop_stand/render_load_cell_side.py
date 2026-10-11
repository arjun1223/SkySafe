"""Straight side-view assembly guide; hardware outline is schematic."""
import os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/skysafe-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

out=Path(__file__).resolve().parent/'previews/load_cell_side_view.png'
fig,ax=plt.subplots(figsize=(12,6.5),facecolor='white')
ax.set_xlim(-14,125);ax.set_ylim(-14,57);ax.set_aspect('equal');ax.axis('off')

def rect(x,y,w,h,fill):
    ax.add_patch(Rectangle((x,y),w,h,facecolor=fill,edgecolor='#65717b',linewidth=1.2))

# Print dimensions/positions match the native assembly, translated to adapter datum.
rect(0,0,90,6,'#c8d0d6')
rect(20,6,26,20,'#e5e9ed');rect(28,26,10,1.2,'#e5e9ed')
rect(70,16,26,10,'#e5e9ed');rect(78,26,10,1.2,'#e5e9ed')
rect(28,27.2,10,.5,'#d49b4d');rect(78,27.2,10,.5,'#d49b4d')
rect(28,27.7,60,12.7,'#8f9ba5')
ax.text(58,34,'METAL LOAD CELL',ha='center',va='center',fontsize=13,color='white')
ax.text(33,14,'TALL\nBLOCK',ha='center',va='center',fontsize=13,color='#24313a')
ax.text(83,21,'SHORT\nBLOCK',ha='center',va='center',fontsize=11,color='#24313a')
ax.text(44,3,'TIP ADAPTER',ha='center',va='center',fontsize=11,color='#24313a')
ax.text(12,-9,'Toward wing root',ha='center',fontsize=12,color='#4b5963')
ax.text(88,-9,'Toward outer tip',ha='center',fontsize=12,color='#4b5963')
ax.annotate('Fix this block\nto the adapter',xy=(23,10),xytext=(-11,23),fontsize=13,color='#24313a',
            ha='left',va='center',arrowprops=dict(arrowstyle='-',color='#65717b',linewidth=1.1))
ax.annotate('Metal bar stays level',xy=(48,40.4),xytext=(26,49),fontsize=14,color='#24313a',
            arrowprops=dict(arrowstyle='-',color='#65717b',linewidth=1.1))
ax.annotate('Hanger attaches\nto this end only',xy=(83,27.7),xytext=(101,35),fontsize=13,color='#24313a',
            ha='left',va='center',arrowprops=dict(arrowstyle='-',color='#65717b',linewidth=1.1))
ax.annotate('',xy=(99,16),xytext=(99,6),arrowprops=dict(arrowstyle='<->',color='#65717b',linewidth=1.1))
ax.text(103,11,'10 mm\nair gap',fontsize=13,va='center',color='#24313a')
ax.text(57,19,'Middle\nstays clear',ha='center',va='center',fontsize=12,color='#4b5963')
fig.text(.055,.94,'Load cell placement — straight side view',fontsize=21,color='#202b33')
fig.text(.055,.885,'Long metal bar runs in the same direction as your bamboo skewers. Hardware outline is schematic.',fontsize=11,color='#65717b')
fig.text(.055,.04,'Gold = thin glue at the end pads only. Use a temporary 10 mm spacer under the short block; remove it after bonding.',fontsize=11,color='#65717b')
fig.subplots_adjust(left=.02,right=.98,bottom=.13,top=.83)
fig.savefig(out,dpi=140)
print(out)
