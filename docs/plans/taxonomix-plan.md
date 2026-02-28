# Plan: Intégration Taxonomies JSON (documents.json + thema.json)

## Résumé

Simplifier et centraliser la classification para-files:

- **documents.json** - Source unique pour classification sémantique (catégories + keywords + issuers)
- **thema.json** - Classification internationale des livres (Thema v1.6)
- **personal_file_tree.yaml** - Réduit à ~100 lignes (config technique + routing par extension)

**Principes appliqués**: DRY, KISS, Functional Programming (python-dev skill)

## Pipeline Simplifié

```
Avant (6 signaux): ValidatedDB → Rules → BookDetector → DomainKB → SemanticRouter → LLM
Après (4 signaux): Rules → BookDetector+Thema → DocumentTaxonomy → LLM (optionnel)
```

**Supprimés**: ValidatedDB (remplacé par JSON), DomainKB (issuers dans JSON), SemanticRouter (keywords dans JSON)

| Signal | Source | Confiance | Condition |
|--------|--------|-----------|-----------|
| 1 | RulesEngine | 95% | Extensions/patterns (photos, videos, etc.) |
| 2 | BookDetector+Thema | 92-100% | ISBN présent → Thema hierarchy |
| 3 | DocumentTaxonomy | 90% | Keywords + Issuers matching |
| 4 | LLM Fallback | 60% | Optionnel |

## Nouvelle Structure documents.json

```json
{
  "taxonomy_metadata": { ... },
  "retention_rules": { ... },
  "categories": [
    {
      "id": "CAT_07_FINANCES_BANQUE",
      "name": "07. Finances & Banque",
      "para_pattern": "4_Archives/banques/{issuer}/{year}",
      "documents": [
        {
          "sub_id": "comptes_bancaires",
          "keywords": ["IBAN", "Relevé", "Carte de crédit"],
          "retention": "10_years",
          "issuers": [
            {"name": "PostFinance", "patterns": ["PostFinance", "postfinance.ch"]},
            {"name": "UBS", "patterns": ["UBS", "ubs.com"]},
            {"name": "BCV", "patterns": ["BCV", "bcv.ch", "5429324"]}
          ]
        }
      ]
    }
  ]
}
```

## Logique de Routage

### 1. Livres (ISBN présent)

```
ISBN → OpenLibrary subjects → Thema code → Hiérarchie
→ 3_Resources/livres/{TopLevel}/{Child}
Exemple: 3_Resources/livres/Informatique/Programmation
```

### 2. Documents (keywords + issuers)

```
Content → Match keywords/issuers → para_pattern + retention
→ {para_pattern} avec placeholders résolus
Exemple: 4_Archives/banques/UBS/2025
```

### 3. Règles techniques (YAML)

```
Extension/Pattern → routing_rules
→ 4_Archives/photos/{YYYY}/{MM}/{DD}
```

---

## Fichiers à Créer (5 fichiers)

### 1. `src/para_files/taxonomies/__init__.py`

Package + exports

### 2. `src/para_files/taxonomies/models.py`

Pydantic models (DRY - un seul fichier):

```python
class Issuer(BaseModel):
    name: str
    patterns: list[str]

class DocumentType(BaseModel):
    sub_id: str
    keywords: list[str]
    retention: str
    issuers: list[Issuer] = []

class DocumentCategory(BaseModel):
    id: str
    name: str
    para_pattern: str
    documents: list[DocumentType]

class ThemaCode(BaseModel):
    CodeValue: str
    CodeDescription: str
    CodeParent: str
```

### 3. `src/para_files/taxonomies/loader.py`

```python
class TaxonomyLoader:
    def load_documents(path: Path) -> list[DocumentCategory]
    def load_thema(path: Path) -> dict[str, ThemaCode]
```

### 4. `src/para_files/classifiers/taxonomy_classifier.py`

Classifier unique qui gère documents + issuers:

```python
class TaxonomyClassifier(BaseClassifier):
    """Remplace DomainKB + SemanticRouter."""

    def match_issuer(content: str) -> tuple[Issuer, DocumentType] | None
    def match_keywords(content: str) -> tuple[DocumentType, float] | None
    def classify(content, metadata) -> ClassificationResult | None
```

### 5. `src/para_files/classifiers/mlx_llm_classifier.py`

Remplace LLMFallback (Ollama) par MLX-LM natif:

```python
class MLXLLMClassifier(BaseClassifier):
    """LLM fallback via mlx-lm (pas Ollama)."""

    def __init__(self, model: str = "mlx-community/Qwen2.5-1.5B-Instruct-4bit"):
        self._model = None  # Lazy loading

    def _load_model(self):
        from mlx_lm import load, generate
        self._model, self._tokenizer = load(self._model_name)

    def classify(content, metadata) -> ClassificationResult | None:
        prompt = f"Classify this document into PARA category: {content[:500]}"
        response = generate(self._model, self._tokenizer, prompt)
        # Parse response to extract category
```

---

## Fichiers à Modifier

### 1. `config/documents.json` - Étendre avec issuers

Migrer tous les known_issuers du YAML:

```json
{
  "categories": [{
    "id": "CAT_07_FINANCES_BANQUE",
    "para_pattern": "4_Archives/banques/{issuer}/{year}",
    "documents": [{
      "sub_id": "comptes_bancaires",
      "issuers": [
        {"name": "PostFinance", "patterns": ["PostFinance"]},
        {"name": "UBS", "patterns": ["UBS", "ubs.com"]}
      ]
    }]
  }]
}
```

