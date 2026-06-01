# SirilJ Analyse — User Guide

**Version 1.0**  
Two analysis tools on Siril's current image, with no native equivalent: **Particle analysis** (ImageJ *Analyze Particles*) and **3D Surface** (ImageJ *Surface Plot*).

> **Note:** this script's interface is in **French**. This guide explains it in English; the actual French labels are shown in **bold** with an English gloss.

---

## Requirements

| Component | Version |
|---|---|
| Siril | 1.3 or later |
| Python (via sirilpy) | 3.10 or later |
| numpy, astropy, scipy | recent |
| scikit-image | recent |
| matplotlib | recent |
| PyQt6 | recent |

Dependencies are installed automatically on first run.

---

## How to run

1. Open an image in Siril.
2. **Script → Execute Script** → `SirilJ_Analyse.py`.
3. The current image loads automatically (**⟳ Recharger l'image** = Reload image, to refresh it).

> The displayed image is an **autostretch preview**. Intensity measurements use the **raw data**; thresholding is performed on the stretched image (consistent with what you see).

---

## Tab ⬤ Particules (Particles)

Detects and measures objects in an image: sunspots, stars, craters, galaxies…

### Settings

| Setting (FR label) | Role |
|---|---|
| **Seuil automatique (Otsu)** (Auto threshold) | Computes an optimal threshold automatically |
| **Seuil** (Threshold slider) | Manual threshold [0–1] on the stretched image (if Otsu unchecked) |
| **Polarité** (Polarity) | *Objets clairs / fond sombre* (light objects / dark background — stars) or *Objets sombres / fond clair* (dark objects / light background — sunspots) |
| **Aire min / max (px²)** (Min/max area) | Size filter (max = 0 → no limit) |
| **Circularité min** (Min circularity) | 1.0 = perfect circle; 0 = no filter |
| **Exclure objets aux bords** (Exclude border objects) | Ignores objects clipped by the frame |

### Results

Table sorted by decreasing area: **#, Aire px² (area), Aire arcsec²** (if plate-solved), **X, Y** (FITS coordinates), **Circ. (circularity), I.moy (mean intensity)**. Objects are outlined on the image with their number.

The left panel shows the **object count**, the **threshold used** and the **total area**.

### CSV export

**Exporter CSV…** (Export CSV) saves all measurements (area, arcsec² area if WCS, X/Y, equivalent diameter, circularity, eccentricity, mean and max intensity).

### Usage examples

- **Sunspot counting:** polarity *dark objects / light background*, min circularity ~0.3.
- **Star counting:** polarity *light objects / dark background*, min area ~3 px².
- **Galaxy/nebula measurement:** a single object, read its area in arcsec².

---

## Tab ⛰ Surface 3D

Renders image intensity as a relief surface — useful for a galaxy core, a stellar PSF, a nebula's brightness profile.

| Setting (FR label) | Role |
|---|---|
| **Résolution** (Resolution) | Max side of the downsampled grid (20–400) |
| **Palette** (Colormap) | viridis, inferno, magma, plasma, gray, hot, jet, cividis |
| **Échelle logarithmique** (Log scale) | Compresses dynamic range (reveals faint extensions) |
| **Appliquer l'autostretch** (Apply autostretch) | Plots stretched intensity rather than linear |

The matplotlib toolbar lets you **rotate, zoom and save** the plot as an image.

> For large images, lower the resolution (the grid is block-mean reduced before rendering).

---

## Notes & tips

- **X/Y** coordinates follow the FITS convention (X from left, Y from bottom), like the *SirilJ Mesures* probe.
- The **object count** depends heavily on the threshold: tune Otsu ↔ manual and the circularity.
- Siril's original data is **never modified**.

---

## Correspondence with ImageJ

| ImageJ function | Equivalent here |
|---|---|
| **Analyze → Analyze Particles** | Particles tab (area, circularity, centroid, intensity, count, CSV) |
| **Analyze → Set Measurements** | Table / CSV columns |
| **Image → Adjust → Threshold** | Otsu / manual threshold + polarity |
| **Analyze → Surface Plot** | 3D Surface tab |
