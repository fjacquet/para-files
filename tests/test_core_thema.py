"""Thema subjects and folders shipped as package data (spec §4.1, plan Stage 4 Task 1)."""

from __future__ import annotations

from importlib.resources import files

from para_files.core.thema import _folders, lookup_thema_code, thema_to_para_path


def test_the_table_is_a_package_resource():
    assert files("para_files.data").joinpath("thema_l1l2.json").is_file()


def test_the_table_holds_only_level_one_and_two_codes():
    table = _folders()
    assert len(table) == 234
    assert all(1 <= len(code) <= 2 for code in table)
    assert all(name.startswith(f"{code}_") for code, name in table.items())


def test_the_most_specific_subject_wins():
    assert lookup_thema_code(["Computing", "Python"]) == "UMX"


def test_unknown_or_no_subjects_give_none():
    assert lookup_thema_code([]) is None
    assert lookup_thema_code(["qqqq"]) is None


def test_a_deep_code_uses_its_level_one_and_two_folders():
    table = _folders()
    assert thema_to_para_path("UMX") == f"3_Resources/livres/{table['U']}/{table['UM']}"


def test_a_level_one_code_gives_one_folder():
    assert thema_to_para_path("U") == f"3_Resources/livres/{_folders()['U']}"


def test_an_unknown_code_gives_the_library_root():
    assert thema_to_para_path("?") == "3_Resources/livres"


def test_medieval_history_files_under_history():
    table = _folders()
    assert lookup_thema_code(["medieval history"]) == "NH"
    assert thema_to_para_path("NH") == f"3_Resources/livres/{table['N']}/{table['NH']}"
