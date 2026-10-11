# Stage 1 — Canonical Tree, Golden Corpus, Bake-off Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Owner's standing preference: implementer and reviewer subagents run on Haiku; this plan carries complete code so tasks are transcription plus testing.

**Goal:** Give para-files a closed, owner-approved list of leaves (with content kind and retention), a golden corpus and an evaluation script, then measure the old pipeline and the signal-4 candidates on it, without moving a single file.

**Architecture:**
- **`src/para_files/core/`** holds the two pieces Stage 2 builds on:
  - strict loading and validation of `tree.yaml`, `rules.yaml` and `issuers.yaml`;
  - the secrets guard.
- **`scripts/`** holds Stage 1 developer tools. They read the PARA tree, write only into the personal config directory, and are tested through a `load_script` fixture.
- **Personal data** lives only in `~/.config/para-files/` (or `$PARA_FILES_CONFIG_DIR`).

**Tech Stack:** Python 3.12, pydantic v2, PyYAML, httpx, python-dotenv (all already installed), pytest.

**Spec:** `docs/superpowers/specs/2026-10-10-para-files-redesign-design.md` (amended 2026-10-11): §1 content kinds, §4.1 leaves, §4.3 secrets guard, §4.5 measurement, §5 Stage 1.

## Global Constraints

**Code style and checks:**
- Python ≥ 3.12; `from __future__ import annotations` in every module; line length 100.
- `src/` code must pass `uv run ruff check src/ tests/`, `uv run ruff format --check src/ tests/` and `uv run mypy src/` (strict).
- `scripts/*.py` are developer tools, not packaged and not in CI lint. Keep them `uv run ruff format`-clean.
- After writing code in any task, run `uv run ruff check --fix src/ tests/` and `uv run ruff format src/ tests/ scripts/` before the checks. They may re-order imports and re-wrap the code shown here; that is expected.

**Personal data and the PARA root:**
- Personal data lives only in `config_dir()` (`$PARA_FILES_CONFIG_DIR`, else `~/.config/para-files`). That covers `tree.yaml`, `rules.yaml`, `issuers.yaml`, `golden.jsonl`, `pred_*.jsonl` and `draft/`.
- Never write these into the repo or commit them.
- Every Stage 1 script is read-only on the PARA root. A script refuses an output path inside the PARA root.

**Spec rules:**
- Leaf schema exactly as spec §4.1: `kind` (`record|library|media|knowledge`), `retention` (`permanent|ret|10y|5y|2y|ctr`, records only), `path` (bucket + ≤ 2 levels, `1_`–`4_` bucket), `subkey` (≤ 2 of `{year}`, `{month}`, `{issuer}`, `{thema}`), `describe`, `keywords`.
- Every cloud request carries `"provider": {"zdr": true, "data_collection": "deny"}`. Gemini 3.8 Flash and Sonnet 5.5 requests carry `"reasoning": {"effort": "low"}` and `max_tokens` 4000 (both reject disabled reasoning). A file for which `secret_reason(...)` returns a value is never sent anywhere.
- Spec S7: tests never touch the network, Ollama or the owner's real config; use `tmp_path` trees.

