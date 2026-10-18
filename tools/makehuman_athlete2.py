# Side Out : joueur réaliste MakeHuman (CC0) avec peau texturée, yeux, sourcils, cils, cheveux et baskets
# des packs officiels CC0, maillot/short/genouillères taillés sur le corps.
import bpy, bmesh, addon_utils, importlib, math, json, os, glob
from mathutils import Vector
A = '/tmp/claude-0/mhassets'
OUT = '/tmp/claude-0/bl'
bpy.ops.wm.read_factory_settings(use_empty=True)
addon_utils.enable("bl_ext.user_default.mpfb", default_set=True)
imp = lambda p, k: getattr(importlib.import_module("bl_ext.user_default." + p), k)
HumanService = imp("mpfb.services.humanservice", "HumanService")
HOP = imp("mpfb.entities.objectproperties", "HumanObjectProperties")
TargetService = imp("mpfb.services.targetservice", "TargetService")

h = HumanService.create_human()
for k, v in [("gender", 1.0), ("muscle", 0.78), ("height", 0.85), ("weight", 0.42), ("age", 0.42), ("proportions", 0.8)]:
    HOP.set_value(k, v, entity_reference=h)
TargetService.reapply_macro_details(h)
rig = HumanService.add_builtin_rig(h, "game_engine")
bpy.context.view_layer.update()

def mhclo(p, kind):
    o = HumanService.add_mhclo_asset(p, h, asset_type=kind, subdiv_levels=0, material_type="MAKESKIN")
    return o
HAIRS = ['short02', 'short04', 'culturalibre_hair_02', 'afro01']
assets = {
    'eyes': mhclo(f'{A}/eyes/low-poly/low-poly.mhclo', 'Eyes'),
    'brows': mhclo(f'{A}/eyebrows/eyebrow001/eyebrow001.mhclo', 'Eyebrows'),
    'lashes': mhclo(f'{A}/eyelashes/eyelashes01/eyelashes01.mhclo', 'Eyelashes'),
    'shoes': mhclo(f'{A}/clothes/shoes05/shoes05.mhclo', 'Clothes'),
}
for n in HAIRS: assets['hair_' + n] = mhclo(f'{A}/hair/{n}/{n}.mhclo', 'Hair')
bpy.context.view_layer.update()

def bake(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    if o.data.shape_keys: bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
    for m in list(o.modifiers):
        if m.type == 'MASK': o.modifiers.remove(m); continue
        if m.type != 'ARMATURE':
            try: bpy.ops.object.modifier_apply(modifier=m.name)
            except Exception as e: print('mod', o.name, m.name, e)
for o in [h] + list(assets.values()): bake(o)
for k, o in assets.items(): o.name = k

me = h.data
B = {b.name: (rig.matrix_world @ b.head_local, rig.matrix_world @ b.tail_local) for b in rig.data.bones}

# --- corps : retirer l'aide, subdiviser une fois
bm = bmesh.new(); bm.from_mesh(me); dl = bm.verts.layers.deform.active
gi = {g.name: g.index for g in h.vertex_groups}
helpers = {gi['HelperGeometry'], gi['JointCubes']}
bmesh.ops.delete(bm, geom=[v for v in bm.verts if any(g in helpers for g in v[dl].keys())], context='VERTS')
bm.to_mesh(me); bm.free()
bpy.ops.object.select_all(action='DESELECT'); h.select_set(True); bpy.context.view_layer.objects.active = h
sub = h.modifiers.new('sub', 'SUBSURF'); sub.levels = 1
bpy.ops.object.modifier_move_to_index(modifier='sub', index=0); bpy.ops.object.modifier_apply(modifier='sub')

# --- matériaux simples, compatibles glTF
def texmat(name, path, alpha=False, size=1024, rough=0.6, fmt='JPEG'):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; p = nt.nodes['Principled BSDF']
    p.inputs['Roughness'].default_value = rough
    if path:
        img = bpy.data.images.load(path); img.name = name + '_tex'
        if img.size[0] > size: img.scale(size, size)
        img.file_format = 'PNG' if alpha else fmt
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = img
        nt.links.new(t.outputs['Color'], p.inputs['Base Color'])
        if alpha:
            nt.links.new(t.outputs['Alpha'], p.inputs['Alpha'])
            try: m.surface_render_method = 'DITHERED'
            except Exception: pass
    return m
def flat(name, c, r=0.7):
    m = bpy.data.materials.new(name); m.use_nodes = True; p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*c, 1); p.inputs['Roughness'].default_value = r; return m
