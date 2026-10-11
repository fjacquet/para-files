"""Tests for scripts/build_golden.py (golden corpus sampling, spec §4.5)."""

from __future__ import annotations

import json
import os
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
    walk = golden.leaf_files(tmp_path / "big", set(), random.Random(1))  # noqa: S311 - sampling
    assert len(walk.files) == 3  # the walk stops after the first folder that reaches the cap
    assert walk.stopped_early


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
    walk = golden.leaf_files(root, set(), random.Random(1))  # noqa: S311 - sampling
    assert [path.name for path in walk.files] == ["cv0.pdf"]


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
    _touch(para, "4_Archives/5y_factures/2025/late.pdf")  # a folder the capped walk never reaches
    monkeypatch.setattr(golden, "WALK_CAP", 5)
    _rows, notes = _build(golden, para, config)
    assert any("walk stopped at 5 files" in note for note in notes)


def _leaves_config(tmp_path: Path, leaves: dict[str, dict[str, str]]):
    directory = tmp_path / "cfg-custom"
    directory.mkdir()
    (directory / "tree.yaml").write_text(yaml.safe_dump({"leaves": leaves}))
    return load_tree_config(directory)


def test_secret_and_hidden_names_are_filtered_in_the_walk(load_script, tmp_path):
    golden = load_script("build_golden")
    root = tmp_path / "leaf"
    for rel in ["cv.pdf", ".hidden.pdf", "s3-credentials.json", "~$draft.docx", "sub/ok.pdf"]:
        _touch(root, rel)
    _touch(root, "credentials/inside.pdf")
    walk = golden.leaf_files(root, set(), random.Random(1))  # noqa: S311 - sampling
    assert sorted(path.name for path in walk.files) == ["cv.pdf", "ok.pdf"]


def test_broken_links_and_fifos_are_not_sampled(load_script, tmp_path):
    golden = load_script("build_golden")
    root = tmp_path / "leaf"
    _touch(root, "cv.pdf")
    (root / "gone.pdf").symlink_to(tmp_path / "missing.pdf")
    os.mkfifo(root / "pipe.pdf")
    walk = golden.leaf_files(root, set(), random.Random(1))  # noqa: S311 - sampling
    assert [path.name for path in walk.files] == ["cv.pdf"]


def test_walk_that_reaches_the_cap_in_its_last_folder_is_not_truncated(load_script, tmp_path):
    golden = load_script("build_golden")
    _touch(tmp_path, "only/a.pdf")
    _touch(tmp_path, "only/b.pdf")
    golden.WALK_CAP = 2  # each load_script call is a fresh module
    walk = golden.leaf_files(tmp_path, set(), random.Random(1))  # noqa: S311 - sampling
    assert len(walk.files) == 2
    assert not walk.stopped_early


def test_unreadable_folder_is_noted_and_skipped(load_script, tmp_path):
    if os.geteuid() == 0:
        pytest.skip("root can read a chmod 000 folder")
    golden = load_script("build_golden")
    root = tmp_path / "leaf"
    _touch(root, "ok/a.pdf")
    _touch(root, "locked/b.pdf")
    locked = root / "locked"
    locked.chmod(0)
    try:
        walk = golden.leaf_files(root, set(), random.Random(1))  # noqa: S311 - sampling
    finally:
        locked.chmod(0o755)
    assert [path.name for path in walk.files] == ["a.pdf"]
    assert walk.unreadable == ["locked"]


def test_file_that_cannot_be_stat_ed_is_skipped(load_script, tmp_path):
    if os.geteuid() == 0:
        pytest.skip("root can stat files in a folder without search permission")
    golden = load_script("build_golden")
    root = tmp_path / "leaf"
    _touch(root, "ok/a.pdf")
    _touch(root, "noexec/b.pdf")
    (root / "noexec").chmod(0o444)  # listable but not searchable: stat() of its files fails
    try:
        walk = golden.leaf_files(root, set(), random.Random(1))  # noqa: S311 - sampling
    finally:
        (root / "noexec").chmod(0o755)
    assert [path.name for path in walk.files] == ["a.pdf"]


