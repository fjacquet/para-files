# Stage 0 — Safety Hotfixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Execution method (owner's choice):** subagent-driven, with implementer and reviewer subagents running on model `haiku`.

**Goal:** Make the current para-files code safe to run: no renames during classification, no overwrites, no path escapes, no swallowed Ctrl+C, no deletion of different books that share an ISBN.

**Architecture:** Five surgical fixes to existing modules, no new modules. Each fix gets a failing test first, then the minimal code change, then a CHANGELOG bullet. The redesign (canonical tree, new pipeline, journal/undo) is *not* part of this plan.

**Tech Stack:** Python 3.12, uv, pytest, ruff, mypy (strict), Typer, loguru, pydantic / pydantic-settings.

**Spec:** `docs/superpowers/specs/2026-10-10-para-files-redesign-design.md` — section 5, "Stage 0 — Safety hotfixes (current code)".

## Global Constraints

- Python 3.12; every module keeps `from __future__ import annotations`.
- Ruff line length 100; mypy strict on `src/`.
- Logging uses loguru `{}` placeholders, never `%s`.
- Surgical changes only: touch nothing a task does not name. Do not reformat or "improve" adjacent code.
- Tests must not reach the network or a live Ollama server.
- Every task adds one bullet to the `### Fixed (Stage 0 safety)` block under `## [Unreleased]` in `CHANGELOG.md` (Task 1 creates the block).
- Spec Stage 0 list (verbatim):
  1. `ocr_rename.enabled` defaults to `False`.
  2. Mover: `para_root` containment check; refuse to overwrite; moves run sequentially.
  3. Pipeline: catch `Exception` at the signal boundary (litellm errors no longer abort; breaker records failures); `KeyboardInterrupt` re-raises.
  4. LLM output: reject paths containing `..` or absolute paths.
  5. `bookstore`: never delete a same-ISBN file whose content differs.
- Placement note for item 2: the `para_root` containment check lives in `ClassificationPipeline.get_target_path` (the only place that knows `para_root` and turns a category into a directory), and `FileMover` refuses any destination *filename* that is not a plain name. Together they guarantee the final path stays inside `para_root` without threading `para_root` through every CLI helper and test mock.
- Work happens on branch `fix/stage0-safety`, created from `docs/redesign-spec`. No push, no PR, no release in this plan.

## Review Focus

Inputs the spec implies but that are easy to miss, most likely first. Each has a test in the task named in brackets.

1. Two *different* files with the *same name* moved in one parallel `move` run → both end up in the destination, neither is lost. [Task 5]
2. An LLM category with `..` hidden behind an allowed prefix (`3_Resources/documentation/../../../etc`) → rejected. [Task 3]
3. Ctrl+C while `move` is classifying a file → the run aborts and the file stays where it was (today it is sent to `6_unclassified`). [Task 2]
4. Two books with the same ISBN but different content (two editions or two scans) → both kept by `bookstore`. [Task 6]
5. An empty category (the `generic_folders` rule has no destination) → refused, instead of dropping the file loose into the PARA root. [Task 4]

## File Structure

| File | Change | Task |
|---|---|---|
| `src/para_files/config.py` | `OCRRenameConfig.enabled` default → `False` | 1 |
| `src/para_files/pipeline.py` | catch `Exception` per signal; stop swallowing `KeyboardInterrupt`; containment in `get_target_path` | 2, 4 |
| `src/para_files/classifiers/llm_classifier.py` | `_sanitize_category` rejects `..` segments and backslashes | 3 |
| `src/para_files/cli/inbox_cmd.py` | handle `ValueError` from `get_target_path` per file | 4 |
| `src/para_files/mover.py` | process-wide move lock; no `OVERWRITE`; unsafe-filename guard; unique `RENAME_WITH_DATE`; final exists-guard | 5 |
| `src/para_files/cli/shared.py` | remove `ConflictChoice.overwrite` | 5 |
| `src/para_files/cli/bookstore_cmd.py` | keep same-ISBN files with different content; serialize move + rename | 6 |
| `tests/test_config.py`, `tests/test_pipeline.py`, `tests/test_llm_classifier.py`, `tests/test_inbox_cmd.py`, `tests/test_mover.py`, `tests/test_main.py`, `tests/test_bookstore_cmd.py` | new and updated tests | 1–6 |
| `tests/test_move_cmd_safety.py` | new: Ctrl+C and parallel same-name tests for `move` | 2, 5 |
| `CHANGELOG.md`, `docs/configuration/overview.md`, `docs/cli/move.md`, `docs/tasks/move-files.md`, `docs/tasks/handle-duplicates.md` | docs | 1, 5 |

---

### Task 1: OCR rename off by default

**Files:**
- Modify: `src/para_files/config.py` (class `OCRRenameConfig`, field `enabled`, ~line 192)
- Modify: `docs/configuration/overview.md` (section `### OCR Rename`, ~line 94)
- Modify: `CHANGELOG.md` (below `## [Unreleased]`)
- Test: `tests/test_config.py`, `tests/test_pipeline.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `OCRRenameConfig().enabled is False`; the `### Fixed (Stage 0 safety)` CHANGELOG block that later tasks append to.

- [ ] **Step 1: Create the branch and a working environment**

Run:
```bash
git checkout docs/redesign-spec
git checkout -b fix/stage0-safety
uv sync --all-extras --frozen
uv run pytest -q
```
Expected: the suite passes (about 1489 passed, 3 skipped). Write down the exact counts; later tasks must not lose any passing test except the ones this plan explicitly replaces.

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_config.py`, inside `class TestOCRRenameConfig` (after its last method):

```python
    def test_ocr_rename_disabled_by_default(self):
        """OCR rename is opt-in: classification must not rename files by default."""
        from para_files.config import OCRRenameConfig

        assert OCRRenameConfig().enabled is False
```

Append at the end of `tests/test_pipeline.py` (module level, not inside a class):

```python
def test_classify_file_does_not_rename_generic_pdf_by_default(
    mock_config: Config, tmp_path: Path
) -> None:
    """With default config, a generic scanner name is never renamed on disk."""
    from para_files.utils.filename_detector import is_generic_filename

    pdf = tmp_path / "scan_001.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
    assert is_generic_filename(pdf.name)

    pipeline = ClassificationPipeline(mock_config)

    assert pipeline._maybe_rename_generic_pdf(pdf) == pdf
    assert pdf.exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["scan_001.pdf"]
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/test_config.py::TestOCRRenameConfig::test_ocr_rename_disabled_by_default tests/test_pipeline.py::test_classify_file_does_not_rename_generic_pdf_by_default -v`
Expected: `test_ocr_rename_disabled_by_default` FAILS with `assert True is False`. The pipeline test may pass or fail depending on OCR availability; that is fine — it pins the behavior.

- [ ] **Step 4: Change the default**

In `src/para_files/config.py`, class `OCRRenameConfig`, replace:

```python
    enabled: bool = Field(
        default=True,
        description="Enable OCR-based renaming of generic filenames before classification",
    )
