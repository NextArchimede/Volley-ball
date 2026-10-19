# Side Out : gestes de volley construits en cinématique directe (FK) sur le squelette du joueur : chaque segment est orienté
# explicitement (direction + dos de la main), ce qui évite les torsions imprévisibles de l'IK.
# Exécuté dans scan_athlete.py après le transfert des animations capturées (variables : T = armature, J, H, shX, zA, legX, crotch, kneeZ).
import bpy
from mathutils import Vector, Euler
sc = bpy.context.scene
PZ = J['pelvis'][0].z
pb = T.pose.bones
ANK = J['calf_l'][1]
def V(x, y, z): return Vector((x, y, z))
SH = zA

# ===== Gestes en cinématique directe (FK) : chaque segment orienté explicitement =====
from mathutils import Matrix
import math as _m
T.animation_data.action = None
bpy.context.view_layer.update()
REST = {b.name: b.matrix_local.to_3x3() for b in T.data.bones}
def solve2(S, Wt, l1, l2, hint):
    d = Wt - S; dist = min(d.length, (l1 + l2) * 0.999); dn = d.normalized()
    h = (hint - dn * hint.dot(dn)).normalized()
    a = (l1 * l1 + dist * dist - l2 * l2) / (2 * dist); r = _m.sqrt(max(0.0, l1 * l1 - a * a))
    E = S + dn * a + h * r; Wr = S + dn * dist
    return E, Wr
def orient(name, ydir, refw, ref_rest_world):
    R0 = REST[name]; ly = Vector((0, 1, 0)); lr = (R0.inverted() @ ref_rest_world).normalized()
    lr = (lr - ly * lr.dot(ly)).normalized(); lc = ly.cross(lr)
    y = ydir.normalized(); b = (refw - y * refw.dot(y)).normalized(); c = y.cross(b)
    A = Matrix((y, b, c)).transposed(); Bm = Matrix((ly, lr, lc)).transposed()
    return A @ Bm.transposed()
def setw(name, R3):
    pbn = pb[name]; M = R3.to_4x4(); M.translation = pbn.head.copy(); pbn.matrix = M; bpy.context.view_layer.update()
LEN = {s: ((J['upperarm_' + s][1] - J['upperarm_' + s][0]).length, (J['lowerarm_' + s][1] - J['lowerarm_' + s][0]).length) for s in 'lr'}
LLEN = {s: ((J['thigh_' + s][1] - J['thigh_' + s][0]).length, (J['calf_' + s][1] - J['calf_' + s][0]).length) for s in 'lr'}
UP = Vector((0, 0, 1)); FWD = Vector((0, -1, 0))
# Sens de flexion du coude, mesuré sur les clips capturés (mouvement réel) : axe local du bras vers lequel l'avant-bras se replie
def flexdir(s):
    acc = Vector((0, 0, 0))
    for an in ('jog', 'idle', 'miss'):
        a = bpy.data.actions.get(an)
        if not a: continue
        T.animation_data.action = a
        for fr in range(int(a.frame_range[0]), int(a.frame_range[1]) + 1, 2):
            sc.frame_set(fr)
            U = pb['upperarm_' + s].matrix.to_3x3(); L = pb['lowerarm_' + s].matrix.to_3x3()
            f = U.inverted() @ (L @ Vector((0, 1, 0))); acc += Vector((f.x, 0, f.z))
    T.animation_data.action = None; sc.frame_set(1); bpy.context.view_layer.update()
    return acc.normalized()
FLEX = {s: flexdir(s) for s in 'lr'}
print('FLEX', {s: tuple(round(c, 2) for c in FLEX[s]) for s in 'lr'})
def frame3(ydir, refw, ly, lr):
    y = ydir.normalized(); b = (refw - y * refw.dot(y)).normalized(); c = y.cross(b)
    lr = (lr - ly * lr.dot(ly)).normalized(); lc = ly.cross(lr)
    return Matrix((y, b, c)).transposed() @ Matrix((ly, lr, lc)).transposed().transposed()
