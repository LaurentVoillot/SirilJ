# SirilJ Measure — User Guide

**Version 1.4**  
Interactive measurement tools for Siril: line distance, angle, area, freehand shape, intensity profile, region statistics — with astrometric conversion, physical conversion, and **object-diameter calibration** (Solar System).

---

## Requirements

| Component | Version |
|---|---|
| Siril | 1.3 or later |
| Python (via sirilpy) | 3.10 or later |
| PyQt6 | recent |
| numpy | recent |
| astropy | recent |

Dependencies are installed automatically on first run via `sirilpy.ensure_installed`.

Two versions are provided, identical code, language only differs:
- `SirilJ_Mesures_US.py` — English UI, numbers formatted **18,407.50** (comma thousands, period decimal)
- `SirilJ_Mesures_FR.py` — French UI, numbers formatted **18 407,50**

---

## How to run

1. Open an image in Siril.
2. **Script → Execute Script** → `SirilJ_Mesures_US.py`.
3. The window opens and loads the current image automatically.

> For **angular** measurements the image must be **plate-solved** (Siril's Astrometry tool). Without a solution the script works in pixel mode — and **object calibration** (below) still provides physical sizes without astrometry.

---

## Interface overview

```
┌──────────────────┬────────────────────────────────────────────┐
│  Tools           │  Image canvas (zoom / pan)                  │
│  Physical dist   │                                             │
│  Object calib    │                                             │
│  WCS status      ├────────────────────────────────────────────┤
│  Pixel probe     │  Scrollable results log (3 lines)           │
│  On Top/Help/    │                                             │
│  Close           │                                             │
└──────────────────┴────────────────────────────────────────────┘
```

All measurement overlays are drawn in **blue**; clicked points are marked with a **red dot**.

### Zoom & pan
| Action | Effect |
|---|---|
| Scroll wheel | Zoom in / out |
| Click & drag | Pan (when no tool is active) |
| **−** / **+** | Zoom ×1.2 |
| **Fit** | Fit image to window |
| **1:1** | Native pixel size |

---

## Tools

### ╱ Line — distance
Click 2 points. Results: pixels (always), angular (if plate-solved), physical (if a distance is set **or** an object is calibrated).
`Line:     1,247.3 px  |  4.23'  |  20,000 km`

### ∠ Angle — angle
Click 3 points: **A** (first arm), **B** (vertex), **C** (second arm). 2-D angle + true on-sky angle (`sky`, if plate-solved).
`Angle:    47° 12' 08.3"  |  sky 47° 11' 52.1"`

### ⬡ Area — polygon area
Click vertices; **double-click** or **right-click** to close. Pixel area, angular (if plate-solved), physical (if distance or calibration).
`Area:     84,320 px²  |  1.247 arcmin²`

### 〰 Freehand — free-form shape
**Click and drag** freely to trace any shape; **release** to close. Same results as the Area tool.
`Freehand: 44,020 px²  |  9,360,000 km²`

### 〜 Profile — intensity plot
Click 2 points. Opens a window plotting R/G/B intensity along the segment (bilinear interpolation).

### ▣ ROI Stats — region statistics
Click and drag a rectangle. Mean, median, min, max, std-dev per channel, on **raw FITS data** [0,1].

---

## Pixel probe

Always active. Hover over the image to read, in real time, the coordinates (FITS convention: X from left, Y from bottom) and R/G/B values of the pixel under the cursor.

---

## Physical distance conversion (astrometry)

Enter the target distance in the **Physical distance** panel to convert angular measurements to physical sizes/areas.

| Input unit | Use for |
|---|---|
| km / AU | Solar System |
| ly / pc | Stars, nebulae |
| kpc / Mpc | Galactic objects, galaxies |

Output unit chosen automatically (km → AU → ly → kly → Mly, and matching areas).

---

## ◎ Object-diameter calibration (Solar System)

Gives physical sizes **without astrometry** — ideal for the Sun, Moon and planets.

**Principle:** the object's true diameter is known; tracing that diameter on the image yields the **km/pixel** scale.

**How to use:**
1. Pick the object: **Sun, Moon, Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune**, or **Custom…** (enter a diameter in km).
2. Click **◎ Trace diameter**, then trace the object's diameter (2 clicks).
3. The **km/px** scale is shown and remembered:
   `Calib:    Ø 1,391,400 km  →  1,234.5 km/px`
4. From then on, **every** measurement reports a physical size:
   - a **line** → length in km
   - an **area / freehand** → surface in km²

**Example — sunspots:** trace the Sun's diameter, then trace a spot:
`Freehand: 44,020 px²  |  9,360,000 km²`

Equatorial diameters used (km): Sun 1,391,400 · Moon 3,475 · Mercury 4,879 · Venus 12,104 · Earth 12,742 · Mars 6,779 · Jupiter 139,820 · Saturn 116,460 · Uranus 50,724 · Neptune 49,244.

> The calibration scale **persists** across "Clear all": calibrate once, measure as much as you like. It is independent of astrometry and adds to the other conversions.

---

## Results log

Every measurement is appended to the scrollable log and sent to **Siril's console**. **Clear all** removes overlays and clears the log (but keeps the calibration).

---

## WCS status badge

| Badge | Meaning |
|---|---|
| `WCS ✓  0.452"/px` | Plate solution found; pixel scale shown |
| `No astrometry — pixel only` | Pixel measurements (object calibration still available) |

---

## Help button

The **?** button opens this documentation. It looks for `SirilJ_Mesures_doc_US.md` in the script directory, then in `~/Claude/SirilJ/`; falls back to embedded help.

---

## Notes & tips

- **All overlays are blue** (`#0000FF`), readable over bright backgrounds like the solar disk; clicked points are red. The Line and Calibration strokes use a constant on-screen width (readable at any zoom).
- **Number format**: US `18,407.50` (comma + period); FR `18 407,50`.
- Measurements **accumulate**; only **Clear all** removes them.
- The displayed image is an **autostretch preview**; original data is not modified.
- Profile and ROI Stats operate on **raw FITS data** [0,1].
- All results are also logged to **Siril's Script Console**.
