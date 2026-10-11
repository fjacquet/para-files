"""Canonical tree, rules and issuers: strict loading and validation (spec §4.1).

Personal config lives in ``config_dir()``: ``$PARA_FILES_CONFIG_DIR`` or ``~/.config/para-files``.
The repository ships only ``examples/``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal, Self, get_args

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from para_files.config import config_dir_path


Kind = Literal["record", "library", "media", "knowledge"]
Retention = Literal["permanent", "ret", "10y", "5y", "2y", "ctr"]
RETENTION_PREFIX = re.compile(
    "^("
    + "|".join(re.escape(value) for value in get_args(Retention) if value != "permanent")
    + ")_"
)

BUCKET_PREFIXES = ("1_", "2_", "3_", "4_")
ARCHIVES = "4_Archives"
MAX_PATH_SEGMENTS = 3  # bucket + 2 levels
MAX_SUBKEY_SEGMENTS = 2
MIN_ARCHIVE_SEGMENTS = 2  # 4_Archives plus the retention folder
SHORT_LITERALS = 3
SUBKEY_PLACEHOLDERS = frozenset({"{year}", "{month}", "{issuer}", "{thema}"})
LEAF_ID = re.compile(r"[a-z][a-z0-9_]*")
GLOB_SYNTAX = re.compile(r"[*?\[\]]")


class TreeError(ValueError):
    """Tree, rules or issuers config breaks a strict rule."""


def config_dir() -> Path:
    """Return the personal config directory (shared rule with the settings loader)."""
    return config_dir_path()


class Leaf(BaseModel):
    """One destination the classifiers may choose."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Kind
    path: str
    describe: str = Field(min_length=1)
    retention: Retention | None = None
    subkey: str | None = None
    keywords: tuple[str, ...] = ()

    @field_validator("path")
    @classmethod
    def _check_path(cls, value: str) -> str:
        parts = value.split("/")
        if not value.startswith(BUCKET_PREFIXES) or any(not p or p != p.strip() for p in parts):
            msg = f"path needs a 1_-4_ bucket and no empty or padded segments: {value!r}"
            raise ValueError(msg)
        if len(parts) > MAX_PATH_SEGMENTS:
            msg = f"path is deeper than a bucket plus 2 levels: {value!r}"
            raise ValueError(msg)
        return value

    @field_validator("subkey")
    @classmethod
    def _check_subkey(cls, value: str | None) -> str | None:
        if value is None:
            return None
        segments = value.split("/")
        if (
            len(segments) > MAX_SUBKEY_SEGMENTS
            or len(set(segments)) != len(segments)
            or not set(segments) <= SUBKEY_PLACEHOLDERS
        ):
            msg = f"subkey must be at most 2 distinct of {sorted(SUBKEY_PLACEHOLDERS)}: {value!r}"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _check_retention(self) -> Self:
        if (self.kind == "record") != (self.retention is not None):
            msg = "record leaves need a retention; other kinds must not have one"
            raise ValueError(msg)
        if self.retention not in {None, "permanent"}:
            parts = self.path.split("/")
            prefix = f"{self.retention}_"
            if (
                parts[0] != ARCHIVES
                or len(parts) < MIN_ARCHIVE_SEGMENTS
                or not parts[1].startswith(prefix)
            ):
                msg = (
                    f"retention {self.retention} requires 4_Archives/{prefix}<name>: {self.path!r}"
                )
                raise ValueError(msg)
        return self


class Tree(BaseModel):
    """The closed list of leaves."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    leaves: dict[str, Leaf] = Field(min_length=1)

    @field_validator("leaves")
    @classmethod
    def _check_ids(cls, value: dict[str, Leaf]) -> dict[str, Leaf]:
        bad = sorted(key for key in value if not LEAF_ID.fullmatch(key))
        if bad:
            msg = f"leaf ids must be snake_case: {bad}"
            raise ValueError(msg)
        return value


class Rule(BaseModel):
    """Filename globs that send a file to one leaf."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    leaf: str
    globs: tuple[str, ...] = Field(min_length=1)


class RulesFile(BaseModel):
    """Contents of rules.yaml."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rules: tuple[Rule, ...] = ()


class Issuer(BaseModel):
    """Patterns naming one issuer, and the leaves its documents may go to."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    patterns: tuple[str, ...] = Field(min_length=1)
    leaves: tuple[str, ...] = Field(min_length=1)


