# Model-First Classification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The cloud model reads every non-secret file (its text, including OCR, its metadata and its type) and ranks the folders. Rule and issuer matches become hints in its prompt. Only a few pinned rules and verified-ISBN books decide on their own, and the owner reviews suggestions group by group.

**Architecture:**
- `core/decide.py` gets a new `choose()` cascade: secret guard, then a verified-ISBN book, then a pinned rule, then the model with hints, then the first hint (always yellow) when the model is off or silent.
- `core/fallback.py` builds a richer prompt (type, metadata, hints, the full preview, the folder path, a short "about") and keys the cache on a prompt version.
- `cli/review.py` reviews yellow files group by group.
- Smaller pieces: quiet logging, a TTY guard on `--review`, `Rule.pin`, retargets that keep `{year}`/`{issuer}`, and few-shot examples taken from the owner's past decisions.

**Tech Stack:** Python 3.12, Typer, pydantic v2, litellm (OpenRouter, ZDR), loguru, pytest, ruff, mypy (strict).

**Spec:** `docs/superpowers/specs/2026-10-10-para-files-redesign-design.md`. Owner decisions of 2026-10-11 are recorded in `~/.claude/plans/ancient-wondering-starlight.md`. Task 11 copies them into spec §4.2 and §8 and into ADR-014.

## Global Constraints

- Python 3.12+, `from __future__ import annotations` in every module, strict mypy, ruff line length 100, `from loguru import logger` for logging.
- Public repo: generic names only in code, tests and docs (`AcmeCard`, `~/PARA`, `Payslip_…`). No personal names, paths or folder names.
- Model calls go through litellm only, with `extra_body={"provider": {"zdr": True, "data_collection": "deny"}, ...}` on every request.
- Secrets: a file flagged by `core.secrets` is never sent to the model and never moved. Secret-named leaves, metadata values, hints and example names are never put in a prompt.
- Bands:
  - pinned rule → green; ISBN book → green;
  - model → green only when its kind has `calibration_min` (100) owner-confirmed decisions and its confidence is at least `fallback_green` (0.9);
  - model below `fallback_red` (0.3) → red;
  - hint → always yellow; no leaf → red;
  - knowledge is never green; library is green only with an ISBN or a fitting issuer.
- Nothing moves without `--apply`. Every move is journaled before it happens, and `undo` reverses a run.
- Gate before every commit:
  - `uv run pytest -m "not slow" -o addopts="-ra --strict-markers --strict-config" -q`
  - `uv run ruff check src/ tests/`
  - `uv run ruff format --check src/ tests/`
  - `uv run mypy src/`
- Docs are updated in the same task as the change that makes them stale (owner rule). Every task adds its line under `CHANGELOG.md` `## [Unreleased]`.
- Commits end with:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx
  ```
  Write the message to a file and use `git commit -F <file>`. Stage files explicitly; never stage `.serena/`, `.claude/`, `.rtk/` or `.superpowers/`.
- Branch `feat/model-first` (already created from `main` at v2.0).

## Review Focus

1. **No key, or model off.** The owner still gets suggestions: unpinned rule and issuer matches show up as yellow `hint` verdicts, never green, and never cached. Task 5 tests this.
2. **A file that matches a pinned rule and also has a verified ISBN.** The ISBN wins and the Thema folder and rename still apply. Task 5 tests this.
3. **Verdicts cached under v2.0** must not be reused after the prompt or the models change. The fingerprint includes `PROMPT_VERSION`, both models and `preview_chars`. Task 4 tests this.
4. **Pressing `q` or ending input in the middle of a group** keeps everything already confirmed, including files confirmed one by one inside that group. Task 7 tests this.
5. **A secret file, metadata value, hint or past-decision name** never appears in any prompt. Tasks 4, 9 and 10 test this.

---

### Task 1: Quiet logging by default, `--verbose`, no litellm chatter

**Files:**
- Modify: `src/para_files/cli/app.py`
- Modify: `src/para_files/core/fallback.py:45-49` (`litellm_complete`)
- Modify: `docs/cli/overview.md` (global options), `CHANGELOG.md`
- Test: `tests/test_cli_app.py`, `tests/test_core_fallback.py`

**Interfaces:**
- Produces: `para_files.cli.app.configure_logging(verbose: bool) -> None`; global option `--verbose/-v`.

- [ ] **Step 1: Write the failing tests.** Append to `tests/test_cli_app.py`:

```python
import sys

import pytest
from loguru import logger

from para_files.cli.app import configure_logging


@pytest.fixture
def restore_logger():
    yield
    logger.remove()
    logger.add(sys.__stderr__)


def test_logging_is_quiet_by_default(capsys, restore_logger):
    configure_logging(verbose=False)
    logger.debug("debug line")
    logger.warning("warning line")
    err = capsys.readouterr().err
    assert "debug line" not in err
    assert "warning line" in err


def test_verbose_shows_debug(capsys, restore_logger):
    configure_logging(verbose=True)
    logger.debug("debug line")
    assert "debug line" in capsys.readouterr().err


def test_verbose_option_is_accepted():
    from typer.testing import CliRunner

    from para_files.cli import app

    result = CliRunner().invoke(app, ["-v", "--version"])
    assert result.exit_code == 0, result.output
```

Append to `tests/test_core_fallback.py`:

```python
def test_litellm_debug_info_is_suppressed(monkeypatch):
    import sys
    import types

    from para_files.core import fallback

    fake = types.SimpleNamespace(suppress_debug_info=False, completion=lambda **_kw: "reply")
    monkeypatch.setitem(sys.modules, "litellm", fake)
    assert fallback.litellm_complete(model="m") == "reply"
    assert fake.suppress_debug_info is True
```

- [ ] **Step 2: Run them to see them fail.**
Run: `uv run pytest tests/test_cli_app.py tests/test_core_fallback.py -q -o addopts="" -k "logging or verbose or suppressed"`
Expected: FAIL with `ImportError: cannot import name 'configure_logging'`, and the suppress test with `assert False is True`.

- [ ] **Step 3: Implement.** In `src/para_files/cli/app.py`, add the imports `import sys` and `from loguru import logger`, then:

```python
LOG_FORMAT = "{level}: {message}"


def configure_logging(verbose: bool) -> None:  # noqa: FBT001 - plain switch
    """WARNING and above on stderr (DEBUG with --verbose); never stdout, so --json stays clean."""
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if verbose else "WARNING", format=LOG_FORMAT)
```

Then change `main` to:

```python
@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version", "-V", callback=_show_version, is_eager=True, help="Show the version."
        ),
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show debug logs on stderr.")
    ] = False,
) -> None:
    """File documents into a PARA tree: preview first, apply on request, undo any run."""
    configure_logging(verbose)
```

In `src/para_files/core/fallback.py`, change `litellm_complete` to:

```python
def litellm_complete(**kwargs: Any) -> Any:  # noqa: ANN401 - litellm's keyword arguments and reply
    """litellm.completion, imported on first use: importing litellm takes seconds."""
    import litellm

    litellm.suppress_debug_info = True  # no "Give Feedback" banners on stdout
    return litellm.completion(**kwargs)
```

- [ ] **Step 4: Run the tests and the gate.**
Run: `uv run pytest tests/test_cli_app.py tests/test_core_fallback.py -q -o addopts=""`, then the full gate.
Expected: PASS. If an existing test added its own loguru sink before invoking the CLI, `logger.remove()` would drop it; `grep -rn "logger.add" tests` finds only the fixture above.

- [ ] **Step 5: Docs and commit.**
  - In `docs/cli/overview.md`, add a "Global options" line: `--verbose/-v` shows debug logs on stderr; by default only warnings are shown.
  - Under `CHANGELOG.md` `## [Unreleased]`, `### Changed`, add: "Logs are quiet by default (warnings only, on stderr); `--verbose` shows debug lines."

```bash
git add src/para_files/cli/app.py src/para_files/core/fallback.py tests/test_cli_app.py tests/test_core_fallback.py docs/cli/overview.md CHANGELOG.md
git commit -F <msgfile>   # "feat(cli): quiet logging by default, --verbose for debug"
```

---

### Task 2: `--review` refuses to run without a terminal

**Files:**
- Modify: `src/para_files/cli/review.py`, `src/para_files/cli/sort_cmd.py`, `tests/core_helpers.py` (`setup_cli`)
- Modify: `docs/cli/sort.md`, `docs/troubleshooting.md`, `CHANGELOG.md`
- Test: `tests/test_cli_sort.py`

**Interfaces:**
- Produces: `para_files.cli.review.stdin_is_tty() -> bool`. The sort command calls it as a module attribute, so tests can patch it.

- [ ] **Step 1: Write the failing test.** Append to `tests/test_cli_sort.py`:

```python
def test_review_refuses_without_a_terminal(tmp_path, monkeypatch):
    from para_files.cli import review as review_cli

    root = setup_cli(tmp_path, monkeypatch)
    monkeypatch.setattr(review_cli, "stdin_is_tty", lambda: False)
    note = put(root, "0_Inbox/a_notes.md", "# a")
    result = runner.invoke(app, ["sort", "--apply", "--review"], input="\n")
    assert result.exit_code != 0
    assert "needs a terminal" in result.output
    assert note.exists()
```

- [ ] **Step 2: Run it to see it fail.**
Run: `uv run pytest tests/test_cli_sort.py -q -o addopts="" -k terminal`
Expected: FAIL with `AttributeError: ... has no attribute 'stdin_is_tty'`.

- [ ] **Step 3: Implement.**
  - In `src/para_files/cli/review.py`, add `import sys` and:

```python
def stdin_is_tty() -> bool:
    """True when a person can answer the questions: stdin is a terminal."""
    return sys.stdin.isatty()
```

  - In `src/para_files/cli/sort_cmd.py`, add `from para_files.cli import review as review_cli`. Directly after the `if review and as_json:` check, add:

```python
    if review and not review_cli.stdin_is_tty():
        fail(
            "--review asks questions and needs a terminal: run it in a terminal window, "
            "not through a pipe or an assistant's shell"
        )
```

  - In `tests/core_helpers.py` `setup_cli`, add this before `return root` (the CLI tests answer through `CliRunner` input):

```python
    from para_files.cli import review as review_cli

    monkeypatch.setattr(review_cli, "stdin_is_tty", lambda: True)
```

- [ ] **Step 4: Run the tests and the gate.**
Run: `uv run pytest tests/test_cli_sort.py -q -o addopts=""`, then the full gate.
Expected: PASS, and every existing review test still passes.

- [ ] **Step 5: Docs and commit.**
  - In `docs/cli/sort.md` "Review", add: "`--review` needs a real terminal; through a pipe or an assistant's shell it stops with an error before classifying anything."
  - In `docs/troubleshooting.md`, add a row: `--review asks questions and needs a terminal` | stdin is not a terminal | run it in a terminal window.
  - In the CHANGELOG under `### Fixed`, add: "`sort --apply --review` refuses to start without a terminal instead of moving the green files and stopping at the first question."

```bash
git add src/para_files/cli/review.py src/para_files/cli/sort_cmd.py tests/core_helpers.py tests/test_cli_sort.py docs/cli/sort.md docs/troubleshooting.md CHANGELOG.md
git commit -F <msgfile>   # "fix(cli): --review refuses to run without a terminal"
```

---

### Task 3: `pin` on rules

**Files:**
- Modify: `src/para_files/core/tree.py` (`Rule`, `validation_warnings`)
- Modify: `src/para_files/cli/tree_cmd.py` (`_print_leaves`)
- Modify: `examples/rules.yaml`, `tests/core_helpers.py` (`RULES`)
- Modify: `docs/configuration.md` (rules.yaml section), `CHANGELOG.md`
- Test: `tests/test_core_tree.py`, `tests/test_cli_tree.py`

**Interfaces:**
- Produces: `Rule.pin: bool | Literal["exif"]` (default `False`). Task 5 reads it through `pin_decides(rule, evidence)`, which Task 5 defines.

- [ ] **Step 1: Write the failing tests.** Append to `tests/test_core_tree.py`:

```python
def test_rule_pin_values():
    from para_files.core.tree import RulesFile

    rules = RulesFile.model_validate(
        {
            "rules": [
                {"name": "a", "leaf": "x", "globs": ["*a*"]},
                {"name": "b", "leaf": "x", "globs": ["*b*"], "pin": True},
                {"name": "c", "leaf": "x", "globs": ["*.jpg"], "pin": "exif"},
            ]
        }
    )
    assert [rule.pin for rule in rules.rules] == [False, True, "exif"]


def test_rule_pin_rejects_other_values():
    from pydantic import ValidationError

    from para_files.core.tree import RulesFile

    with pytest.raises(ValidationError):
        RulesFile.model_validate(
            {"rules": [{"name": "a", "leaf": "x", "globs": ["*a*"], "pin": "maybe"}]}
        )


def test_pin_warnings():
    from para_files.core.tree import RulesFile, TreeConfig, validation_warnings
    from tests.core_helpers import make_config

    base = make_config()
    rules = RulesFile.model_validate(
        {
            "rules": [
                {"name": "notes", "leaf": "resources_it", "globs": ["*notes*"], "pin": True},
                {"name": "pdfs", "leaf": "resources_docs", "globs": ["*.pdf"], "pin": True},
                {"name": "shots", "leaf": "archives_photos", "globs": ["*.jpg"], "pin": "exif"},
            ]
        }
    )
    warnings = validation_warnings(TreeConfig(tree=base.tree, rules=rules, issuers=base.issuers))
    assert any("'notes'" in w and "knowledge" in w for w in warnings)
    assert any("'pdfs'" in w and "extension" in w for w in warnings)
    assert not any("'shots'" in w and "pinned" in w for w in warnings)
```

