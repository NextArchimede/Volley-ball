# Side Out : prépare un personnage généré par IA (GLB texturé, un seul maillage, T-pose)
# -> mis à l'échelle, allégé, squelette « game engine » (mêmes noms que le joueur MakeHuman),
#    maillot séparé pour la couleur d'équipe, animations capture de mouvement transférées.
import bpy, bmesh, math, json, sys
import numpy as np
from mathutils import Vector, Quaternion
IN = sys.argv[sys.argv.index('--in') + 1] if '--in' in sys.argv else '/tmp/claude-0/tr/in.glb'
OUT = '/tmp/claude-0/tr/scan.glb'
HGT = 1.92
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=IN)
ms = [o for o in bpy.data.objects if o.type == 'MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in ms: o.select_set(True)
bpy.context.view_layer.objects.active = ms[0]
if len(ms) > 1: bpy.ops.object.join()
body = bpy.context.view_layer.objects.active
body.parent = None
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
co = np.array([v.co[:] for v in body.data.vertices])
mn, mx = co.min(0), co.max(0)
s = HGT / (mx[2] - mn[2])
for v in body.data.vertices:
    v.co = Vector(((v.co.x - (mn[0] + mx[0]) / 2) * s, (v.co.y - (mn[1] + mx[1]) / 2) * s, (v.co.z - mn[2]) * s))
body.name = 'Body'
# --- nettoyage + allègement
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.remove_doubles(threshold=0.0005); bpy.ops.object.mode_set(mode='OBJECT')
d = body.modifiers.new('dec', 'DECIMATE'); d.ratio = 30000 / len(body.data.polygons); bpy.ops.object.modifier_apply(modifier='dec')
bpy.ops.object.shade_smooth()
H = HGT
co = np.array([v.co[:] for v in body.data.vertices]); X, Y, Z = co[:, 0], co[:, 1], co[:, 2]

# --- repères anatomiques mesurés sur le maillage
arm = co[np.abs(X) > 0.22 * H]; zA = float(np.median(arm[:, 2])); yA = float(np.median(arm[:, 1]))
tip = float(np.abs(X).max())
legs = co[(Z > 0.2 * H) & (Z < 0.3 * H) & (X > 0)]; legX = float(np.median(legs[:, 0])); legY = float(np.median(legs[:, 1]))
mid = co[(np.abs(X) < 0.012 * H) & (Z > 0.3 * H) & (Z < 0.62 * H)]; crotch = float(mid[:, 2].min())
chest = co[np.abs(Z - (zA - 0.09 * H)) < 0.01 * H]; torsoHalf = float(np.abs(chest[:, 0]).max()); yT = float(np.median(chest[:, 1]))
feet = co[(Z < 0.06 * H) & (X > 0)]; toeY = float(feet[:, 1].min()); heelY = float(feet[:, 1].max())
ankZ = 0.048 * H; ankY = heelY - 0.045 * H
shX = torsoHalf * 0.86; L = tip - shX
elX, wrX = shX + L * 0.42, shX + L * 0.76
pelZ = crotch + 0.045 * H; kneeZ = ankZ + (crotch - ankZ) * 0.52
print('MEASURE', dict(zA=round(zA, 3), tip=round(tip, 3), legX=round(legX, 3), crotch=round(crotch, 3), torsoHalf=round(torsoHalf, 3), toeY=round(toeY, 3)))
J = {}
J['pelvis'] = (Vector((0, yT, pelZ)), Vector((0, yT, pelZ + 0.06 * H)))
J['spine_01'] = (J['pelvis'][1], Vector((0, yT, pelZ + 0.13 * H)))
J['spine_02'] = (J['spine_01'][1], Vector((0, yT, zA - 0.12 * H)))
J['spine_03'] = (J['spine_02'][1], Vector((0, yT, zA + 0.015 * H)))
J['neck_01'] = (J['spine_03'][1], Vector((0, yT + 0.005 * H, 0.875 * H)))
J['head'] = (J['neck_01'][1], Vector((0, yT, H)))
for sd, sg in (('l', 1), ('r', -1)):
    J['clavicle_' + sd] = (Vector((sg * 0.02 * H, yT, zA - 0.005 * H)), Vector((sg * shX, yA, zA)))
    J['upperarm_' + sd] = (Vector((sg * shX, yA, zA)), Vector((sg * elX, yA, zA)))
    J['lowerarm_' + sd] = (Vector((sg * elX, yA, zA)), Vector((sg * wrX, yA, zA)))
    J['hand_' + sd] = (Vector((sg * wrX, yA, zA)), Vector((sg * (tip - 0.01 * H), yA, zA)))
    J['thigh_' + sd] = (Vector((sg * legX, legY, crotch + 0.035 * H)), Vector((sg * legX, legY - 0.005 * H, kneeZ)))
    J['calf_' + sd] = (J['thigh_' + sd][1], Vector((sg * legX, ankY, ankZ)))
    J['foot_' + sd] = (J['calf_' + sd][1], Vector((sg * legX, toeY + 0.06 * H, 0.018 * H)))
    J['ball_' + sd] = (J['foot_' + sd][1], Vector((sg * legX, toeY, 0.018 * H)))
PAR = {'spine_01': 'pelvis', 'spine_02': 'spine_01', 'spine_03': 'spine_02', 'neck_01': 'spine_03', 'head': 'neck_01'}
for sd in 'lr':
    PAR.update({f'clavicle_{sd}': 'spine_03', f'upperarm_{sd}': f'clavicle_{sd}', f'lowerarm_{sd}': f'upperarm_{sd}', f'hand_{sd}': f'lowerarm_{sd}',
                f'thigh_{sd}': 'pelvis', f'calf_{sd}': f'thigh_{sd}', f'foot_{sd}': f'calf_{sd}', f'ball_{sd}': f'foot_{sd}'})
arm_d = bpy.data.armatures.new('Rig'); rig = bpy.data.objects.new('Rig', arm_d); bpy.context.scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode='EDIT')
for n, (h, t) in J.items():
    b = arm_d.edit_bones.new(n); b.head = h; b.tail = t
