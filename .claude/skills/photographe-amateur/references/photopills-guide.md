# PhotoPills - Guide de Planification

## Table des matières
1. [Vue d'ensemble](#vue-densemble)
2. [Planificateur (Planner)](#planificateur-planner)
3. [Soleil & Lune](#soleil--lune)
4. [Voie Lactée](#voie-lactée)
5. [Calculateurs](#calculateurs)
6. [Réalité Augmentée](#réalité-augmentée)
7. [Planifier une sortie](#planifier-une-sortie)

---

## Vue d'ensemble

PhotoPills est l'app indispensable pour planifier tes photos. Elle répond à :
- Où sera le soleil/la lune à telle heure ?
- Quand la Voie Lactée sera-t-elle visible ?
- Quelle est l'hyperfocale pour ma focale ?
- À quelle heure est la golden hour ?

### Écran d'accueil (Pills)
- **Planner** : Planificateur principal
- **Sun** : Position soleil
- **Moon** : Position lune + phases
- **Milky Way** : Voie Lactée
- **Exposure** : Calculateur expo
- **DoF** : Profondeur de champ
- **Hyperfocal** : Distance hyperfocale
- **Star Trails** : Calculs filés d'étoiles
- **Timelapse** : Calculs timelapse

---

## Planificateur (Planner)

L'outil central de PhotoPills.

### Interface
```
┌─────────────────────────────────┐
│      [Carte avec position]      │
│                                 │
│  ☀️ ━━━━━━━━━━━━━━━━━━━ 🌅     │ ← Trajectoire soleil
│  🌙 ━━━━━━━━━━━━━━━━━━━ 🌑     │ ← Trajectoire lune
│                                 │
├─────────────────────────────────┤
│ Date: [25 Dec 2024]  [< >]      │
│ Heure: [16:45]       [< >]      │
├─────────────────────────────────┤
│ Lever: 08:12  Coucher: 17:23    │
│ Golden: 07:42-08:42 / 16:53-17:53│
│ Blue: 07:12-07:42 / 17:53-18:23 │
└─────────────────────────────────┘
```

### Lignes sur la carte
| Couleur | Signification |
|---------|---------------|
| **Orange épais** | Lever du soleil |
| **Orange fin** | Coucher du soleil |
| **Jaune** | Trajectoire soleil |
| **Bleu clair** | Lever de lune |
| **Bleu foncé** | Coucher de lune |
| **Gris** | Trajectoire lune |

### Utilisation basique
1. **Placer le pin rouge** sur ton spot
2. **Ajuster la date** avec les flèches
3. **Faire glisser l'heure** pour voir le soleil bouger
4. **Lire les infos** en bas (heures golden/blue hour)

### Trouver l'alignement parfait
1. Placer pin rouge sur le sujet (montagne, monument)
2. Placer pin noir sur ta position de prise de vue
3. Ajuster date/heure jusqu'à ce que le soleil/lune soit aligné

---

## Soleil & Lune

### Pill "Sun"
Affiche pour ta position :
- **Lever** : Heure exacte
- **Coucher** : Heure exacte
- **Golden Hour** : Début et fin (matin + soir)
- **Blue Hour** : Début et fin (matin + soir)
- **Azimut** : Direction du soleil (degrés)
- **Élévation** : Hauteur du soleil (degrés)

### Pill "Moon"
- **Phase actuelle** : Nouvelle → Croissante → Pleine → Décroissante
- **Illumination** : Pourcentage visible
- **Lever/Coucher** : Heures
- **Moonrise/Moonset direction** : Pour alignements

### Calendrier des phases
```
Moon Pill → Calendar
- Repérer nouvelles lunes (astro)
- Repérer pleines lunes (paysage éclairé)
- Planifier semaines à l'avance
```

### Conseils
- **Astro** : Nouvelle lune ± 3 jours
- **Lune dans paysage** : Pleine lune au lever/coucher
- **Super lune** : Lune plus proche = plus grosse (calendrier annuel)

---

## Voie Lactée

### Pill "Milky Way"
Indique quand et où voir la Voie Lactée.

### Informations clés
- **Visibility** : Heures où le centre galactique est visible
- **Azimut** : Direction de la Voie Lactée
- **Élévation** : Hauteur dans le ciel

### Saison de la Voie Lactée (Hémisphère Nord)
| Période | Visibilité | Position |
|---------|------------|----------|
| Fév-Avr | Tôt matin | Horizontale, Est |
| Mai-Juil | Milieu nuit | Verticale, Sud |
| Août-Oct | Début nuit | Inclinée, Ouest |
| Nov-Jan | Difficile | Centre galactique sous horizon |

### Meilleures conditions
1. **Nouvelle lune** (ou lune couchée)
2. **Loin pollution lumineuse** (carte : lightpollutionmap.info)
3. **Ciel dégagé**
4. **Été** : Voie Lactée plus haute et plus longtemps visible

### Planifier une photo Voie Lactée
```
1. Milky Way Pill → Choisir date
2. Vérifier "Galactic Center Rise/Set"
3. Planner → Placer pin sur spot
4. Ajuster heure pour position souhaitée
5. AR → Visualiser sur place
```

---

## Calculateurs

### Exposure Calculator
Calcule les équivalences d'exposition.

**Exemple** : Passer de jour à ND1000
```
Mesure sans filtre : f/8, 1/125s, ISO 200
→ Avec ND1000 : f/8, 8s, ISO 200
```

### DoF Calculator (Profondeur de champ)
```
Entrer :
- Focale : 23mm
- Ouverture : f/8
- Distance sujet : 3m

Résultat :
- Zone nette : 1.5m à ∞
- Hyperfocale : 2.2m
```

### Hyperfocal Table
Table précalculée pour X-T4 (APS-C) :

| Focale | f/5.6 | f/8 | f/11 |
|--------|-------|-----|------|
| 16mm | 1.9m | 1.3m | 1.0m |
| 23mm | 3.9m | 2.7m | 2.0m |
| 35mm | 9.0m | 6.3m | 4.6m |

**Usage** : Faire le point à l'hyperfocale = tout net de moitié à ∞

### Star Trails Calculator
```
Entrer :
- Type de filé souhaité
- Focale
- Orientation (Nord/Sud/Est/Ouest)

Résultat :
- Temps total nécessaire
- Nombre de poses
- Intervalle recommandé
```

### Timelapse Calculator
```
Entrer :
- Durée vidéo souhaitée : 10s
- FPS : 24
- Intervalle : 5s

Résultat :
- Nombre d'images : 240
- Durée tournage : 20 min
```

---

## Réalité Augmentée

### AR Night (Mode nuit)
Superpose Voie Lactée sur la vue caméra.

**Utilisation** :
1. Sur place, de nuit
2. AR → Night AR
3. Voir où sera la Voie Lactée
4. Composer ton cadre avant qu'elle soit visible

### AR Sun/Moon
Superpose trajectoire soleil/lune sur la vue caméra.

**Utilisation** :
1. Sur place, de jour
2. AR → Sun AR ou Moon AR
3. Voir où passera le soleil/lune
4. Planifier l'alignement avec ton sujet

### AR Tips
- Calibrer la boussole (faire des 8)
- Tenir le téléphone vertical pour précision
- Utiliser le niveau intégré

---

## Planifier une sortie

### Workflow complet

#### 1. Choisir la date
```
Critères :
- Météo favorable
- Phase de lune adaptée
- Disponibilité personnelle
```

#### 2. Repérer le spot
```
Options :
- Google Maps/Earth pour visualiser
- Instagram/500px pour inspiration
- Sur place en reconnaissance
```

#### 3. Planifier dans PhotoPills
```
1. Planner → Placer pin sur spot
2. Entrer la date
3. Vérifier golden/blue hour
4. Si astro : vérifier Voie Lactée + phase lune
5. Noter azimut du soleil/lune si alignement voulu
```

#### 4. Créer un plan
```
PhotoPills → My Stuff → Plans
- Sauvegarder le spot (pin)
- Noter les heures clés
- Exporter vers calendrier
```

### Exemple : Photo de montagne au lever

**Objectif** : Soleil qui éclaire le sommet

```
1. Planner → Pin sur sommet
2. Pin noir sur position photo
3. Date souhaitée
4. Trouver quand soleil aligne avec sommet
5. Noter heure de lever + golden hour
6. Arriver 45min avant
7. Installer, tester réglages, attendre
```

### Exemple : Voie Lactée + premier plan

**Objectif** : Voie Lactée verticale au-dessus d'un arbre

```
1. Milky Way Pill → Date en été
2. Vérifier heure centre galactique au zénith
3. Planner → Pin sur l'arbre
4. Ajuster heure pour Voie Lactée verticale
5. Vérifier lune absente (nouvelle lune)
6. AR sur place pour confirmer position
```

### Checklist avant sortie

- [ ] Météo vérifiée (claire)
- [ ] Heures golden/blue hour notées
- [ ] Phase de lune compatible
- [ ] Trajet calculé (arriver 45min avant)
- [ ] Spot repéré (coordonnées GPS)
- [ ] Plan B si météo change