(If `pytest` is not imported at the top of `tests/test_core_tree.py`, add `import pytest`.)

Append to `tests/test_cli_tree.py`:

```python
def test_tree_shows_pinned_rules(tmp_path, monkeypatch):
    setup_cli(tmp_path, monkeypatch)
    result = runner.invoke(app, ["tree"])
    assert result.exit_code == 0, result.output
    assert "pinned 1" in result.output
```

- [ ] **Step 2: Run them to see them fail.**
Run: `uv run pytest tests/test_core_tree.py tests/test_cli_tree.py -q -o addopts="" -k "pin"`
Expected: FAIL. Pydantic rejects the extra field `pin`, and "pinned 1" is not in the output.

- [ ] **Step 3: Implement.**

In `src/para_files/core/tree.py`, add `Literal` to the `typing` import if it is not there, then change `Rule`:

```python
class Rule(BaseModel):
    """A filename rule. `pin: true` decides alone; `pin: exif` decides only for files with an
    EXIF date (camera photos); unpinned rules are hints for the model."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    leaf: NonEmpty
    globs: tuple[NonEmpty, ...] = Field(min_length=1)
    pin: bool | Literal["exif"] = False
```

Add a module constant near `SHORT_LITERALS`:

```python
EXTENSION_ONLY = re.compile(r"\*\.[^*?/]+")
```

In `validation_warnings`, just before `return warnings`, add:

```python
    for rule in config.rules.rules:
        leaf = config.tree.leaves.get(rule.leaf)
        if not rule.pin or leaf is None:
            continue
        if leaf.kind == "knowledge":
            warnings.append(
                f"rule {rule.name!r}: pinned on knowledge leaf {rule.leaf!r}; knowledge is "
                "never green, so the pin only skips the model"
            )
        if rule.pin is True and leaf.kind != "media":
            warnings += [
                f"rule {rule.name!r}: pinned glob {glob!r} matches by extension only; "
                "narrow it, or unpin the rule"
                for glob in rule.globs
                if EXTENSION_ONLY.fullmatch(glob)
            ]
```

In `src/para_files/cli/tree_cmd.py` `_print_leaves`, add `pinned = Counter(rule.leaf for rule in config.rules.rules if rule.pin)` after `rules = ...`, and change the row format to:

```python
            f"rules {rules[leaf_id]:<3} pinned {pinned[leaf_id]:<3} issuers {issuers[leaf_id]}"
```

In `tests/core_helpers.py` `RULES`:
- payslips gets `"pin": True`;
- photos gets `"pin": "exif"`;
- whitepapers and it_notes stay unpinned.

In `examples/rules.yaml`:
- add `pin: true` under `payslips`;
- add `pin: exif` under `photos`;
- change the header comment to:
  `# Example rules: filename globs (case-insensitive) -> leaf. Pinned rules decide alone; the rest are hints for the model.`

- [ ] **Step 4: Run the tests and the gate.**
Run: `uv run pytest tests/test_core_tree.py tests/test_cli_tree.py -q -o addopts=""`, then the full gate.
Expected: PASS. Nothing reads `pin` yet, so behaviour is unchanged.

- [ ] **Step 5: Docs and commit.**
  - In `docs/configuration.md` "rules.yaml", document `pin: true` (decides alone; green, except that knowledge and library are capped at yellow) and `pin: exif` (decides only when the file has an EXIF date, e.g. camera photos). State that unpinned rules are hints for the model, and list the two new warnings.
  - In the CHANGELOG under `### Added`, add: "`pin: true` / `pin: exif` on rules (`rules.yaml`); `tree` shows pinned counts."

```bash
git add src/para_files/core/tree.py src/para_files/cli/tree_cmd.py examples/rules.yaml tests/core_helpers.py tests/test_core_tree.py tests/test_cli_tree.py docs/configuration.md CHANGELOG.md
git commit -F <msgfile>   # "feat(config): pin rules (pin: true / pin: exif)"
```

---

### Task 4: Prompt v2 (hints, metadata, full preview, folder paths, "about") and a versioned cache key

**Files:**
- Modify: `src/para_files/core/fallback.py`, `src/para_files/core/cache.py` (`config_fingerprint`), `src/para_files/core/sort.py` (`build_context`)
- Modify: `CHANGELOG.md`
- Test: `tests/test_core_fallback.py`, `tests/test_core_cache.py`

**Interfaces:**
- Produces:
  - `Hint(source: str, leaf_id: str)` (frozen dataclass);
  - `FallbackChoice.about: str = ""`;
  - `parse_reply(content: str | None, menu: dict[str, str]) -> tuple[Ranked, str]`, which replaces `parse_choices`;
  - `messages(menu, evidence, hints=())`;
  - `evidence_text(evidence, hints=())`;
  - `visible_hints(hints, menu) -> list[Hint]`;
  - `OpenRouterFallback.decide(evidence, tree, hints: Sequence[Hint] = ()) -> FallbackChoice | None`;
  - `PROMPT_VERSION: str`;
  - `config_fingerprint(directory: Path, *parts: str) -> str`.
- `core/decide.py` keeps calling `decide(evidence, tree)` until Task 5; that still works because `hints` defaults to `()`.

- [ ] **Step 1: Write the failing tests.** Append to `tests/test_core_fallback.py`:

```python
import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from para_files.core import fallback
from para_files.core.evidence import Evidence
from para_files.core.fallback import (
    Hint,
    OpenRouterFallback,
    evidence_text,
    leaf_menu,
    messages,
    parse_reply,
)
from tests.core_helpers import make_config


def ev(**kw):
    base = {
        "path": Path("/x/f.pdf"),
        "name": "f.pdf",
        "ext": ".pdf",
        "size": 1,
        "mtime": 0.0,
        "sha256": "0" * 64,
    }
    base.update(kw)
    return Evidence(**base)


def reply(content):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def test_prompt_has_type_metadata_isbn_date_and_the_whole_preview():
    text = evidence_text(
        ev(
            doc_meta={"title": "Storage Guide", "author": "A. Writer", "page_count": "12"},
            isbns=("9780000000001",),
            exif_date=datetime(2025, 3, 4),
            text_preview="A" * 3000,
        )
    )
    assert "Type: .pdf, 12 pages" in text
    assert "Title: Storage Guide" in text
    assert "Author: A. Writer" in text
    assert "ISBN found: 9780000000001" in text
    assert "Date taken: 2025-03-04" in text
    assert "A" * 3000 in text
    assert "may come from OCR" in text


def test_secret_metadata_and_hints_are_left_out(monkeypatch):
    monkeypatch.setattr(
        fallback, "secret_reason", lambda name, text="": "name" if "SECRET" in name else None
    )
    menu = leaf_menu(make_config().tree)
    hints = [
        Hint("rule 'invoices' (glob '*inv*')", "archives_5y_factures"),
        Hint("rule 'gone'", "no_such_leaf"),
        Hint("SECRET rule", "archives_5y_factures"),
    ]
    user = messages(menu, ev(doc_meta={"title": "SECRET plan"}), hints)[1]["content"]
    assert "rule 'invoices' (glob '*inv*') -> archives_5y_factures" in user
    assert "no_such_leaf" not in user
    assert "SECRET" not in user


def test_menu_shows_each_leaf_path():
    menu = leaf_menu(make_config().tree)
    assert menu["archives_5y_factures"].endswith("(4_Archives/5y_factures)")


def test_parse_reply_reads_about_and_choices():
    menu = leaf_menu(make_config().tree)
    content = (
        '{"about": "  Card   statement  ", '
        '"choices": [{"leaf": "archives_10y_banques", "confidence": 0.8}]}'
    )
    assert parse_reply(content, menu) == ([("archives_10y_banques", 0.8)], "Card statement")


def test_decide_sends_hints_and_returns_about():
    seen = {}

    def complete(**kwargs):
        seen.update(kwargs)
        return reply(
            json.dumps(
                {
                    "about": "AcmeCard statement",
                    "choices": [
                        {"leaf": "archives_10y_banques", "confidence": 0.7},
                        {"leaf": "archives_5y_factures", "confidence": 0.2},
                    ],
                }
            )
        )

    model = OpenRouterFallback("key", ["m1"], complete=complete)
    hint = Hint("issuer 'acmecard' (pattern 'AcmeCard')", "archives_10y_banques")
    choice = model.decide(ev(text_preview="AcmeCard"), make_config().tree, [hint])
    assert choice is not None
    assert (choice.leaf_id, choice.about) == ("archives_10y_banques", "AcmeCard statement")
    assert choice.ranked == (("archives_10y_banques", 0.7), ("archives_5y_factures", 0.2))
    assert "issuer 'acmecard'" in seen["messages"][1]["content"]
    assert seen["extra_body"]["provider"] == {"zdr": True, "data_collection": "deny"}
    schema = seen["response_format"]["json_schema"]["schema"]
    assert schema["required"] == ["about", "choices"]
```

Append to `tests/test_core_cache.py`:

```python
def test_fingerprint_depends_on_every_part(tmp_path):
    from para_files.core.cache import config_fingerprint

    base = config_fingerprint(tmp_path, "m1", "m2", "2", "2000")
    assert base == config_fingerprint(tmp_path, "m1", "m2", "2", "2000")
    assert base != config_fingerprint(tmp_path, "m1", "m2", "3", "2000")
    assert base != config_fingerprint(tmp_path, "m1", "m3", "2", "2000")
    assert base != config_fingerprint(tmp_path, "m1", "m2", "2", "4000")
```

- [ ] **Step 2: Run them to see them fail.**
Run: `uv run pytest tests/test_core_fallback.py tests/test_core_cache.py -q -o addopts=""`
Expected: FAIL with `ImportError: cannot import name 'Hint'`.

- [ ] **Step 3: Implement `core/fallback.py`.** Replace the constants block, the dataclasses and every function from `leaf_menu` through `OpenRouterFallback` with the code below. Keep `litellm_complete` (from Task 1), `FallbackError`, `_without_secret_parts`, `_is_secret_leaf`, `_keywords_part`, `_probability` and `make_fallback` as they are. Update the module docstring's first line to: `"""The model reads the file and ranks the leaves (spec §4.2, model first)."""`.

```python
OPENROUTER = "openrouter/"
PRIVACY = {"zdr": True, "data_collection": "deny"}
REASONING = {"effort": "low"}  # Gemini 3.8 Flash and Sonnet 5.5 refuse reasoning off
MAX_TOKENS = 4000
TIMEOUT = 120.0
RETRIES = 2
MAX_LISTED_ENTRIES = 50
MAX_CHOICES = 3
MAX_ISBNS = 3
MAX_ABOUT = 80
# Bump on any change to SYSTEM, messages() or response_format(): it is part of the cache key.
PROMPT_VERSION = "2"
META_FIELDS = (("title", "Title"), ("author", "Author"), ("subject", "Subject"))
SYSTEM = (
    "You file documents into a person's PARA folder tree. Read the content first: the file "
    "name can be misleading. Hints come from the owner's filename rules and issuer patterns; "
    "they are often right but can be wrong, so follow a hint only when the content agrees. "
    "Under 4_Archives, a prefix such as 10y_, 5y_, 2y_, ctr_ or ret_ means records kept for "
    "that retention period; 3_Resources holds reference material, 2_Areas ongoing "
    "responsibilities, 1_Projects active projects. Rank the three most likely folder ids from "
    "the list, most likely first, each with the probability that it is the right folder, and "
    "say in at most 12 words what the document is. Reply only with JSON."
)
Complete = Callable[..., Any]
Ranked = list[tuple[str, float]]


@dataclass(frozen=True)
class Hint:
    """What a non-deciding rule, book heuristic or issuer suggests; shown to the model."""

    source: str
    leaf_id: str


@dataclass(frozen=True)
class FallbackChoice:
    """The model's first choice, which model answered, its ranked list and what the file is."""

    leaf_id: str
    confidence: float
    model: str
    ranked: tuple[tuple[str, float], ...]
    about: str = ""
```

(`litellm_complete` and `FallbackError` stay between `Ranked` and `Hint`, as today.)

