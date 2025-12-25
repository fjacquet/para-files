# Lightroom Classic - Workflow Complet

## Table des matières
1. [Organisation du catalogue](#organisation-du-catalogue)
2. [Import des photos](#import-des-photos)
3. [Tri et sélection](#tri-et-sélection)
4. [Développement RAW](#développement-raw)
5. [Outils de développement](#outils-de-développement)
6. [Presets](#presets)
7. [Export](#export)
8. [Workflow Fuji](#workflow-fuji)

---

## Organisation du catalogue

### Structure recommandée
```
Photos/
├── 2024/
│   ├── 2024-12-24_Noel/
│   ├── 2024-12-31_Reveillon/
│   └── ...
├── 2025/
│   ├── 2025-01-15_Montagne/
│   └── ...
└── Lightroom Catalog/
    └── Photos.lrcat
```

### Convention de nommage
```
AAAA-MM-JJ_Nom-du-projet
```
- Tri chronologique automatique
- Facile à retrouver
- Compatible tous systèmes

### Collections
- **Collections rapides** : Sélection temporaire
- **Collections** : Projets/thèmes permanents
- **Collections dynamiques** : Filtres automatiques (5 étoiles, etc.)

---

## Import des photos

### Paramètres d'import

```
Source : Carte SD
Destination : Disque dur externe ou dossier dédié

Options :
☑ Build Smart Previews (pour édition hors ligne)
☑ Make a Second Copy To (sauvegarde)
☑ Add to Collection (optionnel)

File Renaming :
Date-Sequence : 2024-12-24_001.RAF
```

### Apply During Import
Appliquer automatiquement :
- **Metadata Preset** : Copyright, contact
- **Develop Settings** : Preset de base (optionnel)

### Post-import checklist
- [ ] Vérifier que toutes les photos sont importées
- [ ] Supprimer les ratés évidents
- [ ] Sauvegarder le catalogue

---

## Tri et sélection

### Système de notation

| Note | Usage |
|------|-------|
| ⭐ | À revoir |
| ⭐⭐ | Correcte |
| ⭐⭐⭐ | Bonne |
| ⭐⭐⭐⭐ | Très bonne |
| ⭐⭐⭐⭐⭐ | Portfolio |

### Drapeaux
- **P (Pick)** : Sélectionnée
- **X (Reject)** : À supprimer
- **U (Unflagged)** : Non triée

### Workflow de tri rapide
```
1. Mode Loupe (E) ou Grid (G)
2. Premier passage rapide :
   - P = garder
   - X = supprimer
3. Filtrer : Flagged only
4. Deuxième passage : Ajouter étoiles
5. Filtrer : 4-5 étoiles = à développer
```

### Raccourcis essentiels
| Touche | Action |
|--------|--------|
| G | Vue grille |
| E | Vue loupe |
| D | Module Développement |
| P | Flag pick |
| X | Flag reject |
| 1-5 | Étoiles |
| → ← | Photo suivante/précédente |
| \ | Avant/Après |

---

## Développement RAW

### Ordre des ajustements

```
1. Profil (Camera Matching ou Adobe)
2. Balance des blancs
3. Exposition
4. Hautes lumières / Ombres
5. Blancs / Noirs
6. Clarté / Texture
7. Vibrance / Saturation
8. Courbe des tonalités
9. Couleurs (HSL)
10. Netteté
11. Réduction du bruit
12. Corrections optiques
13. Recadrage
```

### Panneau Basic

#### Profil
```
Pour Fuji X-T4 :
- Camera Matching > Provia (naturel)
- Camera Matching > Velvia (saturé)
- Camera Matching > Classic Chrome (vintage)
```

#### Balance des blancs
- **As Shot** : Garder les réglages boîtier
- **Auto** : Correction automatique
- **Température** : Froid (bleu) ↔ Chaud (orange)
- **Teinte** : Vert ↔ Magenta

#### Exposition & Tonalité
| Curseur | Effet |
|---------|-------|
| **Exposure** | Luminosité globale |
| **Contrast** | Écart clair/foncé |
| **Highlights** | Récupérer ciels cramés |
| **Shadows** | Éclaircir ombres |
| **Whites** | Point blanc (highlight clipping) |
| **Blacks** | Point noir (shadow clipping) |

**Technique** : Maintenir Alt en ajustant Whites/Blacks pour voir l'écrêtage

#### Présence
| Curseur | Effet |
|---------|-------|
| **Texture** | Détails moyens (peau, feuillage) |
| **Clarity** | Contraste local (punch) |
| **Dehaze** | Enlève brume/voile |
| **Vibrance** | Saturation intelligente |
| **Saturation** | Saturation globale |

---

## Outils de développement

### Tone Curve
Contrôle fin des tonalités par zones.

```
Courbe en S classique :
   ┌────────────────┐
   │       ╱        │
   │      ╱         │
   │     ╱          │
   │    ╱           │
   └────────────────┘
= Plus de contraste
```

### HSL / Color
Ajuster couleurs individuellement :
- **Hue** : Teinte (ex: rendre ciel plus bleu)
- **Saturation** : Intensité couleur
- **Luminance** : Clarté couleur

**Astuce paysage** :
- Orange luminance +20 (tons chair)
- Blue saturation +15, luminance -10 (ciels)

### Detail (Netteté & Bruit)

#### Sharpening
```
Amount : 40-80 (selon image)
Radius : 1.0-1.5
Detail : 25-40
Masking : 60-80 (Alt pour voir masque)
```

#### Noise Reduction
```
Luminance : 20-40 (ISO élevés)
Detail : 50
Contrast : 50
Color : 25 (par défaut suffit)
```

### Lens Corrections
```
☑ Remove Chromatic Aberration (toujours)
☑ Enable Profile Corrections (toujours)
Profil : Fujifilm > XF 23mm F2 (auto-détecté)
```

### Transform
```
☑ Constrain Crop (auto)
Upright : Auto ou Guided (lignes manuelles)
```

### Crop
- **Aspect** : Original, 16:9, 4:5 (Instagram), 1:1
- **Angle** : Redresser horizon
- **Règle des tiers** : O pour changer overlay

---

## Presets

### Créer un preset
```
1. Développer une photo de référence
2. + (à côté de Presets)
3. Nommer : "Mon style paysage"
4. Cocher les paramètres à sauvegarder
5. Enregistrer
```

### Paramètres à inclure
**Preset style (look)** :
- ☑ White Balance
- ☑ Basic Tone
- ☑ Tone Curve
- ☑ Color

**Ne pas inclure** :
- ☐ Exposure (varie par photo)
- ☐ Lens Corrections (varie par objectif)
- ☐ Transform (varie par photo)

### Appliquer à l'import
```
File → Import
Apply During Import → Develop Settings → [Mon preset]
```

### Presets recommandés débutant
1. **Base neutre** : Lens corrections + léger sharpen
2. **Paysage punch** : Clarté +15, Vibrance +20
3. **Portrait doux** : Clarity -10, Shadows +20
4. **N&B classique** : Profile B&W + Contrast +20

---

## Export

### Paramètres standard

#### Pour le web / Réseaux sociaux
```
Format : JPEG
Quality : 80
Resize : Long Edge 2048px
Sharpen : Screen, Standard
Metadata : Copyright only
```

#### Pour impression
```
Format : JPEG ou TIFF
Quality : 100
Resize : No resize (ou selon impression)
Resolution : 300 ppi
Sharpen : Matte ou Glossy, selon papier
Color Space : sRGB (imprimeur standard) ou Adobe RGB (labo pro)
```

#### Pour archive
```
Format : TIFF
Bit Depth : 16 bit
Compression : None
Resize : No
Color Space : ProPhoto RGB
```

### Export presets
Créer des presets pour usage répété :
- "Instagram" : 1080px, JPEG 85%
- "Portfolio Web" : 2048px, JPEG 90%
- "Print A3" : Full res, TIFF

---

## Workflow Fuji

### Profils Camera Matching
Lightroom inclut les simulations Fuji :
```
Profile → Camera Matching →
- Camera Provia/Standard
- Camera Velvia/Vivid
- Camera Astia/Soft
- Camera Classic Chrome
- Camera Pro Neg Hi
- Camera Pro Neg Std
- Camera Acros (N&B)
- Camera Eterna
```

### Réduction du bruit X-Trans
Le capteur X-Trans de Fuji nécessite attention :
- **Enhanced Details** : Edit → Enhance → Super Resolution
- Ou : Luminance NR légèrement plus élevée

### Simulations dans LR vs in-camera
| Aspect | In-camera (JPEG) | Lightroom (RAW) |
|--------|------------------|-----------------|
| Flexibilité | Fixe | Modifiable |
| Qualité | Bonne | Meilleure |
| Workflow | Plus rapide | Plus long |

**Recommandation** : Toujours RAW, appliquer simulation dans LR

### Workflow rapide Fuji
```
1. Import RAW (.RAF)
2. Appliquer profil Camera Matching
3. Ajuster exposition
4. Fine-tune (HSL, netteté)
5. Export
```

### Lens profiles Fuji disponibles
La plupart des objectifs XF sont supportés :
- XF 10-24mm F4
- XF 16mm F1.4
- XF 16-55mm F2.8
- XF 18-55mm F2.8-4
- XF 23mm F1.4 / F2
- XF 35mm F1.4 / F2
- XF 56mm F1.2
- etc.

---

## Raccourcis essentiels

### Navigation
| Touche | Action |
|--------|--------|
| G | Grille (Library) |
| E | Loupe (Library) |
| D | Développement |
| C | Comparaison |

### Développement
| Touche | Action |
|--------|--------|
| \ | Avant/Après |
| R | Crop |
| K | Pinceau |
| M | Filtre gradué |
| Shift+M | Filtre radial |
| Cmd/Ctrl+Z | Annuler |
| Cmd/Ctrl+Shift+C | Copier réglages |
| Cmd/Ctrl+Shift+V | Coller réglages |

### Tri
| Touche | Action |
|--------|--------|
| P | Pick |
| X | Reject |
| U | Unflag |
| 0-5 | Étoiles |
| 6-9 | Labels couleur |
