# Phase 10: Classification Accuracy + Move Safety - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix three classes of correctness bugs:
1. Book detector false positives on French financial documents (IBAN-containing PDFs misidentified as books)
2. Silent YAML misconfiguration in `personal_file_tree.yaml` (errors swallowed, not surfaced)
3. Unsafe batch move operations (no rollback on partial failure, no pre-flight permission check)

Also correct the semantic routing of unclassifiable files from `0_Inbox` to `6_unclassified`.

This phase does NOT add new classifier signals, new CLI commands, or new file format support.

</domain>

<decisions>
## Implementation Decisions

### Book Detector False Positive Strategy
- `is_financial_document()` takes **absolute precedence**: if it returns `True`, exit book classification immediately — do not proceed to ISBN signal checking or Thema scoring
- The existing financial pattern list (IBAN, CH/FR IBAN formats, bank/compte/virement keywords) is sufficient; no new patterns needed
- If `is_financial_document()` returns `True`, `classify()` returns `None` (no book match) so the next classifier in the pipeline gets the file
- Test coverage must include: IBAN-containing PDF with no real ISBN, French bank statement with ISBN-like reference numbers, document that passes financial check and then correctly matches a real ISBN (should still classify as book)
- ACC-01 and ACC-02 both addressed by this approach

### Rollback Behavior on Partial Batch Failure
- Track every completed move as a `(source, destination)` tuple in an ordered list before moving each file
- On first failure: stop immediately, do NOT continue with remaining files
- Present to user: "N files moved successfully. Move failed on file X. Roll back the N completed moves?"
- Rollback is offered as an option (not automatic) so user can decide if partial progress is acceptable
- Rollback moves each completed file back to its original location, logging each reversal
- Rollback failures (e.g., destination already deleted) are logged as warnings, not hard errors
- Dry-run mode: show rollback plan without executing
- MOV-01 addressed by this approach

### Destination Permission Validation
- Before starting any batch move, probe the destination directory with `os.access(dest, os.W_OK)`
- If permission check fails: reject the entire batch immediately with a clear error message showing the path and what permission is missing
- Validation happens per unique destination directory (not per file — avoid redundant checks)
- Validation must run BEFORE the first file is moved (pre-flight, not mid-flight)
- MOV-02 addressed by this approach

### YAML Reference Tree Validation
- Add Pydantic models (`ReferenceTreeModel`, `RoutingRuleModel`) wrapping the YAML structure
- Validate at load time in `reference_tree.py` — fail immediately if the structure is invalid
- Error message must include: file path, the failing field or key, and what was expected (type, required keys)
- If YAML is malformed or fails Pydantic validation: raise `ValueError` or a custom `ReferenceTreeError` at startup, not silently log and continue
- Minimum validation: required top-level keys present, `routing_rules` is a list, each rule has required fields (`pattern`, `destination`)
- ACC-04 addressed by this approach

### Unclassifiable File Routing
- Pipeline default changes from `"0_Inbox"` to `"6_unclassified"` as a module-level constant (e.g., `DEFAULT_UNCLASSIFIED_CATEGORY = "6_unclassified"`)
- `0_Inbox` meaning: user-placed files awaiting triage — pipeline should never route there autonomously
- `6_unclassified` meaning: pipeline ran but no classifier could match — requires human review
- The `scan` and `inbox` CLI commands should include unclassified count in their summary output
- ACC-05 addressed by this approach

### Rules Engine Test Coverage
- Add tests for date extraction edge cases: year 1989 (pre-ISBN), year 2041 (future — could trigger false positives), pattern shadowing (one rule's pattern substring of another)
- ACC-03 addressed by these additional tests

### Claude's Discretion
- Exact Pydantic model field names and structure for `ReferenceTreeModel`
- Whether to use a custom exception class (`ReferenceTreeError`) or plain `ValueError`
- Exact format of the rollback confirmation prompt (CLI text wording)
- Whether to add `6_unclassified` to the PARA folder creation logic in `init` command

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements are fully captured in decisions above and in REQUIREMENTS.md.

### Requirements
- `.planning/REQUIREMENTS.md` — ACC-01 through ACC-05, MOV-01, MOV-02 (classification accuracy and move safety requirements)

### Existing Code to Read Before Modifying
- `src/para_files/classifiers/book_detector.py` — `is_financial_document()` function (lines ~159+), `FINANCIAL_PATTERNS`, `DETECTION_THRESHOLD`, `classify()` method
- `src/para_files/mover.py` — `move()` function and `move_classified_file()` — understand current move flow before adding rollback
- `src/para_files/reference_tree.py` — current YAML loading logic to understand what needs Pydantic wrapping
- `src/para_files/pipeline.py` — `classify()` default return (lines ~350-353) for the `6_unclassified` routing change

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `is_financial_document(content, filename)` in `book_detector.py`: already implemented with IBAN detection, French patterns, minimum match threshold — just needs to be called earlier (before ISBN check)
- `FINANCIAL_PATTERNS` list: comprehensive, covers IBAN, Swiss/French patterns, bank keywords
- `move()` in `mover.py`: existing move logic — add tracking list and permission pre-check to it
- Pydantic pattern: already used in `config.py` for all config classes — same approach for YAML models

### Established Patterns
- Fail-fast on startup validated in Phase 8 — `ReferenceTreeError` should follow the same pattern as `PlaceholderError`
- `loguru` logger for all log output (no stdlib logging)
- `pytest` with `tmp_path` fixture for file system tests
- Mypy strict mode — all new code must be fully typed

### Integration Points
- `pipeline.py` line ~351: change `"0_Inbox"` default to `"6_unclassified"` constant
- `book_detector.py` `classify()`: add `is_financial_document()` call at entry, before ISBN extraction loop
- `mover.py` `move()` or caller: add permission pre-flight + completed-moves tracker
- `reference_tree.py` loader: wrap parsed YAML in Pydantic model before use

</code_context>

<specifics>
## Specific Ideas

- The French financial document false positive is the most user-visible bug — IBAN patterns in French bank statements (format: `FR76 XXXX XXXX XXXX`) are being picked up as ISBN-like sequences
- "Stop on first failure + offer rollback" mirrors how database transactions work — stop and give user control rather than auto-deciding
- `6_unclassified` should eventually become a monitored folder the user reviews periodically

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-classification-accuracy-move-safety*
*Context gathered: 2026-03-22 via --auto mode*