```

with:

```python
    enabled: bool = Field(
        default=False,
        description=(
            "Enable OCR-based renaming of generic filenames before classification. "
            "Off by default: it renames files even in preview commands (scan, --dry-run)."
        ),
    )
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_config.py tests/test_pipeline.py -q`
Expected: all PASS.

- [ ] **Step 6: Document the default**

In `docs/configuration/overview.md`, under `### OCR Rename`, insert this bullet as the first bullet of the section (above the `OCR_RENAME_MIN_CONFIDENCE` bullet):

```markdown
- **`PARA_FILES_OCR_RENAME__ENABLED`** - Rename generic PDF names (`scan_001.pdf`, `IMG_1234.pdf`) from their OCR content during classification (default: `false`). Off by default because it renames files even in preview commands such as `scan` and `move --dry-run`.
```

- [ ] **Step 7: Start the CHANGELOG block**

In `CHANGELOG.md`, directly below the line `## [Unreleased]` and its following blank line, insert:

```markdown
### Fixed (Stage 0 safety)

- **OCR rename is off by default** — `ocr_rename.enabled` now defaults to `false`. Before, `scan`, `move --dry-run`, `inbox`, `rescan` and `learn` could rename generic PDFs on disk while classifying. Enable with `PARA_FILES_OCR_RENAME__ENABLED=true`.

```

- [ ] **Step 8: Lint and commit**

Run: `uv run ruff check src/para_files/config.py tests/test_config.py tests/test_pipeline.py && uv run ruff format --check src/para_files/config.py tests/test_config.py tests/test_pipeline.py`
Expected: no errors. If `ruff format --check` lists a file, run `uv run ruff format <file>` on that file only.

```bash
git add src/para_files/config.py tests/test_config.py tests/test_pipeline.py docs/configuration/overview.md CHANGELOG.md
git commit -m "fix(config): disable OCR rename by default so classification never renames files"
```

---

### Task 2: Pipeline survives any signal error and lets Ctrl+C through

**Files:**
- Modify: `src/para_files/pipeline.py` (method `classify`, the loop from `# Run classifiers in priority order` to `logger.info("Classification interrupted by user (Ctrl+C)")`, ~lines 271-346; the `import json` line, ~line 16)
- Test: `tests/test_pipeline.py`, create `tests/test_move_cmd_safety.py`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `ClassificationPipeline.classify` never raises for an `Exception` from a classifier, records a circuit-breaker failure for classifiers named `"SemanticClassifier"` or `"llm"`, and lets `KeyboardInterrupt` propagate.

- [ ] **Step 1: Write the failing tests**

Append at the end of `tests/test_pipeline.py`:

```python
class _FakeProviderError(Exception):
    """Stands in for litellm's APIError, which derives from Exception, not OSError."""


def test_pipeline_skips_classifier_raising_unlisted_exception(mock_config: Config) -> None:
    """A provider error type the pipeline never listed must not abort the cascade."""
    pipeline = ClassificationPipeline(mock_config)
    pipeline._ensure_initialized()

    failing = MagicMock()
    failing.name = "llm"
    failing.classify.side_effect = _FakeProviderError("provider down")

    passing = MagicMock()
    passing.name = "passing_classifier"
    passing.classify.return_value = ClassificationResult(
        category="3_Resources/test",
        confidence=Confidence(value=0.85, source=ClassificationSource.TAXONOMY_CLASSIFIER),
    )

    breaker = MagicMock()
    breaker.is_open = False
    pipeline._classifiers = [failing, passing]
    pipeline._circuit_breaker = breaker

    result = pipeline.classify("any content")

    assert result.category == "3_Resources/test"
    breaker.record_failure.assert_called_once()


def test_pipeline_propagates_keyboard_interrupt(mock_config: Config) -> None:
    """Ctrl+C must abort classification, never become a DEFAULT result."""
    pipeline = ClassificationPipeline(mock_config)
    pipeline._ensure_initialized()

    interrupted = MagicMock()
    interrupted.name = "interrupted_classifier"
    interrupted.classify.side_effect = KeyboardInterrupt

    pipeline._classifiers = [interrupted]

    with pytest.raises(KeyboardInterrupt):
        pipeline.classify("any content")
```

Create `tests/test_move_cmd_safety.py`:

```python
"""Safety tests for the move command (Stage 0)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from para_files.cli.move_cmd import _handle_move_file
from para_files.mover import ConflictStrategy


def test_ctrl_c_during_classification_aborts_and_leaves_file(tmp_path: Path) -> None:
    """Ctrl+C while classifying stops the run; the file is not moved anywhere."""
    source = tmp_path / "doc.txt"
    source.write_text("content")

    pipeline = MagicMock()
    pipeline.classify_file.side_effect = KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        _handle_move_file(
            source,
            pipeline,
            [],
            "Moved",
            dry_run=False,
            copy=False,
            conflict_strategy=ConflictStrategy.RENAME,
            date_prefix=False,
            smart_rename=False,
            output_json=False,
        )

    assert source.exists()
    pipeline.get_target_path.assert_not_called()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_pipeline.py::test_pipeline_skips_classifier_raising_unlisted_exception tests/test_pipeline.py::test_pipeline_propagates_keyboard_interrupt tests/test_move_cmd_safety.py -v`
Expected:
- `test_pipeline_skips_classifier_raising_unlisted_exception` FAILS: `_FakeProviderError` escapes `classify`.
- `test_pipeline_propagates_keyboard_interrupt` FAILS: `DID NOT RAISE KeyboardInterrupt`.
- `test_ctrl_c_during_classification_aborts_and_leaves_file` PASSES already; it pins the end-to-end behavior.

- [ ] **Step 3: Replace the classifier loop**

In `src/para_files/pipeline.py`, method `classify`, replace everything from the line

```python
        # Run classifiers in priority order; stop after first match
```

down to and including the lines

```python
        except KeyboardInterrupt:
            logger.info("Classification interrupted by user (Ctrl+C)")
```

with:

