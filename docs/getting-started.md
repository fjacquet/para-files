---
title: Getting Started
layout: default
nav_order: 3
---

# Getting Started

Complete guide for using para-files to organize your documents with the PARA method.

## What is para-files?

para-files is an intelligent file classification system that:

- **Classifies** your files using AI-powered semantic understanding
- **Organizes** them into the PARA folder structure (Projects, Areas, Resources, Archives)
- **Learns** from your feedback to improve accuracy

## Requirements

- macOS with Apple Silicon (M1/M2/M3/M4)
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

## Quick Start (5 minutes)

### Step 1: Install

```bash
# Clone the repository
git clone https://github.com/fjacquet/para-files.git
cd para-files

# Install dependencies
uv sync --all-extras
```

### Step 2: Configure

```bash
# Set your PARA folder location (required)
export PARA_FILES_PARA_ROOT="/Users/you/Documents/PARA"

# Or create a .env file
echo 'PARA_FILES_PARA_ROOT="/Users/you/Documents/PARA"' > .env
```

### Step 3: Your First Classification

```bash
# Classify a single file
uv run para-files classify invoice.pdf
```

Output:

```
invoice.pdf
  Category: 2_Areas/finances/factures
  Confidence: 85% (semantic_router)
```

## Understanding the PARA Structure

```
PARA Root/
├── 0_Inbox/          # Unprocessed items
├── 1_Projects/       # Active projects with deadlines
├── 2_Areas/          # Ongoing responsibilities
│   ├── finances/
│   ├── sante/
│   └── ...
├── 3_Resources/      # Reference materials
│   ├── livres/
│   ├── formations/
│   └── ...
└── 4_Archives/       # Completed/inactive items
    ├── photos/
    └── ...
```

## Essential Commands

### Classify Files

Preview where files would be organized:

```bash
# Single file
uv run para-files classify document.pdf

# Multiple files
uv run para-files classify *.pdf

# JSON output for scripting
uv run para-files classify document.pdf --json
```

### Move Files

Actually move files to their PARA destinations:

```bash
# Preview first (recommended!)
uv run para-files move document.pdf --dry-run

# Move with confirmation
uv run para-files move document.pdf

# Move all PDFs from Downloads
uv run para-files move ~/Downloads/*.pdf --dry-run
uv run para-files move ~/Downloads/*.pdf
```

### Scan Directories

Preview classifications for an entire directory:

```bash
# Scan Downloads
uv run para-files scan ~/Downloads

# Recursive scan with JSON output
uv run para-files scan ~/Downloads --recursive --json
```

### Clean Up Junk

Remove system files and empty directories:

```bash
# Preview what would be deleted
uv run para-files clean ~/Downloads --dry-run

# Actually clean
uv run para-files clean ~/Downloads
```

## Common Workflows

### Workflow 1: Process Your Downloads

```bash
# 1. Clean junk files first
uv run para-files clean ~/Downloads --dry-run
uv run para-files clean ~/Downloads

# 2. Preview classifications
uv run para-files scan ~/Downloads --recursive

# 3. Move files (with dry run)
uv run para-files move ~/Downloads/* --dry-run

# 4. If happy, actually move
uv run para-files move ~/Downloads/*
```

### Workflow 2: Improve Classification

When a file is misclassified:

```bash
# 1. Use learn command
uv run para-files learn document.pdf

# 2. Follow prompts to correct classification
# 3. Add new utterances if needed
uv run para-files add-utterance route-name "new keyword phrase"
```

### Workflow 3: Add Known Senders

If you receive documents from a specific company:

```bash
# Add the issuer to a category
uv run para-files add-issuer "New Insurance Co" --category assurances

# Now documents from this issuer will be auto-classified
```

## Understanding Classification Results

### Confidence Levels

| Source | Confidence | Meaning |
|--------|------------|---------|
| `validated_db` | 100% | Manual mapping you've confirmed |
| `rules_engine` | 95% | Matched a file pattern rule |
| `book_detector` | 92% | Detected as a technical book |
| `domain_kb` | 90% | Known issuer/domain |
| `semantic_router` | 85% | AI semantic similarity |
| `llm_fallback` | Variable | AI language model decision |

### Example Output Explained

```bash
$ uv run para-files classify bank-statement.pdf

bank-statement.pdf
  Category: 2_Areas/finances/banques/ubs
  Confidence: 90% (domain_kb)
  Signals:
    - validated_db: no match
    - rules_engine: no match
    - domain_kb: matched issuer "UBS" (category: banques)
```

**Translation**: The file was classified into your bank documents folder because "UBS" was recognized as a known banking issuer.

## Special Features

### Photo Organization

Photos with GPS data are organized by location:

```
4_Archives/photos/2024/Geneva/06/15/IMG_1234.jpg
```

### Book Detection

Technical PDFs are detected and organized by technology:

```
3_Resources/livres/python/effective-python.pdf
```

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PARA_FILES_PARA_ROOT` | Root folder for PARA structure | **Required** |
| `PARA_FILES_MLX_SCORE_THRESHOLD` | Min similarity score (0.0-1.0) | `0.75` |
| `PARA_FILES_LLM_ENABLED` | Enable LLM fallback | `false` |

### Example .env File

```bash
# Required
PARA_FILES_PARA_ROOT=/Users/you/Documents/PARA

# Optional: Adjust classification threshold
PARA_FILES_MLX_SCORE_THRESHOLD=0.80

# Optional: Enable LLM for ambiguous cases
PARA_FILES_LLM_ENABLED=true
PARA_FILES_LLM_API_BASE=http://localhost:11434
```

## Troubleshooting

### Files Not Being Classified

1. Check verbose output: `uv run para-files classify file.pdf -v`
2. Verify file can be read (not corrupted)
3. Try lowering threshold: `PARA_FILES_MLX_SCORE_THRESHOLD=0.6`

### Wrong Classification

1. Use learn command: `uv run para-files learn file.pdf`
2. Add new utterances for the correct route
3. Add issuer if it's from a specific company

### Command Not Found

```bash
# Make sure you're in the para-files directory
cd /path/to/para-files

# Use uv to run
uv run para-files --help
```

## Tips for Best Results

1. **Start with dry-run**: Always preview before moving files
2. **Teach the system**: Use `learn` command for misclassifications
3. **Add issuers**: Register companies you frequently receive documents from
4. **Keep utterances specific**: Use exact phrases from your documents
5. **Regular cleanup**: Run `clean` periodically on Downloads

## Getting Help

```bash
# General help
uv run para-files --help

# Command-specific help
uv run para-files classify --help
uv run para-files move --help

# Validate your reference tree
uv run para-files tree --validate

# Show current configuration
uv run para-files config --show
```
