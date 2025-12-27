---
title: CLI Reference
layout: default
nav_order: 3
has_children: true
---

# CLI Reference

Complete reference for all para-files commands.

## Command Categories

| Category | Commands | Purpose |
|----------|----------|---------|
| **Classification** | `classify`, `scan` | Determine file categories |
| **Movement** | `move`, `clean` | Organize files into PARA folders |
| **Learning** | `learn`, `add-issuer`, `add-utterance` | Improve classification accuracy |
| **Configuration** | `init`, `config`, `tree` | Setup and view settings |
| **Inspection** | `routes`, `issuers`, `test-route` | Debug and inspect routing |

## Quick Reference

```bash
# Classification
para-files classify document.pdf      # Classify single file
para-files scan ~/Downloads           # Scan directory

# Movement
para-files move *.pdf --dry-run       # Preview moves
para-files move *.pdf                  # Execute moves

# Learning
para-files learn document.pdf         # Interactive learning
para-files add-issuer "Bank" -c banques

# Configuration
para-files init                        # Initialize config
para-files config                      # Show current config
```

See individual command pages for detailed usage.
