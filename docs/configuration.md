---
title: Configuration
layout: default
nav_order: 4
---

# Configuration

para-files reads two kinds of configuration: **settings** (the PARA root, the model, thresholds, where the cache and journal live) and the **tree** (the folders it may choose, filename rules and issuers). Settings come from the environment. The tree comes from three YAML files in the config directory.

## Where it lives

| What | Where | Required |
|---|---|---|
| Config directory | `$PARA_FILES_CONFIG_DIR`, else `~/.config/para-files/` | no |
| Settings file | `<config dir>/.env` | no |
| Leaves | `<config dir>/tree.yaml` | yes |
| Filename rules | `<config dir>/rules.yaml` | no |
| Issuers | `<config dir>/issuers.yaml` | no |

The repository ships sanitized examples in [`examples/`](https://github.com/fjacquet/para-files/tree/main/examples). Copy them to your config directory and edit them.

Precedence for settings, highest first: init arguments (for example `sort --workers`), environment variables, `<config dir>/.env`, defaults. There is no YAML settings file and no `.env` in the working directory, so the result does not depend on where you run the command.

## Settings

Every setting is `PARA_FILES_` plus the upper-case field name, except the API key, which has its own names.

| Variable | Default | Meaning |
|---|---|---|
| `PARA_FILES_PARA_ROOT` | none (required) | The folder that holds `0_Inbox` to `4_Archives`. It must contain `0_Inbox` and must not be a bucket itself |
| `PARA_FILES_PREVIEW_CHARS` | `2000` (100 to 10000) | Characters of text read per file for the signals and the model |
| `PARA_FILES_MAX_WORKERS` | `4` (1 to 16) | Parallel classifiers; `sort --workers` overrides it |
| `PARA_FILES_FALLBACK_ENABLED` | `true` | Ask the model for every file that no verified ISBN or pinned rule decides |
| `PARA_FILES_FALLBACK_MODEL` | `google/gemini-3.8-flash` | First OpenRouter model asked |
| `PARA_FILES_FALLBACK_BACKUP_MODEL` | `anthropic/claude-sonnet-5.5` | Asked when the first model fails |
| `OPENROUTER_API_KEY` | none | OpenRouter key. Also accepted as `PARA_FILES_OPENROUTER_API_KEY` or `PARA_FILES_LLM_API_KEY`. Without a key the model is never asked |
| `PARA_FILES_CALIBRATION_MIN` | `100` (1 or more) | Confirmed decisions per kind before model matches can be green |
| `PARA_FILES_FALLBACK_GREEN` | `0.9` (0 to 1) | Confidence a model choice needs to be green, once calibrated |
| `PARA_FILES_FALLBACK_RED` | `0.3` (0 to 1) | A model choice below this confidence is red |
| `PARA_FILES_CACHE_PATH` | `~/.cache/para-files/cache.sqlite` | ISBN lookups and signal verdicts |
| `PARA_FILES_STATE_DIR` | `~/.local/state/para-files` | Run journals, in `journal/` |
| `PARA_FILES_CONFIG_DIR` | `~/.config/para-files` | Config directory (read directly, not a settings field) |

A value outside its range stops the command with a message naming the setting. `para-files tree` prints the effective settings, the fallback state and the calibration progress.

Example `.env`:

```bash
PARA_FILES_PARA_ROOT=~/PARA
PARA_FILES_MAX_WORKERS=6
OPENROUTER_API_KEY=sk-or-...
```

## tree.yaml

The closed list of leaves. Every rule, issuer and model choice must name one of these ids.

```yaml
leaves:
  payslips:
    kind: record
    retention: 10y
    path: 4_Archives/10y_travail
    subkey: "{year}"
    describe: "Payslips and employment records"
    keywords: [payslip]
  books:
    kind: library
    path: 3_Resources/livres
    subkey: "{thema}"
    describe: "Books and ebooks"
  photos:
    kind: media
    path: 4_Archives/photos
    subkey: "{year}/{month}"
    describe: "Photos"
  notes:
    kind: knowledge
    path: 3_Resources/notes
    describe: "Personal notes and reference text"
```

| Field | Required | Rule |
|---|---|---|
| leaf id (the key) | yes | Lower-case snake_case: a letter, then lower-case letters, digits or `_` |
| `kind` | yes | `record`, `library`, `media` or `knowledge` |
| `path` | yes | Starts with a `1_`, `2_`, `3_` or `4_` bucket. At most three segments (bucket plus two levels). No empty or space-padded segment |
| `describe` | yes | Non-empty. The model reads it to choose between leaves |
| `retention` | record only | Required for `record`, forbidden for other kinds. One of `permanent`, `ret`, `10y`, `5y`, `2y`, `ctr`. Any value except `permanent` needs a path `4_Archives/<retention>_<name>` |
| `subkey` | no | Up to two different placeholders from `{year}`, `{month}`, `{issuer}`, `{thema}`, joined by `/` |
| `keywords` | no | Strings. Their presence in the text picks a leaf among an issuer's leaves, and the model sees them |

Unknown fields are rejected in every file.

Subfolders are filled per file. `{year}` and `{month}` come from the EXIF date or a date in the filename (`2026` or `2026-03`); `{issuer}` from the issuer match; `{thema}` from the ISBN's Thema subject. If any placeholder cannot be filled, the file goes to the leaf's root folder.

## rules.yaml

Filename globs that send a file to one leaf.

```yaml
rules:
  - name: payslips
    leaf: payslips
    globs: ["*payslip*.pdf", "*salary statement*"]
    pin: true
  - name: photos
    leaf: photos
    globs: ["*.jpg", "*.heic"]
    pin: exif
```

| Field | Rule |
|---|---|
| `name` | Required, unique across rules |
| `leaf` | Required, an existing leaf id |
| `globs` | Required, at least one. Matched against the filename only, case-insensitively, after Unicode NFC normalization |
| `pin` | Optional, default `false`. `true` or `exif` (see below) |

The first rule in file order whose glob matches wins. A pinned rule on a `library` leaf stays yellow, because library is green only with an ISBN or an issuer match (see [architecture](architecture.md#bands-and-caps)).

### Pinning

| `pin` | Effect |
|---|---|
| `false` (default) | A hint for the model. The file is yellow and the model still decides the leaf |
| `true` | Decides alone: green, without asking the model. Knowledge and library leaves are capped at yellow (see [architecture](architecture.md#bands-and-caps)) |
| `exif` | Decides alone only when the file has an EXIF date (camera photos). Otherwise it behaves like `false` |

`para-files tree` shows how many rules are pinned per leaf.

## issuers.yaml

Names the issuers that appear in a document, and the leaves their documents may go to.

```yaml
issuers:
  acmecard:
    patterns: [AcmeCard, acmecard.example]
    leaves: [card_statements, invoices]
```

| Field | Rule |
|---|---|
| issuer name (the key) | Required |
| `patterns` | Required, at least one. Searched in the filename and the text preview, case-insensitively |
| `leaves` | Required, at least one existing leaf id. The one whose keywords match most wins |

A pattern of three characters or fewer matches whole words only, so `ABC` does not fire inside another word. When several patterns match, the longest wins. A pattern may belong to only one issuer.

## Validation

`para-files tree --validate` loads the three files and lists warnings. Errors stop every command that uses the tree.

### Errors

| Message | Cause |
|---|---|
| `<file>: file not found` | `tree.yaml` is missing |
| `<file>: invalid YAML`, `not valid UTF-8`, `expected a mapping` | The file cannot be read as a mapping |
| `<file>: <field>: <message>` | A field breaks a rule in the table above, or an unknown field is present |
| `rules.yaml: duplicate rule name 'x'` | Two rules share a name |
| `rules.yaml: rule 'x' points to unknown leaf 'y'` | A rule names a leaf not in `tree.yaml` |
| `issuers.yaml: issuer 'x' points to unknown leaf 'y'` | An issuer names a leaf not in `tree.yaml` |
| `issuers.yaml: pattern 'x' is used by issuers 'a' and 'b'` | One pattern belongs to two issuers |

Cross-file errors are reported together, separated by `;`.

### Warnings

| Warning | What to do |
|---|---|
| A glob with three or fewer literal characters | Make it more specific, for example `*payslip*` rather than `*pay*` |
| An issuer pattern of three or fewer characters | Check it matches only what you mean; short patterns match whole words only |
| A leaf no rule or issuer points to (knowledge leaves are exempt) | Add a rule or an issuer, or remove the leaf |
| Two leaves share a path | Give one of them a different path |
| A retention prefix such as `10y_` outside a `4_Archives` record | Move the leaf under `4_Archives`, or drop the prefix |
| A pinned rule (`pin: true`) on a knowledge leaf | Unpin it: knowledge is never green, so the pin only skips the model |
| A pinned (`pin: true`) glob that matches by extension only, such as `*.pdf`, on a non-media leaf | Narrow the glob to a name, or unpin the rule |
