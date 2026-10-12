---
title: Troubleshooting
layout: default
nav_order: 6
---

# Troubleshooting

Start with the two commands that show the state of things: `para-files tree --validate` for configuration and calibration, and `para-files explain FILE` for one file. Both change nothing.

## Settings and the PARA root

| Symptom | Cause | Fix |
|---|---|---|
| `para_root has no 0_Inbox folder` | `PARA_FILES_PARA_ROOT` points at a folder without the inbox | Point it at the folder that holds `0_Inbox`, or create `0_Inbox` in it |
| `para_root points at a bucket (2_Areas)` | The variable names a bucket, not the root | Use the parent folder, the one that holds all five buckets |
| `no usable PARA root in the settings` (from `init`) | The variable is unset or invalid | Set `PARA_FILES_PARA_ROOT` in the environment or in `~/.config/para-files/.env`, or pass the root to `init` |
| `<setting>: Input should be less than or equal to 16` (or similar) | A setting is outside its allowed range | See the ranges in [configuration](configuration.md#settings) |
| `sort` uses a root you did not expect | An environment variable overrides `.env` | `env | grep PARA_FILES` shows what is set |
| `--review asks questions and needs a terminal` | stdin is not a terminal | run it in a terminal window |

## Config files

| Symptom | Cause | Fix |
|---|---|---|
| `tree.yaml: file not found` | No config in the config directory | Create it, or set `PARA_FILES_CONFIG_DIR` to the folder that has it |
| `tree.yaml: ... Field required` or `Extra inputs are not permitted` | A leaf is missing a field or has an unknown one | Compare with the table in [configuration](configuration.md#treeyaml) |
| `path needs a 1_-4_ bucket` | A leaf path starts with `0_Inbox` or has no bucket | Leaves live under `1_` to `4_`, never in the inbox |
| `retention 10y requires 4_Archives/10y_<name>` | A retention path is not under `4_Archives` with the matching prefix | Set `path: 4_Archives/10y_<name>` |
| `rules.yaml: rule 'x' points to unknown leaf 'y'` | The rule names a leaf that is not in `tree.yaml` | Fix the leaf id, or add the leaf |
| `issuers.yaml: pattern 'x' is used by issuers 'a' and 'b'` | The same pattern is listed under two issuers | Keep it under one issuer |

Run `para-files tree --validate` after each change. Its warnings are not fatal, but each one usually means a rule or leaf is not doing what you intended.

## Nothing goes green

Usually this is not a fault. Three things keep files yellow:

- **Unpinned rules are hints.** A rule without `pin: true` (or `pin: exif` with an EXIF date) never moves a file alone; it is shown to the model, and without a model answer it is a yellow suggestion. Pin the rules you trust in `rules.yaml`.
- **Calibration.** Model matches stay **yellow** until the kind of the leaf (record, library, media or knowledge) has 100 decisions you confirmed (`PARA_FILES_CALIBRATION_MIN`). Then a model match is green only at confidence 0.9 or more (`PARA_FILES_FALLBACK_GREEN`).
- **Kind caps.** **Knowledge** leaves are never green. **Library** leaves are green only with a verified ISBN or an issuer match, so a pinned library rule stays yellow.

Pinned rules on records and media are green at once.

Check the counts:

```bash
uv run para-files tree
```

The calibration section lists confirmed decisions and how often the proposal was right, per kind. To build them up, confirm yellow files with `sort --apply --review`. Each confirmation counts, including confirmations of files that were already in the right place.

## A file stays red

Red means the tool has no leaf for it, or it must not be moved. Ask it why:

```bash
uv run para-files explain ~/PARA/0_Inbox/some-file.pdf
```

`explain` lists each step the cascade tried (`isbn book`, `pinned rule`, `hint`, `model`), then the decision and the edit that would change it. Common causes:

| Output says | Meaning | Fix |
|---|---|---|
| `decision: red, no leaf` and no signal matched | No rule, issuer or ISBN applies | Add a rule in `rules.yaml` or an issuer in `issuers.yaml` for files like this |
| `secret (...)` | The file looks secret; it is never sent or moved | Keep it local. If the name is a false positive (for example `Secretariat`), rename the file |
| `model` with a low probability, `decision: red` | The model was unsure (below `PARA_FILES_FALLBACK_RED`, 0.3) | Add a pinned rule or an issuer so the decision is deterministic |
| `model  off (no key, or PARA_FILES_FALLBACK_ENABLED=false)` or `model  not asked (use --ask-model)` | `explain` does not call the model unless asked, or the model is off | Use `explain --ask-model`, which sends the file name, type, metadata, text preview, hints and examples of past decisions to OpenRouter, with zero data retention and never for a secret file; for "off", set the key |

A file can also be red because it cannot be read (the plan shows `cannot read`). Check its permissions.

## The model is never asked

`tree` prints the fallback state. It is off when `PARA_FILES_FALLBACK_ENABLED=false`, and shows `key not set` when no key is found. Also check:

- **Secret files** are never sent, whatever the setting.
- **Circuit breaker:** after three files in a row for which both models failed, the model is skipped for the rest of that run. Look for `fallback ... failed` warnings in the output, check the network and the key, then run again.
- **Privacy refusal:** every request demands zero data retention. A model that cannot meet that fails and is not used.

## The model was not asked

A file is decided by hints only when no verified ISBN or pinned rule decides it and the model gave no answer. The plan then ends with a footer:

```text
3 files decided by hints only (model off or did not answer)
```

Those files are yellow. The footer covers three cases: no `OPENROUTER_API_KEY` (or `PARA_FILES_FALLBACK_ENABLED=false`), the model failed on the file, or the circuit breaker is open for the rest of the run. Check `para-files tree`, whose `fallback` line says `(key not set)` when no key is found, then the warnings above.

## Secrets

Secret files are listed under their own heading in the plan and are never sent to the model, moved or trashed. The guard matches:

- names containing terms such as `password`, `secret`, `token`, `api key`, `login`, `recovery phrase`, `.env`, `id_rsa`, `.pem`, `.kdbx`;
- folders and archive entries with those names;
- content with a labelled credential (`password: ...`), a private key block, a cloud access key or a vault key.

The name rule over-flags on purpose. There is no override: a flagged file stays where it is, and keeping it out of the cloud is the point. Rename it if the name is a false positive.

## Plan and apply

| Symptom | Cause | Fix |
|---|---|---|
| `nothing to move` | No green file, and no yellow file confirmed | Review yellow files with `--review`, or fix the red ones with `explain` |
| `skipped ...: changed since the preview` | The file's content changed after the plan | Run `sort` again |
| `skipped ...: source missing` | The file moved or was replaced | Run `sort` again |
| `skipped ...: already in place` | The file is already in its target folder | Nothing to do; a confirmed one is still recorded |
| `skipped ...: target outside the PARA root` | A leaf or subfolder resolves outside the root (for example through a symlink) | Fix the leaf path or the folder |
| `dot-folders are never sorted` | The path is inside a folder that starts with `.` | Sort the folder itself, not a dot-folder |
| `... is a bucket` (from `init`) | `init` was given a bucket folder | Pass the folder that holds the buckets |
| Files in the inbox are never picked up | Dotfiles, `~$` Office lock files, symlinks and dot-folders are skipped on purpose | Rename or move them out of the way |

## Undo left something alone

`undo` reports each step it did not reverse:

```text
left alone <path>: missing
left alone <path>: changed since the run
left alone <path>: source path taken
kept       <folder>: folder not empty
```

| Reason | Meaning |
|---|---|
| `missing` | The file is no longer where the run left it |
| `changed since the run` | Its content differs from the journal, so it is not put back |
| `source path taken` | Something new is at the original location; nothing is overwritten |
| `folder not empty` | A folder the run created now holds other files; it is kept and does not stop the run from being marked undone |

Steps not listed were reversed without a message. A file already back at its original place with the recorded content counts as restored, so running `undo` again after a partial run is safe. A run with a skipped file is not marked undone, so `undo` still targets it; fix the cause, then run `para-files undo <run id>` again. Journals are in `PARA_FILES_STATE_DIR/journal/`.

## Clean

| Message | Cause |
|---|---|
| `clean only works inside the PARA root` | The folder given is outside the root |
| `clean never works inside dot-folders` | The folder is `.git`, `.trash` or similar |
| `skipped ...: now a symlink` | An empty folder in the plan was replaced by a symlink before `--apply`; it is left alone |
| `clean` prints a plan and nothing moves | Expected: `clean` previews until you add `--apply` |

## Still stuck

Run the command with `--json` where it is offered (`sort`), attach the output with the paths anonymised, and open an issue at [github.com/fjacquet/para-files](https://github.com/fjacquet/para-files/issues).
