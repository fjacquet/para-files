# para-files

**macOS-only (Apple Silicon)** intelligent file classification system using MLX-powered semantic routing.

Implements the PARA method (Projects, Areas, Resources, Archives) with a deterministic 5-signal classification pipeline.

## Requirements

- macOS with Apple Silicon (M1/M2/M3)
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/para-files.git
cd para-files

# Install dependencies
uv sync --all-extras
```

## Quick Start

```bash
# Set required configuration (see Configuration section)
export PARA_FILES_PARA_ROOT="/path/to/your/para/folder"

# Classify a file
uv run para-files classify document.pdf

# Classify multiple files
uv run para-files classify *.pdf

# JSON output
uv run para-files classify document.pdf --json
```

## CLI Commands

### classify

Classify one or more files using the PARA method.

```bash
# Single file
uv run para-files classify document.pdf

# Multiple files
uv run para-files classify file1.pdf file2.docx file3.txt

# With custom reference tree
uv run para-files classify document.pdf -r my_tree.yaml

# JSON output
uv run para-files classify document.pdf --json

# Verbose logging
uv run para-files classify document.pdf -v
```

### move

Classify and move one or more files to their PARA destinations.

```bash
# Move single file
uv run para-files move document.pdf

# Move multiple files
uv run para-files move file1.pdf file2.docx file3.txt

# Dry run (preview without moving)
uv run para-files move *.pdf --dry-run

# Copy instead of move
uv run para-files move document.pdf --copy

# Handle conflicts (skip, overwrite, rename, rename_with_date)
uv run para-files move document.pdf --conflict rename

# Add date prefix to filename
uv run para-files move document.pdf --date-prefix

# JSON output
uv run para-files move *.pdf --json
```

### scan

Scan a directory and preview file classifications without moving.

```bash
# Scan directory
uv run para-files scan ~/Downloads

# Recursive scan
uv run para-files scan ~/Downloads --recursive

# Filter by extensions
uv run para-files scan ~/Downloads --ext ".pdf,.docx"

# JSON output with statistics
uv run para-files scan ~/Downloads --json
```

### init

Initialize PARA folder structure from reference tree.

> **Note**: The `move` command automatically creates destination folders if they don't exist.
> Use `init` only for pre-creating the folder structure before any classification.

```bash
# Create PARA folders at default location
uv run para-files init

# Create at specific location
uv run para-files init /path/to/para

# Include subfolders from routes
uv run para-files init --subfolders

# Preview without creating
uv run para-files init --dry-run
```

### tree

Display and validate the reference tree structure.

```bash
# Show tree structure
uv run para-files tree

# Validate for errors/warnings
uv run para-files tree --validate

# Show known issuers
uv run para-files tree --issuers

# Show routing rules
uv run para-files tree --rules

# Verbose (show all issuers)
uv run para-files tree --issuers -v
```

### routes

List all available routes in the reference tree.

```bash
# List routes
uv run para-files routes

# Show utterances for each route
uv run para-files routes --utterances
```

### issuers

List all known issuers by category.

```bash
uv run para-files issuers
```

### add-issuer

Add a new issuer to the reference tree.

```bash
# Add issuer to category
uv run para-files add-issuer "New Bank SA" --category banques
```

### add-utterance

Add a new utterance to a route for better semantic matching.

```bash
# Add utterance to route
uv run para-files add-utterance factures-mobilite "Golden Pass Line"
```

### learn

Interactive classification learning from a file.

```bash
# Learn from a file interactively
uv run para-files learn document.pdf

# With custom reference tree
uv run para-files learn document.pdf -r my_tree.yaml

# Verbose mode
uv run para-files learn document.pdf -v
```

The learn command:
1. Classifies the file using the current pipeline
2. Shows the suggested route and confidence
3. Asks for confirmation or correction
4. Optionally adds new keywords to improve future matching

### test-route

Test a route's configuration and optionally match a file against it.

```bash
# Show route details
uv run para-files test-route factures-mobilite

# Test a file against a specific route
uv run para-files test-route factures-mobilite --file invoice.pdf

# Verbose mode shows more details
uv run para-files test-route factures-mobilite -v
```

### config

Show or initialize configuration.

```bash
# Show current configuration values
uv run para-files config --show

# Show config file path
uv run para-files config --path

# Create config directory and example file
uv run para-files config --init
```

## Configuration

Configuration is loaded from (in priority order):
1. Environment variables with `PARA_FILES_` prefix
2. `.env` file in current directory
3. TOML config file at `~/.config/para-files/config.toml`
4. Default values

### Required Settings

| Variable               | Description                                                        |
|------------------------|--------------------------------------------------------------------|
| `PARA_FILES_PARA_ROOT` | Root directory containing PARA folders (0_Inbox, 1_Projects, etc.) |

### MLX Model Configuration

The embedding model is **loaded lazily** on first classification. No manual download is needed - the model is fetched automatically from Hugging Face on first use.

| Variable                         | Default                               | Description                          |
|----------------------------------|---------------------------------------|--------------------------------------|
| `PARA_FILES_MLX_MODEL_NAME`      | `mlx-community/nomic-embed-text-v1.5` | MLX embedding model from HuggingFace |
| `PARA_FILES_MLX_SCORE_THRESHOLD` | `0.75`                                | Minimum similarity score (0.0-1.0)   |

### LLM Fallback Configuration (Optional)

| Variable                              | Default               | Description                      |
|---------------------------------------|-----------------------|----------------------------------|
| `PARA_FILES_LLM_ENABLED`              | `false`               | Enable LLM for ambiguous cases   |
| `PARA_FILES_LLM_MODEL`                | `ollama/qwen2.5:1.5b` | LLM model identifier for litellm |
| `PARA_FILES_LLM_CONFIDENCE_THRESHOLD` | `0.6`                 | Minimum LLM confidence           |
| `PARA_FILES_LLM_API_BASE`             | `null`                | API base URL (for Ollama, etc.)  |

### Other Settings

| Variable                           | Default                   | Description                        |
|------------------------------------|---------------------------|------------------------------------|
| `PARA_FILES_REFERENCE_TREE_PATH`   | `personal_file_tree.yaml` | Path to PARA reference tree YAML   |
| `PARA_FILES_VALIDATED_DB_PATH`     | `null`                    | Path to validated mappings JSON    |
| `PARA_FILES_CONTENT_PREVIEW_CHARS` | `2000`                    | Characters to extract for matching |

### Example `.env` File

```bash
# Required
PARA_FILES_PARA_ROOT=/Users/you/Documents/PARA

