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
    monkeypatch.setattr(books, "thema_folders", lambda _code: "U_Informatique/UB_Prog")
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
