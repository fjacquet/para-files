"""Run journal: one JSONL per run, flushed per line; owner-confirmed counts per kind."""

from __future__ import annotations

from datetime import datetime

import pytest

from para_files.core.journal import (
    Journal,
    confirmed_counts,
    is_undone,
    last_run_id,
    mark_undone,
    new_run_id,
    read_run,
    run_ids,
)
from tests.core_helpers import make_config


NOW = datetime(2026, 10, 11, 21, 30, 0)


def test_run_id_format_and_uniqueness(tmp_path):
    first = new_run_id(tmp_path, NOW)
    assert first == "20261011-213000"
    Journal(tmp_path, first).close()
    second = new_run_id(tmp_path, NOW)
    assert second == "20261011-213000-2"


def test_append_is_readable_immediately(tmp_path):
    journal = Journal(tmp_path, "r1")
    journal.append({"op": "move", "src": "a", "dst": "b"})
    assert read_run(tmp_path, "r1") == [{"run_id": "r1", "op": "move", "src": "a", "dst": "b"}]
    journal.close()


def test_journal_file_is_never_reused(tmp_path):
    Journal(tmp_path, "r1").close()
    with pytest.raises(FileExistsError):
        Journal(tmp_path, "r1")


def test_last_run_skips_undone(tmp_path):
    assert last_run_id(tmp_path) is None
    for run_id in ("20261011-100000", "20261011-110000"):
        Journal(tmp_path, run_id).close()
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
