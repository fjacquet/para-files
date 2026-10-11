# Example configuration

para-files reads its personal configuration from `~/.config/para-files/` (override with `PARA_FILES_CONFIG_DIR`). These files are sanitized examples; copy them there and edit.

| File | Holds |
|---|---|
| `tree.yaml` | The closed list of leaves. Each has a `kind` (`record`, `library`, `media`, `knowledge`), a `path` and a one-line `describe`; records also carry a `retention` (`permanent`, `ret`, `10y`, `5y`, `2y`, `ctr`) |
| `rules.yaml` | Filename globs that send a file to a leaf |
| `issuers.yaml` | Issuer name patterns and the leaves their documents may go to |

Check a configuration:

```bash
uv run python -c "from para_files.core.tree import load_tree_config, validation_warnings; \
c = load_tree_config(); print(len(c.tree.leaves), 'leaves'); print(*validation_warnings(c), sep='\n')"
```

## Stage 1 tooling (developer scripts)

All scripts are read-only on the PARA root and write only into the config directory. Set `PARA` to your PARA root first.

```bash
uv run python scripts/migrate_config.py --para-root "$PARA"    # draft/ + review.md
uv run python scripts/build_golden.py --para-root "$PARA"      # golden.jsonl
uv run python scripts/run_baseline.py --para-root "$PARA"      # pred_baseline.jsonl
uv run python scripts/bakeoff.py --candidate jev --para-root "$PARA"   # pred_jev.jsonl
uv run python scripts/eval.py --pred ~/.config/para-files/pred_baseline.jsonl
uv run python scripts/eval.py --pred ~/.config/para-files/pred_jev.jsonl --only-predicted
```

The candidates (`gemini`, `sonnet`, `jev`; owner preference in that order) need `OPENROUTER_API_KEY` (or `PARA_FILES_LLM_API_KEY` in `.env`). Every request enforces zero data retention, and secret-looking files are never sent.
