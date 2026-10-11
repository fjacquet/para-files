# undo

```bash
para-files undo [RUN_ID]
```

Reverses a run (default: the last one not yet undone) by replaying its journal backwards. Each step is checked first: a file is put back only if it still has the content the run recorded and its old place is free; a folder is removed only if it is empty. Anything else is left alone and listed.

Journals live in `~/.local/state/para-files/journal/`. `sort --apply` and `clean --apply` print the run id to undo.
