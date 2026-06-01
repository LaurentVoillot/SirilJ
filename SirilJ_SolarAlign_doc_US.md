# SirilJ Solar Align — User Guide

**Version 2.0**  
Aligns Siril's current solar H-alpha sequence with StackReg or ECC, then converts, stacks and loads the result directly in Siril.

> **Note:** this script's interface is in **French**. This guide explains it in English; the actual French button labels are shown in **bold** with an English gloss.

---

## Requirements

| Component | Version |
|---|---|
| Siril | 1.3 or later |
| Python (via sirilpy) | 3.10 or later |
| PyQt6, numpy, astropy | recent |
| pystackreg | recent |
| opencv-python | recent |

Dependencies are installed automatically on first run via `sirilpy.ensure_installed`.

---

## How to run

1. In Siril, **load a sequence of individual FITS files** (*Conversion* without the FITSEQ option, or *Open sequence*).
2. **Script → Execute Script** → `SirilJ_SolarAlign.py`.
3. The window opens and detects the current sequence automatically.

> ⚠ **Single-file sequences are not supported.** A FITSEQ (one `.fits` holding all frames) or SER sequence cannot be aligned directly — the script works on **individual FITS**. Reconvert to individual FITS (Conversion **without** *FITS sequence*), then click **⟳ Rafraîchir** (Refresh).

---

## Interface overview

```
┌──────────────────────┬──────────────────────────────────────┐
│  Siril sequence       │  Preview — reference image            │
│  Reference image      │  (scroll to zoom, drag to pan)        │
│  Algorithm            │                                       │
│  Output & integration ├──────────────────────────────────────┤
│  Prepare / Start      │  Progress bar                         │
│  Stop                 │  Execution log                        │
└──────────────────────┴──────────────────────────────────────┘
```

---

## Two-step workflow

Alignment is always done in two steps: **prepare the reference**, then **start**.

### 1. Prepare the reference

**« Préparer la référence »** (Prepare reference) loads the reference image and shows it in the right-hand preview, so you can visually confirm it's the right frame before the full run.

### 2. Start the alignment

**« ▶ Démarrer l'alignement »** (Start alignment) only enables **after** preparation. It aligns every frame of the sequence onto the reference, then runs the checked Siril steps (convert, stack, load).

**« ⏹ Arrêter »** (Stop) cleanly aborts. On stop, **no** Siril step (convert / stack / load) runs — only the frames already written remain on disk.

---

## Current Siril sequence

| Display | Meaning |
|---|---|
| `✓  <name>` (green) | Sequence detected; frame count, mono/color and path shown |
| `⚠ <name> — séquence mono-fichier` | FITSEQ/SER: export to individual FITS |
| `Aucune séquence chargée` (No sequence loaded) | Load a sequence in Siril, then ⟳ Refresh |

**⟳ Rafraîchir** (Refresh) re-runs detection after any change on the Siril side.

---

## Reference image

| Mode (FR label) | Effect |
|---|---|
| **Meilleure netteté** (Best sharpness) | Scans all frames, keeps the sharpest (gradient variance) |
| **Première** (First) | First frame of the sequence |
| **Dernière** (Last) | Last frame |
| **Manuel** (Manual) | Index typed in the *Index* field |

The preview shows an **autostretch** of the reference (data is not modified).

---

## Algorithms

### StackReg

Python port of the ImageJ StackReg plugin (Thévenaz, EPFL). Robust, parameter-free.

| Model (FR label) | Degrees of freedom |
|---|---|
| **Translation** | X/Y shift |
| **Corps rigide** (Rigid body) | translation + rotation *(recommended for the Sun)* |
| **Rotation/Échelle** (Scaled rotation) | translation + rotation + isotropic scale |
| **Affine** | + shear |
| **Bilinéaire** (Bilinear) | non-linear warp |

### ECC (OpenCV)

Enhanced Correlation Coefficient maximization (Evangelidis & Psarakis) via `cv2.findTransformECC`.

| Option | Role |
|---|---|
| **Modèle** (Model) | Translation, Euclidean, Affine, Homography |
| **Itérations** (Iterations) | max iterations (default 50) |
| **Epsilon** | convergence threshold (default 1e-4) |

> **Tip:** for full-frame solar disks, **StackReg / Corps rigide (Rigid body)** gives excellent results with no tuning. ECC Euclidean is a good alternative; use Affine/Homography only when there's geometric distortion.

---

## Output & Siril integration

Aligned frames are written to an **isolated sub-folder** of the working directory, named after the **prefix** (default `align_` → sub-folder `align/`), numbered sequentially (`align_00001.fit`, …).

> Why a sub-folder? Siril's `convert` command converts **all** FITS in a folder. Isolating the aligned frames prevents the original (unaligned) images from being mixed into the final sequence.

| Option (FR label) | Effect |
|---|---|
| **Préfixe** (Prefix) | Base name of the sub-folder, sequence and result |
| **Convertir en séquence Siril** (Convert to Siril sequence) | `convert <base> -fitseq` in the sub-folder |
| **Empiler après alignement** (Stack after alignment) | `stack <base> <method> -out=<base>_stacked` |
| **Méthode** (Method) | `sum`, `med`, `rej 3 3`, `max`, `min` |
| **Charger le résultat dans Siril** (Load result in Siril) | `load` of the stack (or the 1st aligned frame) |

At the end, the script automatically restores Siril's original working directory.

**Photometric preservation:** the [0,1] normalization is used only for alignment and preview. Saved frames **keep their original scale** (FITS float32), so the stack is photometrically consistent.

---

## Stacking methods

| Method | Typical use |
|---|---|
| **sum** | Sum — maximizes signal (solar default) |
| **med** | Median — removes transients (planes, cosmic rays) |
| **rej 3 3** | Sigma rejection (3σ low / 3σ high) — signal/rejection trade-off |
| **max** | Maximum — useful for prominences |
| **min** | Minimum — attenuates isolated noise |

---

## Execution log

Each step is logged in the right-hand panel and, for key steps, in **Siril's console**.

```
Séquence détectée : sun (240 images)
✓ Référence prête : sun_118.fit
━━ Alignement STACKREG → /…/sun/align
✓ 240/240  —  sun_240.fit
✓ Alignement terminé : 240/240 images.
→ Conversion en séquence Siril : align
✓ Séquence «align» créée.
→ Empilement (sum) → align_stacked
✓ Empilement terminé : align_stacked
→ Chargement dans Siril : align_stacked
✓ Affichage dans Siril mis à jour.
```

---

## Notes & tips

- **Memory:** the "best sharpness" scan reads each frame once; on very long sequences this can take a moment (progress shown).
- **Re-running:** a new run cleanly overwrites the previous outputs of the same prefix (frames, fitseq, `.seq`, stack) without touching other files.
- **Closing:** closing the window during processing aborts it and waits for the thread to finish before quitting (no crash).
- **Color:** color images (3 channels) are aligned per channel with the same transform.
- The **original sequence data is never modified**: all outputs go to the sub-folder.

---

## Correspondence with ImageJ

| ImageJ plugin | Equivalent here |
|---|---|
| **StackReg** (Thévenaz) | StackReg algorithm, all models |
| **TurboReg** (Thévenaz) | Underlying (pyramidal) engine of StackReg |
| **Image Stabilizer** / **Linear Stack Alignment with SIFT** | ECC algorithm (correlation-based) |
| **Image → Stacks → Z Project…** | Stacking step (`sum`, `med`, `max`, `min`) |
