# Stage 2 — New Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the new classification and move core under `src/para_files/core/`, next to the old pipeline: evidence, four signals on leaf ids, bands, cache, plan/apply with a journal, and undo.

**Architecture:** One `extract()` per file builds an immutable `Evidence`. Signals 1–4 (rules, books, issuers, OpenRouter fallback) run in order; the first verdict wins and is cached by content hash and config fingerprint. `finish()` turns a verdict into a `Decision` with a band and a target directory. `apply_ops()` moves files one at a time, journaling every operation, and `undo_run()` replays a journal backwards. Nothing in the old pipeline or CLI changes (Stage 3 wires the CLI).

**Tech Stack:** Python 3.12, pydantic / pydantic-settings, litellm (OpenRouter), sqlite3, loguru, pytest.

**Spec:** `docs/superpowers/specs/2026-10-10-para-files-redesign-design.md` (§4.1–§4.3, §5 Stage 2; amended 2026-10-11, PR #31).

## Global Constraints

- Every module starts with `from __future__ import annotations`; logging via `from loguru import logger`; line length 100; the repo's strict ruff config and `mypy src/` (strict) must pass.
- The repo is PUBLIC: no personal names, paths, issuers or folder names in tracked files. Tests use generic names (`AcmeCard`, `ABC`, `Payslip_…`).
- No network in tests: model calls go through an injected `complete` (default `litellm.completion`); ISBN lookups through an injected `lookup`.
- Model calls always go through litellm (owner rule), never a hand-written HTTP request.
- Every cloud request carries `provider: {"zdr": true, "data_collection": "deny"}`. A file flagged by the secrets guard is never sent, never looked up, never moved.
- Old code is not touched, except removing the `isbnlib.cover()` call (Task 6, spec §4.2).
- Personal data lives in `~/.config/para-files/` (config), `~/.cache/para-files/` (cache), `~/.local/state/para-files/` (journal); never in the repo.
- Gate before every commit: `uv run pytest -m "not slow" -o addopts="-ra --strict-markers --strict-config"`, `uv run ruff check src/ tests/ scripts/`, `uv run ruff format --check src/ tests/ scripts/`, `uv run mypy src/`.
- Commit messages end with:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx
  ```
  Stage files explicitly (never `git add -A`); never stage `.serena/`, `.rtk/` or `uv.lock`.

## Rulings made while writing this plan

| Spec says | Plan does | Why |
|---|---|---|
| `op` ∈ move, trash, rmdir | adds `mkdir` | Without it, `undo` leaves the folders a run created, and S5 (byte-identical tree) fails |
| Package `default_rules.yaml`, `thema_l1l2.json` | not in Stage 2 | Default rules need leaf ids the owner defines; the owner's `rules.yaml` already carries the extension rules. Thema slimming belongs to the Stage 4 purge |
| Settings "env > .env > YAML > defaults" | env > `<config dir>/.env` > defaults (no YAML, no cwd `.env`) | The new tree files hold no settings; a cwd `.env` made results depend on where the command runs |
| Owner-corrected leaf | target is the corrected leaf's root | The subkey was filled for the proposed leaf; the owner refiles below it if needed |

## Review Focus

1. A file deleted or edited between preview and apply → that operation is skipped with a reason, the run continues (Task 10).
2. Two inbox files with identical content → the second goes to `.trash`, nothing is overwritten (Task 10).
3. `PARA_FILES_PARA_ROOT` pointing at `…/0_Inbox` (the known bad `.env`) → a clear error naming the variable (Task 1).
4. macOS NFD filenames and accents in rules, issuers and keywords → match like their NFC form (Tasks 3, 4).
5. Ctrl+C in the middle of an apply → every finished move is journaled and `undo` restores it (Task 11).

## File Structure

| File | Responsibility |
|---|---|
| `src/para_files/core/settings.py` | `CoreSettings`, `load_settings()` |
| `src/para_files/core/evidence.py` | `Evidence`, `extract()`, `sha256_of()` |
| `src/para_files/core/rules.py` | signal 1 |
| `src/para_files/core/issuers.py` | signal 3 |
| `src/para_files/core/cache.py` | SQLite cache, `config_fingerprint()` |
| `src/para_files/core/books.py` | signal 2 |
| `src/para_files/core/fallback.py` | signal 4 (OpenRouter) |
| `src/para_files/core/decide.py` | cascade, bands, target directory, `classify()` |
| `src/para_files/core/journal.py` | run journal, calibration counts |
| `src/para_files/core/apply.py` | `apply_ops()` |
| `src/para_files/core/undo.py` | `undo_run()` |
| `src/para_files/core/sort.py` | `iter_files()`, `build_context()`, `preview()`, `auto_ops()`, `apply()` |
| `tests/core_helpers.py` | shared builders for the tests |

---

### Task 1: Settings

**Files:**
- Create: `src/para_files/core/settings.py`, `tests/core_helpers.py`, `tests/test_core_settings.py`
- Modify: `tests/conftest.py` (sandbox also clears `OPENROUTER_API_KEY`)

**Interfaces:**
- Produces: `CoreSettings` (fields below), `load_settings(**overrides) -> CoreSettings`, `INBOX = "0_Inbox"`.
- Produces (tests): `tests.core_helpers.make_para_root(base) -> Path`, `make_settings(base, **overrides) -> CoreSettings`, `make_config() -> TreeConfig`, `write_config(directory) -> Path`.

- [ ] **Step 1: Sandbox hygiene.** In `tests/conftest.py`, inside `_sanitized_reference_tree`, right after the loop that deletes `PARA_FILES_*` variables, add:

```python
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)  # a real key never reaches a test
```

- [ ] **Step 2: Test helpers.** Create `tests/core_helpers.py`:

```python
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
```

- [ ] **Step 3: Write the failing tests.** Create `tests/test_core_settings.py`:

```python
"""CoreSettings: precedence env > <config dir>/.env > defaults; para_root checks."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from para_files.core.settings import load_settings
from tests.core_helpers import make_para_root


@pytest.fixture
def cfg_dir(tmp_path, monkeypatch):
    path = tmp_path / "cfg"
    path.mkdir()
    monkeypatch.setenv("PARA_FILES_CONFIG_DIR", str(path))
    return path


def test_dotenv_in_config_dir_is_read(tmp_path, cfg_dir):
    root = make_para_root(tmp_path)
    (cfg_dir / ".env").write_text(f"PARA_FILES_PARA_ROOT={root}\nPARA_FILES_MAX_WORKERS=2\n")
    settings = load_settings()
    assert settings.para_root == root
    assert settings.max_workers == 2


def test_environment_beats_dotenv(tmp_path, cfg_dir, monkeypatch):
    root = make_para_root(tmp_path)
    (cfg_dir / ".env").write_text(f"PARA_FILES_PARA_ROOT={root}\nPARA_FILES_MAX_WORKERS=2\n")
    monkeypatch.setenv("PARA_FILES_MAX_WORKERS", "3")
    assert load_settings().max_workers == 3


def test_overrides_beat_environment(tmp_path, cfg_dir, monkeypatch):
    monkeypatch.setenv("PARA_FILES_MAX_WORKERS", "3")
    assert load_settings(para_root=make_para_root(tmp_path), max_workers=5).max_workers == 5


def test_working_directory_dotenv_is_ignored(tmp_path, cfg_dir, monkeypatch):
    root = make_para_root(tmp_path)
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    (cwd / ".env").write_text("PARA_FILES_MAX_WORKERS=7\n")
    monkeypatch.chdir(cwd)
    assert load_settings(para_root=root).max_workers == 4


def test_root_pointing_at_a_bucket_is_refused(tmp_path, cfg_dir):
    root = make_para_root(tmp_path)
    with pytest.raises(ValidationError, match="PARA_FILES_PARA_ROOT"):
        load_settings(para_root=root / "0_Inbox")


def test_root_without_inbox_is_refused(tmp_path, cfg_dir):
    with pytest.raises(ValidationError, match="no 0_Inbox"):
        load_settings(para_root=tmp_path)


def test_openrouter_key_from_its_usual_variable(tmp_path, cfg_dir, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-value")
    settings = load_settings(para_root=make_para_root(tmp_path))
    assert settings.openrouter_api_key is not None
    assert settings.openrouter_api_key.get_secret_value() == "sk-test-value"
    assert "sk-test-value" not in repr(settings)


def test_cache_and_state_default_under_home(tmp_path, cfg_dir):
    settings = load_settings(para_root=make_para_root(tmp_path))
    assert settings.cache_path == Path.home() / ".cache" / "para-files" / "cache.sqlite"
    assert settings.state_dir == Path.home() / ".local" / "state" / "para-files"


def test_defaults(tmp_path, cfg_dir):
    settings = load_settings(para_root=make_para_root(tmp_path))
    assert settings.fallback_model == "google/gemini-3.8-flash"
    assert settings.fallback_backup_model == "anthropic/claude-sonnet-5.5"
    assert settings.calibration_min == 100
    assert settings.preview_chars == 2000
```

- [ ] **Step 4: Run, expect failure.** `uv run pytest tests/test_core_settings.py -q` → FAIL (`ModuleNotFoundError: para_files.core.settings`).

- [ ] **Step 5: Implement.** Create `src/para_files/core/settings.py`:

```python
"""Settings of the new core (spec §4.1, settings precedence).

Sources, highest first: init arguments, environment variables, ``<config dir>/.env``,
defaults. There is no YAML source and no working-directory ``.env``, so the result does not
depend on where a command runs.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from para_files.config import config_dir_path


INBOX = "0_Inbox"
BUCKET_NAME = re.compile(r"^[0-4]_")


def _home(*parts: str) -> Path:
    return Path.home().joinpath(*parts)


class CoreSettings(BaseSettings):
    """Effective settings for sort, explain, undo and clean."""

    model_config = SettingsConfigDict(
        env_prefix="PARA_FILES_",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    para_root: Path
    preview_chars: int = Field(default=2000, ge=100, le=10_000)
    max_workers: int = Field(default=4, ge=1, le=16)
    fallback_enabled: bool = True
    fallback_model: str = "google/gemini-3.8-flash"
    fallback_backup_model: str = "anthropic/claude-sonnet-5.5"
    openrouter_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "OPENROUTER_API_KEY", "PARA_FILES_OPENROUTER_API_KEY", "PARA_FILES_LLM_API_KEY"
        ),
    )
    calibration_min: int = Field(default=100, ge=1)
    issuers_green: float = Field(default=0.9, ge=0.0, le=1.0)
    fallback_green: float = Field(default=0.9, ge=0.0, le=1.0)
    fallback_red: float = Field(default=0.3, ge=0.0, le=1.0)
    cache_path: Path = Field(default_factory=lambda: _home(".cache", "para-files", "cache.sqlite"))
    state_dir: Path = Field(default_factory=lambda: _home(".local", "state", "para-files"))

    @field_validator("para_root", "cache_path", "state_dir")
    @classmethod
    def _expand(cls, value: Path) -> Path:
        return value.expanduser()

    @field_validator("para_root")
    @classmethod
    def _check_root(cls, value: Path) -> Path:
        if BUCKET_NAME.match(value.name):
            msg = (
                f"para_root points at a bucket ({value.name}); set PARA_FILES_PARA_ROOT to the "
                f"folder that contains {INBOX}: {value}"
            )
            raise ValueError(msg)
        if not (value / INBOX).is_dir():
            msg = f"para_root has no {INBOX} folder: {value}"
            raise ValueError(msg)
        return value


def load_settings(**overrides: Any) -> CoreSettings:  # noqa: ANN401 - keyword overrides of any field
    """Settings from the environment, then ``<config dir>/.env``; overrides win over both."""
    return CoreSettings(_env_file=config_dir_path() / ".env", **overrides)  # type: ignore[call-arg]
```

- [ ] **Step 6: Run, expect pass.** `uv run pytest tests/test_core_settings.py -q` → 9 passed.

- [ ] **Step 7: Gate and commit.**

```bash
git add src/para_files/core/settings.py tests/core_helpers.py tests/test_core_settings.py tests/conftest.py
git commit -m "feat(core): settings with env > config-dir .env > defaults precedence" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx"
```

---

### Task 2: Evidence

**Files:**
- Create: `src/para_files/core/evidence.py`, `tests/test_core_evidence.py`

**Interfaces:**
- Consumes: `para_files.core.secrets.secret_reason`; readers in `para_files.utils` (`read_content_preview`, `extract_pdf_metadata`, `extract_epub_metadata`, `extract_mobi_metadata`, `extract_exif`, `is_exiftool_available`).
- Produces: `Evidence` (frozen dataclass: `path, name, ext, size, mtime, sha256, secret, text_preview, doc_meta, isbns, exif_date, archive_listing`), `extract(path, *, root=None, preview_chars=2000) -> Evidence`, `sha256_of(path) -> str`.

Rules: `name` is NFC; `ext` is lower-case with the dot. `secret` is `"folder"` (a folder between `root` and the file is secret-named), `"archive"` (an archive entry name is secret-named), `"name"`, or a content pattern id. A secret evidence carries only filesystem facts and the hash: no preview, no metadata.

- [ ] **Step 1: Write the failing tests.** Create `tests/test_core_evidence.py`:

```python
"""extract(): one Evidence per file; secret files keep no content."""

from __future__ import annotations

import hashlib
import zipfile
from types import SimpleNamespace

from para_files.core import evidence
from para_files.core.evidence import extract


def test_text_file(tmp_path):
    path = tmp_path / "Note.TXT"
    path.write_text("hello world")
    ev = extract(path)
    assert ev.name == "Note.TXT"
    assert ev.ext == ".txt"
    assert ev.size == 11
    assert ev.text_preview.startswith("hello world")
    assert ev.sha256 == hashlib.sha256(b"hello world").hexdigest()
    assert ev.secret is None


