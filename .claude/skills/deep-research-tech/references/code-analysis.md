# Analyse de Code et Librairies

## Méthodologie d'Analyse

### 1. Vue d'Ensemble

Avant de plonger dans le code :

```
1. README.md         → Comprendre le but et l'usage
2. docs/             → Documentation détaillée
3. examples/         → Cas d'usage concrets
4. CHANGELOG.md      → Évolution et breaking changes
5. pyproject.toml    → Dépendances et versions
   / package.json
```

### 2. Architecture

Identifier la structure :

```
src/
├── core/           → Logique métier centrale
├── api/            → Interface publique
├── utils/          → Fonctions utilitaires
├── models/         → Modèles de données
└── tests/          → Suite de tests
```

### 3. Points d'Entrée

- `__init__.py` / `index.js` → Exports publics
- `main.py` / `cli.py` → Point d'entrée CLI
- `app.py` / `server.py` → Point d'entrée serveur

## Évaluation d'une Librairie

### Critères Techniques

| Critère | Comment vérifier | Score /5 |
|---------|------------------|----------|
| API Design | Intuitive, cohérente | |
| Documentation | Complète, exemples | |
| Type Hints | Annotations présentes | |
| Tests | Coverage, CI/CD | |
| Performance | Benchmarks, profiling | |
| Maintenance | Activité récente | |

### Critères Écosystème

| Critère | Comment vérifier | Score /5 |
|---------|------------------|----------|
| Popularité | Stars, downloads | |
| Communauté | Issues, discussions | |
| Maturité | Version, historique | |
| Alternatives | Comparaison | |
| Licence | Compatible projet | |

## Patterns à Identifier

### Design Patterns Courants

| Pattern | Usage | Exemple |
|---------|-------|---------|
| Factory | Création d'objets | `create_model()` |
| Singleton | Instance unique | Config, Logger |
| Strategy | Algorithmes interchangeables | Encoders |
| Observer | Événements | Callbacks, Hooks |
| Decorator | Extension comportement | `@cache`, `@retry` |
| Builder | Construction complexe | Query builders |

### Anti-Patterns à Repérer

| Anti-Pattern | Symptôme | Risque |
|--------------|----------|--------|
| God Object | Classe/fichier énorme | Maintenance difficile |
| Spaghetti | Dépendances circulaires | Bugs, tests difficiles |
| Magic Numbers | Constantes non nommées | Incompréhensible |
| Copy-Paste | Code dupliqué | Bugs synchronisés |
| Premature Optimization | Complexité inutile | Sur-ingénierie |

## Analyse de Performance

### Métriques Clés

| Métrique | Outil | Interprétation |
|----------|-------|----------------|
| Latence (P50, P99) | Profiler | Temps de réponse |
| Throughput | Benchmark | Requêtes/seconde |
| Mémoire | Memory profiler | Footprint, leaks |
| CPU | cProfile | Hotspots |
| I/O | Tracing | Bottlenecks |

### Complexité Algorithmique

| Notation | Exemple | Performance |
|----------|---------|-------------|
| O(1) | Accès dict | Excellente |
| O(log n) | Binary search | Très bonne |
| O(n) | Parcours liste | Bonne |
| O(n log n) | Tri efficace | Acceptable |
| O(n²) | Boucles imbriquées | Problématique |
| O(2^n) | Récursion naïve | Inacceptable |

## Comparaison de Librairies

### Template de Comparaison

```markdown
## Comparaison : [Lib A] vs [Lib B]

| Critère | Lib A | Lib B |
|---------|-------|-------|
| Version | x.y.z | x.y.z |
| Stars | N | N |
| Dernière release | Date | Date |
| Licence | MIT | Apache |
| Python versions | 3.8+ | 3.9+ |
| Dépendances | N | N |

### Performance
[Benchmarks comparatifs]

### API
[Comparaison des interfaces]

### Cas d'usage
- Lib A meilleure pour : [cas]
- Lib B meilleure pour : [cas]

### Recommandation
[Conclusion justifiée]
```

## Outils d'Analyse

### Documentation
- `mcp__context7__get-library-docs` : Docs à jour
- Sphinx, MkDocs : Docs générées

### Code Quality
- `ruff`, `flake8` : Linting Python
- `mypy` : Type checking
- `pylint` : Analyse statique

### Tests
- `pytest` : Framework de test
- `coverage.py` : Couverture de code

### Performance
- `cProfile` : Profiling CPU
- `memory_profiler` : Profiling mémoire
- `py-spy` : Sampling profiler

## Questions à Se Poser

### Avant d'Adopter une Librairie

1. **Besoin réel ?** → Existe-t-il une solution plus simple ?
2. **Maintenance ?** → Le projet est-il activement maintenu ?
3. **Licence ?** → Compatible avec mon projet ?
4. **Dépendances ?** → Tree de dépendances raisonnable ?
5. **Alternatives ?** → Ai-je comparé avec les alternatives ?
6. **Migration ?** → Sera-t-il facile de changer plus tard ?
7. **Communauté ?** → Support disponible si problème ?