```python
def leaf_menu(tree: Tree) -> dict[str, str]:
    """Leaf id -> describe, keywords and path: the model's only choices; no secret leaves."""
    return {
        leaf_id: (
            f"{_without_secret_parts(leaf.describe)}{_keywords_part(leaf.keywords)} ({leaf.path})"
        )
        for leaf_id, leaf in tree.leaves.items()
        if not _is_secret_leaf(leaf_id, leaf.path, leaf.describe)
    }


def _type_line(evidence: Evidence) -> str:
    pages = evidence.doc_meta.get("page_count", "")
    kind = evidence.ext or "(none)"
    return f"Type: {kind}, {pages} pages" if pages not in {"", "0"} else f"Type: {kind}"


def _meta_lines(evidence: Evidence) -> list[str]:
    lines = [_type_line(evidence)]
    for key, label in META_FIELDS:
        value = " ".join(evidence.doc_meta.get(key, "").split())
        if value and secret_reason(value, value) is None:
            lines.append(f"{label}: {value}")
    if evidence.isbns:
        lines.append(f"ISBN found: {', '.join(evidence.isbns[:MAX_ISBNS])}")
    if evidence.exif_date is not None:
        lines.append(f"Date taken: {evidence.exif_date.date().isoformat()}")
    return lines


def visible_hints(hints: Sequence[Hint], menu: dict[str, str]) -> list[Hint]:
    """Hints whose leaf the model may choose and whose wording is not secret."""
    return [hint for hint in hints if hint.leaf_id in menu and secret_reason(hint.source) is None]


def evidence_text(evidence: Evidence, hints: Sequence[Hint] = ()) -> str:
    """Name, type, metadata, hints, the whole preview and archive entries; never the path."""
    lines = [f"Filename: {evidence.name}", *_meta_lines(evidence)]
    if hints:
        lines.append("Hints (from the owner's rules; may be wrong):")
        lines += [f"- {hint.source} -> {hint.leaf_id}" for hint in hints]
    body = evidence.text_preview if evidence.text_preview.strip() else "(no text)"
    text = "\n".join(lines) + f"\n\nContent preview (may come from OCR):\n{body}"
    if evidence.archive_listing:
        entries = "\n".join(evidence.archive_listing[:MAX_LISTED_ENTRIES])
        text += f"\n\nArchive entries:\n{entries}"
    return text


def messages(
    menu: dict[str, str], evidence: Evidence, hints: Sequence[Hint] = ()
) -> list[dict[str, str]]:
    """System prompt, then the folder list (stable, so providers can cache it), then the file."""
    folders = "\n".join(f"- {leaf_id}: {describe}" for leaf_id, describe in menu.items())
    file_part = evidence_text(evidence, visible_hints(hints, menu))
    user = f"Folders:\n{folders}\n\nFile:\n{file_part}"
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def response_format(menu: dict[str, str]) -> dict[str, Any]:
    """JSON schema: a short 'about' and up to 3 choices, each an enum leaf id with a confidence."""
    choice = {
        "type": "object",
        "additionalProperties": False,
        "required": ["leaf", "confidence"],
        "properties": {
            "leaf": {"type": "string", "enum": list(menu)},
            "confidence": {"type": "number"},
        },
    }
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["about", "choices"],
        "properties": {
            "about": {"type": "string"},
            "choices": {"type": "array", "items": choice, "minItems": 1, "maxItems": MAX_CHOICES},
        },
    }
    return {
        "type": "json_schema",
        "json_schema": {"name": "filing", "strict": True, "schema": schema},
    }
```

(`_probability` stays here, unchanged.)

```python
def parse_reply(content: str | None, menu: dict[str, str]) -> tuple[Ranked, str]:
    """Ranked (leaf, probability) and the model's one-line 'about'; bad choices dropped."""
    match = re.search(r"\{.*\}", content or "", re.DOTALL)
    try:
        data = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError as exc:
        msg = "reply is not JSON"
        raise FallbackError(msg) from exc
    choices = data.get("choices") if isinstance(data, dict) else None
    if not isinstance(choices, list):
        msg = "reply has no choices list"
        raise FallbackError(msg)
    ranked: Ranked = []
    for item in choices:
        if not isinstance(item, dict):
            continue
        leaf, probability = item.get("leaf"), _probability(item.get("confidence"))
        if not isinstance(leaf, str) or leaf not in menu or probability is None:
            continue
        if leaf not in {seen for seen, _ in ranked}:
            ranked.append((leaf, probability))
    about = data.get("about") if isinstance(data, dict) else None
    text = " ".join(about.split())[:MAX_ABOUT] if isinstance(about, str) else ""
    return ranked[:MAX_CHOICES], text


class OpenRouterFallback:
    """The model signal: primary model, then backup, through litellm; behind a circuit breaker."""

    def __init__(
        self,
        key: str,
        models: Sequence[str],
        *,
        complete: Complete = litellm_complete,
        breaker: CircuitBreaker | None = None,
    ) -> None:
        self._key = key
        self._models = tuple(models)
        self._complete = complete
        self._breaker = breaker or CircuitBreaker()

    def _ask(
        self, model: str, menu: dict[str, str], evidence: Evidence, hints: Sequence[Hint]
    ) -> tuple[Ranked, str]:
        response = self._complete(
            model=f"{OPENROUTER}{model}",
            messages=messages(menu, evidence, hints),
            api_key=self._key,
            temperature=0,
            max_tokens=MAX_TOKENS,
            response_format=response_format(menu),
            extra_body={"provider": PRIVACY, "reasoning": REASONING},
            timeout=TIMEOUT,
            num_retries=RETRIES,
        )
        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, TypeError) as exc:
            msg = f"malformed reply: {type(exc).__name__}"
            raise FallbackError(msg) from exc
        ranked, about = parse_reply(content, menu)
        if not ranked:
            msg = "reply has no usable choice"
            raise FallbackError(msg)
        return ranked, about

    def decide(
        self, evidence: Evidence, tree: Tree, hints: Sequence[Hint] = ()
    ) -> FallbackChoice | None:
        """First choice of the first model that answers; None for secrets or failures."""
        if evidence.secret is not None or self._breaker.is_open:
            return None
        menu = leaf_menu(tree)
        if not menu:
            return None
        for model in self._models:
            try:
                ranked, about = self._ask(model, menu, evidence, hints)
            except Exception as exc:  # noqa: BLE001 - any provider error moves on to the backup
                logger.warning("model {} failed on {}: {}", model, evidence.name, exc)
                continue
            self._breaker.record_success()
            leaf_id, confidence = ranked[0]
            return FallbackChoice(leaf_id, confidence, model, tuple(ranked), about)
        self._breaker.record_failure()
        return None
```

Remove the `PREVIEW_CHARS` constant: the evidence preview is already cut at `settings.preview_chars`. In the existing tests, replace every use of `parse_choices(content, menu)` with `parse_reply(content, menu)[0]`. Also update any test that asserts the old schema `required == ["choices"]`, the old menu text without `(path)`, or the old `Content preview:` label (`grep -n "parse_choices\|Content preview\|required" tests/test_core_fallback.py`).

- [ ] **Step 4: Implement the cache key.** In `src/para_files/core/cache.py`:

```python
def config_fingerprint(directory: Path, *parts: str) -> str:
    """Hash of tree.yaml, rules.yaml, issuers.yaml (missing = empty) and the given parts
    (models, prompt version, preview size): change any of them and the model is asked again."""
    digest = hashlib.sha256()
    for name in CONFIG_FILES:
        path = directory / name
        digest.update(name.encode() + b"\0")
        digest.update((path.read_bytes() if path.exists() else b"") + b"\0")
    for part in parts:
        digest.update(part.encode() + b"\0")
    return digest.hexdigest()
```

In `src/para_files/core/sort.py`, import `PROMPT_VERSION` from `para_files.core.fallback` (next to `make_fallback`) and set:

```python
        fingerprint=config_fingerprint(
            directory,
            settings.fallback_model,
            settings.fallback_backup_model,
            PROMPT_VERSION,
            str(settings.preview_chars),
        ),
```

- [ ] **Step 5: Run the tests and the gate.**
Run: `uv run pytest tests/test_core_fallback.py tests/test_core_cache.py tests/test_core_sort.py -q -o addopts=""`, then the full gate.
Expected: PASS.

- [ ] **Step 6: Commit.** In the CHANGELOG under `### Changed`, add: "The model's prompt carries the file type, page count, title/author/subject, ISBNs, EXIF date, the whole preview (including OCR text), each folder's path, and the rule and issuer matches as hints; it also answers a short 'about'. Cached verdicts are keyed by prompt version, both models and preview size."

```bash
git add src/para_files/core/fallback.py src/para_files/core/cache.py src/para_files/core/sort.py tests/test_core_fallback.py tests/test_core_cache.py CHANGELOG.md
git commit -F <msgfile>   # "feat(model): prompt v2 with hints, metadata and about; versioned cache key"
```

---

### Task 5: Model-first cascade, bands and `explain`

**Files:**
- Modify: `src/para_files/core/decide.py` (rewrite the cascade part), `src/para_files/cli/explain_cmd.py`
- Modify: `src/para_files/core/settings.py` (drop `issuers_green`), `src/para_files/cli/tree_cmd.py` (settings line), `.env.example`
- Modify: `docs/architecture.md`, `docs/configuration.md`, `docs/cli/explain.md`, `CHANGELOG.md`
- Test: `tests/test_core_decide.py`, `tests/test_cli_explain.py`, plus updates in `tests/test_core_sort.py` and `tests/test_cli_sort.py`

**Interfaces:**
- Consumes: `Hint`, `FallbackChoice.about`, `decide(evidence, tree, hints)` (Task 4); `Rule.pin` (Task 3).
- Produces:
  - `pin_decides(rule: Rule, evidence: Evidence) -> bool`;
  - `issuer_for(leaf_id: str, issuer: str | None, config: TreeConfig) -> str | None`;
  - `Step(name: str, verdict: Verdict | None, note: str | None = None)`;
  - `choose(evidence, ctx, *, ask_model: bool = True) -> tuple[Verdict, list[Step]]`;
  - `Verdict.ranked: tuple[tuple[str, float], ...] = ()` and `Verdict.about: str | None = None`;
  - `Decision.ranked` and `Decision.about`, with the same types.
  - Signal names: `"secret"`, `"books"` (ISBN only), `"rules"` (pinned only), `"fallback"` (model), `"hint"`, `"none"`, `"error"`.
  - `Verdict.issuer` is now the **matched** issuer, whatever the chosen leaf. `decision_for` keeps it only when `issuer_for(...)` says the leaf is one of that issuer's leaves.
- Removed: `SIGNALS`, `run_signals`, `signal_verdicts`, `_rules`, `_books`, `_issuers`, `_fallback`, `CoreSettings.issuers_green`.

- [ ] **Step 1: Write the failing tests.** Append to `tests/test_core_decide.py`. Also add `from para_files.core.tree import RulesFile, TreeConfig` and `from para_files.core.fallback import Hint` to its imports if they are missing.

