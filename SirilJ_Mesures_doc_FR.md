# SirilJ Mesures — Guide d'utilisation

**Version 1.4**  
Outils de mesure interactifs pour Siril : distance, angle, aire, forme libre, profil d'intensité, statistiques de zone — avec conversion astrométrique, conversion physique, et **calibration par diamètre d'objet** (Système Solaire).

---

## Prérequis

| Composant | Version |
|---|---|
| Siril | 1.3 ou ultérieur |
| Python (via sirilpy) | 3.10 ou ultérieur |
| PyQt6 | récent |
| numpy | récent |
| astropy | récent |

Les dépendances sont installées automatiquement au premier lancement via `sirilpy.ensure_installed`.

Deux versions sont fournies, au code identique, seule la langue change :
- `SirilJ_Mesures_FR.py` — interface française, nombres au format **18 407,50** (espace milliers, virgule décimale)
- `SirilJ_Mesures_US.py` — interface anglaise, nombres au format **18,407.50**

---

## Lancement

1. Ouvrir une image dans Siril.
2. **Script → Exécuter un script** → `SirilJ_Mesures_FR.py`.
3. La fenêtre s'ouvre et charge l'image courante automatiquement.

> Pour les mesures **angulaires**, l'image doit avoir été **résolue astrométriquement** (outil Astrométrie de Siril). Sans solution, le script fonctionne en mode pixel — et la **calibration d'objet** (ci-dessous) permet quand même d'obtenir des dimensions physiques, sans astrométrie.

---

## Présentation de l'interface

```
┌──────────────────┬────────────────────────────────────────────┐
│  Outils          │  Zone image (zoom / déplacement)            │
│  Dist. physique  │                                             │
│  Calibration obj │                                             │
│  Badge WCS       ├────────────────────────────────────────────┤
│  Sonde pixel     │  Journal des résultats (3 lignes, défilable)│
│  Au-dessus/Aide/ │                                             │
│  Fermer          │                                             │
└──────────────────┴────────────────────────────────────────────┘
```

Tous les tracés de mesure sont en **bleu** ; les points cliqués sont marqués par un **point rouge**.

### Zoom & déplacement
| Action | Effet |
|---|---|
| Molette | Zoom avant / arrière |
| Clic + glisser | Déplacement (quand aucun outil n'est actif) |
| **−** / **+** | Zoom ×1.2 |
| **Fit** | Ajuster à la fenêtre |
| **1:1** | Taille native |

---

## Outils

### ╱ Ligne — distance
2 clics. Résultats : pixels (toujours), angulaire (si astrométrie), physique (si distance saisie **ou** objet calibré).
`Ligne  :  1 247,3 px  |  4,23'  |  20 000 km`

### ∠ Angle — angle
3 clics : **A** (premier bras), **B** (sommet), **C** (second bras). Angle 2-D + angle vrai sur le ciel (`sky`, si astrométrie).
`Angle  :  47° 12' 08,3"  |  sky 47° 11' 52,1"`

### ⬡ Aire — surface (polygone)
Cliquer les sommets ; **double-clic** ou **clic droit** pour clore. Aire pixel, angulaire (si astrométrie), physique (si distance ou objet calibré).
`Aire   :  84 320 px²  |  1,247 arcmin²`

### 〰 Patate — forme libre
**Cliquer-glisser** librement pour tracer une forme quelconque ; **relâcher** pour clore. Mêmes résultats que l'outil Aire.
`Patate :  44 020 px²  |  9 360 000 km²`

### 〜 Profil — profil d'intensité
2 clics. Ouvre une fenêtre traçant l'intensité R/G/B le long du segment (interpolation bilinéaire).

### ▣ Stats ROI — statistiques de zone
Cliquer-glisser un rectangle. Moyenne, médiane, min, max, écart-type par canal, sur les **données FITS brutes** [0,1].

---

## Sonde pixel

Toujours active. Survoler l'image affiche en temps réel les coordonnées (convention FITS : X depuis la gauche, Y depuis le bas) et les valeurs R/G/B du pixel.

---

## Conversion en distance physique (astrométrie)

Saisir la distance à l'objet dans le panneau **Distance physique** pour convertir les mesures angulaires en tailles/surfaces physiques.

| Unité d'entrée | Usage |
|---|---|
| km / AU | Système Solaire |
| ly / pc | Étoiles, nébuleuses |
| kpc / Mpc | Objets galactiques, galaxies |

Unité de sortie choisie automatiquement (km → AU → ly → kly → Mly, et les surfaces correspondantes).

---

## ◎ Calibration par diamètre d'objet (Système Solaire)

Permet d'obtenir des dimensions physiques **sans astrométrie** — idéal pour le Soleil, la Lune et les planètes.

**Principe :** on connaît le diamètre réel de l'objet ; en traçant ce diamètre sur l'image, on en déduit l'échelle **km/pixel**.

**Mode d'emploi :**
1. Choisir l'objet dans la liste : **Soleil, Lune, Mercure, Vénus, Terre, Mars, Jupiter, Saturne, Uranus, Neptune**, ou **Personnalisé…** (saisir le diamètre en km).
2. Cliquer **◎ Tracer le diamètre**, puis tracer le diamètre de l'objet (2 clics).
3. L'échelle **km/px** s'affiche et se mémorise :
   `Calib  :  Ø 1 391 400 km  →  1 234,5 km/px`
4. Ensuite, **toute** mesure donne sa dimension physique :
   - une **ligne** → longueur en km
   - une **aire / patate** → surface en km²

**Exemple — taches solaires :** tracer le diamètre du Soleil, puis tracer une tache :
`Patate :  44 020 px²  |  9 360 000 km²`

Diamètres équatoriaux utilisés (km) : Soleil 1 391 400 · Lune 3 475 · Mercure 4 879 · Vénus 12 104 · Terre 12 742 · Mars 6 779 · Jupiter 139 820 · Saturne 116 460 · Uranus 50 724 · Neptune 49 244.

> L'échelle de calibration **persiste** après « Tout effacer » : calibrez une fois, mesurez autant que voulu. Elle est indépendante de l'astrométrie et s'ajoute aux autres conversions.

---

## Journal des résultats

Chaque mesure est ajoutée au journal défilable et envoyée à la **console de Siril**. **Tout effacer** supprime les tracés et vide le journal (mais conserve la calibration).

---

## Badge WCS

| Badge | Signification |
|---|---|
| `WCS ✓  0,452"/px` | Solution astrométrique trouvée ; échelle affichée |
| `Pas d'astrométrie — pixels seulement` | Mesures en pixels (la calibration d'objet reste disponible) |

---

## Bouton Aide

Le bouton **?** ouvre cette documentation. Cherche d'abord `SirilJ_Mesures_doc_FR.md` dans le répertoire du script puis dans `~/Claude/SirilJ/` ; affiche une aide intégrée en dernier recours.

---

## Notes & conseils

- **Tous les tracés sont en bleu** (`#0000FF`), lisibles sur fond clair comme le disque solaire ; les points cliqués sont rouges. La ligne et la calibration utilisent un trait d'épaisseur constante à l'écran (lisible à tout zoom).
- **Format des nombres** : FR `18 407,50` (espace + virgule) ; US `18,407.50`.
- Les mesures **s'accumulent** ; seul **Tout effacer** les supprime.
- L'image affichée est un **aperçu autostretch** ; les données originales ne sont pas modifiées.
- Profil et Stats ROI opèrent sur les **données FITS brutes** [0,1].
- Tous les résultats sont aussi envoyés à la **console de script Siril**.
