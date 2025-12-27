---
title: Path Configuration
layout: default
parent: Configuration
nav_order: 7
---

# Path Configuration

Configure where para-files finds its reference tree and validated database.

## REFERENCE_TREE_PATH

Path to your YAML reference tree file.

### Default

```
config/personal_file_tree.yaml
```

### Set Custom Path

```bash
# Environment variable
export PARA_FILES_REFERENCE_TREE_PATH=~/.config/my_tree.yaml

# .env file
PARA_FILES_REFERENCE_TREE_PATH=~/.config/my_tree.yaml

# YAML config (in the tree itself)
config:
  reference_tree_path: "~/.config/my_tree.yaml"
```

### When to Customize

Use when:
- You have multiple reference trees
- You store config elsewhere
- You want to share between projects

### Examples

```bash
# Use tree from config directory
export PARA_FILES_REFERENCE_TREE_PATH=~/.config/para-files/tree.yaml

# Use tree from project
export PARA_FILES_REFERENCE_TREE_PATH=~/Projects/my-org/para_tree.yaml

# Use absolute path
export PARA_FILES_REFERENCE_TREE_PATH=/etc/para-files/tree.yaml
```

## VALIDATED_DB_PATH

Path to JSON file with manual mappings you've approved.

### Default

```
null  # Disabled
```

### What Is Validated DB?

Manual sender/issuer → category mappings that you've explicitly approved.

This is the **highest confidence signal** (100% confidence, Signal 1).

### Set Validated DB

```bash
# Environment variable
export PARA_FILES_VALIDATED_DB_PATH=~/.config/para-files/validated.json

# .env file
PARA_FILES_VALIDATED_DB_PATH=~/.config/para-files/validated.json

# YAML config
config:
  validated_db_path: "~/.config/para-files/validated.json"
```

### Validated DB Format

JSON file with mappings:

```json
{
  "mappings": [
    {
      "from": "invoice@mybank.com",
      "to": "factures-utilities",
      "type": "email"
    },
    {
      "from": "UBS Switzerland",
      "to": "factures-banking",
      "type": "issuer"
    }
  ]
}
```

### When to Use

Use Validated DB when:
- You want 100% reliable mappings
- You're doing enterprise classification
- You want audit trail of approvals

Usually unnecessary—just use `learn` command instead.

## CONTENT_PREVIEW_CHARS

How much of file to read for content analysis.

### Default

```
2000  # characters
```

### Set Custom Value

```bash
export PARA_FILES_CONTENT_PREVIEW_CHARS=5000

# .env file
PARA_FILES_CONTENT_PREVIEW_CHARS=5000

# YAML config
config:
  content_preview_chars: 5000
```

### When to Adjust

- **Lower (500)**: Fast classification, less accurate
- **Higher (5000)**: Slower classification, more accurate
- **Default (2000)**: Good balance

## Examples

### Multiple Reference Trees

Keep different trees for different purposes:

```bash
# Personal files
uv run para-files classify -r ~/.config/personal_tree.yaml file.pdf

# Work email
uv run para-files classify -r ~/.config/work_tree.yaml email.pdf
```

### Custom Directory Structure

```bash
# Store config elsewhere
export PARA_FILES_REFERENCE_TREE_PATH=~/.config/para-files/tree.yaml
export PARA_FILES_VALIDATED_DB_PATH=~/.config/para-files/validated.json

uv run para-files classify file.pdf
```

## Verify Paths

```bash
# See which paths are configured
uv run para-files config --show

# See which file is actually being used
uv run para-files config --path
```

## Troubleshooting

**"Reference tree not found" error?**

```bash
# Check the path exists
ls -la ~/.config/para-files/tree.yaml

# Verify it's set correctly
uv run para-files config --path
```

**Wrong tree being used?**

```bash
# Environment variable overrides YAML config
# Unset if you want YAML config to be used:
unset PARA_FILES_REFERENCE_TREE_PATH

# Or use -r flag to specify directly:
uv run para-files classify -r /path/to/tree.yaml file.pdf
```

## Related

- **[Configuration Overview](overview.md)** - All configuration
- **[Reference Tree](../architecture/reference-tree.md)** - Tree structure
