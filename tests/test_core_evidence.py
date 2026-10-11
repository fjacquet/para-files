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


def test_secret_entry_past_listing_cap(tmp_path):
    path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for i in range(250):
            archive.writestr(f"doc{i}.txt", "x")
        archive.writestr("keys/id_rsa", "x")
    assert extract(path).secret == "archive"  # noqa: S105


def test_archive_listing_capped_at_200(tmp_path):
    path = tmp_path / "many.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for i in range(250):
            archive.writestr(f"doc{i}.txt", "x")
    ev = extract(path)
    assert ev.secret is None
    assert len(ev.archive_listing) == 200