def first_png(d, key='diffuse'):
    c = [f for f in glob.glob(d + '/*.png') if 'normal' not in f and 'thumb' not in f]
    k = [f for f in c if key in f]; return (k or c)[0]

skinM = texmat('skin', first_png(f'{A}/skins/young_caucasian_male'), rough=0.55)
MATS = [skinM, flat('jersey', (0.05, 0.2, 0.75), 0.6), flat('shorts', (0.02, 0.03, 0.08), 0.7), flat('pad', (0.92, 0.92, 0.9), 0.8)]
me.materials.clear()
for m in MATS: me.materials.append(m)
MI = {m.name: i for i, m in enumerate(MATS)}

def segdist(p, a, b):
    ab = b - a; t = max(0, min(1, (p - a).dot(ab) / ab.length_squared)); return (p - (a + ab * t)).length, t
names = [g.name for g in h.vertex_groups]; BONES = set(rig.data.bones.keys())
knee = {s: B['calf_' + s][0] for s in 'lr'}
bm = bmesh.new(); bm.from_mesh(me); dl = bm.verts.layers.deform.active
for f in bm.faces:
    c = f.calc_center_median(); acc = {}
    for v in f.verts:
        for g, w in v[dl].items():
            if names[g] in BONES: acc[names[g]] = acc.get(names[g], 0) + w
    dom = max(acc, key=acc.get) if acc else 'pelvis'; r = 'skin'
    if dom in ('spine_01', 'spine_02', 'spine_03', 'clavicle_l', 'clavicle_r'): r = 'jersey'
    elif dom.startswith('upperarm'):
        s = dom[-1]; _, t = segdist(c, *B['upperarm_' + s]); r = 'jersey' if t < 0.55 else 'skin'
    elif dom == 'pelvis': r = 'shorts' if c.z < B['spine_01'][0].z + 0.03 else 'jersey'
    elif dom.startswith('thigh'):
        s = dom[-1]; _, t = segdist(c, *B['thigh_' + s]); r = 'shorts' if t < 0.42 else ('pad' if abs(c.z - knee[s].z) < 0.065 else 'skin')
    elif dom.startswith('calf'):
        s = dom[-1]; r = 'pad' if abs(c.z - knee[s].z) < 0.065 else 'skin'
    f.material_index = MI[r]
# pieds cachés par les baskets : supprimés pour éviter qu'ils traversent
feet = [f for f in bm.faces if f.calc_center_median().z < B['foot_l'][0].z + 0.02]
bmesh.ops.delete(bm, geom=feet, context='FACES')
THICK = {'jersey': 0.009, 'shorts': 0.012, 'pad': 0.02}
for rname, d in THICK.items():
    faces = [f for f in bm.faces if f.material_index == MI[rname]]
    edges = {e for f in faces for e in f.edges if any(l.face.material_index != MI[rname] for l in e.link_loops)}
    bmesh.ops.split_edges(bm, edges=list(edges)); bm.normal_update()
    for v in {v for f in bm.faces if f.material_index == MI[rname] for v in f.verts}: v.co += v.normal * d
bm.to_mesh(me); bm.free()
dec = h.modifiers.new('dec', 'DECIMATE'); dec.ratio = 0.3
bpy.ops.object.modifier_apply(modifier='dec'); bpy.ops.object.shade_smooth()

