# Side Out

Jeu de volley-ball en 3D, 6 contre 6, jouable dans le navigateur (PC et mobile).
Simulation : physique du ballon avec traînée, effet et flottement, rotations en 5-1 avec libéro,
réception et passes intentionnelles, attaque, contre.

## Lancer le jeu

Le jeu doit être servi par un petit serveur web (il charge le modèle des joueurs depuis `assets/`) :

```bash
python3 -m http.server 8000
```

puis ouvrir http://localhost:8000.

## Commandes (clavier)

| Touche | Action |
|---|---|
| Flèches | Direction (déplacement, visée, choix de passe/réception) |
| A | Manchette (maintenir = plongeon ; en aide pro, pas d'appel avant la frappe adverse) |
| Z | Touche haute : passe, réception haute ; en l'air = balle placée (↓ = feinte) |
| E | Saut (ou course d'élan en aide pro), puis 2e appui = frappe ; saut au contre |
| R | Service : lancer, puis frapper au sommet |
| C / V | Changer de vue / afficher le cercle de chute |

## Fichiers

- `index.html` : le jeu
- `labo-ballon.html` : banc d'essai des trajectoires du ballon
- `vestiaire.html` : premiers joueurs et animations (prototype)
- `assets/player.json` : modèle des joueurs (glTF, généré dans Blender)
- `assets/skin_*.jpg` : textures de peau
- `tools/` : scripts Blender qui génèrent les modèles (`makehuman_athlete2.py` = modèle actuel)

## Crédits et licences

- Corps, peaux, cheveux, sourcils, cils, yeux et chaussures : [MakeHuman](http://www.makehumancommunity.org) / MPFB2,
  packs « system assets », « skins02 », « hair01 », « eyebrows01 », tous sous licence CC0.
- Moteur 3D : [three.js](https://threejs.org) (MIT), chargé depuis jsDelivr.