class IssuersFile(BaseModel):
    """Contents of issuers.yaml."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    issuers: dict[str, Issuer] = Field(default_factory=dict)


class TreeConfig(BaseModel):
    """tree.yaml, rules.yaml and issuers.yaml, cross-checked."""

    model_config = ConfigDict(frozen=True)

    tree: Tree
    rules: RulesFile
    issuers: IssuersFile


def _read_yaml(path: Path) -> dict[str, object]:
    try:
        with path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except FileNotFoundError as exc:
        msg = f"{path}: file not found"
        raise TreeError(msg) from exc
    except OSError as exc:
        msg = f"{path}: cannot read: {exc}"
        raise TreeError(msg) from exc
    except UnicodeDecodeError as exc:
        msg = f"{path}: not valid UTF-8: {exc}"
        raise TreeError(msg) from exc
    except yaml.YAMLError as exc:
        msg = f"{path}: invalid YAML: {exc}"
        raise TreeError(msg) from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        msg = f"{path}: expected a mapping"
        raise TreeError(msg)
    return data


def _parse[M: BaseModel](model: type[M], path: Path) -> M:
    try:
        return model.model_validate(_read_yaml(path))
    except ValidationError as exc:
        msg = f"{path}: {exc}"
        raise TreeError(msg) from exc


def _reference_problems(tree: Tree, rules: RulesFile, issuers: IssuersFile) -> list[str]:
    """Cross-file problems; each names the file it comes from (rules.yaml or issuers.yaml)."""
    names = [rule.name for rule in rules.rules]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    problems = [f"rules.yaml: duplicate rule name {name!r}" for name in duplicates]
    problems += [
        f"rules.yaml: rule {rule.name!r} points to unknown leaf {rule.leaf!r}"
        for rule in rules.rules
        if rule.leaf not in tree.leaves
    ]
    owner: dict[str, str] = {}
    for name, issuer in issuers.issuers.items():
        problems += [
            f"issuers.yaml: issuer {name!r} points to unknown leaf {leaf!r}"
            for leaf in issuer.leaves
            if leaf not in tree.leaves
        ]
        for pattern in issuer.patterns:
            first = owner.setdefault(pattern.casefold(), name)
            if first != name:
                problems.append(
                    f"issuers.yaml: pattern {pattern!r} is used by issuers {first!r} and {name!r}"
                )
    return problems


def load_tree_config(directory: Path | None = None) -> TreeConfig:
    """Load tree.yaml (required), rules.yaml and issuers.yaml (optional), strictly."""
    base = directory or config_dir()
    rules_path = base / "rules.yaml"
    issuers_path = base / "issuers.yaml"
    tree = _parse(Tree, base / "tree.yaml")
    rules = _parse(RulesFile, rules_path) if rules_path.exists() else RulesFile()
    issuers = _parse(IssuersFile, issuers_path) if issuers_path.exists() else IssuersFile()
    problems = _reference_problems(tree, rules, issuers)
    if problems:
        msg = "; ".join(problems)
        raise TreeError(msg)
    return TreeConfig(tree=tree, rules=rules, issuers=issuers)


def _literals(glob: str) -> int:
    return len(GLOB_SYNTAX.sub("", glob))


def validation_warnings(config: TreeConfig) -> list[str]:
    """Non-fatal problems for the owner to review (shown by `tree --validate` in Stage 3)."""
    warnings = [
        f"rule {rule.name!r}: glob {glob!r} has <= {SHORT_LITERALS} literal characters"
        for rule in config.rules.rules
        for glob in rule.globs
        if _literals(glob) <= SHORT_LITERALS
    ]
    warnings += [
        f"issuer {name!r}: pattern {pattern!r} has <= {SHORT_LITERALS} characters"
        for name, issuer in config.issuers.issuers.items()
        for pattern in issuer.patterns
        if len(pattern) <= SHORT_LITERALS
    ]
    used = {rule.leaf for rule in config.rules.rules}
    used |= {leaf for issuer in config.issuers.issuers.values() for leaf in issuer.leaves}
    warnings += [
        f"leaf {leaf_id!r}: no rule or issuer points to it"
        for leaf_id, leaf in config.tree.leaves.items()
        if leaf_id not in used and leaf.kind != "knowledge"
    ]
    seen: dict[str, str] = {}
    for leaf_id, leaf in config.tree.leaves.items():
        first = seen.setdefault(leaf.path, leaf_id)
        if first != leaf_id:
            warnings.append(f"leaves {first!r} and {leaf_id!r} share path {leaf.path!r}")
        parts = leaf.path.split("/")
        prefixed = any(RETENTION_PREFIX.match(part) for part in parts[1:])
        allowed = (
            leaf.kind == "record"
            and leaf.retention not in {None, "permanent"}
            and parts[0] == ARCHIVES
        )
        if prefixed and not allowed:
            warnings.append(
                f"leaf {leaf_id!r}: retention prefix outside 4_Archives records: {leaf.path!r}"
            )
    return warnings
