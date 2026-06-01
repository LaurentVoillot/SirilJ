##############################################
# SirilJ — Solar Align
# Alignement de la séquence courante de Siril
# Version 2.0.0
##############################################
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Crédits
# -------
#   • StackReg : pystackreg (P. Thévenaz, EPFL 1998)
#   • ECC      : OpenCV (cv2.findTransformECC)
#   • Interface : PyQt6 / conventions VeraLux

"""
SirilJ SolarAlign — alignement de la séquence courante de Siril.

  • Détection automatique de la séquence chargée dans Siril
  • Sélection ou détection de l'image de référence (meilleure netteté)
  • Algorithme StackReg ou ECC OpenCV
  • Création optionnelle d'une nouvelle séquence Siril à partir
    des fichiers alignés (commande `convert`)
  • Empilement optionnel (commande `stack`)
  • Chargement automatique du résultat dans Siril

Compatibilité
-------------
• Siril 1.3+
• Python 3.10+ (via sirilpy)
• Dépendances : pystackreg, opencv-python, numpy, astropy, PyQt6
"""

import sys
import os
import re

try:
    import sirilpy as s
except ImportError:
    print("Erreur : module sirilpy introuvable.")
    sys.exit(1)

s.ensure_installed("numpy", "astropy", "pystackreg", "opencv-python", "PyQt6")

import numpy as np
from pathlib import Path
from typing import Optional

from astropy.io import fits

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox,
    QSpinBox, QDoubleSpinBox, QProgressBar, QTextEdit,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings, QTimer
from PyQt6.QtGui import QImage, QPixmap, QPainter

VERSION = "2.0.0"

# ── Dark stylesheet ───────────────────────────────────────────────────────────
DARK_SS = """
QWidget            { background:#2b2b2b; color:#d4d4d4; font-size:11px; }
QMainWindow        { background:#2b2b2b; }
QPushButton        { background:#3c3c3c; color:#d4d4d4; border:1px solid #555;
                     border-radius:4px; padding:4px 10px; }
QPushButton:hover  { background:#4a4a4a; }
QPushButton:pressed{ background:#555; }
QPushButton:disabled { color:#666; border-color:#444; }
QPushButton#BtnStart { background:#1e6b1e; color:#fff; font-weight:bold;
                       font-size:12px; border:1px solid #2a9b2a; padding:6px 12px; }
QPushButton#BtnStart:hover    { background:#248c24; }
QPushButton#BtnStart:disabled { background:#333; color:#666; border-color:#444; }
QPushButton#BtnPrep  { background:#1e3d6b; color:#fff; border:1px solid #2a60a0;
                       padding:4px 10px; }
QPushButton#BtnPrep:hover    { background:#255080; }
QPushButton#BtnPrep:disabled { background:#333; color:#666; border-color:#444; }
QLineEdit          { background:#1e1e1e; border:1px solid #555; border-radius:3px;
                     padding:3px 6px; color:#d4d4d4; }
QComboBox          { background:#3c3c3c; border:1px solid #555; border-radius:3px;
                     padding:3px 6px; color:#d4d4d4; }
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
QScrollBar:vertical   { background:#2b2b2b; width:10px; }
QScrollBar::handle:vertical { background:#555; border-radius:5px; }
QScrollBar:horizontal { background:#2b2b2b; height:10px; }
QScrollBar::handle:horizontal { background:#555; border-radius:5px; }
QLabel#SeqInfoOK   { color:#7ec77e; font-weight:bold; }
QLabel#SeqInfoKO   { color:#d77; font-weight:bold; }
QFrame#HSep        { background:#444; max-height:1px; }
"""

# ── FITS helpers ──────────────────────────────────────────────────────────────
FITS_EXT = {".fit", ".fits", ".fts"}

def natural_key(name: str):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", name)]

def load_frame(path: str) -> tuple[np.ndarray, fits.Header]:
    """Load FITS → float32 aux valeurs d'origine (NON normalisées).

    On conserve l'échelle d'origine : la normalisation par frame
    (min/max) fausserait l'empilement (un seul pixel chaud change
    l'échelle d'une frame). La normalisation n'est appliquée que pour
    l'enregistrement (reg_lum) et l'affichage (autostretch).
    """
    with fits.open(path) as hdul:
        hdr  = hdul[0].header
        data = hdul[0].data.astype(np.float32)
    return data, hdr

def to_lum(data: np.ndarray) -> np.ndarray:
    return data if data.ndim == 2 else data.mean(axis=0)

