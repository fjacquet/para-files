# explain

```bash
para-files explain FILE [--ask-model]
```

Shows the evidence read from the file, then the steps the cascade tried in order: `isbn book` (a verified ISBN), `pinned rule` (a `pin: true` or `pin: exif` rule), `hint` (each unpinned rule, heuristic book or issuer match that suggested a leaf) and `model`. The first step that decides is the verdict. A model answer also shows an `about:` line, the model's one-line description of the file. Then the resulting decision and which config entry to edit to change it. Changes nothing.

```text
steps:
  isbn book    no verified ISBN
  pinned rule  no pinned rule matches
  hint         resources_docs (1.00): rule 'broad' (glob '*card*')
  model        off (no key, or PARA_FILES_FALLBACK_ENABLED=false)
decision: yellow, resources_docs -> 3_Resources/docs
to change it: a rule or issuer suggested this; pin the rule if it is always right, or fix it
```

A hint is always yellow: it moves nothing with `sort --apply` until you confirm it with `--review`.

When `sort` already asked the model about this file, `explain` shows that cached answer without asking again, so its decision matches `sort`. Otherwise the model is asked only with `--ask-model`, since that sends the file name, type, metadata, the start of its text, the hints and examples of past decisions to the model (with zero data retention, and never for a secret file). For a secret file, only the reason it was flagged is shown.

```bash
para-files explain 0_Inbox/scan_0001.pdf
para-files explain 0_Inbox/scan_0001.pdf --ask-model
```
