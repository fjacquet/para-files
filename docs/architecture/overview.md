---
title: Architecture Overview
layout: default
parent: Architecture
nav_order: 1
---

# Architecture Overview

Understanding how para-files classifies documents.

## The 4-Signal Pipeline (v2.0)

Para-files tries 4 classification signals in order. The first confident match wins.

```mermaid
flowchart TD
    A[Input File] --> B{Signal 1: Rules Engine<br/>95% confidence}
    B -->|Match| Z[Classification Result]
    B -->|No Match| C{Signal 2: Book Detector<br/>92% confidence}
    C -->|Match| Z
    C -->|No Match| D{Signal 3: Taxonomy Classifier<br/>90% confidence}
    D -->|Match| Z
    D -->|No Match| E{Signal 4: MLX-LLM Fallback<br/>60% confidence}
    E -->|Match| Z
    E -->|No Match| G[Inbox Fallback<br/>0_Inbox/]
    G --> Z
```

## Signal Details (v2.0)

| Signal | Confidence | What It Does | Data Source |
|--------|-----------|-------------|-------------|
| **1. Rules Engine** | 95% | Matches extensions/patterns | `personal_file_tree.yaml` |
| **2. Book Detector** | 92% | Detects books via ISBN + Thema | `thema.json` hierarchy |
| **3. Taxonomy Classifier** | 90% | Matches keywords + issuers | `documents.json` |
| **4. MLX-LLM Fallback** | 60% | Native MLX-LM inference | In-process (no Ollama) |

### Removed in v2.0

| Signal | Replaced By |
|--------|-------------|
| Validated DB | Taxonomy Classifier (issuers) |
| Domain KB | Taxonomy Classifier (issuers) |
| Semantic Router | Taxonomy Classifier (keywords) |
| LLM Fallback (Ollama) | MLX-LLM Fallback (native) |

## How to Improve Matching

Choose based on your situation:

- **Photo/video routing** → Add extension patterns to `personal_file_tree.yaml`
- **From known companies** → Add issuer to `documents.json`
- **Document type detection** → Add keywords to `documents.json`
- **Technical books** → Automatic via ISBN lookup + Thema classification

## Component Architecture

```mermaid
graph LR
    A["CLI<br/>main.py"]
    B["ClassificationPipeline<br/>Orchestrator"]

    C["4 Signals<br/>Classifiers"]
    D["Taxonomies<br/>JSON Loaders"]
    E["Reference Tree<br/>YAML Config"]

    A --> B
    B --> C
    B --> D
    B --> E
    C --> D
```

## Data Flow

```
File Input
    ↓
Extract Metadata (filename, content, dates)
    ↓
Try Signal 1 → 2 → 3 → 4
    ↓
Return Result (category + confidence + source)
    ↓
Action (classify, move, etc.)
```

## Key Technologies

- **MLX-LM** - Native LLM inference on Apple Silicon (replaces Ollama)
- **JSON Taxonomies** - `documents.json` (issuers + keywords), `thema.json` (books)
- **YAML Reference Tree** - Routing rules by extension/pattern
- **Pydantic** - Type-safe taxonomy models

## Next Steps

Learn about each signal:

- **[Signal 1: Rules Engine](signal-1-rules.md)** - Extension/pattern matching
- **[Signal 2: Book Detector](signal-2-book-detector.md)** - ISBN + Thema classification
- **[Signal 3: Taxonomy Classifier](signal-3-taxonomy.md)** - Keywords + issuers
- **[Signal 4: MLX-LLM Fallback](signal-4-mlx-llm.md)** - Native AI inference
