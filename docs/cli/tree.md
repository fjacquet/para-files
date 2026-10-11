# tree

```bash
para-files tree [--validate]
```

Prints the leaves from `tree.yaml` (path, id, kind, retention, how many rules and issuers point to each), the effective settings (the API key shows only as set or not set), and the calibration progress: per kind, how many decisions you confirmed in `sort --review` and how often the proposal was right.

`--validate` adds the config warnings: short globs and issuer patterns, leaves nothing points to, retention prefixes in the wrong place. Errors that stop the config from loading are always reported.