def arm(s, S, E, Wr, hint, bh):
    """Bras anatomique : le rouli du bras est imposé par le plan du coude (charnière), seule la pronation de l'avant-bras est libre."""
    u = (E - S).normalized(); f = (Wr - E).normalized(); ly = Vector((0, 1, 0))
    perp = f - u * f.dot(u)
    if perp.length < 0.08: perp = -(hint - u * hint.dot(u))   # bras tendu : le coude « s'ouvrirait » côté opposé à l'indice
    Ru = frame3(u, perp, ly, FLEX[s])
    ax = u.cross(f)
    Rf = (Matrix.Rotation(u.angle(f), 3, ax.normalized()) @ Ru) if ax.length > 1e-4 else Ru.copy()
    # pronation/supination : tourner l'avant-bras autour de son axe pour amener le dos de la main vers bh (limité)
    lb = REST['lowerarm_' + s].inverted() @ UP; lb = (lb - ly * lb.dot(ly)).normalized()
    cur = Rf @ lb; cur = (cur - f * cur.dot(f)).normalized(); want = (bh - f * bh.dot(f)).normalized()
    tw = _m.atan2(f.dot(cur.cross(want)), cur.dot(want)); tw = max(-1.4, min(1.4, tw))
    return Ru, Matrix.Rotation(tw, 3, f) @ Rf
def fk_pose(f, P):
    for n in pb.keys():
        pbn = pb[n]; pbn.rotation_mode = 'QUATERNION'; pbn.rotation_quaternion = (1, 0, 0, 0); pbn.location = (0, 0, 0)
    bpy.context.view_layer.update()
    p = pb['pelvis']; p.location = (0, -P.get('drop', 0), 0)
    p.rotation_quaternion = Euler((P.get('lean', 0) * 0.3, 0, 0)).to_quaternion()
    for n, a in (('spine_01', P.get('lean', 0) * 0.35), ('spine_02', P.get('lean', 0) * 0.35)):
        pb[n].rotation_quaternion = Euler((a, P.get('twist', 0) * 0.5, 0)).to_quaternion()
    pb['head'].rotation_quaternion = Euler((P.get('head', 0), 0, 0)).to_quaternion()
    bpy.context.view_layer.update()
    for s in 'lr':
        S = pb['upperarm_' + s].head.copy(); l1, l2 = LEN[s]
        E, Wr = solve2(S, P['w' + s], l1, l2, P['e' + s])
        Ru, Rf = arm(s, S, E, Wr, P['e' + s], P['bh' + s])
        setw('upperarm_' + s, Ru); setw('lowerarm_' + s, Rf)
        Hh = pb['thigh_' + s].head.copy(); l1, l2 = LLEN[s]
        K, A = solve2(Hh, P['a' + s], l1, l2, P.get('k' + s, FWD + UP * 0.2))
        setw('thigh_' + s, orient('thigh_' + s, K - Hh, FWD, FWD))
        setw('calf_' + s, orient('calf_' + s, A - K, FWD, FWD))
        Rf_ = REST['foot_' + s]; setw('foot_' + s, Rf_.copy())
    for n in pb.keys():
        pbn = pb[n]; pbn.keyframe_insert('rotation_quaternion', frame=f)
        if n == 'pelvis': pbn.keyframe_insert('location', frame=f)
def fk_clip(name, keys):
    old = bpy.data.actions.get(name)
    if old: bpy.data.actions.remove(old)
    act = bpy.data.actions.new(name); T.animation_data.action = act
    for f, P in keys: fk_pose(f, P)
    T.animation_data.action = None
    print('FK', name, keys[-1][0])