def test_secret_name_reads_no_content(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(evidence, "read_content_preview", lambda *a: calls.append(a) or "x")
    path = tmp_path / "passwords.txt"
    path.write_text("anything")
    ev = extract(path)
    assert ev.secret == "name"  # noqa: S105
    assert ev.text_preview == ""
    assert calls == []


def test_secret_content_drops_the_preview(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("server\npassword: hunter22\n")
    ev = extract(path)
    assert ev.secret == "credential_value"  # noqa: S105
    assert ev.text_preview == ""


def test_secret_folder_below_root(tmp_path):
    root = tmp_path / "PARA"
    path = root / "2_Areas" / "IT" / "credentials" / "a.txt"
    path.parent.mkdir(parents=True)
    path.write_text("plain")
    assert extract(path, root=root).secret == "folder"  # noqa: S105


def test_folders_above_root_are_not_checked(tmp_path):
    root = tmp_path / "tokens" / "PARA"
    path = root / "0_Inbox" / "a.txt"
    path.parent.mkdir(parents=True)
    path.write_text("plain")
    assert extract(path, root=root).secret is None


def test_zip_listing(tmp_path):
    path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("a.txt", "x")
        archive.writestr("b/c.txt", "y")
    assert extract(path).archive_listing == ("a.txt", "b/c.txt")


def test_secret_archive_entry(tmp_path):
    path = tmp_path / "backup.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("keys/id_rsa", "x")
    ev = extract(path)
    assert ev.secret == "archive"  # noqa: S105
    assert ev.archive_listing == ()


def test_reader_error_leaves_preview_empty(tmp_path, monkeypatch):
    def boom(*_args):
        msg = "reader broke"
        raise RuntimeError(msg)

    monkeypatch.setattr(evidence, "read_content_preview", boom)
    path = tmp_path / "a.docx"
    path.write_bytes(b"not really docx")
    assert extract(path).text_preview == ""


def test_binary_placeholder_preview_is_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(evidence, "read_content_preview", lambda path, _n: f"Filename: {path.name}")
    path = tmp_path / "blob.bin"
    path.write_bytes(b"\x00\x01")
    assert extract(path).text_preview == ""


def test_pdf_metadata_and_isbns(tmp_path, monkeypatch):
    meta = SimpleNamespace(
        title="T", author="A", subject="S", page_count=300, isbns=["9780596517748"]
    )
    monkeypatch.setattr(evidence, "extract_pdf_metadata", lambda *_a, **_k: meta)
    monkeypatch.setattr(evidence, "read_content_preview", lambda *_a: "text")
    path = tmp_path / "book.pdf"
    path.write_bytes(b"%PDF-1.4")
    ev = extract(path)
    assert ev.doc_meta == {"title": "T", "author": "A", "subject": "S", "page_count": "300"}
    assert ev.isbns == ("9780596517748",)


def test_nfd_name_becomes_nfc(tmp_path):
    import unicodedata

    path = tmp_path / unicodedata.normalize("NFD", "décompte.txt")
    path.write_text("x")
    assert extract(path).name == unicodedata.normalize("NFC", "décompte.txt")
```

- [ ] **Step 2: Run, expect failure.** `uv run pytest tests/test_core_evidence.py -q` → FAIL (module missing).

- [ ] **Step 3: Implement.** Create `src/para_files/core/evidence.py`:

```python
"""Evidence: everything the signals may read about one file, extracted once (spec §4.2)."""

from __future__ import annotations

import hashlib
import tarfile
import unicodedata
import zipfile
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path

from loguru import logger

from para_files.core.secrets import secret_reason
from para_files.utils.epub_metadata import extract_epub_metadata
from para_files.utils.exiftool import extract_exif, is_exiftool_available
from para_files.utils.file_utils import read_content_preview
from para_files.utils.mobi_metadata import extract_mobi_metadata
from para_files.utils.pdf_metadata import extract_pdf_metadata


MAX_ARCHIVE_ENTRIES = 200
MAX_ISBN_PAGES = 10
MEDIA_EXTENSIONS = frozenset(
    {".jpg", ".jpeg", ".png", ".heic", ".tif", ".tiff", ".dng", ".cr2", ".nef", ".arw"}
    | {".mov", ".mp4", ".m4v"}
)
TAR_SUFFIXES = (".tar", ".tgz", ".tar.gz", ".tar.bz2", ".tar.xz")


@dataclass(frozen=True)
class Evidence:
    """One file as the signals see it. A secret file carries only filesystem facts."""

    path: Path
    name: str
    ext: str
    size: int
    mtime: float
    sha256: str
    secret: str | None = None
    text_preview: str = ""
    doc_meta: dict[str, str] = field(default_factory=dict)
    isbns: tuple[str, ...] = ()
    exif_date: datetime | None = None
    archive_listing: tuple[str, ...] = ()


def sha256_of(path: Path) -> str:
    """Content hash (hex)."""
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _secret_folder(path: Path, root: Path | None) -> str | None:
    """'folder' when a folder between root and the file is secret-named."""
    if root is None:
        return None
    try:
        parts = path.resolve().parent.relative_to(root.resolve()).parts  # /var vs /private/var
    except ValueError:
        return None
    return "folder" if any(secret_reason(part) for part in parts) else None


def _preview(path: Path, max_chars: int) -> str:
    try:
        text = read_content_preview(path, max_chars)
    except Exception as exc:  # noqa: BLE001 - a reader failure leaves the preview empty
        logger.warning("preview failed for {}: {}", path.name, exc)
        return ""
    return "" if text.strip() == f"Filename: {path.name}" else text[:max_chars]


def _book_meta(path: Path, ext: str) -> tuple[dict[str, str], tuple[str, ...]]:
    try:
        if ext == ".pdf":
            pdf = extract_pdf_metadata(path, max_pages_for_isbn=MAX_ISBN_PAGES)
            if pdf is None:
                return {}, ()
            meta = {
                "title": pdf.title or "",
                "author": pdf.author or "",
                "subject": pdf.subject or "",
                "page_count": str(pdf.page_count or 0),
            }
            return meta, tuple(pdf.isbns)
        if ext in {".epub", ".mobi"}:
            book = extract_epub_metadata(path) if ext == ".epub" else extract_mobi_metadata(path)
            if book is None:
                return {}, ()
            return {"title": book.title or "", "author": book.author or ""}, tuple(book.isbns)
    except Exception as exc:  # noqa: BLE001 - metadata is optional evidence
        logger.warning("metadata failed for {}: {}", path.name, exc)
    return {}, ()


def _exif_date(path: Path, ext: str) -> datetime | None:
    if ext not in MEDIA_EXTENSIONS or not is_exiftool_available():
        return None
    try:
        data = extract_exif(path)
    except Exception as exc:  # noqa: BLE001 - EXIF is optional evidence
        logger.warning("EXIF failed for {}: {}", path.name, exc)
        return None
    return (data.date_taken or data.date_created) if data else None


def _archive_listing(path: Path) -> tuple[str, ...]:
    lower = path.name.lower()
    try:
        if lower.endswith(".zip"):
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
        elif lower.endswith(TAR_SUFFIXES):
            with tarfile.open(path) as archive:
                names = archive.getnames()
        else:
            return ()
    except (OSError, zipfile.BadZipFile, tarfile.TarError) as exc:
        logger.warning("archive listing failed for {}: {}", path.name, exc)
        return ()
    return tuple(names[:MAX_ARCHIVE_ENTRIES])


def extract(path: Path, *, root: Path | None = None, preview_chars: int = 2000) -> Evidence:
    """Read one file once; secret checks run before any content is kept."""
    path = path.absolute()
    stat = path.stat()
    base = Evidence(
        path=path,
        name=unicodedata.normalize("NFC", path.name),
        ext=path.suffix.lower(),
        size=stat.st_size,
        mtime=stat.st_mtime,
        sha256=sha256_of(path),
    )
    secret = _secret_folder(path, root) or secret_reason(base.name)
    if secret:
        return replace(base, secret=secret)
    listing = _archive_listing(path)
    if any(secret_reason(entry) for entry in listing):
        return replace(base, secret="archive")  # noqa: S106 - a reason, not a password
    preview = _preview(path, preview_chars)
    secret = secret_reason(base.name, preview)
    if secret:
        return replace(base, secret=secret)
    meta, isbns = _book_meta(path, base.ext)
    return replace(
        base,
        text_preview=preview,
        doc_meta=meta,
        isbns=isbns,
        exif_date=_exif_date(path, base.ext),
        archive_listing=listing,
    )
```

- [ ] **Step 4: Run, expect pass.** `uv run pytest tests/test_core_evidence.py -q` → 11 passed.

- [ ] **Step 5: Gate and commit.**

```bash
git add src/para_files/core/evidence.py tests/test_core_evidence.py
git commit -m "feat(core): evidence extraction with the secrets guard first" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx"
```

---

### Task 3: Signal 1 — rules

**Files:**
- Create: `src/para_files/core/rules.py`, `tests/test_core_rules.py`

**Interfaces:**
- Consumes: `para_files.core.tree.Rule`.
- Produces: `RuleMatch(rule: str, glob: str, leaf_id: str)`, `match_rule(name: str, rules: Sequence[Rule]) -> RuleMatch | None`.

Matching is case-insensitive and NFC-normalized on both sides (spec §4.1); the first rule in file order wins.

- [ ] **Step 1: Write the failing tests.** Create `tests/test_core_rules.py`:

```python
"""Signal 1: filename globs, case-insensitive, first rule wins."""

from __future__ import annotations

import unicodedata

from para_files.core.rules import RuleMatch, match_rule
from para_files.core.tree import Rule


RULES = (
    Rule(name="payslips", leaf="travail", globs=("*payslip*", "*compte de salaire*")),
    Rule(name="pdfs", leaf="docs", globs=("*.pdf",)),
)


def test_first_matching_rule_wins():
    assert match_rule("Payslip_2025-12.pdf", RULES) == RuleMatch("payslips", "*payslip*", "travail")


def test_case_insensitive():
    assert match_rule("REPORT.PDF", RULES) == RuleMatch("pdfs", "*.pdf", "docs")


def test_nfd_name_matches_nfc_glob():
    name = unicodedata.normalize("NFD", "2025.11 - Décompte de salaire.pdf")
    assert match_rule(name, RULES).rule == "payslips"


def test_no_match():
    assert match_rule("notes.txt", RULES) is None
```

- [ ] **Step 2: Run, expect failure.** `uv run pytest tests/test_core_rules.py -q` → FAIL.

- [ ] **Step 3: Implement.** Create `src/para_files/core/rules.py`:

```python
"""Signal 1, rules: owner globs on the filename (spec §4.2). Case-insensitive, NFC."""

from __future__ import annotations

import fnmatch
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from para_files.core.tree import Rule


@dataclass(frozen=True)
class RuleMatch:
    """The rule and glob that matched, and the leaf they send the file to."""

    rule: str
    glob: str
    leaf_id: str


def _fold(text: str) -> str:
    return unicodedata.normalize("NFC", text).casefold()


def match_rule(name: str, rules: Sequence[Rule]) -> RuleMatch | None:
    """First rule (file order) with a glob matching the filename."""
    folded = _fold(name)
    for rule in rules:
        for glob in rule.globs:
            if fnmatch.fnmatchcase(folded, _fold(glob)):
                return RuleMatch(rule.name, glob, rule.leaf)
    return None
```

- [ ] **Step 4: Run, expect pass.** `uv run pytest tests/test_core_rules.py -q` → 4 passed.

- [ ] **Step 5: Gate and commit.**

```bash
git add src/para_files/core/rules.py tests/test_core_rules.py
git commit -m "feat(core): signal 1, case-insensitive filename rules" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx"
```

---

### Task 4: Signal 3 — issuers

**Files:**
- Create: `src/para_files/core/issuers.py`, `tests/test_core_issuers.py`

**Interfaces:**
- Consumes: `TreeConfig` (`config.issuers.issuers`, `config.tree.leaves[...].keywords`).
- Produces: `IssuerMatch(issuer: str, pattern: str, leaf_id: str, agreed: bool)`, `match_issuer(name: str, preview: str, config: TreeConfig) -> IssuerMatch | None`, `found(pattern: str, text: str) -> bool`.

Rules:
- Search text = filename + preview, NFC and casefolded.
- A pattern of 3 characters or fewer matches only as a whole word: no letter or digit right before or after it (`_`, `-`, `.`, space and line breaks are separators). Longer patterns match as substrings. This answers the 164 short-pattern warnings of the Stage 1 tree.
- Several issuers match → the longest matching pattern wins; ties go to file order.
- Leaf: among the issuer's `leaves`, the one with the most of its own `keywords` found (same `found` rule); ties go to the issuer's order. `agreed` is true when that count is at least 1.

- [ ] **Step 1: Write the failing tests.** Create `tests/test_core_issuers.py`:

```python
"""Signal 3: issuer patterns; short ones match whole words only."""

from __future__ import annotations

import unicodedata

from para_files.core.issuers import IssuerMatch, found, match_issuer
from tests.core_helpers import make_config


def test_short_pattern_needs_a_whole_word():
    assert not found("ABC", "nabcd subscription")
    assert found("ABC", "abc_releve_2025.pdf")
    assert found("ABC", "statement from ABC.")


def test_long_pattern_is_a_substring():
    assert found("AcmeCard", "2026-01-23_acmecardfacture.pdf")


def test_keyword_agreement_picks_the_leaf():
    config = make_config()
    match = match_issuer("2026-01-23_acmecard_invoice.pdf", "", config)
    assert match == IssuerMatch("acmecard", "AcmeCard", "archives_5y_factures", agreed=True)


def test_tie_goes_to_the_first_leaf():
    config = make_config()
    match = match_issuer("acmecard_facture.pdf", "", config)
    assert match.leaf_id == "archives_10y_banques"
    assert match.agreed


def test_no_keyword_is_not_agreed():
    match = match_issuer("abc_2025.pdf", "", make_config())
    assert match == IssuerMatch("abc", "ABC", "archives_10y_banques", agreed=False)


def test_pattern_found_in_preview():
    match = match_issuer("scan_0001.pdf", "Your AcmeCard monthly statement", make_config())
    assert match.issuer == "acmecard"
    assert match.leaf_id == "archives_10y_banques"


def test_longest_pattern_wins():
    match = match_issuer("abc and acmecard.example notice", "", make_config())
    assert match.pattern == "acmecard.example"


def test_nfd_text_matches():
    config = make_config()
    name = unicodedata.normalize("NFD", "AcmeCard relevé facture.pdf")
    assert match_issuer(name, "", config).issuer == "acmecard"


def test_no_issuer():
    assert match_issuer("holiday.txt", "nothing here", make_config()) is None
```

- [ ] **Step 2: Run, expect failure.** `uv run pytest tests/test_core_issuers.py -q` → FAIL.

- [ ] **Step 3: Implement.** Create `src/para_files/core/issuers.py`:

```python
"""Signal 3, issuers: an issuer pattern in the name or preview, leaf by keyword agreement.

Patterns of SHORT characters or fewer match only as whole words, so "ABC" never fires inside
"nabcd" (spec §4.1 warns about them; this is the fix).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from para_files.core.tree import TreeConfig


SHORT = 3


@dataclass(frozen=True)
class IssuerMatch:
    """Which issuer and pattern matched, the chosen leaf, and whether a leaf keyword agreed."""

    issuer: str
    pattern: str
    leaf_id: str
    agreed: bool


def _fold(text: str) -> str:
    return unicodedata.normalize("NFC", text).casefold()


def found(pattern: str, text: str) -> bool:
    """Pattern in text (text already folded or not); short patterns as whole words."""
    needle, haystack = _fold(pattern), _fold(text)
    if len(needle) > SHORT:
        return needle in haystack
    return re.search(rf"(?<![^\W_]){re.escape(needle)}(?![^\W_])", haystack) is not None


def match_issuer(name: str, preview: str, config: TreeConfig) -> IssuerMatch | None:
    """Longest matching issuer pattern; then the issuer leaf with the most keyword hits."""
    text = _fold(f"{name}\n{preview}")
    best: tuple[str, str] | None = None
    for issuer_name, issuer in config.issuers.issuers.items():
        for pattern in issuer.patterns:
            if found(pattern, text) and (best is None or len(pattern) > len(best[1])):
                best = (issuer_name, pattern)
    if best is None:
        return None
    issuer_name, pattern = best
    scores = [
        (sum(found(keyword, text) for keyword in config.tree.leaves[leaf_id].keywords), leaf_id)
        for leaf_id in config.issuers.issuers[issuer_name].leaves
    ]
    top = max(score for score, _ in scores)
    leaf_id = next(leaf for score, leaf in scores if score == top)
    return IssuerMatch(issuer_name, pattern, leaf_id, agreed=top > 0)
```

- [ ] **Step 4: Run, expect pass.** `uv run pytest tests/test_core_issuers.py -q` → 9 passed.

- [ ] **Step 5: Gate and commit.**

```bash
git add src/para_files/core/issuers.py tests/test_core_issuers.py
git commit -m "feat(core): signal 3, issuers with whole-word short patterns" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx"
```

---

### Task 5: SQLite cache

**Files:**
- Create: `src/para_files/core/cache.py`, `tests/test_core_cache.py`

**Interfaces:**
- Produces: `Cache(path)` with `get_isbn(isbn) -> dict | None`, `put_isbn(isbn, info: dict)`, `get_verdict(sha256, fingerprint) -> dict | None`, `put_verdict(sha256, fingerprint, verdict: dict)`, `close()`; `config_fingerprint(directory: Path, model: str) -> str`.

The cache stores JSON dicts; callers convert. It is thread-safe (one connection, one lock) because classification runs in a thread pool.

- [ ] **Step 1: Write the failing tests.** Create `tests/test_core_cache.py`:

```python
"""SQLite cache: ISBN lookups and verdicts; fingerprint of the config files and model."""

from __future__ import annotations

import threading

from para_files.core.cache import Cache, config_fingerprint


def test_roundtrip_and_miss(tmp_path):
    cache = Cache(tmp_path / "c" / "cache.sqlite")
    assert cache.get_isbn("123") is None
    cache.put_isbn("123", {"title": "T"})
    assert cache.get_isbn("123") == {"title": "T"}
    assert cache.get_verdict("sha", "fp") is None
    cache.put_verdict("sha", "fp", {"leaf_id": "x"})
    assert cache.get_verdict("sha", "fp") == {"leaf_id": "x"}
    assert cache.get_verdict("sha", "other") is None
    cache.close()


def test_persists_across_instances(tmp_path):
    path = tmp_path / "cache.sqlite"
    first = Cache(path)
    first.put_verdict("sha", "fp", {"leaf_id": "x"})
    first.close()
    second = Cache(path)
    assert second.get_verdict("sha", "fp") == {"leaf_id": "x"}
    second.close()


def test_threads_share_one_cache(tmp_path):
    cache = Cache(tmp_path / "cache.sqlite")

    def work(n):
        for i in range(50):
            cache.put_isbn(f"{n}-{i}", {"i": i})
            assert cache.get_isbn(f"{n}-{i}") == {"i": i}

    threads = [threading.Thread(target=work, args=(n,)) for n in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert cache.get_isbn("3-49") == {"i": 49}
    cache.close()


def test_fingerprint_follows_files_and_model(tmp_path):
    (tmp_path / "tree.yaml").write_text("leaves: {}\n")
    base = config_fingerprint(tmp_path, "model-a")
    assert config_fingerprint(tmp_path, "model-a") == base
    assert config_fingerprint(tmp_path, "model-b") != base
    (tmp_path / "rules.yaml").write_text("rules: []\n")
    assert config_fingerprint(tmp_path, "model-a") != base
```

- [ ] **Step 2: Run, expect failure.** `uv run pytest tests/test_core_cache.py -q` → FAIL.

- [ ] **Step 3: Implement.** Create `src/para_files/core/cache.py`:

```python
"""SQLite cache (spec §4.2, robustness and caching): ISBN lookups and signal verdicts.

Verdicts are keyed by (content sha256, config fingerprint), so a preview followed by an apply
pays for model calls once, and any edit of tree/rules/issuers or of the model id starts fresh.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any


CONFIG_FILES = ("tree.yaml", "rules.yaml", "issuers.yaml")


class Cache:
    """Two key/value tables in one SQLite file; safe to share between threads."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        with self._lock, self._db:
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS isbn (isbn TEXT PRIMARY KEY, info TEXT NOT NULL)"
            )
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS verdict (sha256 TEXT NOT NULL, "
                "fingerprint TEXT NOT NULL, verdict TEXT NOT NULL, "
                "PRIMARY KEY (sha256, fingerprint))"
            )

    def _get(self, sql: str, args: tuple[str, ...]) -> dict[str, Any] | None:
        with self._lock:
            row = self._db.execute(sql, args).fetchone()
        return json.loads(row[0]) if row else None

    def _put(self, sql: str, args: tuple[str, ...]) -> None:
        with self._lock, self._db:
            self._db.execute(sql, args)

    def get_isbn(self, isbn: str) -> dict[str, Any] | None:
        """Stored lookup result, or None."""
        return self._get("SELECT info FROM isbn WHERE isbn = ?", (isbn,))

    def put_isbn(self, isbn: str, info: dict[str, Any]) -> None:
        """Store a lookup result."""
        self._put("INSERT OR REPLACE INTO isbn VALUES (?, ?)", (isbn, json.dumps(info)))

    def get_verdict(self, sha256: str, fingerprint: str) -> dict[str, Any] | None:
        """Stored verdict for this content under this config, or None."""
        return self._get(
            "SELECT verdict FROM verdict WHERE sha256 = ? AND fingerprint = ?",
            (sha256, fingerprint),
        )

    def put_verdict(self, sha256: str, fingerprint: str, verdict: dict[str, Any]) -> None:
        """Store a verdict."""
        self._put(
            "INSERT OR REPLACE INTO verdict VALUES (?, ?, ?)",
            (sha256, fingerprint, json.dumps(verdict)),
        )

    def close(self) -> None:
        """Close the connection."""
        with self._lock:
            self._db.close()


def config_fingerprint(directory: Path, model: str) -> str:
    """Hash of tree.yaml, rules.yaml, issuers.yaml (missing = empty) and the fallback model."""
    digest = hashlib.sha256()
    for name in CONFIG_FILES:
        path = directory / name
        digest.update(name.encode() + b"\0")
        digest.update((path.read_bytes() if path.exists() else b"") + b"\0")
    digest.update(model.encode())
    return digest.hexdigest()
```

- [ ] **Step 4: Run, expect pass.** `uv run pytest tests/test_core_cache.py -q` → 4 passed.

- [ ] **Step 5: Gate and commit.**

```bash
git add src/para_files/core/cache.py tests/test_core_cache.py
git commit -m "feat(core): SQLite cache for ISBN lookups and verdicts" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx"
```

---

### Task 6: Signal 2 — books (and no more cover lookups)

**Files:**
- Create: `src/para_files/core/books.py`, `tests/test_core_books.py`
- Modify: `src/para_files/utils/isbn_lookup.py` (remove the `isbnlib.cover` block, ~lines 150–158), `tests/test_isbn_lookup.py` (`test_lookup_success_with_enrichment`)

**Interfaces:**
- Consumes: `Evidence`, `Tree`, `Cache`; `BookInfo`, `lookup_isbn`, `is_title_coherent_with_filename` (`para_files.utils.isbn_lookup`); `lookup_thema_code`, `thema_to_para_path` (`para_files.utils.thema_lookup`); `score_book_structure` (`para_files.classifiers.book_detector`); `sanitize_filename`.
- Produces: `Lookup = Callable[[str], BookInfo | None]`, `BookMatch(leaf_id, confidence, isbn=None, thema=None, suggested_name=None)`, `match_book(evidence, tree, cache, lookup=lookup_isbn) -> BookMatch | None`, `book_leaf(tree) -> str | None`, `ISBN_CONFIDENCE = 1.0`, `HEURISTIC_CONFIDENCE = 0.7`.

Rules:
- Only `.pdf`, `.epub`, `.mobi`. Books go to the first `library` leaf whose `subkey` contains `{thema}`; no such leaf → no match.
- Up to 3 ISBNs are tried; a lookup counts only when its title is coherent with the filename. Only successful lookups are cached, so a network failure is retried next time.
- Without a usable ISBN: `.epub`/`.mobi`, or a PDF with ≥ 50 pages and `score_book_structure(preview) ≥ 0.3`, match at 0.7 (the band cap keeps them yellow).
- `thema` is the part of `thema_to_para_path(code)` below `3_Resources/livres/` (e.g. `U_Informatique/UB_Programmation`).
- `suggested_name` = `Author - Title (Year)` sanitized, plus the extension; no author → `Title (Year)`.

- [ ] **Step 1: Remove the cover call (test first).** In `tests/test_isbn_lookup.py`, in `test_lookup_success_with_enrichment`: replace the decorator line `@patch("isbnlib.cover")` with nothing, remove the `mock_cover: MagicMock,` parameter and the line `mock_cover.return_value = {"thumbnail": "https://example.com/cover.jpg"}`, and change the last assertion to `assert result.cover_url is None`. Add this test to the same class:

```python
    @patch("isbnlib.canonical")
    @patch("isbnlib.is_isbn10")
    @patch("isbnlib.is_isbn13")
    @patch("isbnlib.to_isbn13")
    @patch("isbnlib.meta")
    @patch("isbnlib.desc")
    @patch("isbnlib.cover")
    def test_lookup_never_fetches_a_cover(  # noqa: PLR0913
        self,
        mock_cover: MagicMock,
        mock_desc: MagicMock,
        mock_meta: MagicMock,
        mock_to_isbn13: MagicMock,
        mock_is_isbn13: MagicMock,
        mock_is_isbn10: MagicMock,
        mock_canonical: MagicMock,
    ):
        """The unused cover network call is gone (spec §4.2)."""
        mock_canonical.return_value = "9780596517748"
        mock_is_isbn10.return_value = False
        mock_is_isbn13.return_value = True
        mock_to_isbn13.return_value = "9780596517748"
        mock_meta.return_value = {"Title": "Python Cookbook", "Authors": ["A"]}
        mock_desc.return_value = ""
        assert lookup_isbn("9780596517748") is not None
        mock_cover.assert_not_called()
```

Run `uv run pytest tests/test_isbn_lookup.py -q` → the new test FAILS (`cover` called).

- [ ] **Step 2: Delete the block.** In `src/para_files/utils/isbn_lookup.py` `lookup_isbn`, delete the whole `# Try to get cover URL (optional enrichment)` block (the `try: cover = isbnlib.cover(...)` through its `except … logger.warning(...)`). Keep the `cover_url` field on `BookInfo` (always None now). Run `uv run pytest tests/test_isbn_lookup.py -q` → all pass.

- [ ] **Step 3: Write the failing tests.** Create `tests/test_core_books.py`:

```python
"""Signal 2: ISBN with a coherent lookup (green), else capped book heuristics."""

from __future__ import annotations

import dataclasses
from pathlib import Path

from para_files.core import books
from para_files.core.books import BookMatch, book_leaf, match_book
from para_files.core.cache import Cache
from para_files.core.evidence import Evidence
from para_files.core.tree import Tree
from para_files.utils.filename_sanitizer import sanitize_filename
from para_files.utils.isbn_lookup import BookInfo
from tests.core_helpers import make_config


ISBN = "9780596517748"
INFO = BookInfo(title="Python Cookbook", authors=["David Beazley"], publish_date="2013")


def ev(name, *, isbns=(), pages="", preview=""):
    return Evidence(
        path=Path("/x") / name,
        name=name,
        ext=Path(name).suffix.lower(),
        size=1,
        mtime=0.0,
        sha256="s",
        text_preview=preview,
        doc_meta={"page_count": pages} if pages else {},
        isbns=tuple(isbns),
    )


class Lookup:
    def __init__(self, info):
        self.info, self.calls = info, []

    def __call__(self, isbn):
        self.calls.append(isbn)
        return self.info


def test_isbn_with_coherent_title(tmp_path):
    lookup = Lookup(INFO)
    match = match_book(
        ev("Python Cookbook.pdf", isbns=[ISBN]), make_config().tree, Cache(tmp_path / "c"), lookup
    )
    expected = sanitize_filename("David Beazley - Python Cookbook (2013)") + ".pdf"
    assert match == BookMatch("resources_livres", 1.0, ISBN, None, expected)


def test_incoherent_title_is_ignored(tmp_path):
    match = match_book(
        ev("tax_return.pdf", isbns=[ISBN]), make_config().tree, Cache(tmp_path / "c"), Lookup(INFO)
    )
    assert match is None


def test_lookup_hits_are_cached(tmp_path):
    cache, lookup = Cache(tmp_path / "c"), Lookup(INFO)
    tree = make_config().tree
    match_book(ev("Python Cookbook.pdf", isbns=[ISBN]), tree, cache, lookup)
    match_book(ev("Python Cookbook.pdf", isbns=[ISBN]), tree, cache, lookup)
    assert lookup.calls == [ISBN]
    assert cache.get_isbn(ISBN) == dataclasses.asdict(INFO)


def test_lookup_misses_are_not_cached(tmp_path):
    cache, lookup = Cache(tmp_path / "c"), Lookup(None)
    tree = make_config().tree
    match_book(ev("a.pdf", isbns=[ISBN]), tree, cache, lookup)
    match_book(ev("a.pdf", isbns=[ISBN]), tree, cache, lookup)
    assert lookup.calls == [ISBN, ISBN]


def test_ebook_without_isbn_is_a_heuristic_match(tmp_path):
    match = match_book(ev("novel.epub"), make_config().tree, Cache(tmp_path / "c"), Lookup(None))
    assert match == BookMatch("resources_livres", 0.7)


def test_long_structured_pdf_is_a_heuristic_match(tmp_path, monkeypatch):
    monkeypatch.setattr(books, "score_book_structure", lambda _text: 0.9)
    match = match_book(
        ev("manual.pdf", pages="300", preview="Chapter 1"),
        make_config().tree,
        Cache(tmp_path / "c"),
        Lookup(None),
    )
    assert match == BookMatch("resources_livres", 0.7)


def test_short_pdf_is_not_a_book(tmp_path, monkeypatch):
    monkeypatch.setattr(books, "score_book_structure", lambda _text: 0.9)
    match = match_book(
        ev("invoice.pdf", pages="2"), make_config().tree, Cache(tmp_path / "c"), Lookup(None)
    )
    assert match is None


def test_thema_segments(tmp_path, monkeypatch):
    monkeypatch.setattr(books, "lookup_thema_code", lambda _subjects: "UB")
    monkeypatch.setattr(
        books, "thema_to_para_path", lambda _code: "3_Resources/livres/U_Informatique/UB_Prog"
    )
    info = dataclasses.replace(INFO, subjects=["Programming"])
    match = match_book(
        ev("Python Cookbook.pdf", isbns=[ISBN]),
        make_config().tree,
        Cache(tmp_path / "c"),
        Lookup(info),
    )
    assert match.thema == "U_Informatique/UB_Prog"


def test_other_extensions_and_missing_book_leaf(tmp_path):
    cache, lookup = Cache(tmp_path / "c"), Lookup(INFO)
    assert match_book(ev("a.txt", isbns=[ISBN]), make_config().tree, cache, lookup) is None
    tree = Tree.model_validate(
        {"leaves": {"docs": {"kind": "library", "path": "3_Resources/docs", "describe": "d"}}}
    )
    assert book_leaf(tree) is None
    assert match_book(ev("novel.epub"), tree, cache, lookup) is None
```

- [ ] **Step 4: Run, expect failure.** `uv run pytest tests/test_core_books.py -q` → FAIL.

- [ ] **Step 5: Implement.** Create `src/para_files/core/books.py`:

```python
"""Signal 2, books: ISBN with a coherent lookup, else a book heuristic (spec §4.2).

An ISBN match is confidence 1.0 (may be green). The heuristic is 0.7 and stays yellow, since
the preliminary bake-off showed records pulled into the library without an ISBN.
"""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Callable
from dataclasses import dataclass

from para_files.classifiers.book_detector import score_book_structure
from para_files.core.cache import Cache
from para_files.core.evidence import Evidence
from para_files.core.tree import Tree
from para_files.utils.filename_sanitizer import sanitize_filename
from para_files.utils.isbn_lookup import BookInfo, is_title_coherent_with_filename, lookup_isbn
from para_files.utils.thema_lookup import lookup_thema_code, thema_to_para_path


Lookup = Callable[[str], BookInfo | None]

BOOK_EXTENSIONS = frozenset({".pdf", ".epub", ".mobi"})
EBOOK_EXTENSIONS = frozenset({".epub", ".mobi"})
ISBN_CONFIDENCE = 1.0
HEURISTIC_CONFIDENCE = 0.7
MAX_ISBNS = 3
MIN_PAGES = 50
MIN_STRUCTURE = 0.3
LIBRARY_ROOT = "3_Resources/livres/"
YEAR = re.compile(r"\d{4}")


@dataclass(frozen=True)
class BookMatch:
    """A book: its leaf, confidence, the ISBN that proved it, thema folders and a new name."""

    leaf_id: str
    confidence: float
    isbn: str | None = None
    thema: str | None = None
    suggested_name: str | None = None


def book_leaf(tree: Tree) -> str | None:
    """The library leaf whose subkey holds {thema}: where books go."""
    return next(
        (
            leaf_id
            for leaf_id, leaf in tree.leaves.items()
            if leaf.kind == "library" and "{thema}" in (leaf.subkey or "")
        ),
        None,
    )


def cached_lookup(isbn: str, cache: Cache, lookup: Lookup) -> BookInfo | None:
    """Lookup through the cache; only hits are stored, so a network failure is retried."""
    data = cache.get_isbn(isbn)
    if data is not None:
        return BookInfo(**data)
    info = lookup(isbn)
    if info is not None:
        cache.put_isbn(isbn, dataclasses.asdict(info))
    return info


def thema_segments(info: BookInfo) -> str | None:
    """Thema folders below the library root, e.g. 'U_Informatique/UB_Programmation'."""
    code = lookup_thema_code(info.subjects) if info.subjects else None
    if code is None:
        return None
    path = thema_to_para_path(code)
    return path.removeprefix(LIBRARY_ROOT) if path.startswith(LIBRARY_ROOT) else None


def suggested_name(info: BookInfo, ext: str) -> str | None:
    """'Author - Title (Year)' + ext, sanitized; None without a title."""
    if not info.title:
        return None
    base = f"{info.authors[0]} - {info.title}" if info.authors else info.title
    year = YEAR.match(info.publish_date or "")
    if year:
        base += f" ({year.group(0)})"
    return sanitize_filename(base) + ext


def _looks_like_book(evidence: Evidence) -> bool:
    if evidence.ext in EBOOK_EXTENSIONS:
        return True
    pages = evidence.doc_meta.get("page_count", "")
    return (
        pages.isdigit()
        and int(pages) >= MIN_PAGES
        and score_book_structure(evidence.text_preview) >= MIN_STRUCTURE
    )


def match_book(
    evidence: Evidence, tree: Tree, cache: Cache, lookup: Lookup = lookup_isbn
) -> BookMatch | None:
    """ISBN match (1.0), else heuristic match (0.7), else None."""
    if evidence.ext not in BOOK_EXTENSIONS:
        return None
    leaf_id = book_leaf(tree)
    if leaf_id is None:
        return None
    for isbn in evidence.isbns[:MAX_ISBNS]:
        info = cached_lookup(isbn, cache, lookup)
        if info and info.title and is_title_coherent_with_filename(info.title, evidence.name):
            return BookMatch(
                leaf_id,
                ISBN_CONFIDENCE,
                isbn,
                thema_segments(info),
                suggested_name(info, evidence.ext),
            )
    return BookMatch(leaf_id, HEURISTIC_CONFIDENCE) if _looks_like_book(evidence) else None
```

- [ ] **Step 6: Run, expect pass.** `uv run pytest tests/test_core_books.py tests/test_isbn_lookup.py -q` → all pass.

- [ ] **Step 7: Gate and commit.**

```bash
git add src/para_files/core/books.py tests/test_core_books.py src/para_files/utils/isbn_lookup.py tests/test_isbn_lookup.py
git commit -m "feat(core): signal 2, books by ISBN; drop the unused cover lookup" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx"
```

---

### Task 7: Signal 4 — OpenRouter fallback

**Files:**
- Create: `src/para_files/core/fallback.py`, `tests/test_core_fallback.py`

**Interfaces:**
- Consumes: `Evidence`, `Tree`, `CoreSettings`, `secret_reason`, `OllamaCircuitBreaker` (`para_files.circuit_breaker`; generic despite its name: `is_open`, `record_failure()`, `record_success()`).
- Produces: `FallbackChoice(leaf_id, confidence, model, ranked)`, `OpenRouterFallback(key, models, *, complete=litellm.completion, breaker=None)` with `decide(evidence, tree) -> FallbackChoice | None`, `make_fallback(settings, *, complete=litellm.completion) -> OpenRouterFallback | None`, `leaf_menu(tree) -> dict[str, str]`, constants `OPENROUTER = "openrouter/"`, `PRIVACY`, `REASONING`.

Rules:
- Called through `litellm.completion` with model `openrouter/<model id>` and the key passed as `api_key`. Same request as the Stage 1 bake-off (`scripts/bakeoff.py` `ask_llm`): `temperature 0`, `max_tokens 4000`, JSON-schema `response_format` whose `leaf` is an enum of leaf ids, up to 3 ranked choices. OpenRouter-only fields go in `extra_body`: `provider {"zdr": true, "data_collection": "deny"}` and `reasoning {"effort": "low"}`. litellm retries transient errors (`num_retries=2`); timeout 120 s.
- Evidence sent: filename, first 2000 preview characters, first 50 archive entries. Never the path.
- A secret evidence is never sent (returns None before any call). Secret-named leaves are left out of the menu, and secret-named parts are dropped from `describe` "(contains: …)" lists.
- Models are tried in order (primary, then backup) on any litellm error or an unusable reply. When every model fails, the breaker records a failure; when it is open, no call is made.
- The API key is passed only as `api_key`, never in the messages.

- [ ] **Step 1: Write the failing tests.** Create `tests/test_core_fallback.py`:

```python
"""Signal 4: litellm to OpenRouter with ZDR on every request; secrets never sent."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from para_files.circuit_breaker import OllamaCircuitBreaker
from para_files.core.evidence import Evidence
from para_files.core.fallback import (
    FallbackChoice,
    OpenRouterFallback,
    leaf_menu,
    make_fallback,
)
from para_files.core.tree import Tree
from tests.core_helpers import make_config, make_settings


KEY = "sk-test-key"


def reply(choices):
    content = json.dumps({"choices": choices})
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class FakeComplete:
    """Stands in for litellm.completion: records calls, returns or raises in turn."""

    def __init__(self, *outcomes):
        self.outcomes, self.calls = list(outcomes), []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def ev(name="scan.pdf", preview="Monthly statement", secret=None, listing=()):
    return Evidence(
        path=Path("/private/somewhere") / name,
        name=name,
        ext=".pdf",
        size=1,
        mtime=0.0,
        sha256="s",
        secret=secret,
        text_preview=preview,
        archive_listing=listing,
    )


def test_request_carries_zdr_and_low_reasoning():
    complete = FakeComplete(reply([{"leaf": "archives_10y_banques", "confidence": 0.8}]))
    fallback = OpenRouterFallback(KEY, ["google/m1", "anthropic/m2"], complete=complete)
    choice = fallback.decide(ev(), make_config().tree)
    assert choice == FallbackChoice(
        "archives_10y_banques", 0.8, "google/m1", (("archives_10y_banques", 0.8),)
    )
    call = complete.calls[0]
    assert call["model"] == "openrouter/google/m1"
    assert call["extra_body"] == {
        "provider": {"zdr": True, "data_collection": "deny"},
        "reasoning": {"effort": "low"},
    }
    assert call["api_key"] == KEY
    assert call["temperature"] == 0
    sent = json.dumps(call["messages"])
    assert KEY not in sent
    assert "/private/somewhere" not in sent
    schema = call["response_format"]["json_schema"]["schema"]
    leaf = schema["properties"]["choices"]["items"]["properties"]["leaf"]
    assert set(leaf["enum"]) == set(make_config().tree.leaves)


def test_secret_evidence_is_never_sent():
    complete = FakeComplete()
    fallback = OpenRouterFallback(KEY, ["m1"], complete=complete)
    secret_evidence = ev(secret="name")  # noqa: S106 - a reason, not a password
    assert fallback.decide(secret_evidence, make_config().tree) is None
    assert complete.calls == []


def test_backup_model_after_an_error():
    complete = FakeComplete(
        RuntimeError("HTTP 500"),
        reply([{"leaf": "archives_5y_factures", "confidence": 0.6}]),
    )
    choice = OpenRouterFallback(KEY, ["m1", "m2"], complete=complete).decide(
        ev(), make_config().tree
    )
    assert choice.model == "m2"
    assert [call["model"] for call in complete.calls] == ["openrouter/m1", "openrouter/m2"]


def test_all_models_fail_records_a_breaker_failure():
    breaker = OllamaCircuitBreaker(threshold=1)
    complete = FakeComplete(RuntimeError("HTTP 500"), RuntimeError("HTTP 502"))
    fallback = OpenRouterFallback(KEY, ["m1", "m2"], complete=complete, breaker=breaker)
    assert fallback.decide(ev(), make_config().tree) is None
    assert breaker.is_open
    assert fallback.decide(ev(), make_config().tree) is None
    assert len(complete.calls) == 2


def test_malformed_reply_moves_on():
    complete = FakeComplete(
        SimpleNamespace(choices=[]),
        reply([{"leaf": "resources_docs", "confidence": 0.5}]),
    )
    choice = OpenRouterFallback(KEY, ["m1", "m2"], complete=complete).decide(
        ev(), make_config().tree
    )
    assert choice.model == "m2"


def test_unknown_or_malformed_choices_are_dropped():
    complete = FakeComplete(
        reply(
            [
                {"leaf": "nope", "confidence": 0.9},
                {"leaf": ["x"], "confidence": 0.9},
                {"leaf": "resources_it", "confidence": True},
                {"leaf": "archives_photos", "confidence": 1e400},
                {"leaf": "resources_docs", "confidence": 1.7},
            ]
        )
    )
    choice = OpenRouterFallback(KEY, ["m1"], complete=complete).decide(ev(), make_config().tree)
    assert choice == FallbackChoice("resources_docs", 1.0, "m1", (("resources_docs", 1.0),))


def test_empty_choices_mean_no_decision():
    complete = FakeComplete(reply([]))
    fallback = OpenRouterFallback(KEY, ["m1"], complete=complete)
    assert fallback.decide(ev(), make_config().tree) is None


def test_archive_entries_are_sent():
    complete = FakeComplete(reply([{"leaf": "resources_docs", "confidence": 0.5}]))
    fallback = OpenRouterFallback(KEY, ["m1"], complete=complete)
    fallback.decide(ev(listing=("guide/readme.txt",)), make_config().tree)
    assert "guide/readme.txt" in complete.calls[0]["messages"][1]["content"]


def test_menu_drops_secret_leaves_and_parts():
    tree = Tree.model_validate(
        {
            "leaves": {
                "areas_it": {
                    "kind": "knowledge",
                    "path": "2_Areas/IT",
                    "describe": "IT (contains: credentials, scripts)",
                },
                "areas_passwords": {
                    "kind": "knowledge",
                    "path": "2_Areas/passwords",
                    "describe": "p",
                },
            }
        }
    )
    assert leaf_menu(tree) == {"areas_it": "IT (contains: scripts)"}


def test_make_fallback(tmp_path):
    assert make_fallback(make_settings(tmp_path)) is None
    assert make_fallback(make_settings(tmp_path, fallback_enabled=True)) is None
    settings = make_settings(tmp_path, fallback_enabled=True, openrouter_api_key=KEY)
    assert isinstance(make_fallback(settings), OpenRouterFallback)
```

- [ ] **Step 2: Run, expect failure.** `uv run pytest tests/test_core_fallback.py -q` → FAIL.

- [ ] **Step 3: Implement.** Create `src/para_files/core/fallback.py`:

```python
"""Signal 4, fuzzy fallback: an OpenRouter model, called through litellm, chooses a leaf id.

Every request carries OpenRouter's provider.zdr=true and data_collection=deny (sent through
litellm's extra_body), so it fails rather than reach a provider that keeps data. A secret file
is never sent; secret-named leaves are never listed. Same request as the Stage 1 bake-off.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import litellm
from loguru import logger

from para_files.circuit_breaker import OllamaCircuitBreaker
from para_files.core.evidence import Evidence
from para_files.core.secrets import secret_reason
from para_files.core.settings import CoreSettings
from para_files.core.tree import Tree


OPENROUTER = "openrouter/"
PRIVACY = {"zdr": True, "data_collection": "deny"}
REASONING = {"effort": "low"}  # Gemini 3.8 Flash and Sonnet 5.5 refuse reasoning off
MAX_TOKENS = 4000
TIMEOUT = 120.0
RETRIES = 2
PREVIEW_CHARS = 2000
MAX_LISTED_ENTRIES = 50
MAX_CHOICES = 3
SYSTEM = (
    "You file documents into a person's PARA folder tree. Rank the three most likely folder "
    "ids from the list for this file, most likely first, each with the probability that it is "
    "the right folder. Reply only with JSON."
)
Complete = Callable[..., Any]
Ranked = list[tuple[str, float]]


class FallbackError(RuntimeError):
    """A reply that cannot be used."""


@dataclass(frozen=True)
class FallbackChoice:
    """The model's first choice, which model answered, and its ranked list."""

    leaf_id: str
    confidence: float
    model: str
    ranked: tuple[tuple[str, float], ...]


def _without_secret_parts(describe: str) -> str:
    head, marker, tail = describe.partition(" (contains: ")
    if not marker:
        return describe
    kept = [part for part in tail.removesuffix(")").split(", ") if not secret_reason(part)]
    return f"{head} (contains: {', '.join(kept)})" if kept else head


def _is_secret_leaf(leaf_id: str, path: str, describe: str) -> bool:
    head = describe.partition(" (contains: ")[0]
    return any(secret_reason(name) for name in (leaf_id, head, *Path(path).parts))


def leaf_menu(tree: Tree) -> dict[str, str]:
    """Leaf id -> describe, the only choices the model sees; no secret-named leaves."""
    return {
        leaf_id: _without_secret_parts(leaf.describe)
        for leaf_id, leaf in tree.leaves.items()
        if not _is_secret_leaf(leaf_id, leaf.path, leaf.describe)
    }


def evidence_text(evidence: Evidence) -> str:
    """Filename, preview and archive entries; never the path."""
    preview = evidence.text_preview[:PREVIEW_CHARS]
    body = preview if preview.strip() else "(no text)"
    text = f"Filename: {evidence.name}\n\nContent preview:\n{body}"
    if evidence.archive_listing:
        entries = "\n".join(evidence.archive_listing[:MAX_LISTED_ENTRIES])
        text += f"\n\nArchive entries:\n{entries}"
    return text


def messages(menu: dict[str, str], evidence: Evidence) -> list[dict[str, str]]:
    """System prompt, then the leaf list and the file evidence."""
    folders = "\n".join(f"- {leaf_id}: {describe}" for leaf_id, describe in menu.items())
    user = f"Folders:\n{folders}\n\nFile:\n{evidence_text(evidence)}"
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def response_format(menu: dict[str, str]) -> dict[str, Any]:
    """JSON schema: up to 3 choices, each an enum leaf id with a confidence."""
    choice = {
        "type": "object",
        "additionalProperties": False,
        "required": ["leaf", "confidence"],
        "properties": {
            "leaf": {"type": "string", "enum": list(menu)},
            "confidence": {"type": "number"},
        },
    }
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["choices"],
        "properties": {
            "choices": {"type": "array", "items": choice, "minItems": 1, "maxItems": MAX_CHOICES}
        },
    }
    return {
        "type": "json_schema",
        "json_schema": {"name": "filing", "strict": True, "schema": schema},
    }


def _probability(value: object) -> float | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except OverflowError:
        return None
    return max(0.0, min(1.0, number)) if math.isfinite(number) else None


def parse_choices(content: str | None, menu: dict[str, str]) -> Ranked:
    """Ranked (leaf, probability); unknown, repeated or malformed choices dropped."""
    match = re.search(r"\{.*\}", content or "", re.DOTALL)
    try:
        data = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError as exc:
        msg = "reply is not JSON"
        raise FallbackError(msg) from exc
    choices = data.get("choices") if isinstance(data, dict) else None
    if not isinstance(choices, list):
        msg = "reply has no choices list"
        raise FallbackError(msg)
    ranked: Ranked = []
    for item in choices:
        if not isinstance(item, dict):
            continue
        leaf, probability = item.get("leaf"), _probability(item.get("confidence"))
        if not isinstance(leaf, str) or leaf not in menu or probability is None:
            continue
        if leaf not in {seen for seen, _ in ranked}:
            ranked.append((leaf, probability))
    return ranked[:MAX_CHOICES]


class OpenRouterFallback:
    """Signal 4: primary model, then backup, through litellm; behind a circuit breaker."""

    def __init__(
        self,
        key: str,
        models: Sequence[str],
        *,
        complete: Complete = litellm.completion,
        breaker: OllamaCircuitBreaker | None = None,
    ) -> None:
        self._key = key
        self._models = tuple(models)
        self._complete = complete
        self._breaker = breaker or OllamaCircuitBreaker()

    def _ask(self, model: str, menu: dict[str, str], evidence: Evidence) -> Ranked:
        response = self._complete(
            model=f"{OPENROUTER}{model}",
            messages=messages(menu, evidence),
            api_key=self._key,
            temperature=0,
            max_tokens=MAX_TOKENS,
            response_format=response_format(menu),
            extra_body={"provider": PRIVACY, "reasoning": REASONING},
            timeout=TIMEOUT,
            num_retries=RETRIES,
        )
        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, TypeError) as exc:
            msg = f"malformed reply: {type(exc).__name__}"
            raise FallbackError(msg) from exc
        return parse_choices(content, menu)

    def decide(self, evidence: Evidence, tree: Tree) -> FallbackChoice | None:
        """First choice of the first model that answers; None for secrets or failures."""
        if evidence.secret is not None or self._breaker.is_open:
            return None
        menu = leaf_menu(tree)
        if not menu:
            return None
        for model in self._models:
            try:
                ranked = self._ask(model, menu, evidence)
            except Exception as exc:  # noqa: BLE001 - any provider error moves on to the backup
                logger.warning("fallback {} failed on {}: {}", model, evidence.name, exc)
                continue
            self._breaker.record_success()
            if not ranked:
                return None
            leaf_id, confidence = ranked[0]
            return FallbackChoice(leaf_id, confidence, model, tuple(ranked))
        self._breaker.record_failure()
        return None


