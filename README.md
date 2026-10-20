# Side Out

Jeu de volley-ball en 3D, 6 contre 6, jouable dans le navigateur (PC et mobile).
Simulation : physique du ballon avec traînée, effet et flottement, rotations en 5-1 avec libéro,
réception et passes intentionnelles, attaque, contre.

## Modes

- **Mode Joueur** : 4 contre 4, postes libres. Tu choisis ton joueur et tu ne contrôles que lui, caméra derrière toi ; l'IA joue tes coéquipiers.
- **Mode Équipe** : 6 contre 6 en 5-1 avec libéro et rotations ; tu contrôles le joueur qui touche le ballon.

## Lancer le jeu

Le jeu doit être servi par un petit serveur web (il charge le modèle des joueurs depuis `assets/`) :

```bash
python3 -m http.server 8000
```

puis ouvrir http://localhost:8000.

## Commandes (clavier + souris)

| Commande | Action |
|---|---|
| ZQSD (ou flèches) | Déplacement (WASD sur un clavier QWERTY : mêmes touches physiques) |
| Souris | Viser : le réticule au sol indique où part le ballon (service, réception, passe, attaque) |
| Clic gauche | Manchette ; service (lancer, puis frapper au sommet) ; frappe en plein saut. Maintenu en défense = plongeon |
| E | Passe / touche haute. En 2e touche, viser le camp adverse = deuxième main |
| Espace | Saut (attaque, ou course d'élan en aide pro) ; saut au contre |
| Clic droit en l'air | Balle placée (visée courte = feinte) |
| C / V | Changer de vue / afficher le cercle de chute |
| M / F | Couper le son / afficher les images par seconde |

Passe selon la zone visée dans son camp : côté gauche ou droit = balle haute (tout près du filet = tendue), milieu = centre rapide, derrière les 3 m = pipe.

Sur téléphone : joystick et boutons A Z E R (A touche, Z deuxième main / placée, E saut puis frappe, R service).

## Fichiers

- `index.html` : le jeu
- `labo-ballon.html` : banc d'essai des trajectoires du ballon
- `vestiaire.html` : premiers joueurs et animations (prototype)
- `assets/player.json` : modèle des joueurs (glTF, généré dans Blender)
- `assets/skin_*.jpg` : textures de peau
- `tools/` : scripts Blender qui génèrent les modèles (`makehuman_athlete2.py` = modèle actuel)

## Crédits et licences

- Joueur actuel : généré par IA (TRELLIS.2, Microsoft, licence MIT) à partir d'une image, puis riggé et animé dans Blender (`tools/scan_athlete.py`).
- Ancien joueur (MakeHuman) : corps, peaux, cheveux, sourcils, cils, yeux et chaussures : [MakeHuman](http://www.makehumancommunity.org) / MPFB2,
  packs « system assets », « skins02 », « hair01 », « eyebrows01 », tous sous licence CC0.
- Déplacement latéral et saut au contre : générés avec Cinevva Prompt Animations.
- Animations d'attente, de course, de plongeon et de réaction : capture de mouvement [Mixamo](https://www.mixamo.com) (Adobe), transférée sur le squelette du joueur et intégrée au modèle. Les fichiers Mixamo bruts ne sont pas redistribués ici.
- Moteur 3D : [three.js](https://threejs.org) (MIT), chargé depuis jsDelivr.