SX = J['upperarm_l'][0].x
def legs(wl=0.26, wr=-0.26, yl=0.0, yr=0.0, kh=0.25):
    return dict(al=V(wl, ANK.y + yl, ANK.z), ar=V(wr, ANK.y + yr, ANK.z), kl=V(kh + 0.45, -1, 0.25), kr=V(-kh - 0.45, -1, 0.25))
# Touche haute (passe) : mains en triangle au-dessus du front, coudes ouverts vers l'avant, dos des mains vers l'arrière
def setpose(zw, yw, drop, head=0.25):
    d = legs(0.24, -0.24); d.update(drop=drop, lean=0.0, head=head,
        wl=V(0.11, yw, zw), wr=V(-0.11, yw, zw), el=V(1, -0.35, -0.25), er=V(-1, -0.35, -0.25),
        bhl=V(0.2, 0.7, -0.5), bhr=V(-0.2, 0.7, -0.5)); return d
fk_clip('set', [(1, setpose(SH + 0.40, -0.17, 0.16)), (8, setpose(SH + 0.37, -0.15, 0.20)), (15, setpose(SH + 0.60, -0.26, 0.02, 0.3)), (24, setpose(SH + 0.58, -0.26, 0.0, 0.2))])
# Service flottant (droitier) : pied gauche devant, main gauche porte le ballon puis lance, bras droit armé coude haut, frappe devant-haut
def srv(wl, el_, wr, er_, bhr, twist, drop=0.04):
    d = legs(0.14, -0.20, -0.22, 0.12, 0.2); d.update(drop=drop, lean=0.08, twist=twist, head=0.25,
        wl=wl, el=el_, bhl=V(0.3, 0.2, -1), wr=wr, er=er_, bhr=bhr); return d
S_hold = srv(V(0.04, -0.42, SH - 0.22), V(0.6, 0.2, -1), V(-0.30, 0.10, SH + 0.24), V(-1, 0.5, -0.4), V(-0.2, 1, 0.2), 0.35)
S_toss = srv(V(0.03, -0.36, SH + 0.50), V(1, 0, 0), V(-0.32, 0.12, SH + 0.26), V(-1, 0.6, -0.3), V(-0.2, 1, 0.2), 0.40)
S_hit = srv(V(0.24, -0.18, SH - 0.40), V(1, 0, -0.5), V(-0.14, -0.22, SH + 0.66), V(-1, 0.2, 0.0), V(0, 1, 0.3), -0.10)
fk_clip('serve', [(1, S_hold), (10, S_toss), (16, S_hit), (26, S_hit)])

# Manchette : bras tendus joints devant le bassin, dos des mains vers le bas et l'extérieur, poussée des jambes
def bp(z, y, drop, lean, w=0.075):
    d = legs(0.32, -0.32, 0.0, 0.0, 0.3); d.update(drop=drop, lean=lean, head=-0.25,
        wl=V(w, y, z), wr=V(-w, y, z), el=V(1, 0, -0.4), er=V(-1, 0, -0.4),
        bhl=V(0.55, 0.1, -0.8), bhr=V(-0.55, 0.1, -0.8)); return d
fk_clip('bump', [(1, bp(PZ - 0.12, -0.70, 0.24, 0.55)), (9, bp(PZ - 0.04, -0.74, 0.18, 0.45)), (16, bp(PZ + 0.08, -0.72, 0.10, 0.35)),
                 (24, dict(legs(0.30, -0.30), drop=0.20, lean=0.4, head=-0.2, wl=V(0.28, -0.38, PZ + 0.05), wr=V(-0.28, -0.38, PZ + 0.05),
                           el=V(1, 0.4, -1), er=V(-1, 0.4, -1), bhl=V(0.7, 0.3, -0.6), bhr=V(-0.7, 0.3, -0.6)))])
