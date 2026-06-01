##############################################
# SirilJ — Measure  (US English version)
# Interactive measurement tools with WCS support
# Version 1.4.0
##############################################
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Crédits
# -------
#   • Moteur d'autostretch : VeraLux Shared GUI Framework (Riccardo Paterniti)
#   • WCS / conversions angulaires : astropy
#   • Interface : PyQt6 / conventions VeraLux

"""
SirilJ Mesures — outils de mesure interactifs sur l'image courante de Siril.

  • Ligne   — 2 clics → distance en pixels, angulaire, physique
  • Angle   — 3 clics (A, sommet B, C) → angle en degrés/DMS + ciel
  • Aire    — sommets + double-clic/clic droit → aire pixel et angulaire
  • Patate  — glisser librement → forme libre, relâcher pour clore
  • Profil  — 2 clics → graphe d'intensité R/G/B
  • Stats ROI — cliquer-glisser → statistiques par canal

La sonde pixel est toujours active : survolez l'image pour lire les valeurs.

Compatibilité
-------------
• Siril 1.3+
• Python 3.10+ (via sirilpy)
• Dépendances : sirilpy, PyQt6, numpy, astropy
"""

LANG = "US"   # Change to "FR" for French version

import sys
import os
import math
import tempfile

try:
    import sirilpy as s
    from sirilpy import LogColor
except ImportError:
    print("Erreur : module sirilpy introuvable.")
    sys.exit(1)

s.ensure_installed("numpy", "astropy", "PyQt6")

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
from astropy.coordinates import SkyCoord

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QGridLayout,
    QWidget, QLabel, QPushButton, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QGroupBox, QPlainTextEdit, QDialog, QTextEdit,
    QDoubleSpinBox, QComboBox, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPointF
from PyQt6.QtGui import (
    QImage, QPixmap, QPen, QBrush, QColor, QPolygonF, QFont, QPainter
)

VERSION = "1.4.0"

# ---------------------
#  TOOL IDS
# ---------------------

TOOL_NONE     = 0
TOOL_LINE     = 1
TOOL_ANGLE    = 2
TOOL_AREA     = 3
TOOL_PROFILE  = 4
TOOL_ROI      = 5
TOOL_FREEHAND = 6
TOOL_CALIB    = 7

# ---------------------
#  VISUAL CONSTANTS
# ---------------------

COL_LINE      = QColor("#0000FF")   # bleu — tous les tracés de mesure
COL_ANGLE     = QColor("#0000FF")
COL_AREA      = QColor("#0000FF")
COL_PROFILE   = QColor("#0000FF")
COL_ROI       = QColor("#0000FF")
COL_FREEHAND  = QColor("#0000FF")
COL_CALIB     = QColor("#0000FF")
COL_VERTEX    = QColor("#ff4444")   # rouge — points cliqués (repères)
COL_LABEL     = QColor("#ffffff")
POINT_R       = 4
LINE_W        = 1.5
LINE_MEASURE_W = 3.0                 # largeur (px écran, pen cosmétique) ligne/calib

# ---------------------
#  DARK STYLESHEET
# ---------------------

DARK_STYLESHEET = """
QWidget { background-color: #2b2b2b; color: #e0e0e0; font-size: 10pt; }
QToolTip { background-color: #333333; color: #ffffff; border: 1px solid #88aaff; }
QGroupBox { border: 1px solid #444444; margin-top: 5px; font-weight: bold;
            border-radius: 4px; padding-top: 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 3px; color: #88aaff; }
QLabel { color: #cccccc; }
QDoubleSpinBox, QComboBox {
    background-color: #3c3c3c; color: #ffffff;
    border: 1px solid #555555; padding: 3px; border-radius: 3px;
}
QPushButton {
    background-color: #444444; color: #dddddd;
    border: 1px solid #666666; border-radius: 4px;
    padding: 6px 10px; font-weight: bold;
}
QPushButton:hover   { background-color: #555555; border-color: #777777; }
QPushButton:checked { background-color: #285299; border-color: #1e3f7a; color: #ffffff; }
QPushButton:disabled { background-color: #333333; color: #666666; border-color: #444444; }
QPushButton#CloseButton { background-color: #5a2a2a; border: 1px solid #804040; }
QPushButton#CloseButton:hover { background-color: #7a3a3a; }
QPushButton#ZBtn { min-width: 28px; font-weight: bold; }
QPushButton#HelpButton {
    background-color: transparent; border: 1px solid #555555; color: #888888;
    border-radius: 11px; min-width: 22px; max-width: 22px;
    min-height: 22px; max-height: 22px; font-size: 11pt;
    padding: 0; font-weight: bold;
}
QPushButton#HelpButton:hover { color: #88aaff; border-color: #88aaff; }
QCheckBox { spacing: 5px; color: #cccccc; }
QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #666666;
                       background: #3c3c3c; border-radius: 4px; }
QCheckBox::indicator:checked { background-color: #285299; border: 1px solid #88aaff; }
QFrame#Sep { background-color: #444444; }
QPlainTextEdit {
    background-color: #1a1a1a; color: #ffb000;
    border: none; font-size: 9pt; font-family: "Monospace";
    padding: 4px;
}
QTextEdit {
    background-color: #1a1a1a; color: #e0e0e0;
    border: none; font-size: 10pt; padding: 6px;
}
"""

# ---------------------
#  TRANSLATIONS
# ---------------------

