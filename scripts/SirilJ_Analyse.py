##############################################
# SirilJ — Analyse
# Outils d'analyse d'image (équivalents ImageJ)
# Version 1.0.0
##############################################
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Crédits
# -------
#   • Analyse de particules : scikit-image (regionprops)
#   • Surface 3D : matplotlib
#   • Interface : PyQt6 / conventions VeraLux

"""
SirilJ Analyse — deux outils d'analyse sur l'image courante de Siril,
sans équivalent natif dans Siril :

  Onglet Particules (ImageJ « Analyze Particles »)
  ------------------------------------------------
  Seuillage → étiquetage → mesure de chaque objet (taches solaires,
  étoiles, cratères…) : aire, centroïde, diamètre équivalent,
  circularité, intensité moyenne. Tableau exportable en CSV, contours
  superposés sur l'image. Conversion en arcsec² si l'image est résolue.

  Onglet Surface 3D (ImageJ « Surface Plot »)
  -------------------------------------------
  Représentation en relief de l'intensité (cœur de galaxie, PSF,
  nébuleuse). Sous-échantillonnage réglable, palette, échelle log.

Compatibilité
-------------
• Siril 1.3+
• Python 3.10+ (via sirilpy)
• Dépendances : numpy, astropy, scipy, scikit-image, matplotlib, PyQt6
"""

import sys
import os
import csv
import tempfile

try:
    import sirilpy as s
except ImportError:
    print("Erreur : module sirilpy introuvable.")
    sys.exit(1)

s.ensure_installed("numpy", "astropy", "scipy", "scikit-image", "matplotlib", "PyQt6")

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar,
)
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (enregistre la projection 3d)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QComboBox, QCheckBox, QSlider,
    QSpinBox, QDoubleSpinBox, QProgressBar, QTextEdit, QFileDialog,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGroupBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings, QTimer
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QFont

VERSION = "1.0.0"

# ── Dark stylesheet ───────────────────────────────────────────────────────────
DARK_SS = """
QWidget            { background:#2b2b2b; color:#d4d4d4; font-size:11px; }
QMainWindow        { background:#2b2b2b; }
QTabWidget::pane   { border:1px solid #444; }
QTabBar::tab       { background:#3c3c3c; color:#999; padding:5px 16px;
                     border:1px solid #444; border-bottom:none;
                     border-radius:3px 3px 0 0; }
QTabBar::tab:selected { background:#2b2b2b; color:#d4d4d4; }
QPushButton        { background:#3c3c3c; color:#d4d4d4; border:1px solid #555;
                     border-radius:4px; padding:4px 10px; }
QPushButton:hover  { background:#4a4a4a; }
QPushButton:pressed{ background:#555; }
QPushButton:disabled { color:#666; border-color:#444; }
QPushButton#BtnGo  { background:#1e6b1e; color:#fff; font-weight:bold;
                     border:1px solid #2a9b2a; padding:6px 12px; }
QPushButton#BtnGo:hover    { background:#248c24; }
QPushButton#BtnGo:disabled { background:#333; color:#666; border-color:#444; }
QLineEdit, QComboBox { background:#3c3c3c; border:1px solid #555;
                       border-radius:3px; padding:3px 6px; color:#d4d4d4; }
QComboBox QAbstractItemView { background:#2b2b2b; color:#d4d4d4;
                               selection-background-color:#555; }
QSpinBox, QDoubleSpinBox { background:#1e1e1e; border:1px solid #555;
                            border-radius:3px; padding:2px 4px; color:#d4d4d4; }
QCheckBox::indicator { width:14px; height:14px; border:1px solid #666;
                        border-radius:2px; background:#1e1e1e; }
QCheckBox::indicator:checked { background:#4caf50; border-color:#4caf50; }
QGroupBox          { border:1px solid #555; border-radius:4px;
                     margin-top:8px; padding-top:4px; }
QGroupBox::title   { subcontrol-origin:margin; subcontrol-position:top left;
                     padding:0 4px; color:#aaa; }
QProgressBar       { border:1px solid #555; border-radius:3px; background:#1e1e1e;
                     text-align:center; color:#d4d4d4; }
QProgressBar::chunk { background:#2a6f2a; }
QTextEdit          { background:#1a1a1a; border:1px solid #444; color:#b4b4b4;
                     font-family:monospace; font-size:10px; }
QGraphicsView      { background:#111; border:1px solid #444; }
QTableWidget       { background:#1e1e1e; gridline-color:#3a3a3a; color:#d4d4d4; }
QTableWidget::item:selected { background:#3a5f3a; }
QHeaderView::section { background:#333; color:#aaa; padding:3px; border:1px solid #444; }
QSlider::groove:horizontal { height:4px; background:#555; border-radius:2px; }
QSlider::handle:horizontal { width:12px; background:#aaa; border-radius:6px;
                              margin:-5px 0; }
QScrollBar:vertical   { background:#2b2b2b; width:10px; }
QScrollBar::handle:vertical { background:#555; border-radius:5px; }
QScrollBar:horizontal { background:#2b2b2b; height:10px; }
QScrollBar::handle:horizontal { background:#555; border-radius:5px; }
"""

