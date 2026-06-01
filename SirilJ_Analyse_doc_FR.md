# SirilJ Analyse — Guide d'utilisation

**Version 1.0**  
Deux outils d'analyse sur l'image courante de Siril, sans équivalent natif : **Analyse de particules** (équivalent ImageJ *Analyze Particles*) et **Surface 3D** (équivalent ImageJ *Surface Plot*).

---

## Prérequis

| Composant | Version |
|---|---|
| Siril | 1.3 ou ultérieur |
| Python (via sirilpy) | 3.10 ou ultérieur |
| numpy, astropy, scipy | récents |
| scikit-image | récent |
| matplotlib | récent |
| PyQt6 | récent |

Les dépendances sont installées automatiquement au premier lancement.

---

## Lancement

1. Ouvrir une image dans Siril.
2. **Script → Exécuter un script** → `SirilJ_Analyse.py`.
3. L'image courante est chargée automatiquement (bouton **⟳ Recharger l'image** pour la rafraîchir).

> L'image affichée est un **aperçu autostretch**. Les mesures d'intensité portent sur les **données brutes** ; le seuillage, lui, s'effectue sur l'image étirée (cohérent avec ce que l'on voit).

---

## Onglet ⬤ Particules

Détecte et mesure les objets d'une image : taches solaires, étoiles, cratères, galaxies…

### Réglages

| Réglage | Rôle |
|---|---|
| **Seuil automatique (Otsu)** | Calcule un seuil optimal automatiquement |
| **Seuil** (curseur) | Seuil manuel [0–1] sur l'image étirée (si Otsu décoché) |
| **Polarité** | *Objets clairs / fond sombre* (étoiles) ou *Objets sombres / fond clair* (taches solaires) |
| **Aire min / max (px²)** | Filtre de taille (max = 0 → pas de limite) |
| **Circularité min** | 1.0 = cercle parfait ; 0 = aucun filtre |
| **Exclure objets aux bords** | Ignore les objets coupés par le cadre |

### Résultats

Tableau trié par aire décroissante : **#, Aire px², Aire arcsec²** (si astrométrie), **X, Y** (coordonnées FITS), **Circularité, Intensité moyenne**. Les objets sont entourés sur l'image avec leur numéro.

Le panneau de gauche affiche le **nombre d'objets**, le **seuil retenu** et l'**aire totale**.

### Export CSV

Le bouton **Exporter CSV…** enregistre toutes les mesures (aire, aire arcsec² si WCS, X/Y, diamètre équivalent, circularité, excentricité, intensité moyenne et max).

### Exemples d'usage

- **Comptage de taches solaires** : polarité *Objets sombres / fond clair*, circularité min ~0.3.
- **Comptage d'étoiles** : polarité *Objets clairs / fond sombre*, aire min ~3 px².
- **Mesure d'une galaxie/nébuleuse** : un seul objet, lire son aire en arcsec².

---

## Onglet ⛰ Surface 3D

Représente l'intensité de l'image en relief — utile pour visualiser un cœur de galaxie, une PSF d'étoile, le profil d'une nébuleuse.

| Réglage | Rôle |
|---|---|
| **Résolution** | Côté max de la grille sous-échantillonnée (20–400) |
| **Palette** | viridis, inferno, magma, plasma, gray, hot, jet, cividis |
| **Échelle logarithmique** | Comprime la dynamique (révèle les extensions faibles) |
| **Appliquer l'autostretch** | Trace l'intensité étirée plutôt que linéaire |

La barre d'outils matplotlib permet de **pivoter, zoomer et enregistrer** le graphe en image.

> Pour les grandes images, baissez la résolution (la grille est réduite par moyenne de blocs avant le rendu).

---

## Notes & conseils

- Les coordonnées **X/Y** suivent la convention FITS (X depuis la gauche, Y depuis le bas), comme la sonde de *SirilJ Mesures*.
- Le **nombre d'objets** dépend fortement du seuil : ajustez Otsu ↔ manuel et la circularité.
- Les données originales de Siril ne sont **jamais modifiées**.

---

## Correspondance avec ImageJ

| Fonction ImageJ | Équivalent ici |
|---|---|
| **Analyze → Analyze Particles** | Onglet Particules (aire, circularité, centroïde, intensité, comptage, CSV) |
| **Analyze → Set Measurements** | Colonnes du tableau / CSV |
| **Image → Adjust → Threshold** | Seuil Otsu / manuel + polarité |
| **Analyze → Surface Plot** | Onglet Surface 3D |
