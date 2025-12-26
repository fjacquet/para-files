---
title: Architecture
layout: default
nav_order: 2
---

# Architecture

para-files uses a **5-signal classification pipeline** where each signal is tried in priority order. The first classifier that returns a confident result wins.

## Pipeline Overview

```mermaid
flowchart TD
    A[Input File] --> B{Signal 1: Validated DB}
    B -->|Match| Z[Classification Result]
    B -->|No Match| C{Signal 2: Rules Engine}
    C -->|Match| Z
    C -->|No Match| D{Signal 3: Domain KB}
    D -->|Match| Z
    D -->|No Match| E{Signal 4: Semantic Router}
    E -->|Match| Z
    E -->|No Match| F{Signal 5: LLM Fallback}
    F -->|Match| Z
    F -->|No Match| G[Inbox Fallback]
    G --> Z
```

## Classification Signals

| Signal | Confidence | Description |
|--------|------------|-------------|
| **1. Validated DB** | 100% | Manual sender/issuer → category mappings from user feedback |
| **2. Rules Engine** | 95% | Glob patterns on filename, path, or sender domain |
| **3. Domain KB** | 90% | Known domain/issuer to category mappings from reference tree |
| **4. Semantic Router** | 85% | MLX embedding similarity to reference category utterances |
| **5. LLM Fallback** | Configurable | Optional AI classification for ambiguous cases |

## Component Architecture

```mermaid
graph LR
    subgraph CLI
        A[main.py]
    end

    subgraph Core
        B[ClassificationPipeline]
        C[Config]
        D[ReferenceTree]
    end

    subgraph Classifiers
        E[ValidatedDB]
        F[RulesEngine]
        G[DomainKB]
        H[SemanticRouter]
        I[LLMFallback]
    end

    subgraph Encoders
        J[MLXEncoder]
    end

    A --> B
    B --> C
    B --> D
    B --> E
    B --> F
    B --> G
    B --> H
    B --> I
    H --> J
```

## MLX Stack

- **Embedding Model**: `nomic-embed-text-v1.5` (768 dimensions, 8192 token context)
- **Library**: `mlx-embedding-models` for Apple Silicon optimization
- **Semantic Router**: `aurelio-labs/semantic-router` with custom MLX encoder
- **LLM Fallback**: Optional Qwen 2.5-1.5B via Ollama (requires separate setup)

## Reference Tree Structure

The `personal_file_tree.yaml` defines:

```yaml
config:
  para_root: "~/Documents/PARA"
  mlx:
    model_name: "nomic-text-v1.5"
    score_threshold: 0.75

routes:
  - name: factures-cloud
    path: 4_Archives/factures/{year}/_Cloud/{issuer}
    utterances:
      - "Netflix subscription invoice"
      - "Cloud storage billing"

issuers:
  banques:
    - "UBS Switzerland"
    - "Credit Suisse"
```

## Data Flow

1. **File Input**: User provides file path(s) to classify
2. **Metadata Extraction**: Filename, extension, dates, content preview
3. **Pipeline Cascade**: Each classifier tries to match in priority order
4. **Result**: Category path, confidence score, source classifier
5. **Action**: Move/copy file to PARA destination folder