# --- matériaux des accessoires
def setmat(o, m):
    o.data.materials.clear(); o.data.materials.append(m)
setmat(assets['eyes'], texmat('eye', f'{A}/eyes/materials/brown_eye.png', size=256, rough=0.15))
setmat(assets['brows'], texmat('brow', f'{A}/eyebrows/eyebrow001/eyebrow001.png', alpha=True, size=256, rough=0.9))
setmat(assets['lashes'], texmat('lash', f'{A}/eyelashes/eyelashes01/eyelashes01.png', alpha=True, size=256, rough=0.9))
setmat(assets['shoes'], texmat('shoe', f'{A}/clothes/shoes05/shoes05_diffuse.png', size=512, rough=0.5))
for n in HAIRS: setmat(assets['hair_' + n], texmat('hair_' + n, first_png(f'{A}/hair/{n}'), alpha=True, size=512, rough=0.8))
for o in assets.values():
    if len(o.data.polygons) > 6000:
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        d = o.modifiers.new('dec', 'DECIMATE'); d.ratio = 6000 / len(o.data.polygons); bpy.ops.object.modifier_apply(modifier='dec')
    o.data.polygons.foreach_set('use_smooth', [True] * len(o.data.polygons))

# --- repères pour le jeu
pts = [h.matrix_world @ v.co for v in me.vertices]
zc = B['spine_03'][0].z + 0.06
band = [p for p in pts if abs(p.z - zc) < 0.02 and abs(p.x) < 0.04]
back = max(band, key=lambda p: p.y); front = min(band, key=lambda p: p.y)
tris = sum(len(p.vertices) - 2 for o in [h] + list(assets.values()) for p in o.data.polygons)
info = {"backNum": [0, back.z, -back.y], "frontNum": [0, front.z + 0.06, -front.y], "thigh": (B['thigh_l'][0] - B['calf_l'][0]).length,
        "calf": (B['calf_l'][0] - B['foot_l'][0]).length, "top": max(p.z for p in pts) + 0.03, "hairs": ['hair_' + n for n in HAIRS], "tris": tris}
bpy.context.scene["sideout"] = json.dumps(info); print("INFO", json.dumps(info))

# --- Animations Mixamo (capture de mouvement) transférées sur le squelette du joueur
from mathutils import Quaternion
MX = '/tmp/claude-0/mx'
MAP = {'pelvis': 'Hips', 'spine_01': 'Spine', 'spine_02': 'Spine1', 'spine_03': 'Spine2', 'neck_01': 'Neck', 'head': 'Head'}
for sd, SD in (('l', 'Left'), ('r', 'Right')):
    MAP.update({f'clavicle_{sd}': f'{SD}Shoulder', f'upperarm_{sd}': f'{SD}Arm', f'lowerarm_{sd}': f'{SD}ForeArm', f'hand_{sd}': f'{SD}Hand',
                f'thigh_{sd}': f'{SD}UpLeg', f'calf_{sd}': f'{SD}Leg', f'foot_{sd}': f'{SD}Foot', f'ball_{sd}': f'{SD}ToeBase'})
    for f_, F in (('thumb', 'Thumb'), ('index', 'Index'), ('middle', 'Middle'), ('ring', 'Ring'), ('pinky', 'Pinky')):
        for i in (1, 2, 3): MAP[f'{f_}_0{i}_{sd}'] = f'{SD}Hand{F}{i}'
print('SIDE', 'thigh_l x=', round(B['thigh_l'][0].x, 3))
# squelettes sources : Mixamo (FBX) et Cinevva (BVH)
REN_BVH = {'Spine': 'Spine1', 'Spine1': 'Spine2', 'Spine2': 'Chest', 'Neck': 'Neck1', 'LeftUpLeg': 'LeftLeg', 'LeftLeg': 'LeftShin', 'RightUpLeg': 'RightLeg', 'RightLeg': 'RightShin'}
def srcmap(kind):
    if kind == 'fbx': return {t: 'mixamorig:' + n for t, n in MAP.items()}, {k: 'mixamorig:' + k for k in ('Hips', 'LeftUpLeg', 'LeftLeg', 'LeftFoot')}
    return {t: REN_BVH.get(n, n) for t, n in MAP.items()}, {k: REN_BVH.get(k, k) for k in ('Hips', 'LeftUpLeg', 'LeftLeg', 'LeftFoot')}