def make_fallback(
    settings: CoreSettings, *, complete: Complete = litellm.completion
) -> OpenRouterFallback | None:
    """The configured fallback, or None when it is off or no key is set."""
    if not settings.fallback_enabled or settings.openrouter_api_key is None:
        return None
    return OpenRouterFallback(
        settings.openrouter_api_key.get_secret_value(),
        (settings.fallback_model, settings.fallback_backup_model),
        complete=complete,
    )
```

- [ ] **Step 4: Run, expect pass.** `uv run pytest tests/test_core_fallback.py -q` → 10 passed.

- [ ] **Step 5: Gate and commit.**

```bash
git add src/para_files/core/fallback.py tests/test_core_fallback.py
git commit -m "feat(core): signal 4, OpenRouter fallback through litellm with ZDR on every request" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx"
```

---

### Task 8: Cascade, bands and target directory

**Files:**
- Create: `src/para_files/core/decide.py`, `tests/test_core_decide.py`

**Interfaces:**
- Consumes: Tasks 1–7 (`extract`, `match_rule`, `match_book`/`Lookup`, `match_issuer`, `FallbackChoice`, `Cache`, `CoreSettings`, `TreeConfig`, `Leaf`, `Kind`).
- Produces:
  - `Band = Literal["green", "yellow", "red"]`
  - `Fallback` (Protocol): `decide(evidence: Evidence, tree: Tree) -> FallbackChoice | None`
  - `Verdict(leaf_id, signal, confidence, summary, isbn=None, issuer=None, thema=None, suggested_name=None)` (frozen)
  - `Decision(path, sha256, leaf_id, target_dir, band, signal, confidence, evidence_summary, kind=None, suggested_name=None)` (frozen); `target_dir` is relative to the PARA root
  - `Context(config, settings, cache, fingerprint, confirmed={}, fallback=None, lookup=lookup_isbn)` (mutable dataclass)
  - `classify(path: Path, ctx: Context) -> Decision`, `run_signals(evidence, ctx) -> Verdict`, `band_for(verdict, kind, ctx) -> Band`, `target_dir(leaf, evidence, verdict) -> str`, `file_date(evidence) -> tuple[str | None, str | None]`

Rules (spec §4.2 Bands, §4.1 caps):
- Order: rules, books, issuers, fallback; first verdict wins. A signal that raises `Exception` is logged and the next one runs; `KeyboardInterrupt` propagates.
- Secret evidence → red, signal `secret`, no signal runs.
- Verdicts are cached by `(sha256, ctx.fingerprint)`; a verdict without a leaf is never cached. Band and target are computed on every call (they depend on `ctx.confirmed` and the file's dates).
- Bands: no leaf → red. Fallback below `fallback_red` → red. Rules → green. Books → green only with an ISBN, else yellow. Issuers and fallback → green only when the leaf's kind has ≥ `calibration_min` owner-confirmed decisions **and** confidence ≥ `issuers_green` / `fallback_green`; else yellow. Then caps: `knowledge` → at most yellow; `library` → green only with an ISBN or an issuer match.
- Issuer confidence: 0.95 with keyword agreement, 0.8 without.
- Target: leaf path plus the subkey; `{year}`/`{month}` from EXIF date, else a date in the filename (`2025-12`, `2025.11`, `2025_12_22`, `2025`); `{issuer}` the issuer key; `{thema}` the book's thema folders. Any placeholder that cannot be filled → the leaf root.

- [ ] **Step 1: Write the failing tests.** Create `tests/test_core_decide.py`:

```python
"""The cascade: first signal wins; bands, caps, calibration and targets."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from para_files.core import decide
from para_files.core.cache import Cache
from para_files.core.decide import Context, Verdict, classify, target_dir
from para_files.core.evidence import Evidence
from para_files.core.fallback import FallbackChoice
from tests.core_helpers import make_config, make_settings


class FakeFallback:
    def __init__(self, leaf="archives_5y_factures", confidence=0.95):
        self.leaf, self.confidence, self.calls = leaf, confidence, []

    def decide(self, evidence, tree):
        self.calls.append(evidence.name)
        if self.leaf is None:
            return None
        return FallbackChoice(self.leaf, self.confidence, "m1", ((self.leaf, self.confidence),))


def make_ctx(tmp_path, *, fallback=None, confirmed=None):
    settings = make_settings(tmp_path)
    return Context(
        config=make_config(),
        settings=settings,
        cache=Cache(settings.cache_path),
        fingerprint="fp",
        confirmed=confirmed or {},
        fallback=fallback,
        lookup=lambda _isbn: None,
    )


def inbox_file(ctx, name, text="x"):
    path = ctx.settings.para_root / "0_Inbox" / name
    path.write_text(text)
    return path


def test_rule_is_green_with_year(tmp_path):
    ctx = make_ctx(tmp_path)
    d = classify(inbox_file(ctx, "Payslip_2025-12-22.txt"), ctx)
    assert (d.leaf_id, d.signal, d.band, d.kind) == (
        "archives_10y_travail",
        "rules",
        "green",
        "record",
    )
    assert d.target_dir == "4_Archives/10y_travail/2025"


def test_unfillable_subkey_goes_to_leaf_root(tmp_path):
    ctx = make_ctx(tmp_path)
    assert classify(inbox_file(ctx, "Payslip.txt"), ctx).target_dir == "4_Archives/10y_travail"


def test_knowledge_is_capped_at_yellow(tmp_path):
    ctx = make_ctx(tmp_path)
    d = classify(inbox_file(ctx, "notes.md"), ctx)
    assert (d.leaf_id, d.band) == ("resources_it", "yellow")


def test_library_by_rule_is_capped_at_yellow(tmp_path):
    ctx = make_ctx(tmp_path)
    d = classify(inbox_file(ctx, "storage_whitepaper.txt"), ctx)
    assert (d.leaf_id, d.band) == ("resources_docs", "yellow")


def test_issuer_is_yellow_before_calibration(tmp_path):
    ctx = make_ctx(tmp_path)
    d = classify(inbox_file(ctx, "2026-01-23_acmecard_facture.txt", "AcmeCard"), ctx)
    assert (d.leaf_id, d.signal, d.band) == ("archives_10y_banques", "issuers", "yellow")
    assert d.target_dir == "4_Archives/10y_banques/acmecard/2026"
    assert d.confidence == 0.95


def test_issuer_with_keyword_is_green_after_calibration(tmp_path):
    ctx = make_ctx(tmp_path, confirmed={"record": 100})
    d = classify(inbox_file(ctx, "2026-01-23_acmecard_facture.txt", "AcmeCard"), ctx)
    assert d.band == "green"


def test_issuer_without_keyword_stays_yellow_after_calibration(tmp_path):
    ctx = make_ctx(tmp_path, confirmed={"record": 100})
    d = classify(inbox_file(ctx, "abc_2025.txt", "hello"), ctx)
    assert (d.signal, d.confidence, d.band) == ("issuers", 0.8, "yellow")


def test_fallback_bands(tmp_path):
    ctx = make_ctx(tmp_path, fallback=FakeFallback(confidence=0.95))
    assert classify(inbox_file(ctx, "random.txt", "hello"), ctx).band == "yellow"
    ctx.confirmed = {"record": 100}
    assert classify(inbox_file(ctx, "random2.txt", "hello 2"), ctx).band == "green"
    ctx.fallback = FakeFallback(confidence=0.1)
    assert classify(inbox_file(ctx, "random3.txt", "hello 3"), ctx).band == "red"


def test_secret_is_red_and_never_reaches_a_signal(tmp_path):
    fallback = FakeFallback()
    ctx = make_ctx(tmp_path, fallback=fallback)
    d = classify(inbox_file(ctx, "Payslip_passwords.txt"), ctx)
    assert (d.band, d.signal, d.leaf_id) == ("red", "secret", None)
    assert fallback.calls == []


def test_failing_signal_hands_over(tmp_path, monkeypatch):
    def boom(*_args):
        msg = "broken rules"
        raise RuntimeError(msg)

    monkeypatch.setattr(decide, "match_rule", boom)
    ctx = make_ctx(tmp_path, fallback=FakeFallback())
    d = classify(inbox_file(ctx, "Payslip_2025.txt"), ctx)
    assert d.signal == "fallback"


def test_keyboard_interrupt_propagates(tmp_path, monkeypatch):
    def stop(*_args):
        raise KeyboardInterrupt

    monkeypatch.setattr(decide, "match_rule", stop)
    ctx = make_ctx(tmp_path)
    with pytest.raises(KeyboardInterrupt):
        classify(inbox_file(ctx, "a.txt"), ctx)


def test_verdict_is_cached_but_band_is_recomputed(tmp_path):
    fallback = FakeFallback(confidence=0.95)
    ctx = make_ctx(tmp_path, fallback=fallback)
    path = inbox_file(ctx, "random.txt", "same")
    assert classify(path, ctx).band == "yellow"
    ctx.confirmed = {"record": 100}
    assert classify(path, ctx).band == "green"
    assert fallback.calls == ["random.txt"]


def test_no_leaf_is_red_and_not_cached(tmp_path):
    fallback = FakeFallback(leaf=None)
    ctx = make_ctx(tmp_path, fallback=fallback)
    path = inbox_file(ctx, "random.txt", "same")
    assert classify(path, ctx).band == "red"
    assert classify(path, ctx).band == "red"
    assert fallback.calls == ["random.txt", "random.txt"]


def test_target_from_exif_date():
    leaf = make_config().tree.leaves["archives_photos"]
    evidence = Evidence(
        path=Path("/x/IMG_1.jpg"),
        name="IMG_1.jpg",
        ext=".jpg",
        size=1,
        mtime=0.0,
        sha256="s",
        exif_date=datetime(2024, 5, 1),
    )
    verdict = Verdict("archives_photos", "rules", 1.0, "rule")
    assert target_dir(leaf, evidence, verdict) == "4_Archives/photos/2024/05"
```

- [ ] **Step 2: Run, expect failure.** `uv run pytest tests/test_core_decide.py -q` → FAIL.

- [ ] **Step 3: Implement.** Create `src/para_files/core/decide.py`:

```python
"""The cascade (spec §4.2): evidence -> first deciding signal -> band -> target directory."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal, Protocol

