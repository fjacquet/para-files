"""Thema subjects and folders shipped as package data (spec §4.1, plan Stage 4 Task 1)."""

from __future__ import annotations

from importlib.resources import files

import pytest

from para_files.core.thema import SUBJECT_TO_THEMA, _folders, lookup_thema_code, thema_to_para_path


def test_the_table_is_a_package_resource():
    assert files("para_files").joinpath("data/thema_l1l2.json").is_file()


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


def test_a_blank_subject_gives_none():
    assert lookup_thema_code([""]) is None
    assert lookup_thema_code(["  "]) is None


@pytest.mark.parametrize("subject", ["Tax laws", "Ergonomics", "Trust law", "Startups"])
def test_a_keyword_inside_another_word_does_not_match(subject):
    assert lookup_thema_code([subject]) not in {"UTC", "UMX", "A"}


def test_unrelated_subjects_do_not_combine_into_a_language():
    assert lookup_thema_code(["Fiction", "Algorithms"]) != "UMX"


def test_keywords_with_symbols_match_whole():
    if "c++" in SUBJECT_TO_THEMA:
        assert lookup_thema_code(["C++"]) == SUBJECT_TO_THEMA["c++"]


def test_a_keyword_inside_a_phrase_still_matches():
    # "programming" comes before "python" in the map, so the first whole-word key wins.
    assert lookup_thema_code(["Python programming"]) == SUBJECT_TO_THEMA["programming"]
