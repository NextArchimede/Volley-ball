import bpy, bmesh, math
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene

# --- Squelette de référence (Blender : Z haut, le joueur regarde -Y, sa gauche = +X)
J={}
def j(n,x,y,z): J[n]=Vector((x,y,z))
j('hips',0,0,0.975); j('spine',0,0,1.055); j('chest',0,0,1.225); j('neck',0,0,1.535); j('head',0,0,1.625); j('top',0,0,1.86)
A=0.32
for s,sx in (('L',1),('R',-1)):
    sh=Vector((sx*0.2,0,1.46)); el=sh+Vector((sx*0.3*math.sin(A),0,-0.3*math.cos(A))); wr=el+Vector((sx*0.27*math.sin(A),0,-0.27*math.cos(A)))
    J['sh'+s]=sh;J['el'+s]=el;J['wr'+s]=wr;J['hand'+s]=wr+Vector((sx*0.1*math.sin(A),0,-0.1*math.cos(A)))
    B=0.12
    hp=Vector((sx*0.088,0,0.945)); kn=hp+Vector((sx*0.44*math.sin(B),0,-0.44*math.cos(B))); an=kn+Vector((sx*0.42*math.sin(B),0,-0.42*math.cos(B)))
    J['hp'+s]=hp;J['kn'+s]=kn;J['an'+s]=an;J['toe'+s]=Vector((an.x,-0.17,0.035));J['heel'+s]=Vector((an.x,0.045,0.04))

# --- Corps : modificateur Skin sur un graphe de sommets
verts=[];edges=[];rad=[]
def v(p,rx,ry=None):
    verts.append(p.copy());rad.append((rx,ry if ry is not None else rx));return len(verts)-1
def e(a,b):edges.append((a,b))
iH=v(J['hips'],0.165,0.12); iW=v(Vector((0,0,1.1)),0.148,0.108); iC1=v(Vector((0,0,1.24)),0.172,0.115)
iC2=v(Vector((0,0,1.36)),0.2,0.128); iN0=v(Vector((0,0,1.47)),0.16,0.1); iNk=v(Vector((0,0,1.56)),0.055,0.058)
e(iH,iW);e(iW,iC1);e(iC1,iC2);e(iC2,iN0);e(iN0,iNk)
for s,sx in (('L',1),('R',-1)):
    a=v(J['sh'+s],0.07); e(iN0,a)
    m1=v(J['sh'+s].lerp(J['el'+s],0.45),0.062); e(a,m1)
    b=v(J['el'+s],0.048); e(m1,b)
    m2=v(J['el'+s].lerp(J['wr'+s],0.35),0.047); e(b,m2)
    c=v(J['wr'+s],0.034,0.028); e(m2,c)
    dr=(J['hand'+s]-J['wr'+s]).normalized()
    palm=v(J['wr'+s]+dr*0.055,0.032,0.016); e(c,palm)
    for k,fy in enumerate((-0.026,-0.009,0.008,0.024)):
        ln=(0.075,0.083,0.079,0.066)[k]
        r0=v(J['wr'+s]+dr*0.085+Vector((0,fy,0)),0.0105); e(palm,r0)
        r1=v(J['wr'+s]+dr*(0.085+ln*0.55)+Vector((0,fy,0))+Vector((-sx*0.006,0,0)),0.0095); e(r0,r1)
        r2=v(J['wr'+s]+dr*(0.085+ln)+Vector((0,fy*1.05,0))+Vector((-sx*0.016,0,0)),0.0085); e(r1,r2)
    t0=v(J['wr'+s]+dr*0.03+Vector((-sx*0.012,-0.03,0)),0.012); e(c,t0)
    t1=v(J['wr'+s]+dr*0.065+Vector((-sx*0.02,-0.045,0)),0.0105); e(t0,t1)
    t2=v(J['wr'+s]+dr*0.095+Vector((-sx*0.022,-0.05,0)),0.0095); e(t1,t2)
    h=v(J['hp'+s],0.105); e(iH,h)
    t=v(J['hp'+s].lerp(J['kn'+s],0.45),0.097); e(h,t)
    k=v(J['kn'+s],0.066); e(t,k)
    cf=v(J['kn'+s].lerp(J['an'+s],0.3),0.072,0.078); e(k,cf)
    an=v(J['an'+s],0.045); e(cf,an)
    hl=v(J['heel'+s],0.05,0.045); e(an,hl)
    to=v(J['toe'+s],0.048,0.035); e(hl,to)
me=bpy.data.meshes.new('body');me.from_pydata(verts,edges,[]);me.update()
body=bpy.data.objects.new('Athlete',me);sc.collection.objects.link(body)
bpy.context.view_layer.objects.active=body;body.select_set(True)
sk=body.modifiers.new('skin','SKIN')
for i,(rx,ry) in enumerate(rad):
    me.skin_vertices[0].data[i].radius=(rx,ry)