```python
        # Run classifiers in priority order; stop after first match.
        # KeyboardInterrupt is deliberately not caught: Ctrl+C must abort the
        # run instead of becoming a DEFAULT result that a caller would move.
        for idx, classifier in enumerate(self._classifiers):
            # Skip Ollama-dependent classifiers when circuit breaker is open
            if (
                self._circuit_breaker
                and self._circuit_breaker.is_open
                and classifier.name in _ollama_classifiers
            ):
                signal_source = self._get_signal_source(classifier)
                signals.append(
                    SignalResult(
                        source=signal_source,
                        name=classifier.name,
                        score=0.0,
                        matched=False,
                        skipped=True,
                    )
                )
                continue

            signal_source = self._get_signal_source(classifier)
            try:
                result = classifier.classify(content, metadata)
                if result is not None:
                    if self._circuit_breaker and classifier.name in _ollama_classifiers:
                        self._circuit_breaker.record_success()
                    signals.append(
                        SignalResult(
                            source=signal_source,
                            name=classifier.name,
                            score=result.confidence.value,
                            matched=True,
                        )
                    )
                    winner = result
                    winner_idx = idx
                    logger.debug(
                        "Classified by {}: {} ({:.0f}%)",
                        classifier.name,
                        result.category,
                        result.confidence.value * 100,
                    )
                    break
                signals.append(
                    SignalResult(
                        source=signal_source,
                        name=classifier.name,
                        score=0.0,
                        matched=False,
                    )
                )
            # Any signal failure (including provider errors such as litellm's,
            # which derive from Exception) must not abort the cascade.
            except Exception as e:  # noqa: BLE001
                if self._circuit_breaker and classifier.name in _ollama_classifiers:
                    self._circuit_breaker.record_failure()
                logger.exception("Classifier {} failed: {}", classifier.name, e)
                signals.append(
                    SignalResult(
                        source=signal_source,
                        name=classifier.name,
                        score=0.0,
                        matched=False,
                    )
                )
```

Then delete the line `import json` near the top of `src/para_files/pipeline.py` (it was only used by the removed exception tuple).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_pipeline.py tests/test_pipeline_order.py tests/test_circuit_breaker.py tests/test_move_cmd_safety.py -q`
Expected: all PASS.

- [ ] **Step 5: Lint and type-check**

Run: `uv run ruff check src/para_files/pipeline.py tests/test_pipeline.py tests/test_move_cmd_safety.py && uv run mypy src/para_files/pipeline.py`
Expected: no errors. If ruff reports `RUF100` (unused `noqa`) on the `except Exception` line, delete the `# noqa: BLE001` comment and re-run.

- [ ] **Step 6: CHANGELOG and commit**

In `CHANGELOG.md`, append this bullet at the end of the `### Fixed (Stage 0 safety)` block:

```markdown
- **One failing signal no longer aborts classification** — the pipeline now catches any `Exception` from a classifier (litellm provider errors were not caught), so the next signal runs and the circuit breaker records the failure. Ctrl+C now aborts the run instead of returning a default result that `move` would act on.
```

```bash
git add src/para_files/pipeline.py tests/test_pipeline.py tests/test_move_cmd_safety.py CHANGELOG.md
git commit -m "fix(pipeline): survive any classifier error and propagate Ctrl+C"
```

---

### Task 3: LLM categories cannot climb out of PARA

**Files:**
- Modify: `src/para_files/classifiers/llm_classifier.py` (method `_sanitize_category`, after the absolute/Windows path check, ~line 293)
- Test: `tests/test_llm_classifier.py`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: nothing.
- Produces: `LLMClassifier._sanitize_category(category: str) -> str | None` returns `None` for any category containing a `..` path segment or a backslash.

- [ ] **Step 1: Write the failing tests**

In `tests/test_llm_classifier.py`, insert directly after `test_sanitize_category_rejects_windows_path`:

```python
def test_sanitize_category_rejects_parent_traversal(classifier: LLMClassifier) -> None:
    """A '..' segment behind an allowed prefix is rejected."""
    result = classifier._sanitize_category("3_Resources/documentation/../../../etc")
    assert result is None


def test_sanitize_category_rejects_backslash(classifier: LLMClassifier) -> None:
    """Backslash separators are rejected."""
    result = classifier._sanitize_category("3_Resources\\documentation\\Python")
    assert result is None


def test_sanitize_category_allows_dots_inside_a_name(classifier: LLMClassifier) -> None:
    """Dots inside a folder name are not traversal."""
    result = classifier._sanitize_category("3_Resources/documentation/Python..notes")
    assert result == "3_Resources/documentation/Python..notes"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_llm_classifier.py -k "traversal or backslash or dots_inside" -v`
Expected: `test_sanitize_category_rejects_parent_traversal` FAILS (returns the path). The other two may pass already; they pin behavior.

- [ ] **Step 3: Add the check**

In `src/para_files/classifiers/llm_classifier.py`, method `_sanitize_category`, directly after this existing block:

```python
        if category.startswith(("/", "~")) or ":\\" in category or is_windows_path:
            logger.debug("LLM rejected hallucinated path: {}", category[:100])
            return None
```

insert:

```python

        # Reject traversal and backslash separators: the category becomes a
        # directory under para_root, so it must never climb out of it.
        if "\\" in category or ".." in category.split("/"):
            logger.debug("LLM rejected path traversal: {}", category[:100])
            return None
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_llm_classifier.py -q`
Expected: all PASS.

- [ ] **Step 5: Lint, CHANGELOG, commit**

Run: `uv run ruff check src/para_files/classifiers/llm_classifier.py tests/test_llm_classifier.py`
Expected: no errors.

Append to the `### Fixed (Stage 0 safety)` block in `CHANGELOG.md`:

```markdown
- **LLM categories cannot escape the PARA root** — `_sanitize_category` now rejects any category containing a `..` segment or a backslash, even behind an allowed prefix such as `3_Resources/documentation/`.
```

```bash
git add src/para_files/classifiers/llm_classifier.py tests/test_llm_classifier.py CHANGELOG.md
git commit -m "fix(llm): reject path traversal in LLM category output"
```

---

### Task 4: Target directories must be strictly inside the PARA root

**Files:**
- Modify: `src/para_files/pipeline.py` (method `get_target_path`, ~line 474)
- Modify: `src/para_files/cli/inbox_cmd.py` (function `_process_inbox_file`, the line `target_dir = pipeline.get_target_path(result)`, ~line 82)
- Test: `tests/test_pipeline.py`, `tests/test_inbox_cmd.py`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: nothing.
- Produces: `ClassificationPipeline.get_target_path(result: ClassificationResult) -> Path` returns `para_root / result.category` unchanged for valid categories, and raises `ValueError` when the resolved target is the PARA root itself or lies outside it. Callers in `move_cmd`, `classify_cmd` and `scan_cmd` already wrap it in `except Exception` and report the file as failed; `inbox_cmd` is fixed here.

