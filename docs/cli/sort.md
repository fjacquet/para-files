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

`--review` goes folder by folder: the yellow files proposed for the same leaf form one group, biggest group first. The group header shows the leaf, its folder and the file count.

**Groups:**

- **Enter**: accept the whole group;
- **o**: go through the group one by one;
- **s**: skip the whole group (its files stay);
- **q**: stop reviewing (what you confirmed so far is applied);
- **?**: list the leaves;
- a **leaf id** (or a unique start of one): send the whole group there.

**One by one:**

- **Enter**: accept the proposal;
- **2** / **3**: take the model's alternative (the other leaves it ranked, with their confidence);
- **s**: skip the file (it stays);
- **q**: stop reviewing;
- **?**: list the leaves;
- a **leaf id**: file it there instead.

Accepting a group counts every file in it as a confirmed decision.

`--review` needs a real terminal; through a pipe or an assistant's shell it stops with an error before classifying anything.

Every answer is journaled as a confirmed decision. `para-files tree` shows how many each kind has; at 100, the model may start moving files on its own (at confidence 0.9 or more).

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