**Repo and git hygiene:**
- No new dependencies in `pyproject.toml`.
- No personal identifiers (real paths, people's names, account numbers, property names) in any tracked file, this plan included.
- Never stage `uv.lock`, `.serena/` or `.rtk/`.
- Every commit message ends with these two lines (pass them as a second `-m`):

  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx
  ```

**Deliberately not in this plan:**
- the shadowed-glob warning: it belongs to Stage 3's `tree --validate`;
- case-insensitive glob matching: it belongs to Stage 2's rule signal;
- the tree-cleanup generator and the reorganization of the existing tree: batches on demand after Stage 2, following the spec's tree cleanup policy (§4.1). Task 5 is intentionally empty.

## Review Focus

Failure modes the spec implies but no feature test exercises, most likely first. Each is pinned by a test in the task named.

1. **NFD names from macOS/SMB volumes.** Folder and file names compared against NFC strings (documents.json, golden paths) must still match, never fail silently. Tests: Task 4 (NFD folder becomes a leaf), Task 7 (NFD golden path joins an NFC prediction).
2. **Huge folders** (tens of thousands of photos). Counting and sampling stop at a cap, so a run takes minutes, not hours. Tests: Task 4 (`count_files` cap), Task 6 (`WALK_CAP`).
3. **Symlinked folders inside PARA pointing outside.** Never followed, never planned. Test: Task 4 (`scan_folders` skips symlinked folders).
4. **Unreadable or online-only files.** One bad file never stops a run. Tests: Task 8 (classifier raises → red row), Task 9 (preview raises → still predicted).
5. **Secrets inside PARA.** Never sampled into the golden corpus, never sent to a cloud model. Tests: Task 6, Task 9.
6. **Retention prefixes never merge.** `2y_x`, `5y_x` and `ctr_x` stay three folders at every depth; only an unprefixed legacy folder or a stray prefix is remapped. Test: Task 4.

---

### Task 1: Move the personal reference tree out of the repo

**Files:**
- Modify: `src/para_files/config.py:30` (constant) and `:269-272` (field default)
- Modify: `src/para_files/cli/shared.py:19,140`
- Modify: `src/para_files/cli/config_cmd.py:43-47`
- Modify: `src/para_files/classifiers/book_detector.py` (one list entry, see Step 6)
- Modify: `docs/plans/classification-issues-report.md:135`
- Modify: `tests/test_config.py`, `tests/test_main.py`, `.gitignore`, `CLAUDE.md:79`, `CHANGELOG.md`
- Create: `tests/test_repo_hygiene.py`

**Interfaces:**
- Produces:
  - `para_files.config.LEGACY_REFERENCE_TREE: Path` (= `Path("config/personal_file_tree.yaml")`)
  - `para_files.config.DEFAULT_REFERENCE_TREE: Path` (= `~/.config/para-files/personal_file_tree.yaml`)
  - `para_files.config.default_reference_tree() -> Path`

- [ ] **Step 1: Write the failing tests**

In `tests/test_config.py`, extend the import block to:

```python
from para_files.config import (
    DEFAULT_LLM_CONFIDENCE_THRESHOLD,
    DEFAULT_LLM_MODEL,
    DEFAULT_MLX_MODEL,
    DEFAULT_REFERENCE_TREE,
    DEFAULT_SCORE_THRESHOLD,
    LEGACY_REFERENCE_TREE,
    Config,
    LLMConfig,
    MLXConfig,
    _load_yaml_config,
    default_reference_tree,
    load_config,
)
```

In `TestConfig.test_minimal_config`, replace the line `assert config.reference_tree_path == Path("config/personal_file_tree.yaml")` with:

```python
        assert config.reference_tree_path == default_reference_tree()
```

In `TestYAMLConfig`, replace `test_default_reference_tree_path` with these two tests:

```python
    def test_default_reference_tree_path(self):
        """The personal reference tree lives in ~/.config/para-files/."""
        expected = Path.home() / ".config" / "para-files" / "personal_file_tree.yaml"
        assert expected == DEFAULT_REFERENCE_TREE

    def test_default_reference_tree_prefers_personal_copy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Use the personal copy when it exists, else the legacy in-repo path."""
        import para_files.config as config_module

        personal = tmp_path / "personal_file_tree.yaml"
        monkeypatch.setattr(config_module, "DEFAULT_REFERENCE_TREE", personal)
        assert config_module.default_reference_tree() == LEGACY_REFERENCE_TREE
        personal.write_text("routing_rules: {}\n")
        assert config_module.default_reference_tree() == personal
```

Create `tests/test_repo_hygiene.py`:

```python
"""Repository hygiene: personal config must not be tracked (spec S6)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
GIT = shutil.which("git")


@pytest.mark.skipif(
    GIT is None or not (ROOT / ".git").exists(), reason="needs a git checkout"
)
def test_personal_reference_tree_is_not_tracked():
    assert GIT is not None
    tracked = subprocess.run(  # noqa: S603 - fixed git command, no user input
        [GIT, "ls-files", "config/personal_file_tree.yaml"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert tracked.strip() == ""
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_config.py tests/test_repo_hygiene.py -q`
Expected: FAIL. The import of `LEGACY_REFERENCE_TREE` fails, and the hygiene test reports the file is tracked.

- [ ] **Step 3: Implement the new default location**

In `src/para_files/config.py`, replace the line `DEFAULT_REFERENCE_TREE = Path("config/personal_file_tree.yaml")` with:

```python
LEGACY_REFERENCE_TREE = Path("config/personal_file_tree.yaml")
DEFAULT_REFERENCE_TREE = Path.home() / ".config" / "para-files" / "personal_file_tree.yaml"


def default_reference_tree() -> Path:
    """Return the personal reference tree if it exists, else the legacy in-repo path."""
    return DEFAULT_REFERENCE_TREE if DEFAULT_REFERENCE_TREE.exists() else LEGACY_REFERENCE_TREE
```

In the same file, change the `reference_tree_path` field to:

```python
    reference_tree_path: Path = Field(
        default_factory=default_reference_tree,
        description="Path to the PARA reference tree YAML file",
    )
```

`_load_yaml_config` keeps trying `DEFAULT_REFERENCE_TREE` first, then `Path.cwd() / "config" / "personal_file_tree.yaml"`. Leave it unchanged.

In `src/para_files/cli/shared.py`:
- change the import to `from para_files.config import default_reference_tree, load_config`;
- change `return DEFAULT_REFERENCE_TREE` (inside the `except ValidationError` branch) to `return default_reference_tree()`.

In `src/para_files/cli/config_cmd.py`, replace lines 43-47 with:

```python
    from para_files.config import default_reference_tree

    if path:
        tree_path = default_reference_tree()
        typer.echo(f"Reference tree: {tree_path}")
        typer.echo(f"  Exists: {tree_path.exists()}")
```

- [ ] **Step 4: Point CLI tests at the sanitized fixture tree**

In `tests/test_main.py`, add these imports below `from __future__ import annotations`:

```python
from pathlib import Path

import pytest
```

Add this fixture just above `class TestInitCommand:`:

```python
FIXTURE_TREE = Path(__file__).parent / "fixtures" / "test_reference_tree.yaml"


@pytest.fixture
def fixture_reference_tree(monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the CLI at the sanitized fixture tree instead of the owner's real one."""
    monkeypatch.setenv("PARA_FILES_REFERENCE_TREE_PATH", str(FIXTURE_TREE))
    return FIXTURE_TREE
```

Put `@pytest.mark.usefixtures("fixture_reference_tree")` on the line directly above each of these five classes: `TestInitCommand`, `TestTreeCommand`, `TestRoutesCommand`, `TestIssuersCommand`, `TestInitAdvanced`.

- [ ] **Step 5: Untrack the personal tree, keep it on disk, copy it to the config directory**

```bash
mkdir -p ~/.config/para-files
cp -n config/personal_file_tree.yaml ~/.config/para-files/personal_file_tree.yaml
git rm --cached config/personal_file_tree.yaml
printf '\n# Personal reference tree (lives in ~/.config/para-files/)\nconfig/personal_file_tree.yaml\n' >> .gitignore
```

The file stays in `config/` on disk (now untracked and ignored), so nothing breaks locally. It remains in git history: the owner decided not to rewrite it.

- [ ] **Step 6: Remove the two remaining personal identifiers**

1. In `src/para_files/classifiers/book_detector.py`, delete the single list entry whose trailing comment is `# UBS account number prefix`. It is a 4-digit string inside `financial_filename_patterns`:

   ```bash
   sed -i '' '/# UBS account number prefix/d' src/para_files/classifiers/book_detector.py
   ```

2. In `docs/plans/classification-issues-report.md`, line 135 names one of the owner's properties (a hyphenated proper noun). Replace that name with `<property>` and change nothing else on the line.

- [ ] **Step 7: Run the full suite**

Run: `uv run pytest -q`
Expected: all pass. That includes the 12 `test_main.py` init/tree/routes/issuers tests, now on the fixture tree, and the hygiene test.

Run: `uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run mypy src/`
Expected: clean.

- [ ] **Step 8: Docs**

1. In `CLAUDE.md`, replace the table row `` | `config/personal_file_tree.yaml` | PARA reference tree (example) | `` with:

   ```
   | `~/.config/para-files/personal_file_tree.yaml` | Legacy reference tree (personal, not tracked; `config/` copy is the fallback) |
   ```

2. In `CHANGELOG.md`, insert directly below the `## [Unreleased]` line (with a blank line on each side):

   ```markdown
   ### Changed (Stage 1)

   - **Personal reference tree moved out of the repo** — the default is now `~/.config/para-files/personal_file_tree.yaml`; `config/personal_file_tree.yaml` is untracked and still used as a fallback when the personal copy is missing. CLI tests use the sanitized fixture tree. Two remaining personal identifiers were removed from tracked files.
   ```

- [ ] **Step 9: Commit**

```bash
git add src/para_files/config.py src/para_files/cli/shared.py src/para_files/cli/config_cmd.py \
  src/para_files/classifiers/book_detector.py docs/plans/classification-issues-report.md \
  tests/test_config.py tests/test_main.py tests/test_repo_hygiene.py .gitignore CLAUDE.md CHANGELOG.md
git commit -m "chore(config): move the personal reference tree out of the repo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx"
```

The `git rm --cached` from Step 5 is already staged and goes into this commit.

---

### Task 2: Canonical tree model, strict loader, validation warnings, examples

**Files:**
- Create: `src/para_files/core/__init__.py`, `src/para_files/core/tree.py`
- Create: `examples/tree.yaml`, `examples/rules.yaml`, `examples/issuers.yaml`, `examples/README.md`
- Test: `tests/test_core_tree.py`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Produces (module `para_files.core.tree`):
  - `class TreeError(ValueError)`
  - `config_dir() -> Path`
  - `class Leaf` (pydantic, frozen): `kind`, `path`, `describe`, `retention`, `subkey`, `keywords`
  - `class Tree`: `leaves: dict[str, Leaf]`
  - `class Rule`: `name`, `leaf`, `globs: tuple[str, ...]`
  - `class RulesFile`: `rules: tuple[Rule, ...]`
  - `class Issuer`: `patterns: tuple[str, ...]`, `leaves: tuple[str, ...]`
  - `class IssuersFile`: `issuers: dict[str, Issuer]`
  - `class TreeConfig`: `tree`, `rules`, `issuers`
  - `load_tree_config(directory: Path | None = None) -> TreeConfig`
  - `validation_warnings(config: TreeConfig) -> list[str]`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_core_tree.py`:

```python
"""Tests for the canonical tree, rules and issuers loader (spec §4.1)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from para_files.core.tree import TreeError, config_dir, load_tree_config, validation_warnings

EXAMPLES = Path(__file__).parent.parent / "examples"


def _leaf(**overrides):
    leaf = {"kind": "knowledge", "path": "2_Areas/carriere", "describe": "Career"}
    leaf.update(overrides)
    return leaf


def _write(directory: Path, leaves: dict, rules=None, issuers=None) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "tree.yaml").write_text(yaml.safe_dump({"leaves": leaves}))
    if rules is not None:
        (directory / "rules.yaml").write_text(yaml.safe_dump({"rules": rules}))
    if issuers is not None:
        (directory / "issuers.yaml").write_text(yaml.safe_dump({"issuers": issuers}))
    return directory


class TestExamples:
    def test_examples_load_cleanly(self):
        cfg = load_tree_config(EXAMPLES)
        kinds = {leaf.kind for leaf in cfg.tree.leaves.values()}
        assert kinds == {"record", "library", "media", "knowledge"}
        expected = ["leaf 'identity_papers': no rule or issuer points to it"]
        assert validation_warnings(cfg) == expected


class TestLeafRules:
    @pytest.mark.parametrize(
        ("leaf", "message"),
        [
            (_leaf(path="0_Inbox/x"), "1_-4_ bucket"),
            (_leaf(path="2_Areas/a/b/c"), "deeper than"),
            (_leaf(path="2_Areas/carriere "), "padded"),
            (_leaf(kind="record"), "record leaves need a retention"),
            (_leaf(retention="5y"), "record leaves need a retention"),
            (
                _leaf(kind="record", retention="5y", path="4_Archives/10y_banques"),
                "requires 4_Archives/5y_",
            ),
            (_leaf(subkey="{technology}"), "subkey must be"),
            (_leaf(subkey="{year}/{month}/{issuer}"), "subkey must be"),
            (_leaf(colour="blue"), "Extra inputs are not permitted"),
        ],
    )
    def test_invalid_leaf_is_rejected(self, tmp_path, leaf, message):
        _write(tmp_path, {"bad": leaf})
        with pytest.raises(TreeError, match=message):
            load_tree_config(tmp_path)

    def test_permanent_record_may_live_outside_archives(self, tmp_path):
        leaf = _leaf(kind="record", retention="permanent", path="2_Areas/Officiel")
        _write(tmp_path, {"papers": leaf})
        assert load_tree_config(tmp_path).tree.leaves["papers"].retention == "permanent"

    def test_leaf_ids_must_be_snake_case(self, tmp_path):
        _write(tmp_path, {"Career": _leaf()})
        with pytest.raises(TreeError, match="snake_case"):
            load_tree_config(tmp_path)


class TestReferences:
    def test_rule_with_unknown_leaf_is_rejected(self, tmp_path):
        rules = [{"name": "cv", "leaf": "nope", "globs": ["*cv*"]}]
        _write(tmp_path, {"career": _leaf()}, rules=rules)
        with pytest.raises(TreeError, match="unknown leaf 'nope'"):
            load_tree_config(tmp_path)

    def test_duplicate_issuer_pattern_is_rejected_case_insensitively(self, tmp_path):
        issuers = {
            "a": {"patterns": ["Swisscom"], "leaves": ["career"]},
            "b": {"patterns": ["swisscom"], "leaves": ["career"]},
        }
        _write(tmp_path, {"career": _leaf()}, issuers=issuers)
        with pytest.raises(TreeError, match="used by issuers 'a' and 'b'"):
            load_tree_config(tmp_path)

    def test_duplicate_rule_names_are_rejected(self, tmp_path):
        rule = {"name": "cv", "leaf": "career", "globs": ["*cv*"]}
        _write(tmp_path, {"career": _leaf()}, rules=[rule, dict(rule)])
        with pytest.raises(TreeError, match="duplicate rule name 'cv'"):
            load_tree_config(tmp_path)

    def test_rules_and_issuers_files_are_optional(self, tmp_path):
        _write(tmp_path, {"career": _leaf()})
        cfg = load_tree_config(tmp_path)
        assert cfg.rules.rules == ()
        assert cfg.issuers.issuers == {}


class TestWarnings:
    def test_warnings_flag_weak_config(self, tmp_path):
        leaves = {
            "invoices": _leaf(kind="record", retention="5y", path="4_Archives/5y_factures"),
            "shots": _leaf(kind="media", path="3_Resources/5y_screenshots"),
            "career": _leaf(),
        }
        rules = [{"name": "tiny", "leaf": "shots", "globs": ["*ab*"]}]
        issuers = {"hp": {"patterns": ["HP"], "leaves": ["shots"]}}
        warnings = validation_warnings(load_tree_config(_write(tmp_path, leaves, rules, issuers)))
        assert "rule 'tiny': glob '*ab*' has <= 3 literal characters" in warnings
        assert "issuer 'hp': pattern 'HP' has <= 3 characters" in warnings
        assert "leaf 'invoices': no rule or issuer points to it" in warnings
        assert (
            "leaf 'shots': retention prefix outside 4_Archives records: "
            "'3_Resources/5y_screenshots'"
        ) in warnings
        assert not any("career" in warning for warning in warnings)


def test_config_dir_honours_override(monkeypatch, tmp_path):
    monkeypatch.setenv("PARA_FILES_CONFIG_DIR", str(tmp_path))
    assert config_dir() == tmp_path
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_core_tree.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'para_files.core'`.

- [ ] **Step 3: Implement the module**

Create `src/para_files/core/__init__.py`:

```python
"""Redesign core (spec §4): canonical tree, secrets guard; grows in Stage 2."""
```

Create `src/para_files/core/tree.py`:

```python
"""Canonical tree, rules and issuers: strict loading and validation (spec §4.1).

Personal config lives in ``config_dir()``: ``$PARA_FILES_CONFIG_DIR`` or ``~/.config/para-files``.
The repository ships only ``examples/``.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

Kind = Literal["record", "library", "media", "knowledge"]
Retention = Literal["permanent", "ret", "10y", "5y", "2y", "ctr"]

BUCKET_PREFIXES = ("1_", "2_", "3_", "4_")
ARCHIVES = "4_Archives"
MAX_PATH_SEGMENTS = 3  # bucket + 2 levels
MAX_SUBKEY_SEGMENTS = 2
SHORT_LITERALS = 3
SUBKEY_PLACEHOLDERS = frozenset({"{year}", "{month}", "{issuer}", "{thema}"})
LEAF_ID = re.compile(r"^[a-z][a-z0-9_]*$")
RETENTION_PREFIX = re.compile(r"^(\d+y|ret|ctr)_")
GLOB_SYNTAX = re.compile(r"[*?\[\]]")


class TreeError(ValueError):
    """Tree, rules or issuers config breaks a strict rule."""


def config_dir() -> Path:
    """Return the personal config directory."""
    override = os.environ.get("PARA_FILES_CONFIG_DIR")
    return Path(override).expanduser() if override else Path.home() / ".config" / "para-files"


class Leaf(BaseModel):
    """One destination the classifiers may choose."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Kind
    path: str
    describe: str = Field(min_length=1)
    retention: Retention | None = None
    subkey: str | None = None
    keywords: tuple[str, ...] = ()

    @field_validator("path")
    @classmethod
    def _check_path(cls, value: str) -> str:
        parts = value.split("/")
        if not value.startswith(BUCKET_PREFIXES) or any(not p or p != p.strip() for p in parts):
            msg = f"path needs a 1_-4_ bucket and no empty or padded segments: {value!r}"
            raise ValueError(msg)
        if len(parts) > MAX_PATH_SEGMENTS:
            msg = f"path is deeper than a bucket plus 2 levels: {value!r}"
            raise ValueError(msg)
        return value

    @field_validator("subkey")
    @classmethod
    def _check_subkey(cls, value: str | None) -> str | None:
        if value is None:
            return None
        segments = value.split("/")
        if len(segments) > MAX_SUBKEY_SEGMENTS or not set(segments) <= SUBKEY_PLACEHOLDERS:
            msg = f"subkey must be at most 2 of {sorted(SUBKEY_PLACEHOLDERS)}: {value!r}"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _check_retention(self) -> Self:
        if (self.kind == "record") != (self.retention is not None):
            msg = "record leaves need a retention; other kinds must not have one"
            raise ValueError(msg)
        if self.retention not in {None, "permanent"}:
            parts = self.path.split("/")
            prefix = f"{self.retention}_"
            if parts[0] != ARCHIVES or len(parts) < 2 or not parts[1].startswith(prefix):
                msg = f"retention {self.retention} requires 4_Archives/{prefix}<name>: {self.path!r}"
                raise ValueError(msg)
        return self


class Tree(BaseModel):
    """The closed list of leaves."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    leaves: dict[str, Leaf] = Field(min_length=1)

    @field_validator("leaves")
    @classmethod
    def _check_ids(cls, value: dict[str, Leaf]) -> dict[str, Leaf]:
        bad = sorted(key for key in value if not LEAF_ID.match(key))
        if bad:
            msg = f"leaf ids must be snake_case: {bad}"
            raise ValueError(msg)
        return value


class Rule(BaseModel):
    """Filename globs that send a file to one leaf."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    leaf: str
    globs: tuple[str, ...] = Field(min_length=1)


class RulesFile(BaseModel):
    """Contents of rules.yaml."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rules: tuple[Rule, ...] = ()


class Issuer(BaseModel):
    """Patterns naming one issuer, and the leaves its documents may go to."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    patterns: tuple[str, ...] = Field(min_length=1)
    leaves: tuple[str, ...] = Field(min_length=1)


class IssuersFile(BaseModel):
    """Contents of issuers.yaml."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    issuers: dict[str, Issuer] = Field(default_factory=dict)


class TreeConfig(BaseModel):
    """tree.yaml, rules.yaml and issuers.yaml, cross-checked."""

    model_config = ConfigDict(frozen=True)

    tree: Tree
    rules: RulesFile
    issuers: IssuersFile


def _read_yaml(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _reference_problems(tree: Tree, rules: RulesFile, issuers: IssuersFile) -> list[str]:
    names = [rule.name for rule in rules.rules]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    problems = [f"duplicate rule name {name!r}" for name in duplicates]
    problems += [
        f"rule {rule.name!r} points to unknown leaf {rule.leaf!r}"
        for rule in rules.rules
        if rule.leaf not in tree.leaves
    ]
    owner: dict[str, str] = {}
    for name, issuer in issuers.issuers.items():
        problems += [
            f"issuer {name!r} points to unknown leaf {leaf!r}"
            for leaf in issuer.leaves
            if leaf not in tree.leaves
        ]
        for pattern in issuer.patterns:
            first = owner.setdefault(pattern.casefold(), name)
            if first != name:
                problems.append(f"pattern {pattern!r} is used by issuers {first!r} and {name!r}")
    return problems


def load_tree_config(directory: Path | None = None) -> TreeConfig:
    """Load tree.yaml (required), rules.yaml and issuers.yaml (optional), strictly."""
    base = directory or config_dir()
    rules_path = base / "rules.yaml"
    issuers_path = base / "issuers.yaml"
    try:
        tree = Tree.model_validate(_read_yaml(base / "tree.yaml"))
        rules = (
            RulesFile.model_validate(_read_yaml(rules_path)) if rules_path.exists() else RulesFile()
        )
        issuers = (
            IssuersFile.model_validate(_read_yaml(issuers_path))
            if issuers_path.exists()
            else IssuersFile()
        )
    except ValidationError as exc:
        raise TreeError(str(exc)) from exc
    problems = _reference_problems(tree, rules, issuers)
    if problems:
        msg = "; ".join(problems)
        raise TreeError(msg)
    return TreeConfig(tree=tree, rules=rules, issuers=issuers)


def _literals(glob: str) -> int:
    return len(GLOB_SYNTAX.sub("", glob))


def validation_warnings(config: TreeConfig) -> list[str]:
    """Non-fatal problems for the owner to review (shown by `tree --validate` in Stage 3)."""
    warnings = [
        f"rule {rule.name!r}: glob {glob!r} has <= {SHORT_LITERALS} literal characters"
        for rule in config.rules.rules
        for glob in rule.globs
        if _literals(glob) <= SHORT_LITERALS
    ]
    warnings += [
        f"issuer {name!r}: pattern {pattern!r} has <= {SHORT_LITERALS} characters"
        for name, issuer in config.issuers.issuers.items()
        for pattern in issuer.patterns
        if len(pattern) <= SHORT_LITERALS
    ]
    used = {rule.leaf for rule in config.rules.rules}
    used |= {leaf for issuer in config.issuers.issuers.values() for leaf in issuer.leaves}
    warnings += [
        f"leaf {leaf_id!r}: no rule or issuer points to it"
        for leaf_id, leaf in config.tree.leaves.items()
        if leaf_id not in used and leaf.kind != "knowledge"
    ]
    seen: dict[tuple[str, str | None], str] = {}
    for leaf_id, leaf in config.tree.leaves.items():
        first = seen.setdefault((leaf.path, leaf.subkey), leaf_id)
        if first != leaf_id:
            warnings.append(f"leaves {first!r} and {leaf_id!r} share path {leaf.path!r}")
        parts = leaf.path.split("/")
        prefixed = any(RETENTION_PREFIX.match(part) for part in parts[1:])
        allowed = (
            leaf.kind == "record"
            and leaf.retention not in {None, "permanent"}
            and parts[0] == ARCHIVES
        )
        if prefixed and not allowed:
            warnings.append(
                f"leaf {leaf_id!r}: retention prefix outside 4_Archives records: {leaf.path!r}"
            )
    return warnings
```

- [ ] **Step 4: Create the sanitized examples**

Create `examples/tree.yaml`:

```yaml
# Example canonical tree (spec §4.1). Copy to ~/.config/para-files/tree.yaml and edit.
leaves:
  telecom_invoices:
    kind: record
    retention: 5y
    path: 4_Archives/5y_factures/Telephonie
    subkey: "{issuer}/{year}"
    describe: Phone, mobile and internet invoices
    keywords: [facture, invoice, abonnement]
  payslips:
    kind: record
    retention: 10y
    path: 4_Archives/10y_travail/salaires
    subkey: "{year}"
    describe: Payslips and salary statements
    keywords: [salaire, payslip]
  identity_papers:
    kind: record
    retention: permanent
    path: 2_Areas/Officiel
    describe: Civil-status and identity papers kept for life
  books:
    kind: library
    path: 3_Resources/livres
    subkey: "{thema}"
    describe: Books and ebooks
  vendor_docs:
    kind: library
    path: 3_Resources/docs
    subkey: "{issuer}"
    describe: Vendor documentation, datasheets and white papers
  photos:
    kind: media
    path: 4_Archives/photos
    subkey: "{year}"
    describe: Photos
  career:
    kind: knowledge
    path: 2_Areas/carriere
    describe: Career material - CV, evaluations, applications
```

Create `examples/rules.yaml`:

```yaml
# Example rules: filename globs (case-insensitive) -> leaf. First match wins.
rules:
  - name: phone_invoices
    leaf: telecom_invoices
    globs: ["*swisscom*.pdf", "*salt*facture*.pdf"]
  - name: payslips
    leaf: payslips
    globs: ["*payslip*.pdf", "*salaire*.pdf"]
  - name: ebooks
    leaf: books
    globs: ["*.epub", "*.mobi"]
  - name: photos
    leaf: photos
    globs: ["*.jpg", "*.jpeg", "*.heic"]
```

Create `examples/issuers.yaml`:

```yaml
# Example issuers: patterns found in a filename or text preview -> candidate leaves.
issuers:
  swisscom:
    patterns: [Swisscom]
    leaves: [telecom_invoices]
  salt:
    patterns: [Salt Mobile]
    leaves: [telecom_invoices]
  vmware:
    patterns: [VMware]
    leaves: [vendor_docs]
```

Create `examples/README.md`:

````markdown
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
````

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_core_tree.py -q`
Expected: PASS.

Run: `uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run mypy src/`
Expected: clean.

- [ ] **Step 6: Changelog**

In `CHANGELOG.md`, insert directly below the `## [Unreleased]` line, above `### Changed (Stage 1)`:

```markdown
### Added (Stage 1)

- **Canonical tree loader** — `para_files.core.tree` loads `tree.yaml`, `rules.yaml` and `issuers.yaml` from `~/.config/para-files/` strictly (unknown keys, unknown leaves, duplicate issuer patterns and retention/path mismatches are errors) and reports review warnings. Sanitized examples in `examples/`.
```

- [ ] **Step 7: Commit**

```bash
git add src/para_files/core/__init__.py src/para_files/core/tree.py examples/ tests/test_core_tree.py CHANGELOG.md
git commit -m "feat(core): canonical tree loader with kinds, retention and validation" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx"
```

---

### Task 3: Secrets guard

**Files:**
- Create: `src/para_files/core/secrets.py`
- Test: `tests/test_core_secrets.py`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Produces: `para_files.core.secrets.secret_reason(name: str, text: str = "") -> str | None`. The return value is:
  - `"name"` for a secret-looking filename;
  - one of `"private_key"`, `"cloud_access_key"`, `"vault_keys"`, `"recovery_phrase"` or `"credential_value"` for secret-looking content;
  - `None` otherwise.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_core_secrets.py`:

```python
"""Tests for the secrets guard (spec §4.3, S8)."""

from __future__ import annotations

import pytest

from para_files.core.secrets import secret_reason

SWITCH_POLICY = "passwdcfg.minlength: 8\npasswdcfg.oldpasswd: 1\npasswdcfg.lockoutduration: 30\n"


@pytest.mark.parametrize(
    "name",
    [
        "wallet_recovery_phrase.txt",
        "s3-credentials.json",
        "portal_login.txt",
        "license-string.txt",
        "id_rsa",
        "server.pem",
        "vault.kdbx",
        "API_KEY.txt",
    ],
)
def test_secret_names_are_flagged(name):
    assert secret_reason(name) == "name"


@pytest.mark.parametrize(
    "name",
    [
        "2026-01-23_acme_facture.pdf",
        "Bulletin salaire 2019.pdf",
        "vendor-cyber-recovery-overview.pptx",
        "rack-front.jpg",
    ],
)
def test_ordinary_names_pass(name):
    assert secret_reason(name, "Invoice total CHF 49.90") is None


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("-----BEGIN OPENSSH PRIVATE KEY-----\nabc", "private_key"),
        ("aws_access_key_id = AKIAABCDEFGHIJKLMNOP", "cloud_access_key"),
        ('{"root_token": "s.abc", "unseal_keys_b64": []}', "vault_keys"),
        ("Write down your recovery phrase and keep it safe", "recovery_phrase"),
        ("user: admin\npassword: hunter22\n", "credential_value"),
    ],
)
def test_secret_content_is_flagged(text, reason):
    assert secret_reason("notes.txt", text) == reason


@pytest.mark.parametrize("text", [SWITCH_POLICY, "Chapter 3: Backup and Recovery: restore"])
def test_settings_without_values_pass(text):
    assert secret_reason("switch-config.txt", text) is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_core_secrets.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'para_files.core.secrets'`.

- [ ] **Step 3: Implement**

Create `src/para_files/core/secrets.py`:

```python
"""Secrets guard (spec §4.3): files that must never leave the machine or be moved."""

from __future__ import annotations

import re

_NAME = re.compile(
    r"credential|passw|secret|token|api[_-]?key|login"
    r"|recovery[_ -]?(?:phrase|code|key)|seed[_ -]?phrase"
    r"|licen[cs]e[_ -]?(?:key|string|code)"
    r"|id_rsa|id_ed25519|\.(?:pem|key|p12|pfx|kdbx)$",
    re.IGNORECASE,
)
_TEXT: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("cloud_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("vault_keys", re.compile(r'"(?:root_token|unseal_keys(?:_b64|_hex)?)"\s*:')),
    (
        "recovery_phrase",
        re.compile(r"\b(?:recovery|seed|mnemonic)\s+(?:phrase|words?)\b", re.IGNORECASE),
    ),
    (
        "credential_value",
        re.compile(
            r"^\s*[\w.-]*(?:password|passwd|pwd|secret|token|api[_-]?key|mot de passe)"
            r"\s*[:=]\s*\S{4,}",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
)


def secret_reason(name: str, text: str = "") -> str | None:
    """Return why a file looks secret ("name" or a content pattern id), else None.

    Values shorter than 4 characters do not count, so settings such as a switch's
    password-policy lines (``passwdcfg.minlength: 8``) pass.
    """
    if _NAME.search(name):
        return "name"
    for reason, pattern in _TEXT:
        if pattern.search(text):
            return reason
    return None
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_core_secrets.py -q`
Expected: PASS.

Run: `uv run ruff format src/ tests/ && uv run ruff check src/ tests/ && uv run mypy src/`
Expected: clean.

- [ ] **Step 5: Changelog**

Under `### Added (Stage 1)` in `CHANGELOG.md`, append:

```markdown
- **Secrets guard** — `para_files.core.secrets.secret_reason()` flags credential, key, recovery-phrase and similar files by name or content; Stage 1 tools never sample or send such files.
```

- [ ] **Step 6: Commit**

```bash
git add src/para_files/core/secrets.py tests/test_core_secrets.py CHANGELOG.md
git commit -m "feat(core): secrets guard for names and content" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx"
```

---

### Task 4: Tree inventory and the config migration seeder

**Files:**
- Modify: `tests/conftest.py` (add `load_script` and `snapshot` fixtures)
- Create: `scripts/para_inventory.py`, `scripts/migrate_config.py`
- Test: `tests/test_migrate_config.py`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes:
  - `para_files.core.tree.config_dir`, `load_tree_config`, `validation_warnings` (Task 2)
  - `para_files.config.default_reference_tree` (Task 1)
- Produces:
  - **`scripts/para_inventory.py`** (spec §4.1 "Tree cleanup policy", rules R1–R5 and R9; doubtful folders map to `INBOX`):
    - `BUCKETS` (`1_Projets`–`4_Archives`; other top-level folders are never read), `ARCHIVES`, `INBOX`, `RETENTION_PREFIX`, `SYNONYMS`, `MEDIA`, `LIBRARY`, `COUNT_CAP`
    - `nfc(text) -> str`, `strip_prefix(name) -> str`, `retention_of(name) -> str | None`
    - `name_key(name) -> str` (variant key, prefix kept), `stem_key(name) -> str` (prefix dropped; twins and stray prefixes only)
    - `@dataclass Folder(bucket, name, files, subfolders)` with properties `rel` and `trimmed`
    - `count_files(root, cap=COUNT_CAP) -> int`
    - `scan_folders(para_root, buckets=BUCKETS) -> list[Folder]`
    - `retentions_by_stem(documents) -> dict[str, set[str]]` (the taxonomy from `documents.json`)
    - `canonical_map(folders, taxonomy=None) -> dict[str, str]`
    - `make_canon(folders, taxonomy=None) -> Callable[[str], str]`
  - **`scripts/migrate_config.py`:** `main(argv: list[str] | None = None) -> int`. It writes `tree.yaml`, `rules.yaml`, `issuers.yaml` and `review.md` into `--out` (default `config_dir()/"draft"`).
  - **Fixtures in `tests/conftest.py`:**
    - `load_script` → `Callable[[str], ModuleType]`
    - `snapshot` → `Callable[[Path], dict[str, tuple[int, int]]]`

- [ ] **Step 1: Add the shared test fixtures**

Append to `tests/conftest.py` (the existing `Path` and `pytest` imports stay; add the new imports at the top of the import block):

```python
import importlib.util
import os
import sys
from collections.abc import Callable
from types import ModuleType

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"


@pytest.fixture
def load_script() -> Callable[[str], ModuleType]:
    """Import a module from scripts/ by name (scripts/ is not a package)."""

    def _load(name: str) -> ModuleType:
        if str(SCRIPTS_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_DIR))
        spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    return _load


def _snapshot(root: Path) -> dict[str, tuple[int, int]]:
    """Every entry under root with size and mtime_ns; equal snapshots mean nothing changed."""
    entries: dict[str, tuple[int, int]] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for name in [*dirnames, *filenames]:
            path = Path(dirpath) / name
            stat = path.lstat()
            entries[str(path.relative_to(root))] = (stat.st_size, stat.st_mtime_ns)
    return entries


@pytest.fixture
def snapshot() -> Callable[[Path], dict[str, tuple[int, int]]]:
    """Return a function that snapshots a directory tree (read-only checks)."""
    return _snapshot
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_migrate_config.py`:

```python
"""Tests for scripts/para_inventory.py and scripts/migrate_config.py (Stage 1 seeder)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from para_files.core.tree import load_tree_config


def _touch(root: Path, rel: str, content: str = "x") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@pytest.fixture
def para(tmp_path: Path) -> Path:
    root = tmp_path / "PARA"
    for rel in [
        "4_Archives/factures/2024/a.pdf",
        "4_Archives/5y_factures/2024/b.pdf",
        "4_Archives/5y_factures/2025/c.pdf",
        "4_Archives/2y_factures/d.pdf",
        "4_Archives/ctr_factures/e.pdf",
        "4_Archives/travail/2019/p.pdf",
        "4_Archives/10y_travail/2020/q.pdf",
        "4_Archives/10y_travail/2021/q.pdf",
        "4_Archives/5y_travail/{year}/r.pdf",
        "4_Archives/ret_prevoyance/lpp.pdf",
        "4_Archives/photos/2020/x.jpg",
        "4_Archives/evernote/note.enex",
        "3_Resources/docs/one.pdf",
        "3_Resources/docs/two.pdf",
        "3_Resources/documentation/three.pdf",
        "3_Resources/livres/book.epub",
        "3_Resources/administratif/identite/passport.pdf",
        "3_Resources/ret_prevoyance/avs.pdf",
        "3_Resources/prevoyance/avs-old.pdf",
        "3_Resources/5y_screenshots/s1.png",
        "3_Resources/5y_screenshots/s2.png",
        "3_Resources/screenshots/s3.png",
        "2_Areas/carriere/cv.pdf",
        "2_Areas/sante/a.txt",
        "2_Areas/sante/b.txt",
        "2_Areas/santé/c.txt",
        "1_Projets/alpha/readme.md",
        "5_others/kept.txt",
        "0_Inbox/2026-01-23_acme_facture.pdf",
        "0_Inbox/2026-02-23_acme_facture.pdf",
        "0_Inbox/random.txt",
    ]:
        _touch(root, rel)
    return root


@pytest.fixture
def legacy(tmp_path: Path) -> Path:
    rules = {
        "phone": {
            "patterns": ["*swisscom*"],
            "extensions": [".pdf"],
            "destination": "4_Archives/5y_factures/Telephonie/{YYYY}",
        },
        "phone_v2": {"patterns": ["*swisscom*"], "destination": "4_Archives/5y_factures"},
        "vmware_docs": {
            "patterns": ["*vmware*"],
            "destination": "3_Resources/documentation/{technology}",
            "known_vendors": ["VMware", "Broadcom"],
        },
        "old_bills": {"patterns": ["*bill*"], "destination": "4_Archives/factures"},
        "photos": {"extensions": [".jpg"], "destination": "4_Archives/photos/{YYYY}"},
        "tiny": {"patterns": ["*ab*", "*cv*.pdf"], "destination": "2_Areas/carriere"},
        "nowhere": {"patterns": ["*zzz*"], "destination": "9_Nowhere/x"},
        "flatten": {"patterns": ["*tmp*"], "action": "flatten_to_inbox"},
    }
    path = tmp_path / "legacy.yaml"
    path.write_text(yaml.safe_dump({"routing_rules": rules}, sort_keys=False))
    return path


def _doc(sub_id: str, retention: str, pattern: str, **extra: object) -> dict[str, object]:
    return {
        "sub_id": sub_id,
        "name": sub_id,
        "examples": [],
        "keywords": [],
        "retention": retention,
        "paper_required": False,
        "para_pattern": pattern,
        **extra,
    }


@pytest.fixture
def documents(tmp_path: Path) -> Path:
    issuers = [
        {"name": "Swisscom", "patterns": ["Swisscom"]},
        {"name": "Salt", "patterns": ["Salt Mobile", "swisscom"]},
    ]
    invoices = [
        _doc("telecom", "5_years", "4_Archives/5y_factures/{issuer}/{year}", issuers=issuers),
        _doc("warranty", "warranty_2_years", "4_Archives/2y_factures/{issuer}/{year}"),
        _doc("tenant", "contract_duration", "4_Archives/ctr_factures/{issuer}"),
    ]
    other = [
        _doc("payslips", "10_years", "4_Archives/10y_travail/{issuer}/{year}"),
        _doc("id", "permanent", "3_Resources/administratif/identite"),
    ]
    data = {
        "categories": [
            {"id": "A", "name": "Invoices", "description": "", "documents": invoices},
            {"id": "B", "name": "Other", "description": "", "documents": other},
        ]
    }
    path = tmp_path / "documents.json"
    path.write_text(json.dumps(data))
    return path


@pytest.fixture
def mapping(load_script, para, documents):
    inventory = load_script("para_inventory")
    taxonomy = inventory.retentions_by_stem(json.loads(documents.read_text()))
    return inventory.canonical_map(inventory.scan_folders(para), taxonomy)


@pytest.fixture
def draft(load_script, para, legacy, documents, tmp_path):
    migrate = load_script("migrate_config")
    out = tmp_path / "draft"
    argv = ["--para-root", str(para), "--legacy-tree", str(legacy)]
    argv += ["--documents", str(documents), "--out", str(out)]
    assert migrate.main(argv) == 0
    return out


class TestInventory:
    def test_count_files_stops_at_cap(self, load_script, tmp_path):
        inventory = load_script("para_inventory")
        for index in range(7):
            _touch(tmp_path, f"many/{index}.jpg")
        assert inventory.count_files(tmp_path / "many", cap=5) == 5

    def test_only_buckets_are_scanned_and_symlinks_are_skipped(self, load_script, para, tmp_path):
        _touch(tmp_path, "outside/secret.txt")
        (para / "3_Resources/linked").symlink_to(tmp_path / "outside", target_is_directory=True)
        inventory = load_script("para_inventory")
        rels = {folder.rel for folder in inventory.scan_folders(para)}
        assert "1_Projets/alpha" in rels
        assert "3_Resources/linked" not in rels
        assert not any(rel.startswith(("0_Inbox", "5_others")) for rel in rels)

    def test_retention_prefixes_never_merge(self, mapping):
        for prefix in ("2y", "5y", "ctr"):
            assert mapping[f"4_Archives/{prefix}_factures"] == f"4_Archives/{prefix}_factures"

    def test_split_stem_legacy_folder_is_doubtful(self, mapping):
        assert mapping["4_Archives/factures"] == "0_Inbox"

    def test_twin_and_stray_prefix_fold_into_the_taxonomy_prefix(self, mapping):
        assert mapping["4_Archives/travail"] == "4_Archives/10y_travail"
        assert mapping["4_Archives/5y_travail"] == "4_Archives/10y_travail"
        assert mapping["4_Archives/10y_travail"] == "4_Archives/10y_travail"

    def test_name_variants_fold_into_the_largest(self, mapping):
        assert mapping["2_Areas/santé"] == "2_Areas/sante"
        assert mapping["2_Areas/sante"] == "2_Areas/sante"

    def test_synonyms_fold_into_the_larger(self, mapping):
        assert mapping["3_Resources/documentation"] == "3_Resources/docs"
        assert mapping["2_Areas/carriere"] == "2_Areas/carriere"

    def test_prefixes_outside_archives(self, mapping):
        assert mapping["3_Resources/ret_prevoyance"] == "4_Archives/ret_prevoyance"
        assert mapping["3_Resources/prevoyance"] == "4_Archives/ret_prevoyance"
        assert mapping["3_Resources/5y_screenshots"] == "3_Resources/screenshots"
        assert mapping["3_Resources/screenshots"] == "3_Resources/screenshots"

    def test_canon_resolves_unknown_paths_by_variant_and_synonym(self, load_script, para):
        inventory = load_script("para_inventory")
        canon = inventory.make_canon(inventory.scan_folders(para))
        assert canon("3_Resources/books") == "3_Resources/livres"
        assert canon("3_Resources/Documentation") == "3_Resources/docs"
        assert canon("9_Nowhere/x") == "9_Nowhere/x"


class TestDraftTree:
    def test_draft_is_valid_and_kinds_are_proposed(self, draft):
        leaves = load_tree_config(draft).tree.leaves
        for absent in (
            "archives_factures",
            "archives_travail",
            "archives_5y_travail",
            "resources_documentation",
            "resources_ret_prevoyance",
            "resources_5y_screenshots",
        ):
            assert absent not in leaves
        invoices = leaves["archives_5y_factures"]
        assert (invoices.kind, invoices.retention) == ("record", "5y")
        assert invoices.subkey == "{issuer}/{year}"
        assert leaves["archives_2y_factures"].retention == "2y"
        assert leaves["archives_ctr_factures"].retention == "ctr"
        assert leaves["archives_10y_travail"].retention == "10y"
        assert leaves["archives_ret_prevoyance"].retention == "ret"
        assert leaves["resources_docs"].kind == "library"
        assert leaves["resources_livres"].subkey == "{thema}"
        assert leaves["resources_screenshots"].kind == "media"
        assert leaves["archives_photos"].kind == "media"
        identity = leaves["resources_administratif"]
        assert (identity.kind, identity.retention) == ("record", "permanent")
        assert leaves["archives_evernote"].retention == "permanent"
        assert leaves["areas_carriere"].kind == "knowledge"
        assert leaves["projects_alpha"].kind == "knowledge"
        assert not any(leaf.path.startswith("5_others") for leaf in leaves.values())

    def test_nfd_folder_names_become_nfc_leaves(self, load_script, tmp_path, legacy, documents):
        root = tmp_path / "PARA"
        _touch(root, "2_Areas/matière/notes.txt")
        out = tmp_path / "nfd-draft"
        migrate = load_script("migrate_config")
        argv = ["--para-root", str(root), "--legacy-tree", str(legacy)]
        argv += ["--documents", str(documents), "--out", str(out)]
        assert migrate.main(argv) == 0
        leaves = load_tree_config(out).tree.leaves
        assert leaves["areas_matiere"].path == "2_Areas/matière"


class TestDraftRules:
    def test_rules_keep_the_legacy_and_of_patterns_and_extensions(self, draft):
        rules = {rule.name: rule for rule in load_tree_config(draft).rules.rules}
        assert rules["phone"].leaf == "archives_5y_factures"
        assert rules["phone"].globs == ("*swisscom*.pdf",)
        assert rules["vmware_docs"].leaf == "resources_docs"
        assert rules["photos"].globs == ("*.jpg",)
        assert rules["tiny"].globs == ("*cv*.pdf",)
        assert {"phone_v2", "old_bills", "nowhere", "flatten"}.isdisjoint(rules)

    def test_extension_only_rules_come_last(self, draft):
        names = [rule.name for rule in load_tree_config(draft).rules.rules]
        assert names == ["phone", "vmware_docs", "tiny", "photos"]


class TestDraftIssuers:
    def test_issuers_come_from_documents_and_legacy_vendors(self, draft):
        issuers = load_tree_config(draft).issuers.issuers
        assert issuers["swisscom"].leaves == ("archives_5y_factures",)
        assert issuers["salt"].patterns == ("Salt Mobile",)
        assert issuers["vmware"].leaves == ("resources_docs",)
        assert issuers["broadcom"].patterns == ("Broadcom",)


class TestReview:
    def test_review_lists_merges_doubtful_conflicts_and_inbox_families(self, draft):
        review = (draft / "review.md").read_text()
        assert "merge: 4_Archives/5y_travail -> 4_Archives/10y_travail" in review
        assert "doubtful: 4_Archives/factures -> 0_Inbox" in review
        assert "rule old_bills: destination 4_Archives/factures is doubtful" in review
        assert "already used by swisscom" in review
        assert "acme facture.pdf: 2 files" in review
        assert "random" not in review


class TestReadOnly:
    def test_para_root_is_untouched(self, load_script, para, legacy, documents, tmp_path, snapshot):
        before = snapshot(para)
        migrate = load_script("migrate_config")
        argv = ["--para-root", str(para), "--legacy-tree", str(legacy)]
        argv += ["--documents", str(documents), "--out", str(tmp_path / "out")]
        assert migrate.main(argv) == 0
        assert snapshot(para) == before

    def test_out_inside_para_root_is_refused(self, load_script, para, legacy, documents):
        migrate = load_script("migrate_config")
        argv = ["--para-root", str(para), "--legacy-tree", str(legacy)]
        argv += ["--documents", str(documents), "--out", str(para / "draft")]
        with pytest.raises(SystemExit):
            migrate.main(argv)
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/test_migrate_config.py -q`
Expected: FAIL with `FileNotFoundError` (no `scripts/para_inventory.py` yet).

- [ ] **Step 4: Implement `scripts/para_inventory.py`**

```python
"""Inventory of the PARA buckets and the canonical folder map (Stage 1, read-only).

Each first-level folder maps to its canonical folder, or to INBOX when it is doubtful
(spec §4.1 "Tree cleanup policy": doubtful content goes back to 0_Inbox in a later batch).
A retention prefix is part of a folder's identity: name-based rules never merge two
different prefixes; only a prefix the taxonomy does not define for a stem is remapped.
"""

from __future__ import annotations

import os
import re
import unicodedata
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


BUCKETS = ("1_Projets", "2_Areas", "3_Resources", "4_Archives")
ARCHIVES = "4_Archives"
INBOX = "0_Inbox"
RETENTION_PREFIX = re.compile(r"^(\d+y|ret|ctr)_")
SYNONYMS = (("livres", "books"), ("formation", "formations"), ("docs", "documentation"))
MEDIA = frozenset({"photos", "videos", "media", "screenshots"})
LIBRARY = frozenset(
    {
        "livres",
        "books",
        "docs",
        "documentation",
        "formation",
        "formations",
        "certifications",
        "courses-completed",
        "licences",
        "isos",
        "programmes",
    }
)
COUNT_CAP = 5000


def nfc(text: str) -> str:
    """Text in Unicode NFC (macOS and SMB volumes may hand back NFD names)."""
    return unicodedata.normalize("NFC", text)


def strip_prefix(name: str) -> str:
    """Folder name without its retention prefix, trimmed and lower-cased."""
    return RETENTION_PREFIX.sub("", nfc(name).strip()).lower()


def retention_of(name: str) -> str | None:
    """Retention prefix of a folder name (5y, 10y, 2y, ret, ctr), or None."""
    match = RETENTION_PREFIX.match(nfc(name).strip())
    return match.group(1) if match else None


def name_key(name: str) -> str:
    """Variant key: case, accents, separators, plural and padding folded; prefix KEPT."""
    text = unicodedata.normalize("NFKD", nfc(name).strip().lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[\s_\-.]+", " ", text).strip()
    return re.sub(r"(?<=\w\w)[sx]$", "", text)


def stem_key(name: str) -> str:
    """name_key without the retention prefix; only used to find twins and stray prefixes."""
    return name_key(RETENTION_PREFIX.sub("", nfc(name).strip()))


@dataclass
class Folder:
    """A first-level folder of a PARA bucket."""

    bucket: str
    name: str  # NFC; may still carry padding spaces, as on disk
    files: int
    subfolders: list[str] = field(default_factory=list)

    @property
    def rel(self) -> str:
        """bucket/name as on disk (NFC)."""
        return f"{self.bucket}/{self.name}"

    @property
    def trimmed(self) -> str:
        """bucket/name with the padding removed."""
        return f"{self.bucket}/{self.name.strip()}"


def count_files(root: Path, cap: int = COUNT_CAP) -> int:
    """Count non-hidden files under root, stopping at cap; never follows symlinks."""
    total = 0
    for _dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        total += sum(1 for name in filenames if not name.startswith("."))
        if total >= cap:
            return cap
    return total


def scan_folders(para_root: Path, buckets: tuple[str, ...] = BUCKETS) -> list[Folder]:
    """First-level folders of each bucket; other top-level folders are never read."""
    folders: list[Folder] = []
    for bucket in buckets:
        base = para_root / bucket
        if not base.is_dir():
            continue
        for entry in sorted(base.iterdir(), key=lambda path: path.name):
            if entry.is_symlink() or not entry.is_dir() or entry.name.startswith((".", "_")):
                continue
            subfolders = sorted(
                nfc(sub.name)
                for sub in entry.iterdir()
                if sub.is_dir() and not sub.is_symlink() and not sub.name.startswith(".")
            )
            folders.append(Folder(bucket, nfc(entry.name), count_files(entry), subfolders))
    return folders


def retentions_by_stem(documents: dict[str, Any]) -> dict[str, set[str]]:
    """Archive stem -> retention prefixes documents.json files it under (the taxonomy)."""
    found: dict[str, set[str]] = {}
    for category in documents.get("categories", []):
        for doc in category.get("documents", []):
            parts = (doc.get("para_pattern") or "").split("/")
            prefix = retention_of(parts[1]) if len(parts) > 1 and parts[0] == ARCHIVES else None
            if prefix:
                found.setdefault(stem_key(parts[1]), set()).add(prefix)
    return found


def _group_targets(
    bucket: str, stem: str, group: list[Folder], taxonomy: dict[str, set[str]]
) -> dict[str, str]:
    """Targets for one (bucket, stem) group of folders."""
    reps: dict[str, Folder] = {}
    for folder in sorted(group, key=lambda f: (-f.files, f.name)):
        reps.setdefault(name_key(folder.name), folder)  # R4: variants fold into the largest
    rep_target = {key: rep.trimmed for key, rep in reps.items()}
    prefixed = [rep for rep in reps.values() if retention_of(rep.name)]
    plain = [rep for rep in reps.values() if not retention_of(rep.name)]
    if bucket != ARCHIVES and prefixed:  # R9: retention prefixes belong to the vault
        largest = max(prefixed, key=lambda f: f.files)
        if strip_prefix(largest.name) in MEDIA | LIBRARY:
            bare = RETENTION_PREFIX.sub("", largest.name.strip())
            target = plain[0].trimmed if plain else f"{bucket}/{bare}"
        else:
            target = f"{ARCHIVES}/{largest.name.strip()}"
        rep_target = dict.fromkeys(rep_target, target)
    elif bucket == ARCHIVES and (prefixed or stem in taxonomy):
        allowed = taxonomy.get(stem) or {retention_of(rep.name) for rep in prefixed}
        keepers = [rep.trimmed for rep in prefixed if retention_of(rep.name) in allowed]
        single = keepers[0] if len(allowed) == 1 and len(keepers) == 1 else None
        for key, rep in reps.items():
            prefix = retention_of(rep.name)
            if prefix in allowed:
                continue  # a prefix the taxonomy defines: its own canonical folder
            if single is not None:
                rep_target[key] = single  # R1 legacy twin, R3 stray prefix
            elif len(allowed) > 1:
                rep_target[key] = INBOX  # R2: legacy or stray folder of a split stem, doubtful
    return {folder.rel: rep_target[name_key(folder.name)] for folder in group}


def _target_named(targets: list[str], bucket: str, word: str) -> str | None:
    """The target in bucket whose folder name has the same variant key as word, if any."""
    for target in targets:
        target_bucket, _, name = target.partition("/")
        if target_bucket == bucket and name_key(name) == name_key(word):
            return target
    return None


def canonical_map(
    folders: list[Folder], taxonomy: dict[str, set[str]] | None = None
) -> dict[str, str]:
    """Map each folder's rel path (as on disk) to its canonical rel path, or to INBOX."""
    taxonomy = taxonomy or {}
    groups: dict[tuple[str, str], list[Folder]] = {}
    for folder in folders:
        groups.setdefault((folder.bucket, stem_key(folder.name)), []).append(folder)
    mapping: dict[str, str] = {}
    for (bucket, stem), group in groups.items():
        mapping.update(_group_targets(bucket, stem, group, taxonomy))
    size: Counter[str] = Counter()
    for folder in folders:
        size[mapping[folder.rel]] += folder.files
    for first, second in SYNONYMS:  # R5: the smaller folds into the larger
        for bucket in BUCKETS:
            a = _target_named(list(size), bucket, first)
            b = _target_named(list(size), bucket, second)
            if a is None or b is None or a == b:
                continue
            keep, drop = (a, b) if size[a] >= size[b] else (b, a)
            mapping = {rel: keep if target == drop else target for rel, target in mapping.items()}
            size[keep] += size.pop(drop)
    return mapping


def make_canon(
    folders: list[Folder], taxonomy: dict[str, set[str]] | None = None
) -> Callable[[str], str]:
    """Return canon(rel) -> canonical rel or INBOX; unknown paths match by variant key."""
    mapping = canonical_map(folders, taxonomy)
    by_trimmed = {folder.trimmed: mapping[folder.rel] for folder in folders}
    by_key = {(folder.bucket, name_key(folder.name)): mapping[folder.rel] for folder in folders}
    for first, second in SYNONYMS:
        for bucket in BUCKETS:
            for word, other in ((first, second), (second, first)):
                known = by_key.get((bucket, name_key(other)))
                if known is not None:
                    by_key.setdefault((bucket, name_key(word)), known)

    def canon(rel: str) -> str:
        key = nfc(rel).strip()
        if key in by_trimmed:
            return by_trimmed[key]
        bucket, _, name = key.partition("/")
        return by_key.get((bucket, name_key(name)), key)

    return canon
```

- [ ] **Step 5: Implement `scripts/migrate_config.py`**

```python
"""Draft tree.yaml, rules.yaml and issuers.yaml from the current PARA tree (Stage 1, throwaway).

Read-only on the PARA root. Writes only to --out (default: <config dir>/draft).

Usage:
    uv run python scripts/migrate_config.py --para-root "$PARA"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from para_inventory import (
    INBOX,
    LIBRARY,
    MEDIA,
    Folder,
    make_canon,
    nfc,
    retention_of,
    retentions_by_stem,
    scan_folders,
    strip_prefix,
)

from para_files.config import default_reference_tree
from para_files.core.tree import config_dir, load_tree_config, validation_warnings


BOOKS = frozenset({"livres", "books"})
TAGS = {
    "1_Projects": "projects",
    "1_Projets": "projects",
    "2_Areas": "areas",
    "3_Resources": "resources",
    "4_Archives": "archives",
}
RETENTIONS = frozenset({"ret", "10y", "5y", "2y", "ctr"})
RETENTION_FROM_DOCS = {
    "permanent": "permanent",
    "retirement": "ret",
    "10_years": "10y",
    "5_years": "5y",
    "contract_duration": "ctr",
    "warranty_2_years": "2y",
}
YEAR = re.compile(r"^(19|20)\d{2}$")
PLACEHOLDER = re.compile(r"\{[^}]+\}")
SUBKEY_FROM_DOCS = ("{issuer}", "{year}")
Canon = Callable[[str], str]


def slug(text: str) -> str:
    """ASCII snake_case of text."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", ascii_text.lower()).strip("_")


def folder_of(pattern: str) -> str | None:
    """bucket/folder of a destination pattern, or None when that part is a placeholder."""
    parts = [nfc(part).strip() for part in pattern.split("/") if part.strip()]
    if len(parts) < 2 or PLACEHOLDER.search(parts[0]) or PLACEHOLDER.search(parts[1]):
        return None
    return f"{parts[0]}/{parts[1]}"


def document_folders(documents: dict[str, Any], canon: Canon) -> dict[str, tuple[str, str | None]]:
    """Canonical folder -> (retention, subkey) taken from documents.json."""
    found: dict[str, tuple[str, str | None]] = {}
    for category in documents.get("categories", []):
        for doc in category.get("documents", []):
            pattern = doc.get("para_pattern") or category.get("para_pattern") or ""
            folder = folder_of(pattern)
            if folder is None:
                continue
            subkey = "/".join(p for p in SUBKEY_FROM_DOCS if p in pattern) or None
            retention = RETENTION_FROM_DOCS.get(doc.get("retention", ""), "permanent")
            target = canon(folder)
            if target != INBOX:
                found.setdefault(target, (retention, subkey))
    return found


def propose_leaf(
    folder: Folder, docs: dict[str, tuple[str, str | None]], notes: list[str]
) -> dict[str, Any]:
    """kind / retention / subkey / describe proposal for one canonical folder."""
    rel = f"{folder.bucket}/{folder.name.strip()}"
    name = strip_prefix(folder.name)
    subs = [s.strip() for s in folder.subfolders]
    years = [s for s in subs if YEAR.match(s)]
    year_subkey = "{year}" if subs and len(years) * 2 >= len(subs) else None
    others = [s for s in subs if not YEAR.match(s)][:10]
    describe = folder.name.strip() + (f" (contains: {', '.join(others)})" if others else "")
    leaf: dict[str, Any] = {"path": rel, "describe": describe}
    prefix = retention_of(folder.name)
    doc_retention, doc_subkey = docs.get(rel, (None, None))
    if name in MEDIA:
        leaf.update(kind="media", subkey="{year}")
    elif name in LIBRARY:
        leaf.update(kind="library", subkey="{thema}" if name in BOOKS else None)
    elif prefix in RETENTIONS and folder.bucket == "4_Archives":
        leaf.update(kind="record", retention=prefix, subkey=doc_subkey or year_subkey)
    elif prefix is not None or doc_retention is not None or folder.bucket == "4_Archives":
        if prefix is not None or doc_retention not in (None, "permanent"):
            notes.append(f"{rel}: retention needs a decision; proposed permanent")
        elif doc_retention is None:
            notes.append(f"{rel}: unprefixed archive folder; proposed record/permanent")
        leaf.update(kind="record", retention="permanent", subkey=doc_subkey or year_subkey)
    else:
        leaf.update(kind="knowledge")
    return {key: value for key, value in leaf.items() if value is not None}


def draft_tree(
    folders: list[Folder], canon: Canon, docs: dict[str, tuple[str, str | None]], notes: list[str]
) -> dict[str, dict[str, Any]]:
    """One proposed leaf per canonical folder; merged and doubtful folders are noted only."""
    leaves: dict[str, dict[str, Any]] = {}
    for folder in folders:
        rel = folder.trimmed
        target = canon(rel)
        if target == INBOX:
            notes.append(f"doubtful: {rel} -> {INBOX} (later batch)")
            continue
        if target != rel:
            notes.append(f"merge: {rel} -> {target}")
            continue
        base = f"{TAGS.get(folder.bucket, slug(folder.bucket))}_{slug(folder.name)}"
        leaf_id, counter = base, 2
        while leaf_id in leaves:
            leaf_id, counter = f"{base}_{counter}", counter + 1
        leaves[leaf_id] = propose_leaf(folder, docs, notes)
    return leaves


def combine_globs(patterns: list[str], extensions: list[str]) -> list[str]:
    """Globs equivalent to the legacy rule: a filename pattern AND an extension."""
    exts = [e.lower() if e.startswith(".") else f".{e.lower()}" for e in extensions]
    if not patterns:
        return [f"*{ext}" for ext in exts]
    if not exts:
        return list(dict.fromkeys(patterns))
    globs = []
    for pattern in patterns:
        for ext in exts:
            if pattern.lower().endswith(ext):
                globs.append(pattern)
            elif pattern.endswith("*"):
                globs.append(f"{pattern}{ext}")
    return list(dict.fromkeys(globs))


def is_short_substring(glob: str) -> bool:
    """A '*xy*'-style glob with 3 or fewer literal characters (matches far too much)."""
    literals = re.sub(r"[*?\[\]]", "", glob)
    return glob.startswith("*") and glob.endswith("*") and len(literals) <= 3


def draft_rules(
    legacy_rules: dict[str, Any], canon: Canon, leaf_of: dict[str, str], notes: list[str]
) -> tuple[list[dict[str, Any]], list[tuple[str, list[str], str | None]]]:
    """Rules (pattern rules first, extension-only rules last) and issuers found in rules."""
    pattern_rules: list[dict[str, Any]] = []
    extension_rules: list[dict[str, Any]] = []
    issuers: list[tuple[str, list[str], str | None]] = []
    for name, rule in legacy_rules.items():
        if not isinstance(rule, dict) or not rule.get("destination"):
            notes.append(f"rule {name}: no destination, dropped")
            continue
        if name.endswith("_v2") and name[:-3] in legacy_rules:
            notes.append(f"rule {name}: copy of {name[:-3]}, dropped")
            continue
        folder = folder_of(rule["destination"])
        target = canon(folder) if folder else None
        leaf = leaf_of.get(target) if target else None
        if leaf is None:
            reason = "is doubtful" if target == INBOX else "has no leaf"
            notes.append(f"rule {name}: destination {rule['destination']} {reason}, dropped")
            continue
        if rule.get("action"):
            notes.append(f"rule {name}: action {rule['action']} ignored")
        issuers += [
            (i["name"], list(i.get("patterns") or []), leaf) for i in rule.get("issuers") or []
        ]
        vendors = [*(rule.get("known_vendors") or []), *(rule.get("known_technologies") or [])]
        issuers += [(vendor, [vendor], leaf) for vendor in vendors]
        patterns = list(rule.get("patterns") or [])
        globs = combine_globs(patterns, list(rule.get("extensions") or []))
        short = [glob for glob in globs if is_short_substring(glob)]
        if short:
            notes.append(f"rule {name}: dropped short globs {short}")
        globs = [glob for glob in globs if not is_short_substring(glob)]
        if not globs:
            notes.append(f"rule {name}: no usable glob left, dropped")
            continue
        target = pattern_rules if patterns else extension_rules
        target.append({"name": name, "leaf": leaf, "globs": globs})
    return pattern_rules + extension_rules, issuers


def draft_issuers(
    documents: dict[str, Any],
    canon: Canon,
    leaf_of: dict[str, str],
    extra: list[tuple[str, list[str], str | None]],
    notes: list[str],
) -> dict[str, dict[str, list[str]]]:
    """Issuers from documents.json plus those found in legacy rules; patterns stay unique."""
    entries: list[tuple[str, list[str], str | None]] = []
    for category in documents.get("categories", []):
        for doc in category.get("documents", []):
            folder = folder_of(doc.get("para_pattern") or category.get("para_pattern") or "")
            leaf = leaf_of.get(canon(folder)) if folder else None
            entries += [
                (i["name"], list(i.get("patterns") or []), leaf) for i in doc.get("issuers") or []
            ]
    entries += extra
    issuers: dict[str, dict[str, list[str]]] = {}
    owner: dict[str, str] = {}
    for name, patterns, leaf in entries:
        key = slug(name) or "issuer"
        if leaf is None:
            notes.append(f"issuer {name}: destination has no leaf, skipped")
            continue
        entry = issuers.setdefault(key, {"patterns": [], "leaves": []})
        for pattern in patterns:
            first = owner.setdefault(nfc(pattern).casefold(), key)
            if first != key:
                notes.append(f"issuer {key}: pattern {pattern!r} already used by {first}, skipped")
            elif pattern not in entry["patterns"]:
                entry["patterns"].append(pattern)
        if leaf not in entry["leaves"]:
            entry["leaves"].append(leaf)
    return {key: value for key, value in issuers.items() if value["patterns"]}


def inbox_families(inbox: Path) -> list[tuple[str, int, str]]:
    """Recurring filename families in the inbox: (family, count, example), count >= 2."""
    counts: Counter[str] = Counter()
    example: dict[str, str] = {}
    for _dirpath, dirnames, filenames in os.walk(inbox):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for filename in filenames:
            if filename.startswith("."):
                continue
            path = Path(nfc(filename))
            stem = re.sub(r"\d+", "#", path.stem.lower())
            family = re.sub(r"[#_\-\s.()]+", " ", stem).strip() + path.suffix.lower()
            counts[family] += 1
            example.setdefault(family, path.name)
    return [(family, n, example[family]) for family, n in counts.most_common() if n >= 2]


def write_review(
    out: Path,
    leaves: dict[str, dict[str, Any]],
    notes: list[str],
    families: list[tuple[str, int, str]],
    warnings: list[str],
) -> None:
    """review.md: what the seeder decided and what the owner must decide."""
    kinds = Counter(leaf["kind"] for leaf in leaves.values())
    summary = ", ".join(f"{kind} {n}" for kind, n in sorted(kinds.items()))
    lines = [
        "# Draft review",
        "",
        f"{len(leaves)} leaves proposed ({summary}). Target 20-30: merge or drop leaves, "
        "then copy tree.yaml, rules.yaml and issuers.yaml one level up.",
        "",
        "## Notes",
        "",
        *[f"- {note}" for note in notes],
        "",
        "## Recurring inbox families (issuer candidates)",
        "",
        *[f"- {family}: {n} files, e.g. {example}" for family, n, example in families],
        "",
        "## Validation warnings",
        "",
        *[f"- {warning}" for warning in warnings],
        "",
    ]
    (out / "review.md").write_text("\n".join(lines), encoding="utf-8")


def _dump(path: Path, data: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Write the draft config and review.md; return 0."""
    parser = argparse.ArgumentParser(description="Draft tree.yaml, rules.yaml and issuers.yaml.")
    parser.add_argument("--para-root", type=Path, required=True)
    parser.add_argument("--legacy-tree", type=Path, default=None)
    parser.add_argument("--documents", type=Path, default=Path("config/documents.json"))
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    para_root = args.para_root.expanduser().resolve()
    out = (args.out or config_dir() / "draft").expanduser().resolve()
    if out.is_relative_to(para_root):
        parser.error("--out must be outside the PARA root")
    legacy_path = args.legacy_tree or default_reference_tree()
    legacy = yaml.safe_load(legacy_path.read_text(encoding="utf-8")) or {}
    documents = json.loads(args.documents.read_text(encoding="utf-8"))

    folders = scan_folders(para_root)
    canon = make_canon(folders, retentions_by_stem(documents))
    notes: list[str] = []
    leaves = draft_tree(folders, canon, document_folders(documents, canon), notes)
    leaf_of = {leaf["path"]: leaf_id for leaf_id, leaf in leaves.items()}
    rules, rule_issuers = draft_rules(legacy.get("routing_rules") or {}, canon, leaf_of, notes)
    issuers = draft_issuers(documents, canon, leaf_of, rule_issuers, notes)

    out.mkdir(parents=True, exist_ok=True)
    _dump(out / "tree.yaml", {"leaves": leaves})
    _dump(out / "rules.yaml", {"rules": rules})
    _dump(out / "issuers.yaml", {"issuers": issuers})
    warnings = validation_warnings(load_tree_config(out))
    write_review(out, leaves, notes, inbox_families(para_root / "0_Inbox"), warnings)
    print(f"{len(leaves)} leaves, {len(rules)} rules, {len(issuers)} issuers -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run ruff format scripts/ tests/ && uv run pytest tests/test_migrate_config.py -q`
Expected: PASS.

Run: `uv run ruff check src/ tests/ && uv run mypy src/`
Expected: clean.

- [ ] **Step 7: Changelog**

Under `### Added (Stage 1)` in `CHANGELOG.md`, append:

```markdown
- **Config migration seeder** — `scripts/migrate_config.py` drafts `tree.yaml`, `rules.yaml` and `issuers.yaml` from the current PARA tree, the legacy routing rules and `config/documents.json`. It folds legacy twins, name variants, stray retention prefixes and synonym folders (retention prefixes defined by the taxonomy never merge), marks doubtful folders for a later return to `0_Inbox`, proposes a kind and retention per leaf, keeps the legacy pattern-and-extension semantics, and lists recurring inbox families as issuer candidates in `review.md`. Read-only on the PARA root.
```

- [ ] **Step 8: Commit**

```bash
git add tests/conftest.py scripts/para_inventory.py scripts/migrate_config.py tests/test_migrate_config.py CHANGELOG.md
git commit -m "feat(scripts): draft the canonical tree from the current PARA tree" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx"
```

---

### Task 5: (removed) Tree-cleanup plan generator

Moved out of Stage 1: the owner starts with the inbox, and the existing tree is reorganized later in batches on demand (spec §4.1 "Tree cleanup policy", §5 "Batch reorganization"). Nothing to implement; skip to Task 6.

---

### Task 6: Golden corpus builder

**Files:**
- Create: `scripts/build_golden.py`
- Test: `tests/test_build_golden.py`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes:
  - `para_files.core.tree.TreeConfig`, `config_dir`, `load_tree_config` (Task 2)
  - `para_files.core.secrets.secret_reason` (Task 3)
  - `para_inventory.nfc` (Task 4)
- Produces: `scripts/build_golden.py` with:
  - `WALK_CAP: int`
  - `leaf_files(root, excluded, rng) -> list[Path]`
  - `build_golden(para_root, config, *, per_leaf, knowledge_per_leaf, seed) -> tuple[list[dict], list[str]]`
  - `main(argv) -> int`

  Golden rows have the shape `{"path": <relative to PARA root, NFC>, "leaf": <leaf id>, "kind": <kind>}`. Task 7 (`eval.py`), Task 8 (`run_baseline.py`) and Task 9 (`bakeoff.py`) all read this format.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_build_golden.py`:

```python
"""Tests for scripts/build_golden.py (golden corpus sampling, spec §4.5)."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest
import yaml

from para_files.core.tree import load_tree_config


def _touch(root: Path, rel: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x")


@pytest.fixture
def para(tmp_path: Path) -> Path:
    root = tmp_path / "PARA"
    for index in range(12):
        _touch(root, f"4_Archives/5y_factures/2024/inv{index}.pdf")
    for index in range(3):
        _touch(root, f"4_Archives/5y_factures/Telephonie/tel{index}.pdf")
    _touch(root, "4_Archives/5y_factures/s3-credentials.json")
    _touch(root, "4_Archives/5y_factures/.hidden.pdf")
    for index in range(8):
        _touch(root, f"2_Areas/carriere/cv{index}.pdf")
    return root


@pytest.fixture
def config(tmp_path: Path):
    leaves = {
        "invoices": {
            "kind": "record", "retention": "5y", "path": "4_Archives/5y_factures",
            "describe": "Invoices",
        },
        "telecom": {
            "kind": "record", "retention": "5y", "path": "4_Archives/5y_factures/Telephonie",
            "describe": "Telecom invoices",
        },
        "career": {"kind": "knowledge", "path": "2_Areas/carriere", "describe": "Career"},
        "books": {"kind": "library", "path": "3_Resources/livres", "describe": "Books"},
    }
    directory = tmp_path / "cfg"
    directory.mkdir()
    (directory / "tree.yaml").write_text(yaml.safe_dump({"leaves": leaves}))
    return load_tree_config(directory)


def _build(module, para, config, seed=1):
    return module.build_golden(para, config, per_leaf=10, knowledge_per_leaf=5, seed=seed)


def test_samples_per_leaf_without_crossing_into_nested_leaves(load_script, para, config):
    golden = load_script("build_golden")
    rows, _notes = _build(golden, para, config)
    by_leaf = {}
    for row in rows:
        by_leaf.setdefault(row["leaf"], []).append(row["path"])
    assert len(by_leaf["invoices"]) == 10
    assert not any("Telephonie" in path for path in by_leaf["invoices"])
    assert len(by_leaf["telecom"]) == 3
    assert len(by_leaf["career"]) == 5
    assert {row["kind"] for row in rows if row["leaf"] == "career"} == {"knowledge"}


def test_secret_and_hidden_files_are_never_sampled(load_script, para, config):
    golden = load_script("build_golden")
    rows, _notes = _build(golden, para, config)
    paths = " ".join(row["path"] for row in rows)
    assert "credentials" not in paths
    assert ".hidden" not in paths


def test_missing_leaf_folder_is_reported_not_fatal(load_script, para, config):
    golden = load_script("build_golden")
    _rows, notes = _build(golden, para, config)
    assert notes == ["leaf books: no files under 3_Resources/livres"]


def test_sampling_is_deterministic(load_script, para, config):
    golden = load_script("build_golden")
    assert _build(golden, para, config, seed=7) == _build(golden, para, config, seed=7)


def test_walk_stops_at_cap(load_script, tmp_path, monkeypatch):
    golden = load_script("build_golden")
    for folder in ("a", "b"):
        for index in range(3):
            _touch(tmp_path, f"big/{folder}/{index}.pdf")
    monkeypatch.setattr(golden, "WALK_CAP", 2)
    files = golden.leaf_files(tmp_path / "big", set(), random.Random(1))
    assert len(files) == 3  # the walk stops after the first folder that reaches the cap


def test_main_writes_jsonl_and_leaves_para_untouched(load_script, para, config, tmp_path, snapshot):
    golden = load_script("build_golden")
    cfg_dir = tmp_path / "cfg"
    out = tmp_path / "golden.jsonl"
    before = snapshot(para)
    argv = ["--para-root", str(para), "--config-dir", str(cfg_dir), "--out", str(out)]
    assert golden.main(argv) == 0
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert rows
    assert set(rows[0]) == {"path", "leaf", "kind"}
    assert snapshot(para) == before
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_build_golden.py -q`
Expected: FAIL with `FileNotFoundError` for `scripts/build_golden.py`.

- [ ] **Step 3: Implement**

Create `scripts/build_golden.py`:

```python
"""Sample the golden corpus from the owner-approved tree (spec §4.5). Read-only on PARA.

Writes <config dir>/golden.jsonl with lines {"path": <relative to PARA root>, "leaf": id,
"kind": kind}. Secret-looking and hidden files are never sampled. Delete lines for ambiguous
files before running the baseline.

Usage:
    uv run python scripts/build_golden.py --para-root "$PARA"
"""

from __future__ import annotations

import argparse
import json
import os
import random
from collections import Counter
from pathlib import Path
from typing import Any

from para_inventory import nfc

from para_files.core.secrets import secret_reason
from para_files.core.tree import TreeConfig, config_dir, load_tree_config

WALK_CAP = 2000


def leaf_files(root: Path, excluded: set[str], rng: random.Random) -> list[Path]:
    """Candidate files under root, skipping hidden, secret-named and other leaves' folders.

    The walk stops after the folder in which WALK_CAP candidates are reached.
    """
    found: list[Path] = []
    if not root.is_dir():
        return found
    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        dirnames[:] = sorted(
            d for d in dirnames if not d.startswith(".") and nfc(str(here / d)) not in excluded
        )
        rng.shuffle(dirnames)
        found += [
            here / name
            for name in sorted(filenames)
            if not name.startswith((".", "~$")) and secret_reason(name) is None
        ]
        if len(found) >= WALK_CAP:
            break
    return found


def build_golden(
    para_root: Path, config: TreeConfig, *, per_leaf: int, knowledge_per_leaf: int, seed: int
) -> tuple[list[dict[str, Any]], list[str]]:
    """Up to per_leaf files per leaf (knowledge_per_leaf for knowledge leaves), plus notes."""
    rng = random.Random(seed)  # noqa: S311 - sampling, not security
    leaf_dirs = {leaf_id: para_root / leaf.path for leaf_id, leaf in config.tree.leaves.items()}
    rows: list[dict[str, Any]] = []
    notes: list[str] = []
    for leaf_id, leaf in config.tree.leaves.items():
        excluded = {nfc(str(path)) for other, path in leaf_dirs.items() if other != leaf_id}
        files = leaf_files(leaf_dirs[leaf_id], excluded, rng)
        if not files:
            notes.append(f"leaf {leaf_id}: no files under {leaf.path}")
            continue
        wanted = knowledge_per_leaf if leaf.kind == "knowledge" else per_leaf
        for path in sorted(rng.sample(files, min(wanted, len(files)))):
            rows.append(
                {"path": nfc(str(path.relative_to(para_root))), "leaf": leaf_id, "kind": leaf.kind}
            )
    return rows, notes


def main(argv: list[str] | None = None) -> int:
    """Write golden.jsonl and print counts per kind; return 0."""
    parser = argparse.ArgumentParser(description="Sample the golden corpus.")
    parser.add_argument("--para-root", type=Path, required=True)
    parser.add_argument("--config-dir", type=Path, default=None)
    parser.add_argument("--per-leaf", type=int, default=10)
    parser.add_argument("--knowledge-per-leaf", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    para_root = args.para_root.expanduser().resolve()
    cfg_dir = args.config_dir or config_dir()
    out = (args.out or cfg_dir / "golden.jsonl").expanduser().resolve()
    if out.is_relative_to(para_root):
        parser.error("--out must be outside the PARA root")
    rows, notes = build_golden(
        para_root,
        load_tree_config(cfg_dir),
        per_leaf=args.per_leaf,
        knowledge_per_leaf=args.knowledge_per_leaf,
        seed=args.seed,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), "utf-8")
    for kind, count in sorted(Counter(row["kind"] for row in rows).items()):
        print(f"{count:5}  {kind}")
    print(*notes, sep="\n")
    print(f"golden -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run ruff format scripts/ tests/ && uv run pytest tests/test_build_golden.py -q`
Expected: PASS.

Run: `uv run ruff check src/ tests/`
Expected: clean.

- [ ] **Step 5: Changelog**

Under `### Added (Stage 1)` in `CHANGELOG.md`, append:

```markdown
- **Golden corpus builder** — `scripts/build_golden.py` samples up to 10 files per leaf (5 per knowledge leaf) from the approved tree into `~/.config/para-files/golden.jsonl`, never crossing into nested leaves and never sampling secret-looking or hidden files.
```

- [ ] **Step 6: Commit**

```bash
git add scripts/build_golden.py tests/test_build_golden.py CHANGELOG.md
git commit -m "feat(scripts): sample the golden corpus from the approved tree" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx"
```

---

### Task 7: Evaluation script

**Files:**
- Create: `scripts/eval.py`
- Test: `tests/test_eval_script.py`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes:
  - golden rows (Task 6);
  - `para_files.core.tree.config_dir` (Task 2).
- Produces:
  - **Prediction row format**, shared by Tasks 8 and 9:
    `{"path": <relative to PARA root>, "leaf": <leaf id or null>, "confidence": float, "band": "green"|"yellow"|"red", "signal": str, "top3": [leaf ids] (optional), "secs": float, "cost": float}`
  - **Functions in `scripts/eval.py`:**
    - `read_jsonl(path) -> list[dict]`
    - `curve(rows, n) -> list[tuple[float, float, float]]`
    - `max_coverage(points, target=0.98) -> float`
    - `summarize(rows) -> dict`
    - `evaluate(golden, preds) -> dict`, returning keys `overall`, `kinds`, `signals`, `missing_predictions`
    - `render(report) -> str`
    - `main(argv) -> int`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_eval_script.py`:

```python
"""Tests for scripts/eval.py (per-kind and per-signal metrics, spec §4.5)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

GOLDEN = [
    {"path": "a.pdf", "leaf": "inv", "kind": "record"},
    {"path": "b.pdf", "leaf": "inv", "kind": "record"},
    {"path": "c.pdf", "leaf": "books", "kind": "library"},
    {"path": "Matière.pdf", "leaf": "notes", "kind": "knowledge"},  # NFD on purpose
]
PREDS = [
    {"path": "a.pdf", "leaf": "inv", "confidence": 0.9, "band": "green", "signal": "rules",
     "secs": 0.1, "cost": 0.0},
    {"path": "b.pdf", "leaf": "bank", "confidence": 0.6, "band": "green", "signal": "rules",
     "secs": 0.3, "cost": 0.0},
    {"path": "Matière.pdf", "leaf": "misc", "confidence": 0.4, "band": "yellow",
     "signal": "fallback", "top3": ["misc", "notes", "x"], "secs": 1.0, "cost": 0.002},
]


@pytest.fixture
def report(load_script):
    return load_script("eval").evaluate(GOLDEN, PREDS)


def test_overall_metrics(report):
    overall = report["overall"]
    assert overall["n"] == 4
    assert overall["accuracy"] == pytest.approx(0.25)
    assert overall["green_precision"] == pytest.approx(0.5)
    assert overall["green_coverage"] == pytest.approx(0.5)
    assert overall["yellow_share"] == pytest.approx(0.25)
    assert overall["red_share"] == pytest.approx(0.25)
    assert overall["top3_hit"] == pytest.approx(1.0)
    assert overall["max_coverage_at_98"] == pytest.approx(0.25)
    assert overall["p50_secs"] == pytest.approx(0.3)
    assert overall["p95_secs"] == pytest.approx(1.0)
    assert overall["cost_per_1000"] == pytest.approx(0.5)
    assert report["missing_predictions"] == 1


def test_nfd_golden_path_joins_nfc_prediction(report):
    assert report["kinds"]["knowledge"]["top3_hit"] == pytest.approx(1.0)
    assert report["kinds"]["knowledge"]["yellow_share"] == pytest.approx(1.0)


def test_per_kind_metrics(report):
    assert report["kinds"]["record"]["n"] == 2
    assert report["kinds"]["record"]["accuracy"] == pytest.approx(0.5)
    assert report["kinds"]["library"]["red_share"] == pytest.approx(1.0)


def test_per_signal_curve(report):
    rules = report["signals"]["rules"]
    assert rules["curve"] == [
        pytest.approx((0.9, 1.0, 0.5)),
        pytest.approx((0.6, 0.5, 1.0)),
    ]
    assert rules["max_coverage_at_98"] == pytest.approx(0.5)


def test_main_renders_markdown_and_filters_to_predicted(load_script, tmp_path: Path, capsys):
    module = load_script("eval")
    golden, preds = tmp_path / "golden.jsonl", tmp_path / "preds.jsonl"
    golden.write_text("".join(json.dumps(row) + "\n" for row in GOLDEN))
    preds.write_text("".join(json.dumps(row) + "\n" for row in PREDS))
    assert module.main(["--golden", str(golden), "--pred", str(preds), "--only-predicted"]) == 0
    output = capsys.readouterr().out
    assert "| overall | 3 |" in output
    assert "| record |" in output
    assert module.main(["--golden", str(golden), "--pred", str(preds), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["overall"]["n"] == 4
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_eval_script.py -q`
Expected: FAIL with `FileNotFoundError` for `scripts/eval.py`.

- [ ] **Step 3: Implement**

Create `scripts/eval.py`:

```python
"""Score predictions against the golden corpus, per kind and per signal (spec §4.5).

Usage:
    uv run python scripts/eval.py --pred ~/.config/para-files/pred_baseline.jsonl
    uv run python scripts/eval.py --pred ~/.config/para-files/pred_jev.jsonl --only-predicted
"""

from __future__ import annotations

import argparse
import json
import unicodedata
from pathlib import Path
from typing import Any

from para_files.core.tree import config_dir

TARGET_PRECISION = 0.98
CURVE_POINTS = 20
PCT = (
    "accuracy", "green_precision", "green_coverage", "yellow_share", "red_share",
    "top3_hit", "max_coverage_at_98",
)
COLUMNS = ("n", *PCT, "p50_secs", "p95_secs", "cost_per_1000")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Rows of a JSONL file."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def key(path: str) -> str:
    """Join key for paths: NFC, so NFD names from macOS volumes still match."""
    return unicodedata.normalize("NFC", path)


def _quantile(values: list[float], q: float) -> float:
    return values[min(len(values) - 1, int(q * len(values)))]


def curve(rows: list[dict[str, Any]], n: int) -> list[tuple[float, float, float]]:
    """(threshold, precision, coverage of n) at each distinct confidence of decided rows."""
    decided = [r for r in rows if r["pred"].get("leaf")]
    ranked = sorted(decided, key=lambda r: -float(r["pred"].get("confidence", 0.0)))
    points: list[tuple[float, float, float]] = []
    correct = 0
    for index, row in enumerate(ranked, 1):
        correct += row["pred"]["leaf"] == row["gold"]["leaf"]
        confidence = float(row["pred"].get("confidence", 0.0))
        following = ranked[index]["pred"].get("confidence") if index < len(ranked) else None
        if following is None or float(following) != confidence:
            points.append((confidence, correct / index, index / n))
    return points


def max_coverage(points: list[tuple[float, float, float]], target: float = TARGET_PRECISION) -> float:
    """Largest coverage among curve points whose precision reaches target."""
    return max((cov for _, precision, cov in points if precision >= target), default=0.0)


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Metrics for a set of joined {"gold", "pred"} rows."""
    n = len(rows)
    if n == 0:
        return {"n": 0}
    green = [r for r in rows if r["pred"].get("band") == "green"]
    green_ok = sum(r["pred"].get("leaf") == r["gold"]["leaf"] for r in green)
    with_top3 = [r for r in rows if r["pred"].get("top3")]
    secs = sorted(float(r["pred"].get("secs", 0.0)) for r in rows)
    return {
        "n": n,
        "accuracy": sum(r["pred"].get("leaf") == r["gold"]["leaf"] for r in rows) / n,
        "green_precision": green_ok / len(green) if green else None,
        "green_coverage": len(green) / n,
        "yellow_share": sum(r["pred"].get("band") == "yellow" for r in rows) / n,
        "red_share": sum(r["pred"].get("band", "red") == "red" for r in rows) / n,
        "top3_hit": (
            sum(r["gold"]["leaf"] in r["pred"]["top3"] for r in with_top3) / len(with_top3)
            if with_top3
            else None
        ),
        "max_coverage_at_98": max_coverage(curve(rows, n)),
        "p50_secs": _quantile(secs, 0.5),
        "p95_secs": _quantile(secs, 0.95),
        "cost_per_1000": sum(float(r["pred"].get("cost", 0.0) or 0.0) for r in rows) / n * 1000,
    }


def evaluate(golden: list[dict[str, Any]], preds: list[dict[str, Any]]) -> dict[str, Any]:
    """Join predictions to golden rows by NFC path and compute all metrics."""
    by_path = {key(p["path"]): p for p in preds}
    rows = [{"gold": g, "pred": by_path.get(key(g["path"]), {"band": "red"})} for g in golden]
    report: dict[str, Any] = {"overall": summarize(rows), "kinds": {}, "signals": {}}
    for kind in sorted({g["kind"] for g in golden}):
        report["kinds"][kind] = summarize([r for r in rows if r["gold"]["kind"] == kind])
    for signal in sorted({r["pred"]["signal"] for r in rows if r["pred"].get("signal")}):
        subset = [r for r in rows if r["pred"].get("signal") == signal]
        report["signals"][signal] = {
            **summarize(subset),
            "curve": curve(subset, len(subset))[:CURVE_POINTS],
        }
    report["missing_predictions"] = sum(1 for r in rows if "path" not in r["pred"])
    return report


def _cell(column: str, value: Any) -> str:
    if value is None:
        return "-"
    if column in PCT:
        return f"{value:.1%}"
    if column == "n":
        return str(value)
    return f"{value:.2f}"


def render(report: dict[str, Any]) -> str:
    """Markdown table: overall, each kind, each signal."""
    lines = ["| scope | " + " | ".join(COLUMNS) + " |", "|" + "---|" * (len(COLUMNS) + 1)]
    scopes = [
        ("overall", report["overall"]),
        *report["kinds"].items(),
        *((f"signal:{name}", stats) for name, stats in report["signals"].items()),
    ]
    for name, stats in scopes:
        if stats.get("n"):
            cells = " | ".join(_cell(column, stats.get(column)) for column in COLUMNS)
            lines.append(f"| {name} | {cells} |")
    lines.append(f"\nmissing predictions: {report['missing_predictions']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Print the report as Markdown (default) or JSON; return 0."""
    parser = argparse.ArgumentParser(description="Score predictions against the golden corpus.")
    parser.add_argument("--golden", type=Path, default=None)
    parser.add_argument("--pred", type=Path, required=True)
    parser.add_argument("--only-predicted", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    golden = read_jsonl(args.golden or config_dir() / "golden.jsonl")
    preds = read_jsonl(args.pred)
    if args.only_predicted:
        predicted = {key(p["path"]) for p in preds}
        golden = [g for g in golden if key(g["path"]) in predicted]
    report = evaluate(golden, preds)
    print(json.dumps(report, indent=2) if args.json else render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run ruff format scripts/ tests/ && uv run pytest tests/test_eval_script.py -q`
Expected: PASS.

Run: `uv run ruff check src/ tests/`
Expected: clean.

- [ ] **Step 5: Changelog**

Under `### Added (Stage 1)` in `CHANGELOG.md`, append:

```markdown
- **Evaluation script** — `scripts/eval.py` scores a predictions file against the golden corpus. It reports, overall, per kind and per signal: accuracy, green precision and coverage, yellow/red share, top-3 hit rate, best coverage at ≥ 98% precision, latency and cost per 1000 files.
```

- [ ] **Step 6: Commit**

```bash
git add scripts/eval.py tests/test_eval_script.py CHANGELOG.md
git commit -m "feat(scripts): per-kind and per-signal evaluation against the golden corpus" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx"
```

---

### Task 8: Baseline runner (old pipeline, signals 1–3)

**Files:**
- Create: `scripts/run_baseline.py`
- Test: `tests/test_run_baseline.py`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes:
  - golden rows (Task 6) and the prediction row format (Task 7);
  - `para_inventory.make_canon`, `nfc`, `retentions_by_stem`, `scan_folders` (Task 4);
  - `para_files.core.tree.Tree`, `config_dir`, `load_tree_config` (Task 2).
- Produces: `scripts/run_baseline.py` with:
  - `leaf_for_category(category, tree, canon) -> str | None`
  - `old_pipeline_classifier() -> Classify`, where `Classify = Callable[[Path], tuple[str, float, str]]` returns `(category, confidence, signal)`
  - `run_baseline(para_root, golden, tree, canon, classify, workdir) -> list[dict]`
  - `main(argv) -> int`, which writes `<config dir>/pred_baseline.jsonl`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_run_baseline.py`:

```python
"""Tests for scripts/run_baseline.py (old pipeline over the golden corpus)."""

from __future__ import annotations

from pathlib import Path

import pytest

from para_files.core.tree import Tree

TREE = Tree.model_validate(
    {
        "leaves": {
            "invoices": {
                "kind": "record", "retention": "5y", "path": "4_Archives/5y_factures",
                "describe": "Invoices",
            },
            "telecom": {
                "kind": "record", "retention": "5y", "path": "4_Archives/5y_factures/Telephonie",
                "describe": "Telecom invoices",
            },
            "docs": {"kind": "library", "path": "3_Resources/docs", "describe": "Vendor docs"},
        }
    }
)
CANON_MAP = {
    "4_Archives/factures": "4_Archives/5y_factures",
    "3_Resources/documentation": "3_Resources/docs",
}


def canon(rel: str) -> str:
    return CANON_MAP.get(rel, rel)


@pytest.mark.parametrize(
    ("category", "leaf"),
    [
        ("4_Archives/factures/Telephonie/2024", "telecom"),
        ("4_Archives/5y_factures/2024", "invoices"),
        ("3_Resources/documentation/VMware", "docs"),
        ("0_Inbox", None),
        ("4_Archives/unknown/x", None),
    ],
)
def test_leaf_for_category_prefers_canonical_and_longest(load_script, category, leaf):
    baseline = load_script("run_baseline")
    assert baseline.leaf_for_category(category, TREE, canon) == leaf


def test_run_baseline_maps_errors_to_red_and_never_exposes_para_paths(
    load_script, tmp_path: Path, snapshot
):
    baseline = load_script("run_baseline")
    para = tmp_path / "PARA"
    for name in ("a.pdf", "b.pdf", "c.pdf"):
        path = para / "4_Archives/5y_factures" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")
    golden = [
        {"path": f"4_Archives/5y_factures/{name}", "leaf": "invoices", "kind": "record"}
        for name in ("a.pdf", "b.pdf", "c.pdf")
    ]
    seen: list[Path] = []

    def classify(path: Path) -> tuple[str, float, str]:
        seen.append(path)
        if path.name == "b.pdf":
            msg = "unreadable"
            raise PermissionError(msg)
        if path.name == "c.pdf":
            return "0_Inbox", 0.8, "extension_router"
        return "4_Archives/factures/2024", 0.95, "rules_engine"

    before = snapshot(para)
    preds = baseline.run_baseline(para, golden, TREE, canon, classify, tmp_path / "work")
    by_name = {Path(p["path"]).name: p for p in preds}
    assert by_name["a.pdf"]["leaf"] == "invoices"
    assert by_name["a.pdf"]["band"] == "green"
    assert by_name["a.pdf"]["signal"] == "rules_engine"
    assert by_name["b.pdf"]["band"] == "red"
    assert by_name["b.pdf"]["signal"] == "error"
    assert by_name["c.pdf"]["leaf"] is None
    assert by_name["c.pdf"]["band"] == "red"
    assert all(not path.is_relative_to(para) for path in seen)
    assert snapshot(para) == before
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_run_baseline.py -q`
Expected: FAIL with `FileNotFoundError` for `scripts/run_baseline.py`.

- [ ] **Step 3: Implement**

Create `scripts/run_baseline.py`:

```python
"""Baseline: the old pipeline over the golden corpus, written as predictions for eval.py.

The old pipeline runs with the semantic classifier and the LLM off, so it uses books, rules,
taxonomy and the extension router. OCR rename is off and patched out. Each file is classified
through a symlink in a temporary folder, so its PARA location cannot leak into the decision.
Read-only on PARA.

Usage:
    uv run python scripts/run_baseline.py --para-root "$PARA"
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from para_inventory import make_canon, nfc, retentions_by_stem, scan_folders

from para_files.core.tree import Tree, config_dir, load_tree_config

Classify = Callable[[Path], tuple[str, float, str]]


def leaf_for_category(category: str, tree: Tree, canon: Callable[[str], str]) -> str | None:
    """Most specific leaf whose path contains the old pipeline's category path."""
    parts = [nfc(part).strip() for part in category.split("/") if part.strip()]
    if len(parts) < 2:
        return None
    path = "/".join([canon("/".join(parts[:2])), *parts[2:]])
    best: str | None = None
    for leaf_id, leaf in tree.leaves.items():
        inside = path == leaf.path or path.startswith(leaf.path + "/")
        if inside and (best is None or len(leaf.path) > len(tree.leaves[best].path)):
            best = leaf_id
    return best


def old_pipeline_classifier() -> Classify:
    """The old pipeline with semantic, LLM and OCR rename disabled."""
    os.environ.update(
        PARA_FILES_MLX_SEMANTIC_ENABLED="false",
        PARA_FILES_LLM_ENABLED="false",
        PARA_FILES_OCR_RENAME__ENABLED="false",
    )
    from para_files.config import load_config
    from para_files.pipeline import ClassificationPipeline

    pipeline = ClassificationPipeline(load_config())
    pipeline._maybe_rename_generic_pdf = lambda path: path  # never rename during a measurement

    def classify(path: Path) -> tuple[str, float, str]:
        result = pipeline.classify_file(path)
        return result.category, result.confidence.value, str(result.confidence.source)

    return classify


def run_baseline(
    para_root: Path,
    golden: list[dict[str, Any]],
    tree: Tree,
    canon: Callable[[str], str],
    classify: Classify,
    workdir: Path,
) -> list[dict[str, Any]]:
    """One prediction per golden row; a failing file becomes a red row."""
    preds: list[dict[str, Any]] = []
    for index, row in enumerate(golden):
        source = para_root / row["path"]
        link = workdir / str(index) / source.name
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(source)
        start = time.monotonic()
        try:
            category, confidence, signal = classify(link)
            leaf = leaf_for_category(category, tree, canon)
        except Exception as exc:  # noqa: BLE001 - one unreadable file must not stop the run
            category, confidence, signal, leaf = f"error: {type(exc).__name__}", 0.0, "error", None
        preds.append(
            {
                "path": row["path"],
                "leaf": leaf,
                "confidence": confidence if leaf else 0.0,
                "band": "green" if leaf else "red",
                "signal": signal,
                "raw": category,
                "secs": round(time.monotonic() - start, 3),
                "cost": 0.0,
            }
        )
    return preds


def main(argv: list[str] | None = None) -> int:
    """Write pred_baseline.jsonl next to the golden corpus; return 0."""
    parser = argparse.ArgumentParser(description="Run the old pipeline over the golden corpus.")
    parser.add_argument("--para-root", type=Path, required=True)
    parser.add_argument("--config-dir", type=Path, default=None)
    parser.add_argument("--documents", type=Path, default=Path("config/documents.json"))
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    para_root = args.para_root.expanduser().resolve()
    cfg_dir = args.config_dir or config_dir()
    out = (args.out or cfg_dir / "pred_baseline.jsonl").expanduser().resolve()
    if out.is_relative_to(para_root):
        parser.error("--out must be outside the PARA root")
    golden = [json.loads(line) for line in (cfg_dir / "golden.jsonl").read_text().splitlines()]
    tree = load_tree_config(cfg_dir).tree
    taxonomy = retentions_by_stem(json.loads(args.documents.read_text(encoding="utf-8")))
    canon = make_canon(scan_folders(para_root), taxonomy)  # same canonical map as the seeder
    with tempfile.TemporaryDirectory() as workdir:
        preds = run_baseline(para_root, golden, tree, canon, old_pipeline_classifier(), Path(workdir))
    out.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in preds), "utf-8")
    decided = sum(1 for p in preds if p["leaf"])
    print(f"baseline: {decided}/{len(preds)} decided -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run ruff format scripts/ tests/ && uv run pytest tests/test_run_baseline.py -q`
Expected: PASS.

Run: `uv run ruff check src/ tests/`
Expected: clean.

- [ ] **Step 5: Changelog**

Under `### Added (Stage 1)` in `CHANGELOG.md`, append:

```markdown
- **Baseline runner** — `scripts/run_baseline.py` runs the old pipeline (semantic and LLM off, no OCR rename) over the golden corpus through symlinks and maps its categories onto the new leaves, so `eval.py` can score it.
```

- [ ] **Step 6: Commit**

```bash
git add scripts/run_baseline.py tests/test_run_baseline.py CHANGELOG.md
git commit -m "feat(scripts): baseline the old pipeline on the golden corpus" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx"
```

---

### Task 9: Authoritative bake-off runner

**Files:**
- Create: `scripts/bakeoff.py`
- Test: `tests/test_bakeoff_script.py`
- Modify: `examples/README.md`, `CHANGELOG.md`

**Interfaces:**
- Consumes:
  - golden rows (Task 6), baseline predictions (Task 8) and the prediction row format (Task 7);
  - `para_files.core.secrets.secret_reason` (Task 3);
  - `para_files.core.tree.Tree`, `config_dir`, `load_tree_config` (Task 2);
  - `para_inventory.nfc` (Task 4).
- Produces: `scripts/bakeoff.py` with:
  - `CANDIDATES = {"gemini", "sonnet", "jev"}`, each mapping to `(ask, workers)`. Insertion order is the owner's preference and breaks ties. There is no local model: the owner dropped local AI on 2026-10-11.
  - `ask_llm(model, post, key, menu, name, preview)`: the shared OpenRouter chat call
  - `ask_gemini`, `ask_sonnet`, `ask_jev`, each `(post, key, menu, name, preview) -> (ranked, cost)`, where `ranked` is a list of `(leaf_id, probability)` pairs, at most 3
  - `select_scope(golden, baseline) -> list[dict]`
  - `predict(row, para_root, menu, ask, post, key, preview_of) -> dict`
  - `read_preview(path) -> str`, the default `preview_of`
  - `main(argv) -> int`, which writes `<config dir>/pred_<candidate>.jsonl`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_bakeoff_script.py`:

```python
"""Tests for scripts/bakeoff.py: privacy flags, secrets guard, parsing, scope (no network)."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

MENU = {"inv": "Invoices", "notes": "Notes"}


class FakePost:
    """Records requests and replays canned responses; never touches the network."""

    def __init__(self, *responses: httpx.Response) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    def __call__(self, url: str, **kwargs) -> httpx.Response:
        self.calls.append({"url": url, **kwargs})
        response = self.responses.pop(0)
        response.request = httpx.Request("POST", url)
        return response


def _chat(content: str) -> httpx.Response:
    payload = {"choices": [{"message": {"content": content}}], "usage": {"cost": 0.001}}
    return httpx.Response(200, json=payload)


def _never(*_args, **_kwargs):
    msg = "a secret file must never be sent"
    raise AssertionError(msg)


@pytest.fixture
def bakeoff(load_script):
    return load_script("bakeoff")


@pytest.mark.parametrize(("ask", "model"), [("ask_gemini", "GEMINI"), ("ask_sonnet", "SONNET")])
def test_llm_request_enforces_zdr_and_low_reasoning(bakeoff, ask, model):
    post = FakePost(_chat('{"choices": [{"leaf": "notes", "confidence": 0.7}]}'))
    ranked, cost = getattr(bakeoff, ask)(post, "k", MENU, "a.pdf", "text")
    body = post.calls[0]["json"]
    assert body["model"] == getattr(bakeoff, model)
    assert body["provider"] == {"zdr": True, "data_collection": "deny"}
    assert body["reasoning"] == {"effort": "low"}
    assert body["max_tokens"] == 4000
    schema = body["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["choices"]["items"]["properties"]["leaf"]["enum"] == ["inv", "notes"]
    assert ranked == [("notes", 0.7)]
    assert cost == pytest.approx(0.001)


def test_candidates_follow_owner_preference(bakeoff):
    assert list(bakeoff.CANDIDATES) == ["gemini", "sonnet", "jev"]


def test_jev_request_enforces_zdr_and_ranks_probabilities(bakeoff):
    answer = {"leaf": {"type": "choice", "choice": "notes",
                       "probabilities": {"inv": 0.2, "notes": 0.7, "bogus": 0.1}}}
    post = FakePost(httpx.Response(200, json={"answers": answer, "usage": {"cost": 0.0002}}))
    ranked, _cost = bakeoff.ask_jev(post, "k", MENU, "a.pdf", "text")
    body = post.calls[0]["json"]
    assert body["provider"] == {"zdr": True, "data_collection": "deny"}
    assert body["questions"]["leaf"]["criteria"] == MENU
    assert ranked == [("notes", 0.7), ("inv", 0.2)]


def test_parse_choices_drops_unknown_and_duplicate_leaves(bakeoff):
    text = (
        'noise {"choices": [{"leaf": "zzz", "confidence": 0.9}, '
        '{"leaf": "inv", "confidence": 1.4}, {"leaf": "inv", "confidence": 0.2}]}'
    )
    assert bakeoff.parse_choices(text, MENU) == [("inv", 1.0)]
    assert bakeoff.parse_choices("not json", MENU) == []


def test_secret_named_file_is_never_sent(bakeoff, tmp_path: Path):
    row = {"path": "0_Inbox/wallet_recovery_phrase.txt", "leaf": "notes", "kind": "knowledge",
           "scope": "b"}
    pred = bakeoff.predict(row, tmp_path, MENU, bakeoff.ask_jev, _never, "k", lambda _p: "")
    assert (pred["band"], pred["signal"], pred["leaf"]) == ("red", "secret", None)


def test_secret_content_is_never_sent(bakeoff, tmp_path: Path):
    row = {"path": "4_Archives/x/key.txt", "leaf": "inv", "kind": "record", "scope": "a"}
    pred = bakeoff.predict(
        row, tmp_path, MENU, bakeoff.ask_gemini, _never, "k",
        lambda _p: "-----BEGIN RSA PRIVATE KEY-----\nMIIE",
    )
    assert pred["signal"] == "secret"


def test_unreadable_file_is_still_predicted(bakeoff, tmp_path: Path):
    def unreadable(_path: Path) -> str:
        msg = "online-only file"
        raise PermissionError(msg)

    post = FakePost(_chat('{"choices": [{"leaf": "inv", "confidence": 0.8}]}'))
    row = {"path": "4_Archives/x/a.pdf", "leaf": "inv", "kind": "record", "scope": "a"}
    pred = bakeoff.predict(row, tmp_path, MENU, bakeoff.ask_gemini, post, "k", unreadable)
    assert pred["leaf"] == "inv"
    assert pred["top3"] == ["inv"]
    assert "(no text)" in post.calls[0]["json"]["messages"][1]["content"]


def test_rate_limit_is_retried(bakeoff, monkeypatch):
    monkeypatch.setattr(bakeoff.time, "sleep", lambda _seconds: None)
    post = FakePost(
        httpx.Response(429, headers={"Retry-After": "1"}),
        _chat('{"choices": [{"leaf": "inv", "confidence": 0.5}]}'),
    )
    ranked, _cost = bakeoff.ask_gemini(post, "k", MENU, "a.pdf", "")
    assert ranked == [("inv", 0.5)]
    assert len(post.calls) == 2


def test_select_scope(bakeoff):
    golden = [
        {"path": "a.pdf", "leaf": "inv", "kind": "record"},
        {"path": "b.pdf", "leaf": "inv", "kind": "record"},
        {"path": "c.pdf", "leaf": "notes", "kind": "knowledge"},
    ]
    baseline = [{"path": "a.pdf", "band": "green"}, {"path": "b.pdf", "band": "red"}]
    scoped = {row["path"]: row["scope"] for row in bakeoff.select_scope(golden, baseline)}
    assert scoped == {"b.pdf": "a", "c.pdf": "b"}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_bakeoff_script.py -q`
Expected: FAIL with `FileNotFoundError` for `scripts/bakeoff.py`.

- [ ] **Step 3: Implement**

Create `scripts/bakeoff.py`:

```python
"""Authoritative bake-off for signal 4 (spec §4.5). Throwaway developer tool.

Scope (a): golden record/library/media files the baseline left non-green.
Scope (b): golden knowledge files, scored as top-3 suggestions.

Every cloud request carries provider.zdr=true; files flagged by the secrets guard are never sent.
Predictions are all "yellow": eval.py's curve (max coverage at >= 98% precision) is the verdict.

Usage:
    uv run python scripts/bakeoff.py --candidate jev --para-root "$PARA"
    uv run python scripts/eval.py --pred ~/.config/para-files/pred_jev.jsonl --only-predicted
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values
from para_inventory import nfc

from para_files.core.secrets import secret_reason
from para_files.core.tree import Tree, config_dir, load_tree_config

OPENROUTER = "https://openrouter.ai"
GEMINI = "google/gemini-3.8-flash"
SONNET = "anthropic/claude-sonnet-5.5"
JEV = "typesafe/jev-1.13"
PRIVACY = {"zdr": True, "data_collection": "deny"}
# Gemini 3.8 Flash and Sonnet 5.5 reject reasoning.enabled=false; reasoning tokens need room.
REASONING = {"effort": "low"}
MAX_TOKENS = 4000
RETRY_STATUS = frozenset({429, 502, 503, 524, 529})
SYSTEM = (
    "You file documents into a person's PARA folder tree. Rank the three most likely folder "
    "ids from the list for this file, most likely first, each with the probability that it is "
    "the right folder. Reply only with JSON."
)
Post = Callable[..., httpx.Response]
Ranked = list[tuple[str, float]]


def leaf_menu(tree: Tree) -> dict[str, str]:
    """Leaf id -> describe, the choice list every candidate sees."""
    return {leaf_id: leaf.describe for leaf_id, leaf in tree.leaves.items()}


def evidence_text(name: str, preview: str) -> str:
    """Identical evidence for every candidate: filename + preview."""
    body = preview if preview.strip() and preview.strip() != name else "(no text)"
    return f"Filename: {name}\n\nContent preview:\n{body}"


def llm_schema(menu: dict[str, str]) -> dict[str, Any]:
    """JSON schema: up to 3 choices, each an enum leaf id with a confidence."""
    choice = {
        "type": "object",
        "additionalProperties": False,
        "required": ["leaf", "confidence"],
        "properties": {
            "leaf": {"type": "string", "enum": list(menu)},
            "confidence": {"type": "number"},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["choices"],
        "properties": {"choices": {"type": "array", "items": choice, "minItems": 1, "maxItems": 3}},
    }


def llm_messages(menu: dict[str, str], name: str, preview: str) -> list[dict[str, str]]:
    """System + user messages listing the leaves and the file evidence."""
    folders = "\n".join(f"- {leaf_id}: {describe}" for leaf_id, describe in menu.items())
    user = f"Folders:\n{folders}\n\nFile:\n{evidence_text(name, preview)}"
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def parse_choices(text: str | None, menu: dict[str, str]) -> Ranked:
    """Ranked (leaf, probability) pairs from an LLM reply; unknown or repeated leaves dropped."""
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    try:
        data = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        return []
    ranked: Ranked = []
    for item in data.get("choices", []) if isinstance(data, dict) else []:
        leaf, confidence = item.get("leaf"), item.get("confidence")
        known = leaf in menu and leaf not in [seen for seen, _ in ranked]
        if known and isinstance(confidence, (int, float)):
            ranked.append((leaf, max(0.0, min(1.0, float(confidence)))))
    return ranked[:3]


def post_with_retry(post: Post, url: str, **kwargs: Any) -> httpx.Response:
    """POST, retrying rate limits and transient provider errors (Retry-After honoured)."""
    response = post(url, **kwargs)
    for attempt in range(4):
        if response.status_code not in RETRY_STATUS:
            return response
        retry_after = response.headers.get("Retry-After", "")
        delay = float(retry_after) if retry_after.isdigit() else min(30.0, 2**attempt + random.random())
        time.sleep(delay)
        response = post(url, **kwargs)
    return response


def ask_llm(
    model: str, post: Post, key: str, menu: dict[str, str], name: str, preview: str
) -> tuple[Ranked, float]:
    """An OpenRouter chat model: enum-constrained, low reasoning effort, ZDR enforced."""
    response = post_with_retry(
        post,
        f"{OPENROUTER}/api/v1/chat/completions",
        timeout=120,
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": model,
            "messages": llm_messages(menu, name, preview),
            "temperature": 0,
            "max_tokens": MAX_TOKENS,
            "reasoning": REASONING,
            "provider": PRIVACY,
            "usage": {"include": True},
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "filing", "strict": True, "schema": llm_schema(menu)},
            },
        },
    )
    response.raise_for_status()
    data = response.json()
    cost = float(data.get("usage", {}).get("cost", 0.0) or 0.0)
    return parse_choices(data["choices"][0]["message"].get("content"), menu), cost


def ask_gemini(
    post: Post, key: str, menu: dict[str, str], name: str, preview: str
) -> tuple[Ranked, float]:
    """Gemini 3.8 Flash, the owner's first choice."""
    return ask_llm(GEMINI, post, key, menu, name, preview)


def ask_sonnet(
    post: Post, key: str, menu: dict[str, str], name: str, preview: str
) -> tuple[Ranked, float]:
    """Claude Sonnet 5.5, the owner's second choice."""
    return ask_llm(SONNET, post, key, menu, name, preview)


def ask_jev(post: Post, key: str, menu: dict[str, str], name: str, preview: str) -> tuple[Ranked, float]:
    """Jev 1.13 via the Decisions API: one choice question, probability per leaf, ZDR enforced."""
    response = post_with_retry(
        post,
        f"{OPENROUTER}/api/alpha/decisions",
        timeout=120,
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": JEV,
            "provider": PRIVACY,
            "questions": {
                "leaf": {
                    "type": "choice",
                    "criteria": menu,
                    "instructions": "Which folder of this person's PARA file tree should "
                    "this file be filed in?",
                }
            },
            "state": {"filename": name, "content_preview": evidence_text(name, preview)},
        },
    )
    response.raise_for_status()
    data = response.json()
    probabilities = data["answers"]["leaf"].get("probabilities", {})
    ranked = sorted(
        ((leaf, float(p)) for leaf, p in probabilities.items() if leaf in menu),
        key=lambda pair: -pair[1],
    )
    return ranked[:3], float(data.get("usage", {}).get("cost", 0.0) or 0.0)


# Insertion order is the owner's preference; it breaks ties between equal results (spec §4.5).
CANDIDATES: dict[str, tuple[Callable[..., tuple[Ranked, float]], int]] = {
    "gemini": (ask_gemini, 6),
    "sonnet": (ask_sonnet, 6),
    "jev": (ask_jev, 8),
}


def select_scope(golden: list[dict[str, Any]], baseline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Scope (a): non-knowledge files the baseline left non-green. Scope (b): knowledge files."""
    base = {nfc(p["path"]): p for p in baseline}
    scoped: list[dict[str, Any]] = []
    for row in golden:
        if row["kind"] == "knowledge":
            scoped.append({**row, "scope": "b"})
        elif base.get(nfc(row["path"]), {}).get("band") != "green":
            scoped.append({**row, "scope": "a"})
    return scoped


def read_preview(path: Path) -> str:
    """First 2000 characters of text, using the existing extractors (read-only)."""
    from para_files.utils.file_utils import read_content_preview

    return read_content_preview(path, max_chars=2000)


def predict(
    row: dict[str, Any],
    para_root: Path,
    menu: dict[str, str],
    ask: Callable[..., tuple[Ranked, float]],
    post: Post,
    key: str,
    preview_of: Callable[[Path], str],
) -> dict[str, Any]:
    """One prediction row; secret files are never sent; one bad file never stops the run."""
    path = para_root / row["path"]
    start = time.monotonic()
    try:
        preview = preview_of(path)
    except Exception:  # noqa: BLE001 - unreadable or online-only: classify by name alone
        preview = ""
    base = {"path": row["path"], "scope": row["scope"], "band": "yellow", "cost": 0.0}
    if secret_reason(path.name, preview):
        return {**base, "leaf": None, "confidence": 0.0, "band": "red", "signal": "secret", "secs": 0.0}
    error = None
    try:
        ranked, cost = ask(post, key, menu, path.name, preview)
    except (httpx.HTTPError, KeyError, ValueError, IndexError) as exc:
        ranked, cost, error = [], 0.0, f"{type(exc).__name__}: {exc}"[:200]
    pred = {
        **base,
        "leaf": ranked[0][0] if ranked else None,
        "confidence": ranked[0][1] if ranked else 0.0,
        "top3": [leaf for leaf, _ in ranked],
        "signal": "fallback",
        "secs": round(time.monotonic() - start, 3),
        "cost": cost,
    }
    if error:
        pred["error"] = error
    return pred


def main(argv: list[str] | None = None) -> int:
    """Run one candidate over the bake-off scope and write its predictions; return 0."""
    parser = argparse.ArgumentParser(description="Run one signal-4 candidate.")
    parser.add_argument("--candidate", choices=sorted(CANDIDATES), required=True)
    parser.add_argument("--para-root", type=Path, required=True)
    parser.add_argument("--config-dir", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)
    cfg_dir = args.config_dir or config_dir()
    para_root = args.para_root.expanduser().resolve()
    key = os.environ.get("OPENROUTER_API_KEY") or dotenv_values(".env").get("PARA_FILES_LLM_API_KEY") or ""
    if not key:
        parser.error("set OPENROUTER_API_KEY or PARA_FILES_LLM_API_KEY in .env")
    read = lambda path: [json.loads(line) for line in path.read_text().splitlines() if line]  # noqa: E731
    rows = select_scope(read(cfg_dir / "golden.jsonl"), read(cfg_dir / "pred_baseline.jsonl"))
    rows = rows[: args.limit]
    menu = leaf_menu(load_tree_config(cfg_dir).tree)
    ask, workers = CANDIDATES[args.candidate]
    with ThreadPoolExecutor(workers) as pool:
        preds = list(
            pool.map(lambda r: predict(r, para_root, menu, ask, httpx.post, key, read_preview), rows)
        )
    out = cfg_dir / f"pred_{args.candidate}.jsonl"
    out.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in preds), "utf-8")
    errors = sum(1 for p in preds if "error" in p)
    secrets = sum(1 for p in preds if p["signal"] == "secret")
    print(f"{args.candidate}: {len(preds)} files, {errors} errors, {secrets} secrets kept local -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run ruff format scripts/ tests/ && uv run pytest tests/test_bakeoff_script.py -q`
Expected: PASS, with no network access.

Run: `uv run ruff check src/ tests/ && uv run pytest -q`
Expected: clean; the full suite passes.

- [ ] **Step 5: Document the Stage 1 tooling**

Append to `examples/README.md`:

````markdown
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
````

- [ ] **Step 6: Changelog**

Under `### Added (Stage 1)` in `CHANGELOG.md`, append:

```markdown
- **Bake-off runner** — `scripts/bakeoff.py` runs Gemini 3.8 Flash, Claude Sonnet 5.5 (both at low reasoning effort) or Jev 1.13 over the files the baseline leaves undecided (and over knowledge files as top-3 suggestions). Every cloud request enforces zero data retention, and secret-looking files are never sent.
```

- [ ] **Step 7: Commit**

```bash
git add scripts/bakeoff.py tests/test_bakeoff_script.py examples/README.md CHANGELOG.md
git commit -m "feat(scripts): authoritative signal-4 bake-off with ZDR and secrets guard" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx"
```

---

### Task 10: Real-data run, owner checkpoints, results

This task runs the tools on the owner's PARA volume. The controller (not a subagent) runs it, and it stops at **CHECKPOINT A** and **CHECKPOINT C** for the owner. Nothing in it moves a file. Set `PARA` to the PARA root in the shell first. Its value is personal: never write it into a tracked file.

**Files:**
- Modify: `docs/superpowers/specs/2026-10-10-para-files-redesign-design.md` (§4.5 results, §8 decisions)
- Modify: `CHANGELOG.md`
- Personal (never committed): everything under `~/.config/para-files/`

- [ ] **Step 1: Draft the tree**

```bash
uv run python scripts/migrate_config.py --para-root "$PARA"
```

Expected: `~/.config/para-files/draft/` holds `tree.yaml`, `rules.yaml`, `issuers.yaml` and `review.md`.

- [ ] **Step 2: CHECKPOINT A — owner approves the tree**

Owner and controller edit the draft into `~/.config/para-files/tree.yaml`, `rules.yaml` and `issuers.yaml`:
- 20–30 leaves;
- every leaf has the right `kind` and `retention`;
- non-canonical folders listed in `review.md` (legacy twins, stray prefixes, variants, and doubtful folders whose content later goes back to `0_Inbox`) are not leaves;
- issuers added for the recurring inbox families listed in `review.md`.

Validate:

```bash
uv run python -c "from para_files.core.tree import load_tree_config, validation_warnings; \
c = load_tree_config(); print(len(c.tree.leaves), 'leaves'); print(*validation_warnings(c), sep='\n')"
```

Expected: loads without error and prints 20–30 leaves. The owner accepts the remaining warnings or fixes them. Do not continue without the owner's explicit approval of the tree.

- [ ] **Step 3: Golden corpus, then CHECKPOINT C**

```bash
uv run python scripts/build_golden.py --para-root "$PARA"
```

The owner deletes lines for ambiguous files from `~/.config/para-files/golden.jsonl`, then confirms.

- [ ] **Step 4: Baseline**

```bash
uv run python scripts/run_baseline.py --para-root "$PARA"
uv run python scripts/eval.py --pred ~/.config/para-files/pred_baseline.jsonl
```

Keep the printed table; Step 7 records it.

- [ ] **Step 5: Bake-off**

The cloud candidates send each in-scope file's name and first 2000 characters to OpenRouter. ZDR is enforced per request and secret-looking files stay local. The owner consented to this for the bake-off.

```bash
uv run python scripts/bakeoff.py --candidate gemini --para-root "$PARA"
uv run python scripts/bakeoff.py --candidate sonnet --para-root "$PARA"
uv run python scripts/bakeoff.py --candidate jev --para-root "$PARA"
for c in gemini sonnet jev; do uv run python scripts/eval.py --pred ~/.config/para-files/pred_$c.jsonl --only-predicted; done
```

- [ ] **Step 6: Apply the spec's winner and drop rules**

Spec §4.5 defines both rules:
- **Scope (a), winner:** the highest `max_coverage_at_98` on record/library/media files. Ties follow the owner's preference: Gemini 3.8 Flash, then Sonnet 5.5, then Jev 1.13.
- **Scope (b), winner:** the highest `top3_hit` on knowledge files.
- **Drop rule:** if no candidate adds ≥ 5 points of green coverage on (a) over the baseline, and none beats the baseline on (b), signal 4 is removed.

Write the decision down with its numbers.

- [ ] **Step 7: Record the results (no personal data) and commit**

1. In the spec, add a subsection `#### Stage 1 results (<date>)` at the end of §4.5. It holds:
   - the per-kind tables from `eval.py` for the baseline and each candidate: n, accuracy, green precision and coverage, top-3 hit, `max_coverage_at_98`, p50 latency, cost per 1000;
   - the leaf count;
   - the signal-4 decision.

   Add a matching row to §8 Decisions Log. No file names, paths or leaf descriptions.
2. In `CHANGELOG.md`, under `### Added (Stage 1)`, add one line with the green precision and coverage per kind and the signal-4 decision.
3. Commit:

```bash
git add docs/superpowers/specs/2026-10-10-para-files-redesign-design.md CHANGELOG.md
git commit -m "docs(spec): record Stage 1 baseline, bake-off and signal-4 decision" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx"
```

- [ ] **Step 8: Inbox preview (old pipeline, nothing moves)**

```bash
PARA_FILES_LLM_ENABLED=false PARA_FILES_MLX_SEMANTIC_ENABLED=false \
  uv run para-files scan "$PARA/0_Inbox" --recursive --json > ~/.config/para-files/inbox-preview.json
```

`scan` only previews (OCR rename has been off by default since Stage 0); the two variables keep it local (no cloud call, no Ollama). Report to the owner, per recurring inbox family from `review.md`, where the old pipeline would send the files and whether that matches the approved leaves. Nothing is moved.

Stage 1 exit (spec §5) is met when all of these are true:
- the tree is owner-approved;
- the eval baseline is recorded;
- the signal-4 decision is recorded;
- the owner has reviewed the inbox preview.