# ── Autostretch (VeraLux / Siril MTF) ──────────────────────────────────────────
def _mtf(x, m, lo, hi):
    dist = hi - lo
    if dist < 1e-9:
        return np.where(x > lo, 1.0, 0.0).astype(np.float32)
    xp = np.clip((x - lo) / dist, 0.0, 1.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        y = ((m - 1.0) * xp) / ((2.0 * m - 1.0) * xp - m)
    return np.nan_to_num(y, nan=0.0, posinf=1.0, neginf=0.0).astype(np.float32)

def apply_autostretch(img_rgb):
    """img_rgb : (3,H,W) [0,1] → (3,H,W) étiré [0,1]."""
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


# ── Image loader (image courante de Siril) ──────────────────────────────────────
class ImageLoadWorker(QThread):
    done  = pyqtSignal(object, object, object, int, int, object)  # pixmap, wcs, pscale, W, H, data
    error = pyqtSignal(str)

    def __init__(self, siril):
        super().__init__()
        self.siril = siril

    def run(self):
        fits_path = None
        try:
            tmp = tempfile.mktemp(prefix="sirilj_analyse_")
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

            dmax = float(np.max(data))
            if dmax > 1.0:
                data = data / (65535.0 if dmax <= 65535.0 else dmax)
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
            qimg = QImage(disp.tobytes(), w_d, h, 3 * w_d, QImage.Format.Format_RGB888)
            self.done.emit(QPixmap.fromImage(qimg), wcs, pscale, W, H, data)

        except Exception as e:
            self.error.emit(str(e))
        finally:
            if fits_path and os.path.exists(fits_path):
                try: os.remove(fits_path)
                except Exception: pass


# ── Particle analysis worker ────────────────────────────────────────────────────
def _prop(pr, *names, default=0.0):
    """Lecture robuste d'une propriété regionprops (noms variant selon
    la version de scikit-image)."""
    for nm in names:
        try:
            v = getattr(pr, nm)
            if v is not None:
                return v
        except Exception:
            pass
    return default


class ParticleWorker(QThread):
    done  = pyqtSignal(object)   # list of dict
    error = pyqtSignal(str)

    def __init__(self, lum_raw, lum_disp, params, parent=None):
        super().__init__(parent)
        self.lum_raw  = lum_raw     # valeurs d'origine (intensités mesurées)
        self.lum_disp = lum_disp    # autostretch [0,1] (sert au seuillage)
        self.params   = params

    def run(self):
        try:
            from skimage.measure import label, regionprops
            from skimage.filters import threshold_otsu

            disp = self.lum_disp     # seuillage sur l'image affichée (étirée)
            raw  = self.lum_raw      # mesures d'intensité sur les données brutes
            p    = self.params

            # Le seuil porte sur l'image étirée → cohérent avec ce que l'on voit.
            thr = float(threshold_otsu(disp)) if p["auto_thr"] else float(p["thr"])
            mask = (disp < thr) if p["dark_objects"] else (disp > thr)

            lbl   = label(mask)
            props = regionprops(lbl, intensity_image=raw)

            H, W = disp.shape
            res  = []
            for pr in props:
                area = float(pr.area)
                if area < p["min_area"] or (p["max_area"] > 0 and area > p["max_area"]):
                    continue
                minr, minc, maxr, maxc = pr.bbox
                if p["exclude_border"] and (minr == 0 or minc == 0
                                            or maxr >= H or maxc >= W):
                    continue
                per  = float(_prop(pr, "perimeter"))
                circ = min(4.0 * np.pi * area / (per * per), 1.0) if per > 0 else 0.0
                if circ < p["min_circ"]:
                    continue
                r, c = pr.centroid           # (row, col) en orientation FITS
                res.append({
                    "area":   area,
                    "x":      float(c),       # FITS X (depuis la gauche)
                    "y":      float(r),       # FITS Y (depuis le bas)
                    "diam":   float(_prop(pr, "equivalent_diameter",
                                          "equivalent_diameter_area")),
                    "circ":   circ,
                    "ecc":    float(_prop(pr, "eccentricity")),
                    "imean":  float(_prop(pr, "intensity_mean", "mean_intensity")),
                    "imax":   float(_prop(pr, "intensity_max", "max_intensity")),
                    "bbox":   (int(minr), int(minc), int(maxr), int(maxc)),
                })
            res.sort(key=lambda d: d["area"], reverse=True)
            self.done.emit({"thr": thr, "items": res})
        except Exception as e:
            self.error.emit(str(e))


# ── Zoom view ────────────────────────────────────────────────────────────────
class ZoomView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    def wheelEvent(self, event):
        f = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(f, f)


# ── Main window ────────────────────────────────────────────────────────────────
class AnalyseWindow(QMainWindow):

    def __init__(self, siril):
        super().__init__()
        self.siril = siril
        self.setWindowTitle(f"SirilJ Analyse — v{VERSION}")
        self.setMinimumSize(1040, 700)
        self.setStyleSheet(DARK_SS)

        # State
        self.data:     "np.ndarray|None" = None   # (3,H,W) [0,1] orientation FITS
        self.lum:      "np.ndarray|None" = None   # (H,W) brute
        self.lum_disp: "np.ndarray|None" = None   # (H,W) autostretch
        self.W = self.H = 0
        self.wcs = None
        self.pscale = None                       # arcsec/px
        self._particles = []
        self._loader = None
        self._pworker = None

        self._build_ui()
        self._load_image()

    # =========================================================================
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        v = QVBoxLayout(central)
        v.setContentsMargins(6, 6, 6, 4)
        v.setSpacing(4)

        top = QHBoxLayout()
        self.lbl_img = QLabel("Image : —")
        self.lbl_img.setStyleSheet("color:#7ec77e; font-weight:bold;")
        top.addWidget(self.lbl_img)
        top.addStretch()
        btn_reload = QPushButton("⟳ Recharger l'image")
        btn_reload.clicked.connect(self._load_image)
        top.addWidget(btn_reload)
        v.addLayout(top)

        self.tabs = QTabWidget()
        v.addWidget(self.tabs)
        self._build_tab_particles()
        self._build_tab_surface()

        self.statusBar().showMessage("Chargement de l'image…")

    # ── Onglet Particules ──────────────────────────────────────────────────────
    def _build_tab_particles(self):
        tab = QWidget()
        self.tabs.addTab(tab, "⬤  Particules")
        h = QHBoxLayout(tab)
        h.setSpacing(8)

        left = QWidget(); left.setFixedWidth(250)
        lv = QVBoxLayout(left); lv.setContentsMargins(0,0,0,0); lv.setSpacing(6)

        grp = QGroupBox("Seuillage")
        g = QGridLayout(grp)
        self.chk_auto = QCheckBox("Seuil automatique (Otsu)")
        self.chk_auto.setChecked(True)
        self.chk_auto.toggled.connect(self._on_auto_toggled)
        g.addWidget(self.chk_auto, 0, 0, 1, 2)
        g.addWidget(QLabel("Seuil :"), 1, 0)
        self.sld_thr = QSlider(Qt.Orientation.Horizontal)
        self.sld_thr.setRange(0, 1000); self.sld_thr.setValue(500)
        self.sld_thr.setEnabled(False)
        self.sld_thr.valueChanged.connect(
            lambda val: self.lbl_thr.setText(f"{val/1000:.3f}"))
        g.addWidget(self.sld_thr, 1, 1)
        self.lbl_thr = QLabel("0.500")
        g.addWidget(self.lbl_thr, 2, 1)
        self.cmb_pol = QComboBox()
        self.cmb_pol.addItems(["Objets clairs / fond sombre (étoiles)",
                               "Objets sombres / fond clair (taches)"])
        g.addWidget(self.cmb_pol, 3, 0, 1, 2)
        lv.addWidget(grp)

        grp2 = QGroupBox("Filtres")
        g2 = QGridLayout(grp2)
        g2.addWidget(QLabel("Aire min (px²) :"), 0, 0)
        self.spn_amin = QSpinBox(); self.spn_amin.setRange(1, 10_000_000); self.spn_amin.setValue(5)
        g2.addWidget(self.spn_amin, 0, 1)
        g2.addWidget(QLabel("Aire max (px²) :"), 1, 0)
        self.spn_amax = QSpinBox(); self.spn_amax.setRange(0, 100_000_000); self.spn_amax.setValue(0)
        self.spn_amax.setToolTip("0 = pas de limite")
        g2.addWidget(self.spn_amax, 1, 1)
        g2.addWidget(QLabel("Circularité min :"), 2, 0)
        self.spn_circ = QDoubleSpinBox(); self.spn_circ.setRange(0.0, 1.0)
        self.spn_circ.setSingleStep(0.05); self.spn_circ.setValue(0.0)
        g2.addWidget(self.spn_circ, 2, 1)
        self.chk_border = QCheckBox("Exclure objets aux bords")
        self.chk_border.setChecked(True)
        g2.addWidget(self.chk_border, 3, 0, 1, 2)
        lv.addWidget(grp2)

        self.lbl_count = QLabel("—")
        self.lbl_count.setStyleSheet("color:#7ec77e; font-weight:bold; font-size:12px;")
        self.lbl_count.setWordWrap(True)
        lv.addWidget(self.lbl_count)

        lv.addStretch()
        self.btn_analyse = QPushButton("▶  Analyser")
        self.btn_analyse.setObjectName("BtnGo")
        self.btn_analyse.clicked.connect(self._analyse)
        lv.addWidget(self.btn_analyse)
        self.btn_csv = QPushButton("Exporter CSV…")
        self.btn_csv.setEnabled(False)
        self.btn_csv.clicked.connect(self._export_csv)
        lv.addWidget(self.btn_csv)
        h.addWidget(left)

        right = QWidget()
        rv = QVBoxLayout(right); rv.setContentsMargins(0,0,0,0); rv.setSpacing(4)
        self._scene = QGraphicsScene()
        self._view  = ZoomView(self._scene)
        self._pixitem = None
        rv.addWidget(self._view, stretch=3)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["#", "Aire px²", "Aire arcsec²", "X", "Y", "Circ.", "I.moy"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setMaximumHeight(170)
        rv.addWidget(self.table, stretch=1)
        h.addWidget(right, stretch=1)

    # ── Onglet Surface 3D ───────────────────────────────────────────────────────
    def _build_tab_surface(self):
        tab = QWidget()
        self.tabs.addTab(tab, "⛰  Surface 3D")
        h = QHBoxLayout(tab)
        h.setSpacing(8)

        left = QWidget(); left.setFixedWidth(230)
        lv = QVBoxLayout(left); lv.setContentsMargins(0,0,0,0); lv.setSpacing(6)

        grp = QGroupBox("Rendu")
        g = QGridLayout(grp)
        g.addWidget(QLabel("Résolution :"), 0, 0)
        self.spn_res = QSpinBox(); self.spn_res.setRange(20, 400); self.spn_res.setValue(150)
        self.spn_res.setToolTip("Côté max de la grille sous-échantillonnée")
        g.addWidget(self.spn_res, 0, 1)
        g.addWidget(QLabel("Palette :"), 1, 0)
        self.cmb_cmap = QComboBox()
        self.cmb_cmap.addItems(["viridis", "inferno", "magma", "plasma",
                                "gray", "hot", "jet", "cividis"])
        g.addWidget(self.cmb_cmap, 1, 1)
        self.chk_log = QCheckBox("Échelle logarithmique")
        g.addWidget(self.chk_log, 2, 0, 1, 2)
        self.chk_stretch = QCheckBox("Appliquer l'autostretch")
        g.addWidget(self.chk_stretch, 3, 0, 1, 2)
        lv.addWidget(grp)

        lv.addStretch()
        self.btn_surf = QPushButton("▶  Tracer la surface")
        self.btn_surf.setObjectName("BtnGo")
        self.btn_surf.clicked.connect(self._plot_surface)
        lv.addWidget(self.btn_surf)
        h.addWidget(left)

        right = QWidget()
        rv = QVBoxLayout(right); rv.setContentsMargins(0,0,0,0); rv.setSpacing(2)
        self.fig    = Figure(figsize=(5, 4), facecolor="#2b2b2b")
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, right)
        rv.addWidget(self.toolbar)
        rv.addWidget(self.canvas, stretch=1)
        h.addWidget(right, stretch=1)

    # =========================================================================
    #  Image loading
    # =========================================================================
    def _load_image(self):
        self.statusBar().showMessage("Chargement de l'image…")
        self._loader = ImageLoadWorker(self.siril)
        self._loader.done.connect(self._on_image)
        self._loader.error.connect(lambda e: self.statusBar().showMessage(f"✗ {e}"))
        self._loader.start()

    def _on_image(self, pixmap, wcs, pscale, W, H, data):
        self.data   = data
        self.lum    = data.mean(axis=0).astype(np.float32)   # (H,W) brute, FITS orient.
        # Luminance étirée : sert de base au seuillage (cohérent avec l'affichage)
        self.lum_disp = apply_autostretch(np.stack([self.lum, self.lum, self.lum]))[0]
        self.W, self.H = W, H
        self.wcs    = wcs
        self.pscale = pscale

        if self._pixitem is None:
            self._pixitem = self._scene.addPixmap(pixmap)
        else:
            self._pixitem.setPixmap(pixmap)
        self._scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
        QTimer.singleShot(50, lambda: self._view.fitInView(
            self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio))

        scale = f"  •  {pscale:.3f}\"/px" if pscale else "  •  pas d'astrométrie"
        self.lbl_img.setText(f"Image : {W}×{H} px{scale}")
        self.statusBar().showMessage("Image chargée.")

    # =========================================================================
    #  Particles
    # =========================================================================
    def _on_auto_toggled(self, checked: bool):
        self.sld_thr.setEnabled(not checked)

    def _analyse(self):
        if self.lum is None:
            self.statusBar().showMessage("Aucune image chargée.")
            return
        params = {
            "auto_thr":       self.chk_auto.isChecked(),
            "thr":            self.sld_thr.value() / 1000.0,
            "dark_objects":   self.cmb_pol.currentIndex() == 1,
            "min_area":       float(self.spn_amin.value()),
            "max_area":       float(self.spn_amax.value()),
            "min_circ":       float(self.spn_circ.value()),
            "exclude_border": self.chk_border.isChecked(),
        }
        self.btn_analyse.setEnabled(False)
        self.statusBar().showMessage("Analyse en cours…")
        self._pworker = ParticleWorker(self.lum, self.lum_disp, params)
        self._pworker.done.connect(self._on_particles)
        self._pworker.error.connect(lambda e: (self.statusBar().showMessage(f"✗ {e}"),
                                               self.btn_analyse.setEnabled(True)))
        self._pworker.start()

    def _on_particles(self, result):
        self.btn_analyse.setEnabled(True)
        items = result["items"]
        self._particles = items
        n = len(items)

        total_area = sum(d["area"] for d in items)
        msg = f"{n} objet(s) détecté(s)\nSeuil = {result['thr']:.3f}"
        if n:
            msg += f"\nAire totale : {total_area:,.0f} px²"
            if self.pscale:
                a2 = total_area * self.pscale ** 2
                msg += f"  ({a2:,.1f} arcsec²)"
        self.lbl_count.setText(msg)
        self.btn_csv.setEnabled(n > 0)

        # Tableau
        self.table.setRowCount(n)
        for i, d in enumerate(items):
            a2 = f"{d['area']*self.pscale**2:,.2f}" if self.pscale else "—"
            vals = [str(i+1), f"{d['area']:,.0f}", a2,
                    f"{d['x']:.1f}", f"{d['y']:.1f}",
                    f"{d['circ']:.3f}", f"{d['imean']:.4f}"]
            for col, val in enumerate(vals):
                it = QTableWidgetItem(val)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(i, col, it)

        self._draw_overlays()
        self.statusBar().showMessage(f"✓ {n} objet(s).")
        try: self.siril.log(f"SirilJ Analyse — {n} particule(s) détectée(s).")
        except Exception: pass

    def _draw_overlays(self):
        # Retire les anciens marqueurs (garde le pixmap)
        for item in list(self._scene.items()):
            if not isinstance(item, QGraphicsPixmapItem):
                self._scene.removeItem(item)
        pen  = QPen(QColor("#ff4444"), 0)   # cosmetic pen (épaisseur constante)
        pen.setCosmetic(True)
        fnt  = QFont("Monospace", 7)
        H = self.H
        for i, d in enumerate(self._particles):
            minr, minc, maxr, maxc = d["bbox"]   # maxr/maxc exclusifs
            # FITS row r → scène y = H-1-r. Lignes occupées : minr..maxr-1.
            # Haut du rectangle (plus petit y scène) = H - maxr.
            sy_top = H - maxr
            sx     = minc
            w      = maxc - minc
            ht     = maxr - minr
            self._scene.addRect(sx, sy_top, w, ht, pen)
            t = self._scene.addText(str(i+1), fnt)
            t.setDefaultTextColor(QColor("#ffd24d"))
            t.setPos(sx, sy_top - 14)

    def _export_csv(self):
        if not self._particles:
            return
        f, _ = QFileDialog.getSaveFileName(self, "Exporter CSV",
                                           os.path.join(os.getcwd(), "particules.csv"),
                                           "CSV (*.csv)")
        if not f:
            return
        try:
            with open(f, "w", newline="") as fh:
                wcsv = csv.writer(fh)
                head = ["#", "aire_px2", "x_fits", "y_fits", "diam_px",
                        "circularite", "excentricite", "i_moy", "i_max"]
                if self.pscale:
                    head.insert(2, "aire_arcsec2")
                wcsv.writerow(head)
                for i, d in enumerate(self._particles):
                    row = [i+1, f"{d['area']:.1f}", f"{d['x']:.2f}", f"{d['y']:.2f}",
                           f"{d['diam']:.2f}", f"{d['circ']:.4f}", f"{d['ecc']:.4f}",
                           f"{d['imean']:.6f}", f"{d['imax']:.6f}"]
                    if self.pscale:
                        row.insert(2, f"{d['area']*self.pscale**2:.3f}")
                    wcsv.writerow(row)
            self.statusBar().showMessage(f"✓ CSV exporté : {f}")
        except Exception as e:
            self.statusBar().showMessage(f"✗ {e}")

    # =========================================================================
    #  Surface 3D
    # =========================================================================
    def _plot_surface(self):
        if self.lum is None:
            self.statusBar().showMessage("Aucune image chargée.")
            return
        try:
            from skimage.measure import block_reduce
            z = self.lum
            if self.chk_stretch.isChecked():
                z = apply_autostretch(np.stack([z, z, z]))[0]

            target = self.spn_res.value()
            factor = max(1, int(max(z.shape) / target))
            if factor > 1:
                z = block_reduce(z, (factor, factor), np.mean)
            if self.chk_log.isChecked():
                z = np.log1p(np.clip(z, 0, None))

            H, W = z.shape
            xs = np.arange(W); ys = np.arange(H)
            X, Y = np.meshgrid(xs, ys)

            self.fig.clear()
            ax = self.fig.add_subplot(111, projection="3d")
            ax.set_facecolor("#2b2b2b")
            surf = ax.plot_surface(X, Y, z, cmap=self.cmb_cmap.currentText(),
                                   linewidth=0, antialiased=True)
            ax.set_xlabel("X", color="#ccc"); ax.set_ylabel("Y", color="#ccc")
            ax.set_zlabel("Intensité", color="#ccc")
            ax.tick_params(colors="#999")
            for pane in (ax.xaxis, ax.yaxis, ax.zaxis):
                pane.set_pane_color((0.17, 0.17, 0.17, 1.0))
            self.fig.colorbar(surf, ax=ax, shrink=0.6, pad=0.1)
            self.canvas.draw()
            self.statusBar().showMessage(
                f"Surface tracée ({W}×{H}, sous-éch. ×{factor}).")
        except Exception as e:
            self.statusBar().showMessage(f"✗ {e}")

    # =========================================================================
    def closeEvent(self, event):
        for w in (self._loader, self._pworker):
            if w and w.isRunning():
                w.wait(3000)
        super().closeEvent(event)


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    siril = s.SirilInterface()
    try:
        siril.connect()
    except Exception as e:
        print(f"Avertissement : connexion Siril impossible ({e}).")
    win = AnalyseWindow(siril)
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