- [ ] **Step 1: Write the failing tests**

Append at the end of `tests/test_pipeline.py`:

```python
@pytest.mark.parametrize(
    "category",
    ["../outside", "3_Resources/../../outside", "/etc", "", "."],
)
def test_get_target_path_refuses_escape_or_root(mock_config: Config, category: str) -> None:
    """Targets must be a subfolder of para_root: never outside it, never the root itself."""
    pipeline = ClassificationPipeline(mock_config)
    result = ClassificationResult(
        category=category,
        confidence=Confidence(value=0.9, source=ClassificationSource.LLM_FALLBACK),
    )

    with pytest.raises(ValueError, match="PARA root"):
        pipeline.get_target_path(result)


def test_get_target_path_accepts_nested_category(mock_config: Config) -> None:
    """A normal category still maps to para_root / category."""
    pipeline = ClassificationPipeline(mock_config)
    result = ClassificationResult(
        category="4_Archives/5y_factures/Telephonie",
        confidence=Confidence(value=0.9, source=ClassificationSource.RULES_ENGINE),
    )

    assert pipeline.get_target_path(result) == (
        mock_config.para_root / "4_Archives/5y_factures/Telephonie"
    )
```

In `tests/test_inbox_cmd.py`, add this method at the end of `class TestProcessInboxFile`:

```python
    def test_refused_target_is_counted_as_error_and_file_stays(self, tmp_path: Path) -> None:
        """A target outside the PARA root is reported per file; the run continues."""
        file_path = self._make_file(tmp_path)
        pipeline = MagicMock()
        pipeline.classify_file.return_value = self._make_result(ClassificationSource.RULES_ENGINE)
        pipeline.get_target_path.side_effect = ValueError("Refusing target outside PARA root")

        stats = _InboxStats(total=1)

        _process_inbox_file(
            file_path,
            pipeline,
            stats,
            idx=1,
            total=1,
            dry_run=False,
            conflict_strategy=ConflictStrategy.RENAME,
            verbose=False,
        )

        assert stats.failed == 1
        assert stats.moved == 0
        assert file_path.exists()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_pipeline.py -k "get_target_path" tests/test_inbox_cmd.py::TestProcessInboxFile::test_refused_target_is_counted_as_error_and_file_stays -v`
Expected: the five `test_get_target_path_refuses_escape_or_root` cases FAIL (`DID NOT RAISE`); the inbox test FAILS with an uncaught `ValueError`; `test_get_target_path_accepts_nested_category` and the existing `test_get_target_path` PASS.

- [ ] **Step 3: Add the containment check**

In `src/para_files/pipeline.py`, replace the whole method:

```python
    def get_target_path(self, result: ClassificationResult) -> Path:
        """Get full target path for a classification result.

        Args:
            result: Classification result with category.

        Returns:
            Full path under PARA root.
        """
        return self._config.para_root / result.category
```

with:

```python
    def get_target_path(self, result: ClassificationResult) -> Path:
        """Get full target path for a classification result.

        Args:
            result: Classification result with category.

        Returns:
            Full path under PARA root.

        Raises:
            ValueError: If the target is the PARA root itself or lies outside it.
        """
        root = self._config.para_root
        target = root / result.category
        resolved_root = root.resolve()
        resolved_target = target.resolve()
        if resolved_target == resolved_root or not resolved_target.is_relative_to(resolved_root):
            msg = f"Refusing target outside PARA root subfolders: {result.category!r}"
            raise ValueError(msg)
        return target
```

- [ ] **Step 4: Handle the refusal in `inbox`**

In `src/para_files/cli/inbox_cmd.py`, function `_process_inbox_file`, replace the line:

```python
    target_dir = pipeline.get_target_path(result)
```

with:

```python
    try:
        target_dir = pipeline.get_target_path(result)
    except ValueError as e:
        stats.failed += 1
        typer.echo(f"[{idx}/{total}] ERROR: {file_path.name} - {e}", err=True)
        return
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_pipeline.py tests/test_inbox_cmd.py tests/test_scan_cmd.py tests/test_concurrent_move.py tests/test_parallel.py -q`
Expected: all PASS.

- [ ] **Step 6: Lint, type-check, CHANGELOG, commit**

Run: `uv run ruff check src/para_files/pipeline.py src/para_files/cli/inbox_cmd.py tests/test_pipeline.py tests/test_inbox_cmd.py && uv run mypy src/para_files/pipeline.py src/para_files/cli/inbox_cmd.py`
Expected: no errors.

Append to the `### Fixed (Stage 0 safety)` block in `CHANGELOG.md`:

```markdown
- **Targets must stay inside the PARA root** — `get_target_path` now refuses any category that resolves outside `para_root` or to `para_root` itself (for example the `generic_folders` rule, which has no destination and used to drop files loose into the root). `inbox` reports such files as errors and continues.
```

```bash
git add src/para_files/pipeline.py src/para_files/cli/inbox_cmd.py tests/test_pipeline.py tests/test_inbox_cmd.py CHANGELOG.md
git commit -m "fix(pipeline): refuse move targets outside PARA root subfolders"
```

---

### Task 5: The mover never overwrites and moves one file at a time

**Files:**
- Modify: `src/para_files/mover.py` (imports; `ConflictStrategy`; `FileMover.move`; `_resolve_conflict`; `_execute_move`)
- Modify: `src/para_files/cli/shared.py` (class `ConflictChoice`, ~line 57)
- Modify: `tests/test_mover.py`, `tests/test_main.py`, `tests/test_move_cmd_safety.py`
- Modify: `docs/cli/move.md`, `docs/tasks/move-files.md`, `docs/tasks/handle-duplicates.md`, `CHANGELOG.md`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `ConflictStrategy` members: `SKIP`, `RENAME`, `RENAME_WITH_DATE` (no `OVERWRITE`).
  - `ConflictChoice` members: `skip`, `rename`, `rename_with_date` (no `overwrite`).
  - `FileMover.move(source, destination_dir, classification=None) -> MoveResult` holds the module lock `_MOVE_LOCK` for the whole operation; the body lives in `FileMover._move_unlocked` with the same signature.
  - `MoveResult(success=False, action="error")` when the destination filename is not a plain name, or when the destination exists at the moment of the move.

- [ ] **Step 1: Write the failing tests**

In `tests/test_mover.py`, change the import block at the top from:

```python
from para_files.types import ClassificationResult
```

to:

```python
from para_files.types import ClassificationResult, ClassificationSource, Confidence
```

In `tests/test_mover.py`, `class TestConflictStrategy`, replace the method `test_all_strategies_defined` with:

```python
    def test_all_strategies_defined(self):
        """Test all conflict strategies are defined, and none overwrites."""
        assert ConflictStrategy.SKIP.value == "skip"
        assert ConflictStrategy.RENAME.value == "rename"
        assert ConflictStrategy.RENAME_WITH_DATE.value == "rename_with_date"
        assert "overwrite" not in {s.value for s in ConflictStrategy}
```

In `tests/test_mover.py`, `class TestConflictResolution`, delete the whole method `test_overwrite_existing` (the one that builds `FileMover(conflict_strategy=ConflictStrategy.OVERWRITE)`).

Append at the end of `tests/test_mover.py`:

```python
class TestNoClobber:
    """Stage 0: the mover never overwrites and never escapes the target directory."""

    def test_existing_destination_never_overwritten(self, tmp_path: Path):
        """_execute_move refuses to replace a file that exists at the destination."""
        source = tmp_path / "new.txt"
        source.write_text("new content")
        dest = tmp_path / "dest" / "new.txt"
        dest.parent.mkdir()
        dest.write_text("old content")

        result = FileMover()._execute_move(source, dest)

        assert result.success is False
        assert result.action == "error"
        assert dest.read_text() == "old content"
        assert source.read_text() == "new content"

    def test_rename_with_date_never_reuses_taken_name(self, tmp_path: Path):
        """Two moves in the same second get distinct names."""
        from datetime import UTC, datetime
        from unittest.mock import patch

        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        (dest_dir / "report.docx").write_text("existing")
        (dest_dir / "report_20261010_120000.docx").write_text("earlier same-second move")
        source = tmp_path / "report.docx"
        source.write_text("new")

        with patch("para_files.mover.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 10, 10, 12, 0, 0, tzinfo=UTC)
            mock_dt.fromtimestamp = datetime.fromtimestamp
            result = FileMover(conflict_strategy=ConflictStrategy.RENAME_WITH_DATE).move(
                source, dest_dir
            )

        assert result.success is True
        assert result.destination == dest_dir / "report_20261010_120000_1.docx"
        assert (dest_dir / "report_20261010_120000.docx").read_text() == (
            "earlier same-second move"
        )

    def test_smart_rename_with_path_separator_is_refused(self, tmp_path: Path):
        """A suggested name containing a path cannot place the file elsewhere."""
        source = tmp_path / "book.pdf"
        source.write_bytes(b"%PDF-1.4")
        dest_dir = tmp_path / "para" / "3_Resources" / "livres"
        classification = ClassificationResult(
            category="3_Resources/livres",
            confidence=Confidence(value=1.0, source=ClassificationSource.BOOK_DETECTOR),
            extracted_params={"suggested_name": "../../escaped"},
        )

        result = FileMover(smart_rename=True).move(source, dest_dir, classification)

        assert result.success is False
        assert "unsafe" in result.message
        assert source.exists()
        assert not (tmp_path / "para" / "escaped.pdf").exists()

    def test_parallel_moves_of_same_name_keep_every_file(self, tmp_path: Path):
        """Concurrent moves of different files with one name lose nothing."""
        from concurrent.futures import ThreadPoolExecutor

        dest_dir = tmp_path / "dest"
        sources = []
        for i in range(8):
            src_dir = tmp_path / f"src{i}"
            src_dir.mkdir()
            f = src_dir / "same.txt"
            f.write_text(f"content {i}")
            sources.append(f)

        mover = FileMover(conflict_strategy=ConflictStrategy.RENAME)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda s: mover.move(s, dest_dir), sources))

        assert all(r.success for r in results)
        contents = sorted(p.read_text() for p in dest_dir.iterdir())
        assert contents == sorted(f"content {i}" for i in range(8))
```

Append at the end of `tests/test_move_cmd_safety.py`:

```python
def test_parallel_move_keeps_same_named_files(tmp_path: Path) -> None:
    """A parallel `move` of six different files named alike keeps all six."""
    from para_files.cli.move_cmd import _move_files_parallel
    from para_files.types import ClassificationResult, ClassificationSource, Confidence

    target = tmp_path / "para" / "3_Resources" / "test"
    files = []
    for i in range(6):
        folder = tmp_path / f"in{i}"
        folder.mkdir()
        f = folder / "same.txt"
        f.write_text(f"payload {i}")
        files.append(f)

    pipeline = MagicMock()
    pipeline.classify_file.return_value = ClassificationResult(
        category="3_Resources/test",
        confidence=Confidence(value=0.9, source=ClassificationSource.RULES_ENGINE),
    )
    pipeline.get_target_path.return_value = target

    _, _, success, skipped, failed = _move_files_parallel(
        files,
        pipeline,
        4,
        dry_run=False,
        copy=False,
        conflict_strategy=ConflictStrategy.RENAME,
        date_prefix=False,
        smart_rename=False,
        skip_unclassifiable=False,
        output_json=True,
        action_verb="Moved",
    )

    assert (success, skipped, failed) == (6, 0, 0)
    contents = sorted(p.read_text() for p in target.iterdir())
    assert contents == sorted(f"payload {i}" for i in range(6))
```

In `tests/test_main.py`, method `test_conflict_choice_enum`, replace the line:

```python
        assert ConflictChoice.overwrite.value == "overwrite"
```

with:

```python
        assert "overwrite" not in {c.value for c in ConflictChoice}
```

In `tests/test_main.py`, replace the whole method `test_move_with_conflict_overwrite` with:

```python
    def test_move_rejects_conflict_overwrite(self, tmp_path):
        """The overwrite strategy no longer exists on the CLI."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        result = runner.invoke(
            app, ["move", str(test_file), "--dry-run", "--conflict", "overwrite"]
        )
        assert result.exit_code == 2
        assert test_file.read_text() == "Test content"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_mover.py::TestConflictStrategy tests/test_mover.py::TestNoClobber tests/test_main.py::TestHelperFunctions::test_conflict_choice_enum tests/test_main.py::TestMoveAdvanced::test_move_rejects_conflict_overwrite tests/test_move_cmd_safety.py -v`

Expected FAILs:
- `test_all_strategies_defined` (`overwrite` still present)
- `test_existing_destination_never_overwritten` (the move succeeds and overwrites)
- `test_rename_with_date_never_reuses_taken_name` (it returns the taken name)
- `test_smart_rename_with_path_separator_is_refused` (the move succeeds)
- `test_conflict_choice_enum`
- `test_move_rejects_conflict_overwrite` (exit code 0)

The two parallel tests may pass or fail depending on thread timing; they pin the behavior.

- [ ] **Step 3: Add the lock and remove `OVERWRITE` in `mover.py`**

In `src/para_files/mover.py`, change the imports from:

