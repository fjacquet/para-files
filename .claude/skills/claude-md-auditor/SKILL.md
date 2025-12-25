---
name: claude-md-auditor
description: Audit and synchronize CLAUDE.md files with actual vault structure. Use when user asks to check/update/audit CLAUDE.md files, verify folder documentation accuracy, or after reorganizing the vault structure. Detects missing folders, removed folders, outdated file counts, and incorrect paths in CLAUDE.md documentation.
---

# CLAUDE.md Auditor

Audit and update CLAUDE.md files to match actual vault structure.

## Workflow

### 1. Scan Structure

```bash
# Find all CLAUDE.md files
find . -name "CLAUDE.md" -type f

# List actual subfolders for comparison
ls -d */
```

### 2. Compare Each CLAUDE.md

For each CLAUDE.md file:
1. Read the documented structure (tables, lists of folders)
2. List actual subfolders in that directory
3. Identify discrepancies:
   - **Missing**: Folder exists but not in CLAUDE.md
   - **Removed**: Documented in CLAUDE.md but folder doesn't exist
   - **Moved**: Folder relocated (check by name similarity)
   - **Counts**: File counts significantly outdated

### 3. Report Findings

Present discrepancies in a table:

| File | Issue | Details |
|------|-------|---------|
| `2_Areas/CLAUDE.md` | Removed | `openshift/` no longer exists |
| `3_Resources/CLAUDE.md` | Missing | `dell/` folder not documented |

### 4. Apply Updates

After user confirmation:
- Update folder structure tables
- Fix entry points sections
- Update file counts (use `~` prefix for approximate)
- Add/remove subfolder CLAUDE.md references

## Key Checks

### Structure Tables
Look for markdown tables with `| Folder |` or `| Dossier |` headers.

### Entry Points
Sections with `## Entry Points` or `## Key Entry Points` listing paths.

### Subfolder References
Sections mentioning other CLAUDE.md files to update cross-references.

### File Counts
Numbers in structure tables - verify with:
```bash
find <folder> -type f -name "*.md" | wc -l
```

## P.A.R.A. Context

| Folder | Purpose |
|--------|---------|
| `0_Inbox/` | Unsorted notes |
| `1_Projects/` | Active projects with goals |
| `2_Areas/` | Ongoing responsibilities |
| `3_Resources/` | Stable reference materials |
| `4_Archives/` | Completed/inactive content |

When folders move between Areas ↔ Resources, update both source and destination CLAUDE.md files.