for n, p in PAR.items(): arm_d.edit_bones[n].parent = arm_d.edit_bones[p]; arm_d.edit_bones[n].use_connect = False
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='DESELECT'); body.select_set(True); rig.select_set(True); bpy.context.view_layer.objects.active = rig
# poids : distance aux segments d'os, limitée au bon côté pour bras et jambes, 3 os max, lissée
names = list(J.keys())
P = np.array([v.co[:] for v in body.data.vertices])
def segd(P, a, b):
    a = np.array(a[:]); b = np.array(b[:]); ab = b - a; t = np.clip(((P - a) @ ab) / (ab @ ab), 0, 1)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1)
D = np.stack([segd(P, *J[n]) for n in names], 1)
side = np.sign(P[:, 0])
for i, n in enumerate(names):
    if n[-2:] in ('_l', '_r'):
        sg = 1 if n.endswith('_l') else -1
        bad = side != sg
        if n.startswith(('thigh', 'calf', 'foot', 'ball')): bad &= np.abs(P[:, 0]) > 0.02 * H
        if n.startswith(('upperarm', 'lowerarm', 'hand')): bad |= np.abs(P[:, 0]) < shX - 0.06 * H
        if n.startswith(('calf', 'foot', 'ball')): bad |= P[:, 2] > kneeZ + 0.12 * H
        D[bad, i] = 9.0
    if n in ('neck_01', 'head'): D[P[:, 2] < zA - 0.03 * H, i] = 9.0
    if n.startswith('clavicle'): D[:, i] += 0.03