me.skin_vertices[0].data[iH].use_root=True
sub=body.modifiers.new('sub','SUBSURF');sub.levels=3;sub.render_levels=3
bpy.ops.object.modifier_apply(modifier='skin');bpy.ops.object.modifier_apply(modifier='sub')
# coupes nettes aux limites des vêtements
bm=bmesh.new();bm.from_mesh(body.data)
def cut(co,no):
    g=bm.verts[:]+bm.edges[:]+bm.faces[:]
    bmesh.ops.bisect_plane(bm,geom=g,plane_co=co,plane_no=no,clear_inner=False,clear_outer=False)
for z in (0.99,0.745,0.44,0.58,0.11,0.29,1.52):cut(Vector((0,0,z)),Vector((0,0,1)))
for s_ in 'LR':
    a,b=J['sh'+s_],J['el'+s_];cut(a+(b-a)*0.33,(b-a).normalized())
bm.to_mesh(body.data);bm.free()

# --- Tête : crâne + mâchoire + nez + oreilles, fusionnés
def sphere(name,loc,scale,seg=24,ring=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=ring,radius=1,location=loc)
    o=bpy.context.active_object;o.name=name;o.scale=scale;bpy.ops.object.transform_apply(scale=True);return o

# --- Matériaux par région
def mat(n,c,r=0.7):
    m=bpy.data.materials.new(n);m.use_nodes=True;b=m.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=(*c,1);b.inputs['Roughness'].default_value=r;return m
M={k:mat(k,c,r) for k,c,r in [('skin',(0.8,0.55,0.4),0.55),('jersey',(0.05,0.2,0.75),0.6),('shorts',(0.02,0.03,0.08),0.7),('sock',(0.9,0.9,0.9),0.8),('shoe',(0.92,0.92,0.92),0.45),('pad',(0.02,0.02,0.025),0.8),('hair',(0.05,0.03,0.02),0.9),('sole',(0.05,0.2,0.75),0.6),('eye',(0.02,0.015,0.01),0.3),('eyewhite',(0.85,0.83,0.8),0.35),('lip',(0.55,0.3,0.25),0.5),('brow',(0.05,0.03,0.02),0.9)]}
order=['skin','jersey','shorts','sock','shoe','pad','hair','sole','eye','eyewhite','lip','brow']
for k in order: body.data.materials.append(M[k])
def segdist(p,a,b):
    ab=b-a;t=max(0,min(1,(p-a).dot(ab)/ab.length_squared));return (p-(a+ab*t)).length,t
for poly in body.data.polygons:
    c=poly.center;zs=[body.data.vertices[i].co.z for i in poly.vertices];z=c.z;zmin=min(zs);zmax=max(zs);idx=0
    arm=None
    fore=False
    for s in 'LR':
        sg=(1 if s=='L' else -1)
        d,t=segdist(c,J['sh'+s],J['el'+s])
        if d<0.09 and c.x*sg>0.17:arm=(t)
        d2,_=segdist(c,J['el'+s],J['hand'+s])
        if d2<0.075 and c.x*sg>0.2:fore=True
    if z>1.53: idx=0
    elif fore: idx=0
    elif arm is not None: idx=1 if arm<0.33 else 0
    elif zmin>0.99 and abs(c.x)<0.26: idx=1
    elif zmin>0.745 and abs(c.x)<0.3: idx=2
    elif zmin>0.44 and zmax<0.58: idx=5
    elif zmin>0.11 and zmax<0.29: idx=3
    elif z<=0.025: idx=7
    elif z<=0.11: idx=4
    poly.material_index=idx

# --- Tête : pièces séparées avec leurs matériaux, puis fusion avec le corps
def part_(name,loc,scale,mname,seg=24,ring=16):
    o=sphere(name,loc,scale,seg,ring);o.data.materials.append(M[mname]);return o
HC=Vector((0,0.004,1.705))
bpy.ops.mesh.primitive_uv_sphere_add(segments=40,ring_count=28,radius=1,location=HC)
skull=bpy.context.active_object;skull.name='skull'
for vt in skull.data.vertices:
    x,y,z=vt.co.x,vt.co.y,vt.co.z
    if z<0:
        t=(-z)**1.4;x*=1-0.38*t;y*=1-0.12*t+(0.06*(-z) if y<0 else 0)
    if y<0 and z>0.2:y*=0.94
    vt.co.x,vt.co.y,vt.co.z=x*0.09,y*0.1,z*0.118
skull.data.materials.append(M['skin']);skull.data.materials.append(M['hair'])
for poly in skull.data.polygons:
    c=poly.center
    poly.material_index=1 if (c.z>0.05 or (c.z>-0.035 and c.y>0.02 and abs(c.x)<0.088) or (c.z>0.03 and c.y>-0.06)) else 0
