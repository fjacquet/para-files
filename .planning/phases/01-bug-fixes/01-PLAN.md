---
phase: phase-1-bug-fixes
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/para_files/utils/file_utils.py
  - src/para_files/config.py
  - src/para_files/encoders/mlx_encoder.py
  - tests/test_file_utils.py
  - tests/test_config.py
  - tests/test_encoders.py
autonomous: true
requirements:
  - BUG-01
  - BUG-02
  - BUG-03

must_haves:
  truths:
    - "A file named document.PDF is classified correctly, not skipped"
    - "OCR rename only triggers when confidence exceeds 0.7"
    - "Technical or symbol-dense text receives a real embedding, not a zero vector"
  artifacts:
    - path: "src/para_files/utils/file_utils.py"
      provides: "Normalized lowercase extension in FileMetadata"
      contains: "extension=file_path.suffix.lower()"
    - path: "src/para_files/config.py"
      provides: "Raised OCR rename confidence threshold"
      contains: "default=0.7"
    - path: "src/para_files/encoders/mlx_encoder.py"
      provides: "Per-text adaptive truncation fallback"
      contains: "encode_single"
    - path: "tests/test_file_utils.py"
      provides: "Extension case normalization tests"
      exports: ["test_extension_stored_lowercase"]
    - path: "tests/test_config.py"
      provides: "OCR rename confidence default test"
      exports: ["test_ocr_rename_min_confidence_default"]
    - path: "tests/test_encoders.py"
      provides: "Zero-vector guard test"
      exports: ["test_no_zero_vector_for_dense_text"]
  key_links:
    - from: "src/para_files/utils/file_utils.py"
      to: "src/para_files/types.py FileMetadata.extension"
      via: "extension=file_path.suffix.lower() in extract_file_metadata"
      pattern: "extension=file_path\\.suffix\\.lower\\(\\)"
    - from: "src/para_files/encoders/mlx_encoder.py"
      to: "self._model.encode"
      via: "per-text retry loop before final fallback"
      pattern: "encode_single|aggressive"
---

<objective>
Fix three confirmed bugs in the classification pipeline: uppercase extension
blindness (BUG-01), an overly lenient OCR rename trigger (BUG-02), and a
zero-vector fallback for high-density text in the MLX encoder (BUG-03).

Purpose: The pipeline must handle real-world input — mixed-case filenames,
bank statement headers, and source-code files — correctly without silent
fallbacks that send files to the wrong category or corrupt semantic routing.

Output: Three targeted source edits and matching tests. No behavior changes
outside the stated bugs.
</objective>

<execution_context>
@/Users/fjacquet/.claude/get-shit-done/workflows/execute-plan.md
@/Users/fjacquet/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@/Users/fjacquet/Projects/para-files/.planning/ROADMAP.md
@/Users/fjacquet/Projects/para-files/src/para_files/utils/file_utils.py
@/Users/fjacquet/Projects/para-files/src/para_files/pipeline.py
@/Users/fjacquet/Projects/para-files/src/para_files/config.py
@/Users/fjacquet/Projects/para-files/src/para_files/encoders/mlx_encoder.py
@/Users/fjacquet/Projects/para-files/tests/test_file_utils.py
@/Users/fjacquet/Projects/para-files/tests/test_config.py
@/Users/fjacquet/Projects/para-files/tests/test_encoders.py
</context>

<tasks>

<task type="auto">
  <name>Task 1 (BUG-01): Normalize extension to lowercase at FileMetadata construction</name>
  <files>
    src/para_files/utils/file_utils.py
    tests/test_file_utils.py
  </files>
  <action>
In `src/para_files/utils/file_utils.py`, `extract_file_metadata` (around line 172),
change the `FileMetadata` constructor call from:

    extension=file_path.suffix,

to:

    extension=file_path.suffix.lower(),

This is the single authoritative construction point for `FileMetadata.extension`.
All downstream consumers — `rules_engine.py` (line 129), `book_detector.py`
(line 500), `read_content_preview` (line 204) — already call `.lower()` when
they use the extension, so this change is additive and safe.

The pipeline's OCR rename check at `pipeline.py:267` already uses
`file_path.suffix.lower()` on the live path (not from metadata), so it is
correct and should NOT be changed.

Do NOT touch `read_content_preview` — it already uses `file_path.suffix.lower()`
at line 204 because it receives the raw path, not a FileMetadata object.

