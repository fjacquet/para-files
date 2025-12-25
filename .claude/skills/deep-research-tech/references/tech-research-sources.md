# Sources pour la Recherche Technique

## Sources Académiques

### Plateformes de Papers

| Source | Domaine | Fiabilité | Accès |
|--------|---------|-----------|-------|
| [arXiv](https://arxiv.org) | CS, ML, Physics | Haute (preprints) | Gratuit |
| [Semantic Scholar](https://semanticscholar.org) | Multi-domaines | Haute | Gratuit |
| [Google Scholar](https://scholar.google.com) | Tous | Variable | Gratuit |
| [ACL Anthology](https://aclanthology.org) | NLP | Très haute | Gratuit |
| [IEEE Xplore](https://ieeexplore.ieee.org) | Engineering | Très haute | Payant |
| [ACM Digital Library](https://dl.acm.org) | CS | Très haute | Payant |

### Conférences Majeures (peer-reviewed)

| Conférence | Domaine | Qualité |
|------------|---------|---------|
| NeurIPS | ML/AI | Top-tier |
| ICML | ML | Top-tier |
| ICLR | Deep Learning | Top-tier |
| CVPR/ICCV | Computer Vision | Top-tier |
| ACL/EMNLP | NLP | Top-tier |
| KDD | Data Mining | Top-tier |
| SIGMOD | Databases | Top-tier |

### Utilisation via MCP

```
mcp__hugging-face__paper_search
```

Recherche directe dans les papers ML/AI indexés par HuggingFace.

## Documentation Technique

### Utilisation de Context7

```
1. mcp__context7__resolve-library-id  → Trouver l'ID de la lib
2. mcp__context7__get-library-docs    → Obtenir la doc à jour
```

### Sources Officielles

| Type | Exemples | Fiabilité |
|------|----------|-----------|
| Docs officielles | React, Python, Kubernetes | Très haute |
| Blogs officiels | Google AI Blog, Meta AI | Haute |
| Changelogs | GitHub releases | Très haute |
| RFCs | IETF, W3C | Très haute |

### Sources Communautaires

| Type | Exemples | Fiabilité |
|------|----------|-----------|
| GitHub (>1k stars) | Repos populaires | Haute |
| Stack Overflow (votes) | Réponses acceptées | Moyenne-Haute |
| Reddit (r/MachineLearning) | Discussions | Moyenne |
| Hacker News | Actualités tech | Moyenne |

## Blogs Techniques de Référence

### Entreprises Tech

| Blog | Domaine | URL |
|------|---------|-----|
| Google AI Blog | ML/AI | ai.googleblog.com |
| Meta AI | ML/AI | ai.meta.com/blog |
| OpenAI Blog | LLMs | openai.com/blog |
| Anthropic | AI Safety | anthropic.com/news |
| AWS Architecture | Cloud | aws.amazon.com/blogs/architecture |
| Netflix Tech Blog | Infra | netflixtechblog.com |
| Uber Engineering | Infra | eng.uber.com |

### Blogs Individuels de Référence

| Auteur | Domaine | Fiabilité |
|--------|---------|-----------|
| Andrej Karpathy | ML/DL | Très haute |
| Lilian Weng | ML | Très haute |
| Jay Alammar | NLP/Transformers | Haute |
| Martin Fowler | Architecture | Très haute |
| Julia Evans | Linux/Networking | Haute |

## Évaluation des Repos GitHub

### Critères de Qualité

| Critère | Bon signe |
|---------|-----------|
| Stars | > 1000 |
| Dernière activité | < 6 mois |
| Issues ouvertes/fermées | Ratio sain |
| Documentation | README complet |
| Tests | CI/CD présent |
| Licence | MIT, Apache, BSD |
| Contributeurs | > 10 |

### Red Flags

- Pas de mise à jour depuis > 1 an
- Beaucoup d'issues sans réponse
- Pas de documentation
- Pas de tests
- Licence restrictive ou absente

## Benchmarks et Leaderboards

| Domaine | Ressource |
|---------|-----------|
| LLM | [Chatbot Arena](https://chat.lmsys.org) |
| NLP | [GLUE/SuperGLUE](https://gluebenchmark.com) |
| Vision | [ImageNet](https://image-net.org) |
| Code | [HumanEval](https://github.com/openai/human-eval) |
| Multi-modal | [MMLU](https://github.com/hendrycks/test) |

## Workflow de Recherche Tech

```
1. Identifier le sujet technique exact
   │
   ▼
2. Chercher papers récents (HuggingFace, arXiv)
   │
   ▼
3. Consulter documentation officielle (Context7)
   │
   ▼
4. Explorer repos GitHub populaires
   │
   ▼
5. Vérifier benchmarks/leaderboards
   │
   ▼
6. Croiser avec blogs techniques
   │
   ▼
7. Synthétiser avec état de l'art
```