from loguru import logger

from para_files.core.books import Lookup, match_book
from para_files.core.cache import Cache
from para_files.core.evidence import Evidence, extract
from para_files.core.fallback import FallbackChoice
from para_files.core.issuers import match_issuer
from para_files.core.rules import match_rule
from para_files.core.settings import CoreSettings
from para_files.core.tree import Kind, Leaf, Tree, TreeConfig
from para_files.utils.isbn_lookup import lookup_isbn


Band = Literal["green", "yellow", "red"]
RULE_CONFIDENCE = 1.0
ISSUER_AGREED = 0.95
ISSUER_ALONE = 0.8
DATE_IN_NAME = re.compile(r"(?<!\d)((?:19|20)\d{2})(?:[-_. ]?(0[1-9]|1[0-2]))?(?!\d)")


class Fallback(Protocol):
    """Signal 4 as the cascade sees it."""

    def decide(self, evidence: Evidence, tree: Tree) -> FallbackChoice | None:
        """Leaf choice for this evidence, or None."""


@dataclass(frozen=True)
class Verdict:
    """What the winning signal said; cached by content hash and config fingerprint."""

    leaf_id: str | None
    signal: str
    confidence: float
    summary: str
    isbn: str | None = None
    issuer: str | None = None
    thema: str | None = None
    suggested_name: str | None = None


