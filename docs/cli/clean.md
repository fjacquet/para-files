# clean

```bash
para-files clean [PATH] [--duplicates] [--apply]
```

Finds, under PATH (default: the whole PARA root):

- junk files: `.DS_Store`, `Thumbs.db`, `desktop.ini`, Office lock files (`~$…`) and AppleDouble files (`._…`);
- folders that are empty, or would be once the junk is gone;
- with `--duplicates`, files whose content is identical to another file (the first by path is kept).

With `--apply`, junk and duplicate copies go to `<PARA root>/.trash/<run id>/` and empty folders are removed. The run is journaled, so `para-files undo` reverses it. Secret files are never trashed. PATH must be inside the PARA root. Bucket folders and the leaf folders from `tree.yaml` are never removed, even when empty; dot-folders such as `.git` or `.trash` are never cleaned.
