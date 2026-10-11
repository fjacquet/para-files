"""The classify command exits 1 when at least one file failed to classify."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from para_files.main import app
from para_files.pipeline import ClassificationPipeline
from para_files.types import ClassificationResult, ClassificationSource, Confidence


runner = CliRunner()


@pytest.fixture
def failing_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Files named bad* raise during classification; every other file classifies."""

    def classify_file(self: ClassificationPipeline, file_path: Path) -> ClassificationResult:
        if file_path.name.startswith("bad"):
            msg = "boom"
            raise RuntimeError(msg)
        return ClassificationResult(
            category="0_Inbox",
            confidence=Confidence(value=0.9, source=ClassificationSource.RULES_ENGINE),
        )

    monkeypatch.setattr(ClassificationPipeline, "classify_file", classify_file)
    monkeypatch.setattr(
        ClassificationPipeline,
        "get_target_path",
        lambda self, result: Path("0_Inbox") / "file",
    )


def _touch(directory: Path, *names: str) -> list[str]:
    paths = []
    for name in names:
        path = directory / name
        path.write_text("content")
        paths.append(str(path))
    return paths


def test_exit_zero_when_every_file_classifies(tmp_path: Path, failing_pipeline: None) -> None:
    """No failures, no error exit."""
    files = _touch(tmp_path, "good1.txt", "good2.txt")
    result = runner.invoke(app, ["classify", *files, "--json"])
    assert result.exit_code == 0


def test_exit_one_when_one_of_several_files_fails_in_json(
    tmp_path: Path, failing_pipeline: None
) -> None:
    """JSON still lists every file, and the exit code reports the failure."""
    files = _touch(tmp_path, "good.txt", "bad.txt")
    result = runner.invoke(app, ["classify", *files, "--json"])
    assert result.exit_code == 1
    entries = json.loads(result.stdout[result.stdout.index("[") :])  # skip any log lines
    assert {e["source_file"].rsplit("/", 1)[-1] for e in entries if "error" in e} == {"bad.txt"}


def test_exit_one_when_single_file_fails_sequentially(
    tmp_path: Path, failing_pipeline: None
) -> None:
    """Sequential human output path (one file) exits 1 on failure."""
    files = _touch(tmp_path, "bad.txt")
    result = runner.invoke(app, ["classify", *files])
    assert result.exit_code == 1


def test_sequential_failure_prints_the_warning_line(tmp_path: Path, failing_pipeline: None) -> None:
    """The one-file human path names the failed file, as the parallel path does."""
    files = _touch(tmp_path, "bad.txt")
    result = runner.invoke(app, ["classify", *files])
    assert "⚠️ bad.txt: classification failed" in result.output


def test_exit_one_when_one_of_several_files_fails_in_parallel(
    tmp_path: Path, failing_pipeline: None
) -> None:
    """Parallel human output path (several files) exits 1 and keeps the per-file error line."""
    files = _touch(tmp_path, "good.txt", "bad.txt")
    result = runner.invoke(app, ["classify", *files])
    assert result.exit_code == 1
    assert "bad.txt: classification failed" in result.output