In `tests/test_file_utils.py`, add a test class `TestExtensionNormalization`
with the following tests:

    def test_extension_stored_lowercase(tmp_path):
        """FileMetadata.extension is always lowercase regardless of filename case."""
        f = tmp_path / "document.PDF"
        f.write_bytes(b"%PDF-1.4 fake")
        meta = extract_file_metadata(f, extract_exif=False)
        assert meta.extension == ".pdf"

    def test_extension_lowercase_epub(tmp_path):
        f = tmp_path / "book.EPUB"
        f.write_bytes(b"PK fake epub")
        meta = extract_file_metadata(f, extract_exif=False)
        assert meta.extension == ".epub"

    def test_extension_lowercase_chm(tmp_path):
        f = tmp_path / "manual.CHM"
        f.write_bytes(b"ITSF fake chm")
        meta = extract_file_metadata(f, extract_exif=False)
        assert meta.extension == ".chm"

    def test_mixed_case_extension(tmp_path):
        f = tmp_path / "file.TxT"
        f.write_text("hello")
        meta = extract_file_metadata(f, extract_exif=False)
        assert meta.extension == ".txt"
  </action>
  <verify>
    uv run pytest tests/test_file_utils.py::TestExtensionNormalization -v
  </verify>
  <done>
    All four new tests pass. `FileMetadata.extension` is lowercase for .PDF,
    .EPUB, .CHM, and mixed-case inputs.
  </done>
</task>

<task type="auto">
  <name>Task 2 (BUG-02): Raise OCR rename min_confidence default from 0.3 to 0.7</name>
  <files>
    src/para_files/config.py
    tests/test_config.py
  </files>
  <action>
In `src/para_files/config.py`, `OCRRenameConfig` class (around line 184),
change the `min_confidence` field default:

    min_confidence: float = Field(
        default=0.3,   # BEFORE
        ...
    )

to:

    min_confidence: float = Field(
        default=0.7,   # AFTER
        ...
    )

Do NOT change the `ge=0.0` / `le=1.0` validators or the description string.

In `tests/test_config.py`, add a test class `TestOCRRenameConfig` with:

    def test_ocr_rename_min_confidence_default():
        """Default min_confidence is 0.7 — only high-confidence metadata triggers rename."""
        from para_files.config import OCRRenameConfig
        cfg = OCRRenameConfig()
        assert cfg.min_confidence == 0.7

    def test_ocr_rename_min_confidence_accepts_low_value():
        """Users can override to a lower threshold explicitly."""
        from para_files.config import OCRRenameConfig
        cfg = OCRRenameConfig(min_confidence=0.3)
        assert cfg.min_confidence == 0.3

    def test_ocr_rename_min_confidence_rejects_out_of_range():
        """Values outside [0.0, 1.0] are rejected by pydantic."""
        from pydantic import ValidationError
        from para_files.config import OCRRenameConfig
        with pytest.raises(ValidationError):
            OCRRenameConfig(min_confidence=1.5)
  </action>
  <verify>
    uv run pytest tests/test_config.py::TestOCRRenameConfig -v
  </verify>
  <done>
    Three new tests pass. `OCRRenameConfig().min_confidence == 0.7`. A bank
    statement header text that scores below 0.7 will not trigger a rename.
  </done>
</task>

<task type="auto">
  <name>Task 3 (BUG-03): Replace zero-vector fallback with per-text aggressive truncation in MLXEncoder</name>
  <files>
    src/para_files/encoders/mlx_encoder.py
    tests/test_encoders.py
  </files>
  <action>
In `src/para_files/encoders/mlx_encoder.py`, replace the existing `__call__`
method's inner exception handler (lines 86-98) with a per-text retry loop.

Current code (lines 83-98):

    try:
        embeddings_array = self._model.encode(truncated_texts)
    except IndexError as e:
        logger.warning("Text exceeds token limit, using fallback truncation: {}", e)
        shorter_texts = [t[: self.fallback_chars] for t in texts]
        try:
            embeddings_array = self._model.encode(shorter_texts)
        except IndexError:
            logger.exception("Text still exceeds token limit after truncation")
            return [[0.0] * 768 for _ in texts]

Replace with this strategy (preserve the class fields `max_chars` and
`fallback_chars`; add a new `_encode_single` helper method and update
`__call__`):

Add private helper method `_encode_single` to the class:

    def _encode_single(self, text: str) -> list[float]:
        """Encode a single text with progressive truncation on IndexError.

        Tries progressively shorter truncations (fallback_chars, 400, 200)
        before giving up and returning a mean-pooled partial result.
        Never returns a zero vector — uses the shortest encodable prefix instead.

        Args:
            text: Text to encode.

        Returns:
            Embedding vector as a list of floats.
        """
        candidates = [
            text[: self.fallback_chars],
            text[:400],
            text[:200],
        ]
        for candidate in candidates:
            try:
                arr = self._model.encode([candidate])
                return arr.tolist()[0]
            except IndexError:
                continue
        # Absolute last resort: encode just the first sentence or 100 chars
        # This should never fail because 100 chars << token limit
        last_chance = text[:100] if text else "document"
        try:
            arr = self._model.encode([last_chance])
            return arr.tolist()[0]
        except Exception:  # noqa: BLE001
            logger.exception("MLX encoder failed on 100-char text — model may be broken")
            # Only now do we return a zero vector, and we log it as an error
            dim = getattr(self._model, "dims", 768)
            return [0.0] * dim