@dataclass(frozen=True)
class Decision:
    """One file's outcome: leaf, target (relative to the PARA root), band and why."""

    path: Path
    sha256: str
    leaf_id: str | None
    target_dir: str | None
    band: Band
    signal: str
    confidence: float
    evidence_summary: str
    kind: Kind | None = None
    suggested_name: str | None = None


@dataclass
class Context:
    """Everything classify() needs, built once per run."""

    config: TreeConfig
    settings: CoreSettings
    cache: Cache
    fingerprint: str
    confirmed: Mapping[str, int] = field(default_factory=dict)
    fallback: Fallback | None = None
    lookup: Lookup = lookup_isbn


def _rules(evidence: Evidence, ctx: Context) -> Verdict | None:
    match = match_rule(evidence.name, ctx.config.rules.rules)
    if match is None:
        return None
    return Verdict(
        match.leaf_id, "rules", RULE_CONFIDENCE, f"rule {match.rule!r} glob {match.glob!r}"
    )


def _books(evidence: Evidence, ctx: Context) -> Verdict | None:
    match = match_book(evidence, ctx.config.tree, ctx.cache, ctx.lookup)
    if match is None:
        return None
    summary = f"ISBN {match.isbn}" if match.isbn else "book heuristics (no ISBN)"
    return Verdict(
        match.leaf_id,
        "books",
        match.confidence,
        summary,
        isbn=match.isbn,
        thema=match.thema,
        suggested_name=match.suggested_name,
    )


def _issuers(evidence: Evidence, ctx: Context) -> Verdict | None:
    match = match_issuer(evidence.name, evidence.text_preview, ctx.config)
    if match is None:
        return None
    summary = f"issuer {match.issuer!r} pattern {match.pattern!r}"
    return Verdict(
        match.leaf_id,
        "issuers",
        ISSUER_AGREED if match.agreed else ISSUER_ALONE,
        summary + (" + leaf keyword" if match.agreed else ""),
        issuer=match.issuer,
    )


def _fallback(evidence: Evidence, ctx: Context) -> Verdict | None:
    if ctx.fallback is None:
        return None
    choice = ctx.fallback.decide(evidence, ctx.config.tree)
    if choice is None:
        return None
    ranked = ", ".join(f"{leaf} {p:.2f}" for leaf, p in choice.ranked)
    return Verdict(choice.leaf_id, "fallback", choice.confidence, f"{choice.model}: {ranked}")


