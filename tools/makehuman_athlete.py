# Side Out : joueur réaliste à partir du corps MakeHuman (MPFB2, CC0), tenue et cheveux modélisés ici.
import bpy, bmesh, addon_utils, importlib, math, sys, json
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
addon_utils.enable("bl_ext.user_default.mpfb", default_set=True)
imp = lambda p, k: getattr(importlib.import_module("bl_ext.user_default." + p), k)
HumanService = imp("mpfb.services.humanservice", "HumanService")
HOP = imp("mpfb.entities.objectproperties", "HumanObjectProperties")
TargetService = imp("mpfb.services.targetservice", "TargetService")

GENDER = float(sys.argv[-1]) if sys.argv[-1].replace('.', '').isdigit() else 1.0
h = HumanService.create_human()
for k, v in [("gender", GENDER), ("muscle", 0.78), ("height", 0.85), ("weight", 0.42), ("age", 0.45), ("proportions", 0.8)]:
    try: HOP.set_value(k, v, entity_reference=h)
    except Exception as e: print("prop", k, e)
TargetService.reapply_macro_details(h)
rig = HumanService.add_builtin_rig(h, "game_engine")
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT'); h.select_set(True); bpy.context.view_layer.objects.active = h
if h.data.shape_keys: bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
for m in list(h.modifiers):
    if m.type == 'MASK': h.modifiers.remove(m); continue
    if m.type not in ('ARMATURE',):
        try: bpy.ops.object.modifier_apply(modifier=m.name)
        except Exception as e: print('mod', m.name, e)

me = h.data
gi = {g.name: g.index for g in h.vertex_groups}
def centroid(gname):
    idx = gi[gname]; pts = [h.matrix_world @ v.co for v in me.vertices if any(g.group == idx and g.weight > 0.0 for g in v.groups)]
    if not pts: print('empty group', gname); return Vector()
    return sum(pts, Vector()) / len(pts)
EYE = {s: centroid('helper-%s-eye' % s) for s in 'lr'}
MOUTH = centroid('joint-mouth')
B = {b.name: (rig.matrix_world @ b.head_local, rig.matrix_world @ b.tail_local) for b in rig.data.bones}

# --- retirer la géométrie d'aide, sauf les yeux
bm = bmesh.new(); bm.from_mesh(me); dl = bm.verts.layers.deform.active
keep = {gi['helper-l-eye'], gi['helper-r-eye']}
helpers = {gi['HelperGeometry'], gi['JointCubes']}
kill = [v for v in bm.verts if any(g in helpers for g in v[dl].keys()) and not any(g in keep and w > 0.5 for g, w in v[dl].items())]
bmesh.ops.delete(bm, geom=kill, context='VERTS'); bm.to_mesh(me); bm.free()

# --- un niveau de subdivision pour des limites de vêtements nettes
sub=h.modifiers.new('sub','SUBSURF');sub.levels=1;sub.render_levels=1
bpy.ops.object.modifier_apply(modifier='sub')

# --- matériaux
def mat(n, c, r=0.7):
    m = bpy.data.materials.new(n); m.use_nodes = True; p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*c, 1); p.inputs['Roughness'].default_value = r; return m
MATS = [('skin', (0.72, 0.5, 0.38), 0.5), ('jersey', (0.05, 0.2, 0.75), 0.6), ('shorts', (0.02, 0.03, 0.08), 0.7), ('sock', (0.9, 0.9, 0.9), 0.8),
        ('shoe', (0.92, 0.92, 0.92), 0.45), ('pad', (0.9, 0.9, 0.9), 0.8), ('hair', (0.05, 0.03, 0.02), 0.85), ('sole', (0.05, 0.2, 0.75), 0.6),
        ('eye', (0.05, 0.03, 0.02), 0.2), ('eyewhite', (0.85, 0.83, 0.8), 0.3), ('lip', (0.55, 0.3, 0.25), 0.45), ('brow', (0.05, 0.03, 0.02), 0.9)]
me.materials.clear()
for n, c, r in MATS: me.materials.append(mat(n, c, r))
MI = {n: i for i, (n, _, _) in enumerate(MATS)}

# --- régions par os dominant
names = [g.name for g in h.vertex_groups]
def segdist(p, a, b):
    ab = b - a; t = max(0, min(1, (p - a).dot(ab) / ab.length_squared)); return (p - (a + ab * t)).length, t
bm = bmesh.new(); bm.from_mesh(me); dl = bm.verts.layers.deform.active; bm.faces.ensure_lookup_table()
eyeset = set()
for v in bm.verts:
    if any(names[g] in ('helper-l-eye', 'helper-r-eye') and w > 0.5 for g, w in v[dl].items()): eyeset.add(v.index)