Update the `__call__` method to replace the batch-level fallback with per-text
retry. The new `__call__` body (inside the `try` / `except IndexError` block):

    try:
        embeddings_array = self._model.encode(truncated_texts)
    except IndexError as e:
        # Batch failed — likely one problematic text. Retry per-text.
        logger.warning(
            "Batch encode failed (token limit), retrying per-text: {}", e
        )
        return [self._encode_single(t) for t in texts]

    # Convert to list of lists
    embeddings: list[list[float]] = embeddings_array.tolist()
    return embeddings

Remove the nested `try/except IndexError` and the `return [[0.0] * 768 ...]`
line entirely. The zero-vector path is now only reachable inside `_encode_single`
as a logged error, never silently.

Also update the `encode_batch` method to delegate to `self(batch)` — it already
does so, no change needed there.

In `tests/test_encoders.py`, add a test class `TestMLXEncoderZeroVectorGuard`:

    @patch("para_files.encoders.mlx_encoder.EmbeddingModel.from_registry")
    def test_no_zero_vector_for_dense_text(mock_from_registry):
        """Per-text retry must not return a zero vector when a shorter prefix succeeds."""
        mock_model = MagicMock()
        call_count = 0

        def side_effect(texts):
            nonlocal call_count
            call_count += 1
            # First call (batch) raises IndexError
            # Subsequent calls (per-text via _encode_single) succeed with 200-char prefix
            if call_count == 1:
                raise IndexError("sequence length exceeds maximum")
            import numpy as np
            return np.array([[0.1] * 768 for _ in texts])

        mock_model.encode.side_effect = side_effect
        mock_from_registry.return_value = mock_model

        encoder = MLXEncoder()
        encoder._model = mock_model
        encoder._loaded = True

        dense_text = "x" * 2000  # Simulates symbol-dense / token-heavy text
        result = encoder([dense_text])

        assert len(result) == 1
        assert result[0] != [0.0] * 768, "Must not return zero vector when retry succeeds"
        assert any(v != 0.0 for v in result[0])

    @patch("para_files.encoders.mlx_encoder.EmbeddingModel.from_registry")
    def test_encode_single_progressive_truncation(mock_from_registry):
        """_encode_single tries shorter and shorter prefixes on IndexError."""
        mock_model = MagicMock()
        attempts = []

        def side_effect(texts):
            attempts.append(len(texts[0]))
            if len(texts[0]) > 200:
                raise IndexError("too long")
            import numpy as np
            return np.array([[0.5] * 768])

        mock_model.encode.side_effect = side_effect
        mock_from_registry.return_value = mock_model

        encoder = MLXEncoder()
        encoder._model = mock_model
        encoder._loaded = True

        result = encoder._encode_single("a" * 1000)

        # Must have tried multiple lengths before succeeding at 200
        assert len(attempts) >= 2
        assert result != [0.0] * 768
  </action>
  <verify>
    uv run pytest tests/test_encoders.py::TestMLXEncoderZeroVectorGuard -v
    uv run mypy src/para_files/encoders/mlx_encoder.py
  </verify>
  <done>
    Both new tests pass. mypy reports no new errors. The zero-vector path in
    `__call__` is removed. A 2000-char symbol-dense input receives a non-zero
    embedding by retrying with progressively shorter prefixes.
  </done>
</task>

</tasks>

<verification>
After all three tasks complete, run the full test suite and linters:

    uv run pytest tests/test_file_utils.py tests/test_config.py tests/test_encoders.py -v
    uv run pytest --tb=short
    uv run ruff check src/ tests/
    uv run ruff format --check src/ tests/
    uv run mypy src/

Expected outcome: all pre-existing tests continue to pass, all nine new tests
pass, no new mypy or ruff errors.
</verification>

<success_criteria>
1. `uv run pytest` exits 0 with all new tests passing.
2. A file named `document.PDF` — when passed through `extract_file_metadata` —
   returns `metadata.extension == ".pdf"` (verified by TestExtensionNormalization).
3. `OCRRenameConfig().min_confidence == 0.7` — a bank statement header scoring
   below 0.7 does not trigger a rename (verified by TestOCRRenameConfig).
4. An MLXEncoder with a mocked model that raises IndexError on the first batch
   call returns a non-zero embedding after per-text retry
   (verified by TestMLXEncoderZeroVectorGuard).
5. No ruff or mypy errors introduced.
</success_criteria>

<output>
After completion, create `.planning/phases/phase-1-bug-fixes/phase-1-bug-fixes-01-SUMMARY.md`
with a brief summary of what was changed, the files modified, and which tests
were added for each bug.
</output>
