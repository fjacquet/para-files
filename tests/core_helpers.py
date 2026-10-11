"""Shared builders for the new-core tests: a PARA root, settings and a small tree."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from para_files.core.settings import CoreSettings
from para_files.core.tree import IssuersFile, RulesFile, Tree, TreeConfig


BUCKETS = ("0_Inbox", "1_Projets", "2_Areas", "3_Resources", "4_Archives")

LEAVES: dict[str, dict[str, Any]] = {
    "archives_10y_travail": {
        "kind": "record",
        "retention": "10y",
        "path": "4_Archives/10y_travail",
        "subkey": "{year}",
        "describe": "Payslips and employment records",
        "keywords": ["salaire", "payslip"],
    },
    "archives_10y_banques": {
        "kind": "record",
        "retention": "10y",
        "path": "4_Archives/10y_banques",
        "subkey": "{issuer}/{year}",
        "describe": "Bank and card statements",
        "keywords": ["releve", "statement", "facture"],
    },
    "archives_5y_factures": {
        "kind": "record",
        "retention": "5y",
        "path": "4_Archives/5y_factures",
        "subkey": "{year}",
        "describe": "Invoices",
        "keywords": ["facture", "invoice"],
    },
    "resources_livres": {
        "kind": "library",
        "path": "3_Resources/livres",
        "subkey": "{thema}",
        "describe": "Books and ebooks",
    },
    "resources_docs": {
        "kind": "library",
        "path": "3_Resources/docs",
        "describe": "Vendor documentation",
    },
    "resources_it": {"kind": "knowledge", "path": "3_Resources/IT", "describe": "IT notes"},
    "archives_photos": {
        "kind": "media",
        "path": "4_Archives/photos",
        "subkey": "{year}/{month}",
        "describe": "Photos",
    },
}
RULES: list[dict[str, Any]] = [
    {
        "name": "payslips",
        "leaf": "archives_10y_travail",
        "globs": ["*payslip*", "*compte de salaire*"],
    },
    {"name": "photos", "leaf": "archives_photos", "globs": ["*.jpg", "*.heic"]},
    {"name": "whitepapers", "leaf": "resources_docs", "globs": ["*_whitepaper*"]},
    {"name": "it_notes", "leaf": "resources_it", "globs": ["*.md"]},
]
ISSUERS: dict[str, dict[str, Any]] = {
    "acmecard": {
        "patterns": ["AcmeCard", "acmecard.example"],
        "leaves": ["archives_10y_banques", "archives_5y_factures"],
    },
    "abc": {"patterns": ["ABC"], "leaves": ["archives_10y_banques"]},
}


def make_para_root(base: Path) -> Path:
    """base/PARA with the five buckets."""
    root = base / "PARA"
    for bucket in BUCKETS:
        (root / bucket).mkdir(parents=True, exist_ok=True)
    return root


def make_settings(base: Path, **overrides: Any) -> CoreSettings:
    """Settings on a fresh PARA root; cache and journal outside it; fallback off."""
    values: dict[str, Any] = {
        "para_root": make_para_root(base),
        "cache_path": base / "cache" / "cache.sqlite",
        "state_dir": base / "state",
        "fallback_enabled": False,
    }
    values.update(overrides)
    return CoreSettings(**values)


def make_config() -> TreeConfig:
    """The small tree above, validated."""
    return TreeConfig(
        tree=Tree.model_validate({"leaves": LEAVES}),
        rules=RulesFile.model_validate({"rules": RULES}),
        issuers=IssuersFile.model_validate({"issuers": ISSUERS}),
    )


def write_config(directory: Path) -> Path:
    """Write tree.yaml, rules.yaml and issuers.yaml into directory; return it."""
    directory.mkdir(parents=True, exist_ok=True)
    for name, data in (
        ("tree.yaml", {"leaves": LEAVES}),
        ("rules.yaml", {"rules": RULES}),
        ("issuers.yaml", {"issuers": ISSUERS}),
    ):
        (directory / name).write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return directory


def setup_cli(base: Path, monkeypatch: Any) -> Path:
    """A PARA root and the small tree in the sandbox config dir, wired through the env.

    Returns the PARA root. The cache and journal live under base, outside the root;
    the fallback is off.
    """
    import os

    root = make_para_root(base)
    write_config(Path(os.environ["PARA_FILES_CONFIG_DIR"]))
    monkeypatch.setenv("PARA_FILES_PARA_ROOT", str(root))
    monkeypatch.setenv("PARA_FILES_CACHE_PATH", str(base / "cache" / "cache.sqlite"))
    monkeypatch.setenv("PARA_FILES_STATE_DIR", str(base / "state"))
    monkeypatch.setenv("PARA_FILES_FALLBACK_ENABLED", "false")
    from para_files.cli import review as review_cli

    monkeypatch.setattr(review_cli, "stdin_is_tty", lambda: True)
    return root