Wt = 1.0 / (D ** 4 + 1e-9)
top = np.argsort(-Wt, 1)[:, :3]; M = np.zeros_like(Wt); rows = np.arange(len(P))[:, None]; M[rows, top] = Wt[rows, top]
M /= M.sum(1, keepdims=True)
for i, n in enumerate(names):
    g = body.vertex_groups.new(name=n)
    idx = np.nonzero(M[:, i] > 0.01)[0]
    for k in idx: g.add([int(k)], float(M[k, i]), 'REPLACE')
body.parent = rig
mod = body.modifiers.new('Armature', 'ARMATURE'); mod.object = rig
bpy.ops.object.select_all(action='DESELECT'); body.select_set(True); bpy.context.view_layer.objects.active = body
bpy.ops.object.mode_set(mode='WEIGHT_PAINT'); bpy.ops.object.vertex_group_smooth(group_select_mode='ALL', factor=0.5, repeat=3); bpy.ops.object.vertex_group_normalize_all(lock_active=False)
bpy.ops.object.mode_set(mode='OBJECT')
print('WEIGHTS ok')

# --- maillot séparé (couleur d'équipe) : faces grises claires du torse et des manches
mat0 = body.data.materials[0]; mat0.name = 'skin'
img = None
for nd in mat0.node_tree.nodes:
    if nd.type == 'TEX_IMAGE' and nd.image:
        if any(l.to_socket.name == 'Base Color' for l in nd.outputs['Color'].links): img = nd.image
w_, h_ = img.size; px = np.array(img.pixels[:]).reshape(h_, w_, 4)
jer = mat0.copy(); jer.name = 'jersey'; body.data.materials.append(jer)
uv = body.data.uv_layers.active.data
cnt = 0
for p in body.data.polygons:
    c = p.center
    if not (crotch + 0.07 * H < c.z < 0.83 * H and abs(c.x) < shX + 0.09 * H): continue
    u = sum(uv[i].uv[0] for i in p.loop_indices) / len(p.loop_indices); v = sum(uv[i].uv[1] for i in p.loop_indices) / len(p.loop_indices)
    r, g, b_, _ = px[min(h_ - 1, int(v * h_)) % h_, min(w_ - 1, int(u * w_)) % w_]
    mxc, mnc = max(r, g, b_), min(r, g, b_)
    if mxc > 0.35 and (mxc - mnc) < 0.07:
        p.material_index = 1; cnt += 1
print('JERSEY faces', cnt)

# --- repères pour le jeu
co = np.array([v.co[:] for v in body.data.vertices]); X, Y, Z = co[:, 0], co[:, 1], co[:, 2]
zc = zA - 0.1 * H; band = co[(np.abs(Z - zc) < 0.012 * H) & (np.abs(X) < 0.03 * H)]
B = {n: (rig.matrix_world @ rig.data.bones[n].head_local, rig.matrix_world @ rig.data.bones[n].tail_local) for n in J}
info = {"kind": "scan", "backNum": [0, zc, -float(band[:, 1].max())], "frontNum": [0, zc + 0.07 * H, -float(band[:, 1].min())],
        "thigh": (B['thigh_l'][0] - B['calf_l'][0]).length, "calf": (B['calf_l'][0] - B['foot_l'][0]).length, "top": H, "tris": len(body.data.polygons)}
bpy.context.scene["sideout"] = json.dumps(info); print("INFO", json.dumps(info))

# --- animations (même code que pour le joueur MakeHuman)
MX = '/tmp/claude-0/mx'
exec(open('/tmp/claude-0/tr/retarget_block.py').read())
for a_ in list(bpy.data.actions):
    if a_.name not in [c[0] for c in CLIPS]: bpy.data.actions.remove(a_)
T.animation_data.action = None
for pb in T.pose.bones: pb.rotation_quaternion = Quaternion(); pb.location = Vector()
bpy.context.scene.frame_set(1)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_skins=True, export_animations=True, export_animation_mode='ACTIONS', export_frame_step=2, export_extras=True, export_image_format='JPEG', export_image_quality=85)
print('EXPORTED')
