# Side Out : gestes de volley construits en cinématique inverse (IK) sur le squelette du joueur, puis cuits en animations.
# Exécuté dans scan_athlete.py après le transfert des animations capturées (variables : T = armature, J, H, shX, zA, legX, crotch, kneeZ).
import bpy
from mathutils import Vector, Euler
sc = bpy.context.scene
PZ = J['pelvis'][0].z
def emp(name):
    e = bpy.data.objects.new(name, None); sc.collection.objects.link(e); return e
TG = {k: emp('tg_' + k) for k in ('hl', 'hr', 'fl', 'fr', 'el', 'er', 'kl', 'kr')}
pb = T.pose.bones
CONS = []
def ik(bone, target, pole, chain=2, pole_angle=0.0):
    c = pb[bone].constraints.new('IK'); c.target = TG[target]; c.pole_target = TG[pole]; c.chain_count = chain; c.pole_angle = pole_angle
    CONS.append((bone, c))
ik('lowerarm_l', 'hl', 'el'); ik('lowerarm_r', 'hr', 'er'); ik('calf_l', 'fl', 'kl'); ik('calf_r', 'fr', 'kr')
ANK = J['calf_l'][1]
def V(x, y, z): return Vector((x, y, z))
# pose = dict(pel=(abaissement, inclinaison avant rad), hl, hr, fl, fr, el, er (coudes, pôles), kl, kr, spine=avant rad, twist=rad, head=rad)
def stance(w=0.30, drop=0.22, fy=0.0):
    return dict(fl=V(w, ANK.y + fy, ANK.z), fr=V(-w, ANK.y - fy, ANK.z), kl=V(w + 0.05, -1.0, 0.6), kr=V(-w - 0.05, -1.0, 0.6), drop=drop)
def apply(f, P):
    for k in ('hl', 'hr', 'fl', 'fr', 'el', 'er', 'kl', 'kr'):
        TG[k].location = P[k]; TG[k].keyframe_insert('location', frame=f)
    p = pb['pelvis']; p.rotation_mode = 'XYZ'; p.location = (0, -P['drop'], 0); p.rotation_euler = Euler((P.get('lean', 0) * 0.3, 0, 0))
    p.keyframe_insert('location', frame=f); p.keyframe_insert('rotation_euler', frame=f)
    for n, a in (('spine_01', P.get('lean', 0) * 0.35), ('spine_02', P.get('lean', 0) * 0.35)):
        b = pb[n]; b.rotation_mode = 'XYZ'; b.rotation_euler = Euler((a, P.get('twist', 0) * 0.5, 0)); b.keyframe_insert('rotation_euler', frame=f)
    b = pb['spine_03']; b.rotation_mode = 'XYZ'; b.rotation_euler = Euler((P.get('chest', 0), 0, 0)); b.keyframe_insert('rotation_euler', frame=f)
    b = pb['head']; b.rotation_mode = 'XYZ'; b.rotation_euler = Euler((P.get('head', 0), 0, 0)); b.keyframe_insert('rotation_euler', frame=f)
def P_(base, **kw):
    d = dict(base); d.update(kw); return d
