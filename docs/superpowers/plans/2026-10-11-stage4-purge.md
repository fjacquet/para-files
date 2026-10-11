# Stage 4 — Purge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete everything the new CLI does not use (the old pipeline, local AI, Stage 1 scripts, unused dependencies, the 3.6 MB Thema file), ship the Thema folder names as package data, and finish the docs and ADRs, leaving a codebase about half its current size that passes its tests from a clean clone with no network.

**Architecture:** The CLI (`para_files.cli`) and the core (`para_files.core`) stay as they are. A few helpers they still borrow from old modules move into the core first: the config directory, the circuit breaker and the Thema lookup. After that, every module the CLI cannot reach is deleted in one task, with its tests. The order is moves (Tasks 1–2), then delete (Task 3), then dependencies (Task 4), then repo hygiene and docs (Tasks 5–6), then the exit check (Task 7).

**Tech Stack:** Python 3.12, uv, Typer, pydantic-settings, litellm, pytest, ruff, mypy, `importlib.resources`.

**Spec:** `docs/superpowers/specs/2026-10-10-para-files-redesign-design.md` (§5 Stage 4, §3 S6/S7, §4.1 package data)

## Decisions in this plan (owner reviews before execution)

| # | Decision | Why |
|---|---|---|
| D1 | `default_rules.yaml` is dropped, not shipped | Rules name `leaf_id`s, which are personal (they live in the owner's `tree.yaml`). A shipped rule file cannot know them. The owner's `rules.yaml` already carries the extension rules. The spec §4.1 is amended. |
| D2 | `thema_l1l2.json` holds only the 234 level-1/level-2 folder names. The subject-keyword map stays in Python (`core/thema.py`). | Thema codes are prefix-hierarchical: all 9,187 codes were checked and none breaks the rule, so a code's folders are its first one and two characters. The keyword map is code that is reviewed with code; JSON would add a loader and nothing else. |
| D3 | `scripts/` is deleted entirely, with `config/thema.json` and `config/documents.json` | The scripts were Stage 1 tooling: the golden corpus and bake-off were dropped on 2026-10-11, and the tree migration is done. After Task 1 no code reads either JSON file. Git history keeps them. |
| D4 | S1/S2 are read from `para-files tree` (the confirmation statistics), not `scripts/eval.py` | `eval.py` scores against the dropped golden corpus. `tree` already prints confirmed and right counts per kind (S2). S1 needs the misses deferred as M-7. |
| D5 | ADR-013 records the redesign and the end of local AI; it supersedes ADR-010. Its *Deciders* line says "Project owner". | Spec §5 Stage 4. No personal names in new files (S6). |

## Global Constraints

- Python 3.12+, `from __future__ import annotations` in every module, strict mypy, ruff with line length 100, `from loguru import logger` for logging.
- Public repo: generic names only in code, tests and docs (`AcmeCard`, `~/PARA`). No personal names, paths or folder names (S6).
- Model calls go through litellm (unchanged here).
- No new runtime dependency.
- Behaviour of the six commands does not change. Every `tests/test_cli_*.py` and `tests/test_core_*.py` test passes unchanged, except imports of moved names (listed per task).
- Gate before every commit: `uv run pytest -m "not slow" -o addopts="-ra --strict-markers --strict-config" -q`, `uv run ruff check src/ tests/`, `uv run ruff format --check src/ tests/`, `uv run mypy src/`. Until Task 3 deletes `scripts/`, also run `uv run ruff check scripts/`.
- Docs are updated in the same task as the change that makes them stale (owner rule: never deferred).
- Stage files explicitly. Never stage `.serena/`, `.rtk/` or `.superpowers/`. `uv.lock` is staged only in Task 4.
- Commit messages end with:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx
  ```
  Write each message to a file and use `git commit -F <file>`.

## Review Focus

1. **Installed package, not a repo checkout:** books still get their Thema folders when para-files runs from a wheel. The JSON must be a package resource, never a path relative to the repo. Task 1 tests the resource; Task 7 builds the wheel and checks that the file is in it.
2. **Existing library folders:** after the purge, a book's Thema folders are the same strings as before; otherwise books land in new twin folders. Task 1 compares old and new output for every Thema code before the old code is deleted.
3. **Personal config dir:** `PARA_FILES_CONFIG_DIR` and `~/.config/para-files/.env` are still honoured after `config_dir_path` moves (Task 2 test).
4. **Offline machine:** the full `uv run pytest`, including slow tests, passes from a clean clone with no network and no Ollama (S7). Task 7 runs it with the proxies pointed at a dead port.
5. **Untracking `.serena/` and `.claude/`:** the owner's local files must stay on disk. Task 5 uses `git rm --cached` and checks the files still exist.

---

### Task 1: Thema folders as package data (`core/thema.py`)

**Files:**
- Create: `src/para_files/core/thema.py`
- Create: `src/para_files/data/__init__.py`
- Create: `src/para_files/data/thema_l1l2.json` (generated in Step 3)
- Modify: `src/para_files/core/books.py:19` (import)
- Test: `tests/test_core_thema.py`

**Interfaces:**
- Consumes: `para_files.utils.thema_lookup` and `para_files.taxonomies` (old, still present), used only to generate and check the data.
- Produces:
  - `para_files.core.thema.lookup_thema_code(subjects: list[str]) -> str | None`
  - `para_files.core.thema.thema_to_para_path(code: str) -> str`
  - `para_files.core.thema.SUBJECT_TO_THEMA: dict[str, str]`

  Same names and behaviour as in `utils/thema_lookup.py`; Task 3 deletes the old module.

- [ ] **Step 1: Write the failing tests** in `tests/test_core_thema.py`:

```python
"""Thema subjects and folders shipped as package data (spec §4.1, plan Stage 4 Task 1)."""

from __future__ import annotations

from importlib.resources import files

from para_files.core.thema import _folders, lookup_thema_code, thema_to_para_path


def test_the_table_is_a_package_resource():
    assert files("para_files.data").joinpath("thema_l1l2.json").is_file()


def test_the_table_holds_only_level_one_and_two_codes():
    table = _folders()
    assert len(table) == 234
    assert all(1 <= len(code) <= 2 for code in table)
    assert all(name.startswith(f"{code}_") for code, name in table.items())


def test_the_most_specific_subject_wins():
    assert lookup_thema_code(["Computing", "Python"]) == "UMX"


def test_unknown_or_no_subjects_give_none():
    assert lookup_thema_code([]) is None
    assert lookup_thema_code(["qqqq"]) is None


def test_a_deep_code_uses_its_level_one_and_two_folders():
    table = _folders()
    assert thema_to_para_path("UMX") == f"3_Resources/livres/{table['U']}/{table['UM']}"


def test_a_level_one_code_gives_one_folder():
    assert thema_to_para_path("U") == f"3_Resources/livres/{_folders()['U']}"


def test_an_unknown_code_gives_the_library_root():
    assert thema_to_para_path("?") == "3_Resources/livres"
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/test_core_thema.py -q -o addopts=""`
Expected: FAIL with `ModuleNotFoundError: No module named 'para_files.core.thema'`.

- [ ] **Step 3: Generate the data from the old taxonomy**

Create `src/para_files/data/__init__.py`:

```python
"""Package data: files read through importlib.resources, never through repo paths."""
```

Run this once from the repo root (it writes the JSON; do not commit the snippet):

```bash
uv run python - <<'EOF'
import json
from pathlib import Path

from para_files.taxonomies.loader import get_taxonomy_loader
from para_files.taxonomies.models import _make_folder_name

taxonomy = get_taxonomy_loader().load_thema()
table = {
    code: _make_folder_name(entry)
    for code, entry in taxonomy.codes.items()
    if len(taxonomy.get_hierarchy(code)) <= 2
}
out = Path("src/para_files/data/thema_l1l2.json")
out.write_text(json.dumps(table, ensure_ascii=False, indent=0, sort_keys=True) + "\n", encoding="utf-8")
print(len(table), "codes,", out.stat().st_size, "bytes")
EOF
```

Expected: `234 codes,` and a size of about 10 KB.

- [ ] **Step 4: Write `src/para_files/core/thema.py`**

Copy these blocks verbatim from `src/para_files/utils/thema_lookup.py` into the place marked `# --- subject maps ---`:
- `COMPUTING_SUBJECT_MAP` through `HISTORY_SUBJECT_MAP` (lines 22–315);
- `SUBJECT_TO_THEMA` (lines 318–326);
- the comment banners between them.

Do not change any key or value.

```python
"""Thema book subjects (spec §4.1): subject keywords to a Thema code, and a code to folders.

Only the Thema level-1 and level-2 folder names ship, in ``data/thema_l1l2.json``, generated
once from Thema v1.6. Thema codes are prefix-hierarchical, so a code's level-1 and level-2
ancestors are its first one and two characters.
"""

from __future__ import annotations

import json
from functools import cache
from importlib.resources import files


LIBRARY = "3_Resources/livres"

# --- subject maps ---


@cache
def _folders() -> dict[str, str]:
    """Thema level-1 and level-2 code -> folder name, e.g. 'UB' -> 'UB_Programmation'."""
    text = files("para_files.data").joinpath("thema_l1l2.json").read_text(encoding="utf-8")
    table: dict[str, str] = json.loads(text)
    return table


def lookup_subject(subject: str) -> str | None:
    """Thema code for one subject: exact keyword first, then the first partial match."""
    wanted = subject.lower().strip()
    if wanted in SUBJECT_TO_THEMA:
        return SUBJECT_TO_THEMA[wanted]
    for key, code in SUBJECT_TO_THEMA.items():
        if key in wanted or wanted in key:
            return code
    return None


def lookup_thema_code(subjects: list[str]) -> str | None:
    """The most specific (longest) Thema code any subject maps to; the first wins a tie."""
    best: str | None = None
    for subject in subjects:
        code = lookup_subject(subject)
        if code and len(code) > len(best or ""):
            best = code
    return best


def thema_to_para_path(code: str) -> str:
    """Library path for a Thema code, e.g. '3_Resources/livres/U_Informatique/UB_Programmation'."""
    table = _folders()
    names = [table[prefix] for prefix in dict.fromkeys((code[:1], code[:2])) if prefix in table]
    return "/".join([LIBRARY, *names])
```

- [ ] **Step 5: Check the new module against the old one for every code**

Run:

```bash
uv run python - <<'EOF'
from para_files.core import thema as new
from para_files.utils import thema_lookup as old

taxonomy = old.get_thema_lookup().taxonomy
assert new.SUBJECT_TO_THEMA == old.SUBJECT_TO_THEMA
missing = sorted({c for c in old.SUBJECT_TO_THEMA.values() if taxonomy.get_code(c) is None})
assert not missing, missing
diff = [c for c in taxonomy.codes if new.thema_to_para_path(c) != old.thema_to_para_path(c)]
assert not diff, diff[:10]
for subjects in (["Python"], ["Computing", "devops"], ["histoire"], []):
    assert new.lookup_thema_code(subjects) == old.lookup_thema_code(subjects), subjects
print("identical for", len(taxonomy.codes), "codes")
EOF
```

Expected: `identical for 9187 codes`. If `missing` is not empty, stop and report: a subject maps to a code that does not exist, and the old and new paths would differ for it.

- [ ] **Step 6: Point `core/books.py` at the new module**

In `src/para_files/core/books.py`, replace
`from para_files.utils.thema_lookup import lookup_thema_code, thema_to_para_path`
with
`from para_files.core.thema import lookup_thema_code, thema_to_para_path`.

- [ ] **Step 7: Run the tests and the gate**

Run: `uv run pytest tests/test_core_thema.py tests/test_core_books.py -q -o addopts=""`, then the full gate.
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add src/para_files/core/thema.py src/para_files/data/__init__.py src/para_files/data/thema_l1l2.json src/para_files/core/books.py tests/test_core_thema.py
git commit -F <message file>   # "feat(core): Thema folders as package data (234 codes, replaces thema.json lookup)"
```

---

### Task 2: Config directory and circuit breaker move into the core

**Files:**
- Modify: `src/para_files/core/settings.py` (add `config_dir_path`; drop the `para_files.config` import)
- Modify: `src/para_files/core/tree.py:16` (import)
- Modify: `src/para_files/config.py:35-38` (re-export from core until Task 3 deletes it)
- Create: `src/para_files/core/breaker.py`
- Modify: `src/para_files/core/fallback.py:20,179,184`
- Modify: `tests/test_core_fallback.py:11,103,152`
- Test: `tests/test_core_settings.py`, `tests/test_core_breaker.py`

**Interfaces:**
- Produces:
  - `para_files.core.settings.config_dir_path() -> Path`
  - `para_files.core.breaker.CircuitBreaker(threshold: int = 3)` with `is_open: bool`, `record_failure() -> None` and `record_success() -> None`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_core_settings.py`:

```python
def test_config_dir_follows_the_environment(tmp_path, monkeypatch):
    from para_files.core.settings import config_dir_path
    from para_files.core.tree import config_dir

    monkeypatch.setenv("PARA_FILES_CONFIG_DIR", str(tmp_path / "cfg"))
    assert config_dir_path() == tmp_path / "cfg" == config_dir()


def test_config_dir_defaults_to_home(tmp_path, monkeypatch):
    from para_files.core.settings import config_dir_path

    monkeypatch.delenv("PARA_FILES_CONFIG_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert config_dir_path() == tmp_path / ".config" / "para-files"


def test_settings_read_the_env_file_in_the_config_dir(tmp_path, monkeypatch):
    from para_files.core.settings import load_settings

    root = tmp_path / "PARA"
    (root / "0_Inbox").mkdir(parents=True)
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    (cfg / ".env").write_text(f"PARA_FILES_PARA_ROOT={root}\nPARA_FILES_MAX_WORKERS=7\n")
    monkeypatch.setenv("PARA_FILES_CONFIG_DIR", str(cfg))
    settings = load_settings()
    assert settings.para_root == root
    assert settings.max_workers == 7
```

Create `tests/test_core_breaker.py`:

```python
"""The model fallback's circuit breaker."""

from __future__ import annotations

from para_files.core.breaker import CircuitBreaker


def test_opens_after_threshold_failures_in_a_row():
    breaker = CircuitBreaker(threshold=2)
    breaker.record_failure()
    assert not breaker.is_open
    breaker.record_failure()
    assert breaker.is_open


def test_a_success_resets_the_count():
    breaker = CircuitBreaker(threshold=2)
    breaker.record_failure()
    breaker.record_success()
    breaker.record_failure()
    assert not breaker.is_open


def test_an_open_breaker_stays_open():
    breaker = CircuitBreaker(threshold=1)
    breaker.record_failure()
    breaker.record_success()
    assert breaker.is_open
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/test_core_settings.py tests/test_core_breaker.py -q -o addopts=""`
Expected: FAIL with `ImportError` (`config_dir_path` is not in `para_files.core.settings`; there is no module `para_files.core.breaker`).

- [ ] **Step 3: Move `config_dir_path`**

In `src/para_files/core/settings.py`:
- add `import os` to the imports;
- remove `from para_files.config import config_dir_path`;
- add this function above `class PathSettings`:

```python
def config_dir_path() -> Path:
    """Personal config directory: $PARA_FILES_CONFIG_DIR if set, else ~/.config/para-files."""
    override = os.environ.get("PARA_FILES_CONFIG_DIR")
    return Path(override).expanduser() if override else Path.home() / ".config" / "para-files"
```

In `src/para_files/core/tree.py`, replace `from para_files.config import config_dir_path` with `from para_files.core.settings import config_dir_path`. If that creates an import cycle (`settings` importing `tree`), stop and report it.

In `src/para_files/config.py`, replace the body of its `config_dir_path` definition (lines 35–38) with an import at the top of the module, `from para_files.core.settings import config_dir_path`, so old modules keep working until Task 3. Add `# noqa: F401` only if ruff asks for it.

- [ ] **Step 4: Write `src/para_files/core/breaker.py`**

```python
"""Circuit breaker for the model fallback: stop calling after N failures in a row."""

from __future__ import annotations

from loguru import logger


class CircuitBreaker:
    """Opens after `threshold` consecutive failures and stays open for the rest of the run."""

    def __init__(self, threshold: int = 3) -> None:
        """Start closed, with no failures counted."""
        self._threshold = threshold
        self._failures = 0
        self._open = False

    @property
    def is_open(self) -> bool:
        """True once the breaker has tripped."""
        return self._open

    def record_failure(self) -> None:
        """Count one failure; open the breaker when the count reaches the threshold."""
        self._failures += 1
        if self._failures >= self._threshold and not self._open:
            logger.warning("model fallback off for this run after {} failures", self._failures)
            self._open = True

    def record_success(self) -> None:
        """Reset the failure count; an open breaker stays open."""
        self._failures = 0
```

In `src/para_files/core/fallback.py`:
- replace `from para_files.circuit_breaker import OllamaCircuitBreaker` with `from para_files.core.breaker import CircuitBreaker`;
- replace both other uses of `OllamaCircuitBreaker` with `CircuitBreaker`.

In `tests/test_core_fallback.py`, make the same replacement on lines 11, 103 and 152.

- [ ] **Step 5: Run the tests and the gate**

Run: `uv run pytest tests/test_core_settings.py tests/test_core_breaker.py tests/test_core_fallback.py tests/test_core_tree.py -q -o addopts=""`, then the full gate.
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/para_files/core/settings.py src/para_files/core/tree.py src/para_files/config.py src/para_files/core/breaker.py src/para_files/core/fallback.py tests/test_core_fallback.py tests/test_core_settings.py tests/test_core_breaker.py
git commit -F <message file>   # "refactor(core): config dir and circuit breaker live in the core"
```

---

### Task 3: Delete everything the CLI cannot reach

**Files:**
- Delete (src):
  - `pipeline.py`, `mover.py`, `learner.py`, `reference_tree.py`, `types.py`, `config.py`, `logging.py`, `circuit_breaker.py`
  - the folders `classifiers/`, `encoders/`, `learning/`, `taxonomies/`
  - in `utils/`: `chm_metadata.py`, `cleanup.py`, `filename_detector.py`, `geolocation.py`, `nfo_parser.py`, `ocr_metadata.py`, `placeholder_resolver.py`, `smart_renamer.py`, `technology_extractor.py`, `validation.py`, `thema_lookup.py`

  All paths are under `src/para_files/`.
- Delete: `scripts/` (all files) and `config/` (`thema.json`, `documents.json`).
- Delete (tests): `test_analyze_inbox.py`, `test_bakeoff_script.py`, `test_book_detector.py`, `test_build_golden.py`, `test_chm_metadata.py`, `test_circuit_breaker.py`, `test_classifiers.py`, `test_cleanup.py`, `test_config.py`, `test_encoders.py`, `test_eval_script.py`, `test_extension_router.py`, `test_filename_detector.py`, `test_geolocation.py`, `test_learner.py`, `test_learning.py`, `test_llm_classifier.py`, `test_migrate_config.py`, `test_mover.py`, `test_nfo_parser.py`, `test_ocr_metadata.py`, `test_pipeline.py`, `test_pipeline_order.py`, `test_placeholder_resolver.py`, `test_reference_tree.py`, `test_rules_engine.py`, `test_run_baseline.py`, `test_smart_renamer.py`, `test_technology_extractor.py`, `test_thema_taxonomy.py`, `test_types.py`, `test_validation.py`, and `tests/fixtures/test_reference_tree.yaml`. All are under `tests/`.
- Modify: `src/para_files/utils/file_utils.py` (drop `extract_file_metadata`, lines 125–195, and the `para_files.types` import), `src/para_files/utils/__init__.py`, `src/para_files/__init__.py` (docstring if it names old parts), `tests/conftest.py`, `tests/test_isolation.py`, `tests/test_file_utils.py`, `pyproject.toml`.
- Create: `tests/test_reachability.py`

**Interfaces:**
- Consumes: Tasks 1–2 (`core.thema`, `core.settings.config_dir_path`, `core.breaker`).
- Produces: a source tree where every module under `src/para_files/` is reachable from `para_files.cli`.

- [ ] **Step 1: Write the failing reachability test** in `tests/test_reachability.py`:

```python
"""Stage 4 exit: every module of the package is reachable from the CLI (no dead modules)."""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).parent.parent / "src"
PACKAGE = SRC / "para_files"