# Optional: Reference tree location
PARA_FILES_REFERENCE_TREE_PATH=/Users/you/.config/para-files/personal_file_tree.yaml

# Optional: Adjust similarity threshold
PARA_FILES_MLX_SCORE_THRESHOLD=0.80

# Optional: Enable LLM fallback with Ollama
PARA_FILES_LLM_ENABLED=true
PARA_FILES_LLM_API_BASE=http://localhost:11434
```

### Example `config.toml` File

Create with `uv run para-files config --init`:

```toml
# ~/.config/para-files/config.toml
para_root = "~/Documents/PARA"
reference_tree_path = "personal_file_tree.yaml"

[mlx]
model_name = "nomic-text-v1.5"
score_threshold = 0.75

[llm]
enabled = false
# model = "ollama/qwen2.5:1.5b"
# api_base = "http://localhost:11434"
```

## Model Loading

The MLX embedding model is loaded **lazily** - it downloads automatically on first use:

```python
from para_files.encoders import MLXEncoder

# Create encoder (model not loaded yet)
encoder = MLXEncoder(
    model_name="mlx-community/nomic-embed-text-v1.5",
    score_threshold=0.75,
)

# Model loads on first call (~100MB download, cached thereafter)
embeddings = encoder(["Hello world"])
```

The model is cached in `~/.cache/huggingface/` after first download.

### Programmatic Usage

```python
from pathlib import Path
from para_files.config import load_config
from para_files.pipeline import ClassificationPipeline

# Load config from environment
config = load_config()

# Or with explicit values
config = load_config(
    para_root=Path("/Users/you/PARA"),
    reference_tree_path=Path("personal_file_tree.yaml"),
)

# Create pipeline (lazy initialization)
pipeline = ClassificationPipeline(config)

# Classify a file
result = pipeline.classify_file(Path("document.pdf"))

print(f"Category: {result.category}")
print(f"Confidence: {result.confidence.value:.0%}")
print(f"Source: {result.confidence.source.value}")
```

## Architecture

### 5-Signal Classification Pipeline

Files are classified using signals in priority order (first match wins):

| Signal             | Confidence   | Description                                      |
|--------------------|--------------|--------------------------------------------------|
| 1. Validated DB    | 100%         | Manual sender/issuer → category mappings         |
| 2. Rules Engine    | 95%          | Glob patterns on filename/path/domain            |
| 3. Domain KB       | 90%          | Known domain/issuer to category mappings         |
| 4. Semantic Router | 85%          | MLX embedding similarity to reference categories |
| 5. LLM Fallback    | Configurable | Optional AI for ambiguous cases                  |

### MLX Stack

- **Embeddings**: `nomic-embed-text-v1.5` via `mlx-community` (~100MB, 10-15ms latency)
- **Semantic Router**: Custom implementation with cosine similarity
- **SLM Fallback**: Optional Qwen 2.5-1.5B-Instruct via Ollama
- **OCR**: Vision Framework (Apple Neural Engine) - coming soon

### Reference Tree

The `personal_file_tree.yaml` defines:
- PARA folder structure with paths
- Semantic utterances for each category (used for embedding matching)
- Special routing rules (photos by date, courses by platform)
- Known issuers database (banks, insurance, utilities)

## Development

```bash
# Install with dev dependencies
uv sync --all-extras

# Run linter
uv run ruff check src/ tests/

# Run formatter
uv run ruff format src/ tests/

# Run type checker
uv run mypy src/

# Run tests
uv run pytest -v

# Run all checks
uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run mypy src/ && uv run pytest
```

## Project Structure

```text
para-files/
├── src/para_files/
│   ├── __init__.py
│   ├── main.py              # CLI entry point
│   ├── config.py            # Configuration management
│   ├── pipeline.py          # 5-signal classification orchestrator
│   ├── reference_tree.py    # YAML reference tree loader
│   ├── types.py             # Data types and models
│   ├── classifiers/         # Classification signals
│   │   ├── validated_db.py  # Signal 1: Manual mappings
│   │   ├── rules_engine.py  # Signal 2: Glob patterns
│   │   ├── domain_kb.py     # Signal 3: Known issuers
│   │   ├── semantic_router.py  # Signal 4: MLX embeddings
│   │   └── llm_fallback.py  # Signal 5: LLM fallback
│   ├── encoders/
│   │   └── mlx_encoder.py   # MLX embedding encoder
│   └── utils/
│       └── file_utils.py    # File content extraction
├── tests/
├── personal_file_tree.yaml  # PARA reference tree
└── pyproject.toml
```

## License

MIT