def test_symlinked_leaf_root_is_skipped_with_a_note(load_script, tmp_path):
    golden = load_script("build_golden")
    para = tmp_path / "PARA"
    _touch(para, "2_Areas/other/x.pdf")
    outside = tmp_path / "outside"
    _touch(outside, "y.pdf")
    (para / "2_Areas" / "linked").symlink_to(outside, target_is_directory=True)
    config = _leaves_config(
        tmp_path,
        {
            "linked": {"kind": "knowledge", "path": "2_Areas/linked", "describe": "Linked"},
            "other": {"kind": "knowledge", "path": "2_Areas/other", "describe": "Other"},
        },
    )
    rows, notes = _build(golden, para, config)
    assert {row["leaf"] for row in rows} == {"other"}
    assert "leaf linked: root is a symlink; skipped" in notes


def test_files_under_secret_named_folders_are_not_sampled_in_the_leaf(load_script, para, config):
    golden = load_script("build_golden")
    _touch(para, "2_Areas/carriere/secrets/key.pdf")
    rows, _notes = _build(golden, para, config)
    assert not any("secrets" in row["path"] for row in rows)


def test_capped_walk_note_is_absent_for_a_leaf_that_is_not_truncated(load_script, para, config):
    golden = load_script("build_golden")
    golden.WALK_CAP = 8  # career holds exactly 8 files in one folder
    _rows, notes = _build(golden, para, config)
    assert not any(note.startswith("leaf career: walk stopped") for note in notes)


def test_no_files_note_is_printed_before_the_refusal(load_script, config, tmp_path, capsys):
    golden = load_script("build_golden")
    empty = tmp_path / "EMPTY"
    empty.mkdir()
    argv = ["--para-root", str(empty), "--config-dir", str(tmp_path / "cfg")]
    with pytest.raises(SystemExit):
        golden.main([*argv, "--out", str(tmp_path / "golden.jsonl")])
    assert "leaf career: no files under 2_Areas/carriere" in capsys.readouterr().out


def test_config_dir_with_tilde_is_expanded(load_script, para, tmp_path):
    cfg = Path(os.environ["HOME"]) / "cfg"
    cfg.mkdir()
    leaves = {"career": {"kind": "knowledge", "path": "2_Areas/carriere", "describe": "C"}}
    (cfg / "tree.yaml").write_text(yaml.safe_dump({"leaves": leaves}))
    golden = load_script("build_golden")
    assert golden.main(["--para-root", str(para), "--config-dir", "~/cfg"]) == 0
    assert (cfg / "golden.jsonl").exists()


def test_a_leaf_sample_does_not_depend_on_other_leaves(load_script, para, config):
    """Leaves are sampled in sorted order; career comes before invoices, so career's new files
    must not reshuffle the invoices sample."""
    golden = load_script("build_golden")
    before, _ = _build(golden, para, config)
    for index in range(8):
        _touch(para, f"2_Areas/carriere/more{index}.pdf")
    after, _ = _build(golden, para, config)
    invoices = [row for row in before if row["leaf"] == "invoices"]
    assert invoices
    assert invoices == [row for row in after if row["leaf"] == "invoices"]


def test_out_inside_para_root_is_refused(load_script, para, config, tmp_path):
    golden = load_script("build_golden")
    argv = ["--para-root", str(para), "--config-dir", str(tmp_path / "cfg")]
    with pytest.raises(SystemExit):
        golden.main([*argv, "--out", str(para / "golden.jsonl")])
    assert not (para / "golden.jsonl").exists()


def test_leaf_under_a_bucket_symlinked_outside_para_is_not_sampled(load_script, tmp_path):
    golden = load_script("build_golden")
    para = tmp_path / "PARA"
    para.mkdir()
    outside = tmp_path / "outside"
    _touch(outside, "carriere/cv0.pdf")
    (para / "2_Areas").symlink_to(outside, target_is_directory=True)
    config = _leaves_config(
        tmp_path,
        {"career": {"kind": "knowledge", "path": "2_Areas/carriere", "describe": "Career"}},
    )
    rows, notes = _build(golden, para, config)
    assert rows == []
    assert "leaf career: resolves outside the PARA root; skipped" in notes