SH = zA
ready = stance(0.32, 0.26)
GEST = {}
# Manchette : bras tendus joints devant le bassin, poussée des jambes
b0 = P_(ready, hl=V(0.10, -0.66, PZ - 0.12), hr=V(-0.10, -0.66, PZ - 0.12), el=V(0.45, -0.5, PZ - 0.7), er=V(-0.45, -0.5, PZ - 0.7), lean=0.55, head=-0.25)
b1 = P_(b0, drop=0.18, hl=V(0.10, -0.70, PZ - 0.02), hr=V(-0.10, -0.70, PZ - 0.02), lean=0.45)
b2 = P_(b0, drop=0.10, hl=V(0.10, -0.68, PZ + 0.10), hr=V(-0.10, -0.68, PZ + 0.10), lean=0.35)
GEST['g_bump'] = [(1, b0), (9, b1), (16, b2), (24, P_(ready, hl=V(0.3, -0.35, PZ + 0.05), hr=V(-0.3, -0.35, PZ + 0.05), el=V(0.6, 0, PZ - 0.2), er=V(-0.6, 0, PZ - 0.2), lean=0.4))]
# Passe : mains au-dessus du front, coudes ouverts, extension bras + jambes
s0 = P_(stance(0.24, 0.16), hl=V(0.09, -0.16, SH + 0.36), hr=V(-0.09, -0.16, SH + 0.36), el=V(0.6, -0.2, SH + 0.1), er=V(-0.6, -0.2, SH + 0.1), lean=0.05, head=0.25)
s1 = P_(s0, drop=0.12, hl=V(0.08, -0.20, SH + 0.40), hr=V(-0.08, -0.20, SH + 0.40))
s2 = P_(s0, drop=0.0, hl=V(0.07, -0.30, SH + 0.72), hr=V(-0.07, -0.30, SH + 0.72), head=0.3)
GEST['g_set'] = [(1, s0), (8, s1), (15, s2), (24, s2)]
# Attaque (en l'air) : armé, frappe haute devant, accompagnement vers la hanche gauche ; jambes repliées
air = dict(fl=V(0.18, ANK.y + 0.10, ANK.z + 0.22), fr=V(-0.16, ANK.y - 0.05, ANK.z + 0.12), kl=V(0.3, -1, 0.8), kr=V(-0.3, -1, 0.8), drop=0.0)
a0 = P_(air, hl=V(0.22, -0.30, SH + 0.50), hr=V(-0.28, -0.12, SH + 0.50), el=V(0.6, -0.2, SH), er=V(-0.6, 0.3, SH), lean=-0.1, twist=0.2, head=0.35)
a1 = P_(air, hl=V(0.20, -0.36, SH + 0.46), hr=V(-0.24, 0.20, SH + 0.36), el=V(0.6, -0.4, SH), er=V(-0.7, 0.4, SH + 0.5), lean=-0.25, twist=0.55, head=0.35, chest=-0.15)
a2 = P_(air, hl=V(0.18, -0.30, SH + 0.10), hr=V(-0.14, -0.28, SH + 0.52), el=V(0.6, -0.2, SH - 0.2), er=V(-0.5, 0.2, SH + 0.4), lean=0.1, twist=-0.35, head=0.25)
a3 = P_(air, hl=V(0.25, -0.15, PZ + 0.10), hr=V(0.12, -0.40, PZ + 0.15), el=V(0.6, 0, PZ - 0.2), er=V(-0.4, -0.4, PZ + 0.3), lean=0.45, twist=-0.4, head=0.0)
GEST['g_spike'] = [(1, a0), (9, a1), (13, a2), (20, a3), (26, P_(a3, lean=0.3))]
# Service flottant : lancer bras gauche, bras droit armé, frappe sèche devant-haut
v0 = P_(stance(0.22, 0.04, 0.18), hl=V(0.12, -0.40, SH - 0.25), hr=V(-0.30, 0.05, SH + 0.32), el=V(0.6, -0.2, SH - 0.5), er=V(-0.7, 0.4, SH + 0.3), lean=0.1, twist=0.3)
v1 = P_(v0, hl=V(0.10, -0.42, SH + 0.55), head=0.4)
v2 = P_(v0, hl=V(0.25, -0.25, SH - 0.15), hr=V(-0.14, -0.45, SH + 0.55), er=V(-0.5, 0.2, SH + 0.3), twist=-0.2, head=0.3)
GEST['g_serve'] = [(1, v0), (10, v1), (16, v2), (26, v2)]
# Contre : mains aux épaules puis bras tendus au-dessus du filet ; jambes tendues en l'air
k0 = P_(stance(0.26, 0.20), hl=V(0.24, -0.20, SH + 0.05), hr=V(-0.24, -0.20, SH + 0.05), el=V(0.7, 0, SH - 0.3), er=V(-0.7, 0, SH - 0.3), lean=0.1)
k1 = P_(dict(fl=V(0.2, ANK.y, ANK.z + 0.05), fr=V(-0.2, ANK.y, ANK.z + 0.05), kl=V(0.3, -1, 0.6), kr=V(-0.3, -1, 0.6), drop=0.0),
        hl=V(0.20, -0.32, SH + 0.82), hr=V(-0.20, -0.32, SH + 0.82), el=V(0.6, 0, SH + 0.3), er=V(-0.6, 0, SH + 0.3), lean=-0.05, head=0.2)
GEST['g_block'] = [(1, k0), (10, k1), (22, k1), (30, k0)]
# Pas chassés vers la gauche (boucle de 16 images), position basse
def sh_(f_l, f_r, d):
    return P_(stance(0.30, d), fl=V(f_l, ANK.y, ANK.z), fr=V(f_r, ANK.y, ANK.z), hl=V(0.28, -0.40, PZ + 0.05), hr=V(-0.28, -0.40, PZ + 0.05), el=V(0.7, 0, PZ - 0.2), er=V(-0.7, 0, PZ - 0.2), lean=0.45, head=-0.2)
GEST['g_shuffle'] = [(1, sh_(0.30, -0.30, 0.24)), (5, P_(sh_(0.44, -0.28, 0.20), fl=V(0.44, ANK.y, ANK.z + 0.06))), (9, sh_(0.44, -0.16, 0.26)),
                     (13, P_(sh_(0.38, -0.22, 0.22), fr=V(-0.22, ANK.y, ANK.z + 0.05))), (17, sh_(0.30, -0.30, 0.24))]
for gname, keys in GEST.items():
    act = bpy.data.actions.new(gname + '_src'); T.animation_data.action = act
    for e in TG.values():
        e.animation_data_clear()
    for f, P in keys: apply(f, P)
    f1 = keys[-1][0]
    bpy.ops.object.select_all(action='DESELECT'); T.select_set(True); bpy.context.view_layer.objects.active = T
    bpy.ops.object.mode_set(mode='POSE'); bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.nla.bake(frame_start=1, frame_end=f1, only_selected=True, visual_keying=True, clear_constraints=False, use_current_action=False, bake_types={'POSE'})
    baked = T.animation_data.action; baked.name = gname[2:] if gname != 'g_shuffle' else 'shuffleL'
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.data.actions.remove(act)
    print('GESTURE', baked.name, f1)
for bone, c in CONS: pb[bone].constraints.remove(c)
for e in TG.values(): bpy.data.objects.remove(e, do_unlink=True)
