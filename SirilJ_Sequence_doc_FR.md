# SirilJ Séquence — Guide d'utilisation

**Version 1.0**  
Deux outils sur la séquence courante de Siril, sans équivalent natif : **Montage** (équivalent ImageJ *Make Montage*) et **Blink / Animation** (équivalent ImageJ *Animation* + différence d'images).

---

## Prérequis

| Composant | Version |
|---|---|
| Siril | 1.3 ou ultérieur |
| Python (via sirilpy) | 3.10 ou ultérieur |
| numpy, astropy | récents |
| PyQt6 | récent |

Les dépendances sont installées automatiquement au premier lancement.

---

## Lancement

1. Dans Siril, charger une **séquence de FITS individuels** (Conversion sans l'option FITSEQ, ou *Ouvrir une séquence*).
2. **Script → Exécuter un script** → `SirilJ_Sequence.py`.
3. La séquence courante est détectée automatiquement. Bouton **⟳ Rafraîchir** après tout changement côté Siril.

> ⚠ **Séquences mono-fichier non prises en charge.** FITSEQ (un seul `.fits`) ou SER : reconvertir en FITS individuels puis ⟳ Rafraîchir.
>
> Les frames couleur sont traitées en **luminance** (moyenne des canaux).

---

## Onglet ▦ Montage

Assemble les frames en une planche-contact (grille) — rotation planétaire, time-lapse, aperçu de séquence.

| Réglage | Rôle |
|---|---|
| **Début / Fin / Pas** | Plage de frames et échantillonnage |
| **Colonnes** | Nombre de colonnes de la grille |
| **Échelle** | Réduction de chaque vignette (1/1 → 1/16) |
| **Bordure (px)** | Espace entre vignettes |
| **Bordure** | Couleur des bordures (noir / blanc / gris) |
| **Étirement par frame** | Autostretch indépendant par vignette (sinon étirement global) |

Le bouton **Construire le montage** assemble la planche et l'affiche (zoom molette, déplacement glisser).  
Le bouton **Enregistrer + charger dans Siril** sauvegarde la planche en FITS et la charge dans Siril.

> Mémoire : sur de longues séquences, augmentez le **pas** ou réduisez l'**échelle** pour limiter la taille de la planche.

---

## Onglet ▶ Blink / Animation

Fait défiler les frames pour repérer les objets mobiles (astéroïdes, novæ, comètes) ou les variations.

### Transport

| Contrôle | Effet |
|---|---|
| **◀ / ▶** | Image précédente / suivante |
| **▶ Lecture / ⏸ Pause** | Animation en boucle |
| **Curseur d'image** | Aller directement à une frame |
| **Vitesse** | 1 à 30 images/seconde |

### Modes

| Mode | Effet |
|---|---|
| **Normal** | Affiche chaque frame (autostretch) |
| **Différence avec réf.** | Frame − frame de référence : un mobile apparaît en doublet clair/sombre |
| **Différence avec précédente** | Frame − frame précédente : met en évidence tout déplacement entre images consécutives |

Le bouton **Définir la frame courante comme réf.** fixe l'image de référence du mode différence.  
En mode différence, l'image est centrée sur le gris (50 %) : le **noir/blanc** marque les écarts négatifs/positifs.

> **Méthode pour chercher un astéroïde :** aligner d'abord la séquence sur les étoiles (voir *SirilJ SolarAlign* ou l'alignement de Siril), puis passer en **Différence avec réf.** — les étoiles fixes disparaissent, seul l'objet mobile « clignote ».

---

## Notes & conseils

- Les frames sont mises en cache (LRU) pour fluidifier la lecture ; la première passe peut être plus lente.
- Le **montage** enregistré est une image de présentation (luminance étirée), pas une donnée photométrique.
- Les données originales de la séquence ne sont **jamais modifiées**.

---

## Correspondance avec ImageJ

| Fonction ImageJ | Équivalent ici |
|---|---|
| **Image → Stacks → Make Montage** | Onglet Montage |
| **Image → Stacks → Animation (Start/Stop)** | Onglet Blink — Lecture/Pause + vitesse |
| **Image → Stacks → Tools → Blink** | Onglet Blink — modes de différence |
| **Process → Image Calculator (Difference)** | Modes *Différence avec réf./précédente* |