def reg_lum(data: np.ndarray) -> np.ndarray:
    """Luminance normalisée [0,1] utilisée pour l'enregistrement."""
    lum = to_lum(data).astype(np.float32)
    mn, mx = float(lum.min()), float(lum.max())
    if mx > mn:
        return (lum - mn) / (mx - mn)
    return lum

def estimate_sharpness(lum: np.ndarray) -> float:
    return float(np.var(np.diff(lum, axis=0)) + np.var(np.diff(lum, axis=1)))

def save_frame(data: np.ndarray, hdr: fits.Header, path: str):
    """Sauvegarde en FITS float32 (BITPIX=-32), échelle d'origine préservée.

    float32 évite tout conflit BZERO/BSCALE (astropy applique déjà
    l'échelle à la lecture mais laisse les mots-clés dans le header).
    """
    out = np.asarray(data, dtype=np.float32)
    hdr_out = hdr.copy()
    for kw in ("BZERO", "BSCALE", "BLANK", "DATAMAX", "DATAMIN"):
        hdr_out.remove(kw, ignore_missing=True)
    fits.PrimaryHDU(out, header=hdr_out).writeto(path, overwrite=True)

# ── Display helpers ───────────────────────────────────────────────────────────
def _mtf(x: np.ndarray, m: float = 0.25) -> np.ndarray:
    m = max(m, 1e-6)
    den = (2*m - 1)*x - m
    return np.where(den == 0, 0.0, np.clip((m - 1)*x / den, 0, 1))

def autostretch(data: np.ndarray) -> np.ndarray:
    """Autostretch d'affichage → 2-D float32 [0,1] (normalise en interne)."""
    lum    = reg_lum(data)   # ramène l'échelle à [0,1] quel que soit le BITPIX
    med    = float(np.median(lum))
    mad    = float(np.median(np.abs(lum - med))) * 1.4826
    bg     = max(0.0, min(med - 2.8 * mad, 1.0))
    denom  = 1 - bg + 1e-9
    # IMPORTANT : borner l'entrée à [0,1]. Sans ce clip, les pixels plus
    # sombres que le fond (x<0) ressortent en blanc → image en négatif.
    x      = np.clip((lum - bg) / denom, 0.0, 1.0)
    return np.clip(_mtf(x), 0, 1).astype(np.float32)

def to_qpixmap(arr: np.ndarray) -> QPixmap:
    # FITS : ligne 0 = bas. On retourne verticalement pour afficher Y vers le
    # haut, comme Siril (et comme SirilJ Mesures / Séquence).
    gray = np.ascontiguousarray((np.clip(np.flipud(arr), 0, 1) * 255).astype(np.uint8))
    h, w = gray.shape
    img  = QImage(gray.tobytes(), w, h, w, QImage.Format.Format_Grayscale8)
    return QPixmap.fromImage(img)

# ── StackReg ──────────────────────────────────────────────────────────────────
SR_MODELS = ["Translation", "Corps rigide", "Rotation/Échelle", "Affine", "Bilinéaire"]

def _sr_const(name: str):
    from pystackreg import StackReg as SR
    return {
        "Translation":      SR.TRANSLATION,
        "Corps rigide":     SR.RIGID_BODY,
        "Rotation/Échelle": SR.SCALED_ROTATION,
        "Affine":           SR.AFFINE,
        "Bilinéaire":       SR.BILINEAR,
    }.get(name, SR.RIGID_BODY)

def _apply_tmat(data: np.ndarray, tmat: np.ndarray, sr) -> np.ndarray:
    if data.ndim == 2:
        return sr.transform(data, tmat).astype(np.float32)
    return np.stack([sr.transform(data[c], tmat).astype(np.float32)
                     for c in range(data.shape[0])])

# ── ECC (OpenCV) ──────────────────────────────────────────────────────────────
ECC_MODELS = ["Translation", "Euclidien", "Affine", "Homographie"]

def _ecc_motion(name: str):
    import cv2
    return {
        "Translation":  cv2.MOTION_TRANSLATION,
        "Euclidien":    cv2.MOTION_EUCLIDEAN,
        "Affine":       cv2.MOTION_AFFINE,
        "Homographie":  cv2.MOTION_HOMOGRAPHY,
    }.get(name, cv2.MOTION_EUCLIDEAN)