```python
import hashlib
import os
import shutil
```

to:

```python
import hashlib
import os
import shutil
import threading
```

After the line `_hash_cache: dict[tuple[str, float], str] = {}`, add:

```python

# Process-wide lock: moves run one at a time, so the destination check and the
# filesystem operation never interleave between worker threads.
_MOVE_LOCK = threading.Lock()
```

In `class ConflictStrategy`, delete the line:

```python
    OVERWRITE = "overwrite"  # Overwrite existing file
```

- [ ] **Step 4: Wrap `move` in the lock and refuse unsafe filenames**

In `class FileMover`, rename the existing method `def move(` to `def _move_unlocked(` and replace its docstring's first line `"""Move or copy a file to the destination directory.` with `"""Move body; the caller must hold ``_MOVE_LOCK``.` (leave the Args/Returns sections as they are).

Then insert this new method directly above `_move_unlocked`:

```python
    def move(
        self,
        source: Path,
        destination_dir: Path,
        classification: ClassificationResult | None = None,
    ) -> MoveResult:
        """Move or copy a file to the destination directory.

        Moves are serialized process-wide so that the conflict check and the
        filesystem operation are atomic with respect to other threads.

        Args:
            source: Source file path.
            destination_dir: Target directory (will be created if needed).
            classification: Optional classification result for smart renaming.

        Returns:
            MoveResult with operation details.
        """
        with _MOVE_LOCK:
            return self._move_unlocked(source, destination_dir, classification)
```

In `_move_unlocked`, directly after the line:

```python
        filename = self._build_filename(source, classification)
```

insert:

```python
        if filename in {"", ".", ".."} or Path(filename).name != filename:
            return MoveResult(
                source=source,
                destination=destination_dir / source.name,
                success=False,
                action="error",
                message=f"Refusing unsafe destination filename: {filename!r}",
            )
```

- [ ] **Step 5: Make conflict resolution never return an occupied path**

In `_resolve_conflict`, delete these two lines:

```python
        if self.conflict_strategy == ConflictStrategy.OVERWRITE:
            return destination
```

and replace the final block:

```python
        # RENAME_WITH_DATE: Add current timestamp to make unique
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        stem = destination.stem
        suffix = destination.suffix
        return destination.with_name(f"{stem}_{timestamp}{suffix}")
```

with:

```python
        # RENAME_WITH_DATE: add a timestamp, then a counter if that name is taken too
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        dated = destination.with_name(f"{destination.stem}_{timestamp}{destination.suffix}")
        return dated if not dated.exists() else self._find_unique_name(dated)
```

In `_execute_move`, directly after the `if self.dry_run:` block (the one returning `action=f"would be {action}"`), insert:

```python
        if destination.exists():
            return MoveResult(
                source=source,
                destination=destination,
                success=False,
                action="error",
                message=f"Refusing to overwrite existing file: {destination}",
            )
```

- [ ] **Step 6: Remove the CLI choice**

In `src/para_files/cli/shared.py`, class `ConflictChoice`, delete the line:

```python
    overwrite = "overwrite"
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `uv run pytest tests/test_mover.py tests/test_main.py tests/test_move_cmd_safety.py tests/test_concurrent_move.py tests/test_parallel.py tests/test_inbox_cmd.py tests/test_bookstore_cmd.py -q`
Expected: all PASS.

Then check that nothing else referenced the removed member:

Run: `grep -rn "OVERWRITE\|ConflictChoice.overwrite" src/ tests/`
Expected: no output.

- [ ] **Step 8: Update the docs**

`docs/cli/move.md`:
- In the `### --conflict` option list, delete the line `` - `overwrite` - Replace existing file ``.
- Under `**"File already exists"?**`, replace `` Use `--conflict rename` or `--conflict overwrite` `` with `` Use `--conflict rename` or `--conflict rename_with_date`. Existing files are never overwritten. ``

`docs/tasks/move-files.md`: delete these two lines and the blank line before them:

```text
# Overwrite (careful!)
uv run para-files move *.pdf --conflict overwrite
```

`docs/tasks/handle-duplicates.md`:
- In the `## Conflict Options` code block, delete the line `--conflict overwrite      # Replace existing (careful!)`.
- Delete the whole `## Overwrite (Careful!)` section: its heading, its code block, and its `**When to use:** Almost never—very dangerous` line.

- [ ] **Step 9: Lint, type-check, CHANGELOG, commit**

Run: `uv run ruff check src/para_files/mover.py src/para_files/cli/shared.py tests/test_mover.py tests/test_main.py tests/test_move_cmd_safety.py && uv run mypy src/para_files/mover.py src/para_files/cli/shared.py`
Expected: no errors.

Append to the `### Fixed (Stage 0 safety)` block in `CHANGELOG.md`:

```markdown
- **Moves never overwrite and run one at a time** — parallel `move` could silently replace a file when two files with the same name went to the same folder. Moves are now serialized process-wide, `rename_with_date` never reuses a taken name, a final check refuses to replace an existing file, and a suggested filename containing a path is refused.

### Removed (Stage 0 safety)

- **`--conflict overwrite`** and `ConflictStrategy.OVERWRITE` — the tool no longer replaces existing files. Use `rename` or `rename_with_date`.
```

```bash
git add src/para_files/mover.py src/para_files/cli/shared.py tests/test_mover.py tests/test_main.py tests/test_move_cmd_safety.py docs/cli/move.md docs/tasks/move-files.md docs/tasks/handle-duplicates.md CHANGELOG.md
git commit -m "fix(mover): never overwrite, serialize moves, refuse unsafe filenames"
```

---

### Task 6: `bookstore` keeps books that share an ISBN but differ

**Files:**
- Modify: `src/para_files/cli/bookstore_cmd.py` (imports; new `_sha256`; `_handle_isbn_duplicate`; `_BookstoreContext`; `_check_and_register_isbn`; `_process_book_file`)
- Test: `tests/test_bookstore_cmd.py`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: `FileMover.move` from Task 5 (already serialized; this task also serializes the rename that follows it).
- Produces:
  - `_sha256(path: Path) -> str`
  - `_BookstoreContext.isbn_hashes: dict[str, str]` and `_BookstoreContext.move_lock: Lock`
  - `_check_and_register_isbn(isbn, book_file, ctx, *, file_hash: str = "") -> tuple[bool, Path | None]` (records `file_hash` for the first file of each ISBN)
  - `_handle_isbn_duplicate(book_file, first_file, isbn, *, identical: bool, keep_duplicates: bool, dry_run: bool, verbose: bool) -> None` (deletes only when `identical` is `True`)

- [ ] **Step 1: Update the existing tests and write the failing ones**

