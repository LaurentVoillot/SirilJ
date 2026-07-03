##############################################
# SirilJ — Séquence
# Outils de séquence (équivalents ImageJ)
# Version 1.0.0
##############################################
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Crédits
# -------
#   • Interface : PyQt6 / conventions VeraLux

"""
SirilJ Séquence — deux outils sur la séquence courante de Siril,
sans équivalent natif dans Siril :

  Onglet Montage (ImageJ « Make Montage »)
  ----------------------------------------
  Assemble les frames d'une séquence en une planche-contact (grille).
  Idéal pour une rotation planétaire, un time-lapse, un aperçu de
  séquence. Colonnes, échelle, bordures et numéros réglables.
  La planche peut être enregistrée et chargée dans Siril.

  Onglet Blink / Animation (ImageJ « Animation » + différence d'images)
  ---------------------------------------------------------------------
  Fait défiler les frames pour repérer les objets mobiles
  (astéroïdes, novæ) : lecture/pause, vitesse, image par image, et
  modes de différence (avec une frame de référence ou la précédente).

Compatibilité
-------------
• Siril 1.3+
• Python 3.10+ (via sirilpy)
• Dépendances : numpy, astropy, PyQt6
"""

import sys
import os
import re
import math

try:
    import sirilpy as s
except ImportError:
    print("Erreur : module sirilpy introuvable.")
    sys.exit(1)

s.ensure_installed("numpy", "astropy", "PyQt6")

import numpy as np
from pathlib import Path
from typing import Optional
from collections import OrderedDict

from astropy.io import fits

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox,
    QSpinBox, QDoubleSpinBox, QSlider, QProgressBar, QTextEdit, QFileDialog,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGroupBox,
    QTabWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings, QTimer