heads=[skull,
  part_('nose',(0,-0.098,1.69),(0.0105,0.015,0.021),'skin',16,10),
  part_('eyewL',(0.033,-0.084,1.722),(0.011,0.008,0.0085),'eyewhite',16,10),part_('eyewR',(-0.033,-0.084,1.722),(0.011,0.008,0.0085),'eyewhite',16,10),
  part_('irisL',(0.033,-0.0915,1.722),(0.0055,0.0025,0.0058),'eye',12,8),part_('irisR',(-0.033,-0.0915,1.722),(0.0055,0.0025,0.0058),'eye',12,8),
  part_('browL',(0.034,-0.088,1.738),(0.017,0.005,0.0035),'brow',12,8),part_('browR',(-0.034,-0.088,1.738),(0.017,0.005,0.0035),'brow',12,8),
  part_('lip',(0,-0.085,1.645),(0.017,0.005,0.0036),'lip',12,8),
  part_('earL',(0.088,0.006,1.70),(0.011,0.022,0.03),'skin',12,8),part_('earR',(-0.088,0.006,1.70),(0.011,0.022,0.03),'skin',12,8)]
bpy.ops.object.select_all(action='DESELECT')
for o in heads:o.select_set(True)
body.select_set(True);bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
dec=body.modifiers.new('dec','DECIMATE');dec.ratio=0.42;bpy.ops.object.modifier_apply(modifier='dec')
bpy.ops.object.shade_smooth()

# --- Armature (noms = articulations du jeu)
arm=bpy.data.armatures.new('Rig');rig=bpy.data.objects.new('Rig',arm);sc.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
eb=arm.edit_bones
def bone(n,h,t,par=None):
    b=eb.new(n);b.head=h;b.tail=t
    if par:b.parent=eb[par];b.use_connect=False
    return b
bone('hips',J['hips'],J['spine']);bone('spine',J['spine'],J['chest'],'hips');bone('chest',J['chest'],J['neck'],'spine')
bone('neck',J['neck'],J['head'],'chest');bone('head',J['head'],J['top'],'neck')
for s in 'LR':
    bone('sh'+s,J['sh'+s],J['el'+s],'chest');bone('el'+s,J['el'+s],J['wr'+s],'sh'+s);bone('hand'+s,J['wr'+s],J['hand'+s],'el'+s)
    bone('hp'+s,J['hp'+s],J['kn'+s],'hips');bone('kn'+s,J['kn'+s],J['an'+s],'hp'+s);bone('an'+s,J['an'+s],J['toe'+s],'kn'+s)
bpy.ops.object.mode_set(mode='OBJECT')
body.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
vg=[g.name for g in body.vertex_groups]
empty=[g for g in vg if not any(g==body.vertex_groups[g].name and True for _ in [0])]
import sys;sys.stderr.write('TRIS %d\n'%sum(len(p.vertices)-2 for p in body.data.polygons));print('vertex groups',len(vg),'verts',len(body.data.vertices),'tris',sum(len(p.vertices)-2 for p in body.data.polygons))

bpy.ops.export_scene.gltf(filepath='/tmp/claude-0/bl/athlete.glb',export_format='GLB',use_selection=False,export_skins=True,export_animations=False,export_apply=False)

# --- Rendu de contrôle
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam'));sc.collection.objects.link(cam)
cam.location=(1.6,-2.6,1.3);cam.rotation_euler=(math.radians(84),0,math.radians(32));sc.camera=cam;cam.data.lens=45
for loc,en in [((3,-3,5),3.0),((-3,2,3),1.2)]:
    l=bpy.data.objects.new('l',bpy.data.lights.new('l','SUN'));l.data.energy=en;l.location=loc;l.rotation_euler=(0.6,0.2,0.8 if loc[0]>0 else -2.4);sc.collection.objects.link(l)
w=bpy.data.worlds.new('w');sc.world=w;w.use_nodes=True;w.node_tree.nodes['Background'].inputs[0].default_value=(0.05,0.08,0.11,1)
bpy.ops.mesh.primitive_plane_add(size=6)
sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.device='CPU';sc.render.resolution_x=420;sc.render.resolution_y=520
sc.render.filepath='/tmp/claude-0/bl/full.png';bpy.ops.render.render(write_still=True)
cam.location=(0.25,-0.55,1.72);cam.rotation_euler=(math.radians(90),0,math.radians(24));cam.data.lens=80
sc.render.filepath='/tmp/claude-0/bl/face.png';bpy.ops.render.render(write_still=True)
cam.location=(0.75,-0.55,0.95);cam.rotation_euler=(math.radians(97),0,math.radians(32));cam.data.lens=70
sc.render.filepath='/tmp/claude-0/bl/hand.png';bpy.ops.render.render(write_still=True)