region = {}
BONES = set(rig.data.bones.keys())
headC = B['head'][0]
knee = {s: B['calf_' + s][0] for s in 'lr'}
for f in bm.faces:
    c = f.calc_center_median()
    if all(v.index in eyeset for v in f.verts):
        side = 'l' if c.x > 0 else 'r'; ec = EYE[side]
        n = (c - ec).normalized(); region[f.index] = 'eye' if n.y < -0.86 else 'eyewhite'; continue
    acc = {}
    for v in f.verts:
        for g, w in v[dl].items():
            if names[g] in BONES or names[g] in ('scalp', 'lips'): acc[names[g]] = acc.get(names[g], 0) + w
    sc_ = acc.pop('scalp', 0); lp = acc.pop('lips', 0)
    dom = max(acc, key=acc.get) if acc else 'pelvis'
    r = 'skin'
    if lp > 2: region[f.index] = 'lip'; continue
    if dom in ('spine_01', 'spine_02', 'spine_03', 'clavicle_l', 'clavicle_r'): r = 'jersey'
    elif dom.startswith('upperarm'):
        s = dom[-1]; _, t = segdist(c, B['upperarm_' + s][0], B['upperarm_' + s][1]); r = 'jersey' if t < 0.55 else 'skin'
    elif dom == 'pelvis': r = 'shorts' if c.z < B['spine_01'][0].z + 0.03 else 'jersey'
    elif dom.startswith('thigh'):
        s = dom[-1]; _, t = segdist(c, B['thigh_' + s][0], B['thigh_' + s][1]); r = 'shorts' if t < 0.42 else ('pad' if abs(c.z - knee[s].z) < 0.065 else 'skin')
    elif dom.startswith('calf'):
        s = dom[-1]; _, t = segdist(c, B['calf_' + s][0], B['calf_' + s][1])
        r = 'pad' if abs(c.z - knee[s].z) < 0.065 else ('sock' if t > 0.62 else 'skin')
    elif dom.startswith('foot') or dom.startswith('ball'): r = 'shoe'
    elif dom in ('head', 'neck_01'):
        rel = c - headC; ey = (EYE['l'].z + EYE['r'].z) / 2
        front = c.y < headC.y - 0.035
        if sc_ > 2 or c.z > ey + 0.05 or (c.y > headC.y + 0.01 and c.z > ey - 0.02): r = 'hair'
        elif (c - MOUTH).length < 0.02 and front: r = 'lip'
    region[f.index] = r
for f in bm.faces: f.material_index = MI[region[f.index]]
from collections import Counter;print('REGIONS',Counter(region.values()));print('GROUPS',[n for n in names if not n.startswith('joint') and not n.startswith('helper')])

# --- vêtements : on détache chaque région et on la gonfle le long des normales
THICK = {'jersey': 0.009, 'shorts': 0.012, 'sock': 0.004, 'shoe': 0.024, 'pad': 0.02, 'hair': 0.007}
for rname, d in THICK.items():
    faces = [f for f in bm.faces if f.material_index == MI[rname]]
    if not faces: continue
    edges = {e for f in faces for e in f.edges if any(l.face.material_index != MI[rname] for l in e.link_loops)}
    bmesh.ops.split_edges(bm, edges=list(edges))
    bm.normal_update()
    vs = {v for f in bm.faces if f.material_index == MI[rname] for v in f.verts}
    for v in vs: v.co += v.normal * d
    if rname in ('shoe', 'hair'):
        bmesh.ops.smooth_vert(bm, verts=list(vs), factor=0.6, use_axis_x=True, use_axis_y=True, use_axis_z=True)
        bmesh.ops.smooth_vert(bm, verts=list(vs), factor=0.6, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    if rname == 'shoe':
        for v in vs:
            if v.co.z < 0.018: v.co.z = 0.0
        bm.normal_update()
        for f in bm.faces:
            if f.material_index == MI['shoe'] and f.normal.z < -0.5: f.material_index = MI['sole']
bm.to_mesh(me); bm.free()

dec = h.modifiers.new('dec', 'DECIMATE'); dec.ratio = 0.22
bpy.context.view_layer.objects.active = h
for m in list(h.modifiers):
    if m.type in ('DECIMATE',): bpy.ops.object.modifier_apply(modifier=m.name)
bpy.ops.object.shade_smooth()
tris = sum(len(p.vertices) - 2 for p in me.polygons)

# --- repères pour le jeu (numéros, longueur de jambe)
pts = [h.matrix_world @ v.co for v in me.vertices]
zc = B['spine_03'][0].z + 0.06
band = [p for p in pts if abs(p.z - zc) < 0.02 and abs(p.x) < 0.03]
back = max(band, key=lambda p: p.y); front = min(band, key=lambda p: p.y)
leg = (B['thigh_l'][0] - B['foot_l'][0]).length
info = {"backNum": [back.x, back.z, -back.y], "frontNum": [front.x, front.z + 0.06, -front.y], "legLen": leg,
        "pelvisH": B['pelvis'][0].z, "tris": tris, "thigh": (B['thigh_l'][0]-B['calf_l'][0]).length, "calf": (B['calf_l'][0]-B['foot_l'][0]).length, "ankle": B['foot_l'][0].z, "top": max(p.z for p in pts)}
bpy.context.scene["sideout"] = json.dumps(info)
print("INFO", json.dumps(info))
bpy.ops.export_scene.gltf(filepath='/tmp/claude-0/bl/mh_athlete.glb', export_format='GLB', export_skins=True, export_animations=False, export_extras=True)

# --- rendus de contrôle
sc = bpy.context.scene
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
for loc, en, rot in [((3, -3, 5), 3.0, (0.6, 0.2, 0.8)), ((-3, 2, 3), 1.2, (0.6, 0.2, -2.4))]:
    l = bpy.data.objects.new('l', bpy.data.lights.new('l', 'SUN')); l.data.energy = en; l.location = loc; l.rotation_euler = rot; sc.collection.objects.link(l)
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (0.06, 0.08, 0.11, 1)
sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.cycles.device = 'CPU'; sc.render.resolution_x = 420; sc.render.resolution_y = 560
top = max(p.z for p in pts)
cam.location = (1.5, -3.6, top * 0.55); cam.rotation_euler = (math.radians(90), 0, math.radians(22)); cam.data.lens = 50
sc.render.filepath = '/tmp/claude-0/bl/mh_full.png'; bpy.ops.render.render(write_still=True)
cam.location = (0.22, -0.62, headC.z + 0.06); cam.rotation_euler = (math.radians(90), 0, math.radians(20)); cam.data.lens = 85
sc.render.filepath = '/tmp/claude-0/bl/mh_face.png'; bpy.ops.render.render(write_still=True)