T = rig; TWq = T.matrix_world.to_quaternion(); tb = T.data.bones
depth = lambda b: 0 if not b.parent else 1 + depth(b.parent)
order = sorted([b.name for b in tb], key=lambda n: depth(tb[n]))
restA = {b.name: b.matrix_local.to_quaternion() for b in tb}
restW = {n: TWq @ restA[n] for n in restA}
legT = (B['thigh_l'][0] - B['calf_l'][0]).length + (B['calf_l'][0] - B['foot_l'][0]).length
for pb in T.pose.bones: pb.rotation_mode = 'QUATERNION'
T.animation_data_create()
CLIPS = [('idle', 'idle.fbx', 1), ('diveL', 'dive.fbx', 1), ('diveR', 'dive2.fbx', 1), ('miss', 'miss.fbx', 1), ('jog', 'jog.fbx', 1), ('shuffleL', 'src_shuffle.bvh', 1), ('block', 'src_block.bvh', 1)]
# jog : un cycle de foulée (images 47→72) et cap figé (le clip d'origine tourne en rond)
CLIP_OPT = {'jog': {'range': (47, 72), 'unyaw': True}, 'shuffleL': {'range': (40, 63)}, 'block': {'range': (25, 72)}}
for cname, fname, step in CLIPS:
    before = set(bpy.data.objects)
    kind = 'bvh' if fname.endswith('.bvh') else 'fbx'
    if kind == 'fbx': bpy.ops.import_scene.fbx(filepath=f'{MX}/{fname}')
    else: bpy.ops.import_anim.bvh(filepath=f'{MX}/{fname}', global_scale=0.01)
    SMAP, SK = srcmap(kind)
    new = [o for o in bpy.data.objects if o not in before]
    src = [o for o in new if o.type == 'ARMATURE'][0]; SW = src.matrix_world; sb = src.data.bones
    f0, f1 = map(int, src.animation_data.action.frame_range)
    opt = CLIP_OPT.get(cname, {})
    if 'range' in opt: f0, f1 = opt['range']
    yaw0 = None
    if opt.get('unyaw'):  # cap de référence = celui de la première image du fichier (face avant)
        bpy.context.scene.frame_set(1); hq = (SW @ src.pose.bones[SK['Hips']].matrix).to_quaternion(); fw = hq @ Vector((0, 0, 1)); yaw0 = math.atan2(fw.x, fw.y)
    align = {}
    for t, sname in MAP.items():
        if t not in tb or SMAP[t] not in sb: continue
        qs = (SW @ sb[SMAP[t]].matrix_local).to_quaternion()
        ds = qs @ Vector((0, 1, 0)); dt_ = restW[t] @ Vector((0, 1, 0))
        align[t] = (qs.inverted(), dt_.rotation_difference(ds))
    hipRest = (SW @ sb[SK['Hips']].matrix_local).translation
    legS = ((SW @ sb[SK['LeftUpLeg']].matrix_local).translation - (SW @ sb[SK['LeftLeg']].matrix_local).translation).length + \
           ((SW @ sb[SK['LeftLeg']].matrix_local).translation - (SW @ sb[SK['LeftFoot']].matrix_local).translation).length
    act = bpy.data.actions.new(cname); act.use_fake_user = True; T.animation_data.action = act
    for f in range(f0, f1 + 1, step):
        bpy.context.scene.frame_set(f)
        poseA = {}; Rfix = Quaternion()
        if opt.get('unyaw'):
            hq = (SW @ src.pose.bones[SK['Hips']].matrix).to_quaternion(); fw = hq @ Vector((0, 0, 1)); yw = math.atan2(fw.x, fw.y)
            if yaw0 is None: yaw0 = yw
            Rfix = Quaternion((0, 0, 1), yw - yaw0)
        kf = f - f0 + 1
        for n in order:
            b = tb[n]; par = b.parent.name if b.parent else None
            if n in align:
                qSW = Rfix @ (SW @ src.pose.bones[SMAP[n]].matrix).to_quaternion()
                si, qa = align[n]
                qA = TWq.inverted() @ (qSW @ si @ qa @ restW[n])
            else:
                qA = (poseA[par] @ (restA[par].inverted() @ restA[n])) if par else restA[n]
            poseA[n] = qA
            basis = ((restA[par].inverted() @ restA[n]).inverted() @ poseA[par].inverted() @ qA) if par else (restA[n].inverted() @ qA)
            pb = T.pose.bones[n]; pb.rotation_quaternion = basis; pb.keyframe_insert('rotation_quaternion', frame=kf)
        hipW = (SW @ src.pose.bones[SK['Hips']].matrix).translation
        dz = (hipW.z - hipRest.z) * legT / legS
        off = TWq.inverted() @ Vector((0, 0, dz))
        pp = T.pose.bones['pelvis']; pp.location = restA['pelvis'].inverted() @ off; pp.keyframe_insert('location', frame=kf)
    print('CLIP', cname, f0, f1)
    for o in new: bpy.data.objects.remove(o, do_unlink=True)
