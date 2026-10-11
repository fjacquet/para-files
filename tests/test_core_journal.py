"""Run journal: one JSONL per run, flushed per line; owner-confirmed counts per kind."""

from __future__ import annotations

import json
import os
from datetime import datetime

import pytest

from para_files.core.journal import (
    Journal,
    confirmed_counts,
    is_undone,
    journal_dir,
    last_run_id,
    mark_undone,
    new_run_id,
    owner_examples,
    read_run,
    run_ids,
)
from tests.core_helpers import make_config


NOW = datetime(2026, 10, 11, 21, 30, 0)


def _run_with_entry(state_dir, run_id):
    with Journal(state_dir, run_id) as journal:
        journal.append({"op": "move"})


def test_run_id_format_and_uniqueness(tmp_path):
    first = new_run_id(tmp_path, NOW)
    assert first == "20261011-213000"
    _run_with_entry(tmp_path, first)
    second = new_run_id(tmp_path, NOW)
    assert second == "20261011-213000-2"


def test_append_is_readable_immediately(tmp_path):
    journal = Journal(tmp_path, "r1")
    journal.append({"op": "move", "src": "a", "dst": "b"})
    assert read_run(tmp_path, "r1") == [{"run_id": "r1", "op": "move", "src": "a", "dst": "b"}]
    journal.close()


def test_journal_file_is_never_reused(tmp_path):
    _run_with_entry(tmp_path, "r1")
    with pytest.raises(FileExistsError):
        Journal(tmp_path, "r1")


def test_last_run_skips_undone(tmp_path):
    assert last_run_id(tmp_path) is None
    for run_id in ("20261011-100000", "20261011-110000"):
        _run_with_entry(tmp_path, run_id)
    assert run_ids(tmp_path) == ["20261011-100000", "20261011-110000"]
    assert last_run_id(tmp_path) == "20261011-110000"
    mark_undone(tmp_path, "20261011-110000")
    assert is_undone(tmp_path, "20261011-110000")
    assert last_run_id(tmp_path) == "20261011-100000"


def test_confirmed_counts(tmp_path):
    tree = make_config().tree
    with Journal(tmp_path, "r1") as journal:
        journal.append({"op": "move", "leaf": "archives_10y_travail", "decided_by": "owner"})
        journal.append({"op": "move", "leaf": "resources_it", "decided_by": "owner"})
        journal.append({"op": "move", "leaf": "archives_10y_travail", "decided_by": "auto"})
        journal.append({"op": "trash", "leaf": "archives_10y_travail", "decided_by": "owner"})
        journal.append({"op": "move", "leaf": "gone_leaf", "decided_by": "owner"})
    with Journal(tmp_path, "r2") as journal:
        journal.append({"op": "move", "leaf": "archives_10y_travail", "decided_by": "owner"})
    mark_undone(tmp_path, "r2")
    assert confirmed_counts(tmp_path, tree) == {"record": 1, "knowledge": 1}


def test_first_append_fsyncs_the_directory_and_the_line(tmp_path, monkeypatch):
    calls: list[int] = []
    real_fsync = os.fsync

    def recording_fsync(fd: int) -> None:
        calls.append(fd)
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", recording_fsync)
    journal = Journal(tmp_path, "r1")
    assert calls == []
    journal.append({"op": "move"})
    assert len(calls) == 2
    journal.close()


def test_journal_without_entries_leaves_no_file(tmp_path):
    journal = Journal(tmp_path, "r1")
    journal.close()
    assert not journal.path.exists()
    assert run_ids(tmp_path) == []
    assert last_run_id(tmp_path) is None


def test_read_run_ignores_torn_final_line(tmp_path):
    journal = Journal(tmp_path, "r1")
    journal.append({"op": "move", "src": "a"})
    journal.close()
    with journal.path.open("a", encoding="utf-8") as handle:
        handle.write('{"op": "mo')
    assert read_run(tmp_path, "r1") == [{"run_id": "r1", "op": "move", "src": "a"}]


def test_read_run_raises_on_malformed_middle_line(tmp_path):
    journal = Journal(tmp_path, "r1")
    journal.append({"op": "move", "src": "a"})
    journal.close()
    with journal.path.open("a", encoding="utf-8") as handle:
        handle.write('{"op": "mo\n{"run_id": "r1", "op": "move"}\n')
    with pytest.raises(json.JSONDecodeError):
        read_run(tmp_path, "r1")


def test_run_ids_sort_suffixes_numerically(tmp_path):
    base = "20261011-213000"
    for run_id in (base, f"{base}-2", f"{base}-10"):
        _run_with_entry(tmp_path, run_id)
    assert run_ids(tmp_path) == [base, f"{base}-2", f"{base}-10"]
    assert last_run_id(tmp_path) == f"{base}-10"


def test_append_cannot_override_run_id(tmp_path):
    with Journal(tmp_path, "r1") as journal:
        journal.append({"run_id": "other", "op": "x"})
    assert read_run(tmp_path, "r1") == [{"run_id": "r1", "op": "x"}]


