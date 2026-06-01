# SirilJ Solar Align — Guide d'utilisation

**Version 2.0**  
Alignement de la séquence H-alpha solaire courante de Siril par StackReg ou ECC, avec conversion, empilement et affichage du résultat directement dans Siril.

---

## Prérequis

| Composant | Version |
|---|---|
| Siril | 1.3 ou ultérieur |
| Python (via sirilpy) | 3.10 ou ultérieur |
| PyQt6 | récent |
| numpy | récent |
| astropy | récent |
| pystackreg | récent |
| opencv-python | récent |

Les dépendances sont installées automatiquement au premier lancement via `sirilpy.ensure_installed`.

---

## Lancement

1. Dans Siril, **charger une séquence de FITS individuels** (menu *Conversion* sans l'option FITSEQ, ou *Ouvrir une séquence*).
2. Aller dans **Script → Exécuter un script** et sélectionner `SirilJ_SolarAlign.py`.
3. La fenêtre s'ouvre et détecte automatiquement la séquence courante.

> ⚠ **Séquences mono-fichier non prises en charge.** Une séquence FITSEQ (un seul `.fits` contenant toutes les frames) ou SER ne peut pas être alignée directement : le script travaille sur des **FITS individuels**. Reconvertissez la séquence en FITS individuels (Conversion **sans** l'option *FITS sequence*), puis cliquez sur **⟳ Rafraîchir**.

---

## Présentation de l'interface

```
┌──────────────────────┬──────────────────────────────────────┐
│  Séquence Siril       │  Aperçu — Image de référence          │
│  Image de référence   │  (zoom molette, déplacement glisser)  │
│  Algorithme           │                                       │
│  Sortie & intégration ├──────────────────────────────────────┤
│  Préparer / Démarrer  │  Barre de progression                 │
│  Arrêter              │  Journal d'exécution                  │
└──────────────────────┴──────────────────────────────────────┘
```

---

## Déroulement en deux étapes

L'alignement se fait toujours en deux temps : **préparer la référence**, puis **démarrer**.

### 1. Préparer la référence

Le bouton **« Préparer la référence »** charge l'image de référence et l'affiche dans l'aperçu de droite. Cela permet de vérifier visuellement qu'il s'agit bien de la bonne image avant de lancer le traitement complet.

### 2. Démarrer l'alignement

Le bouton **« ▶ Démarrer l'alignement »** ne s'active qu'**après** la préparation. Il aligne toutes les frames de la séquence sur la référence, puis enchaîne les étapes Siril cochées (conversion, empilement, chargement).

Le bouton **« ⏹ Arrêter »** interrompt proprement le traitement. En cas d'arrêt, **aucune** étape Siril (conversion / empilement / chargement) n'est lancée — seules les frames déjà écrites restent sur le disque.

---

## Séquence Siril courante

| Affichage | Signification |
|---|---|
| `✓  <nom>` (vert) | Séquence détectée ; nombre d'images, mono/couleur et chemin affichés |
| `⚠ <nom> — séquence mono-fichier` | FITSEQ/SER : exporter en FITS individuels |
| `Aucune séquence chargée` | Charger une séquence dans Siril puis ⟳ Rafraîchir |

Le bouton **⟳ Rafraîchir** relance la détection après tout changement côté Siril.

---

## Image de référence

| Mode | Effet |
|---|---|
| **Meilleure netteté** | Analyse toutes les frames et retient la plus nette (variance du gradient) |
| **Première** | Première frame de la séquence |
| **Dernière** | Dernière frame |
| **Manuel** | Index saisi dans le champ *Index* |

L'aperçu affiche un **autostretch** de la référence (les données ne sont pas modifiées).

---

## Algorithmes

### StackReg

Portage Python du plugin ImageJ StackReg (Thévenaz, EPFL). Robuste, sans réglage.

| Modèle | Degrés de liberté |
|---|---|
| **Translation** | décalage X/Y |
| **Corps rigide** | translation + rotation *(recommandé pour le Soleil)* |
| **Rotation/Échelle** | translation + rotation + échelle isotrope |
| **Affine** | + cisaillement |
| **Bilinéaire** | déformation non linéaire |

### ECC (OpenCV)

Maximisation de corrélation (Evangelidis & Psarakis) via `cv2.findTransformECC`.

| Option | Rôle |
|---|---|
| **Modèle** | Translation, Euclidien, Affine, Homographie |
| **Itérations** | nombre maximal d'itérations (défaut 50) |
| **Epsilon** | seuil de convergence (défaut 1e-4) |

> **Conseil :** pour des disques solaires plein cadre, **StackReg / Corps rigide** donne d'excellents résultats sans réglage. ECC Euclidien est une bonne alternative ; passez aux modèles Affine/Homographie seulement en cas de distorsion géométrique.

---

## Sortie & intégration Siril

Les frames alignées sont écrites dans un **sous-dossier isolé** du dossier de travail, nommé d'après le **préfixe** (par défaut `align_` → sous-dossier `align/`), et numérotées séquentiellement (`align_00001.fit`, …).

> Pourquoi un sous-dossier ? La commande Siril `convert` convertit **tous** les FITS d'un dossier. En isolant les frames alignées, on évite que les images originales (non alignées) soient mélangées à la séquence finale.

| Option | Effet |
|---|---|
| **Préfixe** | Nom de base du sous-dossier, de la séquence et du résultat |
| **Convertir en séquence Siril** | `convert <base> -fitseq` dans le sous-dossier |
| **Empiler après alignement** | `stack <base> <méthode> -out=<base>_stacked` |
| **Méthode** | `sum`, `med`, `rej 3 3`, `max`, `min` |
| **Charger le résultat dans Siril** | `load` de l'empilement (ou de la 1ʳᵉ frame alignée) |

À la fin, le script restaure automatiquement le dossier de travail d'origine de Siril.

**Conservation photométrique :** la normalisation [0,1] ne sert qu'à l'alignement et à l'aperçu. Les frames sauvegardées **conservent l'échelle d'origine** (FITS float32), afin que l'empilement soit photométriquement cohérent.

---

## Méthodes d'empilement

| Méthode | Usage typique |
|---|---|
| **sum** | Addition — maximise le signal (défaut solaire) |
| **med** | Médiane — élimine les transitoires (avions, rayons cosmiques) |
| **rej 3 3** | Rejet sigma (3σ bas / 3σ haut) — compromis signal/rejet |
| **max** | Maximum — utile pour protubérances |
| **min** | Minimum — atténue le bruit isolé |

---

## Journal d'exécution

Chaque étape est tracée dans le journal du panneau droit et, pour les étapes clés, dans la **console de Siril**.

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

## Notes & conseils

- **Mémoire** : l'analyse « meilleure netteté » lit chaque frame une fois ; sur de très longues séquences cela peut prendre un moment (progression affichée).
- **Re-lancement** : relancer écrase proprement les sorties précédentes du même préfixe (frames, fitseq, `.seq`, empilement) sans toucher aux autres fichiers.
- **Fermeture** : fermer la fenêtre pendant un traitement l'interrompt et attend la fin du thread avant de quitter (pas de crash).
- **Couleur** : les images couleur (3 canaux) sont alignées canal par canal avec la même transformation.
- Les **données originales de la séquence ne sont jamais modifiées** : toutes les sorties vont dans le sous-dossier.

---

## Correspondance avec ImageJ

| Plugin ImageJ | Équivalent dans ce script |
|---|---|
| **StackReg** (Thévenaz) | Algorithme StackReg, tous modèles |
| **TurboReg** (Thévenaz) | Moteur sous-jacent de StackReg (pyramidal) |
| **Image Stabilizer** / **Linear Stack Alignment with SIFT** | Algorithme ECC (approche par corrélation) |
| **Image → Stacks → Z Project…** | Étape d'empilement (`sum`, `med`, `max`, `min`) |
