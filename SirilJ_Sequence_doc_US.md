# SirilJ Séquence — User Guide

**Version 1.0**  
Two tools on Siril's current sequence, with no native equivalent: **Montage** (ImageJ *Make Montage*) and **Blink / Animation** (ImageJ *Animation* + image difference).

> **Note:** this script's interface is in **French**. This guide explains it in English; the actual French labels are shown in **bold** with an English gloss.

---

## Requirements

| Component | Version |
|---|---|
| Siril | 1.3 or later |
| Python (via sirilpy) | 3.10 or later |
| numpy, astropy | recent |
| PyQt6 | recent |

Dependencies are installed automatically on first run.

---

## How to run

1. In Siril, load a **sequence of individual FITS files** (Conversion without FITSEQ, or *Open sequence*).
2. **Script → Execute Script** → `SirilJ_Sequence.py`.
3. The current sequence is detected automatically. **⟳ Rafraîchir** (Refresh) after any change on the Siril side.

> ⚠ **Single-file sequences are not supported.** FITSEQ (a single `.fits`) or SER: reconvert to individual FITS, then ⟳ Refresh.
>
> Color frames are processed as **luminance** (channel average).

---

## Tab ▦ Montage

Assembles the frames into a contact sheet (grid) — planetary rotation, time-lapse, sequence overview.

| Setting (FR label) | Role |
|---|---|
| **Début / Fin / Pas** (Start / End / Step) | Frame range and sampling |
| **Colonnes** (Columns) | Number of grid columns |
| **Échelle** (Scale) | Downscale of each thumbnail (1/1 → 1/16) |
| **Bordure (px)** (Border) | Spacing between thumbnails |
| **Bordure** (Border color) | Border color (black / white / gray) |
| **Étirement par frame** (Per-frame stretch) | Independent autostretch per thumbnail (otherwise global stretch) |

**Construire le montage** (Build montage) assembles and displays the sheet (scroll to zoom, drag to pan).  
**Enregistrer + charger dans Siril** (Save + load in Siril) saves the sheet as FITS and loads it in Siril.

> Memory: on long sequences, increase the **Step** or reduce the **Scale** to limit the sheet's size.

---

## Tab ▶ Blink / Animation

Cycles through frames to spot moving objects (asteroids, novae, comets) or variations.

### Transport

| Control (FR label) | Effect |
|---|---|
| **◀ / ▶** | Previous / next frame |
| **▶ Lecture / ⏸ Pause** (Play / Pause) | Looping animation |
| **Curseur d'image** (Frame slider) | Jump directly to a frame |
| **Vitesse** (Speed) | 1 to 30 frames per second |

### Modes

| Mode (FR label) | Effect |
|---|---|
| **Normal** | Shows each frame (autostretch) |
| **Différence avec réf.** (Difference vs reference) | Frame − reference frame: a mover appears as a bright/dark doublet |
| **Différence avec précédente** (Difference vs previous) | Frame − previous frame: highlights any shift between consecutive frames |

**Définir la frame courante comme réf.** (Set current frame as reference) fixes the reference image for the difference mode.  
In difference mode the image is centered on gray (50%): **black/white** marks negative/positive deviations.

> **Asteroid-hunting workflow:** first align the sequence on the stars (see *SirilJ SolarAlign* or Siril's registration), then switch to **Différence avec réf.** — the fixed stars vanish and only the moving object "blinks".

---

## Notes & tips

- Frames are cached (LRU) for smoother playback; the first pass may be slower.
- The saved **montage** is a presentation image (stretched luminance), not photometric data.
- The original sequence data is **never modified**.

---

## Correspondence with ImageJ

| ImageJ function | Equivalent here |
|---|---|
| **Image → Stacks → Make Montage** | Montage tab |
| **Image → Stacks → Animation (Start/Stop)** | Blink tab — Play/Pause + speed |
| **Image → Stacks → Tools → Blink** | Blink tab — difference modes |
| **Process → Image Calculator (Difference)** | *Difference vs reference / previous* modes |