def _name(path: Path) -> str:
    parts = list(path.relative_to(SRC).with_suffix("").parts)
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


MODULES = {_name(path): path for path in PACKAGE.rglob("*.py")}


def _imports(name: str) -> set[str]:
    path = MODULES[name]
    package = name if path.name == "__init__.py" else name.rpartition(".")[0]
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                head = ".".join(package.split(".")[: len(package.split(".")) - node.level + 1])
                base = f"{head}.{base}" if base else head
            found |= {base} | {f"{base}.{alias.name}" for alias in node.names}
    reached: set[str] = set()
    for module in found:
        while module and module not in MODULES:
            module = module.rpartition(".")[0]
        if module:
            parts = module.split(".")
            reached |= {".".join(parts[:i]) for i in range(1, len(parts) + 1)}
    return reached & MODULES.keys()


def test_every_module_is_reachable_from_the_cli():
    seen: set[str] = set()
    todo = ["para_files.cli.app", "para_files.cli"]
    while todo:
        name = todo.pop()
        if name not in seen:
            seen.add(name)
            todo += sorted(_imports(name))
    assert sorted(MODULES.keys() - seen) == []
```

- [ ] **Step 2: Run it to see it fail**

Run: `uv run pytest tests/test_reachability.py -q -o addopts=""`
Expected: FAIL, listing the dead modules (`para_files.pipeline`, `para_files.classifiers…`, …).

- [ ] **Step 3: Delete the dead source, scripts, config data and their tests**

```bash
git rm -q src/para_files/{pipeline,mover,learner,reference_tree,types,config,logging,circuit_breaker}.py
git rm -rq src/para_files/{classifiers,encoders,learning,taxonomies}
git rm -q src/para_files/utils/{chm_metadata,cleanup,filename_detector,geolocation,nfo_parser,ocr_metadata,placeholder_resolver,smart_renamer,technology_extractor,validation,thema_lookup}.py
git rm -rq scripts config
git rm -q tests/fixtures/test_reference_tree.yaml tests/test_{analyze_inbox,bakeoff_script,book_detector,build_golden,chm_metadata,circuit_breaker,classifiers,cleanup,config,encoders,eval_script,extension_router,filename_detector,geolocation,learner,learning,llm_classifier,migrate_config,mover,nfo_parser,ocr_metadata,pipeline,pipeline_order,placeholder_resolver,reference_tree,rules_engine,run_baseline,smart_renamer,technology_extractor,thema_taxonomy,types,validation}.py
```

If `tests/fixtures/` is now empty, `git rm` has removed it. Remove the `fixtures_dir` fixture from `conftest.py` only if no remaining test uses it (`grep -rn fixtures_dir tests`).

- [ ] **Step 4: Trim `file_utils.py` and the package `__init__` files**

- `src/para_files/utils/file_utils.py`: delete `extract_file_metadata` (the whole function, lines 125–195) and `from para_files.types import FileMetadata`. Then delete any import that ruff now reports as unused (`uv run ruff check src/para_files/utils/file_utils.py`).
- `src/para_files/utils/__init__.py`: replace the whole file with:

```python
"""File readers used by the core: text previews, PDF/EPUB/MOBI metadata, EXIF, ISBN lookup."""
```

- `src/para_files/__init__.py`: keep `__version__`. If its docstring mentions MLX, Ollama, embeddings or the pipeline, make it: `"""para-files: file documents into a PARA tree, with preview, journal and undo."""`
- In `tests/test_file_utils.py`, delete every test that calls `extract_file_metadata`, and its import.

- [ ] **Step 5: Rewrite the test sandbox (`tests/conftest.py`)**

Replace the `_sanitized_reference_tree` fixture, `FIXTURE_TREE`, `SCRIPTS_DIR`, `script_loader` and `load_script` with this fixture. Keep `macos_only`, `project_root`, `_snapshot` and `snapshot`, and remove imports that become unused.

```python
@pytest.fixture(autouse=True)
def _sandbox(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Per-test HOME and config dir, no inherited PARA_FILES_ or API key, cwd = tmp_path."""
    for name in [k for k in os.environ if k.startswith("PARA_FILES_")]:
        monkeypatch.delenv(name)  # inherited shell values (e.g. sourced ~/.env) never leak in
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)  # a real key never reaches a test
    home = tmp_path_factory.mktemp("home")  # outside tmp_path so tests listing it stay exact
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PARA_FILES_CONFIG_DIR", str(home / ".config" / "para-files"))
    monkeypatch.chdir(tmp_path)
```

Update the module docstring to: `"""Pytest configuration: every test runs with its own HOME, config dir and cwd, so no test reads the owner's real configuration or PARA volume."""`

Replace the whole of `tests/test_isolation.py` with:

```python
"""Test isolation: no test may read the owner's real configuration or PARA volume."""

from __future__ import annotations

import os
import pwd
from pathlib import Path

from para_files.core.settings import config_dir_path, load_settings


def _real_home() -> Path:
    """The account's real home directory, independent of the HOME the fixture sets."""
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def test_config_dir_is_sandboxed() -> None:
    """The personal config dir resolves inside the per-test HOME, never the owner's."""
    assert not config_dir_path().is_relative_to(_real_home())
    assert config_dir_path().is_relative_to(Path(os.environ["HOME"]))


def test_no_para_files_variable_or_key_leaks_in() -> None:
    assert not [name for name in os.environ if name.startswith("PARA_FILES_") and name not in {
        "PARA_FILES_CONFIG_DIR"
    }]
    assert "OPENROUTER_API_KEY" not in os.environ


def test_a_dotenv_in_the_working_directory_is_never_read(tmp_path: Path) -> None:
    """Only <config dir>/.env is read; a .env in the cwd (tmp_path) is ignored."""
    root = tmp_path / "PARA"
    (root / "0_Inbox").mkdir(parents=True)
    (tmp_path / ".env").write_text("PARA_FILES_MAX_WORKERS=9\n")
    assert load_settings(para_root=root).max_workers == 4
```

- [ ] **Step 6: Fix every remaining failure, then run the reachability test**

Run: `uv run pytest -q -o addopts="" -x`. For each failure:
- if a remaining test imports a deleted module, delete only that test function, never a core or CLI test;
- if a core or CLI test fails, stop and report: the purge removed something still in use.

Then run `uv run pytest tests/test_reachability.py -q -o addopts=""`.
Expected: PASS.

- [ ] **Step 7: Clean `pyproject.toml`**

- Remove the `"scripts/*.py"` block from `[tool.ruff.lint.per-file-ignores]`.
- From the mypy `ignore_missing_imports` module list, remove `semantic_router.*` and `transformers.*`, and any other entry that `uv run mypy src/` reports as an unused section.
- Remove any `[tool.coverage]`, `[tool.hatch]` or `[tool.pytest]` entry that names a deleted path.

- [ ] **Step 8: Update docs that name deleted files**

Run `grep -rnE "scripts/|config/thema.json|config/documents.json|taxonomies|thema_lookup|circuit_breaker|para_files/config.py|pipeline.py|classifiers/" README.md CLAUDE.md docs/*.md docs/cli examples` and update every hit:
- **CLAUDE.md:** drop the deleted rows from Key Files; add `core/thema.py` and `data/thema_l1l2.json`. Replace the paragraph "The old pipeline modules … remain only until the Stage 4 purge …" with "All modules under `src/para_files/` are reachable from the CLI (`tests/test_reachability.py`)." In the Thema section, change the `from para_files.taxonomies.models import ThemaTaxonomy` example to `from para_files.core.thema import thema_to_para_path` / `thema_to_para_path("UB")`.
- **`examples/README.md`:** remove the "Stage 1 tooling (developer scripts)" section. Replace the `uv run python -c …` check with `para-files tree --validate`.
- **Gate commands** in `CLAUDE.md`: no `scripts/`.

- [ ] **Step 9: Run the gate, measure, commit**

Run the full gate (without `scripts/`), then `find src/para_files -name '*.py' | xargs wc -l | tail -1`, and record the source line count in the commit message.

```bash
git add -A src/para_files tests pyproject.toml CLAUDE.md README.md docs examples
git status --short   # .serena/, .rtk/, .superpowers/ and uv.lock must NOT be staged; unstage them if they are
git commit -F <message file>   # "refactor!: delete the old pipeline, local AI, Stage 1 scripts and dead utils (N lines left)"
```

---

### Task 4: Drop unused dependencies

**Files:**
- Modify: `pyproject.toml` (`[project] dependencies`), `uv.lock`, `.github/workflows/ci.yml:11`

- [ ] **Step 1: Prove each dependency is unused**

Run:

```bash
for mod in semantic_router einops geopy faker cryptography bandit httpx; do
  printf '%s: ' "$mod"; grep -rlE "^\s*(import|from) $mod\b" src tests | tr '\n' ' '; echo
done
```

Expected: every line ends with nothing after the colon. If a module is still imported, keep that dependency and report it.

- [ ] **Step 2: Remove them**

In `pyproject.toml` `[project] dependencies`, delete these lines: `"semantic-router>=0.1.0"`, `"einops>=0.8.1"`, `"httpx>=0.28.1"`, `"geopy>=2.4.1"`, `"faker>=39.0.0"`, `"cryptography>=46.0.3"` and `"bandit>=1.9.2"`. httpx still arrives through litellm, but nothing imports it directly.

Then run `uv lock` and `uv sync --all-extras`.

In `.github/workflows/ci.yml`, change the comment `# Apple Silicon required for MLX` to `# macOS: OCR uses the Vision framework`.

- [ ] **Step 3: Run the gate**

Expected: all pass. `uv run para-files --help` lists the six commands.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock .github/workflows/ci.yml
git commit -F <message file>   # "build: drop semantic-router, einops, geopy, faker, cryptography, bandit, httpx"
```

---

### Task 5: Repository hygiene (S6)

**Files:**
- Delete: `TODO-routing-fixes.md`, `docs/archive/how-to-better-claude-code.md`
- Move: `.planning/` to `docs/archive/planning/` (`git mv`)
- Untrack: `.serena/`, `.claude/`. Modify `.gitignore`.
- Modify: `tests/test_repo_hygiene.py`

- [ ] **Step 1: Write the failing test.** Append to `tests/test_repo_hygiene.py`:

```python
@pytest.mark.skipif(GIT is None or not (ROOT / ".git").exists(), reason="needs a git checkout")
@pytest.mark.parametrize("path", [".serena", ".claude", ".planning", "TODO-routing-fixes.md"])
def test_tool_state_and_old_notes_are_not_tracked(path: str):
    assert GIT is not None
    tracked = subprocess.run(  # noqa: S603 - fixed git command, no user input
        [GIT, "ls-files", path], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    assert tracked.strip() == ""
```

- [ ] **Step 2: Run it to see it fail**

Run: `uv run pytest tests/test_repo_hygiene.py -q -o addopts=""`
Expected: 4 failures (all four paths are tracked).

- [ ] **Step 3: Clean up**

```bash
ls .serena .claude > /tmp/before.txt           # owner's local files: must survive
git rm -q TODO-routing-fixes.md docs/archive/how-to-better-claude-code.md
mkdir -p docs/archive && git mv .planning docs/archive/planning
git rm -rq --cached .serena .claude
printf '\n# Local tool state (never tracked)\n.serena/\n.claude/\n' >> .gitignore
ls .serena .claude | diff - /tmp/before.txt && echo "local files intact"
```

Expected: `local files intact`. In `docs/archive/README.md`, add a line: `planning/ — the pre-2026-10 GSD planning notes (milestones, phases, roadmap).`

- [ ] **Step 4: Run the gate and commit**

```bash
git add .gitignore tests/test_repo_hygiene.py docs/archive
git commit -F <message file>   # "chore: untrack .serena/.claude, archive .planning, drop old notes"
```

Check `git status --short`: the files under `.serena/` and `.claude/` show as deleted from the index only, and nothing else is staged.

---

### Task 6: ADR-013, spec and docs

**Files:**
- Create: `docs/adr/ADR-013-redesign-records-first.md`
- Modify:
  - `docs/adr/ADR-010-ollama-litellm-migration.md` (status)
  - `docs/adr/README.md` (index)
  - `docs/superpowers/specs/2026-10-10-para-files-redesign-design.md` (§3 S1/S2 "How verified"; §4.1 package data; §5 Stage 4; §8)
  - `CHANGELOG.md`
  - `docs/architecture.md` and `docs/configuration.md`, only if they mention deleted files

- [ ] **Step 1: Write `docs/adr/ADR-013-redesign-records-first.md`**

```markdown
# ADR-013: Records-First Redesign; Local AI Removed

**Date**: 2026-10-11
**Status**: Accepted
**Deciders**: Project owner
**Supersedes**: [ADR-010](ADR-010-ollama-litellm-migration.md)

---

## Context

The six-signal pipeline (rules, taxonomy, embeddings, extension router, local LLM) had grown to 18.8k lines, and it moved files with no reliable undo. On the owner's records, no signal reached the 98% precision needed to move files unattended. The local models (Ollama embeddings and a local LLM, ADR-010) were slow: 78 minutes for 206 files, with frequent server disconnects. They were also the least accurate signal (17% exact).

## Decision

1. Rebuild around a small core (`para_files.core`). It runs four signals: rules, ISBN books, issuers, and an optional cloud model through litellm and OpenRouter with zero data retention. Bands decide what moves: green moves with `--apply`, yellow needs the owner's confirmation, red stays.
2. Every move is journaled before it happens; `undo` reverses a run.
3. Remove local AI entirely: no Ollama, no embeddings, no local model server.
4. Delete the old pipeline, its CLI and the Stage 1 scripts. Thema folder names ship as package data (`para_files/data/thema_l1l2.json`).

## Rationale

The tree, not the model, was the bottleneck: merging twin folders helped more than any model did. A cloud model behind the owner's confirmations gives suggestions without unattended moves. Records with stable names (payslips, statements) are filed by rules, which are exact.

## Consequences

- No model runs on the machine. The fallback needs an OpenRouter key and is optional.
- Issuers and the model stay yellow until a kind has 100 confirmed decisions.
- The source shrank to about a third of its former size; every module is reachable from the CLI.
- ADR-010 is superseded. ADR-002 and ADR-004 stay superseded.
```

- [ ] **Step 2: Update the ADR status and index**

In `ADR-010-ollama-litellm-migration.md`, change `**Status**: Accepted` to `**Status**: Superseded by [ADR-013](ADR-013-redesign-records-first.md)`.

In `docs/adr/README.md`, replace the index table with:

```markdown
| ADR | Title | Status |
|-----|-------|--------|
| [ADR-001](ADR-001-para-method.md) | Use PARA Method for File Organization | Accepted (amended by ADR-012) |
| [ADR-002](ADR-002-apple-silicon-only.md) | Apple Silicon (macOS) Only Platform | Superseded by ADR-010 |
| [ADR-003](ADR-003-cascading-pipeline.md) | Cascading Classification Pipeline (First-Match Wins) | Accepted |
| [ADR-004](ADR-004-mlx-embeddings.md) | MLX Embeddings with nomic-embed-text-v1.5 | Superseded by ADR-010 |
| [ADR-005](ADR-005-yaml-config.md) | YAML Reference Tree for Routing Configuration | Accepted |
| [ADR-006](ADR-006-pydantic-validation.md) | Pydantic for Data Validation and Settings | Accepted |
| [ADR-007](ADR-007-typer-cli.md) | Typer for CLI Framework | Accepted |
| [ADR-008](ADR-008-uv-package-manager.md) | uv as Package Manager | Accepted |
| [ADR-009](ADR-009-thema-book-taxonomy.md) | Thema v1.6 for Book Subject Classification | Accepted |
| [ADR-010](ADR-010-ollama-litellm-migration.md) | Replace MLX with litellm/Ollama | Superseded by ADR-013 |
| [ADR-011](ADR-011-performance-optimizations.md) | Performance Optimizations | Accepted |
| [ADR-012](ADR-012-records-and-para.md) | Records Retention Vault Alongside PARA | Accepted |
| [ADR-013](ADR-013-redesign-records-first.md) | Records-First Redesign; Local AI Removed | Accepted |
```

Before writing the ADR-002, ADR-004 and ADR-011 rows, check each file's own `**Status**` line. Copy the status as the file states it; if a file disagrees with the table above, the file wins and the table row follows it. In `ADR-012-records-and-para.md`, set `**Status**: Accepted`, since Stages 1–4 implemented it.

- [ ] **Step 3: Amend the spec**

In `docs/superpowers/specs/2026-10-10-para-files-redesign-design.md`:
- **§3 table:** for S1, S2 and S3b, replace `` `scripts/eval.py` on the journal `` with `` `para-files tree` (confirmation statistics from the journal) ``.
- **§4.1 "Package data":** replace the two bullets and the "Both package files are deferred to Stage 4" sentence with: "`thema_l1l2.json` — the 234 Thema level-1/level-2 folder names (≈10 KB, replaces the 3.6 MB `thema.json`); the subject-keyword map stays in `core/thema.py`. No `default_rules.yaml`: rules name personal `leaf_id`s, so the owner's `rules.yaml` carries the extension rules (decision 2026-10-11)."
- **§5 Stage 4:** after the Exit line, add `Status: done 2026-10-11 (see decisions log).`
- **§8 decisions log:** add these rows:
  - `| Stage 4 purge (2026-10-11) | Old pipeline, local AI, Stage 1 scripts, \`config/thema.json\` and \`config/documents.json\` deleted; every module reachable from the CLI; source N lines (from Task 3) |`
  - `| Package data (2026-10-11) | Only \`thema_l1l2.json\`; \`default_rules.yaml\` dropped (rules name personal leaf ids) |`

- [ ] **Step 4: CHANGELOG** under `## [Unreleased]`, add:

```markdown
### Removed (Stage 4)

- The old pipeline (`pipeline`, `mover`, `learner`, `reference_tree`, `classifiers/`, `encoders/`, `learning/`, `taxonomies/`), local AI (Ollama embeddings and local LLM), `config.py`, `types.py`, the Stage 1 `scripts/`, `config/thema.json` and `config/documents.json`, and ten unused `utils` modules. Every remaining module is reachable from the CLI.
- Dependencies `semantic-router`, `einops`, `geopy`, `faker`, `cryptography`, `bandit` and `httpx` (still installed through litellm).
- `.serena/` and `.claude/` are no longer tracked; `.planning/` moved to `docs/archive/planning/`.

### Changed (Stage 4)

- Thema folder names ship as package data (`para_files/data/thema_l1l2.json`, 234 codes), so books get their folders when para-files is installed from a wheel.
- ADR-013 records the redesign and the end of local AI (supersedes ADR-010).
```

- [ ] **Step 5: Check the docs**

```bash
grep -rnE "Ollama|MLX|thema\.json|documents\.json|scripts/|pipeline\.py|classifiers/" README.md CLAUDE.md docs/*.md docs/cli docs/adr/README.md | grep -v "thema_l1l2"
```

Expected: no hit, except lines that explicitly say what was removed (CHANGELOG-style wording) or that link to an ADR. Fix any other hit. Then run the gate.

- [ ] **Step 6: Commit**

```bash
git add docs/adr docs/superpowers/specs/2026-10-10-para-files-redesign-design.md CHANGELOG.md docs/architecture.md docs/configuration.md
git commit -F <message file>   # "docs: ADR-013 (supersedes ADR-010), spec Stage 4 done, changelog"
```

---

### Task 7: Exit check (S6, S7, size, wheel)

**Files:**
- Modify: `docs/superpowers/specs/2026-10-10-para-files-redesign-design.md` §8 (fill in the measured numbers if Task 6 left "N")

- [ ] **Step 1: Run S7 from a clean clone, offline**

```bash
CLONE=$(mktemp -d)/para-files
git clone -q . "$CLONE" && cd "$CLONE"
uv sync --all-extras -q
HTTP_PROXY=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 ALL_PROXY=http://127.0.0.1:9 \
  uv run pytest -q -o addopts="-ra --strict-markers --strict-config" 2>&1 | tail -3
cd - >/dev/null
```

Expected: every test passes, slow ones included. Slow tests may be skipped when `pandoc` or `exiftool` is missing. Any failure that names a network host or a deleted module is a bug: fix it in the owning task's area and commit.

- [ ] **Step 2: Build the wheel and check the package data**

```bash
uv build -q --wheel -o /tmp/para-wheel && unzip -l /tmp/para-wheel/*.whl | grep -E "thema_l1l2.json|para_files/core/thema.py"
```

Expected: both paths are listed.

- [ ] **Step 3: S6 identifier scan and size**

```bash
git ls-files | xargs grep -IlE "/Volumes/|OneDrive|/Users/[a-z]" 2>/dev/null | grep -v "^docs/archive/\|^docs/superpowers/\|^CHANGELOG.md$"
find src/para_files -name '*.py' | xargs wc -l | tail -1
```

Expected: the first command prints nothing; any hit is fixed by making the example generic. The line count is about 6.5k (spec target: about half of 18.8k, i.e. ≤ 9.4k).

- [ ] **Step 4: Record the numbers and commit**

Replace the `N` in the spec §8 "Stage 4 purge" row with the measured line count, if Task 6 left it. Add the line count and the offline test count to the CHANGELOG "Removed (Stage 4)" first bullet.

```bash
git add docs/superpowers/specs/2026-10-10-para-files-redesign-design.md CHANGELOG.md
git commit -F <message file>   # "docs: Stage 4 exit numbers (S6, S7, size)"
```