def _warp_frame(data: np.ndarray, warp: np.ndarray, motion, h: int, w: int) -> np.ndarray:
    import cv2
    flags = cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP
    if motion == cv2.MOTION_HOMOGRAPHY:
        fn = lambda ch: cv2.warpPerspective(ch, warp, (w, h), flags=flags)
    else:
        fn = lambda ch: cv2.warpAffine(ch, warp, (w, h), flags=flags)
    if data.ndim == 2:
        return fn(data).astype(np.float32)
    return np.stack([fn(data[c]).astype(np.float32) for c in range(data.shape[0])])

# ── Siril sequence helpers ────────────────────────────────────────────────────
def get_siril_sequence(siril) -> Optional[dict]:
    """Détecte la séquence courante de Siril.

    Retourne un dict {seqname, work_dir, files, n_total, nb_layers}
    ou None si aucune séquence n'est chargée.
    """
    try:
        seq = siril.get_seq()
    except Exception:
        return None
    if seq is None:
        return None

    seqname = getattr(seq, "seqname", None)
    if not seqname:
        return None

    # Siril fait du dossier courant celui de la séquence
    wd = os.getcwd()

    # Cherche les fichiers FITS qui commencent par seqname dans le wd
    try:
        candidates = [
            f for f in Path(wd).iterdir()
            if f.is_file() and f.suffix.lower() in FITS_EXT
            and f.stem.startswith(seqname)
        ]
    except Exception:
        candidates = []

    candidates.sort(key=lambda p: natural_key(p.name))
    files = [str(p) for p in candidates]

    number = int(getattr(seq, "number", len(files)) or 0)
    # Séquence mono-fichier (FITSEQ .fits multi-HDU ou SER) : Siril annonce
    # N frames mais il n'y a pas N fichiers individuels sur le disque.
    single_file = number > 1 and len(files) <= 1

    return {
        "seqname":     seqname,
        "work_dir":    wd,
        "files":       files,
        "n_total":     number,
        "nb_layers":   int(getattr(seq, "nb_layers", 1) or 1),
        "single_file": single_file,
    }

def siril_safe_cmd(siril, *args) -> bool:
    """Exécute une commande Siril, retourne True si OK."""
    try:
        siril.cmd(*args)
        return True
    except Exception:
        return False

def siril_safe_log(siril, msg: str, color=None):
    try:
        if color is not None:
            siril.log(msg, color=color)
        else:
            siril.log(msg)
    except Exception:
        pass

# ── Workers ───────────────────────────────────────────────────────────────────
class RefLoadWorker(QThread):
    progress = pyqtSignal(int, str)
    done     = pyqtSignal(object, object, int)   # lum, stretched, idx
    error    = pyqtSignal(str)

    def __init__(self, files: list[str], mode: str, manual_idx: int, parent=None):
        super().__init__(parent)
        self.files      = files
        self.mode       = mode
        self.manual_idx = manual_idx
        self._abort     = False

    def abort(self): self._abort = True

    def run(self):
        files = self.files
        if not files:
            self.error.emit("Aucun fichier dans la séquence.")
            return
        n = len(files)

        if self.mode == "first":
            idx = 0
        elif self.mode == "last":
            idx = n - 1
        elif self.mode == "manual":
            idx = max(0, min(self.manual_idx, n - 1))
        else:   # auto — meilleure netteté
            best, best_idx = -1.0, 0
            for i, path in enumerate(files):
                if self._abort: return
                try:
                    data, _ = load_frame(path)
                    score   = estimate_sharpness(to_lum(data))
                    if score > best:
                        best, best_idx = score, i
                except Exception:
                    pass
                self.progress.emit(int(100*(i+1)/n),
                                   f"Analyse {i+1}/{n}  —  {Path(path).name}")
            idx = best_idx

        path = files[idx]
        self.progress.emit(99, f"Chargement référence : {Path(path).name}")
        try:
            data, _ = load_frame(path)
            # reg_lum : luminance normalisée pour l'enregistrement ;
            # autostretch : aperçu d'affichage.
            self.done.emit(reg_lum(data), autostretch(data), idx)
        except Exception as e:
            self.error.emit(f"Erreur chargement : {e}")


