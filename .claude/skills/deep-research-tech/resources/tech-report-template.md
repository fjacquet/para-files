# Template : Rapport de Recherche Technique

Copier ce template pour créer un nouveau rapport technique.

---

```yaml
---
created: {{date}}
updated: {{date}}
type: tech-research-report
status: draft | in-progress | complete
tags:
  - research
  - tech
  - topic/[domaine-tech]
question: "Question de recherche technique"
technologies: [tech1, tech2]
sources_count: [nombre]
papers_reviewed: [nombre]
confidence: high | medium | low
---
```

# [Titre du Rapport Technique]

## TL;DR

> **Question** : [Question technique]
>
> **Réponse** : [Synthèse en 2-3 phrases]
>
> **Recommandation** : [Action suggérée]
>
> **Stack recommandé** : `[tech1]` + `[tech2]`

## Contexte Technique

### Problème à Résoudre
[Description du problème technique]

### Contraintes
- Performance : [exigences]
- Compatibilité : [versions, plateformes]
- Licence : [contraintes]

## Méthodologie

### Sources Consultées

| Type | Nombre | Sources principales |
|------|--------|---------------------|
| Papers académiques | N | [Arxiv, etc.] |
| Documentation officielle | N | [Context7] |
| Repos GitHub | N | [liens] |
| Benchmarks | N | [sources] |

### Outils Utilisés
- `mcp__context7__get-library-docs` : Documentation
- `mcp__hugging-face__paper_search` : Papers ML/AI
- [Autres outils]

## État de l'Art (SOTA)

### Approches Actuelles

| Approche | Performance | Trade-offs |
|----------|-------------|------------|
| [Approche 1] | [métriques] | [avantages/inconvénients] |
| [Approche 2] | [métriques] | [avantages/inconvénients] |

### Évolution Récente
[Timeline des avancées majeures]

```
2023 ─── [Événement 1]
2024 ─── [Événement 2]
2025 ─── [Événement 3]
```

## Analyse Comparative

### Technologies Évaluées

| Critère | Option A | Option B | Option C |
|---------|----------|----------|----------|
| Performance | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Facilité d'usage | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Maintenance | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Communauté | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Total** | 17/20 | 15/20 | 13/20 |

### Benchmarks

```
Performance (ops/sec, higher is better)
─────────────────────────────────────
Option A  ████████████████████  1000
Option B  ██████████████        700
Option C  ████████████████████████  1200
```

## Findings Techniques

### 1. [Premier finding technique]

[Explication détaillée]

```python
# Exemple de code si pertinent
def example():
    pass
```

**Paper de référence** : [Auteur et al., 2024](lien)

### 2. [Deuxième finding technique]

[Explication détaillée]

**Documentation** : [Lien Context7 ou officiel]

### 3. [Troisième finding technique]

[Explication détaillée]

## Implémentation Recommandée

### Architecture Proposée

```
┌─────────────┐     ┌─────────────┐
│  Component  │ ──▶ │  Component  │
│     A       │     │     B       │
└─────────────┘     └─────────────┘
```

### Stack Technologique

| Couche | Technologie | Justification |
|--------|-------------|---------------|
| [Couche 1] | [Tech] | [Raison] |
| [Couche 2] | [Tech] | [Raison] |

### Configuration Recommandée

```yaml
# Exemple de configuration
key: value
```

## Limitations et Risques

### Limitations Identifiées
- [Limitation 1]
- [Limitation 2]

### Risques Techniques
| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| [Risque 1] | Moyenne | Haut | [Action] |

### Ce qui Reste Incertain
- [Point non résolu 1]
- [Point non résolu 2]

## Prochaines Étapes

1. [ ] [Action 1]
2. [ ] [Action 2]
3. [ ] [Action 3]

## Sources

### Papers Académiques
1. [Auteur et al. "Titre." Conférence, 2024.](lien)

### Documentation Officielle
1. [Nom de la lib - Topic](lien)

### Repos GitHub
1. [org/repo](https://github.com/org/repo) - [description]

### Benchmarks
1. [Source du benchmark](lien)

## Related

- [[note-technique-liée]]
- [[définition-tech]]
- [[howto-lié]]

---

*Recherche technique effectuée le {{date}} via /deep-research-tech*
