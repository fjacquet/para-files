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
            "kind": "record",
            "retention": "5y",
            "path": "4_Archives/5y_factures",
            "describe": "Invoices",
        },
        "telecom": {
            "kind": "record",
            "retention": "5y",
            "path": "4_Archives/5y_factures/Telephonie",
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
    files = golden.leaf_files(tmp_path / "big", set(), random.Random(1))  # noqa: S311 - sampling
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


def test_symlinked_file_pointing_outside_the_leaf_is_not_sampled(load_script, tmp_path):
    golden = load_script("build_golden")
    root = tmp_path / "PARA" / "2_Areas" / "carriere"
    _touch(root, "cv0.pdf")
    outside = tmp_path / "outside.pdf"
    outside.write_text("x")
    (root / "link.pdf").symlink_to(outside)
    files = golden.leaf_files(root, set(), random.Random(1))  # noqa: S311 - sampling
    assert [path.name for path in files] == ["cv0.pdf"]


def test_main_rejects_missing_para_root_and_writes_nothing(load_script, config, tmp_path):
    golden = load_script("build_golden")
    out = tmp_path / "golden.jsonl"
    argv = ["--para-root", str(tmp_path / "missing"), "--config-dir", str(tmp_path / "cfg")]
    argv += ["--out", str(out)]
    with pytest.raises(SystemExit):
        golden.main(argv)
    assert not out.exists()


def test_main_refuses_to_overwrite_without_force(load_script, para, config, tmp_path):
    golden = load_script("build_golden")
    cfg_dir = tmp_path / "cfg"
    out = tmp_path / "golden.jsonl"
    out.write_text("my edits\n")
    argv = ["--para-root", str(para), "--config-dir", str(cfg_dir), "--out", str(out)]
    with pytest.raises(SystemExit):
        golden.main(argv)
    assert out.read_text() == "my edits\n"
    assert golden.main([*argv, "--force"]) == 0
    assert [json.loads(line) for line in out.read_text().splitlines()]


def test_main_refuses_to_write_when_nothing_is_sampled(load_script, config, tmp_path):
    golden = load_script("build_golden")
    empty = tmp_path / "EMPTY"
    empty.mkdir()
    out = tmp_path / "golden.jsonl"
    argv = ["--para-root", str(empty), "--config-dir", str(tmp_path / "cfg"), "--out", str(out)]
    with pytest.raises(SystemExit):
        golden.main(argv)
    assert not out.exists()


def test_capped_walk_is_reported_in_notes(load_script, para, config, monkeypatch):
    golden = load_script("build_golden")
    monkeypatch.setattr(golden, "WALK_CAP", 5)
    _rows, notes = _build(golden, para, config)
    assert any("walk stopped at 5 files" in note for note in notes)