for a_ in list(bpy.data.actions):
    if a_.name not in [c[0] for c in CLIPS]: bpy.data.actions.remove(a_)
T.animation_data.action = None
for pb in T.pose.bones: pb.rotation_quaternion = Quaternion(); pb.location = Vector()
bpy.context.scene.frame_set(1)

bpy.ops.export_scene.gltf(filepath=f'{OUT}/mh2.glb', export_format='GLB', export_skins=True, export_animations=True, export_animation_mode='ACTIONS', export_frame_step=2, export_extras=True, export_image_format='AUTO')

# --- peaux alternatives pour varier les joueurs
from PIL import Image
for n in ['young_caucasian_male', 'young_african_male', 'young_asian_male', 'middleage_caucasian_male', 'toigo_light_skin_male_bronze']:
    try: Image.open(first_png(f'{A}/skins/{n}')).convert('RGB').resize((1024, 1024), Image.LANCZOS).save(f'{OUT}/skin_{n}.jpg', quality=85)
    except Exception as e: print('skin', n, e)

# --- rendus de contrôle (une seule coupe visible)
for n in HAIRS[1:]: assets['hair_' + n].hide_render = True
sc = bpy.context.scene
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
for loc, en, rot in [((3, -3, 5), 3.0, (0.6, 0.2, 0.8)), ((-3, 2, 3), 1.2, (0.6, 0.2, -2.4))]:
    l = bpy.data.objects.new('l', bpy.data.lights.new('l', 'SUN')); l.data.energy = en; l.location = loc; l.rotation_euler = rot; sc.collection.objects.link(l)
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (0.06, 0.08, 0.11, 1)
sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.cycles.device = 'CPU'; sc.render.resolution_x = 420; sc.render.resolution_y = 560
top = info['top']; headC = B['head'][0]
cam.location = (1.5, -3.6, top * 0.55); cam.rotation_euler = (math.radians(90), 0, math.radians(22)); cam.data.lens = 50
sc.render.filepath = f'{OUT}/mh2_full.png'; bpy.ops.render.render(write_still=True)
cam.location = (0.25, -0.75, headC.z + 0.08); cam.rotation_euler = (math.radians(90), 0, math.radians(18)); cam.data.lens = 85
sc.render.filepath = f'{OUT}/mh2_face.png'; bpy.ops.render.render(write_still=True)