### 2. `config/personal_file_tree.yaml` - Simplifier (~100 lignes)

Garder uniquement:

```yaml
version: "2.0"
config:
  para_root: "~/OneDrive - Home/PARA"
  taxonomy:
    documents_path: "config/documents.json"
    thema_path: "config/thema.json"

routing_rules:
  photos:
    extensions: [".jpg", ".jpeg", ".png", ".heic"]
    destination: "4_Archives/photos/{YYYY}/{MM}/{DD}"
  videos:
    extensions: [".mp4", ".mov"]
    destination: "4_Archives/videos/{YYYY}/{MM}/{DD}"
  # ... autres règles par extension uniquement
```

**Supprimer**: known_issuers, routes/utterances, inbox/projects/areas/resources/archives

### 3. `src/para_files/pipeline.py` - Simplifier

```python
# Avant: 6 classifiers
# Après: 3 classifiers
self._classifiers = [
    RulesEngine(routing_rules),      # Extensions/patterns
    BookDetector(thema_codes),       # ISBN → Thema
    TaxonomyClassifier(categories),  # Keywords + Issuers
]
```

### 4. `src/para_files/classifiers/book_detector.py`

Ajouter support Thema pour générer le path hiérarchique.

### 5. `src/para_files/reference_tree.py` - Simplifier

Charger uniquement config + routing_rules depuis YAML.
Les taxonomies viennent du TaxonomyLoader.

### 6. `pyproject.toml` - Ajouter mlx-lm

```toml
dependencies = [
    "mlx-lm>=0.19",  # Pour LLM fallback natif
    # ... autres deps
]
```

### 7. Supprimer (plus utilisés)

- `src/para_files/classifiers/domain_kb.py` → remplacé par TaxonomyClassifier
- `src/para_files/classifiers/semantic_router.py` → remplacé par TaxonomyClassifier
- `src/para_files/classifiers/validated_db.py` → plus nécessaire
- `src/para_files/classifiers/llm_fallback.py` → remplacé par MLXLLMClassifier

---

## Tests à Créer

| Fichier | Tests |
|---------|-------|
| `tests/test_taxonomy_models.py` | Pydantic models validation |
| `tests/test_taxonomy_loader.py` | Load JSON, caching |
| `tests/test_taxonomy_classifier.py` | Keywords + issuers matching |
| `tests/test_book_detector_thema.py` | ISBN → Thema path |
| `tests/test_pipeline_simplified.py` | Integration 3 signaux |

Fixtures: `tests/fixtures/test_documents.json`, `tests/fixtures/test_thema.json`

---

## Séquence d'Implémentation (4 phases)

### Phase 1: Migration données (config/)

1. Étendre `documents.json` avec issuers du YAML
2. Simplifier `personal_file_tree.yaml` (~100 lignes)
3. Valider que les 2 fichiers sont cohérents

### Phase 2: Nouveau code (src/)

1. Créer `taxonomies/models.py` (Pydantic)
2. Créer `taxonomies/loader.py`
3. Créer `classifiers/taxonomy_classifier.py`
4. Modifier `book_detector.py` pour Thema

### Phase 3: Simplifier pipeline

1. Modifier `pipeline.py` (3 classifiers)
2. Modifier `reference_tree.py` (YAML minimal)
3. Supprimer `domain_kb.py`, `semantic_router.py`, `validated_db.py`

### Phase 4: Documentation

1. Mettre à jour `SKILL.md`
2. Mettre à jour `docs/`
3. Mettre à jour `CHANGELOG.md`

---

## Configuration MLX (pas Ollama)

Remplacer Ollama par MLX-LM pour le fallback LLM:

```yaml
config:
  mlx:
    # Embeddings (existant)
    embedding_model: "nomic-text-v1.5"

    # LLM Fallback (nouveau - remplace Ollama)
    llm_model: "mlx-community/Qwen2.5-1.5B-Instruct-4bit"
    llm_enabled: true
    llm_confidence: 0.6
```

**Modèles recommandés** (tous via mlx-lm):

- `mlx-community/Qwen2.5-1.5B-Instruct-4bit` - Rapide, petit (~1GB)
- `mlx-community/Phi-3.5-mini-instruct-4bit` - Bon équilibre (~2GB)
- `mlx-community/Llama-3.2-3B-Instruct-4bit` - Plus capable (~2GB)

**Avantage**: Pas de serveur Ollama, tout dans le même process Python.

---

## Nouveau Pipeline Final

```
1. RulesEngine (95%)        → Extensions/patterns techniques
2. BookDetector+Thema (92%) → ISBN présent → Thema hierarchy
3. TaxonomyClassifier (90%) → Keywords + Issuers matching
4. MLX-LLM Fallback (60%)   → Si rien ne matche, demander au LLM
5. Default → 0_Inbox
```

---

## Avantages de cette Approche

| Avant | Après |
|-------|-------|
| 1141 lignes YAML | ~100 lignes YAML |
| 6 classifiers | 4 classifiers |
| Issuers dupliqués | Source unique JSON |
| Utterances manuelles | Keywords structurés |
| Ollama (serveur externe) | MLX-LM (même process) |
| SemanticRouter toujours | SemanticRouter optionnel |
