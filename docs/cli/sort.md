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

## Review

For each yellow file, `--review` shows the proposed leaf and why, then asks:

- **Enter**: accept the proposal;
- **s**: skip the file (it stays);
- **q**: stop reviewing (what you confirmed so far is applied);
- **?**: list the leaves;
- a **leaf id** (or a unique start of one): file it there instead.

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