```python
class HintedFallback:
    """Records the hints it was given; answers a fixed leaf with an 'about'."""

    def __init__(self, leaf="archives_10y_banques", confidence=0.7):
        self.leaf, self.confidence, self.hints = leaf, confidence, []

    def decide(self, evidence, tree, hints=()):
        self.hints.append(list(hints))
        return FallbackChoice(
            self.leaf,
            self.confidence,
            "m1",
            ((self.leaf, self.confidence), ("archives_5y_factures", 0.2)),
            "a card statement",
        )


def with_rules(ctx, *extra):
    base = ctx.config
    rules = RulesFile.model_validate({"rules": [*extra, *[r.model_dump() for r in base.rules.rules]]})
    ctx.config = TreeConfig(tree=base.tree, rules=rules, issuers=base.issuers)
    return ctx


def test_pinned_rule_is_green_and_the_model_is_not_asked(tmp_path):
    model = HintedFallback()
    ctx = make_ctx(tmp_path, fallback=model)
    d = classify(inbox_file(ctx, "Payslip_2025-12-22.txt"), ctx)
    assert (d.leaf_id, d.signal, d.band) == ("archives_10y_travail", "rules", "green")
    assert model.hints == []


def test_unpinned_rule_and_issuer_are_hints_and_the_issuer_fills_the_subkey(tmp_path):
    model = HintedFallback()
    ctx = with_rules(
        make_ctx(tmp_path, fallback=model),
        {"name": "broad", "leaf": "resources_docs", "globs": ["*card*"]},
    )
    d = classify(inbox_file(ctx, "acmecard_2026.txt", "AcmeCard statement"), ctx)
    assert (d.leaf_id, d.signal, d.band) == ("archives_10y_banques", "fallback", "yellow")
    assert d.target_dir == "4_Archives/10y_banques/acmecard/2026"
    assert d.about == "a card statement"
    assert d.ranked == (("archives_10y_banques", 0.7), ("archives_5y_factures", 0.2))
    sources = [hint.source for hint in model.hints[0]]
    assert sources[0].startswith("rule 'broad'")
    assert any(source.startswith("issuer 'acmecard'") for source in sources)


def test_model_off_gives_a_yellow_hint_even_when_calibrated(tmp_path):
    ctx = make_ctx(tmp_path, confirmed={"record": 1000, "library": 1000})
    d = classify(inbox_file(ctx, "statement.txt", "AcmeCard statement"), ctx)
    assert (d.leaf_id, d.signal, d.band) == ("archives_10y_banques", "hint", "yellow")
    assert "(model off)" in d.evidence_summary


def test_hint_verdicts_are_not_cached_but_model_verdicts_are(tmp_path):
    model = HintedFallback()
    ctx = make_ctx(tmp_path, fallback=model)
    path = inbox_file(ctx, "statement.txt", "AcmeCard statement")
    classify(path, ctx)
    classify(path, ctx)
    assert len(model.hints) == 1
    ctx.fallback = None
    other = inbox_file(ctx, "other.txt", "AcmeCard other")
    classify(other, ctx)
    assert ctx.cache.get_verdict(classify(other, ctx).sha256, "fp:other.txt") is None


def test_isbn_beats_a_pinned_rule(tmp_path):
    info = BookInfo(isbn="9780000000002", title="Payslip Handbook", authors=["A. Writer"])
    ctx = make_ctx(tmp_path)
    ctx.lookup = lambda _isbn: info
    path = inbox_file(ctx, "Payslip Handbook.pdf")
    monkey_isbns = ("9780000000002",)
    evidence = Evidence(
        path=path, name=path.name, ext=".pdf", size=1, mtime=0.0, sha256="1" * 64,
        isbns=monkey_isbns,
    )
    verdict, steps = decide.choose(evidence, ctx)
    assert (verdict.signal, verdict.isbn) == ("books", "9780000000002")
    assert steps[0].name == "isbn book"


def test_photo_rule_pins_only_with_an_exif_date(tmp_path):
    ctx = make_ctx(tmp_path)
    base = {"path": Path("/x/IMG_1.jpg"), "name": "IMG_1.jpg", "ext": ".jpg", "size": 1,
            "mtime": 0.0, "sha256": "2" * 64}
    with_date, _ = decide.choose(Evidence(**base, exif_date=datetime(2024, 5, 1)), ctx)
    without, _ = decide.choose(Evidence(**base), ctx)
    assert (with_date.signal, with_date.leaf_id) == ("rules", "archives_photos")
    assert (without.signal, without.leaf_id) == ("hint", "archives_photos")


def test_library_model_verdict_needs_an_issuer_to_be_green(tmp_path):
    model = HintedFallback(leaf="resources_docs", confidence=0.95)
    ctx = make_ctx(tmp_path, fallback=model, confirmed={"library": 1000})
    d = classify(inbox_file(ctx, "guide.txt", "storage guide"), ctx)
    assert (d.signal, d.band) == ("fallback", "yellow")


def test_secret_is_never_sent(tmp_path):
    model = HintedFallback()
    ctx = make_ctx(tmp_path, fallback=model)
    d = classify(inbox_file(ctx, "notes.txt", "vpn\npassword: hunter22\n"), ctx)
    assert (d.signal, d.band) == ("secret", "red")
    assert model.hints == []
```

`BookInfo` field names: check `src/para_files/utils/isbn_lookup.py` `BookInfo` and pass the fields its constructor needs, using a title that `is_title_coherent_with_filename` accepts for `Payslip Handbook.pdf`. The `with_rules` helper puts the extra rule **first**, so it is the first unpinned rule that matches.

Also make these updates to existing tests. They encode the old cascade and are now wrong:

| Where | Old expectation | New expectation |
|---|---|---|
| `tests/test_core_decide.py` | an issuer verdict with signal `"issuers"` (the lines asserting `"issuers"`) | `"hint"` (model off) |
| `tests/test_core_decide.py` | the "issuer green after calibration" test | asserts `band == "yellow"` (hints never go green), renamed `test_hint_stays_yellow_after_calibration` |
| `tests/test_core_decide.py` | the test asserting `classify(random_file).signal == "fallback"` | unchanged when nothing else matches |
| `tests/test_core_decide.py`, `tests/test_core_sort.py`, `tests/test_cli_sort.py` | photo tests expecting `"rules"`/green without an EXIF date | `"hint"`/yellow; tests that pass an `exif_date` still expect `"rules"` |
| `tests/test_core_decide.py` | the `resources_vendor`/AcmeCorp issuer test asserting signal `"issuers"` | `"hint"` |
| fakes in `tests/test_core_decide.py` (`FakeFallback.decide`) and `tests/test_core_sort.py` (`RecordingFallback.decide`) | signature `(self, evidence, tree)` | `(self, evidence, tree, hints=())` |

Replace the last test of `tests/test_cli_explain.py` (`test_signal_verdicts_report_errors_and_skip_the_model`) with:

```python
def test_choose_reports_errors_and_skips_the_model(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    path = root / "0_Inbox" / "a.txt"
    path.write_text("x")

    def boom(*_args):
        msg = "broken rules"
        raise RuntimeError(msg)

    monkeypatch.setattr(decide, "match_rule", boom)
    from para_files.cli.common import context_or_exit, settings_or_exit

    ctx = context_or_exit(settings_or_exit())
    verdict, steps = decide.choose(extract(path, root=root), ctx, ask_model=False)
    assert verdict.signal == "none"
    assert [(step.name, step.note) for step in steps] == [
        ("isbn book", "no verified ISBN"),
        ("pinned rule", "no pinned rule matches"),
        ("hint", "no rule, book or issuer matches"),
        ("model", "off (no key, or PARA_FILES_FALLBACK_ENABLED=false)"),
    ]
```

In `test_rule_match_is_explained`, replace the four signal assertions with:

```python
    assert "pinned rule  archives_10y_travail (1.00): pinned rule 'payslips'" in result.output
    assert "hint         archives_10y_banques" not in result.output
    assert "decision: green, archives_10y_travail -> 4_Archives/10y_travail/2025" in result.output
    assert "edit or unpin this rule in rules.yaml" in result.output
```

In `test_secret_shows_only_the_reason`, replace `"signals" not in result.output` with `"steps" not in result.output`.

- [ ] **Step 2: Run them to see them fail.**
Run: `uv run pytest tests/test_core_decide.py tests/test_cli_explain.py -q -o addopts=""`
Expected: FAIL. `choose` and `Decision.about` do not exist, and the signal names are still the old ones.

- [ ] **Step 3: Implement `core/decide.py`.**
  - Replace the module docstring and imports.
  - Keep `Band`, `RULE_CONFIDENCE`, `ISSUER_AGREED`, `ISSUER_ALONE`, `DATE_IN_NAME`, `Context`, `file_date`, `target_dir` and `classify` as they are.
  - Replace everything else with the code below. Keep `asdict` in the imports; `_verdict` uses it.

```python
"""The cascade (spec §4.2, model first): evidence -> verdict -> band -> target directory.

Order: the secret guard; a verified ISBN book; a pinned rule; the model, given the other
rule, book and issuer matches as hints; when the model is off or silent, the first hint
(always yellow). Only model verdicts are cached: everything else is cheap to recompute.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Literal, Protocol, TypeVar
from collections.abc import Sequence

from loguru import logger

from para_files.core.books import BookMatch, Lookup, match_book
from para_files.core.cache import Cache
from para_files.core.evidence import Evidence, extract
from para_files.core.fallback import FallbackChoice, Hint
from para_files.core.issuers import IssuerMatch, match_issuer
from para_files.core.rules import match_rule
from para_files.core.settings import CoreSettings
from para_files.core.tree import Kind, Leaf, Rule, Tree, TreeConfig
from para_files.utils.isbn_lookup import lookup_isbn
```

(Ruff sorts these imports; run `uv run ruff check --fix src/para_files/core/decide.py`.)

