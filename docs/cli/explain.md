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

The model is asked only with `--ask-model`, since that sends the file name and the start of its text to the model (with zero data retention). `explain` does not use the verdict cache, so its decision line can therefore differ from what `sort` did for a file that `sort` routed through the model. For a secret file, only the reason it was flagged is shown.

```bash
para-files explain 0_Inbox/scan_0001.pdf
para-files explain 0_Inbox/scan_0001.pdf --ask-model
```