_T = {
    "FR": {
        "win_title":    "SirilJ — Mesures",
        "panel_title":  "SirilJ Mesures",
        "grp_tools":    "Outils",
        "grp_phys":     "Distance physique",
        "btn_line":     "╱  Ligne",
        "btn_angle":    "∠  Angle",
        "btn_area":     "⬡  Aire",
        "btn_freehand": "〰  Patate",
        "btn_profile":  "〜  Profil",
        "btn_roi":      "▣  Stats ROI",
        "btn_clear":    "✕  Tout effacer",
        "btn_close":    "Fermer",
        "chk_top":      "Au-dessus",
        "tip_line":     "2 clics — mesure la distance",
        "tip_angle":    "Clic A, sommet B, C — mesure l'angle",
        "tip_area":     "Cliquer les sommets, double-clic ou clic droit pour clore",
        "tip_freehand": "Glisser pour tracer une forme libre — relâcher pour clore",
        "tip_profile":  "2 clics — trace le profil d'intensité R/G/B",
        "tip_roi":      "Cliquer-glisser — statistiques par canal",
        "tip_help":     "Aide",
        "lbl_dist":     "Distance :",
        "lbl_unit":     "Unité :",
        "probe_hdr":    "Sonde pixel",
        "probe_none":   "—",
        "wcs_loading":  "WCS : chargement…",
        "wcs_ok":       "WCS ✓  {}\"/px",
        "wcs_none":     "Pas d'astrométrie — pixels seulement",
        "hint_load":    "Chargement…",
        "hint_wcs":     "Ligne: ×2  |  Angle: A→B→C  |  Aire/Patate: glisser  |  Profil: ×2  |  ROI: glisser  |  Molette: zoom",
        "hint_nowcs":   "Pas de solution astrométrique — mesures en pixels uniquement",
        "placeholder":  "Les résultats apparaîtront ici…",
        "pfx_line":     "Ligne  :",
        "pfx_angle":    "Angle  :",
        "pfx_area":     "Aire   :",
        "pfx_freehand": "Patate :",
        "pfx_profile":  "Profil :",
        "pfx_roi":      "ROI    :",
        "samples":      "échantillons",
        "prof_win":     "Profil d'intensité  —  {n} px",
        "prof_nodata":  "Profil : données image non disponibles",
        "roi_small":    "ROI : sélection trop petite",
        "roi_nodata":   "ROI : données image non disponibles",
        "help_title":   "SirilJ Mesures — Aide",
        "help_doc":     "SirilJ_Mesures_doc_FR.md",
        "err_hint":     "Erreur : {msg}",
        "err_pfx":      "[Erreur]",
        "siril_err":    "SirilJ Mesures erreur : {msg}",
        "siril_pfx":    "SirilJ Mesures — ",
        "log_hdr_2":    "# Ligne, Angle, Aire, Patate, Profil & ROI avec WCS",
        "grp_calib":    "Calibration objet",
        "lbl_object":   "Objet :",
        "lbl_custom":   "Diam. (km) :",
        "btn_calib":    "◎  Tracer le diamètre",
        "tip_calib":    "Choisir un objet puis tracer son diamètre (2 clics) pour fixer l'échelle",
        "calib_none":   "Échelle : —",
        "calib_set":    "Échelle : {scale} km/px\n{obj} (Ø {diam})",
        "pfx_calib":    "Calib  :",
        "objects":      ["Soleil", "Lune", "Mercure", "Vénus", "Terre", "Mars",
                         "Jupiter", "Saturne", "Uranus", "Neptune"],
        "obj_custom":   "Personnalisé…",
    },
    "US": {
        "win_title":    "SirilJ — Measure",
        "panel_title":  "SirilJ Measure",
        "grp_tools":    "Tools",
        "grp_phys":     "Physical distance",
        "btn_line":     "╱  Line",
        "btn_angle":    "∠  Angle",
        "btn_area":     "⬡  Area",
        "btn_freehand": "〰  Freehand",
        "btn_profile":  "〜  Profile",
        "btn_roi":      "▣  ROI Stats",
        "btn_clear":    "✕  Clear all",
        "btn_close":    "Close",
        "chk_top":      "On Top",
        "tip_line":     "Click 2 points — measures distance",
        "tip_angle":    "Click A, vertex B, C — measures angle",
        "tip_area":     "Click vertices, dbl-click or right-click to close",
        "tip_freehand": "Drag to draw a freehand shape — release to close",
        "tip_profile":  "Click 2 points — plots R/G/B intensity profile",
        "tip_roi":      "Click and drag — shows per-channel statistics",
        "tip_help":     "Open help",
        "lbl_dist":     "Distance:",
        "lbl_unit":     "Unit:",
        "probe_hdr":    "Pixel probe",
        "probe_none":   "—",
        "wcs_loading":  "WCS: loading…",
        "wcs_ok":       "WCS ✓  {}\"/px",
        "wcs_none":     "No astrometry — pixel only",
        "hint_load":    "Loading…",
        "hint_wcs":     "Line: ×2  |  Angle: A→B→C  |  Area/Freehand: drag  |  Profile: ×2  |  ROI: drag  |  Scroll: zoom",
        "hint_nowcs":   "No plate solution — pixel measurements only",
        "placeholder":  "Results will appear here…",
        "pfx_line":     "Line:     ",
        "pfx_angle":    "Angle:    ",
        "pfx_area":     "Area:     ",
        "pfx_freehand": "Freehand: ",
        "pfx_profile":  "Profile:  ",
        "pfx_roi":      "ROI:      ",
        "samples":      "samples",
        "prof_win":     "Plot Profile  —  {n} px",
        "prof_nodata":  "Profile: image data not available",
        "roi_small":    "ROI: selection too small",
        "roi_nodata":   "ROI: image data not available",
        "help_title":   "SirilJ Measure — Help",
        "help_doc":     "SirilJ_Mesures_doc_US.md",
        "err_hint":     "Error: {msg}",
        "err_pfx":      "[Error]",
        "siril_err":    "SirilJ Measure error: {msg}",
        "siril_pfx":    "SirilJ Measure — ",
        "log_hdr_2":    "# Line, Angle, Area, Freehand, Profile & ROI with WCS",
        "grp_calib":    "Object calibration",
        "lbl_object":   "Object:",
        "lbl_custom":   "Diam. (km):",
        "btn_calib":    "◎  Trace diameter",
        "tip_calib":    "Pick an object then trace its diameter (2 clicks) to set the scale",
        "calib_none":   "Scale: —",
        "calib_set":    "Scale: {scale} km/px\n{obj} (Ø {diam})",
        "pfx_calib":    "Calib:    ",
        "objects":      ["Sun", "Moon", "Mercury", "Venus", "Earth", "Mars",
                         "Jupiter", "Saturn", "Uranus", "Neptune"],
        "obj_custom":   "Custom…",
    },
}

T = _T[LANG]

# ---------------------
#  EMBEDDED HELP (fallback when .md file not found)
# ---------------------

_HELP_MD = {
    "FR": """\
# SirilJ Mesures — Aide

**Version 1.3**

---

## Outils

### ╱ Ligne
2 clics. Distance en pixels, angulaire (si astrométrie) et physique.

### ∠ Angle
3 clics : A (premier bras), B (sommet), C (second bras). Angle 2-D + angle vrai sur le ciel.

### ⬡ Aire
Cliquer les sommets ; **double-clic** ou **clic droit** pour clore.

### 〰 Patate
**Cliquer-glisser** librement pour tracer une forme quelconque ; **relâcher** pour clore. Mesure la même aire que l'outil Aire.

### 〜 Profil
2 clics. Graphe d'intensité R/G/B le long du segment.

### ▣ Stats ROI
Cliquer-glisser un rectangle. Statistiques par canal (moy/med/min/max/σ).

---

## Sonde pixel
Toujours active. Survoler l'image affiche coordonnées et valeurs R/G/B.

---

## Distance physique

| Unité | Usage |
|-------|-------|
| km  | Lune, Soleil, planètes |
| AU  | Système Solaire |
| ly  | Étoiles proches |
| pc  | Nébuleuses, amas |
| kpc | Objets galactiques |
| Mpc | Galaxies |

---

## Zoom & déplacement
Molette pour zoomer, cliquer-glisser (aucun outil actif) pour se déplacer.

---

## Notes
- Les mesures s'accumulent ; **Tout effacer** supprime tout.
- Profil et Stats ROI opèrent sur les **données FITS brutes** [0,1].
""",
    "US": """\
# SirilJ Measure — Help

**Version 1.3**

---

## Tools

### ╱ Line
Click two points. Pixel distance, angular distance (if plate-solved), physical size.

### ∠ Angle
Click A (first arm), B (vertex), C (second arm). 2-D angle + true on-sky angle.

### ⬡ Area
Click vertices; **double-click** or **right-click** to close.

### 〰 Freehand
**Click-drag** freely to trace any shape; **release** to close. Computes area like the Area tool.

### 〜 Profile
Click two points. Per-channel R/G/B intensity plot along the segment.

### ▣ ROI Stats
Click and drag a rectangle. Per-channel statistics (mean/med/min/max/σ).

---

## Pixel probe
Always active. Hover over the image to read coordinates and R/G/B values.

---

## Physical distance

| Unit | Use for |
|------|---------|
| km  | Moon, Sun, planets |
| AU  | Solar System |
| ly  | Nearby stars |
| pc  | Nebulae, clusters |
| kpc | Galactic objects |
| Mpc | Galaxies |

---

## Zoom & pan
Scroll to zoom, click-drag (no tool active) to pan.

---

## Notes
- Measurements accumulate; **Clear all** removes all overlays and the log.
- Profile and ROI Stats use **raw FITS data** [0,1], not the stretched preview.
""",
}

HELP_MD = _HELP_MD[LANG]

