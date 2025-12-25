# Astrophotographie & Timelapse

## Table des matières

1. [Astrophotographie](#astrophotographie)
2. [Timelapse - Bases](#timelapse---bases)
3. [Unleashed - Configuration](#unleashed---configuration)
4. [Holy Grail (Jour→Nuit)](#holy-grail-journuit)
5. [LRTimelapse 6 - Workflow](#lrtimelapse-6---workflow)
6. [Recettes timelapse](#recettes-timelapse)

---

## Astrophotographie

### Conditions requises

- **Pollution lumineuse** : Fuir les villes (carte : lightpollutionmap.info)
- **Lune** : Nouvelle lune ou lune couchée
- **Météo** : Ciel dégagé, faible humidité
- **Planification** : PhotoPills pour position Voie Lactée

### Règle NPF (plus précise que règle 500)

Évite le filé d'étoiles. Pour X-T4 (capteur APS-C) :

```
Temps max = (35 × ouverture + 30 × pixels) / focale

Simplification X-T4 :
Temps max ≈ 250 / focale
```

| Focale | Temps max |
| ------ | --------- |
| 12mm   | 20s       |
| 16mm   | 15s       |
| 23mm   | 10s       |
| 35mm   | 7s        |

### Réglages Voie Lactée

```
Mode        : M
Ouverture   : Max (f/1.4 - f/2.8)
Vitesse     : Selon règle NPF
ISO         : 3200-6400
Mise au point: Manuelle sur étoile brillante
Balance blanc: 3800-4200K (évite orange)
Stabilisation: OFF
RAW         : Obligatoire
```

### Mise au point sur étoiles

1. Passer en **MF**
2. Viser étoile brillante (Véga, Sirius)
3. Activer **Focus Peaking** + **loupe**
4. Tourner bague jusqu'à point le plus petit
5. **Scotcher la bague** pour éviter décalage

### Composition astro

- Premier plan intéressant (arbre, montagne, lac)
- Voie Lactée comme élément, pas sujet unique
- Centre galactique = partie la plus brillante

### Star Trails (filés d'étoiles)

**Méthode** : Empilement de nombreuses poses courtes

```
Réglages :
- Ouverture : f/4
- Vitesse : 30s
- ISO : 800-1600
- Intervalle : 1s (avec Unleashed)
- Durée : 1h minimum = 120 images
```

**Post-traitement** : StarStax (gratuit) ou Photoshop

---

## Timelapse - Bases

### Calculs essentiels

```
Durée finale = Nombre d'images / FPS
Nombre d'images = Durée tournage / Intervalle
```

**Exemple** :

- Vidéo souhaitée : 10s à 24fps = 240 images
- Intervalle : 5s
- Durée tournage : 240 × 5s = 1200s = 20 min

### Tableau de référence

| Sujet          | Intervalle | Durée tournage | Résultat (10s/24fps) |
| -------------- | ---------- | -------------- | -------------------- |
| Nuages rapides | 2s         | 8 min          | Fluide               |
| Nuages lents   | 5s         | 20 min         | Fluide               |
| Coucher soleil | 3-5s       | 12-20 min      | Fluide               |
| Voie Lactée    | 20-30s     | 1h20-2h        | Acceptable           |
| Fleurs (bloom) | 5-10 min   | 12-24h         | Fluide               |
| Construction   | 30 min     | Jours/Semaines | Variable             |

### Réglages de base

```
Mode        : M (OBLIGATOIRE)
Ouverture   : Fixe (f/8 typique)
ISO         : Fixe ou Auto avec ramping
Vitesse     : 1/2 de l'intervalle max (motion blur naturel)
Balance blanc: Fixe (Kelvin, pas Auto!)
Mise au point: Manuelle + scotchée
Stabilisation: OFF
```

### Éviter le flicker

1. **Mode M** : Pas de variations automatiques
2. **Vitesse ≥ 1/100s** : Variations mécaniques de l'obturateur
3. **Ouverture fixe** : Pas de changement
4. **LRTimelapse** : Deflicker en post

---

## Unleashed - Configuration

### Installation

1. Télécharger app **Unleashed** (iOS/Android)
2. Monter module sur griffe flash X-T4
3. Bluetooth : appareil → téléphone

### Modes principaux

#### Intervalomètre simple

```
Unleashed → Intervalometer
- Interval : temps entre photos
- Frames : nombre total (0 = infini)
- Start Delay : délai avant début
```

#### Bulb Ramping (poses longues)

```
Pour expositions > 30s (astro, nuit)
- Utiliser mode Bulb sur X-T4
- Unleashed contrôle la durée
```

### Réglages recommandés

**Timelapse jour (nuages)** :

```
Interval : 3-5s
Vitesse X-T4 : 1/100s
Frames : 300-500
```

**Timelapse coucher de soleil** :

```
Interval : 4s
Vitesse X-T4 : 1/50s ou plus lent
ISO : Auto (avec LRTimelapse)
Frames : 400-600
```

**Timelapse nuit (Voie Lactée)** :

```
Interval : 25s
Vitesse X-T4 : 20s
Frames : 200+
Start Delay : 5s
```

### Astuces Unleashed

- **Exposure Preview** : Voir l'image sur téléphone
- **GPS tagging** : Géolocalise les photos
- **Batterie** : Désactiver Bluetooth boîtier si non utilisé
- **Mode avion X-T4** : Économise batterie boîtier

---

## Holy Grail (Jour→Nuit)

Le "Saint Graal" du timelapse : transition fluide jour → nuit (ou inverse).

### Défi

- Luminosité change de 15+ stops
- ISO, vitesse, ouverture doivent s'adapter
- Éviter les sauts d'exposition visibles

### Méthode avec X-T4 + LRTimelapse

#### Sur le terrain

```
Mode X-T4    : M
Ouverture    : Fixe f/8
ISO          : Auto (160-6400)
Vitesse      : 1/50s → va ralentir automatiquement
Interval     : 5s
```

**Technique "Bulb Ramping" simplifiée** :

1. Commencer en fin d'après-midi
2. ISO Auto ajuste l'exposition
3. Quand ISO atteint max → ralentir vitesse manuellement
4. LRTimelapse lisse les transitions

#### Workflow simplifié

1. Laisser ISO Auto compenser
2. Surveiller l'histogramme sur Unleashed
3. Ajuster vitesse quand ISO sature
4. Post-traiter dans LRTimelapse (keyframes + deflicker)

---

## LRTimelapse 6 - Workflow

### Installation

- Nécessite Lightroom Classic
- Plugin LRTimelapse s'intègre à LR
- Licence payante (version d'essai disponible)

### Workflow complet

#### Étape 1 : Import dans LRTimelapse

```
1. Ouvrir LRTimelapse
2. Naviguer vers dossier des RAW
3. Cliquer "Initialize"
   → Crée les métadonnées XMP
```

#### Étape 2 : Keyframes

```
1. Bouton "Auto-Keyframes" ou manuel
2. Recommandé : 1 keyframe tous les 30-50 images
3. Plus de keyframes = plus de contrôle transitions
```

#### Étape 3 : Éditer dans Lightroom

```
1. "Drag to Lightroom" (glisser l'icône)
2. Dans LR : import automatique
3. Éditer UNIQUEMENT les keyframes (étoiles jaunes)
4. Développement : exposition, couleur, etc.
```

#### Étape 4 : Retour LRTimelapse

```
1. Dans LR : Metadata → Save to Files (Ctrl+S)
2. Retour LRTimelapse
3. "Reload" pour voir les changements
4. Ajuster courbes si nécessaire
```

#### Étape 5 : Auto-Transition

```
1. Cliquer "Auto Transition"
   → Interpole les réglages entre keyframes
2. "Visual Deflicker" si flicker visible
3. "Save" pour écrire les XMP
```

#### Étape 6 : Export final

```
Option A - Via Lightroom :
1. "Drag to Lightroom" à nouveau
2. LR : Sélectionner toutes les images
3. File → Export (JPEG haute qualité)

Option B - Via LRTimelapse :
1. "Visual Preview" pour vérifier
2. "LRT Export" pour qualité maximale
3. Choisir codec (ProRes, H.264, etc.)
```

### Deflicker

Le flicker = variations de luminosité entre images.

**Causes** :

- Ouverture mécanique légèrement variable
- Mode Auto (ISO, vitesse, balance blanc)
- Nuages passant devant le soleil

**Solution dans LRTimelapse** :

```
1. "Visual Deflicker" après Auto Transition
2. Ajuster "Strength" (10-30 typique)
3. Prévisualiser avant export
```

### Rendu final

**Réglages export recommandés** :

```
Format : H.264 ou ProRes
Résolution : 4K (3840×2160) ou 1080p
FPS : 24 (cinéma) ou 30 (web)
Qualité : Maximum
```

---

## Recettes timelapse

### Nuages dramatiques

```
Durée : 30 min
Interval : 3s
Images : 600
Réglages : M, f/8, 1/100s, ISO 160
Film Sim : Velvia
Post : Contraste +, Clarté +
```

### Coucher de soleil

```
Durée : 1h (commencer 30min avant)
Interval : 4s
Images : 900
Réglages : M, f/8, ISO Auto, 1/50s
Post : White balance keyframes (chaud→froid)
```

### Voie Lactée (rotation)

```
Durée : 2-3h
Interval : 25s
Images : 300-400
Réglages : M, f/1.8, 20s, ISO 3200
Post : Réduction bruit, Voie Lactée +
```

### Holy Grail (jour→nuit)

```
Durée : 2h (1h avant→1h après coucher)
Interval : 5s
Images : 1400
Réglages : M, f/8, ISO Auto, 1/50s→2s
Post : LRTimelapse keyframes + deflicker
```

### Étoiles filées (star trails)

```
Durée : 2-4h
Interval : 1s (gap minimal)
Réglages : M, f/4, 30s, ISO 800
Images : 250-500
Post : StarStax ou empilement Photoshop
```

### Aurores boréales

```
Durée : Toute la nuit
Interval : 6-8s
Réglages : M, f/2.8, 4-6s, ISO 3200
Post : Keyframes couleur, deflicker doux
Conseil : Exposition courte = aurores nettes
```
