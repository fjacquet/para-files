# undo

```bash
para-files undo [RUN_ID]
```

Reverses a run (default: the last one not yet undone) by replaying its journal backwards. Each step is checked first: a file is put back only if it still has the content the run recorded and its old place is free; a folder is removed only if it is empty. Anything else is left alone and listed. A folder that still holds other files is kept (`kept <folder>: folder not empty`) and does not keep the run from being marked undone. Running `undo` again on a partly undone run is safe: files already back in place are not touched.

Journals live in `~/.local/state/para-files/journal/`. `sort --apply` and `clean --apply` print the run id to undo.