# ---------------------
#  AUTOSTRETCH  (Siril MTF — ported from VeraLux)
# ---------------------

def _mtf(x, m, lo, hi):
    dist = hi - lo
    if dist < 1e-9:
        return np.where(x > lo, 1.0, 0.0).astype(np.float32)
    xp = np.clip((x - lo) / dist, 0.0, 1.0)
    with np.errstate(divide='ignore', invalid='ignore'):
        y = ((m - 1.0) * xp) / ((2.0 * m - 1.0) * xp - m)
    return np.nan_to_num(y, nan=0.0, posinf=1.0, neginf=0.0).astype(np.float32)


def apply_autostretch(img_rgb):
    MAD_NORM = 1.4826; SC = -2.8; TBG = 0.25
    sum_c0 = sum_m = 0.0
    for ch in img_rgb:
        stride = max(1, ch.size // 500_000)
        samp = ch.flatten()[::stride]
        med = float(np.median(samp))
        mad = float(np.median(np.abs(samp - med))) * MAD_NORM or 0.001
        sum_c0 += med + SC * mad
        sum_m  += med
    c0 = max(0.0, sum_c0 / 3.0)
    mt = float(_mtf(np.float32(sum_m / 3.0 - c0), TBG, 0.0, 1.0))
    return np.clip(np.stack([_mtf(ch, mt, c0, 1.0) for ch in img_rgb]), 0.0, 1.0)

# ---------------------
#  UNIT HELPERS
# ---------------------

def nfmt(x: float, dec: int = 0) -> str:
    """Format un nombre selon la langue active.
    FR : espace insécable pour les milliers, virgule décimale (18 407,50).
    US : virgule pour les milliers, point décimal (18,407.50)."""
    s = f"{x:,.{dec}f}"
    if LANG == "FR":
        s = s.replace(",", " ").replace(".", ",")
    return s

def _dec(s: str) -> str:
    """Localise uniquement le séparateur décimal (FR : '.' → ',')."""
    return s.replace(".", ",") if LANG == "FR" else s


def fmt_angle(deg: float) -> str:
    asec = deg * 3600.0
    if asec < 60.0:  return f"{nfmt(asec, 2)}\""
    amin = asec / 60.0
    if amin < 60.0:  return f"{nfmt(amin, 3)}'"
    return f"{nfmt(deg, 4)}°"


def fmt_dms(deg: float) -> str:
    d = int(deg)
    rem = (deg - d) * 60.0
    m = int(rem)
    sec = (rem - m) * 60.0
    return f"{d}° {m:02d}' {_dec(f'{sec:04.1f}')}\""


_AU_KM = 149_597_870.7

def fmt_physical(arcsec: float, dist_pc: float) -> str:
    au = dist_pc * arcsec
    km = au * _AU_KM
    if km < 2_000_000:  return f"{nfmt(km, 0)} km"
    if au < 100:
        return f"{nfmt(au, 4)} AU" if au < 0.1 else f"{nfmt(au, 2)} AU"
    ly = au / 63_241.1
    if ly < 1_000:     return f"{nfmt(ly, 2)} ly"
    kly = ly / 1_000
    if kly < 1_000:    return f"{nfmt(kly, 2)} kly"
    return f"{nfmt(kly / 1_000, 2)} Mly"


def fmt_area(arcsec2: float) -> str:
    if arcsec2 < 3_600:  return f"{nfmt(arcsec2, 1)} arcsec²"
    amin2 = arcsec2 / 3_600
    if amin2 < 3_600:    return f"{nfmt(amin2, 3)} arcmin²"
    return f"{nfmt(arcsec2 / 3_600 / 3_600, 4)} deg²"


def fmt_physical_area(arcsec2: float, dist_pc: float) -> str:
    """Convertit une aire angulaire (arcsec²) en aire physique via l'approximation des petits angles."""
    if arcsec2 <= 0 or dist_pc <= 0:
        return ""
    au2     = dist_pc ** 2 * arcsec2
    km2     = au2 * _AU_KM ** 2
    side_km = math.sqrt(km2)
    if side_km < 2_000_000:
        return f"{nfmt(km2, 0)} km²"
    side_au = side_km / _AU_KM
    if side_au < 100:
        return f"{_dec(f'{side_au ** 2:.3g}')} AU²"
    side_ly = side_au / 63_241.1
    if side_ly < 1_000:
        return f"{_dec(f'{side_ly ** 2:.3g}')} ly²"
    side_kly = side_ly / 1_000
    if side_kly < 1_000:
        return f"{_dec(f'{side_kly ** 2:.3g}')} kly²"
    return f"{_dec(f'{(side_kly / 1_000) ** 2:.3g}')} Mly²"


# Objets du Système Solaire — diamètre équatorial moyen en km.
# L'ordre doit correspondre à la liste T["objects"] (sans le « Personnalisé »).
SS_OBJECTS = [
    1_391_400.0,   # Soleil
    3_474.8,       # Lune
    4_879.4,       # Mercure
    12_104.0,      # Vénus
    12_742.0,      # Terre
    6_779.0,       # Mars
    139_820.0,     # Jupiter
    116_460.0,     # Saturne (sans anneaux)
    50_724.0,      # Uranus
    49_244.0,      # Neptune
]

def fmt_km(d_km: float) -> str:
    """Distance physique → toujours en km."""
    if d_km <= 0:
        return ""
    return f"{nfmt(d_km, 0)} km"

def fmt_size_km(px: float, km_per_px: float) -> str:
    if km_per_px <= 0 or px <= 0:
        return ""
    return fmt_km(px * km_per_px)

def fmt_area_km(px2: float, km_per_px: float) -> str:
    """Aire en px² → surface physique en km² via une échelle km/px."""
    if km_per_px <= 0 or px2 <= 0:
        return ""
    return f"{nfmt(px2 * km_per_px ** 2, 0)} km²"


def shoelace(pts) -> float:
    n = len(pts)
    if n < 3: return 0.0
    a = 0.0
    for i in range(n):
        j = (i + 1) % n
        a += pts[i].x() * pts[j].y() - pts[j].x() * pts[i].y()
    return abs(a) / 2.0

# ---------------------
#  PROFILE / ROI HELPERS
# ---------------------

def sample_line_bilinear(img_data, sx1, sy1, sx2, sy2, H):
    """Échantillonnage bilinéaire de img_data (3,H,W) le long d'un segment en coord. scène."""
    _, H_data, W_data = img_data.shape
    n = max(2, int(math.hypot(sx2 - sx1, sy2 - sy1)) + 1)
    t = np.linspace(0, 1, n, dtype=np.float32)

    xs      = (sx1 + t * (sx2 - sx1)).clip(0, W_data - 1)
    ys_fits = ((H - 1) - (sy1 + t * (sy2 - sy1))).clip(0, H_data - 1)

    x0 = np.floor(xs).astype(np.int32)
    y0 = np.floor(ys_fits).astype(np.int32)
    x1 = np.clip(x0 + 1, 0, W_data - 1)
    y1 = np.clip(y0 + 1, 0, H_data - 1)
    fx = (xs - x0).astype(np.float32)
    fy = (ys_fits - y0).astype(np.float32)

    result = {}
    for i, ch in enumerate(("R", "G", "B")):
        d = img_data[i]
        result[ch] = (d[y0, x0] * (1 - fx) * (1 - fy) +
                      d[y0, x1] * fx       * (1 - fy) +
                      d[y1, x0] * (1 - fx) * fy       +
                      d[y1, x1] * fx       * fy)
    return result


def roi_stats(img_data, sx1, sy1, sx2, sy2, H):
    """Statistiques par canal sur un rectangle en coord. scène."""
    _, H_data, W_data = img_data.shape
    x_lo = max(0,       int(min(sx1, sx2)))
    x_hi = min(W_data,  int(max(sx1, sx2)) + 1)
    fy1  = (H - 1) - sy1
    fy2  = (H - 1) - sy2
    y_lo = max(0,       int(min(fy1, fy2)))
    y_hi = min(H_data,  int(max(fy1, fy2)) + 1)

    if x_hi <= x_lo or y_hi <= y_lo:
        return None

    stats = {}
    for i, ch in enumerate(("R", "G", "B")):
        roi = img_data[i, y_lo:y_hi, x_lo:x_hi].flatten()
        stats[ch] = {
            "mean":   float(np.mean(roi)),
            "median": float(np.median(roi)),
            "min":    float(np.min(roi)),
            "max":    float(np.max(roi)),
            "std":    float(np.std(roi)),
        }
    return stats, x_hi - x_lo, y_hi - y_lo

# ---------------------
#  PROFILE PLOT WIDGET
# ---------------------

class ProfilePlot(QWidget):
    PAD       = (54, 14, 18, 36)
    CH_COLORS = (
        ("R", QColor("#ff4444")),
        ("G", QColor("#44cc44")),
        ("B", QColor("#4488ff")),
    )

    def __init__(self, data: dict, dist_px: float):
        super().__init__()
        self.data    = data
        self.dist_px = dist_px
        self.setMinimumSize(480, 260)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        pl, pt, pr, pb = self.PAD
        pw = W - pl - pr
        ph = H - pt - pb

        p.fillRect(0, 0, W, H, QColor("#1a1a1a"))
        p.fillRect(pl, pt, pw, ph, QColor("#111111"))

        p.setPen(QPen(QColor("#2e2e2e"), 1))
        for i in range(1, 4):
            p.drawLine(pl, pt + ph * i // 4, pl + pw, pt + ph * i // 4)
        for i in range(1, 4):
            p.drawLine(pl + pw * i // 4, pt, pl + pw * i // 4, pt + ph)

        p.setPen(QPen(QColor("#555555"), 1))
        p.drawRect(pl, pt, pw, ph)

        font = QFont("Monospace", 7)
        p.setFont(font)
        p.setPen(QPen(QColor("#888888"), 1))
        for i in range(5):
            v = 1.0 - i * 0.25
            y = pt + ph * i // 4
            p.drawText(2, y - 6, pl - 6, 14, Qt.AlignmentFlag.AlignRight, f"{v:.2f}")

        for i in range(5):
            xi = int(self.dist_px * i / 4)
            x  = pl + pw * i // 4
            p.drawText(x - 20, pt + ph + 4, 40, 14, Qt.AlignmentFlag.AlignHCenter, str(xi))

        for ch, color in self.CH_COLORS:
            arr = self.data.get(ch)
            if arr is None or len(arr) < 2:
                continue
            p.setPen(QPen(color, 1.5))
            n = len(arr)
            prev = None
            for i in range(n):
                v  = float(arr[i])
                cx = pl + pw * i / (n - 1)
                cy = pt + ph * (1.0 - v)
                pt_now = QPointF(cx, cy)
                if prev is not None:
                    p.drawLine(prev, pt_now)
                prev = pt_now

        p.end()


class ProfileWindow(QDialog):

    def __init__(self, data: dict, dist_px: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle(T["prof_win"].format(n=int(dist_px)))
        self.setStyleSheet(DARK_STYLESHEET)
        self.resize(640, 380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.plot = ProfilePlot(data, dist_px)
        layout.addWidget(self.plot, stretch=1)

        leg = QHBoxLayout()
        for ch, col in ProfilePlot.CH_COLORS:
            lbl = QLabel(f"━  {ch}")
            lbl.setStyleSheet(
                f"color: {col.name()}; font-family: Monospace; "
                f"font-size: 9pt; font-weight: bold;"
            )
            leg.addWidget(lbl)
            leg.addSpacing(12)
        leg.addStretch()
        btn = QPushButton(T["btn_close"])
        btn.setFixedWidth(72)
        btn.clicked.connect(self.close)
        leg.addWidget(btn)
        layout.addLayout(leg)

# ---------------------
#  HELP WINDOW
# ---------------------

class HelpWindow(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(T["help_title"])
        self.setStyleSheet(DARK_STYLESHEET)
        self.resize(720, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        txt = QTextEdit()
        txt.setReadOnly(True)

        md_content = None
        for search_dir in (
            os.path.dirname(os.path.abspath(__file__)),
            os.path.expanduser("~/Claude/SirilJ"),
        ):
            md_path = os.path.join(search_dir, T["help_doc"])
            if os.path.isfile(md_path):
                try:
                    with open(md_path, encoding="utf-8") as f:
                        md_content = f.read()
                    break
                except Exception:
                    pass

        txt.setMarkdown(md_content if md_content is not None else HELP_MD)
        layout.addWidget(txt, stretch=1)

        btn_close = QPushButton(T["btn_close"])
        btn_close.setFixedWidth(80)
        btn_close.clicked.connect(self.close)
        bl = QHBoxLayout()
        bl.addStretch()
        bl.addWidget(btn_close)
        layout.addLayout(bl)

# ---------------------
#  IMAGE LOAD WORKER
# ---------------------

class ImageLoadWorker(QThread):
    done  = pyqtSignal(object, object, object, int, int, object)
    error = pyqtSignal(str)

    def __init__(self, siril):
        super().__init__()
        self.siril = siril

    def run(self):
        fits_path = None
        try:
            tmp = tempfile.mktemp(prefix="sirilj_mesures_")
            fits_path = tmp + ".fit"
            with self.siril.image_lock():
                self.siril.cmd(f'save "{tmp.replace(os.sep, "/")}"')

            with fits.open(fits_path) as hdul:
                header = hdul[0].header
                raw    = hdul[0].data.astype(np.float32)

            if raw.ndim == 2:
                data = np.stack([raw, raw, raw])
            elif raw.ndim == 3 and raw.shape[0] in (1, 3):
                data = np.concatenate([raw, raw, raw], 0) if raw.shape[0] == 1 else raw
            elif raw.ndim == 3 and raw.shape[2] == 3:
                data = raw.transpose(2, 0, 1)
            else:
                data = np.stack([raw[0], raw[0], raw[0]])

            dmax = np.max(data)
            if dmax > 1.0:
                data /= (65535.0 if dmax <= 65535.0 else dmax)
            _, H, W = data.shape

            wcs = pscale = None
            try:
                w = WCS(header)
                if w.has_celestial:
                    scales = proj_plane_pixel_scales(w)
                    pscale = float(np.mean(np.abs(scales))) * 3600.0
                    wcs = w
            except Exception:
                pass

            disp = np.clip(apply_autostretch(data) * 255, 0, 255).astype(np.uint8)
            disp = np.ascontiguousarray(np.flipud(disp.transpose(1, 2, 0)))
            h, w_d, _ = disp.shape
            qimg = QImage(disp.data.tobytes(), w_d, h, 3 * w_d, QImage.Format.Format_RGB888)
            self.done.emit(QPixmap.fromImage(qimg), wcs, pscale, W, H, data)

        except Exception as e:
            self.error.emit(str(e))
        finally:
            if fits_path and os.path.exists(fits_path):
                try: os.remove(fits_path)
                except Exception: pass

# ---------------------
#  MEASURE SCENE
# ---------------------

class MeasureScene(QGraphicsScene):
    line_ready    = pyqtSignal(QPointF, QPointF)
    angle_ready   = pyqtSignal(QPointF, QPointF, QPointF)
    polygon_ready = pyqtSignal(list, int)   # (pts, source_tool)
    profile_ready = pyqtSignal(QPointF, QPointF)
    roi_ready     = pyqtSignal(QPointF, QPointF)
    calib_ready   = pyqtSignal(QPointF, QPointF)
    probe_pos     = pyqtSignal(QPointF)

    def __init__(self):
        super().__init__()
        self._tool          = TOOL_NONE
        self._p1            = None
        self._roi_p1        = None
        self._ang_pts       = []
        self._verts         = []
        self._rubber        = None
        self._overlays      = []
        self._freehand_pts  = []
        self._freehand_segs = []   # temporary segment items, removed on close

    # ---- public API ----

    def set_tool(self, tool: int):
        self._tool = tool
        self._p1 = None
        self._roi_p1 = None
        self._ang_pts.clear()
        self._verts.clear()
        self._drop_rubber()
        self._clear_freehand()

    def clear_all(self):
        for item in self._overlays:
            self.removeItem(item)
        self._overlays.clear()
        self._p1 = None
        self._roi_p1 = None
        self._ang_pts.clear()
        self._verts.clear()
        self._drop_rubber()
        self._clear_freehand()

    def _measure_pen(self, color, dashed=False):
        """Pen cosmétique (largeur constante à l'écran, lisible à tout zoom)."""
        pen = QPen(color, LINE_MEASURE_W)
        pen.setCosmetic(True)
        if dashed:
            pen.setStyle(Qt.PenStyle.DashLine)
        return pen

    def draw_line_result(self, p1, p2, label):
        item = self.addLine(p1.x(), p1.y(), p2.x(), p2.y(),
                            self._measure_pen(COL_LINE))
        self._overlays.append(item)
        self._label(QPointF((p1.x()+p2.x())/2, (p1.y()+p2.y())/2), label)

    def draw_calib_result(self, p1, p2, label):
        item = self.addLine(p1.x(), p1.y(), p2.x(), p2.y(),
                            self._measure_pen(COL_CALIB))
        self._overlays.append(item)
        self._label(QPointF((p1.x()+p2.x())/2, (p1.y()+p2.y())/2), label)

    def draw_angle_result(self, pa, pb, pc, label):
        self._solid(pb, pa, COL_ANGLE)
        self._solid(pb, pc, COL_ANGLE)
        self._arc(pb, pa, pc)
        self._label(pb, label)

    def draw_area_result(self, pts, label, color=COL_AREA):
        poly  = QPolygonF(pts)
        fill  = QColor(color.red(), color.green(), color.blue(), 35)
        item  = self.addPolygon(poly, QPen(color, LINE_W), QBrush(fill))
        self._overlays.append(item)
        cx = sum(p.x() for p in pts) / len(pts)
        cy = sum(p.y() for p in pts) / len(pts)
        self._label(QPointF(cx, cy), label)

    def draw_profile_result(self, p1, p2):
        self._solid(p1, p2, COL_PROFILE)

    def draw_roi_result(self, p1, p2, label):
        x = min(p1.x(), p2.x());  y = min(p1.y(), p2.y())
        w = abs(p2.x() - p1.x()); h = abs(p2.y() - p1.y())
        item = self.addRect(x, y, w, h,
                            QPen(COL_ROI, LINE_W),
                            QBrush(QColor(0, 0, 255, 30)))
        self._overlays.append(item)
        self._label(QPointF(x, y - 4), label)

    # ---- mouse events ----

    def mousePressEvent(self, event):
        pos = event.scenePos()

        if self._tool == TOOL_NONE:
            super().mousePressEvent(event)
            return

        if event.button() == Qt.MouseButton.LeftButton:

            if self._tool in (TOOL_LINE, TOOL_PROFILE, TOOL_CALIB):
                if self._p1 is None:
                    self._p1 = pos
                    self._dot(pos)
                else:
                    self._dot(pos)
                    self._drop_rubber()
                    p1, self._p1 = self._p1, None
                    if self._tool == TOOL_LINE:
                        self.line_ready.emit(p1, pos)
                    elif self._tool == TOOL_CALIB:
                        self.calib_ready.emit(p1, pos)
                    else:
                        self.profile_ready.emit(p1, pos)

            elif self._tool == TOOL_ANGLE:
                self._dot(pos)
                self._ang_pts.append(pos)
                if len(self._ang_pts) == 3:
                    self._drop_rubber()
                    a, b, c = self._ang_pts
                    self._ang_pts.clear()
                    self.angle_ready.emit(a, b, c)

            elif self._tool == TOOL_AREA:
                if self._verts:
                    self._solid(self._verts[-1], pos, COL_AREA)
                self._dot(pos)
                self._verts.append(pos)
                self._drop_rubber()

            elif self._tool == TOOL_FREEHAND:
                self._clear_freehand()
                self._freehand_pts.append(pos)

            elif self._tool == TOOL_ROI:
                self._roi_p1 = pos

        elif event.button() == Qt.MouseButton.RightButton:
            if self._tool == TOOL_AREA and len(self._verts) >= 3:
                self._close_polygon()

        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._tool == TOOL_FREEHAND and len(self._freehand_pts) >= 3:
                pts = list(self._freehand_pts)
                self._clear_freehand()
                self.polygon_ready.emit(pts, TOOL_FREEHAND)
                event.accept()
                return
            if self._tool == TOOL_ROI and self._roi_p1 is not None:
                p2 = event.scenePos()
                self._drop_rubber()
                p1, self._roi_p1 = self._roi_p1, None
                self.roi_ready.emit(p1, p2)
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self._tool == TOOL_AREA and len(self._verts) >= 3:
            self._close_polygon()
        event.accept()

    def mouseMoveEvent(self, event):
        pos = event.scenePos()
        self.probe_pos.emit(pos)

        if self._tool == TOOL_NONE:
            super().mouseMoveEvent(event)
            return

        # Freehand: accumulate points while left button is held
        if self._tool == TOOL_FREEHAND:
            if event.buttons() & Qt.MouseButton.LeftButton and self._freehand_pts:
                prev = self._freehand_pts[-1]
                seg  = self.addLine(prev.x(), prev.y(), pos.x(), pos.y(),
                                    QPen(COL_FREEHAND, LINE_W))
                self._freehand_segs.append(seg)
                self._freehand_pts.append(pos)
            event.accept()
            return

        self._drop_rubber()
        anchor = col = None

        if self._tool in (TOOL_LINE, TOOL_PROFILE, TOOL_CALIB) and self._p1 is not None:
            anchor = self._p1
            col    = {TOOL_LINE: COL_LINE, TOOL_PROFILE: COL_PROFILE,
                      TOOL_CALIB: COL_CALIB}[self._tool]
        elif self._tool == TOOL_ANGLE and self._ang_pts:
            anchor = self._ang_pts[-1];  col = COL_ANGLE
        elif self._tool == TOOL_AREA and self._verts:
            anchor = self._verts[-1];    col = COL_AREA
        elif self._tool == TOOL_ROI and self._roi_p1 is not None:
            p1 = self._roi_p1
            x = min(p1.x(), pos.x()); y = min(p1.y(), pos.y())
            w = abs(pos.x() - p1.x()); h = abs(pos.y() - p1.y())
            self._rubber = self.addRect(
                x, y, w, h, QPen(COL_ROI, LINE_W, Qt.PenStyle.DashLine)
            )
            event.accept()
            return

        if anchor:
            if self._tool in (TOOL_LINE, TOOL_CALIB):
                pen = self._measure_pen(col, dashed=True)
            else:
                pen = QPen(col, LINE_W, Qt.PenStyle.DashLine)
            self._rubber = self.addLine(anchor.x(), anchor.y(),
                                        pos.x(), pos.y(), pen)
        event.accept()

    # ---- drawing helpers ----

    def _dot(self, pos):
        r = POINT_R
        item = self.addEllipse(pos.x()-r, pos.y()-r, r*2, r*2,
                               QPen(Qt.PenStyle.NoPen), QBrush(COL_VERTEX))
        self._overlays.append(item)

    def _solid(self, p1, p2, color):
        item = self.addLine(p1.x(), p1.y(), p2.x(), p2.y(), QPen(color, LINE_W))
        self._overlays.append(item)

    def _label(self, pos, text):
        item = self.addText(text, QFont("Monospace", 8))
        item.setDefaultTextColor(COL_LABEL)
        item.setPos(pos.x() + 6, pos.y() - 18)
        self._overlays.append(item)

    def _arc(self, vertex, pa, pc):
        d_a = math.hypot(pa.x()-vertex.x(), pa.y()-vertex.y())
        d_c = math.hypot(pc.x()-vertex.x(), pc.y()-vertex.y())
        r   = max(8.0, min(min(d_a, d_c) * 0.25, 35.0))
        ang_a = math.atan2(pa.y()-vertex.y(), pa.x()-vertex.x())
        ang_c = math.atan2(pc.y()-vertex.y(), pc.x()-vertex.x())
        diff = ang_c - ang_a
        while diff >  math.pi: diff -= 2*math.pi
        while diff < -math.pi: diff += 2*math.pi
        steps = max(12, int(abs(math.degrees(diff)) / 4))
        prev = None
        for i in range(steps + 1):
            a  = ang_a + diff * i / steps
            pt = QPointF(vertex.x() + r*math.cos(a), vertex.y() + r*math.sin(a))
            if prev is not None:
                self._solid(prev, pt, COL_ANGLE)
            prev = pt

    def _drop_rubber(self):
        if self._rubber:
            self.removeItem(self._rubber)
            self._rubber = None

    def _clear_freehand(self):
        for seg in self._freehand_segs:
            self.removeItem(seg)
        self._freehand_segs.clear()
        self._freehand_pts.clear()

    def _close_polygon(self):
        pts = list(self._verts)
        self._verts.clear()
        self._drop_rubber()
        self.polygon_ready.emit(pts, TOOL_AREA)

# ---------------------
#  MAIN WINDOW
# ---------------------

class MesuresWindow(QMainWindow):

    def __init__(self, siril, app):
        super().__init__()
        self.siril    = siril
        self.app      = app
        self.wcs      = None
        self.pscale   = None
        self.img_h    = 1
        self.img_w    = 1
        self.img_data = None
        self.km_per_px = 0.0      # échelle de calibration objet (0 = non calibré)

        self.setWindowTitle(f"{T['win_title']}  v{VERSION}")
        self.setStyleSheet(DARK_STYLESHEET)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        self.resize(1140, 760)

        self._log_header()
        self._build_ui()
        self._load_image()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        h = QHBoxLayout(root)
        h.setContentsMargins(8, 8, 8, 8)
        h.setSpacing(8)

        # ── PANNEAU GAUCHE ───────────────────────────────────────────
        left = QWidget(); left.setFixedWidth(210)
        lv = QVBoxLayout(left); lv.setContentsMargins(0, 0, 0, 0); lv.setSpacing(10)

        ttl = QLabel(T["panel_title"])
        ttl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ttl.setStyleSheet("font-size: 13pt; font-weight: bold; color: #88aaff;")
        lv.addWidget(ttl)

        g1 = QGroupBox(T["grp_tools"]); g1l = QVBoxLayout(g1)
        self.btn_line     = QPushButton(T["btn_line"])
        self.btn_angle    = QPushButton(T["btn_angle"])
        self.btn_area     = QPushButton(T["btn_area"])
        self.btn_freehand = QPushButton(T["btn_freehand"])
        self.btn_profile  = QPushButton(T["btn_profile"])
        self.btn_roi      = QPushButton(T["btn_roi"])

        tool_defs = [
            (self.btn_line,     T["tip_line"],     TOOL_LINE),
            (self.btn_angle,    T["tip_angle"],    TOOL_ANGLE),
            (self.btn_area,     T["tip_area"],     TOOL_AREA),
            (self.btn_freehand, T["tip_freehand"], TOOL_FREEHAND),
            (self.btn_profile,  T["tip_profile"],  TOOL_PROFILE),
            (self.btn_roi,      T["tip_roi"],      TOOL_ROI),
        ]
        for btn, tip, tool_id in tool_defs:
            btn.setCheckable(True)
            btn.setToolTip(tip)
            btn.clicked.connect(lambda _=False, t=tool_id: self._set_tool(t))
            g1l.addWidget(btn)

        sep_tools = QFrame(); sep_tools.setObjectName("Sep")
        sep_tools.setFrameShape(QFrame.Shape.HLine); sep_tools.setFixedHeight(1)
        g1l.addWidget(sep_tools)

        btn_clear = QPushButton(T["btn_clear"])
        btn_clear.clicked.connect(self._clear)
        g1l.addWidget(btn_clear)
        lv.addWidget(g1)

        g2 = QGroupBox(T["grp_phys"]); g2l = QGridLayout(g2)
        g2l.addWidget(QLabel(T["lbl_dist"]), 0, 0)
        self.spin_dist = QDoubleSpinBox()
        self.spin_dist.setRange(0, 1e12); self.spin_dist.setDecimals(3)
        self.spin_dist.setSpecialValueText("—")
        g2l.addWidget(self.spin_dist, 0, 1)
        g2l.addWidget(QLabel(T["lbl_unit"]), 1, 0)
        self.cmb_unit = QComboBox()
        self.cmb_unit.addItems(["pc", "kpc", "Mpc", "ly", "kly", "Mly", "AU", "km"])
        g2l.addWidget(self.cmb_unit, 1, 1)
        lv.addWidget(g2)

        # ── Calibration par diamètre d'objet (Système Solaire) ───────
        g3 = QGroupBox(T["grp_calib"]); g3l = QGridLayout(g3)
        g3l.addWidget(QLabel(T["lbl_object"]), 0, 0)
        self.cmb_object = QComboBox()
        self.cmb_object.addItems(T["objects"] + [T["obj_custom"]])
        self.cmb_object.currentIndexChanged.connect(self._on_object_changed)
        g3l.addWidget(self.cmb_object, 0, 1)
        self.lbl_custom = QLabel(T["lbl_custom"])
        g3l.addWidget(self.lbl_custom, 1, 0)
        self.spin_custom = QDoubleSpinBox()
        self.spin_custom.setRange(0.0, 1e12); self.spin_custom.setDecimals(1)
        self.spin_custom.setValue(1000.0); self.spin_custom.setEnabled(False)
        g3l.addWidget(self.spin_custom, 1, 1)
        self.btn_calib = QPushButton(T["btn_calib"])
        self.btn_calib.setCheckable(True)
        self.btn_calib.setToolTip(T["tip_calib"])
        self.btn_calib.clicked.connect(lambda _=False: self._set_tool(TOOL_CALIB))
        g3l.addWidget(self.btn_calib, 2, 0, 1, 2)
        self.lbl_calib = QLabel(T["calib_none"])
        self.lbl_calib.setWordWrap(True)
        self.lbl_calib.setStyleSheet("font-size: 8pt; color: #ffcc66;")
        g3l.addWidget(self.lbl_calib, 3, 0, 1, 2)
        lv.addWidget(g3)

        self.lbl_wcs = QLabel(T["wcs_loading"])
        self.lbl_wcs.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_wcs.setStyleSheet("font-size: 8pt; color: #888888;")
        lv.addWidget(self.lbl_wcs)

        lbl_probe_hdr = QLabel(T["probe_hdr"])
        lbl_probe_hdr.setStyleSheet("font-size: 8pt; color: #555555;")
        lbl_probe_hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lv.addWidget(lbl_probe_hdr)

        self.lbl_probe = QLabel(T["probe_none"])
        self.lbl_probe.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_probe.setStyleSheet(
            "font-size: 8pt; font-family: Monospace; color: #aaaaaa;"
        )
        self.lbl_probe.setWordWrap(True)
        lv.addWidget(self.lbl_probe)

        lv.addStretch()

        fl = QHBoxLayout()
        self.chk_top = QCheckBox(T["chk_top"]); self.chk_top.setChecked(True)
        self.chk_top.toggled.connect(self._toggle_top)

        btn_help = QPushButton("?")
        btn_help.setObjectName("HelpButton")
        btn_help.setToolTip(T["tip_help"])
        btn_help.clicked.connect(self._open_help)

        btn_close = QPushButton(T["btn_close"]); btn_close.setObjectName("CloseButton")
        btn_close.setFixedWidth(64)
        btn_close.clicked.connect(self.close)

        fl.addWidget(self.chk_top)
        fl.addStretch()
        fl.addWidget(btn_help)
        fl.addSpacing(4)
        fl.addWidget(btn_close)
        lv.addLayout(fl)
        h.addWidget(left)

        # ── ZONE DROITE ──────────────────────────────────────────────
        rv = QVBoxLayout()

        zb = QHBoxLayout()
        for sym, fn in [("-",   lambda: self.view.scale(1/1.2, 1/1.2)),
                        ("Fit", self._fit),
                        ("1:1", lambda: self.view.resetTransform()),
                        ("+",   lambda: self.view.scale(1.2, 1.2))]:
            b = QPushButton(sym); b.setObjectName("ZBtn"); b.clicked.connect(fn)
            zb.addWidget(b)
        self.lbl_hint = QLabel(T["hint_load"])
        self.lbl_hint.setStyleSheet("color: #888; font-size: 8pt; font-style: italic; margin-left: 8px;")
        zb.addWidget(self.lbl_hint); zb.addStretch()
        rv.addLayout(zb)

        self.scene = MeasureScene()
        self.view  = QGraphicsView(self.scene)
        self.view.setStyleSheet("background-color: #111111; border: none;")
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.pix_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pix_item)
        rv.addWidget(self.view)

        sep = QFrame(); sep.setObjectName("Sep")
        sep.setFrameShape(QFrame.Shape.HLine); sep.setFixedHeight(1)
        rv.addWidget(sep)

        self.txt_result = QPlainTextEdit()
        self.txt_result.setReadOnly(True)
        self.txt_result.setFixedHeight(64)
        self.txt_result.setPlaceholderText(T["placeholder"])
        rv.addWidget(self.txt_result)

        rw = QWidget(); rw.setLayout(rv)
        h.addWidget(rw)

        self.scene.line_ready.connect(self._on_line)
        self.scene.angle_ready.connect(self._on_angle)
        self.scene.polygon_ready.connect(self._on_polygon)
        self.scene.profile_ready.connect(self._on_profile)
        self.scene.roi_ready.connect(self._on_roi)
        self.scene.calib_ready.connect(self._on_calib)
        self.scene.probe_pos.connect(self._on_probe)

    # ---- chargement image ----

    def _load_image(self):
        self._worker = ImageLoadWorker(self.siril)
        self._worker.done.connect(self._on_loaded)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_loaded(self, pixmap, wcs, pscale, W, H, img_data):
        self.wcs = wcs; self.pscale = pscale
        self.img_w = W; self.img_h = H
        self.img_data = img_data
        self.pix_item.setPixmap(pixmap)
        self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
        self._fit()
        if wcs and pscale:
            self.lbl_wcs.setText(T["wcs_ok"].format(nfmt(pscale, 3)))
            self.lbl_wcs.setStyleSheet("font-size: 8pt; color: #88cc88;")
            self.lbl_hint.setText(T["hint_wcs"])
        else:
            self.lbl_wcs.setText(T["wcs_none"])
            self.lbl_wcs.setStyleSheet("font-size: 8pt; color: #cc8844;")
            self.lbl_hint.setText(T["hint_nowcs"])

    def _on_error(self, msg):
        self.lbl_hint.setText(T["err_hint"].format(msg=msg))
        self._append_result(f"{T['err_pfx']} {msg}")
        try: self.siril.log(T["siril_err"].format(msg=msg), LogColor.RED)
        except Exception: pass

    # ---- outils ----

    def _set_tool(self, tool: int):
        for btn, tid in [
            (self.btn_line,     TOOL_LINE),
            (self.btn_angle,    TOOL_ANGLE),
            (self.btn_area,     TOOL_AREA),
            (self.btn_freehand, TOOL_FREEHAND),
            (self.btn_profile,  TOOL_PROFILE),
            (self.btn_roi,      TOOL_ROI),
            (self.btn_calib,    TOOL_CALIB),
        ]:
            btn.setChecked(tool == tid)
        self.scene.set_tool(tool)
        self.view.setDragMode(
            QGraphicsView.DragMode.NoDrag if tool != TOOL_NONE
            else QGraphicsView.DragMode.ScrollHandDrag
        )

    def _clear(self):
        self.scene.clear_all()
        for btn in (self.btn_line, self.btn_angle, self.btn_area,
                    self.btn_freehand, self.btn_profile, self.btn_roi,
                    self.btn_calib):
            btn.setChecked(False)
        self.scene.set_tool(TOOL_NONE)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.txt_result.clear()

    # ---- mesures ----

    def _fits_xy(self, sx, sy):
        return sx, float(self.img_h - 1) - sy

    def _on_line(self, p1, p2):
        dist_px = math.hypot(p2.x()-p1.x(), p2.y()-p1.y())
        parts = [f"{nfmt(dist_px, 1)} px"]
        if self.wcs and self.pscale:
            try:
                c1 = SkyCoord.from_pixel(*self._fits_xy(p1.x(), p1.y()), self.wcs)
                c2 = SkyCoord.from_pixel(*self._fits_xy(p2.x(), p2.y()), self.wcs)
                sep_deg = c1.separation(c2).deg
                parts.append(fmt_angle(sep_deg))
                dist_pc = self._dist_pc()
                if dist_pc > 0:
                    parts.append(fmt_physical(sep_deg * 3600.0, dist_pc))
            except Exception as e:
                parts.append(f"[WCS:{e}]")
        if self.km_per_px > 0:
            parts.append(fmt_size_km(dist_px, self.km_per_px))
        label = "  |  ".join(parts)
        self.scene.draw_line_result(p1, p2, label)
        self._append_result(f"{T['pfx_line']}  {label}")

    def _on_angle(self, pa, pb, pc):
        bax, bay = pa.x()-pb.x(), pa.y()-pb.y()
        bcx, bcy = pc.x()-pb.x(), pc.y()-pb.y()
        mag_a = math.hypot(bax, bay); mag_c = math.hypot(bcx, bcy)
        if mag_a < 1e-9 or mag_c < 1e-9:
            return
        cos_t     = (bax*bcx + bay*bcy) / (mag_a * mag_c)
        angle_deg = math.degrees(math.acos(max(-1.0, min(1.0, cos_t))))
        parts = [fmt_dms(angle_deg)]

        if self.wcs:
            try:
                sky_b = SkyCoord.from_pixel(*self._fits_xy(pb.x(), pb.y()), self.wcs)
                sky_a = SkyCoord.from_pixel(*self._fits_xy(pa.x(), pa.y()), self.wcs)
                sky_c = SkyCoord.from_pixel(*self._fits_xy(pc.x(), pc.y()), self.wcs)
                pa_ba = sky_b.position_angle(sky_a).deg
                pa_bc = sky_b.position_angle(sky_c).deg
                sky_angle = abs(pa_ba - pa_bc) % 360
                if sky_angle > 180: sky_angle = 360 - sky_angle
                parts.append(f"sky {fmt_dms(sky_angle)}")
            except Exception:
                pass

        label = "  |  ".join(parts)
        self.scene.draw_angle_result(pa, pb, pc, label)
        self._append_result(f"{T['pfx_angle']}  {label}")
        self.scene.set_tool(TOOL_ANGLE)

    def _on_polygon(self, pts: list, source_tool: int):
        area_px2 = shoelace(pts)
        parts = [f"{nfmt(area_px2, 0)} px²"]
        if self.wcs and self.pscale:
            try:
                area_arcsec2 = area_px2 * self.pscale ** 2
                parts.append(fmt_area(area_arcsec2))
                dist_pc = self._dist_pc()
                if dist_pc > 0:
                    phys = fmt_physical_area(area_arcsec2, dist_pc)
                    if phys:
                        parts.append(phys)
            except Exception:
                pass
        if self.km_per_px > 0:
            km_area = fmt_area_km(area_px2, self.km_per_px)
            if km_area:
                parts.append(km_area)
        label = "  |  ".join(parts)

        if source_tool == TOOL_FREEHAND:
            self.scene.draw_area_result(pts, label, COL_FREEHAND)
            self._append_result(f"{T['pfx_freehand']}  {label}")
        else:
            self.scene.draw_area_result(pts, label, COL_AREA)
            self._append_result(f"{T['pfx_area']}  {label}")

        self.scene.set_tool(source_tool)

    def _on_profile(self, p1, p2):
        dist_px = math.hypot(p2.x()-p1.x(), p2.y()-p1.y())
        if self.img_data is None:
            self._append_result(T["prof_nodata"])
            return
        samples = sample_line_bilinear(
            self.img_data, p1.x(), p1.y(), p2.x(), p2.y(), self.img_h
        )
        self.scene.draw_profile_result(p1, p2)
        n = len(samples["R"])
        self._append_result(
            f"{T['pfx_profile']}  {nfmt(int(dist_px), 0)} px  ({nfmt(n, 0)} {T['samples']})"
        )
        win = ProfileWindow(samples, dist_px)
        win.show()
        self._profile_windows = getattr(self, "_profile_windows", [])
        self._profile_windows.append(win)
        self.scene.set_tool(TOOL_PROFILE)

    def _on_roi(self, p1, p2):
        if self.img_data is None:
            self._append_result(T["roi_nodata"])
            return
        result = roi_stats(
            self.img_data, p1.x(), p1.y(), p2.x(), p2.y(), self.img_h
        )
        if result is None:
            self._append_result(T["roi_small"])
            return
        stats, roi_w, roi_h = result
        px_w = abs(p2.x() - p1.x())
        px_h = abs(p2.y() - p1.y())
        label = f"{nfmt(int(px_w), 0)}×{nfmt(int(px_h), 0)} px"
        self.scene.draw_roi_result(p1, p2, label)
        self._append_result(
            f"{T['pfx_roi']}  {label}  ({nfmt(roi_w, 0)}×{nfmt(roi_h, 0)} {T['samples']})"
        )
        for ch in ("R", "G", "B"):
            st = stats[ch]
            self._append_result(
                f"  {ch}  mean:{nfmt(st['mean'], 3)}  med:{nfmt(st['median'], 3)}"
                f"  min:{nfmt(st['min'], 3)}  max:{nfmt(st['max'], 3)}  σ:{nfmt(st['std'], 3)}"
            )
        self.scene.set_tool(TOOL_ROI)

    def _on_object_changed(self, idx: int):
        is_custom = (idx == self.cmb_object.count() - 1)
        self.spin_custom.setEnabled(is_custom)

    def _on_calib(self, p1, p2):
        dist_px = math.hypot(p2.x()-p1.x(), p2.y()-p1.y())
        if dist_px < 1e-6:
            return
        idx = self.cmb_object.currentIndex()
        if idx < len(SS_OBJECTS):
            diam_km  = SS_OBJECTS[idx]
            obj_name = T["objects"][idx]
        else:
            diam_km  = float(self.spin_custom.value())
            obj_name = T["obj_custom"].rstrip("…")
        if diam_km <= 0:
            return
        self.km_per_px = diam_km / dist_px
        label = f"Ø {fmt_km(diam_km)}  →  {nfmt(self.km_per_px, 1)} km/px"
        self.scene.draw_calib_result(p1, p2, label)
        self._append_result(f"{T['pfx_calib']}  {label}")
        self.lbl_calib.setText(T["calib_set"].format(
            scale=nfmt(self.km_per_px, 1), obj=obj_name, diam=fmt_km(diam_km)))
        self.scene.set_tool(TOOL_CALIB)

    def _on_probe(self, pos):
        if self.img_data is None:
            return
        sx, sy = pos.x(), pos.y()
        fx = int(sx)
        fy = int(self.img_h - 1 - sy)
        if 0 <= fx < self.img_w and 0 <= fy < self.img_h:
            r = float(self.img_data[0, fy, fx])
            g = float(self.img_data[1, fy, fx])
            b = float(self.img_data[2, fy, fx])
            self.lbl_probe.setText(
                f"({fx}, {fy})\nR:{nfmt(r, 3)}  G:{nfmt(g, 3)}  B:{nfmt(b, 3)}"
            )
        else:
            self.lbl_probe.setText(T["probe_none"])

    def _append_result(self, text: str):
        self.txt_result.appendPlainText(text)
        try: self.siril.log(f"{T['siril_pfx']}{text}")
        except Exception: pass

    def _dist_pc(self) -> float:
        v = self.spin_dist.value()
        if v <= 0: return 0.0
        return {"pc":  v,
                "kpc": v * 1e3,
                "Mpc": v * 1e6,
                "ly":  v / 3.26156,
                "kly": v * 1e3 / 3.26156,
                "Mly": v * 1e6 / 3.26156,
                "AU":  v / 206_265.0,
                "km":  v / (_AU_KM * 206_265.0),
                }.get(self.cmb_unit.currentText(), v)

    def _fit(self):
        self.view.fitInView(self.pix_item, Qt.AspectRatioMode.KeepAspectRatio)

    def _toggle_top(self, checked):
        flags = self.windowFlags()
        flags = flags | Qt.WindowType.WindowStaysOnTopHint if checked \
            else flags & ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags); self.show()

    def _open_help(self):
        HelpWindow(self).show()

    def _log_header(self):
        msg = (
            "\n##############################################\n"
            f"# {T['win_title']} v{VERSION}\n"
            f"{T['log_hdr_2']}\n"
            "##############################################"
        )
        try: self.siril.log(msg)
        except Exception: print(msg)

# ---------------------
#  ENTRY POINT
# ---------------------

def main():
    app = QApplication(sys.argv)
    siril = s.SirilInterface()
    try: siril.connect()
    except Exception: pass
    gui = MesuresWindow(siril, app)
    gui.show()
    app.exec()


if __name__ == "__main__":
    main()