# Attaque (droitier, en l'air) : bras gauche vise le ballon, bras droit armé coude haut, frappe bras tendu devant-haut, accompagnement vers la hanche gauche
def air(**kw):
    d = dict(al=V(0.16, ANK.y + 0.14, ANK.z + 0.26), ar=V(-0.16, ANK.y + 0.02, ANK.z + 0.16), kl=V(0.5, -1, 0.3), kr=V(-0.5, -1, 0.3), drop=0.0)
    d.update(kw); return d
A0 = air(lean=-0.10, twist=0.25, head=0.35, wl=V(0.20, -0.34, SH + 0.55), el=V(1, 0, -0.3), bhl=V(0.3, 0.9, 0.2),
         wr=V(-0.30, 0.12, SH + 0.30), er=V(-1, 0.5, -0.1), bhr=V(-0.2, 1, 0.3))
A1 = air(lean=-0.25, twist=0.50, head=0.35, chest=-0.1, wl=V(0.18, -0.38, SH + 0.50), el=V(1, 0, -0.3), bhl=V(0.3, 0.9, 0.2),
         wr=V(-0.26, 0.24, SH + 0.36), er=V(-1, 0.6, 0.0), bhr=V(-0.2, 1, 0.3))
A2 = air(lean=0.10, twist=-0.25, head=0.25, wl=V(0.22, -0.26, SH - 0.28), el=V(1, 0.2, -1), bhl=V(1, 0, 0),
         wr=V(-0.16, -0.16, SH + 0.72), er=V(-1, 0.3, 0.2), bhr=V(-0.1, 1, 0.3))
A3 = air(lean=0.45, twist=-0.40, head=0.0, wl=V(0.30, -0.06, PZ + 0.02), el=V(1, 0.3, -1), bhl=V(1, 0, 0),
         wr=V(0.08, -0.36, PZ + 0.18), er=V(-1, 0, -0.3), bhr=V(0, -1, 0.1))
fk_clip('spike', [(1, A0), (9, A1), (13, A2), (20, A3), (26, dict(A3, lean=0.3))])
# Contre : mains devant les épaules, puis bras tendus haut et vers l'avant au-dessus du filet, paumes vers le filet
def blk(z, y, drop, w=0.24, ankz=0.0, lean=0.05):
    d = legs(0.26, -0.26, 0.0, 0.0, 0.25); d['al'].z += ankz; d['ar'].z += ankz
    d.update(drop=drop, lean=lean, head=0.2, wl=V(w, y, z), wr=V(-w, y, z), el=V(1, 0.3, -1), er=V(-1, 0.3, -1),
             bhl=V(0.1, 1, 0.1), bhr=V(-0.1, 1, 0.1)); return d
fk_clip('block', [(1, blk(SH + 0.08, -0.24, 0.20)), (10, blk(SH + 0.88, -0.42, 0.0, 0.21, 0.04, -0.05)), (22, blk(SH + 0.88, -0.42, 0.0, 0.21, 0.04, -0.05)),
                  (30, blk(SH + 0.08, -0.24, 0.20))])
# Pas chassés vers la gauche (boucle de 16 images), position basse, mains prêtes devant le bassin
def shf(xl, xr, drop, zl=0.0, zr=0.0):
    d = legs(xl, xr, 0.0, 0.0, 0.3); d['al'].z += zl; d['ar'].z += zr
    d.update(drop=drop, lean=0.45, head=-0.2, wl=V(0.28, -0.40, PZ + 0.05), wr=V(-0.28, -0.40, PZ + 0.05),
             el=V(1, 0.4, -1), er=V(-1, 0.4, -1), bhl=V(0.7, 0.3, -0.6), bhr=V(-0.7, 0.3, -0.6)); return d
fk_clip('shuffleL', [(1, shf(0.30, -0.30, 0.24)), (5, shf(0.44, -0.28, 0.20, 0.06)), (9, shf(0.44, -0.16, 0.26)),
                     (13, shf(0.38, -0.22, 0.22, 0.0, 0.05)), (17, shf(0.30, -0.30, 0.24))])