SIGNALS: tuple[tuple[str, Callable[[Evidence, Context], Verdict | None]], ...] = (
    ("rules", _rules),
    ("books", _books),
    ("issuers", _issuers),
    ("fallback", _fallback),
)
NO_VERDICT = Verdict(None, "none", 0.0, "no signal decided")


def run_signals(evidence: Evidence, ctx: Context) -> Verdict:
    """First signal with a verdict wins; a failing signal hands over to the next one."""
    for name, signal in SIGNALS:
        try:
            verdict = signal(evidence, ctx)
        except Exception as exc:  # noqa: BLE001 - KeyboardInterrupt is not an Exception
            logger.warning("signal {} failed on {}: {}", name, evidence.name, exc)
            continue
        if verdict is not None:
            return verdict
    return NO_VERDICT


def file_date(evidence: Evidence) -> tuple[str | None, str | None]:
    """(year, month) from EXIF, else from a date in the filename."""
    if evidence.exif_date is not None:
        return f"{evidence.exif_date.year:04d}", f"{evidence.exif_date.month:02d}"
    match = DATE_IN_NAME.search(evidence.name)
    return (match.group(1), match.group(2)) if match else (None, None)


def target_dir(leaf: Leaf, evidence: Evidence, verdict: Verdict) -> str:
    """Leaf path plus its filled subkey; any unfillable placeholder -> the leaf root."""
    if not leaf.subkey:
        return leaf.path
    year, month = file_date(evidence)
    values = {
        "{year}": year,
        "{month}": month,
        "{issuer}": verdict.issuer,
        "{thema}": verdict.thema,
    }
    parts = [values[placeholder] for placeholder in leaf.subkey.split("/")]
    filled = [part for part in parts if part]
    if len(filled) != len(parts):
        return leaf.path
    return "/".join([leaf.path, *filled])


def _cap(band: Band, kind: Kind, verdict: Verdict) -> Band:
    if band != "green":
        return band
    if kind == "knowledge":
        return "yellow"
    if kind == "library" and verdict.isbn is None and verdict.signal != "issuers":
        return "yellow"
    return band


def band_for(verdict: Verdict, kind: Kind, ctx: Context) -> Band:
    """Band from the signal, its confidence and the calibration state, then the kind caps."""
    settings = ctx.settings
    if verdict.leaf_id is None:
        return "red"
    if verdict.signal == "fallback" and verdict.confidence < settings.fallback_red:
        return "red"
    band: Band
    if verdict.signal == "rules":
        band = "green"
    elif verdict.signal == "books":
        band = "green" if verdict.isbn else "yellow"
    else:
        threshold = (
            settings.issuers_green if verdict.signal == "issuers" else settings.fallback_green
        )
        calibrated = ctx.confirmed.get(kind, 0) >= settings.calibration_min
        band = "green" if calibrated and verdict.confidence >= threshold else "yellow"
    return _cap(band, kind, verdict)


def _verdict(evidence: Evidence, ctx: Context) -> Verdict:
    if evidence.secret is not None:
        return Verdict(None, "secret", 0.0, f"secret ({evidence.secret}): never sent, never moved")
    cached = ctx.cache.get_verdict(evidence.sha256, ctx.fingerprint)
    if cached is not None:
        return Verdict(**cached)
    verdict = run_signals(evidence, ctx)
    if verdict.leaf_id is not None:
        ctx.cache.put_verdict(evidence.sha256, ctx.fingerprint, asdict(verdict))
    return verdict


def classify(path: Path, ctx: Context) -> Decision:
    """Extract, decide, band and place one file. Pure: nothing on disk changes."""
    evidence = extract(path, root=ctx.settings.para_root, preview_chars=ctx.settings.preview_chars)
    verdict = _verdict(evidence, ctx)
    leaf = ctx.config.tree.leaves.get(verdict.leaf_id) if verdict.leaf_id else None
    if leaf is None:
        return Decision(
            path=evidence.path,
            sha256=evidence.sha256,
            leaf_id=None,
            target_dir=None,
            band="red",
            signal=verdict.signal,
            confidence=verdict.confidence,
            evidence_summary=verdict.summary,
        )
    return Decision(
        path=evidence.path,
        sha256=evidence.sha256,
        leaf_id=verdict.leaf_id,
        target_dir=target_dir(leaf, evidence, verdict),
        band=band_for(verdict, leaf.kind, ctx),
        signal=verdict.signal,
        confidence=verdict.confidence,
        evidence_summary=verdict.summary,
        kind=leaf.kind,
        suggested_name=verdict.suggested_name,
    )
