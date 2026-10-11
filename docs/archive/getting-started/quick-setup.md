---
title: Quick Setup (5 minutes)
layout: default
parent: Getting Started
nav_order: 2
---

# Quick Setup (5 minutes)

Get para-files working in just 5 minutes.

## Step 1: Create PARA Folder Structure

Choose where you want your PARA folders:

```bash
# Create PARA folder (if it doesn't exist)
mkdir -p ~/Documents/PARA

# Auto-create folder structure on first use, or manually:
uv run para-files init ~/Documents/PARA
```

This creates:

- `0_Inbox/` - Unclassified files
- `1_Projects/` - Active projects
- `2_Areas/` - Ongoing responsibilities
- `3_Resources/` - Reference material
- `4_Archives/` - Completed projects

## Step 2: Set PARA_ROOT

Point para-files to your PARA folder:

```bash
# Option A: Export environment variable
export PARA_FILES_PARA_ROOT=~/Documents/PARA

# Option B: Create .env file
cat > .env << EOF
PARA_FILES_PARA_ROOT=~/Documents/PARA
EOF

# Option C: Add to your shell profile
echo 'export PARA_FILES_PARA_ROOT=~/Documents/PARA' >> ~/.zshrc
source ~/.zshrc
```

## Step 3: Verify Configuration

```bash
uv run para-files config --show
```

Should output your PARA_ROOT and other settings.

## Step 4: Classify Your First File

```bash
# Test classification (doesn't move anything)
uv run para-files classify ~/Downloads/some-document.pdf

# See the result
```

## Step 5: Move Your First File (Optional)

```bash
# Preview where it will go
uv run para-files move ~/Downloads/some-document.pdf --dry-run

# Actually move it
uv run para-files move ~/Downloads/some-document.pdf
```

## What's Next?

- **[First Classification](first-file.md)** - More detailed walkthrough
- **[All CLI Commands](../cli/overview.md)** - See what you can do
- **[Task Guides](../tasks/)** - How-to guides for specific tasks
- **[Full Configuration](../configuration/overview.md)** - Advanced settings

## Common Issues

**"PARA_FILES_PARA_ROOT not set"?**

```bash
# Check it's exported
echo $PARA_FILES_PARA_ROOT

# If empty, you may need to set it in current terminal:
export PARA_FILES_PARA_ROOT=~/Documents/PARA
```

**Wrong Python version?**

```bash
# Check Python version
python3 --version  # Should be 3.12+

# Use uv to manage Python versions
uv python install 3.12
```

**MLX model downloading slowly?**
It's normal on first run (~100MB). The model is cached after that.