In `tests/test_bookstore_cmd.py`, class `TestHandleIsbnDuplicate`: in each of the four existing calls to `_handle_isbn_duplicate`, add the argument `identical=True,` on the line before `keep_duplicates=...`. Their files have the same content, so their expectations do not change.

Add this method at the end of `class TestHandleIsbnDuplicate`:

```python
    def test_keeps_duplicate_with_different_content(self, tmp_path: Path):
        """Same ISBN, different content (another edition or scan): never deleted."""
        duplicate_file = tmp_path / "second_edition.pdf"
        duplicate_file.write_bytes(b"%PDF-1.4 second edition")
        first_file = tmp_path / "first.pdf"
        first_file.write_bytes(b"%PDF-1.4 first edition")

        _handle_isbn_duplicate(
            duplicate_file,
            first_file,
            "9780134685991",
            identical=False,
            keep_duplicates=False,
            dry_run=False,
            verbose=False,
        )

        assert duplicate_file.exists()
        assert first_file.exists()
```

Append at the end of `tests/test_bookstore_cmd.py`:

```python
class TestStage0BookstoreSafety:
    """Stage 0: no data loss in bookstore."""

    def test_register_records_first_file_hash(self, tmp_path: Path) -> None:
        """The first file of an ISBN has its content hash recorded."""
        ctx = _BookstoreContext(
            para_root=tmp_path,
            mover=FileMover(dry_run=True),
            dry_run=True,
            rename=False,
            keep_duplicates=False,
            verbose=False,
        )
        book = tmp_path / "a.pdf"
        book.write_bytes(b"x")

        _check_and_register_isbn("9780134685991", book, ctx, file_hash="abc")

        assert ctx.isbn_hashes["9780134685991"] == "abc"

    def test_parallel_books_with_same_title_are_all_kept(self, tmp_path: Path) -> None:
        """Eight different books renamed to one title in parallel: all eight survive."""
        from para_files.cli.bookstore_cmd import _process_book_file

        para = tmp_path / "para"
        dest = para / "3_Resources" / "livres" / "U_Informatique"
        books: list[Path] = []
        for i in range(8):
            folder = tmp_path / f"in{i}"
            folder.mkdir()
            book = folder / f"scan{i}.pdf"
            book.write_bytes(f"book {i}".encode())
            books.append(book)

        def fake_detect(book_file: Path, para_root: Path, *, rename: bool) -> dict:
            n = books.index(book_file)
            return {
                "isbn": f"isbn-{n}",
                "dest_dir": dest,
                "new_filename": "Same Author - Same Title (2020).pdf",
                "title": "Same Title",
                "authors": "Same Author",
                "thema": "UB",
                "category": "3_Resources/livres/U_Informatique",
            }

        ctx = _BookstoreContext(
            para_root=para,
            mover=FileMover(dry_run=False, deduplicate=True),
            dry_run=False,
            rename=True,
            keep_duplicates=False,
            verbose=False,
        )

        with (
            patch("para_files.cli.bookstore_cmd._extract_isbns_from_file", return_value=["x"]),
            patch(
                "para_files.cli.bookstore_cmd.find_matching_book_info",
                return_value=(MagicMock(), "x"),
            ),
            patch("para_files.cli.bookstore_cmd._detect_book", side_effect=fake_detect),
            ThreadPoolExecutor(max_workers=8) as pool,
        ):
            list(pool.map(lambda b: _process_book_file(b, ctx), books))

        contents = sorted(p.read_bytes() for p in dest.iterdir())
        assert contents == sorted(f"book {i}".encode() for i in range(8))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_bookstore_cmd.py -v`
Expected:
- The four updated `TestHandleIsbnDuplicate` tests and `test_keeps_duplicate_with_different_content` FAIL with `TypeError: ... unexpected keyword argument 'identical'`.
- `test_register_records_first_file_hash` FAILS (`unexpected keyword argument 'file_hash'`).
- `test_parallel_books_with_same_title_are_all_kept` may pass or fail depending on thread timing; it pins the behavior.

- [ ] **Step 3: Add the hash helper and the new context fields**