```

- [ ] **Step 4: Run, expect pass.** `uv run pytest tests/test_core_decide.py -q` → 14 passed.

- [ ] **Step 5: Gate and commit.**

```bash
git add src/para_files/core/decide.py tests/test_core_decide.py
git commit -m "feat(core): cascade with bands, kind caps, calibration cap and targets" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx"
```

---

### Task 9: Journal and calibration counts

**Files:**
- Create: `src/para_files/core/journal.py`, `tests/test_core_journal.py`

**Interfaces:**
- Consumes: `Tree`.
- Produces: `DecidedBy = Literal["auto", "owner"]`, `journal_dir(state_dir) -> Path`, `new_run_id(state_dir, now=None) -> str`, `Journal(state_dir, run_id)` (context manager; `.run_id`, `.path`, `append(entry: dict)`, `close()`), `read_run(state_dir, run_id) -> list[dict]`, `run_ids(state_dir) -> list[str]`, `last_run_id(state_dir) -> str | None`, `mark_undone(state_dir, run_id)`, `is_undone(state_dir, run_id) -> bool`, `confirmed_counts(state_dir, tree) -> dict[str, int]`.

Rules:
- One file per run: `<state_dir>/journal/<run-id>.jsonl`, `run-id = YYYYMMDD-HHMMSS` (local time), `-2`, `-3`… when taken. The file is created exclusively.
- Every line gets `run_id` and is flushed and fsynced before `append` returns.
- An undone run gets a `<run-id>.undone` marker; `last_run_id` and `confirmed_counts` ignore it.
- `confirmed_counts`: per leaf kind, the `move` entries with `decided_by == "owner"` whose `leaf` is still in the tree.

- [ ] **Step 1: Write the failing tests.** Create `tests/test_core_journal.py`:

```python
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
```

- [ ] **Step 2: Run, expect failure.** `uv run pytest tests/test_core_journal.py -q` → FAIL.

- [ ] **Step 3: Implement.** Create `src/para_files/core/journal.py`:

```python
"""Run journal (spec §4.3): one JSONL file per run, one flushed line per operation.

Owner-decided moves are the labels of spec §4.5: confirmed_counts() feeds the calibration cap.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Self

from para_files.core.tree import Tree


DecidedBy = Literal["auto", "owner"]
RUN_ID_FORMAT = "%Y%m%d-%H%M%S"


def journal_dir(state_dir: Path) -> Path:
    """Where run journals live."""
    return state_dir / "journal"


def new_run_id(state_dir: Path, now: datetime | None = None) -> str:
    """YYYYMMDD-HHMMSS (local time), with -2, -3… when already taken."""
    base = (now or datetime.now().astimezone()).strftime(RUN_ID_FORMAT)
    run_id, counter = base, 2
    while (journal_dir(state_dir) / f"{run_id}.jsonl").exists():
        run_id, counter = f"{base}-{counter}", counter + 1
    return run_id


class Journal:
    """Append-only journal of one run; each line is on disk before append() returns."""

    def __init__(self, state_dir: Path, run_id: str) -> None:
        directory = journal_dir(state_dir)
        directory.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self.path = directory / f"{run_id}.jsonl"
        self._handle = self.path.open("x", encoding="utf-8")

    def append(self, entry: dict[str, Any]) -> None:
        """Write one operation, flush and fsync."""
        line = json.dumps({"run_id": self.run_id, **entry}, ensure_ascii=False)
        self._handle.write(line + "\n")
        self._handle.flush()
        os.fsync(self._handle.fileno())

    def close(self) -> None:
        """Close the file."""
        self._handle.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def read_run(state_dir: Path, run_id: str) -> list[dict[str, Any]]:
    """Entries of one run, in order."""
    text = (journal_dir(state_dir) / f"{run_id}.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.split("\n") if line.strip()]


def _marker(state_dir: Path, run_id: str) -> Path:
    return journal_dir(state_dir) / f"{run_id}.undone"


def mark_undone(state_dir: Path, run_id: str) -> None:
    """Record that a run was undone."""
    _marker(state_dir, run_id).touch()


def is_undone(state_dir: Path, run_id: str) -> bool:
    """True when the run was undone."""
    return _marker(state_dir, run_id).exists()


def run_ids(state_dir: Path) -> list[str]:
    """Every journaled run, oldest first."""
    directory = journal_dir(state_dir)
    return sorted(path.stem for path in directory.glob("*.jsonl")) if directory.is_dir() else []


def last_run_id(state_dir: Path) -> str | None:
    """Newest run that was not undone."""
    live = [run_id for run_id in run_ids(state_dir) if not is_undone(state_dir, run_id)]
    return live[-1] if live else None


def confirmed_counts(state_dir: Path, tree: Tree) -> dict[str, int]:
    """Owner-decided moves per leaf kind, over every run not undone."""
    counts: Counter[str] = Counter()
    for run_id in run_ids(state_dir):
        if is_undone(state_dir, run_id):
            continue
        for entry in read_run(state_dir, run_id):
            leaf = tree.leaves.get(str(entry.get("leaf")))
            if entry.get("op") == "move" and entry.get("decided_by") == "owner" and leaf:
                counts[leaf.kind] += 1
    return dict(counts)
```


- [ ] **Step 4: Run, expect pass.** `uv run pytest tests/test_core_journal.py -q` → 5 passed.

- [ ] **Step 5: Gate and commit.**

```bash
git add src/para_files/core/journal.py tests/test_core_journal.py
git commit -m "feat(core): run journal and owner-confirmed counts per kind" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx"
```

---

### Task 10: Apply

**Files:**
- Create: `src/para_files/core/apply.py`, `tests/test_core_apply.py`

**Interfaces:**
- Consumes: `Decision` (Task 8), `sha256_of` (Task 2), `Journal`, `DecidedBy` (Task 9), `TreeConfig`, `sanitize_filename`.
- Produces: `Op(decision: Decision, leaf_id: str, decided_by: DecidedBy)`, `ApplyReport(moved, trashed, skipped, removed_dirs)`, `apply_ops(ops, *, config, para_root, journal, roots) -> ApplyReport`, `TRASH = ".trash"`.

Rules (spec §4.3), one operation at a time, in order:
1. Skip with a reason (`report.skipped`, nothing changes): signal `secret`; unknown leaf; source missing or a symlink; source sha256 differs from the decision ("changed since the preview"); target outside the PARA root after `resolve()`; already in place (same folder, same name).
2. Target folder: the decision's `target_dir` when `op.leaf_id == decision.leaf_id`, else the corrected leaf's root path. Name: `sanitize_filename(suggested_name, preserve_extension=True)` when set, else the current name.
3. Target name free → move. Same sha256 already there → move the source to `<root>/.trash/<run-id>/<source path relative to root>` (op `trash`). Different content → ` (2)`, ` (3)`… suffix.
4. Every folder the run creates is journaled as `mkdir` (top-down) so `undo` can remove it. After each move or trash: journal `{op, src, dst, sha256, size, leaf, proposed_leaf, decided_by, signal, confidence}`.
5. After all operations: source folders emptied by this run are removed, bottom-up, only strictly inside one of `roots`; each is journaled as `rmdir`.
Nothing is deleted or overwritten.

- [ ] **Step 1: Write the failing tests.** Create `tests/test_core_apply.py`:

```python
"""apply_ops: contained, never overwriting, journaled; emptied folders removed."""

from __future__ import annotations

from para_files.core import apply as apply_mod
from para_files.core.apply import Op, apply_ops
from para_files.core.decide import Decision
from para_files.core.evidence import sha256_of
from para_files.core.journal import Journal, read_run
from para_files.utils.filename_sanitizer import sanitize_filename
from tests.core_helpers import make_config, make_settings


def setup(tmp_path):
    settings = make_settings(tmp_path)
    return settings.para_root.resolve(), settings.state_dir  # apply reports resolved paths


def inbox(root, rel, text="payslip"):
    path = root / "0_Inbox" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def decision(path, *, leaf="archives_10y_travail", target="4_Archives/10y_travail/2025", **kw):
    values = {
        "path": path,
        "sha256": sha256_of(path),
        "leaf_id": leaf,
        "target_dir": target,
        "band": "green",
        "signal": "rules",
        "confidence": 1.0,
        "evidence_summary": "rule",
        "kind": "record",
    }
    values.update(kw)
    return Decision(**values)


def run(root, state, ops, roots=None):
    with Journal(state, "r1") as journal:
        report = apply_ops(
            ops,
            config=make_config(),
            para_root=root,
            journal=journal,
            roots=roots or [root / "0_Inbox"],
        )
    return report, read_run(state, "r1")


def test_move_is_journaled(tmp_path):
    root, state = setup(tmp_path)
    src = inbox(root, "Payslip_2025.txt")
    report, entries = run(root, state, [Op(decision(src), "archives_10y_travail", "auto")])
    dst = root / "4_Archives" / "10y_travail" / "2025" / "Payslip_2025.txt"
    assert dst.read_text() == "payslip"
    assert not src.exists()
    assert report.moved == [(src, dst)]
    assert [e["op"] for e in entries] == ["mkdir", "mkdir", "move"]
    move = entries[-1]
    assert move["src"] == str(src)
    assert move["dst"] == str(dst)
    assert (move["leaf"], move["proposed_leaf"], move["decided_by"]) == (
        "archives_10y_travail",
        "archives_10y_travail",
        "auto",
    )
    assert move["sha256"] == sha256_of(dst)


def test_same_content_goes_to_trash(tmp_path):
    root, state = setup(tmp_path)
    existing = root / "4_Archives" / "10y_travail" / "2025" / "Payslip_2025.txt"
    existing.parent.mkdir(parents=True)
    existing.write_text("payslip")
    src = inbox(root, "Payslip_2025.txt")
    report, entries = run(root, state, [Op(decision(src), "archives_10y_travail", "auto")])
    trashed = root / ".trash" / "r1" / "0_Inbox" / "Payslip_2025.txt"
    assert trashed.read_text() == "payslip"
    assert existing.read_text() == "payslip"
    assert report.trashed == [(src, trashed)]
    assert entries[-1]["op"] == "trash"


def test_different_content_gets_a_suffix(tmp_path):
    root, state = setup(tmp_path)
    existing = root / "4_Archives" / "10y_travail" / "2025" / "Payslip_2025.txt"
    existing.parent.mkdir(parents=True)
    existing.write_text("older payslip")
    src = inbox(root, "Payslip_2025.txt")
    run(root, state, [Op(decision(src), "archives_10y_travail", "auto")])
    assert existing.read_text() == "older payslip"
    assert (existing.parent / "Payslip_2025 (2).txt").read_text() == "payslip"


def test_target_outside_root_is_refused(tmp_path):
    root, state = setup(tmp_path)
    src = inbox(root, "a.txt")
    op = Op(decision(src, target="4_Archives/../../outside"), "archives_10y_travail", "auto")
    report, entries = run(root, state, [op])
    assert report.skipped == [(src, "target outside the PARA root")]
    assert src.exists()
    assert not (tmp_path / "outside").exists()
    assert entries == []


def test_secret_unknown_leaf_missing_and_changed_are_skipped(tmp_path):
    root, state = setup(tmp_path)
    secret = inbox(root, "keys.txt")
    changed = inbox(root, "changed.txt")
    changed_decision = decision(changed)
    changed.write_text("edited after preview")
    missing = inbox(root, "missing.txt")
    missing_decision = decision(missing)
    missing.unlink()
    ops = [
        Op(decision(secret, signal="secret"), "archives_10y_travail", "auto"),
        Op(decision(inbox(root, "b.txt")), "no_such_leaf", "owner"),
        Op(missing_decision, "archives_10y_travail", "auto"),
        Op(changed_decision, "archives_10y_travail", "auto"),
    ]
    report, _ = run(root, state, ops)
    assert [reason for _, reason in report.skipped] == [
        "secret",
        "unknown leaf 'no_such_leaf'",
        "source missing",
        "changed since the preview",
    ]
    assert secret.exists()


def test_already_in_place(tmp_path):
    root, state = setup(tmp_path)
    folder = root / "4_Archives" / "10y_travail" / "2025"
    folder.mkdir(parents=True)
    src = folder / "Payslip_2025.txt"
    src.write_text("payslip")
    report, _ = run(root, state, [Op(decision(src), "archives_10y_travail", "auto")])
    assert report.skipped == [(src, "already in place")]


def test_suggested_name_is_sanitized(tmp_path):
    root, state = setup(tmp_path)
    src = inbox(root, "scan.pdf")
    op = Op(decision(src, suggested_name="A: B?.pdf"), "archives_10y_travail", "auto")
    run(root, state, [op])
    name = sanitize_filename("A: B?.pdf", preserve_extension=True)
    assert (root / "4_Archives" / "10y_travail" / "2025" / name).exists()


def test_owner_correction_goes_to_the_leaf_root(tmp_path):
    root, state = setup(tmp_path)
    src = inbox(root, "Payslip_2025.txt")
    _, entries = run(root, state, [Op(decision(src), "archives_5y_factures", "owner")])
    assert (root / "4_Archives" / "5y_factures" / "Payslip_2025.txt").exists()
    move = entries[-1]
    assert (move["leaf"], move["proposed_leaf"], move["decided_by"]) == (
        "archives_5y_factures",
        "archives_10y_travail",
        "owner",
    )


def test_emptied_folders_are_removed_inside_roots_only(tmp_path):
    root, state = setup(tmp_path)
    src = inbox(root, "batch/sub/Payslip_2025.txt")
    keep = inbox(root, "other/keep.txt", "keep")
    report, entries = run(root, state, [Op(decision(src), "archives_10y_travail", "auto")])
    assert not (root / "0_Inbox" / "batch").exists()
    assert (root / "0_Inbox").is_dir()
    assert keep.exists()
    assert report.removed_dirs == [root / "0_Inbox" / "batch" / "sub", root / "0_Inbox" / "batch"]
    assert [e["op"] for e in entries][-2:] == ["rmdir", "rmdir"]


def test_nothing_is_deleted(tmp_path):
    root, state = setup(tmp_path)
    existing = root / "4_Archives" / "10y_travail" / "2025" / "Payslip_2025.txt"
    existing.parent.mkdir(parents=True)
    existing.write_text("payslip")
    sources = [inbox(root, f"Payslip_2025_{n}.txt") for n in range(3)]
    sources.append(inbox(root, "Payslip_2025.txt"))
    before = sum(1 for p in root.rglob("*") if p.is_file())
    run(root, state, [Op(decision(s), "archives_10y_travail", "auto") for s in sources])
    assert sum(1 for p in root.rglob("*") if p.is_file()) == before


def test_trash_folder_name(tmp_path):
    assert apply_mod.TRASH == ".trash"
```

- [ ] **Step 2: Run, expect failure.** `uv run pytest tests/test_core_apply.py -q` → FAIL.

- [ ] **Step 3: Implement.** Create `src/para_files/core/apply.py`:

```python
"""Apply a plan (spec §4.3): sequential, contained, never overwriting, journaled per operation."""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from para_files.core.decide import Decision
from para_files.core.evidence import sha256_of
from para_files.core.journal import DecidedBy, Journal
from para_files.core.tree import TreeConfig
from para_files.utils.filename_sanitizer import sanitize_filename


TRASH = ".trash"
MAX_SUFFIX = 1000


@dataclass(frozen=True)
class Op:
    """One file to move: the decision, the final leaf (owner may correct it), who decided."""

    decision: Decision
    leaf_id: str
    decided_by: DecidedBy


@dataclass
class ApplyReport:
    """What a run did and what it refused, with reasons."""

    moved: list[tuple[Path, Path]] = field(default_factory=list)
    trashed: list[tuple[Path, Path]] = field(default_factory=list)
    skipped: list[tuple[Path, str]] = field(default_factory=list)
    removed_dirs: list[Path] = field(default_factory=list)


def free_path(path: Path) -> Path:
    """path, or 'stem (2).ext', 'stem (3).ext'… whichever does not exist yet."""
    if not path.exists():
        return path
    for number in range(2, MAX_SUFFIX):
        candidate = path.with_name(f"{path.stem} ({number}){path.suffix}")
        if not candidate.exists():
            return candidate
    msg = f"no free name for {path}"
    raise FileExistsError(msg)


class _Applier:
    def __init__(self, config: TreeConfig, para_root: Path, journal: Journal) -> None:
        self.config = config
        self.root = para_root.resolve()
        self.journal = journal
        self.report = ApplyReport()

    def inside(self, path: Path) -> bool:
        return path.resolve().is_relative_to(self.root)

    def makedirs(self, directory: Path) -> None:
        missing: list[Path] = []
        current = directory
        while not current.exists():
            missing.append(current)
            current = current.parent
        for path in reversed(missing):
            path.mkdir()
            self.journal.append({"op": "mkdir", "dst": str(path)})

    def record(self, name: str, op: Op, src: Path, dst: Path) -> None:
        decision = op.decision
        self.journal.append(
            {
                "op": name,
                "src": str(src),
                "dst": str(dst),
                "sha256": decision.sha256,
                "size": dst.stat().st_size,
                "leaf": op.leaf_id,
                "proposed_leaf": decision.leaf_id,
                "decided_by": op.decided_by,
                "signal": decision.signal,
                "confidence": decision.confidence,
            }
        )

    def refusal(self, op: Op) -> str | None:
        src = op.decision.path
        if op.decision.signal == "secret":
            return "secret"
        if op.leaf_id not in self.config.tree.leaves:
            return f"unknown leaf {op.leaf_id!r}"
        if src.is_symlink() or not src.is_file():
            return "source missing"
        if sha256_of(src) != op.decision.sha256:
            return "changed since the preview"
        return None

    def target(self, op: Op) -> Path:
        decision = op.decision
        if op.leaf_id == decision.leaf_id and decision.target_dir:
            return self.root / decision.target_dir
        return self.root / self.config.tree.leaves[op.leaf_id].path

    def apply(self, op: Op) -> None:
        src = op.decision.path
        reason = self.refusal(op)
        target = self.target(op) if reason is None else None
        if target is not None and not self.inside(target):
            reason = "target outside the PARA root"
        suggested = op.decision.suggested_name
        name = sanitize_filename(suggested, preserve_extension=True) if suggested else src.name
        if (
            target is not None
            and reason is None
            and src.parent.resolve() == target.resolve()
            and name == src.name
        ):
            reason = "already in place"
        if reason is not None or target is None:
            self.report.skipped.append((src, reason or "no target"))
            return
        dst = target / name
        if dst.is_file() and sha256_of(dst) == op.decision.sha256:
            self.trash(op, src)
            return
        self.makedirs(target)
        dst = free_path(dst)
        shutil.move(src, dst)
        self.record("move", op, src, dst)
        self.report.moved.append((src, dst))

    def trash(self, op: Op, src: Path) -> None:
        relative = src.resolve().relative_to(self.root) if self.inside(src) else Path(src.name)
        dst = free_path(self.root / TRASH / self.journal.run_id / relative)
        self.makedirs(dst.parent)
        shutil.move(src, dst)
        self.record("trash", op, src, dst)
        self.report.trashed.append((src, dst))

    def remove_emptied(self, roots: Sequence[Path]) -> None:
        bases = [root.resolve() for root in roots]
        sources = {src.parent.resolve() for src, _ in self.report.moved + self.report.trashed}
        for directory in sorted(sources, key=lambda path: len(path.parts), reverse=True):
            current = directory
            while (
                any(current != base and current.is_relative_to(base) for base in bases)
                and current.is_dir()
                and not any(current.iterdir())
            ):
                current.rmdir()
                self.journal.append({"op": "rmdir", "dst": str(current)})
                self.report.removed_dirs.append(current)
                current = current.parent


def apply_ops(
    ops: Sequence[Op],
    *,
    config: TreeConfig,
    para_root: Path,
    journal: Journal,
    roots: Sequence[Path],
) -> ApplyReport:
    """Run every operation in order, then remove folders this run emptied inside roots."""
    applier = _Applier(config, para_root, journal)
    for op in ops:
        applier.apply(op)
    applier.remove_emptied(roots)
    return applier.report
```

- [ ] **Step 4: Run, expect pass.** `uv run pytest tests/test_core_apply.py -q` → 11 passed.

- [ ] **Step 5: Gate and commit.**

```bash
git add src/para_files/core/apply.py tests/test_core_apply.py
git commit -m "feat(core): sequential apply with containment, no-clobber, trash and journal" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx"
```

---

### Task 11: Undo

**Files:**
- Create: `src/para_files/core/undo.py`, `tests/test_core_undo.py`

**Interfaces:**
- Consumes: `journal_dir`, `read_run`, `last_run_id`, `is_undone`, `mark_undone` (Task 9); `sha256_of` (Task 2); `apply_ops`, `Op` (Task 10, tests only).
- Produces: `UndoError(RuntimeError)`, `UndoReport(run_id, restored, recreated, removed_dirs, skipped)`, `undo_run(state_dir, run_id=None) -> UndoReport`.

Rules (spec §4.3 Undo), entries replayed newest first:
- `move` / `trash`: put `dst` back at `src` when `dst` is a file with the journaled sha256 and `src` is free. Otherwise skip with a reason ("missing", "changed since the run", "source path taken").
- `rmdir`: recreate the folder.
- `mkdir`: remove the folder if it is empty, else skip ("folder not empty"); missing folder → nothing to do.
- No run given → the last run not undone. Unknown run, or a run already undone → `UndoError`. The run is marked undone at the end.

- [ ] **Step 1: Write the failing tests.** Create `tests/test_core_undo.py`:

```python
"""undo_run: replays a journal backwards; S5 (byte-identical tree after undo)."""

from __future__ import annotations

import hashlib

import pytest

from para_files.core import apply as apply_mod
from para_files.core.apply import Op, apply_ops
from para_files.core.decide import Decision
from para_files.core.evidence import sha256_of
from para_files.core.journal import Journal, is_undone
from para_files.core.undo import UndoError, undo_run
from tests.core_helpers import make_config, make_settings


def tree_state(root):
    """Every folder, and every file with size, content hash and mtime."""
    state = {}
    for path in root.rglob("*"):
        rel = path.relative_to(root).as_posix()
        if path.is_dir():
            state[rel] = "dir"
        else:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            state[rel] = (path.stat().st_size, digest, path.stat().st_mtime_ns)
    return state


def setup(tmp_path):
    settings = make_settings(tmp_path)
    root = settings.para_root.resolve()
    existing = root / "4_Archives" / "10y_travail" / "2025" / "dup.txt"
    existing.parent.mkdir(parents=True)
    existing.write_text("dup")
    files = {
        "batch/sub/Payslip_2025.txt": "payslip",
        "batch/dup.txt": "dup",
        "loose.txt": "loose",
    }
    for rel, text in files.items():
        path = root / "0_Inbox" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root, settings.state_dir


def op_for(path, leaf="archives_10y_travail", decided_by="auto"):
    decision = Decision(
        path=path,
        sha256=sha256_of(path),
        leaf_id="archives_10y_travail",
        target_dir="4_Archives/10y_travail/2025",
        band="green",
        signal="rules",
        confidence=1.0,
        evidence_summary="rule",
        kind="record",
    )
    return Op(decision, leaf, decided_by)


def apply_all(root, state, ops, run_id="r1"):
    with Journal(state, run_id) as journal:
        return apply_ops(
            ops, config=make_config(), para_root=root, journal=journal, roots=[root / "0_Inbox"]
        )


def test_s5_undo_restores_a_byte_identical_tree(tmp_path):
    root, state = setup(tmp_path)
    before = tree_state(root)
    inbox = root / "0_Inbox"
    ops = [
        op_for(inbox / "batch" / "sub" / "Payslip_2025.txt"),
        op_for(inbox / "batch" / "dup.txt"),
        op_for(inbox / "loose.txt", leaf="archives_5y_factures", decided_by="owner"),
    ]
    report = apply_all(root, state, ops)
    assert len(report.moved) == 2
    assert len(report.trashed) == 1
    assert tree_state(root) != before
    undo = undo_run(state)
    assert undo.run_id == "r1"
    assert undo.skipped == []
    assert tree_state(root) == before
    assert is_undone(state, "r1")


def test_changed_destination_is_left_alone(tmp_path):
    root, state = setup(tmp_path)
    src = root / "0_Inbox" / "loose.txt"
    apply_all(root, state, [op_for(src)])
    moved = root / "4_Archives" / "10y_travail" / "2025" / "loose.txt"
    moved.write_text("edited after the run")
    report = undo_run(state, "r1")
    assert report.skipped == [(str(moved), "changed since the run")]
    assert moved.exists()
    assert not src.exists()


def test_taken_source_path_is_left_alone(tmp_path):
    root, state = setup(tmp_path)
    src = root / "0_Inbox" / "loose.txt"
    apply_all(root, state, [op_for(src)])
    src.write_text("a new file with the same name")
    report = undo_run(state, "r1")
    moved = root / "4_Archives" / "10y_travail" / "2025" / "loose.txt"
    assert report.skipped == [(str(moved), "source path taken")]
    assert src.read_text() == "a new file with the same name"


def test_errors(tmp_path):
    root, state = setup(tmp_path)
    with pytest.raises(UndoError, match="no run"):
        undo_run(state)
    apply_all(root, state, [op_for(root / "0_Inbox" / "loose.txt")])
    with pytest.raises(UndoError, match="no journal"):
        undo_run(state, "nope")
    undo_run(state, "r1")
    with pytest.raises(UndoError, match="already undone"):
        undo_run(state, "r1")


def test_interrupted_apply_is_fully_undoable(tmp_path, monkeypatch):
    root, state = setup(tmp_path)
    before = tree_state(root)
    real_move = apply_mod.shutil.move
    calls = []

    def move_then_stop(src, dst):
        calls.append(src)
        if len(calls) == 2:
            raise KeyboardInterrupt
        return real_move(src, dst)

    monkeypatch.setattr(apply_mod.shutil, "move", move_then_stop)
    inbox = root / "0_Inbox"
    ops = [op_for(inbox / "loose.txt"), op_for(inbox / "batch" / "sub" / "Payslip_2025.txt")]
    with pytest.raises(KeyboardInterrupt):
        apply_all(root, state, ops)
    monkeypatch.setattr(apply_mod.shutil, "move", real_move)
    undo_run(state, "r1")
    assert tree_state(root) == before
```

- [ ] **Step 2: Run, expect failure.** `uv run pytest tests/test_core_undo.py -q` → FAIL.

- [ ] **Step 3: Implement.** Create `src/para_files/core/undo.py`:

```python
"""Undo a run (spec §4.3): replay its journal newest first, checking every step."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from para_files.core.evidence import sha256_of
from para_files.core.journal import is_undone, journal_dir, last_run_id, mark_undone, read_run


class UndoError(RuntimeError):
    """The run cannot be undone (unknown, or already undone)."""


@dataclass
class UndoReport:
    """What undo restored, recreated and removed, and what it left alone and why."""

    run_id: str
    restored: list[Path] = field(default_factory=list)
    recreated: list[Path] = field(default_factory=list)
    removed_dirs: list[Path] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)


