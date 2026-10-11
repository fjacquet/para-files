"""Tests for the canonical tree, rules and issuers loader (spec §4.1)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import get_args

import pytest
import yaml

from para_files.core.tree import (
    RETENTION_PREFIX,
    Retention,
    TreeError,
    load_tree_config,
    validation_warnings,
)


EXAMPLES = Path(__file__).parent.parent / "examples"


def _leaf(**overrides):
    leaf = {"kind": "knowledge", "path": "2_Areas/carriere", "describe": "Career"}
    leaf.update(overrides)
    return leaf


def _write(directory: Path, leaves: dict, rules=None, issuers=None) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "tree.yaml").write_text(yaml.safe_dump({"leaves": leaves}))
    if rules is not None:
        (directory / "rules.yaml").write_text(yaml.safe_dump({"rules": rules}))
    if issuers is not None:
        (directory / "issuers.yaml").write_text(yaml.safe_dump({"issuers": issuers}))
    return directory


class TestExamples:
    def test_examples_load_cleanly(self):
        cfg = load_tree_config(EXAMPLES)
        kinds = {leaf.kind for leaf in cfg.tree.leaves.values()}
        assert kinds == {"record", "library", "media", "knowledge"}
        expected = ["leaf 'identity_papers': no rule or issuer points to it"]
        assert validation_warnings(cfg) == expected


class TestLeafRules:
    @pytest.mark.parametrize(
        ("leaf", "message"),
        [
            (_leaf(path="0_Inbox/x"), "1_-4_ bucket"),
            (_leaf(path="2_Areas/a/b/c"), "deeper than"),
            (_leaf(path="2_Areas/carriere "), "padded"),
            (_leaf(kind="record"), "record leaves need a retention"),
            (_leaf(retention="5y"), "record leaves need a retention"),
            (
                _leaf(kind="record", retention="5y", path="4_Archives/10y_banques"),
                "requires 4_Archives/5y_",
            ),
            (_leaf(subkey="{technology}"), "subkey must be"),
            (_leaf(subkey="{year}/{month}/{issuer}"), "subkey must be"),
            (_leaf(subkey="{year}/{year}"), "subkey must be"),
            (_leaf(colour="blue"), "Extra inputs are not permitted"),
        ],
    )
    def test_invalid_leaf_is_rejected(self, tmp_path, leaf, message):
        _write(tmp_path, {"bad": leaf})
        with pytest.raises(TreeError, match=message):
            load_tree_config(tmp_path)

    def test_permanent_record_may_live_outside_archives(self, tmp_path):
        leaf = _leaf(kind="record", retention="permanent", path="2_Areas/Officiel")
        _write(tmp_path, {"papers": leaf})
        assert load_tree_config(tmp_path).tree.leaves["papers"].retention == "permanent"

    def test_leaf_ids_must_be_snake_case(self, tmp_path):
        _write(tmp_path, {"Career": _leaf()})
        with pytest.raises(TreeError, match="snake_case"):
            load_tree_config(tmp_path)

    def test_leaf_id_with_trailing_newline_is_rejected(self, tmp_path):
        _write(tmp_path, {"career\n": _leaf()})
        with pytest.raises(TreeError, match="snake_case"):
            load_tree_config(tmp_path)


class TestYamlSyntax:
    def test_malformed_yaml_is_a_tree_error_naming_the_file(self, tmp_path):
        (tmp_path / "tree.yaml").write_text("leaves: [unclosed\n")
        with pytest.raises(TreeError, match=r"tree\.yaml: invalid YAML"):
            load_tree_config(tmp_path)

    def test_missing_tree_yaml_is_a_tree_error_naming_the_file(self, tmp_path):
        with pytest.raises(TreeError, match=re.escape(str(tmp_path / "tree.yaml"))):
            load_tree_config(tmp_path)

    def test_non_utf8_file_is_a_tree_error_naming_the_file(self, tmp_path):
        (tmp_path / "tree.yaml").write_bytes(b"leaves:\n  career: \xff\xfe\n")
        with pytest.raises(TreeError, match=re.escape(str(tmp_path / "tree.yaml"))):
            load_tree_config(tmp_path)

    @pytest.mark.parametrize("content", ["[]\n", "just a string\n"])
    def test_non_mapping_rules_file_is_rejected(self, tmp_path, content):
        _write(tmp_path, {"career": _leaf()})
        (tmp_path / "rules.yaml").write_text(content)
        with pytest.raises(TreeError, match=r"rules\.yaml: expected a mapping"):
            load_tree_config(tmp_path)

    def test_empty_rules_file_means_no_rules(self, tmp_path):
        _write(tmp_path, {"career": _leaf()})
        (tmp_path / "rules.yaml").write_text("")
        assert load_tree_config(tmp_path).rules.rules == ()

    def test_validation_errors_name_the_file(self, tmp_path):
        _write(tmp_path, {"bad": _leaf(colour="blue")})
        with pytest.raises(
            TreeError, match=r"(?s)tree\.yaml: 1 validation error.*Extra inputs are not permitted"
        ):
            load_tree_config(tmp_path)


class TestReferences:
    def test_rule_with_unknown_leaf_is_rejected(self, tmp_path):
        rules = [{"name": "cv", "leaf": "nope", "globs": ["*cv*"]}]
        _write(tmp_path, {"career": _leaf()}, rules=rules)
        with pytest.raises(TreeError, match="unknown leaf 'nope'"):
            load_tree_config(tmp_path)

    def test_duplicate_issuer_pattern_is_rejected_case_insensitively(self, tmp_path):
        issuers = {
            "a": {"patterns": ["Swisscom"], "leaves": ["career"]},
            "b": {"patterns": ["swisscom"], "leaves": ["career"]},
        }
        _write(tmp_path, {"career": _leaf()}, issuers=issuers)
        with pytest.raises(TreeError, match="used by issuers 'a' and 'b'"):
            load_tree_config(tmp_path)

    def test_duplicate_rule_names_are_rejected(self, tmp_path):
        rule = {"name": "cv", "leaf": "career", "globs": ["*cv*"]}
        _write(tmp_path, {"career": _leaf()}, rules=[rule, dict(rule)])
        with pytest.raises(TreeError, match="duplicate rule name 'cv'"):
            load_tree_config(tmp_path)

    def test_issuer_with_unknown_leaf_is_rejected(self, tmp_path):
        issuers = {"hp": {"patterns": ["HP"], "leaves": ["nope"]}}
        _write(tmp_path, {"career": _leaf()}, issuers=issuers)
        with pytest.raises(TreeError, match="issuer 'hp' points to unknown leaf 'nope'"):
            load_tree_config(tmp_path)

    def test_rules_and_issuers_files_are_optional(self, tmp_path):
        _write(tmp_path, {"career": _leaf()})
        cfg = load_tree_config(tmp_path)
        assert cfg.rules.rules == ()
        assert cfg.issuers.issuers == {}


class TestWarnings:
    def test_shared_path_warning_ignores_subkeys(self, tmp_path):
        leaves = {
            "a_year": _leaf(kind="library", path="3_Resources/photos", subkey="{year}"),
            "b_month": _leaf(kind="library", path="3_Resources/photos", subkey="{year}/{month}"),
        }
        warnings = validation_warnings(load_tree_config(_write(tmp_path, leaves)))
        assert "leaves 'a_year' and 'b_month' share path '3_Resources/photos'" in warnings

    def test_retention_prefixes_come_from_the_retention_literal(self):
        prefixes = [value for value in get_args(Retention) if value != "permanent"]
        assert prefixes
        assert all(RETENTION_PREFIX.match(f"{value}_name") for value in prefixes)
        assert RETENTION_PREFIX.match("permanent_name") is None

    def test_warnings_flag_weak_config(self, tmp_path):
        leaves = {
            "invoices": _leaf(kind="record", retention="5y", path="4_Archives/5y_factures"),
            "shots": _leaf(kind="media", path="3_Resources/5y_screenshots"),
            "career": _leaf(),
        }
        rules = [{"name": "tiny", "leaf": "shots", "globs": ["*ab*"]}]
        issuers = {"hp": {"patterns": ["HP"], "leaves": ["shots"]}}
        warnings = validation_warnings(load_tree_config(_write(tmp_path, leaves, rules, issuers)))
        assert "rule 'tiny': glob '*ab*' has <= 3 literal characters" in warnings
        assert "issuer 'hp': pattern 'HP' has <= 3 characters" in warnings
        assert "leaf 'invoices': no rule or issuer points to it" in warnings
        assert (
            "leaf 'shots': retention prefix outside 4_Archives records: "
            "'3_Resources/5y_screenshots'"
        ) in warnings
        assert not any("career" in warning for warning in warnings)


class TestReferenceErrorsNameTheirFile:
    def test_unknown_leaf_in_rules_names_rules_yaml(self, tmp_path):
        rules = [{"name": "cv", "leaf": "nope", "globs": ["*cv*"]}]
        _write(tmp_path, {"career": _leaf()}, rules=rules)
        with pytest.raises(TreeError, match=r"rules\.yaml: rule 'cv' points to unknown leaf"):
            load_tree_config(tmp_path)

    def test_duplicate_rule_name_names_rules_yaml(self, tmp_path):
        rule = {"name": "cv", "leaf": "career", "globs": ["*cv*"]}
        _write(tmp_path, {"career": _leaf()}, rules=[rule, dict(rule)])
        with pytest.raises(TreeError, match=r"rules\.yaml: duplicate rule name 'cv'"):
            load_tree_config(tmp_path)

    def test_unknown_leaf_in_issuers_names_issuers_yaml(self, tmp_path):
        issuers = {"hp": {"patterns": ["HP"], "leaves": ["nope"]}}
        _write(tmp_path, {"career": _leaf()}, issuers=issuers)
        with pytest.raises(TreeError, match=r"issuers\.yaml: issuer 'hp' points to unknown leaf"):
            load_tree_config(tmp_path)

    def test_duplicate_pattern_names_issuers_yaml(self, tmp_path):
        issuers = {
            "a": {"patterns": ["Swisscom"], "leaves": ["career"]},
            "b": {"patterns": ["swisscom"], "leaves": ["career"]},
        }
        _write(tmp_path, {"career": _leaf()}, issuers=issuers)
        with pytest.raises(TreeError, match=r"issuers\.yaml: pattern 'swisscom'"):
            load_tree_config(tmp_path)

    def test_unreadable_file_is_a_tree_error_naming_the_file(self, tmp_path):
        (tmp_path / "tree.yaml").mkdir()  # reading a directory raises an OSError
        with pytest.raises(TreeError, match=r"tree\.yaml: cannot read"):
            load_tree_config(tmp_path)


class TestNoEmptyItems:
    @pytest.mark.parametrize(
        ("file_name", "leaves", "rules", "issuers"),
        [
            ("tree.yaml", {"career": _leaf(keywords=[""])}, None, None),
            (
                "rules.yaml",
                {"career": _leaf()},
                [{"name": "r", "leaf": "career", "globs": [""]}],
                None,
            ),
            (
                "rules.yaml",
                {"career": _leaf()},
                [{"name": "r", "leaf": "", "globs": ["*x*"]}],
                None,
            ),
            (
                "issuers.yaml",
                {"career": _leaf()},
                None,
                {"acme": {"patterns": [""], "leaves": ["career"]}},
            ),
            (
                "issuers.yaml",
                {"career": _leaf()},
                None,
                {"acme": {"patterns": ["Acme"], "leaves": [""]}},
            ),
        ],
    )
    def test_empty_string_item_is_a_tree_error_naming_the_file(
        self, tmp_path, file_name, leaves, rules, issuers
    ):
        _write(tmp_path, leaves, rules=rules, issuers=issuers)
        with pytest.raises(TreeError, match=re.escape(str(tmp_path / file_name))):
            load_tree_config(tmp_path)


def test_rule_pin_values():
    from para_files.core.tree import RulesFile

    rules = RulesFile.model_validate(
        {
            "rules": [
                {"name": "a", "leaf": "x", "globs": ["*a*"]},
                {"name": "b", "leaf": "x", "globs": ["*b*"], "pin": True},
                {"name": "c", "leaf": "x", "globs": ["*.jpg"], "pin": "exif"},
            ]
        }
    )
    assert [rule.pin for rule in rules.rules] == [False, True, "exif"]


def test_rule_pin_rejects_other_values():
    from pydantic import ValidationError

    from para_files.core.tree import RulesFile

    with pytest.raises(ValidationError):
        RulesFile.model_validate(
            {"rules": [{"name": "a", "leaf": "x", "globs": ["*a*"], "pin": "maybe"}]}
        )


def test_pin_warnings():
    from para_files.core.tree import RulesFile, TreeConfig, validation_warnings
    from tests.core_helpers import make_config

    base = make_config()
    rules = RulesFile.model_validate(
        {
            "rules": [
                {"name": "notes", "leaf": "resources_it", "globs": ["*notes*"], "pin": True},
                {"name": "pdfs", "leaf": "resources_docs", "globs": ["*.pdf"], "pin": True},
                {"name": "shots", "leaf": "archives_photos", "globs": ["*.jpg"], "pin": "exif"},
            ]
        }
    )
    warnings = validation_warnings(TreeConfig(tree=base.tree, rules=rules, issuers=base.issuers))
    assert any("'notes'" in w and "knowledge" in w for w in warnings)
    assert any("'pdfs'" in w and "extension" in w for w in warnings)
    assert not any("'shots'" in w and "pinned" in w for w in warnings)