class AlignWorker(QThread):
    progress = pyqtSignal(int, str)
    done     = pyqtSignal(int, int, str, bool)   # n_ok, n_total, out_dir, aborted
    error    = pyqtSignal(str)

    def __init__(self, params: dict, parent=None):
        super().__init__(parent)
        self.params = params
        self._abort = False

    def abort(self): self._abort = True

    def _prepare_out_dir(self, out_folder: str, base: str) -> bool:
        """Crée le sous-dossier isolé et purge nos sorties d'un run précédent.

        Sinon `convert` ré-intégrerait les frames alignées, le fitseq et
        l'empilement précédents. On ne supprime QUE nos propres fichiers
        (préfixés par `base`), jamais des données arbitraires.
        """
        try:
            d = Path(out_folder)
            d.mkdir(parents=True, exist_ok=True)
            patterns = (f"{base}_*.fit*", f"{base}.fit*", f"{base}.seq")
            for pat in patterns:
                for old in d.glob(pat):
                    try: old.unlink()
                    except Exception: pass
            return True
        except Exception as e:
            self.error.emit(f"Création dossier sortie impossible : {e}")
            return False

    def run(self):
        p          = self.params
        files      = p["files"]
        out_folder = p["out_folder"]     # sous-dossier ISOLÉ (frames alignées seules)
        base       = p["base"]           # nom de base des frames / de la séquence
        ref_lum    = p["ref_lum"]        # luminance normalisée [0,1]
        algo       = p["algo"]

        n = len(files)
        n_ok = 0
        if not self._prepare_out_dir(out_folder, base):
            return

        def dst_for(i: int) -> str:
            # Numérotation séquentielle → ordre naturel garanti pour `convert`.
            return str(Path(out_folder) / f"{base}_{i+1:05d}.fit")

        if algo == "stackreg":
            from pystackreg import StackReg
            sr = StackReg(_sr_const(p.get("sr_model", "Corps rigide")))
            for i, path in enumerate(files):
                if self._abort: break
                fname = Path(path).name
                try:
                    data, hdr = load_frame(path)
                    tmat      = sr.register(ref_lum, reg_lum(data))
                    aligned   = _apply_tmat(data, tmat, sr)   # sur données brutes
                    save_frame(aligned, hdr, dst_for(i))
                    n_ok += 1
                    self.progress.emit(int(100*(i+1)/n), f"✓ {i+1}/{n}  —  {fname}")
                except Exception as e:
                    self.progress.emit(int(100*(i+1)/n),
                                       f"✗ {i+1}/{n}  —  {fname} : {e}")

        else:   # ECC
            import cv2
            motion   = _ecc_motion(p.get("ecc_model", "Euclidien"))
            n_iter   = int(p.get("ecc_iter", 50))
            eps      = float(p.get("ecc_eps", 1e-4))
            criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, n_iter, eps)
            warp_init = (np.eye(3, 3, dtype=np.float32)
                         if motion == cv2.MOTION_HOMOGRAPHY
                         else np.eye(2, 3, dtype=np.float32))
            ref8 = (np.clip(ref_lum, 0, 1) * 255).astype(np.uint8)
            h, w = ref_lum.shape

            for i, path in enumerate(files):
                if self._abort: break
                fname = Path(path).name
                try:
                    data, hdr = load_frame(path)
                    mov8 = (np.clip(reg_lum(data), 0, 1) * 255).astype(np.uint8)
                    warp = warp_init.copy()
                    _, warp = cv2.findTransformECC(ref8, mov8, warp, motion, criteria)
                    aligned = _warp_frame(data, warp, motion, h, w)   # données brutes
                    save_frame(aligned, hdr, dst_for(i))
                    n_ok += 1
                    self.progress.emit(int(100*(i+1)/n), f"✓ {i+1}/{n}  —  {fname}")
                except Exception as e:
                    self.progress.emit(int(100*(i+1)/n),
                                       f"✗ {i+1}/{n}  —  {fname} : {e}")

        self.done.emit(n_ok, n, out_folder, self._abort)


# ── Zoom view ─────────────────────────────────────────────────────────────────
class ZoomView(QGraphicsView):
    """QGraphicsView avec zoom à la molette et panoramique (clic gauche)."""
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)


