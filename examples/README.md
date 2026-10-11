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