```python
T = TypeVar("T")


class Fallback(Protocol):
    """The model signal as the cascade sees it."""

    def decide(
        self, evidence: Evidence, tree: Tree, hints: Sequence[Hint] = ()
    ) -> FallbackChoice | None:
        """Leaf choice for this evidence, or None."""


@dataclass(frozen=True)
class Verdict:
    """What decided; model verdicts are cached by content hash and config fingerprint."""

    leaf_id: str | None
    signal: str
    confidence: float
    summary: str
    isbn: str | None = None
    issuer: str | None = None
    thema: str | None = None
    suggested_name: str | None = None
    ranked: tuple[tuple[str, float], ...] = ()
    about: str | None = None


@dataclass(frozen=True)
class Decision:
    """One file's outcome: leaf, target (relative to the PARA root), band and why."""

    path: Path
    sha256: str
    leaf_id: str | None
    target_dir: str | None
    band: Band
    signal: str
    confidence: float
    evidence_summary: str
    kind: Kind | None = None
    suggested_name: str | None = None
    ranked: tuple[tuple[str, float], ...] = ()
    about: str | None = None


@dataclass(frozen=True)
class Step:
    """One line of `explain`: what a signal said, or why it said nothing."""

    name: str
    verdict: Verdict | None
    note: str | None = None


@dataclass(frozen=True)
class _Hints:
    """The non-deciding matches for one file, in cascade order, and the issuer among them."""

    seen: tuple[tuple[Hint, float], ...]
    issuer: IssuerMatch | None

    @property
    def hints(self) -> tuple[Hint, ...]:
        return tuple(hint for hint, _ in self.seen)

    def sources(self) -> str:
        return "; ".join(hint.source for hint in self.hints)


NO_VERDICT = Verdict(None, "none", 0.0, "no signal decided")


def _safe(name: str, evidence: Evidence, call: Callable[[], T | None]) -> T | None:
    """call(); a failing signal is logged and treated as silent."""
    try:
        return call()
    except Exception as exc:  # noqa: BLE001 - KeyboardInterrupt is not an Exception
        logger.warning("signal {} failed on {}: {}", name, evidence.name, exc)
        return None


def pin_decides(rule: Rule, evidence: Evidence) -> bool:
    """A pinned rule decides alone; `pin: exif` only when the file has an EXIF date."""
    return rule.pin is True or (rule.pin == "exif" and evidence.exif_date is not None)


def issuer_for(leaf_id: str, issuer: str | None, config: TreeConfig) -> str | None:
    """The issuer, if leaf_id is one of its leaves (then {issuer} may fill); else None."""
    found = config.issuers.issuers.get(issuer) if issuer else None
    return issuer if found is not None and leaf_id in found.leaves else None


def _isbn_verdict(book: BookMatch | None) -> Verdict | None:
    if book is None or book.isbn is None:
        return None
    return Verdict(
        book.leaf_id,
        "books",
        book.confidence,
        f"ISBN {book.isbn}",
        isbn=book.isbn,
        thema=book.thema,
        suggested_name=book.suggested_name,
    )


def _pinned(evidence: Evidence, ctx: Context) -> Verdict | None:
    rules = [rule for rule in ctx.config.rules.rules if pin_decides(rule, evidence)]
    match = match_rule(evidence.name, rules)
    if match is None:
        return None
    summary = f"pinned rule {match.rule!r} glob {match.glob!r}"
    return Verdict(match.leaf_id, "rules", RULE_CONFIDENCE, summary)


def _hints(evidence: Evidence, ctx: Context, book: BookMatch | None) -> _Hints:
    seen: list[tuple[Hint, float]] = []
    rules = [rule for rule in ctx.config.rules.rules if not pin_decides(rule, evidence)]
    rule = _safe("rules", evidence, lambda: match_rule(evidence.name, rules))
    if rule is not None:
        seen.append((Hint(f"rule {rule.rule!r} (glob {rule.glob!r})", rule.leaf_id), 1.0))
    if book is not None and book.isbn is None:
        seen.append((Hint("book heuristics (no ISBN)", book.leaf_id), book.confidence))
    issuer = _safe(
        "issuers", evidence, lambda: match_issuer(evidence.name, evidence.text_preview, ctx.config)
    )
    if issuer is not None:
        agreed = ", leaf keyword agrees" if issuer.agreed else ""
        source = f"issuer {issuer.issuer!r} (pattern {issuer.pattern!r}{agreed})"
        seen.append((Hint(source, issuer.leaf_id), ISSUER_AGREED if issuer.agreed else ISSUER_ALONE))
    return _Hints(tuple(seen), issuer)


def _model_verdict(choice: FallbackChoice, found: _Hints) -> Verdict:
    ranked = ", ".join(f"{leaf} {p:.2f}" for leaf, p in choice.ranked)
    hints = f"; hints: {found.sources()}" if found.seen else ""
    return Verdict(
        choice.leaf_id,
        "fallback",
        choice.confidence,
        f"{choice.model}: {ranked}{hints}",
        issuer=found.issuer.issuer if found.issuer else None,
        ranked=choice.ranked,
        about=choice.about or None,
    )


def _hint_verdict(found: _Hints, why: str) -> Verdict:
    first, confidence = found.seen[0]
    ranked: list[tuple[str, float]] = []
    for hint, value in found.seen:
        if hint.leaf_id not in {leaf for leaf, _ in ranked}:
            ranked.append((hint.leaf_id, value))
    return Verdict(
        first.leaf_id,
        "hint",
        confidence,
        f"{found.sources()} ({why})",
        issuer=found.issuer.issuer if found.issuer else None,
        ranked=tuple(ranked),
    )


def choose(
    evidence: Evidence, ctx: Context, *, ask_model: bool = True
) -> tuple[Verdict, list[Step]]:
    """The winning verdict and every step that led to it (what `explain` prints)."""
    steps: list[Step] = []
    book = _safe(
        "books", evidence, lambda: match_book(evidence, ctx.config.tree, ctx.cache, ctx.lookup)
    )
    isbn = _isbn_verdict(book)
    steps.append(Step("isbn book", isbn, None if isbn else "no verified ISBN"))
    if isbn is not None:
        return isbn, steps
    pinned = _safe("rules", evidence, lambda: _pinned(evidence, ctx))
    steps.append(Step("pinned rule", pinned, None if pinned else "no pinned rule matches"))
    if pinned is not None:
        return pinned, steps
    found = _hints(evidence, ctx, book)
    steps += [
        Step("hint", Verdict(hint.leaf_id, "hint", value, hint.source)) for hint, value in found.seen
    ]
    if not found.seen:
        steps.append(Step("hint", None, "no rule, book or issuer matches"))
    fallback = ctx.fallback
    if fallback is None:
        why = "model off"
        steps.append(Step("model", None, "off (no key, or PARA_FILES_FALLBACK_ENABLED=false)"))
    elif not ask_model:
        why = "model not asked"
        steps.append(Step("model", None, "not asked (use --ask-model)"))
    else:
        why = "model did not answer"
        choice = _safe(
            "fallback", evidence, lambda: fallback.decide(evidence, ctx.config.tree, found.hints)
        )
        model = _model_verdict(choice, found) if choice is not None else None
        steps.append(Step("model", model, None if model else "no answer"))
        if model is not None:
            return model, steps
    return (_hint_verdict(found, why) if found.seen else NO_VERDICT), steps


def _cap(band: Band, kind: Kind, verdict: Verdict) -> Band:
    if band != "green":
        return band
    if kind == "knowledge":
        return "yellow"
    if kind == "library" and verdict.isbn is None and verdict.issuer is None:
        return "yellow"
    return band


def band_for(verdict: Verdict, kind: Kind, ctx: Context) -> Band:
    """Band from the signal, its confidence and the calibration state, then the kind caps.

    verdict.issuer must already be fitted to the leaf (see decision_for).
    """
    settings = ctx.settings
    if verdict.leaf_id is None:
        return "red"
    if verdict.signal == "fallback" and verdict.confidence < settings.fallback_red:
        return "red"
    band: Band
    if verdict.signal in {"rules", "books"}:
        band = "green"
    elif verdict.signal == "fallback":
        calibrated = ctx.confirmed.get(kind, 0) >= settings.calibration_min
        band = "green" if calibrated and verdict.confidence >= settings.fallback_green else "yellow"
    else:
        band = "yellow"
    return _cap(band, kind, verdict)


def _from_cache(data: dict[str, Any]) -> Verdict:
    ranked = tuple((str(leaf), float(p)) for leaf, p in data.pop("ranked", ()))
    return Verdict(**data, ranked=ranked)


def _verdict(evidence: Evidence, ctx: Context) -> Verdict:
    if evidence.secret is not None:
        return Verdict(None, "secret", 0.0, f"secret ({evidence.secret}): never sent, never moved")
    # Rules and issuers read the filename, so the name is part of the cache key.
    key = f"{ctx.fingerprint}:{evidence.name}"
    cached = ctx.cache.get_verdict(evidence.sha256, key)
    if cached is not None:
        return _from_cache(cached)
    verdict, _ = choose(evidence, ctx)
    if verdict.signal == "fallback":
        ctx.cache.put_verdict(evidence.sha256, key, asdict(verdict))
    return verdict


def decision_for(evidence: Evidence, verdict: Verdict, ctx: Context) -> Decision:
    """Band and target for a verdict on this evidence."""
    leaf = ctx.config.tree.leaves.get(verdict.leaf_id) if verdict.leaf_id else None
    if leaf is None or verdict.leaf_id is None:
        return Decision(
            path=evidence.path,
            sha256=evidence.sha256,
            leaf_id=None,
            target_dir=None,
            band="red",
            signal=verdict.signal,
            confidence=verdict.confidence,
            evidence_summary=verdict.summary,
            about=verdict.about,
        )
    fitted = replace(verdict, issuer=issuer_for(verdict.leaf_id, verdict.issuer, ctx.config))
    return Decision(
        path=evidence.path,
        sha256=evidence.sha256,
        leaf_id=verdict.leaf_id,
        target_dir=target_dir(leaf, evidence, fitted),
        band=band_for(fitted, leaf.kind, ctx),
        signal=verdict.signal,
        confidence=verdict.confidence,
        evidence_summary=verdict.summary,
        kind=leaf.kind,
        suggested_name=verdict.suggested_name,
        ranked=verdict.ranked,
        about=verdict.about,
    )
```

Remove the now-unused imports `re` (only if `DATE_IN_NAME` moved; it did not, so keep `re`) and `Mapping` (it is still used by `Context`). Let ruff tell you what is unused.

- [ ] **Step 4: Rewire `explain`, settings and `tree`.**
  - In `src/para_files/cli/explain_cmd.py`:
    - change the import to `from para_files.core.decide import Step, choose, decision_for`;
    - replace `EDIT_HINTS`, `_verdict_line` and the part of `explain_command` from `typer.echo("signals (first match wins):")` to the end with the code below.

```python
EDIT_HINTS = {
    "rules": "edit or unpin this rule in rules.yaml",
    "books": "the ISBN decided; pin a rule in rules.yaml to override it",
    "fallback": "the model chose; pin a rule, or improve the leaf's describe/keywords in tree.yaml",
    "hint": "a rule or issuer suggested this; pin the rule if it is always right, or fix it",
    "none": "add a rule (rules.yaml) or an issuer (issuers.yaml), or describe the leaf better",
}


def _step_line(step: Step) -> str:
    if step.verdict is not None:
        verdict = step.verdict
        return f"  {step.name:<12} {verdict.leaf_id} ({verdict.confidence:.2f}): {verdict.summary}"
    return f"  {step.name:<12} {step.note or 'no match'}"
```

```python
    typer.echo("steps:")
    verdict, steps = choose(evidence, ctx, ask_model=ask_model)
    for step in steps:
        typer.echo(_step_line(step))
    if verdict.about:
        typer.echo(f"  about: {verdict.about}")
    decision = decision_for(evidence, verdict, ctx)
    target = decision.target_dir or "stays in place"
    typer.echo(f"decision: {decision.band}, {decision.leaf_id or 'no leaf'} -> {target}")
    typer.echo(f"to change it: {EDIT_HINTS.get(verdict.signal, EDIT_HINTS['none'])}")
```

  - In `src/para_files/core/settings.py`, delete the `issuers_green` field. `CoreSettings` ignores unknown env names, so an old `.env` line does not break anything.
  - In `src/para_files/cli/tree_cmd.py` `_print_settings`, the "green at" line becomes:
    `f"  green at       model {settings.fallback_green} once calibrated; model below {settings.fallback_red} is red"`.
    In `_print_calibration`, the header becomes:
    `f"calibration (the model stays yellow until {settings.calibration_min} confirmed decisions per kind):"`.
  - In `.env.example`, delete the `# PARA_FILES_ISSUERS_GREEN=0.9` line.

- [ ] **Step 5: Run the tests and the gate.**
Run: `uv run pytest tests/test_core_decide.py tests/test_cli_explain.py tests/test_core_sort.py tests/test_cli_sort.py tests/test_core_settings.py -q -o addopts=""`, then the full gate.
Expected: PASS.

`grep -rn "issuers_green\|run_signals\|signal_verdicts\|SIGNALS" src tests` must print nothing.

- [ ] **Step 6: Docs and commit.**
  - **`docs/architecture.md`:** rewrite the cascade section and its Mermaid diagram (secret → ISBN book → pinned rule → model with hints → hint, always yellow → red) and the bands table. Remove the `PARA_FILES_ISSUERS_GREEN` sentence.
  - **`docs/configuration.md`:** remove the `PARA_FILES_ISSUERS_GREEN` row.
  - **`docs/cli/explain.md`:** describe the `steps:` lines (`isbn book`, `pinned rule`, `hint`, `model`) and the `about:` line.
  - **CHANGELOG `### Changed`:** "**Model first.** Every non-secret file is read by the model unless a verified ISBN or a pinned rule decides. Unpinned rules and issuers are hints in the prompt; with no key (or the model off) the first hint is shown as a yellow suggestion and never moves alone. **Breaking:** unpinned rules no longer move files with `--apply`; pin the rules you trust. `PARA_FILES_ISSUERS_GREEN` is gone."

```bash
git add src/para_files/core/decide.py src/para_files/cli/explain_cmd.py src/para_files/core/settings.py src/para_files/cli/tree_cmd.py .env.example tests/ docs/architecture.md docs/configuration.md docs/cli/explain.md CHANGELOG.md
git commit -F <msgfile>   # "feat(core): model-first cascade; pinned rules decide, the rest are hints"
```

Before committing, check `git status --short`: only the listed files may be staged.

---

### Task 6: Plan output grouped by folder; JSON `ranked`, `about`, `by_signal`; hint footer

**Files:**
- Modify: `src/para_files/cli/output.py`
- Modify: `docs/cli/sort.md`, `CHANGELOG.md`
- Test: `tests/test_cli_sort.py`

**Interfaces:**
- Consumes: `Decision.ranked`, `Decision.about` (Task 5).
- Produces: `para_files.cli.output.group_by_leaf(decisions: Sequence[Decision]) -> list[tuple[str, list[Decision]]]`, which holds yellow decisions with a leaf, biggest group first, then by leaf id, with files sorted by path. Task 7 uses it.

- [ ] **Step 1: Write the failing tests.** Append to `tests/test_cli_sort.py`:

```python
def test_plan_groups_yellow_files_by_folder_and_counts_hints(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    put(root, "0_Inbox/a_notes.md", "# a")
    put(root, "0_Inbox/b_notes.md", "# b")
    put(root, "0_Inbox/statement.txt", "AcmeCard statement")
    result = runner.invoke(app, ["sort"])
    assert result.exit_code == 0, result.output
    assert "  resources_it (2)" in result.output
    assert "  archives_10y_banques (1)" in result.output
    assert "3 files decided by hints only (model off or did not answer)" in result.output


def test_json_has_ranked_about_and_by_signal(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    put(root, "0_Inbox/a_notes.md", "AcmeCard # a")
    result = runner.invoke(app, ["sort", "--json"])
    data = json.loads(result.output)
    decision = data["decisions"][0]
    assert decision["ranked"] == [["resources_it", 1.0], ["archives_10y_banques", 0.8]]
    assert decision["about"] is None
    assert data["summary"]["by_signal"] == {"hint": 1}
```

(Add `import json` at the top of `tests/test_cli_sort.py` if it is missing.)

- [ ] **Step 2: Run them to see them fail.**
Run: `uv run pytest tests/test_cli_sort.py -q -o addopts="" -k "groups or by_signal"`
Expected: FAIL. There is no group heading and no `ranked` key.

- [ ] **Step 3: Implement.** In `src/para_files/cli/output.py`:

```python
def group_by_leaf(decisions: Sequence[Decision]) -> list[tuple[str, list[Decision]]]:
    """Yellow decisions with a leaf, by leaf: biggest group first, then by leaf id."""
    groups: dict[str, list[Decision]] = {}
    for decision in decisions:
        if decision.band == "yellow" and decision.leaf_id:
            groups.setdefault(decision.leaf_id, []).append(decision)
    ordered = [(leaf, sorted(group, key=lambda d: str(d.path))) for leaf, group in groups.items()]
    return sorted(ordered, key=lambda item: (-len(item[1]), item[0]))
```

In `decision_dict`, add the keys:

```python
        "ranked": [[leaf, round(p, 3)] for leaf, p in decision.ranked],
        "about": decision.about,
```

In `summary`, add:

```python
        "by_signal": dict(sorted(Counter(d.signal for d in decisions).items())),
```

In `_line`, append the about text when there is one:

```python
    about = f"  — {decision.about}" if decision.about else ""
    return (
        f"  {name}  ->  {decision.target_dir}{rename}  "
        f"[{decision.signal} {decision.confidence:.2f}]{about}"
    )
```

In `print_plan`, print the yellow band grouped, and add the footer before the totals line:

```python
def print_plan(decisions: Sequence[Decision], root: Path) -> None:
    """Band-grouped plan (yellow by folder); secrets get their own heading."""
    secrets = [d for d in decisions if d.signal == "secret"]
    for band, label in SECTIONS:
        shown = [d for d in decisions if d.band == band and d.signal != "secret"]
        if not shown:
            continue
        typer.echo(f"{band.upper()} ({len(shown)}): {label}")
        if band == "yellow":
            for leaf_id, group in group_by_leaf(shown):
                typer.echo(f"  {leaf_id} ({len(group)})")
                for decision in group:
                    typer.echo("  " + _line(decision, root))
        else:
            for decision in shown:
                typer.echo(_line(decision, root))
    if secrets:
        typer.echo(f"SECRETS ({len(secrets)}): never sent, never moved; keep them in a vault")
        for decision in secrets:
            typer.echo(f"  {relative(decision.path, root)}")
    hinted = sum(d.signal == "hint" for d in decisions)
    if hinted:
        typer.echo(f"{hinted} files decided by hints only (model off or did not answer)")
    counts = summary(decisions)
    typer.echo(
        f"{counts['files']} files: {counts['green']} green, {counts['yellow']} yellow, "
        f"{counts['red']} red ({counts['secrets']} secret)"
    )
```

Yellow decisions without a leaf cannot happen: a decision without a leaf is red.

- [ ] **Step 4: Run the tests and the gate.**
Run: `uv run pytest tests/test_cli_sort.py -q -o addopts=""`, then the full gate.
Expected: PASS. Fix existing assertions on exact plan lines in yellow: those lines now have two more spaces of indent under a group heading.

- [ ] **Step 5: Docs and commit.**
  - In `docs/cli/sort.md`, describe the yellow section grouped by folder, the hint footer, and the JSON keys `ranked`, `about` and `summary.by_signal`.
  - In the CHANGELOG under `### Changed`, add: "The plan groups yellow files by proposed folder and says how many were decided by hints only; JSON adds `ranked`, `about` and `summary.by_signal`."

```bash
git add src/para_files/cli/output.py tests/test_cli_sort.py docs/cli/sort.md CHANGELOG.md
git commit -F <msgfile>   # "feat(cli): plan grouped by folder; JSON ranked/about/by_signal"
```

---

### Task 7: Grouped review

**Files:**
- Modify: `src/para_files/cli/review.py`
- Modify: `docs/cli/sort.md` ("Review"), `CHANGELOG.md`
- Test: `tests/test_cli_sort.py`

**Interfaces:**
- Consumes: `group_by_leaf` (Task 6); `Decision.ranked` and `Decision.about` (Task 5); `stdin_is_tty` (Task 2).
- Produces: `review_ops(decisions, config, root, ask=_ask) -> list[Op]`, same signature as today, now asking group by group.

- [ ] **Step 1: Write the failing tests.** Append to `tests/test_cli_sort.py`:

```python
def test_review_accepts_a_whole_group(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    for name in ("a_notes.md", "b_notes.md", "c_notes.md"):
        put(root, f"0_Inbox/{name}", "# x")
    result = runner.invoke(app, ["sort", "--apply", "--review"], input="\n")
    assert result.exit_code == 0, result.output
    assert "resources_it -> 3_Resources/IT (3 files)" in result.output
    for name in ("a_notes.md", "b_notes.md", "c_notes.md"):
        assert (root / "3_Resources/IT" / name).exists()


def test_review_retargets_a_whole_group(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    put(root, "0_Inbox/a_notes.md", "# a")
    put(root, "0_Inbox/b_notes.md", "# b")
    result = runner.invoke(app, ["sort", "--apply", "--review"], input="archives_5y\n")
    assert result.exit_code == 0, result.output
    assert (root / "4_Archives/5y_factures/a_notes.md").exists()
    assert (root / "4_Archives/5y_factures/b_notes.md").exists()


def test_review_one_by_one_then_stop_keeps_what_was_confirmed(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    put(root, "0_Inbox/a_notes.md", "# a")
    b = put(root, "0_Inbox/b_notes.md", "# b")
    result = runner.invoke(app, ["sort", "--apply", "--review"], input="o\n\nq\n")
    assert result.exit_code == 0, result.output
    assert (root / "3_Resources/IT/a_notes.md").exists()
    assert b.exists()


def test_review_picks_a_ranked_alternative(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    put(root, "0_Inbox/acme_2026.md", "AcmeCard statement")
    result = runner.invoke(app, ["sort", "--apply", "--review"], input="2\n")
    assert result.exit_code == 0, result.output
    entries = read_run(tmp_path / "state", last_run_id(tmp_path / "state"))
    moves = [(e["leaf"], e["proposed_leaf"]) for e in entries if e["op"] == "move"]
    assert moves == [("archives_10y_banques", "resources_it")]
```

Update the existing review tests to the grouped flow. Both notes files land in one group, so add `o` to go one by one:

| Test | Input before | Input after | Expectations |
|---|---|---|---|
| `test_review_accept_and_correct` | `"\narchives_5y\n"` | `"o\n\narchives_5y\n"` | unchanged |
| `test_review_end_of_input_keeps_what_was_confirmed` | `"\n"` | `"o\n\n"` | unchanged |
| `test_review_skip_unknown_and_stop` | `"nope\ns\nq\n"` | `"o\nnope\ns\nq\n"` | unchanged |

- [ ] **Step 2: Run them to see them fail.**
Run: `uv run pytest tests/test_cli_sort.py -q -o addopts="" -k review`
Expected: FAIL. There is no group header, and `2` is read as an unknown leaf.

- [ ] **Step 3: Implement.** Replace `src/para_files/cli/review.py` with:

```python
"""Interactive confirmation of yellow decisions (`sort --apply --review`), folder by folder.

Files proposed for the same leaf are reviewed together: accept the group, skip it, send it
elsewhere, or go through it one by one. Every answer is an owner decision (spec §4.5).
"""

from __future__ import annotations

import contextlib
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

import typer

from para_files.cli.common import relative
from para_files.cli.output import group_by_leaf
from para_files.core.apply import Op
from para_files.core.decide import Decision
from para_files.core.tree import TreeConfig


Ask = Callable[[str], str]
GROUP_PROMPT = "  [Enter] accept all, o one by one, s skip, q stop, ? list leaves, or a leaf id: "
FILE_PROMPT = "  [Enter] accept, 2/3 alternative, s skip, q stop, ? list leaves, or a leaf id: "


class Stop(Exception):  # noqa: N818 - a signal, not an error
    """The owner typed q or input ended: keep what was confirmed, ask nothing more."""


def _ask(prompt: str) -> str:
    return str(typer.prompt(prompt, default="", show_default=False))


def stdin_is_tty() -> bool:
    """True when a person can answer the questions: stdin is a terminal."""
    return sys.stdin.isatty()


def resolve_leaf(text: str, config: TreeConfig) -> str | None:
    """Exact leaf id, or the only leaf id starting with text."""
    leaves = list(config.tree.leaves)
    if text in leaves:
        return text
    found = [leaf_id for leaf_id in leaves if leaf_id.startswith(text)]
    return found[0] if len(found) == 1 else None


def _list_leaves(config: TreeConfig) -> None:
    for leaf_id, leaf in sorted(config.tree.leaves.items(), key=lambda item: item[1].path):
        typer.echo(f"    {leaf_id:<32} {leaf.path}")


def _read(ask: Ask, prompt: str) -> str:
    try:
        return ask(prompt).strip()
    except typer.Abort as exc:
        raise Stop from exc


def _typed_leaf(answer: str, config: TreeConfig) -> str | None:
    leaf_id = resolve_leaf(answer, config)
    if leaf_id is None:
        typer.echo(f"  unknown or ambiguous leaf: {answer!r}")
    return leaf_id


def _alternatives(decision: Decision) -> str:
    others = [f"{n}) {leaf} {p:.2f}" for n, (leaf, p) in enumerate(decision.ranked, 1) if n > 1]
    return f"  alternatives: {', '.join(others)}" if others else ""


def _one(decision: Decision, config: TreeConfig, root: Path, ask: Ask, position: str) -> Op | None:
    """Ask about one file: an Op, or None when skipped. Raises Stop on q or end of input."""
    typer.echo(f"{position} {relative(decision.path, root)}")
    typer.echo(
        f"  proposed: {decision.leaf_id} -> {decision.target_dir} "
        f"({decision.signal} {decision.confidence:.2f}; {decision.evidence_summary})"
    )
    if decision.about:
        typer.echo(f"  about: {decision.about}")
    if alternatives := _alternatives(decision):
        typer.echo(alternatives)
    while True:
        answer = _read(ask, FILE_PROMPT)
        if answer in {"", "y"}:
            return Op(decision, str(decision.leaf_id), "owner")
        if answer == "s":
            return None
        if answer == "q":
            raise Stop
        if answer == "?":
            _list_leaves(config)
            continue
        if answer.isdigit() and 1 <= int(answer) <= len(decision.ranked):
            return Op(decision, decision.ranked[int(answer) - 1][0], "owner")
        if (leaf_id := _typed_leaf(answer, config)) is not None:
            return Op(decision, leaf_id, "owner")


def _show(decision: Decision, root: Path) -> None:
    about = f" — {decision.about}" if decision.about else ""
    typer.echo(
        f"    {relative(decision.path, root)}  "
        f"[{decision.signal} {decision.confidence:.2f}]{about}"
    )
    if alternatives := _alternatives(decision):
        typer.echo(f"  {alternatives}")


def _group(
    leaf_id: str,
    group: list[Decision],
    context: tuple[TreeConfig, Path, Ask],
    position: str,
    ops: list[Op],
) -> None:
    """Ask about one group; confirmed ops are appended to ops as soon as they are given."""
    config, root, ask = context
    if len(group) == 1:
        if (op := _one(group[0], config, root, ask, position)) is not None:
            ops.append(op)
        return
    typer.echo(f"{position} {leaf_id} -> {config.tree.leaves[leaf_id].path} ({len(group)} files)")
    for decision in group:
        _show(decision, root)
    while True:
        answer = _read(ask, GROUP_PROMPT)
        if answer in {"", "y"}:
            ops.extend(Op(decision, leaf_id, "owner") for decision in group)
            return
        if answer == "s":
            return
        if answer == "q":
            raise Stop
        if answer == "?":
            _list_leaves(config)
            continue
        if answer == "o":
            for index, decision in enumerate(group, start=1):
                op = _one(decision, config, root, ask, f"  [{index}/{len(group)}]")
                if op is not None:
                    ops.append(op)
            return
        if (target := _typed_leaf(answer, config)) is not None:
            ops.extend(Op(decision, target, "owner") for decision in group)
            return


def review_ops(
    decisions: Sequence[Decision], config: TreeConfig, root: Path, ask: Ask = _ask
) -> list[Op]:
    """Ask about each folder group of yellow decisions; return the confirmed operations."""
    groups = group_by_leaf(decisions)
    ops: list[Op] = []
    with contextlib.suppress(Stop):
        for index, (leaf_id, group) in enumerate(groups, start=1):
            _group(leaf_id, group, (config, root, ask), f"[{index}/{len(groups)}]", ops)
    return ops
```

`cli/output.py` must not import `cli/review.py`; it does not, so there is no import cycle.

- [ ] **Step 4: Run the tests and the gate.**
Run: `uv run pytest tests/test_cli_sort.py -q -o addopts=""`, then the full gate.
Expected: PASS.

- [ ] **Step 5: Docs and commit.**
  - Rewrite `docs/cli/sort.md` "Review":
    - **Groups:** Enter accepts all, `o` goes one by one, `s` skips, `q` stops and keeps what you confirmed, `?` lists the leaves, a leaf id sends the whole group there.
    - **One by one:** Enter, `2`/`3` for an alternative, `s`, `q`, `?`, a leaf id.
    - **Note:** accepting a group counts every file as a confirmed decision.
  - In the CHANGELOG under `### Changed`, add: "`--review` goes folder by folder: accept, skip or retarget a whole group, or go through it one by one; `2`/`3` pick the model's alternatives."

```bash
git add src/para_files/cli/review.py tests/test_cli_sort.py docs/cli/sort.md CHANGELOG.md
git commit -F <msgfile>   # "feat(cli): review yellow files folder by folder"
```

---

### Task 8: Retargets keep `{year}`, `{month}`, `{thema}` and a fitting `{issuer}`

**Files:**
- Modify: `src/para_files/core/decide.py` (`placeholders`, `fill_subkey`, `target_dir`, `Decision.fill`, `Decision.issuer`, `decision_for`)
- Modify: `src/para_files/core/apply.py` (`_Applier.target`)
- Modify: `CHANGELOG.md`
- Test: `tests/test_core_decide.py`, `tests/test_cli_sort.py`