In `src/para_files/cli/bookstore_cmd.py`, change the imports from:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
```

to:

```python
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
```

Insert this function directly above `def _handle_isbn_duplicate(`:

```python
def _sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of a file's content."""
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


```

In `class _BookstoreContext`, directly after the line:

```python
    processed_isbns: dict[str, Path] = field(default_factory=dict)
```

insert:

```python
    isbn_hashes: dict[str, str] = field(default_factory=dict)
    # Serializes move + rename so two books renamed to one title never collide
    move_lock: Lock = field(default_factory=Lock)
```

- [ ] **Step 4: Delete ISBN duplicates only when identical**

Replace the signature and the start of `_handle_isbn_duplicate`, from `def _handle_isbn_duplicate(` down to and including the line `if keep_duplicates:`, with:

```python
def _handle_isbn_duplicate(
    book_file: Path,
    first_file: Path,
    isbn: str,
    *,
    identical: bool,
    keep_duplicates: bool,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Handle ISBN duplicate file.

    A duplicate is deleted only when its content is identical to the first file
    with this ISBN. Same ISBN with different content (another edition or scan)
    is always kept.

    Args:
        book_file: The duplicate file to handle.
        first_file: The first file with this ISBN (already processed).
        isbn: The ISBN that is duplicated.
        identical: True if book_file has the same content as first_file.
        keep_duplicates: If True, skip without deleting.
        dry_run: If True, don't actually delete.
        verbose: If True, show detailed output.
    """
    if not identical:
        typer.echo(f"⏭️  Kept: {book_file.name}")
        typer.echo(f"   Same ISBN {isbn} as {first_file.name}, but different content")
        typer.echo()
        return
    if keep_duplicates:
```

Leave the rest of the function body (the `keep_duplicates` / `dry_run` / `unlink` branches) unchanged.

- [ ] **Step 5: Record the first file's hash**

Replace the whole function `_check_and_register_isbn` with:

```python
def _check_and_register_isbn(
    isbn: str,
    book_file: Path,
    ctx: _BookstoreContext,
    *,
    file_hash: str = "",
) -> tuple[bool, Path | None]:
    """Thread-safe check and register ISBN, handling duplicates.

    Args:
        isbn: The ISBN to check and register.
        book_file: Path to the book file.
        ctx: Shared context with thread-safe state.
        file_hash: SHA-256 of book_file, recorded for the first file of each ISBN.

    Returns:
        Tuple of (is_duplicate, first_file_if_duplicate).
    """
    with ctx.lock:
        if isbn in ctx.processed_isbns:
            ctx.duplicates_skipped += 1
            return True, ctx.processed_isbns[isbn]
        ctx.processed_isbns[isbn] = book_file
        ctx.isbn_hashes[isbn] = file_hash
        ctx.books_found += 1
        return False, None
```

- [ ] **Step 6: Wire the hash in and serialize move + rename**

In `_process_book_file`, replace this block:

```python
    # Thread-safe ISBN check and registration
    is_duplicate, first_file = _check_and_register_isbn(isbn, book_file, ctx)
    if is_duplicate and first_file:
        _handle_isbn_duplicate(
            book_file,
            first_file,
            isbn,
            keep_duplicates=ctx.keep_duplicates,
            dry_run=ctx.dry_run,
            verbose=ctx.verbose,
        )
        return
```

with:

```python
    # Thread-safe ISBN check and registration
    file_hash = _sha256(book_file)
    is_duplicate, first_file = _check_and_register_isbn(
        isbn, book_file, ctx, file_hash=file_hash
    )
    if is_duplicate and first_file:
        with ctx.lock:
            first_hash = ctx.isbn_hashes.get(isbn, "")
        _handle_isbn_duplicate(
            book_file,
            first_file,
            isbn,
            identical=first_hash == file_hash,
            keep_duplicates=ctx.keep_duplicates,
            dry_run=ctx.dry_run,
            verbose=ctx.verbose,
        )
        return
```

Then, in the same function, replace this block:

```python
    # Move file using FileMover (handles content deduplication)
    move_result = ctx.mover.move(book_file, dest_dir)

    # Check if it was a content duplicate
    if move_result.action and "duplicate" in move_result.action:
        with ctx.lock:
            ctx.content_duplicates += 1
        if ctx.verbose:
            typer.echo(f"🔄 Content duplicate: {book_file.name}")
            typer.echo(f"   Identical to: {final_dest}")
            typer.echo()
        return

    # Rename file if move succeeded and rename is requested
    actual_dest = _rename_after_move(move_result, new_filename, book_file.name, dry_run=ctx.dry_run)
```

with:

```python
    # Move, then rename, as one step: two books renamed to the same title must
    # not both pick the same free name.
    with ctx.move_lock:
        # Move file using FileMover (handles content deduplication)
        move_result = ctx.mover.move(book_file, dest_dir)
        is_content_duplicate = bool(move_result.action) and "duplicate" in move_result.action
        actual_dest = (
            None
            if is_content_duplicate
            else _rename_after_move(
                move_result, new_filename, book_file.name, dry_run=ctx.dry_run
            )
        )

    # Check if it was a content duplicate
    if is_content_duplicate:
        with ctx.lock:
            ctx.content_duplicates += 1
        if ctx.verbose:
            typer.echo(f"🔄 Content duplicate: {book_file.name}")
            typer.echo(f"   Identical to: {final_dest}")
            typer.echo()
        return
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `uv run pytest tests/test_bookstore_cmd.py -q`
Expected: all PASS.

- [ ] **Step 8: Lint, type-check, CHANGELOG, commit**

Run: `uv run ruff check src/para_files/cli/bookstore_cmd.py tests/test_bookstore_cmd.py && uv run ruff format --check src/para_files/cli/bookstore_cmd.py tests/test_bookstore_cmd.py && uv run mypy src/para_files/cli/bookstore_cmd.py`
Expected: no errors. If `ruff format --check` lists a file, run `uv run ruff format <file>` on that file only and re-run.

Append to the `### Fixed (Stage 0 safety)` block in `CHANGELOG.md` (above the `### Removed (Stage 0 safety)` heading added in Task 5):

```markdown
- **`bookstore` no longer deletes different books that share an ISBN** — an ISBN duplicate is deleted only when its content is identical to the first file; other editions or scans are kept and reported. Move and rename now run as one step, so two books renamed to the same title cannot overwrite each other.
```

```bash
git add src/para_files/cli/bookstore_cmd.py tests/test_bookstore_cmd.py CHANGELOG.md
git commit -m "fix(bookstore): keep same-ISBN books with different content; serialize move+rename"
```

---

### Task 7: Whole-branch verification

**Files:**
- No source changes, unless verification finds a defect. In that case fix it inside the task that owns the code, then re-run this task.

**Interfaces:**
- Consumes: Tasks 1–6.
- Produces: a green branch `fix/stage0-safety` ready for review.

- [ ] **Step 1: Full test suite**

Run: `uv run pytest -q`
Expected: all PASS. Passed count = Task 1 baseline − 1 (`test_overwrite_existing`, deleted in Task 5) + 23 new tests (Task 1: 2, Task 2: 3, Task 3: 3, Task 4: 7 counting the 5 parametrized cases, Task 5: 5, Task 6: 3). No test that passed at baseline may fail.

- [ ] **Step 2: Lint, format, types on the whole project**

Run:
```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
```
Expected: no errors from any of them.

- [ ] **Step 3: Spec checklist**

Confirm each Stage 0 item against the code:

| Spec item | Where | Check |
|---|---|---|
| OCR rename default `False` | `config.py` `OCRRenameConfig.enabled` | `uv run python -c "from para_files.config import OCRRenameConfig as C; print(C().enabled)"` prints `False` |
| containment | `pipeline.get_target_path`, `FileMover._move_unlocked` | tests `test_get_target_path_refuses_escape_or_root`, `test_smart_rename_with_path_separator_is_refused` pass |
| refuse overwrite | `FileMover._execute_move`, no `OVERWRITE` | `grep -rn "OVERWRITE" src/` prints nothing |
| moves sequential | `_MOVE_LOCK` in `mover.py`, `move_lock` in `bookstore_cmd.py` | parallel tests pass |
| catch `Exception`, Ctrl+C propagates | `pipeline.classify` | `grep -n "KeyboardInterrupt" src/para_files/pipeline.py` shows only the comment |
| LLM `..` / absolute rejected | `llm_classifier._sanitize_category` | traversal tests pass |
| bookstore keeps different content | `_handle_isbn_duplicate(identical=...)` | `test_keeps_duplicate_with_different_content` passes |

- [ ] **Step 4: Review the CHANGELOG block**

Run: `sed -n '/## \[Unreleased\]/,/^### Fixed$/p' CHANGELOG.md`
Expected: one `### Fixed (Stage 0 safety)` block with 6 bullets, followed by one `### Removed (Stage 0 safety)` block with 1 bullet, both above the older `### Fixed` section.

- [ ] **Step 5: Report**

Report the final test counts, the commit list (`git log --oneline docs/redesign-spec..HEAD`), and any deviations from this plan. Do not push and do not open a PR; the owner decides how to integrate the branch.