def test_owner_confirmations_count_as_labels(tmp_path):
    tree = make_config().tree
    with Journal(tmp_path, "r1") as journal:
        journal.append({"op": "confirm", "leaf": "resources_it", "decided_by": "owner"})
        journal.append({"op": "confirm", "leaf": "resources_it", "decided_by": "auto"})
    assert confirmed_counts(tmp_path, tree) == {"knowledge": 1}


def test_owner_examples_newest_first_one_per_file(tmp_path):
    from para_files.core.journal import Journal, owner_examples

    state = tmp_path / "state"

    def run(run_id, entries):
        with Journal(state, run_id) as journal:
            for entry in entries:
                journal.append(entry)

    run(
        "20260101-000000",
        [
            {
                "op": "move",
                "src": "/r/0_Inbox/a.pdf",
                "dst": "/r/x/a.pdf",
                "sha256": "a",
                "leaf": "archives_5y_factures",
                "proposed_leaf": "resources_docs",
                "decided_by": "owner",
            },
            {
                "op": "move",
                "src": "/r/0_Inbox/auto.pdf",
                "dst": "/r/x/auto.pdf",
                "sha256": "z",
                "leaf": "archives_5y_factures",
                "proposed_leaf": "archives_5y_factures",
                "decided_by": "auto",
            },
        ],
    )
    run(
        "20260102-000000",
        [
            {
                "op": "move",
                "src": "/r/0_Inbox/b.pdf",
                "dst": "/r/y/b.pdf",
                "sha256": "b",
                "leaf": "archives_10y_banques",
                "proposed_leaf": "archives_10y_banques",
                "decided_by": "owner",
            },
            {
                "op": "move",
                "src": "/r/0_Inbox/a.pdf",
                "dst": "/r/z/a.pdf",
                "sha256": "a",
                "leaf": "archives_10y_banques",
                "proposed_leaf": "archives_5y_factures",
                "decided_by": "owner",
            },
        ],
    )
    examples = owner_examples(state, make_config().tree)
    assert [(e.name, e.leaf_id, e.proposed) for e in examples] == [
        ("a.pdf", "archives_10y_banques", "archives_5y_factures"),
        ("b.pdf", "archives_10y_banques", "archives_10y_banques"),
    ]


def _owner_move(src: str, leaf: str = "archives_10y_banques") -> dict[str, str]:
    return {"op": "move", "src": src, "sha256": src, "leaf": leaf, "decided_by": "owner"}


def test_undone_run_gives_no_examples(tmp_path):
    tree = make_config().tree
    with Journal(tmp_path, "20260101-000000") as journal:
        journal.append(_owner_move("/r/0_Inbox/a.pdf"))
    mark_undone(tmp_path, "20260101-000000")
    assert owner_examples(tmp_path, tree) == []


def _write_raw_run(state_dir, run_id, lines):
    directory = journal_dir(state_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{run_id}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_corrupt_middle_line_skips_only_that_run(tmp_path):
    tree = make_config().tree
    good = json.dumps(_owner_move("/r/0_Inbox/a.pdf"))
    _write_raw_run(tmp_path, "20260101-000000", [good, "{not json", good])
    with Journal(tmp_path, "20260102-000000") as journal:
        journal.append(_owner_move("/r/0_Inbox/b.pdf"))
    examples = owner_examples(tmp_path, tree)
    assert [e.name for e in examples] == ["b.pdf"]


def test_non_object_line_is_skipped(tmp_path):
    tree = make_config().tree
    _write_raw_run(tmp_path, "20260101-000000", ["[1, 2]", json.dumps(_owner_move("/r/a.pdf"))])
    with Journal(tmp_path, "20260102-000000") as journal:
        journal.append(_owner_move("/r/b.pdf"))
    assert [e.name for e in owner_examples(tmp_path, tree)] == ["b.pdf", "a.pdf"]


def test_corrupt_journal_does_not_crash_confirmed_counts(tmp_path):
    tree = make_config().tree
    _write_raw_run(
        tmp_path,
        "20260101-000000",
        [
            json.dumps({"op": "move", "leaf": "archives_10y_travail", "decided_by": "owner"}),
            "{not json",
            json.dumps({"op": "move", "leaf": "archives_10y_travail", "decided_by": "owner"}),
        ],
    )
    with Journal(tmp_path, "20260102-000000") as journal:
        journal.append({"op": "move", "leaf": "resources_it", "decided_by": "owner"})
    assert confirmed_counts(tmp_path, tree) == {"knowledge": 1}


def test_entry_without_src_is_skipped(tmp_path):
    tree = make_config().tree
    with Journal(tmp_path, "20260101-000000") as journal:
        journal.append({"op": "confirm", "leaf": "archives_10y_banques", "decided_by": "owner"})
    assert owner_examples(tmp_path, tree) == []


def test_non_utf8_journal_does_not_crash(tmp_path):
    tree = make_config().tree
    directory = journal_dir(tmp_path)
    directory.mkdir(parents=True, exist_ok=True)
    good = json.dumps(_owner_move("/r/a.pdf")).encode("utf-8")
    (directory / "20260101-000000.jsonl").write_bytes(good + b"\n\xff\xfe\n" + good + b"\n")
    with Journal(tmp_path, "20260102-000000") as journal:
        journal.append(_owner_move("/r/b.pdf"))
    assert [e.name for e in owner_examples(tmp_path, tree)] == ["b.pdf"]