**Interfaces:**
- Produces:
  - `placeholders(evidence, verdict) -> tuple[tuple[str, str | None], ...]` (`{year}`, `{month}`, `{thema}`);
  - `fill_subkey(leaf: Leaf, fill: Sequence[tuple[str, str | None]]) -> str`;
  - `Decision.fill` (default `()`);
  - `Decision.issuer: str | None` (the matched issuer, before fitting).

- [ ] **Step 1: Write the failing tests.** Append to `tests/test_cli_sort.py`:

```python
def test_alternative_keeps_issuer_and_year(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    put(root, "0_Inbox/acme_2026.md", "AcmeCard statement")
    result = runner.invoke(app, ["sort", "--apply", "--review"], input="2\n")
    assert result.exit_code == 0, result.output
    assert (root / "4_Archives/10y_banques/acmecard/2026/acme_2026.md").exists()


def test_retarget_keeps_the_year(tmp_path, monkeypatch):
    root = setup_cli(tmp_path, monkeypatch)
    put(root, "0_Inbox/notes_2025.md", "# n")
    result = runner.invoke(app, ["sort", "--apply", "--review"], input="archives_5y\n")
    assert result.exit_code == 0, result.output
    assert (root / "4_Archives/5y_factures/2025/notes_2025.md").exists()
```

Append to `tests/test_core_decide.py`:

```python
def test_fill_subkey_needs_every_placeholder():
    leaf = make_config().tree.leaves["archives_10y_banques"]
    assert decide.fill_subkey(leaf, (("{year}", "2026"), ("{issuer}", "acmecard"))) == (
        "4_Archives/10y_banques/acmecard/2026"
    )
    assert decide.fill_subkey(leaf, (("{year}", "2026"), ("{issuer}", None))) == (
        "4_Archives/10y_banques"
    )
```

- [ ] **Step 2: Run them to see them fail.**
Run: `uv run pytest tests/test_cli_sort.py tests/test_core_decide.py -q -o addopts="" -k "keeps or fill_subkey"`
Expected: FAIL. `fill_subkey` does not exist, and retargeted files land in the leaf root.

- [ ] **Step 3: Implement.** In `src/para_files/core/decide.py`, replace `target_dir` with:

```python
def placeholders(evidence: Evidence, verdict: Verdict) -> tuple[tuple[str, str | None], ...]:
    """The subkey values this file can give, whatever the leaf: date and Thema folders."""
    year, month = file_date(evidence)
    return (("{year}", year), ("{month}", month), ("{thema}", verdict.thema))


def fill_subkey(leaf: Leaf, fill: Sequence[tuple[str, str | None]]) -> str:
    """Leaf path plus its subkey filled from fill; any unfillable placeholder -> the leaf root."""
    if not leaf.subkey:
        return leaf.path
    values = dict(fill)
    parts = [values.get(placeholder) for placeholder in leaf.subkey.split("/")]
    filled = [part for part in parts if part]
    if len(filled) != len(parts):
        return leaf.path
    return "/".join([leaf.path, *filled])


def target_dir(leaf: Leaf, evidence: Evidence, verdict: Verdict) -> str:
    """Leaf path plus its filled subkey (verdict.issuer already fitted to the leaf)."""
    return fill_subkey(leaf, (*placeholders(evidence, verdict), ("{issuer}", verdict.issuer)))
```

Add these two fields to `Decision`, after `about`:

```python
    issuer: str | None = None
    fill: tuple[tuple[str, str | None], ...] = ()
```

In the leaf branch of `decision_for`, add `issuer=verdict.issuer, fill=placeholders(evidence, verdict),` to the `Decision(...)` call.

In `src/para_files/core/apply.py`, import from `para_files.core.decide`: `Decision, fill_subkey, issuer_for`. Change `target`:

```python
    def target(self, op: Op) -> Path:
        decision = op.decision
        if op.leaf_id == decision.leaf_id and decision.target_dir:
            return self.root / decision.target_dir
        leaf = self.config.tree.leaves[op.leaf_id]
        issuer = issuer_for(op.leaf_id, decision.issuer, self.config)
        return self.root / fill_subkey(leaf, (*decision.fill, ("{issuer}", issuer)))
```

- [ ] **Step 4: Run the tests and the gate.**
Run: `uv run pytest tests/test_cli_sort.py tests/test_core_decide.py tests/test_core_apply.py -q -o addopts=""`, then the full gate.
Expected: PASS.

- [ ] **Step 5: Commit.** In the CHANGELOG under `### Fixed`, add: "A file sent to another folder in `--review` keeps its year (and issuer, when it fits) subfolder instead of landing in the folder root."

```bash
git add src/para_files/core/decide.py src/para_files/core/apply.py tests/test_cli_sort.py tests/test_core_decide.py CHANGELOG.md
git commit -F <msgfile>   # "fix(apply): retargeted files keep their year/issuer subfolder"
```

---

### Task 9: End-to-end test with a fake model

**Files:**
- Test: `tests/test_cli_model_first.py` (new)

**Interfaces:**
- Consumes: everything above. `para_files.core.sort.make_fallback` is patched; it is called as `make_fallback(settings)`, and Task 10 adds keyword arguments, so the fake takes `**_kw`.

- [ ] **Step 1: Write the test.**

```python
"""Model first, end to end: pinned rules skip the model, secrets never reach it, hints and
OCR text do, review answers are journaled, undo restores the tree, the cache saves calls."""

from __future__ import annotations

import json
from types import SimpleNamespace

from typer.testing import CliRunner

from para_files.cli import app
from para_files.core import sort as sort_module
from para_files.core.fallback import OpenRouterFallback
from para_files.core.journal import last_run_id, read_run
from para_files.utils.ocr import OCRResult
from tests.core_helpers import setup_cli


runner = CliRunner()


def put(root, rel, text):
    path = root / rel
    path.write_text(text)
    return path


def fake_model(calls):
    def complete(**kwargs):
        user = kwargs["messages"][1]["content"]
        calls.append(user)
        leaf = "archives_10y_banques" if "AcmeCard" in user else "resources_docs"
        content = json.dumps(
            {
                "about": "test document",
                "choices": [
                    {"leaf": leaf, "confidence": 0.8},
                    {"leaf": "archives_5y_factures", "confidence": 0.1},
                ],
            }
        )
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )

    return complete


def test_model_first_end_to_end(tmp_path, monkeypatch, snapshot):
    calls: list[str] = []
    root = setup_cli(tmp_path, monkeypatch)
    monkeypatch.setattr(
        sort_module,
        "make_fallback",
        lambda _settings, **_kw: OpenRouterFallback("key", ["m1"], complete=fake_model(calls)),
    )
    monkeypatch.setattr(
        "para_files.utils.ocr.extract_text",
        lambda *_a, **_k: OCRResult(
            text="AcmeCard invoice 2026 scanned", confidence=0.9, word_count=4
        ),
    )
    put(root, "0_Inbox/Payslip_2026-01.txt", "salary")
    put(root, "0_Inbox/passwords.txt", "vpn\npassword: hunter22\n")
    put(root, "0_Inbox/acme_2026.md", "AcmeCard statement")
    (root / "0_Inbox/scan.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    before = snapshot(root)

    preview = runner.invoke(app, ["sort", "--json"])
    assert preview.exit_code == 0, preview.output
    plan = {d["path"]: d for d in json.loads(preview.output)["decisions"]}
    assert plan["0_Inbox/Payslip_2026-01.txt"]["signal"] == "rules"
    assert plan["0_Inbox/passwords.txt"]["signal"] == "secret"
    acme = plan["0_Inbox/acme_2026.md"]
    assert (acme["signal"], acme["band"]) == ("fallback", "yellow")
    assert acme["target"] == "4_Archives/10y_banques/acmecard/2026"
    assert acme["about"] == "test document"
    sent = "\n".join(calls)
    assert "Payslip_2026-01" not in sent
    assert "hunter22" not in sent and "passwords.txt" not in sent
    assert "rule 'it_notes'" in sent and "issuer 'acmecard'" in sent
    assert "AcmeCard invoice 2026 scanned" in sent
    asked = len(calls)

    again = runner.invoke(app, ["sort", "--json"])
    assert again.exit_code == 0, again.output
    assert len(calls) == asked

    applied = runner.invoke(app, ["sort", "--apply", "--review"], input="\n\n")
    assert applied.exit_code == 0, applied.output
    assert (root / "4_Archives/10y_travail/2026/Payslip_2026-01.txt").exists()
    assert (root / "4_Archives/10y_banques/acmecard/2026/acme_2026.md").exists()
    assert (root / "0_Inbox/passwords.txt").exists()
    entries = read_run(tmp_path / "state", last_run_id(tmp_path / "state"))
    owner = [e for e in entries if e["op"] == "move" and e["decided_by"] == "owner"]
    assert {e["leaf"] for e in owner} == {"archives_10y_banques"}

    undone = runner.invoke(app, ["undo"])
    assert undone.exit_code == 0, undone.output
    assert snapshot(root) == before
```

The `.png` goes to the model with its OCR text; its group answer is the second Enter. The model returns `archives_10y_banques` for it because the OCR text contains "AcmeCard".

- [ ] **Step 2: Run it.**
Run: `uv run pytest tests/test_cli_model_first.py -q -o addopts=""`
Expected: PASS. If it fails, the failure points to a real gap in Tasks 1–8: fix it in the owning module, not in the test, and say so in the report.

- [ ] **Step 3: Gate and commit.**

```bash
git add tests/test_cli_model_first.py
git commit -F <msgfile>   # "test: model-first end to end (pins, secrets, hints, OCR, review, undo, cache)"
```

---

### Task 10: Few-shot examples from the owner's past decisions

**Files:**
- Modify: `src/para_files/core/journal.py` (`Example`, `owner_examples`)
- Modify: `src/para_files/core/fallback.py` (`pick_examples`, `messages`, `OpenRouterFallback`, `make_fallback`, `PROMPT_VERSION = "3"`)
- Modify: `src/para_files/core/sort.py` (`build_context`)
- Modify: `docs/architecture.md`, `CHANGELOG.md`
- Test: `tests/test_core_journal.py`, `tests/test_core_fallback.py`

**Interfaces:**
- Produces:
  - `Example(name: str, leaf_id: str, proposed: str | None)`;
  - `owner_examples(state_dir: Path, tree: Tree) -> list[Example]`, newest first, one per file (sha256);
  - `pick_examples(examples, name, menu, limit=MAX_EXAMPLES) -> list[Example]`;
  - `messages(menu, evidence, hints=(), examples=())`;
  - `OpenRouterFallback(..., examples: Sequence[Example] = ())`;
  - `make_fallback(settings, *, complete=litellm_complete, examples=())`.

- [ ] **Step 1: Write the failing tests.** Append to `tests/test_core_journal.py`:

```python
def test_owner_examples_newest_first_one_per_file(tmp_path):
    from para_files.core.journal import Journal, owner_examples
    from tests.core_helpers import make_config

    state = tmp_path / "state"

    def run(run_id, entries):
        with Journal(state, run_id) as journal:
            for entry in entries:
                journal.append(entry)

    run("20260101-000000", [
        {"op": "move", "src": "/r/0_Inbox/a.pdf", "dst": "/r/x/a.pdf", "sha256": "a",
         "leaf": "archives_5y_factures", "proposed_leaf": "resources_docs",
         "decided_by": "owner"},
        {"op": "move", "src": "/r/0_Inbox/auto.pdf", "dst": "/r/x/auto.pdf", "sha256": "z",
         "leaf": "archives_5y_factures", "proposed_leaf": "archives_5y_factures",
         "decided_by": "auto"},
    ])
    run("20260102-000000", [
        {"op": "move", "src": "/r/0_Inbox/b.pdf", "dst": "/r/y/b.pdf", "sha256": "b",
         "leaf": "archives_10y_banques", "proposed_leaf": "archives_10y_banques",
         "decided_by": "owner"},
        {"op": "move", "src": "/r/0_Inbox/a.pdf", "dst": "/r/z/a.pdf", "sha256": "a",
         "leaf": "archives_10y_banques", "proposed_leaf": "archives_5y_factures",
         "decided_by": "owner"},
    ])
    examples = owner_examples(state, make_config().tree)
    assert [(e.name, e.leaf_id, e.proposed) for e in examples] == [
        ("a.pdf", "archives_10y_banques", "archives_5y_factures"),
        ("b.pdf", "archives_10y_banques", "archives_10y_banques"),
    ]
```

(Use the `Journal` API exactly as the existing tests in this file do. If `Journal.append` is named differently, follow those tests.)

Append to `tests/test_core_fallback.py`:

```python
def test_examples_are_picked_by_shared_words_and_never_secret(monkeypatch):
    from para_files.core.fallback import pick_examples
    from para_files.core.journal import Example

    monkeypatch.setattr(
        fallback, "secret_reason", lambda name, text="": "name" if "SECRET" in name else None
    )
    menu = leaf_menu(make_config().tree)
    examples = [
        Example("holiday_photo.jpg", "archives_photos", None),
        Example("acmecard_statement_2025.pdf", "archives_10y_banques", "resources_docs"),
        Example("SECRET_acmecard.pdf", "archives_10y_banques", None),
        Example("acmecard_gone.pdf", "no_such_leaf", None),
    ]
    picked = pick_examples(examples, "acmecard_statement_2026.pdf", menu, limit=2)
    assert [e.name for e in picked] == ["acmecard_statement_2025.pdf", "holiday_photo.jpg"]
    user = messages(menu, ev(name="acmecard_statement_2026.pdf"), (), picked)[1]["content"]
    assert '"acmecard_statement_2025.pdf" -> archives_10y_banques (tool had proposed resources_docs)' in user
    assert "SECRET" not in user
```

- [ ] **Step 2: Run them to see them fail.**
Run: `uv run pytest tests/test_core_journal.py tests/test_core_fallback.py -q -o addopts="" -k "examples"`
Expected: FAIL with `ImportError: cannot import name 'owner_examples'`.

- [ ] **Step 3: Implement `journal.py`.** Add `from dataclasses import dataclass` to the imports, then:

```python
@dataclass(frozen=True)
class Example:
    """One owner decision: the file name, the leaf it went to, and what the tool proposed."""

    name: str
    leaf_id: str
    proposed: str | None


def owner_examples(state_dir: Path, tree: Tree) -> list[Example]:
    """Owner-decided moves and confirmations of runs not undone; newest first, one per file."""
    found: dict[str, Example] = {}
    for run_id in run_ids(state_dir):
        if is_undone(state_dir, run_id):
            continue
        for entry in read_run(state_dir, run_id):
            leaf_id = str(entry.get("leaf"))
            if (
                entry.get("op") not in {"move", "confirm"}
                or entry.get("decided_by") != "owner"
                or leaf_id not in tree.leaves
            ):
                continue
            key = str(entry.get("sha256") or entry.get("src"))
            proposed = entry.get("proposed_leaf")
            found.pop(key, None)
            found[key] = Example(
                Path(str(entry.get("src"))).name, leaf_id, str(proposed) if proposed else None
            )
    return list(reversed(found.values()))
```

`run_ids` returns runs oldest first, so re-inserting a key moves it to the end and the newest decision wins. Check this in `run_ids`: if it returns newest first, iterate `reversed(run_ids(state_dir))` instead.

- [ ] **Step 4: Implement `fallback.py`.**
  - Set `PROMPT_VERSION = "3"`.
  - Add `from para_files.core.journal import Example`.
  - Add these constants: `MAX_EXAMPLES = 10` and `WORD = re.compile(r"[^\W\d_]{3,}")`.
  - Add these functions:

```python
def _words(name: str) -> set[str]:
    return {word.casefold() for word in WORD.findall(Path(name).stem)}


def pick_examples(
    examples: Sequence[Example], name: str, menu: dict[str, str], limit: int = MAX_EXAMPLES
) -> list[Example]:
    """Past owner decisions most like this file (shared name words, then recency); none secret."""
    words = _words(name)
    usable = [
        (index, example)
        for index, example in enumerate(examples)
        if example.leaf_id in menu and secret_reason(example.name) is None
    ]
    usable.sort(key=lambda item: (-len(words & _words(item[1].name)), item[0]))
    return [example for _, example in usable[:limit]]


def _example_line(example: Example) -> str:
    corrected = example.proposed and example.proposed != example.leaf_id
    note = f" (tool had proposed {example.proposed})" if corrected else ""
    return f'- "{example.name}" -> {example.leaf_id}{note}'
```

  - Change `messages` so the examples come after the folders and before the file:

```python
def messages(
    menu: dict[str, str],
    evidence: Evidence,
    hints: Sequence[Hint] = (),
    examples: Sequence[Example] = (),
) -> list[dict[str, str]]:
    """System prompt, the folder list (stable, so providers can cache it), the owner's past
    decisions for similar files, then the file."""
    folders = "\n".join(f"- {leaf_id}: {describe}" for leaf_id, describe in menu.items())
    user = f"Folders:\n{folders}"
    if examples:
        shown = "\n".join(_example_line(example) for example in examples)
        user += f"\n\nPast decisions by the owner for similar files:\n{shown}"
    user += f"\n\nFile:\n{evidence_text(evidence, visible_hints(hints, menu))}"
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
```

  - In `OpenRouterFallback.__init__`, add the keyword `examples: Sequence[Example] = ()` and store it in `self._examples = tuple(examples)`.
  - In `_ask`, pass `messages(menu, evidence, hints, pick_examples(self._examples, evidence.name, menu))`.
  - `make_fallback` gets `examples: Sequence[Example] = ()` and passes `examples=examples` to `OpenRouterFallback`.
  - Add `examples` to the `SYSTEM` text: after "follow a hint only when the content agrees.", insert "Past decisions show where the owner filed similar files; they are reliable."

  `core/journal.py` must not import `core/fallback.py`; it does not, so there is no cycle.

- [ ] **Step 5: Wire it in `core/sort.py` `build_context`.**

```python
    directory = config_directory or config_dir_path()
    config = load_tree_config(directory)
    examples = owner_examples(settings.state_dir, config.tree)
    return Context(
        config=config,
        settings=settings,
        cache=Cache(settings.cache_path),
        fingerprint=config_fingerprint(
            directory,
            settings.fallback_model,
            settings.fallback_backup_model,
            PROMPT_VERSION,
            str(settings.preview_chars),
        ),
        confirmed=confirmed_counts(settings.state_dir, config.tree),
        fallback=make_fallback(settings, examples=examples),
    )
```

Import `owner_examples` from `para_files.core.journal`.

- [ ] **Step 6: Run the tests and the gate.**
Run: `uv run pytest tests/test_core_journal.py tests/test_core_fallback.py tests/test_cli_model_first.py -q -o addopts=""`, then the full gate.
Expected: PASS.

- [ ] **Step 7: Docs and commit.**
  - In `docs/architecture.md`, add a short "Learning from your decisions" section: up to 10 past owner decisions with similar names (names and folders only, never content) go into the prompt. They are not part of the cache key, so cached verdicts are reused until the config or the prompt changes.
  - In the CHANGELOG under `### Added`, add: "The model sees up to 10 of your past decisions for similar file names (names only), so your corrections teach it."

```bash
git add src/para_files/core/journal.py src/para_files/core/fallback.py src/para_files/core/sort.py tests/test_core_journal.py tests/test_core_fallback.py docs/architecture.md CHANGELOG.md
git commit -F <msgfile>   # "feat(model): learn from the owner's past decisions (few-shot examples)"
```

---

### Task 11: Spec, ADR-014 and the docs sweep

**Files:**
- Create: `docs/adr/ADR-014-model-first.md`
- Modify: `docs/adr/README.md`, `docs/superpowers/specs/2026-10-10-para-files-redesign-design.md`, `README.md`, `CLAUDE.md` (Architecture section), `docs/getting-started.md`, `docs/troubleshooting.md`, `CHANGELOG.md`

- [ ] **Step 1: Write ADR-014.**

```markdown
# ADR-014: Model First; Pinned Rules Decide, Other Rules Are Hints

**Date**: 2026-10-11
**Status**: Accepted
**Deciders**: Project owner
**Amends**: [ADR-013](ADR-013-redesign-records-first.md)

---

## Context

The first real inbox run (153 files) showed that filename rules dominated: 111 files were decided by a filename glob at confidence 1.0, the model saw only 14 leftovers, and 85 of 122 suggestions went to a catch-all folder. A rule such as `*[Ii][Ss][Ee]*` matched the letters "ise" inside a card issuer's name and filed a card invoice as vendor documentation. An evaluation of the 320 rules (5,313 globs) against the existing tree found 67 reliable rules (specific banks, statement types, publishers, photos) and 23 below 50% agreement (topic words and short fragments).

## Decision

1. The model reads every non-secret file first: name, type, metadata, text (including OCR), with rule, book-heuristic and issuer matches as hints.
2. Only a verified ISBN book or a rule marked `pin: true` (or `pin: exif` with an EXIF date) decides without the model.
3. With no key or no answer, the first hint is a yellow suggestion; hints never move a file alone.
4. Review goes folder by folder; the owner's decisions become examples in the prompt.

## Rationale

Content tells an invoice from a datasheet; a filename often does not. Rules stay where they are reliable (they are cheap and exact), and become context everywhere else. Safety is unchanged: secrets are never sent, the model stays yellow until a kind has 100 confirmed decisions, knowledge is never green, every move is journaled and undoable.

## Consequences

- About $5 per 1000 files sent to the model; the cache makes a preview followed by an apply cost one call per file.
- Unpinned rules no longer move files with `--apply` (breaking): the owner pins the rules they trust.
- `PARA_FILES_ISSUERS_GREEN` is removed.
```

Add an index row to `docs/adr/README.md`:
`| [ADR-014](ADR-014-model-first.md) | Model First; Pinned Rules Decide, Other Rules Are Hints | Accepted |`
In the ADR-013 row, change the status to `Accepted (amended by ADR-014)`.

- [ ] **Step 2: Amend the spec.**
  - In §4.2, replace the description of the cascade order with the new order and bands (copy the "Bands" bullet from this plan's Global Constraints).
  - Add a §8 row:
    `| Model first (2026-10-11) | The model reads every non-secret file (text incl. OCR, metadata, type) with rule/issuer matches as hints; only verified ISBN books and pinned rules (pin: true / pin: exif) decide alone; hints never green; grouped review; past owner decisions as examples; owner accepted sending ~2000 chars per file to OpenRouter with ZDR (ADR-014) |`

- [ ] **Step 3: Sweep the docs.**
  - **`README.md`:** "What it does" says the model reads each document and suggests a folder; trusted rules (pinned) and ISBN books file on their own.
  - **`CLAUDE.md`:** in "Architecture → Classification Cascade (core)", replace the 5-item list and the bands paragraph with the new order and bands.
  - **`docs/getting-started.md`:** the minimal `rules.yaml` example pins its rule (`pin: true`). Mention that without an OpenRouter key every unpinned match is only a suggestion.
  - **`docs/troubleshooting.md`:**
    - "Nothing goes green" now covers unpinned rules (they are hints) and calibration.
    - Add "The model was not asked" (no key, model off, breaker open: the footer in the plan says so).

Then run `grep -rn "first match wins\|issuers_green\|ISSUERS_GREEN\|signals (first" README.md CLAUDE.md docs/*.md docs/cli`. It must print nothing.

- [ ] **Step 4: Gate and commit.**

```bash
git add docs/adr docs/superpowers/specs/2026-10-10-para-files-redesign-design.md README.md CLAUDE.md docs/getting-started.md docs/troubleshooting.md CHANGELOG.md
git commit -F <msgfile>   # "docs: ADR-014 model first; spec, README, CLAUDE.md, guides"
```

---

## After the tasks (owner steps; nothing here moves files)

1. **Rules triage** (a one-off script in the session scratchpad, not product code):
   - It reads `rules_eval.csv`, re-matches journal owner decisions against `rules.yaml`, and counts inbox hits per rule.
   - It writes `rules_triage.md` with these sections:
     - **PIN** (about 33 rules: specific records, videos, isos/programmes; photos as `pin: exif`);
     - **PIN AFTER GLOB CLEANUP** (a bank's notices, a second bank, vendor documentation…);
     - **NEAR** (90–95%; the owner decides);
     - **FIX** (bad short globs: `*ise*`, `*ale*`, `*plu*`, the topic-word ebooks globs);
     - **UNUSED** (45 dead rules).
   - The owner approves the list. Then edit `~/.config/para-files/rules.yaml` (classification-config skill) and run `para-files tree --validate`.
   - Do this **before** step 2: any YAML edit changes the cache key.
2. **Real comparison, read-only, only with the owner's go-ahead** (it sends file text to the model):
   - Run `uv run para-files sort --json -w 8 > <scratch>/inbox-model-first.json` (expect about 160–250 model calls, about $1–1.5, 1–2 minutes).
   - Compare it with the v2.0 plan the owner already has from their run:
     - counts by band and signal;
     - the catch-all `3_Resources/docs` share (v2.0: 85 of 122 yellow);
     - red files;
     - the list of files whose folder changed.
   - Then run `PARA_FILES_FALLBACK_ENABLED=false uv run para-files sort --json`: only pinned and ISBN files may be green.
3. **The owner reviews in a real terminal:** `uv run para-files sort --apply --review`.
4. **Update the local skills** `classification-config` and `para-files-inbox` (`.claude/skills/`, untracked) to describe pins, hints and grouped review.

## Left out (YAGNI)

- OCR language hints for Vision.
- Renaming the `fallback_*` settings.
- Confidence boosts when a hint agrees.
- Listing every matching rule as a hint.
- A rules-report command.
- Storing hints or `about` in the journal.
- Raw single-key input.
- A cap on model calls.
- A progress bar.
