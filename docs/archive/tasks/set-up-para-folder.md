---
title: Set Up PARA Folder
layout: default
parent: Tasks
nav_order: 1
---

# Set Up PARA Folder Structure

Create your PARA folder structure and configure para-files.

## Step 1: Choose Location

Where should your PARA folders live?

```bash
# Option A: Default location
~/Documents/PARA

# Option B: Custom location
~/PARA
/Volumes/ExternalDrive/PARA
~/Dropbox/PARA  # For sync across devices
```

## Step 2: Create PARA Folder

```bash
# Create the directory
mkdir -p ~/Documents/PARA
```

## Step 3: Set PARA_ROOT

Tell para-files where your PARA folder is:

```bash
# Option A: Environment variable (temporary)
export PARA_FILES_PARA_ROOT=~/Documents/PARA

# Option B: .env file (permanent)
cat > .env << EOF
PARA_FILES_PARA_ROOT=~/Documents/PARA
EOF

# Option C: Add to shell profile (permanent)
echo 'export PARA_FILES_PARA_ROOT=~/Documents/PARA' >> ~/.zshrc
source ~/.zshrc
```

## Step 4: Create Folder Structure

Let para-files create the structure:

```bash
# Quick: Create basic structure
uv run para-files init

# Or: Include subfolders for all routes
uv run para-files init --subfolders
```

This creates:

```
PARA/
  0_Inbox/           - Unclassified files
  1_Projects/        - Active projects
  2_Areas/           - Ongoing responsibilities
  3_Resources/       - Reference material
  4_Archives/        - Completed items
```

## Step 5: Verify Setup

```bash
# Check configuration
uv run para-files config --show

# Should show your PARA_ROOT

# Check folder structure
ls -la ~/Documents/PARA/
```

## Step 6: Test First Classification

```bash
# Classify a test file
uv run para-files classify ~/Downloads/test_document.pdf

# See where it would go
uv run para-files move ~/Downloads/test_document.pdf --dry-run

# If satisfied, move it
uv run para-files move ~/Downloads/test_document.pdf
```

## Manual Folder Creation (Optional)

If you prefer to create folders manually:

```bash
mkdir -p ~/Documents/PARA/{0_Inbox,1_Projects,2_Areas,3_Resources,4_Archives}
```

Then para-files will use them automatically.

## Troubleshooting

**"Directory does not exist" error?**

```bash
# Create it first
mkdir -p ~/Documents/PARA

# Then set PARA_ROOT again
export PARA_FILES_PARA_ROOT=~/Documents/PARA
```

**PARA_ROOT not being used?**

```bash
# Check what's configured
uv run para-files config --show

# Verify PARA_FILES_PARA_ROOT matches
```

**Permission denied?**

```bash
# Check permissions
ls -ld ~/Documents/PARA

# Fix if needed
chmod 755 ~/Documents/PARA
```

## Next Steps

- **[Classify Your First File](../getting-started/first-file.md)** - Test it out
- **[Move Files](move-files.md)** - Batch operations
- **[Manage Issuers](manage-issuers.md)** - Improve matching
