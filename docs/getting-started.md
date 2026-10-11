---
title: Getting started
layout: default
nav_order: 2
---

# Getting started

From a clone to your first sorted folder, in about ten minutes. Nothing moves until you ask it to.

## 1. Install

```bash
git clone https://github.com/fjacquet/para-files.git
cd para-files
uv sync --all-extras
uv run para-files --version
```

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/). No local model server is needed.

## 2. Choose the PARA root

The PARA root is one folder that holds the buckets `0_Inbox`, `1_Projets`, `2_Areas`, `3_Resources` and `4_Archives`. Create the inbox; `init` creates the rest later.

```bash
mkdir -p ~/PARA/0_Inbox
mkdir -p ~/.config/para-files
echo 'PARA_FILES_PARA_ROOT=~/PARA' > ~/.config/para-files/.env
```

The settings loader reads `~/.config/para-files/.env`, so the root applies in every shell. An environment variable with the same name wins over the file.

## 3. Write the tree, one rule and one issuer

Three files live in `~/.config/para-files/`. This is a minimal, generic set; see [configuration](configuration.md) for every field.

`tree.yaml` lists the leaves, the only folders the tool may choose:

```yaml
leaves:
  payslips:
    kind: record
    retention: 10y
    path: 4_Archives/10y_travail
    subkey: "{year}"
    describe: "Payslips and employment records"
    keywords: [payslip]
  card_statements:
    kind: record
    retention: 10y
    path: 4_Archives/10y_banques
    subkey: "{issuer}/{year}"
    describe: "Bank and card statements"
    keywords: [statement]
  notes:
    kind: knowledge
    path: 3_Resources/notes
    describe: "Personal notes and reference text"
```

`rules.yaml` sends files by filename:

```yaml
rules:
  - name: payslips
    leaf: payslips
    globs: ["*payslip*"]
```

`issuers.yaml` names the issuers that appear inside documents:

```yaml
issuers:
  acmecard:
    patterns: [AcmeCard]
    leaves: [card_statements]
```

Check the configuration. It should report no warnings:

```bash
uv run para-files tree --validate
```

## 4. Create the missing folders

```bash
uv run para-files init            # lists the folders that do not exist yet
uv run para-files init --apply    # creates them; the run is journaled
```

## 5. Preview the sort

Put a few documents in `~/PARA/0_Inbox`, then preview:

```bash
uv run para-files sort
```

The plan groups every file by band: **GREEN** (safe to move), **YELLOW** (needs your confirmation) and **RED** (stays where it is). Secret-looking files are listed separately and are never sent or moved. Ask why a file lands where it does with `explain`:

```bash
uv run para-files explain ~/PARA/0_Inbox/some-file.pdf
```

## 6. Move the green files

```bash
uv run para-files sort --apply
```

The run is journaled and prints its run id.

## 7. Confirm the yellow files

```bash
uv run para-files sort --apply --review
```

For each yellow file, press Enter to accept, `s` to skip, `q` to stop, `?` to list the leaves, or type a leaf id to correct it. Each answer is recorded as your decision. Those decisions are what let issuer and model matches turn green later (see [architecture](architecture.md#bands-and-caps)).

## 8. Undo

```bash
uv run para-files undo            # reverses the last run that was not undone
uv run para-files undo 20261011-101500   # or a specific run id
```

Undo checks every step and leaves alone anything that changed since the run. See [troubleshooting](troubleshooting.md#undo-left-something-alone).

## Optional: the cloud model

Rules, books and issuers decide most files without any network call. For the rest, the tool can ask a model through [OpenRouter](https://openrouter.ai/). To enable it, add a key to `~/.config/para-files/.env`:

```bash
OPENROUTER_API_KEY=sk-or-...
```

Without a key the model is never asked. Every request asks OpenRouter for zero data retention (`zdr` on, data collection denied), and files that look secret are never sent. Model settings are in [configuration](configuration.md#settings).