from PyQt6.QtGui import QImage, QPixmap, QPainter

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
QSlider::groove:horizontal { height:4px; background:#555; border-radius:2px; }
QSlider::handle:horizontal { width:12px; background:#aaa; border-radius:6px;
                              margin:-5px 0; }
QLabel#SeqOK { color:#7ec77e; font-weight:bold; }
QLabel#SeqKO { color:#d77; font-weight:bold; }
QScrollBar:vertical   { background:#2b2b2b; width:10px; }
QScrollBar::handle:vertical { background:#555; border-radius:5px; }
"""

# ── FITS / sequence helpers ─────────────────────────────────────────────────────
FITS_EXT = {".fit", ".fits", ".fts"}

def natural_key(name: str):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", name)]

def to_lum(data: np.ndarray) -> np.ndarray:
    return data if data.ndim == 2 else data.mean(axis=0)

def load_lum(path: str) -> np.ndarray:
    """Charge un FITS → luminance 2-D float32 aux valeurs d'origine."""
    with fits.open(path) as hdul:
        data = hdul[0].data.astype(np.float32)
    return to_lum(data)

def norm01(a: np.ndarray) -> np.ndarray:
    mn, mx = float(a.min()), float(a.max())
    return (a - mn) / (mx - mn) if mx > mn else np.zeros_like(a)

def _mtf(x, m, lo, hi):
    dist = hi - lo
    if dist < 1e-9:
        return np.where(x > lo, 1.0, 0.0).astype(np.float32)
    xp = np.clip((x - lo) / dist, 0.0, 1.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        y = ((m - 1.0) * xp) / ((2.0 * m - 1.0) * xp - m)
    return np.nan_to_num(y, nan=0.0, posinf=1.0, neginf=0.0).astype(np.float32)

def autostretch_lum(lum: np.ndarray) -> np.ndarray:
    """Autostretch d'une luminance 2-D → [0,1]."""
    MAD_NORM = 1.4826; SC = -2.8; TBG = 0.25
    x = norm01(lum)
    stride = max(1, x.size // 500_000)
    samp = x.flatten()[::stride]
    med = float(np.median(samp))
    mad = float(np.median(np.abs(samp - med))) * MAD_NORM or 0.001
    c0  = max(0.0, med + SC * mad)
    mt  = float(_mtf(np.float32(med - c0), TBG, 0.0, 1.0))
    return np.clip(_mtf(x, mt, c0, 1.0), 0.0, 1.0)

def downsample(a: np.ndarray, factor: int) -> np.ndarray:
    """Réduction par moyenne de blocs (sans dépendance externe)."""
    if factor <= 1:
        return a
    H, W = a.shape
    H2, W2 = H // factor, W // factor
    if H2 == 0 or W2 == 0:
        return a
    a = a[:H2*factor, :W2*factor]
    return a.reshape(H2, factor, W2, factor).mean(axis=(1, 3))

def lum_to_pixmap(lum01: np.ndarray) -> QPixmap:
    """Luminance [0,1] (orientation FITS) → QPixmap (affichage, Y vers le haut)."""
    disp = np.ascontiguousarray(np.flipud((np.clip(lum01, 0, 1) * 255).astype(np.uint8)))
    h, w = disp.shape
    img = QImage(disp.tobytes(), w, h, w, QImage.Format.Format_Grayscale8)
    return QPixmap.fromImage(img)

def get_siril_sequence(siril) -> Optional[dict]:
    try:
        seq = siril.get_seq()
    except Exception:
        return None
    if seq is None:
        return None
    seqname = getattr(seq, "seqname", None)
    if not seqname:
        return None
    wd = os.getcwd()
    try:
        cands = [f for f in Path(wd).iterdir()
                 if f.is_file() and f.suffix.lower() in FITS_EXT
                 and f.stem.startswith(seqname)]
    except Exception:
        cands = []
    cands.sort(key=lambda p: natural_key(p.name))
    files = [str(p) for p in cands]
    number = int(getattr(seq, "number", len(files)) or 0)
    single_file = number > 1 and len(files) <= 1
    return {"seqname": seqname, "work_dir": wd, "files": files,
            "n_total": number, "single_file": single_file}

def save_fits(data01: np.ndarray, path: str):
    out = np.clip(data01, 0, 1).astype(np.float32)
    fits.PrimaryHDU(out).writeto(path, overwrite=True)


# ── Montage worker ──────────────────────────────────────────────────────────────
class MontageWorker(QThread):
    progress = pyqtSignal(int, str)
    done     = pyqtSignal(object)   # montage float32 [0,1]
    error    = pyqtSignal(str)

    def __init__(self, params, parent=None):
        super().__init__(parent)
        self.p = params
        self._abort = False

    def abort(self): self._abort = True

    def run(self):
        try:
            files  = self.p["files"]
            idxs   = self.p["indices"]
            factor = self.p["factor"]
            cols   = self.p["cols"]
            border = self.p["border"]
            bval   = self.p["border_val"]
            per_frame_stretch = self.p["per_frame"]

            n = len(idxs)
            if n == 0:
                self.error.emit("Aucune frame sélectionnée.")
                return
            cols = max(1, cols)
            rows = math.ceil(n / cols)

            # Dimension d'une cellule (depuis la 1re frame)
            first = downsample(load_lum(files[idxs[0]]), factor)
            ch, cw = first.shape
            Hm = rows * ch + (rows + 1) * border
            Wm = cols * cw + (cols + 1) * border
            montage = np.full((Hm, Wm), float(bval), dtype=np.float32)

            for k, fi in enumerate(idxs):
                if self._abort:
                    break
                lum = downsample(load_lum(files[fi]), factor)
                cell = autostretch_lum(lum) if per_frame_stretch else norm01(lum)
                # Recadre/complète si tailles légèrement différentes
                cell = cell[:ch, :cw]
                ph, pw = cell.shape
                r, c = divmod(k, cols)
                y0 = border + r * (ch + border)
                x0 = border + c * (cw + border)
                montage[y0:y0+ph, x0:x0+pw] = cell
                self.progress.emit(int(100*(k+1)/n),
                                   f"{k+1}/{n}  —  {Path(files[fi]).name}")

            if not per_frame_stretch:
                montage = autostretch_lum(montage)
            self.done.emit(montage)
        except Exception as e:
            self.error.emit(str(e))


# ── Frame cache for blink ────────────────────────────────────────────────────────
class FrameCache:
    """Cache LRU des luminances brutes (valeurs d'origine)."""
    def __init__(self, files, maxlen=40):
        self.files = files
        self.maxlen = maxlen
        self._d = OrderedDict()

    def get(self, i: int) -> np.ndarray:
        if i in self._d:
            self._d.move_to_end(i)
            return self._d[i]
        lum = load_lum(self.files[i])
        self._d[i] = lum
        if len(self._d) > self.maxlen:
            self._d.popitem(last=False)
        return lum


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


# ── Main window ───────────────────────────────────────────────────────────────
class SequenceWindow(QMainWindow):

    def __init__(self, siril):
        super().__init__()
        self.siril = siril
        self.setWindowTitle(f"SirilJ Séquence — v{VERSION}")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet(DARK_SS)

        self.seq_info: Optional[dict] = None
        self._mworker: Optional[MontageWorker] = None
        self._montage: Optional[np.ndarray] = None
        # Items graphiques — initialisés ici car currentChanged se déclenche
        # dès le 1er addTab(), avant la fin de construction des onglets.
        self._mpix = None
        self._bpix = None

        # Blink state
        self._cache: Optional[FrameCache] = None
        self._cur = 0
        self._ref_lum: Optional[np.ndarray] = None
        self._ref_idx = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._blink_next)

        self._build_ui()
        self._refresh_sequence()

    # =========================================================================
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        v = QVBoxLayout(central)
        v.setContentsMargins(6, 6, 6, 4)
        v.setSpacing(4)

        top = QHBoxLayout()
        self.lbl_seq = QLabel("—")
        self.lbl_seq.setObjectName("SeqKO")
        self.lbl_seq.setWordWrap(True)
        top.addWidget(self.lbl_seq, stretch=1)
        btn_refresh = QPushButton("⟳ Rafraîchir")
        btn_refresh.clicked.connect(self._refresh_sequence)
        top.addWidget(btn_refresh)
        v.addLayout(top)

        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self._on_tab_changed)
        v.addWidget(self.tabs)
        self._build_tab_montage()
        self._build_tab_blink()
        self.statusBar().showMessage("Prêt.")

    # ── Onglet Montage ──────────────────────────────────────────────────────────
    def _build_tab_montage(self):
        tab = QWidget()
        self.tabs.addTab(tab, "▦  Montage")
        h = QHBoxLayout(tab); h.setSpacing(8)

        left = QWidget(); left.setFixedWidth(230)
        lv = QVBoxLayout(left); lv.setContentsMargins(0,0,0,0); lv.setSpacing(6)

        grp = QGroupBox("Frames")
        g = QGridLayout(grp)
        g.addWidget(QLabel("Début :"), 0, 0)
        self.spn_start = QSpinBox(); self.spn_start.setRange(0, 0)
        g.addWidget(self.spn_start, 0, 1)
        g.addWidget(QLabel("Fin :"), 1, 0)
        self.spn_end = QSpinBox(); self.spn_end.setRange(0, 0)
        g.addWidget(self.spn_end, 1, 1)
        g.addWidget(QLabel("Pas :"), 2, 0)
        self.spn_step = QSpinBox(); self.spn_step.setRange(1, 999); self.spn_step.setValue(1)
        g.addWidget(self.spn_step, 2, 1)
        lv.addWidget(grp)

        grp2 = QGroupBox("Disposition")
        g2 = QGridLayout(grp2)
        g2.addWidget(QLabel("Colonnes :"), 0, 0)
        self.spn_cols = QSpinBox(); self.spn_cols.setRange(1, 100); self.spn_cols.setValue(5)
        g2.addWidget(self.spn_cols, 0, 1)
        g2.addWidget(QLabel("Échelle :"), 1, 0)
        self.cmb_scale = QComboBox()
        self.cmb_scale.addItems(["1/1", "1/2", "1/4", "1/8", "1/16"])
        self.cmb_scale.setCurrentIndex(2)
        g2.addWidget(self.cmb_scale, 1, 1)
        g2.addWidget(QLabel("Bordure (px) :"), 2, 0)
        self.spn_border = QSpinBox(); self.spn_border.setRange(0, 100); self.spn_border.setValue(2)
        g2.addWidget(self.spn_border, 2, 1)
        g2.addWidget(QLabel("Bordure :"), 3, 0)
        self.cmb_bcol = QComboBox(); self.cmb_bcol.addItems(["Noir", "Blanc", "Gris"])
        g2.addWidget(self.cmb_bcol, 3, 1)
        self.chk_perframe = QCheckBox("Étirement par frame")
        self.chk_perframe.setChecked(True)
        g2.addWidget(self.chk_perframe, 4, 0, 1, 2)
        lv.addWidget(grp2)

        lv.addStretch()
        self.btn_build = QPushButton("▶  Construire le montage")
        self.btn_build.setObjectName("BtnGo")
        self.btn_build.clicked.connect(self._build_montage)
        lv.addWidget(self.btn_build)
        self.btn_save = QPushButton("Enregistrer + charger dans Siril")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self._save_montage)
        lv.addWidget(self.btn_save)
        h.addWidget(left)

        right = QWidget()
        rv = QVBoxLayout(right); rv.setContentsMargins(0,0,0,0); rv.setSpacing(4)
        self._mscene = QGraphicsScene()
        self._mview = ZoomView(self._mscene)
        self._mpix = None
        rv.addWidget(self._mview, stretch=1)
        self.prog = QProgressBar()
        rv.addWidget(self.prog)
        h.addWidget(right, stretch=1)

    # ── Onglet Blink ──────────────────────────────────────────────────────────
    def _build_tab_blink(self):
        tab = QWidget()
        self.tabs.addTab(tab, "▶  Blink / Animation")
        v = QVBoxLayout(tab); v.setSpacing(6)

        self._bscene = QGraphicsScene()
        self._bview = ZoomView(self._bscene)
        self._bpix = None
        v.addWidget(self._bview, stretch=1)

        # Frame slider + label
        row1 = QHBoxLayout()
        self.lbl_frame = QLabel("— / —")
        self.lbl_frame.setFixedWidth(110)
        row1.addWidget(self.lbl_frame)
        self.sld_frame = QSlider(Qt.Orientation.Horizontal)
        self.sld_frame.setRange(0, 0)
        self.sld_frame.valueChanged.connect(self._on_slider)
        row1.addWidget(self.sld_frame, stretch=1)
        v.addLayout(row1)

        # Transport controls
        row2 = QHBoxLayout()
        self.btn_prev = QPushButton("◀")
        self.btn_prev.setFixedWidth(40)
        self.btn_prev.clicked.connect(lambda: self._step(-1))
        self.btn_play = QPushButton("▶ Lecture")
        self.btn_play.setCheckable(True)
        self.btn_play.toggled.connect(self._toggle_play)
        self.btn_next = QPushButton("▶")
        self.btn_next.setFixedWidth(40)
        self.btn_next.clicked.connect(lambda: self._step(1))
        row2.addWidget(self.btn_prev)
        row2.addWidget(self.btn_play)
        row2.addWidget(self.btn_next)
        row2.addSpacing(16)
        row2.addWidget(QLabel("Vitesse :"))
        self.sld_fps = QSlider(Qt.Orientation.Horizontal)
        self.sld_fps.setRange(1, 30); self.sld_fps.setValue(8)
        self.sld_fps.setFixedWidth(120)
        self.sld_fps.valueChanged.connect(self._on_fps)
        row2.addWidget(self.sld_fps)
        self.lbl_fps = QLabel("8 fps")
        row2.addWidget(self.lbl_fps)
        row2.addStretch()
        v.addLayout(row2)

        # Mode
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Mode :"))
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItems(["Normal", "Différence avec réf.", "Différence avec précédente"])
        self.cmb_mode.currentIndexChanged.connect(self._on_mode)
        row3.addWidget(self.cmb_mode)
        self.btn_setref = QPushButton("Définir la frame courante comme réf.")
        self.btn_setref.clicked.connect(self._set_ref)
        row3.addWidget(self.btn_setref)
        self.lbl_ref = QLabel("réf. : 0")
        row3.addWidget(self.lbl_ref)
        row3.addStretch()
        v.addLayout(row3)

    # =========================================================================
    #  Sequence detection
    # =========================================================================
    def _refresh_sequence(self):
        info = get_siril_sequence(self.siril)
        if info and info.get("single_file"):
            self.seq_info = None
            self.lbl_seq.setObjectName("SeqKO")
            self.lbl_seq.setText(f"⚠ {info['seqname']} — séquence mono-fichier "
                                 "(FITSEQ/SER). Exporter en FITS individuels.")
            self._set_enabled(False)
        elif not info or not info["files"]:
            self.seq_info = None
            self.lbl_seq.setObjectName("SeqKO")
            self.lbl_seq.setText("Aucune séquence chargée — charger dans Siril puis ⟳.")
            self._set_enabled(False)
        else:
            self.seq_info = info
            n = len(info["files"])
            self.lbl_seq.setObjectName("SeqOK")
            self.lbl_seq.setText(f"✓ {info['seqname']}  —  {n} frames  —  📂 {info['work_dir']}")
            self.spn_start.setRange(0, n-1); self.spn_start.setValue(0)
            self.spn_end.setRange(0, n-1);   self.spn_end.setValue(n-1)
            self.sld_frame.setRange(0, n-1)
            self._cache = FrameCache(info["files"])
            self._cur = 0
            self._ref_idx = 0
            self._ref_lum = None
            self._set_enabled(True)
            self._show_frame(0)
        self.lbl_seq.style().unpolish(self.lbl_seq)
        self.lbl_seq.style().polish(self.lbl_seq)

    def _set_enabled(self, on: bool):
        for w in (self.btn_build, self.btn_play, self.btn_prev, self.btn_next,
                  self.sld_frame, self.btn_setref):
            w.setEnabled(on)
        if not on:
            self.btn_save.setEnabled(False)

    def _on_tab_changed(self, idx: int):
        if idx == 1 and self._bpix is not None:
            self._bview.fitInView(self._bscene.sceneRect(),
                                  Qt.AspectRatioMode.KeepAspectRatio)
        if idx == 0 and self._mpix is not None:
            self._mview.fitInView(self._mscene.sceneRect(),
                                  Qt.AspectRatioMode.KeepAspectRatio)

    # =========================================================================
    #  Montage
    # =========================================================================
    def _build_montage(self):
        if not self.seq_info:
            return
        n = len(self.seq_info["files"])
        start = self.spn_start.value()
        end   = self.spn_end.value()
        step  = self.spn_step.value()
        if end < start:
            self.statusBar().showMessage("⚠ Fin < Début.")
            return
        idxs = list(range(start, min(end, n-1) + 1, step))
        factor = [1, 2, 4, 8, 16][self.cmb_scale.currentIndex()]
        bval = {"Noir": 0.0, "Blanc": 1.0, "Gris": 0.5}[self.cmb_bcol.currentText()]

        params = {
            "files":      self.seq_info["files"],
            "indices":    idxs,
            "factor":     factor,
            "cols":       self.spn_cols.value(),
            "border":     self.spn_border.value(),
            "border_val": bval,
            "per_frame":  self.chk_perframe.isChecked(),
        }
        self.btn_build.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.prog.setValue(0)
        self.statusBar().showMessage(f"Construction du montage ({len(idxs)} frames)…")
        self._mworker = MontageWorker(params)
        self._mworker.progress.connect(lambda p, m: (self.prog.setValue(p),
                                                     self.statusBar().showMessage(m)))
        self._mworker.done.connect(self._on_montage)
        self._mworker.error.connect(lambda e: (self.statusBar().showMessage(f"✗ {e}"),
                                               self.btn_build.setEnabled(True)))
        self._mworker.start()

    def _on_montage(self, montage):
        self._montage = montage
        pm = lum_to_pixmap(montage)
        if self._mpix is None:
            self._mpix = self._mscene.addPixmap(pm)
        else:
            self._mpix.setPixmap(pm)
        self._mscene.setSceneRect(0, 0, pm.width(), pm.height())
        QTimer.singleShot(50, lambda: self._mview.fitInView(
            self._mscene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio))
        self.prog.setValue(100)
        self.btn_build.setEnabled(True)
        self.btn_save.setEnabled(True)
        self.statusBar().showMessage(f"✓ Montage {pm.width()}×{pm.height()} px.")

    def _save_montage(self):
        if self._montage is None:
            return
        base = self.seq_info["seqname"] if self.seq_info else "montage"
        # Répertoire de travail de Siril (os.getcwd()) par défaut.
        default = str(Path(os.getcwd()) / f"{base}_montage.fit")
        f, _ = QFileDialog.getSaveFileName(self, "Enregistrer le montage", default,
                                           "FITS (*.fit *.fits)")
        if not f:
            return
        try:
            save_fits(self._montage, f)
            self.statusBar().showMessage(f"✓ Enregistré : {f}")
            # Charge dans Siril (sans extension)
            stem = str(Path(f).with_suffix(""))
            try:
                self.siril.cmd(f'load "{stem}"')   # guillemets : chemins avec espaces
                self.siril.log(f"SirilJ Séquence — montage chargé : {Path(f).name}")
            except Exception:
                self.statusBar().showMessage(f"✓ Enregistré : {f} (chargez-le manuellement)")
        except Exception as e:
            self.statusBar().showMessage(f"✗ {e}")

    # =========================================================================
    #  Blink
    # =========================================================================
    def _display_lum(self, i: int) -> np.ndarray:
        """Luminance d'affichage [0,1] selon le mode courant."""
        cur = self._cache.get(i)
        mode = self.cmb_mode.currentIndex()
        if mode == 0:                       # Normal
            return autostretch_lum(cur)
        if mode == 1:                       # Diff. avec réf.
            if self._ref_lum is None:
                self._ref_lum = self._cache.get(self._ref_idx)
            diff = cur - self._ref_lum
        else:                               # Diff. avec précédente
            j = max(0, i - 1)
            diff = cur - self._cache.get(j)
        # Map signé → [0,1] centré sur 0.5 (robuste)
        span = float(np.percentile(np.abs(diff), 99)) or 1e-6
        return np.clip(0.5 + diff / (2.0 * span), 0.0, 1.0)

    def _show_frame(self, i: int):
        if not self.seq_info or self._cache is None:
            return
        n = len(self.seq_info["files"])
        i = max(0, min(i, n - 1))
        self._cur = i
        try:
            lum01 = self._display_lum(i)
        except Exception as e:
            self.statusBar().showMessage(f"✗ {e}")
            return
        pm = lum_to_pixmap(lum01)
        first = self._bpix is None
        if first:
            self._bpix = self._bscene.addPixmap(pm)
        else:
            self._bpix.setPixmap(pm)
        self._bscene.setSceneRect(0, 0, pm.width(), pm.height())
        if first:
            QTimer.singleShot(50, lambda: self._bview.fitInView(
                self._bscene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio))
        self.lbl_frame.setText(f"{i+1} / {n}")
        if self.sld_frame.value() != i:
            self.sld_frame.blockSignals(True)
            self.sld_frame.setValue(i)
            self.sld_frame.blockSignals(False)

    def _on_slider(self, val: int):
        self._show_frame(val)

    def _step(self, d: int):
        if not self.seq_info:
            return
        n = len(self.seq_info["files"])
        self._show_frame((self._cur + d) % n)

    def _blink_next(self):
        self._step(1)

    def _toggle_play(self, on: bool):
        if on and self.seq_info:
            self.btn_play.setText("⏸ Pause")
            self._timer.start(int(1000 / self.sld_fps.value()))
        else:
            self.btn_play.setText("▶ Lecture")
            self._timer.stop()

    def _on_fps(self, val: int):
        self.lbl_fps.setText(f"{val} fps")
        if self._timer.isActive():
            self._timer.start(int(1000 / val))

    def _on_mode(self, idx: int):
        self.btn_setref.setEnabled(idx == 1)
        self._show_frame(self._cur)

    def _set_ref(self):
        self._ref_idx = self._cur
        self._ref_lum = None    # rechargé à la demande
        self.lbl_ref.setText(f"réf. : {self._ref_idx + 1}")
        if self.cmb_mode.currentIndex() == 1:
            self._show_frame(self._cur)

    # =========================================================================
    def closeEvent(self, event):
        self._timer.stop()
        if self._mworker and self._mworker.isRunning():
            self._mworker.abort()
            self._mworker.wait(3000)
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
    win = SequenceWindow(siril)
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
