# sort

```bash
para-files sort [PATH…] [--apply] [--review] [--json] [-w N]
```

Classifies every file under the paths (default: `0_Inbox`) and prints the plan grouped by band. Nothing moves without `--apply`.

| Option | Effect |
|---|---|
| `--apply` | Move the green files |
| `--apply --review` | Also go through the yellow files one by one |
| `--json` | Print the plan (and the run, with `--apply`) as JSON |
| `-w N`, `--workers N` | Parallel classifiers (1–16) |

## The plan

The yellow section is grouped by proposed folder: each leaf id heads a group with its file count, biggest group first. Each file line shows its signal, its confidence and, when the model gave one, its short `about` text.

When some files are decided by hints alone (the model is off or did not answer), a footer says how many. Hint files are always yellow.

## JSON

`--json` returns `decisions` and `summary`. Each decision has:

| Key | Meaning |
|---|---|
| `ranked` | `[leaf, probability]` pairs, most likely first; the model's list is capped at three, hint lists are not (empty when nothing ranked a leaf) |
| `about` | The model's one-line description of the file, or `null` |

`summary` has the counts per band, `secrets`, `by_kind` and `by_signal`, the number of files per signal (for example `hint` and `secret`).

## Review

For each yellow file, `--review` shows the proposed leaf and why, then asks:

- **Enter**: accept the proposal;
- **s**: skip the file (it stays);
- **q**: stop reviewing (what you confirmed so far is applied);
- **?**: list the leaves;
- a **leaf id** (or a unique start of one): file it there instead.

`--review` needs a real terminal; through a pipe or an assistant's shell it stops with an error before classifying anything.

Every answer is journaled as a confirmed decision. `para-files tree` shows how many each kind has; at 100, issuers and the model may start moving files on their own.

## Secrets

Files that look like secrets (passwords, keys, recovery phrases, files in folders named like `credentials`) are listed under **SECRETS**. They are never sent to the model and never moved.

## Examples

```bash
para-files sort                          # preview the inbox
para-files sort --apply                  # move the green files
para-files sort --apply --review         # and confirm the yellow ones
para-files sort 4_Archives/factures      # preview one folder
para-files sort --json > plan.json
```