# ── Main window ───────────────────────────────────────────────────────────────
class SolarAlignWindow(QMainWindow):

    def __init__(self, siril):
        super().__init__()
        self.siril = siril
        self.setWindowTitle(f"SirilJ Solar Align — v{VERSION}")
        self.setMinimumSize(960, 640)
        self.setStyleSheet(DARK_SS)

        # ── State ─────────────────────────────────────────────────────────────
        self.seq_info:      Optional[dict]       = None
        self.ref_lum:       Optional[np.ndarray] = None
        self.ref_stretched: Optional[np.ndarray] = None
        self.ref_idx:       int                  = 0
        self.ref_fname:     str                  = ""
        self._out_subdir:   str                  = ""
        self._out_base:     str                  = "align"

        self._ref_worker:   Optional[RefLoadWorker] = None
        self._align_worker: Optional[AlignWorker]   = None

        self._build_ui()
        self._restore_settings()
        self._refresh_sequence()

    # =========================================================================
    #  UI
    # =========================================================================
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        hl = QHBoxLayout(central)
        hl.setContentsMargins(6, 6, 6, 6)
        hl.setSpacing(8)

        # ── Panneau gauche ────────────────────────────────────────────────────
        left = QWidget()
        left.setFixedWidth(250)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(6)

        # Séquence Siril
        grp_seq = QGroupBox("Séquence Siril courante")
        sv = QVBoxLayout(grp_seq)
        self.lbl_seq_name = QLabel("—")
        self.lbl_seq_name.setObjectName("SeqInfoKO")
        self.lbl_seq_name.setWordWrap(True)
        self.lbl_seq_info = QLabel("")
        self.lbl_seq_info.setWordWrap(True)
        self.lbl_seq_info.setStyleSheet("color:#999; font-size:10px;")
        sv.addWidget(self.lbl_seq_name)
        sv.addWidget(self.lbl_seq_info)
        btn_refresh = QPushButton("⟳  Rafraîchir")
        btn_refresh.clicked.connect(self._refresh_sequence)
        sv.addWidget(btn_refresh)
        lv.addWidget(grp_seq)

        # Référence
        grp_ref = QGroupBox("Image de référence")
        rg = QGridLayout(grp_ref)
        rg.addWidget(QLabel("Mode :"), 0, 0)
        self.cmb_ref_mode = QComboBox()
        self.cmb_ref_mode.addItems(["Meilleure netteté", "Première", "Dernière", "Manuel"])
        self.cmb_ref_mode.currentIndexChanged.connect(
            lambda i: self.spn_ref_idx.setEnabled(i == 3))
        rg.addWidget(self.cmb_ref_mode, 0, 1)
        rg.addWidget(QLabel("Index :"), 1, 0)
        self.spn_ref_idx = QSpinBox()
        self.spn_ref_idx.setRange(0, 99999)
        self.spn_ref_idx.setEnabled(False)
        rg.addWidget(self.spn_ref_idx, 1, 1)
        lv.addWidget(grp_ref)

        # Algorithme
        grp_algo = QGroupBox("Algorithme")
        ag = QVBoxLayout(grp_algo)
        self.cmb_algo = QComboBox()
        self.cmb_algo.addItems(["StackReg", "ECC (OpenCV)"])
        self.cmb_algo.currentIndexChanged.connect(self._on_algo_changed)
        ag.addWidget(self.cmb_algo)

        self.grp_sr = QGroupBox("Modèle StackReg")
        sg = QVBoxLayout(self.grp_sr)
        self.cmb_sr = QComboBox()
        self.cmb_sr.addItems(SR_MODELS)
        self.cmb_sr.setCurrentIndex(1)
        sg.addWidget(self.cmb_sr)
        ag.addWidget(self.grp_sr)

        self.grp_ecc = QGroupBox("Options ECC")
        eg = QGridLayout(self.grp_ecc)
        eg.addWidget(QLabel("Modèle :"), 0, 0)
        self.cmb_ecc = QComboBox()
        self.cmb_ecc.addItems(ECC_MODELS)
        self.cmb_ecc.setCurrentIndex(1)
        eg.addWidget(self.cmb_ecc, 0, 1)
        eg.addWidget(QLabel("Itérations :"), 1, 0)
        self.spn_iter = QSpinBox()
        self.spn_iter.setRange(5, 2000)
        self.spn_iter.setValue(50)
        eg.addWidget(self.spn_iter, 1, 1)
        eg.addWidget(QLabel("Epsilon :"), 2, 0)
        self.spn_eps = QDoubleSpinBox()
        self.spn_eps.setRange(1e-8, 1e-1)
        self.spn_eps.setValue(1e-4)
        self.spn_eps.setDecimals(8)
        self.spn_eps.setSingleStep(1e-5)
        eg.addWidget(self.spn_eps, 2, 1)
        self.grp_ecc.setVisible(False)
        ag.addWidget(self.grp_ecc)
        lv.addWidget(grp_algo)

        # Sortie + intégration Siril
        grp_out = QGroupBox("Sortie & intégration Siril")
        og = QGridLayout(grp_out)
        og.addWidget(QLabel("Préfixe :"), 0, 0)
        self.ed_prefix = QLineEdit("align_")
        og.addWidget(self.ed_prefix, 0, 1)
        self.chk_convert = QCheckBox("Convertir en séquence Siril")
        self.chk_convert.setChecked(True)
        og.addWidget(self.chk_convert, 1, 0, 1, 2)
        self.chk_stack = QCheckBox("Empiler après alignement")
        self.chk_stack.setChecked(True)
        self.chk_stack.toggled.connect(
            lambda c: c and self.chk_convert.setChecked(True))
        og.addWidget(self.chk_stack, 2, 0, 1, 2)
        og.addWidget(QLabel("Méthode :"), 3, 0)
        self.cmb_stack = QComboBox()
        self.cmb_stack.addItems(["sum", "med", "rej 3 3", "max", "min"])
        self.cmb_stack.setCurrentIndex(0)
        og.addWidget(self.cmb_stack, 3, 1)
        self.chk_load = QCheckBox("Charger le résultat dans Siril")
        self.chk_load.setChecked(True)
        og.addWidget(self.chk_load, 4, 0, 1, 2)
        lv.addWidget(grp_out)

        lv.addStretch()

        # Boutons
        self.btn_prep = QPushButton("Préparer la référence")
        self.btn_prep.setObjectName("BtnPrep")
        self.btn_prep.clicked.connect(self._prepare_ref)
        lv.addWidget(self.btn_prep)

        self.btn_start = QPushButton("▶  Démarrer l'alignement")
        self.btn_start.setObjectName("BtnStart")
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self._start_align)
        lv.addWidget(self.btn_start)

        self.btn_abort = QPushButton("⏹  Arrêter")
        self.btn_abort.setEnabled(False)
        self.btn_abort.clicked.connect(self._abort_all)
        lv.addWidget(self.btn_abort)

        hl.addWidget(left)

        # ── Panneau droit ─────────────────────────────────────────────────────
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(4)

        grp_prev = QGroupBox("Aperçu — Image de référence")
        pv = QVBoxLayout(grp_prev)
        self._scene = QGraphicsScene()
        self._view  = ZoomView(self._scene)
        self._view.setMinimumHeight(340)
        self._pixitem: Optional[QGraphicsPixmapItem] = None
        self.lbl_ref_info = QLabel("Aucune référence chargée.")
        self.lbl_ref_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_ref_info.setStyleSheet("color:#888; font-size:10px;")
        pv.addWidget(self._view)
        pv.addWidget(self.lbl_ref_info)
        rv.addWidget(grp_prev, stretch=3)

        self.prog = QProgressBar()
        rv.addWidget(self.prog)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(120)
        rv.addWidget(self.log)

        hl.addWidget(right, stretch=1)

        self.statusBar().showMessage("Prêt.")

    # =========================================================================
    #  Sequence detection
    # =========================================================================
    def _refresh_sequence(self):
        info = get_siril_sequence(self.siril)
        if info and info.get("single_file"):
            # FITSEQ / SER : Siril annonce N frames mais sans fichiers individuels.
            self.seq_info = None
            self.lbl_seq_name.setObjectName("SeqInfoKO")
            self.lbl_seq_name.setText(f"⚠ {info['seqname']} — séquence mono-fichier")
            self.lbl_seq_info.setText(
                f"FITSEQ/SER détecté ({info['n_total']} frames). Ce script aligne "
                "des FITS individuels.\nExportez la séquence en FITS individuels "
                "(Convert sans -fitseq) puis ⟳ Rafraîchir.")
            self.btn_prep.setEnabled(False)
            self.btn_start.setEnabled(False)
        elif not info or not info["files"]:
            self.seq_info = None
            self.lbl_seq_name.setObjectName("SeqInfoKO")
            self.lbl_seq_name.setText("Aucune séquence chargée")
            self.lbl_seq_info.setText(
                "Chargez une séquence dans Siril (Convert / Open sequence) "
                "puis cliquez sur ⟳ Rafraîchir.")
            self.btn_prep.setEnabled(False)
            self.btn_start.setEnabled(False)
        else:
            self.seq_info = info
            self.lbl_seq_name.setObjectName("SeqInfoOK")
            self.lbl_seq_name.setText(f"✓  {info['seqname']}")
            layers = "monochrome" if info["nb_layers"] == 1 else "couleur (3 canaux)"
            self.lbl_seq_info.setText(
                f"{len(info['files'])} image(s)  •  {layers}\n"
                f"📂 {info['work_dir']}"
            )
            self.spn_ref_idx.setRange(0, len(info["files"]) - 1)
            self.btn_prep.setEnabled(True)
            self._log(f"Séquence détectée : {info['seqname']} ({len(info['files'])} images)")
        # Force re-polish (objectName changed)
        self.lbl_seq_name.style().unpolish(self.lbl_seq_name)
        self.lbl_seq_name.style().polish(self.lbl_seq_name)

    # =========================================================================
    #  Référence
    # =========================================================================
    def _on_algo_changed(self, idx: int):
        self.grp_sr.setVisible(idx == 0)
        self.grp_ecc.setVisible(idx == 1)

    def _prepare_ref(self):
        if not self.seq_info:
            self._log("⚠ Pas de séquence chargée.")
            return
        modes = ["auto", "first", "last", "manual"]
        mode  = modes[self.cmb_ref_mode.currentIndex()]

        self.btn_prep.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.btn_abort.setEnabled(True)
        self.prog.setValue(0)
        self._log("Recherche de la meilleure référence…" if mode == "auto"
                  else "Chargement de la référence…")

        self._ref_worker = RefLoadWorker(
            self.seq_info["files"], mode, self.spn_ref_idx.value())
        self._ref_worker.progress.connect(lambda p, m: (self.prog.setValue(p), self._log(m)))
        self._ref_worker.done.connect(self._on_ref_done)
        self._ref_worker.error.connect(lambda e: self._log(f"✗ {e}"))
        self._ref_worker.finished.connect(self._set_idle)
        self._ref_worker.start()

    def _on_ref_done(self, lum, stretched, idx: int):
        self.ref_lum       = lum
        self.ref_stretched = stretched
        self.ref_idx       = idx
        self.ref_fname     = Path(self.seq_info["files"][idx]).name

        pm = to_qpixmap(stretched)
        if self._pixitem is None:
            self._pixitem = self._scene.addPixmap(pm)
        else:
            self._pixitem.setPixmap(pm)
        self._scene.setSceneRect(0, 0, pm.width(), pm.height())
        QTimer.singleShot(50, lambda: self._view.fitInView(
            self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio))

        self.lbl_ref_info.setText(
            f"Référence #{idx}  —  {self.ref_fname}  |  {lum.shape[1]}×{lum.shape[0]} px")
        self.prog.setValue(100)
        self._log(f"✓ Référence prête : {self.ref_fname}")
        self.btn_start.setEnabled(True)

    # =========================================================================
    #  Alignement
    # =========================================================================
    def _start_align(self):
        if not self.seq_info or self.ref_lum is None:
            return
        algo = "stackreg" if self.cmb_algo.currentIndex() == 0 else "ecc"
        base = (self.ed_prefix.text().strip().rstrip("_") or "align")

        # Sous-dossier ISOLÉ : les frames alignées ne cohabitent pas avec les
        # originaux, sinon `convert` les mélangerait dans la même séquence.
        out_subdir = str(Path(self.seq_info["work_dir"]) / base)
        self._out_subdir = out_subdir
        self._out_base   = base

        params = {
            "files":      self.seq_info["files"],
            "out_folder": out_subdir,
            "base":       base,
            "ref_lum":    self.ref_lum,
            "algo":       algo,
            "sr_model":   self.cmb_sr.currentText(),
            "ecc_model":  self.cmb_ecc.currentText(),
            "ecc_iter":   self.spn_iter.value(),
            "ecc_eps":    self.spn_eps.value(),
        }

        self.btn_start.setEnabled(False)
        self.btn_prep.setEnabled(False)
        self.btn_abort.setEnabled(True)
        self.prog.setValue(0)
        self._log(f"━━ Alignement {algo.upper()} → {out_subdir}")
        siril_safe_log(self.siril,
            f"SirilJ SolarAlign — Alignement {algo.upper()} (séquence : {base})")

        self._align_worker = AlignWorker(params)
        self._align_worker.progress.connect(lambda p, m: (self.prog.setValue(p), self._log(m)))
        self._align_worker.done.connect(self._on_align_done)
        self._align_worker.error.connect(lambda e: self._log(f"✗ {e}"))
        self._align_worker.finished.connect(self._set_idle)
        self._align_worker.start()

    def _on_align_done(self, n_ok: int, n: int, out_dir: str, aborted: bool):
        self.prog.setValue(100)
        if aborted:
            self._log(f"⏹ Interrompu : {n_ok}/{n} images écrites — "
                      "étapes Siril (convert/stack/load) non lancées.")
            return

        msg = f"✓ Alignement terminé : {n_ok}/{n} images."
        self._log(msg)
        siril_safe_log(self.siril, msg)
        self.statusBar().showMessage(msg)

        if n_ok == 0:
            self._log("⚠ Aucun fichier produit — étapes Siril non lancées.")
            return

        if not (self.chk_convert.isChecked() or self.chk_stack.isChecked()
                or self.chk_load.isChecked()):
            return

        base       = self._out_base
        subdir_abs = str(Path(out_dir).resolve())
        orig_wd    = os.getcwd()

        # On se place dans le sous-dossier isolé : `convert` n'y voit QUE les
        # frames alignées (aucun original), et `stack`/`load` y trouvent leur
        # sortie. On restaure le dossier de travail Siril à la fin.
        if not siril_safe_cmd(self.siril, "cd", subdir_abs):
            self._log(f"⚠ Impossible de faire 'cd {subdir_abs}' dans Siril. "
                      "Étapes Siril annulées.")
            return
        try:
            # ── Conversion en séquence ────────────────────────────────────────
            if self.chk_convert.isChecked() or self.chk_stack.isChecked():
                self._log(f"→ Conversion en séquence Siril : {base}")
                ok = siril_safe_cmd(self.siril, "convert", base, "-fitseq")
                if not ok:
                    ok = siril_safe_cmd(self.siril, "convert", base)
                self._log(f"✓ Séquence «{base}» créée." if ok
                          else "⚠ Échec de la commande convert.")

            # ── Empilement ────────────────────────────────────────────────────
            result_file = None
            if self.chk_stack.isChecked():
                method  = self.cmb_stack.currentText()
                out_img = f"{base}_stacked"
                self._log(f"→ Empilement ({method}) → {out_img}")
                args = ["stack", base] + method.split() + [f"-out={out_img}"]
                if siril_safe_cmd(self.siril, *args):
                    self._log(f"✓ Empilement terminé : {out_img}")
                    result_file = out_img
                else:
                    self._log("⚠ Échec de la commande stack.")

            # ── Chargement du résultat ────────────────────────────────────────
            if self.chk_load.isChecked():
                if result_file is None:
                    result_file = f"{base}_00001"   # 1re frame alignée
                self._log(f"→ Chargement dans Siril : {result_file}")
                if siril_safe_cmd(self.siril, "load", result_file):
                    self._log("✓ Affichage dans Siril mis à jour.")
                else:
                    self._log(f"⚠ Échec de load (chargez {result_file} manuellement).")
        finally:
            # Restaure le dossier de travail d'origine de Siril.
            siril_safe_cmd(self.siril, "cd", orig_wd)

    def _set_idle(self):
        self.btn_prep.setEnabled(self.seq_info is not None)
        self.btn_abort.setEnabled(False)
        self.btn_start.setEnabled(self.ref_lum is not None)

    def _abort_all(self, wait: bool = False):
        for w in (self._ref_worker, self._align_worker):
            if w and w.isRunning():
                w.abort()
                if wait:
                    w.wait(5000)   # joint le thread avant destruction
        if not wait:
            self._log("⏹ Arrêté.")

    # =========================================================================
    #  Log
    # =========================================================================
    def _log(self, msg: str):
        self.log.append(msg)
        self.log.ensureCursorVisible()
        self.statusBar().showMessage(msg)

    # =========================================================================
    #  Settings
    # =========================================================================
    def _restore_settings(self):
        s_ = QSettings("VeraLux", "SirilJ_SolarAlign")
        if s_.contains("geometry"):
            self.restoreGeometry(s_.value("geometry"))
        self.ed_prefix.setText(s_.value("prefix", "align_"))

    def closeEvent(self, event):
        # Joint les threads avant destruction de la fenêtre, sinon
        # « QThread: Destroyed while thread is still running » → crash.
        self._abort_all(wait=True)
        s_ = QSettings("VeraLux", "SirilJ_SolarAlign")
        s_.setValue("geometry", self.saveGeometry())
        s_.setValue("prefix",   self.ed_prefix.text())
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
    win = SolarAlignWindow(siril)
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
