# SirilJ

**Outils Python pour [Siril](https://siril.org/)** — une suite de scripts apportant à Siril des fonctions d'analyse et de mesure inspirées d'ImageJ.

*Python tools for Siril — a suite of scripts bringing ImageJ-style measurement and analysis features to Siril. (UI mostly in French; the Measure tool also ships in English.)*

Les scripts s'exécutent depuis **Siril → Scripts**, ouvrent une interface PyQt6 (thème sombre), et installent automatiquement leurs dépendances au premier lancement via `sirilpy.ensure_installed`.

---

## Scripts

| Script | Description | Doc |
|---|---|---|
| `SirilJ_Mesures_FR.py` / `SirilJ_Mesures_US.py` | **Mesures interactives** : distance, angle, aire, forme libre (« patate »), profil d'intensité R/G/B, statistiques de zone, sonde pixel. Conversions angulaires (WCS) et physiques, **calibration par diamètre d'objet** (Soleil, planètes…). FR et US. | [FR](SirilJ_Mesures_doc_FR.md) · [US](SirilJ_Mesures_doc_US.md) |
| `SirilJ_SolarAlign.py` | **Alignement de séquence solaire H-alpha** : recale la séquence courante par **StackReg** (portage de Thévenaz/EPFL) ou **ECC** (OpenCV), avec aperçu de la référence, conversion en séquence, empilement et chargement du résultat dans Siril. | [FR](SirilJ_SolarAlign_doc_FR.md) · [US](SirilJ_SolarAlign_doc_US.md) |
| `SirilJ_Analyse.py` | **Analyse d'image** : *Analyze Particles* (comptage/morphométrie : taches solaires, étoiles…) et *Surface Plot 3D* (relief d'intensité). | [FR](SirilJ_Analyse_doc_FR.md) · [US](SirilJ_Analyse_doc_US.md) |
| `SirilJ_Sequence.py` | **Outils de séquence** : *Make Montage* (planche-contact) et *Blink / Animation* (défilement + différence d'images pour repérer les objets mobiles). | [FR](SirilJ_Sequence_doc_FR.md) · [US](SirilJ_Sequence_doc_US.md) |

---

## Voir aussi

La chaîne complète de **traitement HDR d'éclipse solaire** — conversion RAW triée par
vitesse, alignement sur la Lune, empilement, fusion HDR, révélation de la couronne — est
dans le dépôt **[Eclipse_HDR](https://github.com/LaurentVoillot/Eclipse_HDR)**.

> **Vous cherchez l'alignement sur la Lune ?** Il est là-bas, dans
> [`scripts/SirilJ_Align.py`](https://github.com/LaurentVoillot/Eclipse_HDR/blob/main/scripts/SirilJ_Align.py) :
> malgré son préfixe « SirilJ », ce fichier appartient à Eclipse_HDR. Il offre deux modes,
> ☼ *Soleil — surface* (recalage multi-points par corrélation de phase et champ de
> déformation local) et ☾ *Éclipse — Lune* (recalage de poses de luminosités très
> différentes sur le disque lunaire).
>
> Le `SirilJ_SolarAlign.py` ci-dessus est l'aligneur solaire **d'origine**, par StackReg
> ou ECC — une transformation globale, sans mode Lune. Les deux approches restent
> valables ; elles ne recalent simplement pas de la même manière.

---

## Installation

1. Copier les fichiers de [`scripts/`](scripts/) dans le dossier de scripts de Siril :
   - **macOS** : `~/siril/scripts/` (ou le dossier configuré dans *Préférences → Scripts*)
   - **Linux** : `~/.siril/scripts/` ou `~/siril/scripts/`
   - **Windows** : le dossier scripts indiqué dans les préférences de Siril
2. Dans Siril : **Scripts → Rafraîchir**, puis lancer le script voulu.
3. Au premier lancement, les dépendances Python manquantes sont installées automatiquement.

> Pour que le bouton **Aide** des scripts Mesures retrouve la documentation complète, placer les fichiers `*_doc_*.md` dans `~/Claude/SirilJ/` (sinon une aide intégrée abrégée est affichée).

---

## Prérequis

- **Siril 1.3+** (avec son module Python `sirilpy`)
- **Python 3.10+**
- Dépendances installées automatiquement selon le script :
  `PyQt6`, `numpy`, `astropy`, `scipy`, `scikit-image`, `matplotlib`, `pystackreg`, `opencv-python`

---

## Correspondance avec ImageJ

| Fonction ImageJ | Script SirilJ |
|---|---|
| Measure, Plot Profile, ROI statistics | `SirilJ_Mesures` |
| StackReg / TurboReg, Z Project | `SirilJ_SolarAlign` |
| Analyze Particles, Surface Plot | `SirilJ_Analyse` |
| Make Montage, Animation, Image Calculator (difference) | `SirilJ_Sequence` |

---

## Crédits

- Moteur d'autostretch : *VeraLux Shared GUI Framework* (Riccardo Paterniti)
- StackReg / TurboReg : Philippe Thévenaz (EPFL)
- Bibliothèques : astropy, scipy, scikit-image, matplotlib, pystackreg, OpenCV, PyQt6

---

## Licence

[GPL-3.0-or-later](LICENSE). Chaque script porte l'en-tête `SPDX-License-Identifier: GPL-3.0-or-later`.