def _blocked(dst: Path, src: Path, sha256: str) -> str | None:
    if not dst.is_file():
        return "missing"
    if sha256_of(dst) != sha256:
        return "changed since the run"
    if src.exists():
        return "source path taken"
    return None


def _undo_entry(entry: dict[str, Any], report: UndoReport) -> None:
    op, dst = entry.get("op"), Path(entry["dst"])
    if op == "rmdir":
        dst.mkdir(parents=True, exist_ok=True)
        report.recreated.append(dst)
    elif op == "mkdir":
        if dst.is_dir() and not any(dst.iterdir()):
            dst.rmdir()
            report.removed_dirs.append(dst)
        elif dst.exists():
            report.skipped.append((str(dst), "folder not empty"))
    elif op in {"move", "trash"}:
        src = Path(entry["src"])
        reason = _blocked(dst, src, entry["sha256"])
        if reason is not None:
            report.skipped.append((str(dst), reason))
            return
        src.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(dst, src)
        report.restored.append(src)


def undo_run(state_dir: Path, run_id: str | None = None) -> UndoReport:
    """Undo one run (default: the last one not undone) and mark it undone."""
    target = run_id or last_run_id(state_dir)
    if target is None:
        msg = "no run to undo"
        raise UndoError(msg)
    if not (journal_dir(state_dir) / f"{target}.jsonl").exists():
        msg = f"no journal for run {target}"
        raise UndoError(msg)
    if is_undone(state_dir, target):
        msg = f"run {target} was already undone"
        raise UndoError(msg)
    report = UndoReport(target)
    for entry in reversed(read_run(state_dir, target)):
        _undo_entry(entry, report)
    mark_undone(state_dir, target)
    return report
```

- [ ] **Step 4: Run, expect pass.** `uv run pytest tests/test_core_undo.py -q` → 5 passed.

- [ ] **Step 5: Gate and commit.**

```bash
git add src/para_files/core/undo.py tests/test_core_undo.py
git commit -m "feat(core): undo a run from its journal (S5)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx"
```

---

### Task 12: Sort entry points, exit checks S4/S8, docs

**Files:**
- Create: `src/para_files/core/sort.py`, `tests/test_core_sort.py`
- Modify: `CHANGELOG.md`, `docs/superpowers/specs/2026-10-10-para-files-redesign-design.md`

**Interfaces:**
- Consumes: everything above.
- Produces (used by the Stage 3 CLI):
  - `iter_files(paths: Sequence[Path]) -> Iterator[Path]`: files under the paths, sorted; never descends into dot-folders, skips dotfiles, `~$` Office lock files and symlinks.
  - `build_context(settings, config_directory=None) -> Context`: loads the tree strictly, opens the cache, fingerprints the config with `settings.fallback_model`, reads `confirmed_counts`, and builds the fallback from settings.
  - `preview(paths, ctx) -> list[Decision]`: classify in a thread pool (`settings.max_workers`), input order kept. A file that cannot be read becomes a red decision with signal `error`. Ctrl+C cancels pending work and re-raises.
  - `auto_ops(decisions) -> list[Op]`: green decisions with a leaf, `decided_by="auto"`.
  - `apply(ops, ctx, roots) -> tuple[str, ApplyReport]`: new run id, journal, `apply_ops`.

- [ ] **Step 1: Write the failing tests.** Create `tests/test_core_sort.py`:

```python
"""Entry points and the Stage 2 exit checks: S4 (preview changes nothing), S8 (secrets)."""

from __future__ import annotations

from pathlib import Path

from para_files.core.apply import Op
from para_files.core.decide import Decision
from para_files.core.fallback import FallbackChoice
from para_files.core.sort import apply, auto_ops, build_context, iter_files, preview
from tests.core_helpers import make_settings, write_config


class RecordingFallback:
    def __init__(self):
        self.names = []

    def decide(self, evidence, tree):
        self.names.append(evidence.name)
        return FallbackChoice("archives_5y_factures", 0.6, "m1", (("archives_5y_factures", 0.6),))


def build(tmp_path):
    settings = make_settings(tmp_path)
    ctx = build_context(settings, write_config(tmp_path / "cfg"))
    ctx.fallback = RecordingFallback()
    lookups = []
    ctx.lookup = lookups.append
    return settings.para_root.resolve(), ctx, lookups


def put(root, rel, text="x"):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def full_state(root):
    """Names, inodes and mtimes of every entry (S4 is about all three)."""
    state = {}
    for path in root.rglob("*"):
        stat = path.lstat()
        state[path.relative_to(root).as_posix()] = (stat.st_ino, stat.st_mtime_ns)
    return state


def test_iter_files_skips_hidden_and_links(tmp_path):
    put(tmp_path, "a.txt")
    put(tmp_path, ".hidden.txt")
    put(tmp_path, "~$lock.docx")
    put(tmp_path, ".trash/r1/old.txt")
    put(tmp_path, "sub/b.txt")
    (tmp_path / "link.txt").symlink_to(tmp_path / "a.txt")
    (tmp_path / "linkdir").symlink_to(tmp_path / "sub")
    assert [p.relative_to(tmp_path).as_posix() for p in iter_files([tmp_path])] == [
        "a.txt",
        "sub/b.txt",
    ]


def test_s4_preview_changes_nothing(tmp_path):
    root, ctx, _ = build(tmp_path)
    put(root, "0_Inbox/Payslip_2025-12.txt", "payslip")
    put(root, "0_Inbox/2026-01-23_acmecard_facture.txt", "AcmeCard")
    put(root, "0_Inbox/batch/notes.md", "# notes")
    put(root, "0_Inbox/random.txt", "hello")
    before = full_state(root)
    decisions = preview([root / "0_Inbox"], ctx)
    assert len(decisions) == 4
    assert full_state(root) == before


def test_preview_keeps_order_and_bands(tmp_path):
    root, ctx, _ = build(tmp_path)
    put(root, "0_Inbox/a_Payslip_2025.txt", "payslip")
    put(root, "0_Inbox/b_random.txt", "hello")
    decisions = preview([root / "0_Inbox"], ctx)
    assert [(d.path.name, d.band, d.signal) for d in decisions] == [
        ("a_Payslip_2025.txt", "green", "rules"),
        ("b_random.txt", "yellow", "fallback"),
    ]
    assert [op.decision.path.name for op in auto_ops(decisions)] == ["a_Payslip_2025.txt"]


def test_unreadable_file_is_a_red_error(tmp_path, monkeypatch):
    from para_files.core import sort

    root, ctx, _ = build(tmp_path)
    path = put(root, "0_Inbox/a.txt")

    def boom(*_args):
        msg = "denied"
        raise PermissionError(msg)

    monkeypatch.setattr(sort, "classify", boom)
    (decision,) = preview([root / "0_Inbox"], ctx)
    assert (decision.path, decision.band, decision.signal) == (path, "red", "error")


def test_s8_secrets_never_sent_never_moved(tmp_path):
    root, ctx, lookups = build(tmp_path)
    secrets = [
        put(root, "0_Inbox/passwords.txt", "x"),
        put(root, "0_Inbox/notes.txt", "vpn\npassword: hunter22\n"),
        put(root, "0_Inbox/token_Payslip_2025.txt", "x"),
        put(root, "2_Areas/IT/credentials/Payslip_2025.txt", "x"),
        put(root, "0_Inbox/secret_book.pdf", "%PDF"),
    ]
    decisions = preview([root / "0_Inbox", root / "2_Areas"], ctx)
    assert {d.path for d in decisions} == set(secrets)
    assert {(d.band, d.signal, d.leaf_id) for d in decisions} == {("red", "secret", None)}
    assert ctx.fallback.names == []
    assert lookups == []
    forced = [Op(d, "archives_10y_travail", "owner") for d in decisions]
    _, report = apply(forced, ctx, [root / "0_Inbox"])
    assert [reason for _, reason in report.skipped] == ["secret"] * len(secrets)
    assert all(path.exists() for path in secrets)


def test_owner_moves_feed_calibration(tmp_path):
    root, ctx, _ = build(tmp_path)
    put(root, "0_Inbox/random.txt", "hello")
    (decision,) = preview([root / "0_Inbox"], ctx)
    run_id, report = apply([Op(decision, "archives_5y_factures", "owner")], ctx, [root / "0_Inbox"])
    assert len(report.moved) == 1
    again = build_context(ctx.settings, tmp_path / "cfg")
    assert again.confirmed == {"record": 1}
    assert run_id


def test_auto_ops_ignores_yellow_red_and_leafless():
    def d(band, leaf):
        return Decision(
            path=Path("/x"),
            sha256="s",
            leaf_id=leaf,
            target_dir=None,
            band=band,
            signal="rules",
            confidence=1.0,
            evidence_summary="",
        )

    ops = auto_ops([d("green", "a"), d("yellow", "b"), d("red", "c"), d("green", None)])
    assert [(op.leaf_id, op.decided_by) for op in ops] == [("a", "auto")]
```

- [ ] **Step 2: Run, expect failure.** `uv run pytest tests/test_core_sort.py -q` → FAIL.

- [ ] **Step 3: Implement.** Create `src/para_files/core/sort.py`:

```python
"""Entry points for the Stage 3 CLI: find files, classify them in parallel, apply a plan."""

from __future__ import annotations

import os
from collections.abc import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from para_files.core.apply import ApplyReport, Op, apply_ops
from para_files.core.cache import Cache, config_fingerprint
from para_files.core.decide import Context, Decision, classify
from para_files.core.fallback import make_fallback
from para_files.core.journal import Journal, confirmed_counts, new_run_id
from para_files.core.settings import CoreSettings
from para_files.core.tree import config_dir, load_tree_config


SKIPPED_PREFIXES = (".", "~$")


def iter_files(paths: Sequence[Path]) -> Iterator[Path]:
    """Files under paths, sorted; no dot-folders, dotfiles, Office lock files or symlinks."""
    for path in paths:
        if path.is_symlink():
            continue
        if path.is_file():
            yield path
            continue
        for dirpath, dirnames, filenames in os.walk(path):
            dirnames[:] = sorted(name for name in dirnames if not name.startswith("."))
            for name in sorted(filenames):
                file = Path(dirpath) / name
                if not name.startswith(SKIPPED_PREFIXES) and not file.is_symlink():
                    yield file


def build_context(settings: CoreSettings, config_directory: Path | None = None) -> Context:
    """Strict config, cache, fingerprint, calibration counts and fallback for one run."""
    directory = config_directory or config_dir()
    config = load_tree_config(directory)
    return Context(
        config=config,
        settings=settings,
        cache=Cache(settings.cache_path),
        fingerprint=config_fingerprint(directory, settings.fallback_model),
        confirmed=confirmed_counts(settings.state_dir, config.tree),
        fallback=make_fallback(settings),
    )


def _safe_classify(path: Path, ctx: Context) -> Decision:
    try:
        return classify(path, ctx)
    except OSError as exc:
        return Decision(
            path=path,
            sha256="",
            leaf_id=None,
            target_dir=None,
            band="red",
            signal="error",
            confidence=0.0,
            evidence_summary=f"cannot read: {exc}",
        )


def preview(paths: Sequence[Path], ctx: Context) -> list[Decision]:
    """Decisions for every file under paths, in order. Nothing on disk changes."""
    files = list(iter_files(paths))
    with ThreadPoolExecutor(max_workers=ctx.settings.max_workers) as pool:
        futures = [pool.submit(_safe_classify, file, ctx) for file in files]
        try:
            return [future.result() for future in futures]
        except KeyboardInterrupt:
            for future in futures:
                future.cancel()
            raise


def auto_ops(decisions: Sequence[Decision]) -> list[Op]:
    """Green decisions with a leaf, applied without review."""
    return [Op(d, d.leaf_id, "auto") for d in decisions if d.band == "green" and d.leaf_id]


def apply(ops: Sequence[Op], ctx: Context, roots: Sequence[Path]) -> tuple[str, ApplyReport]:
    """Apply ops under a new journaled run; return the run id and the report."""
    run_id = new_run_id(ctx.settings.state_dir)
    with Journal(ctx.settings.state_dir, run_id) as journal:
        report = apply_ops(
            ops,
            config=ctx.config,
            para_root=ctx.settings.para_root,
            journal=journal,
            roots=roots,
        )
    return run_id, report
```

Notes for the implementer:
- `test_unreadable_file_is_a_red_error` patches `sort.classify`, so `_safe_classify` must call the module-level name `classify` (as written).
- `test_s4_preview_changes_nothing` uses `os.lstat` inode and mtime. If a reader opens files with write access, the mtimes change and the test catches it.

- [ ] **Step 4: Run, expect pass.** `uv run pytest tests/test_core_sort.py -q` → 8 passed.

- [ ] **Step 5: Docs.**
  - `CHANGELOG.md`, under `## [Unreleased]`, add a section after any existing `### Changed` block:

    ```markdown
    ### Added (Stage 2)

    - **New core (`para_files.core`)**, alongside the old pipeline (the CLI still uses the old one until Stage 3):
      - one `extract()` per file, with the secrets guard first (names, folders below the PARA root, archive entries, content);
      - four signals on leaf ids: case-insensitive rules, books by ISBN (lookups cached; the unused cover lookup is gone), issuers (patterns of 3 characters or fewer match whole words only) and an OpenRouter fallback through litellm (Gemini 3.8 Flash, then Sonnet 5.5, zero data retention on every request);
      - bands with kind caps, and a calibration cap: issuers and the fallback stay yellow until a kind has 100 owner-confirmed decisions;
      - an SQLite cache of verdicts keyed by content hash and config fingerprint;
      - sequential apply: contained, never overwriting, `.trash` for identical files, emptied folders removed, every step journaled (`mkdir`, `move`, `trash`, `rmdir`) with `proposed_leaf` and `decided_by`;
      - `undo` of a run, checked step by step.
    - **Core settings**: env > `<config dir>/.env` > defaults. A `PARA_FILES_PARA_ROOT` that points at a bucket (such as `…/0_Inbox`) is refused with a message naming the variable.
    ```

  - Spec, two edits:
    1. §4.3 Journal: replace ``op` ∈ `move`, `trash`, `rmdir`.`` with ``op` ∈ `mkdir`, `move`, `trash`, `rmdir` (`mkdir` lets `undo` remove the folders a run created).`.
    2. §4.1 Config files: after the line ``- `thema_l1l2.json` — …``, add the line `Both package files are deferred to Stage 4: the owner's rules.yaml already carries the extension rules, and the Thema slimming is part of the purge.`

- [ ] **Step 6: Full gate.** Run all four gate commands. Then the controller scans the branch diff (`git diff main`) for personal identifiers (owner name, real issuers, PARA paths) before any push; the pattern list lives outside the repo.

- [ ] **Step 7: Commit.**

```bash
git add src/para_files/core/sort.py tests/test_core_sort.py CHANGELOG.md docs/superpowers/specs/2026-10-10-para-files-redesign-design.md
git commit -m "feat(core): sort entry points; S4 and S8 exit checks; docs" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TnHHvHPS4t1tVuqpTZiEJx"
```

Stage 2 exit (spec §5) is met when S4 (`test_s4_preview_changes_nothing`), S5 (`test_s5_undo_restores_a_byte_identical_tree`) and S8 (`test_s8_secrets_never_sent_never_moved`, `test_secret_evidence_is_never_sent`) pass with the full gate green.

## Deliberately not in this plan

- CLI commands (`sort`, `explain`, `undo`, `clean`, `tree`, `init`) and the interactive `--review` flow: Stage 3. `Op(decision, leaf, "owner")` is the hook the review flow will use.
- `clean --duplicates`, renaming generic PDFs by OCR, package default rules and the Thema slimming: later stages.
- Any change to the old pipeline beyond the cover-lookup removal.
