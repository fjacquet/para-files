"""Tests for scripts/run_baseline.py (old pipeline over the golden corpus)."""

from __future__ import annotations

from pathlib import Path

import pytest

from para_files.classifiers.extension_router import ExtensionRouterClassifier
from para_files.config import Config, ExtensionRoutingConfig, LLMConfig, LoggingConfig, MLXConfig
from para_files.core.tree import Tree


TREE = Tree.model_validate(
    {
        "leaves": {
            "invoices": {
                "kind": "record",
                "retention": "5y",
                "path": "4_Archives/5y_factures",
                "describe": "Invoices",
            },
            "telecom": {
                "kind": "record",
                "retention": "5y",
                "path": "4_Archives/5y_factures/Telephonie",
                "describe": "Telecom invoices",
            },
            "docs": {"kind": "library", "path": "3_Resources/docs", "describe": "Vendor docs"},
        }
    }
)
CANON_MAP = {
    "4_Archives/factures": "4_Archives/5y_factures",
    "3_Resources/documentation": "3_Resources/docs",
}


def canon(rel: str) -> str:
    return CANON_MAP.get(rel, rel)


@pytest.mark.parametrize(
    ("category", "leaf"),
    [
        ("4_Archives/factures/Telephonie/2024", "telecom"),
        ("4_Archives/5y_factures/2024", "invoices"),
        ("3_Resources/documentation/VMware", "docs"),
        ("0_Inbox", None),
        ("4_Archives/unknown/x", None),
    ],
)
def test_leaf_for_category_prefers_canonical_and_longest(load_script, category, leaf):
    baseline = load_script("run_baseline")
    assert baseline.leaf_for_category(category, TREE, canon) == leaf


def test_run_baseline_maps_errors_to_red_and_never_exposes_para_paths(
    load_script, tmp_path: Path, snapshot
):
    baseline = load_script("run_baseline")
    para = tmp_path / "PARA"
    for name in ("a.pdf", "b.pdf", "c.pdf"):
        path = para / "4_Archives/5y_factures" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")
    golden = [
        {"path": f"4_Archives/5y_factures/{name}", "leaf": "invoices", "kind": "record"}
        for name in ("a.pdf", "b.pdf", "c.pdf")
    ]
    seen: list[Path] = []

    def classify(path: Path) -> tuple[str, float, str]:
        seen.append(path)
        if path.name == "b.pdf":
            msg = "unreadable"
            raise PermissionError(msg)
        if path.name == "c.pdf":
            return "0_Inbox", 0.8, "extension_router"
        return "4_Archives/factures/2024", 0.95, "rules_engine"

    before = snapshot(para)
    preds = baseline.run_baseline(para, golden, TREE, canon, classify, tmp_path / "work")
    by_name = {Path(p["path"]).name: p for p in preds}
    assert by_name["a.pdf"]["leaf"] == "invoices"
    assert by_name["a.pdf"]["band"] == "green"
    assert by_name["a.pdf"]["signal"] == "rules_engine"
    assert by_name["b.pdf"]["band"] == "red"
    assert by_name["b.pdf"]["signal"] == "error"
    assert by_name["c.pdf"]["leaf"] is None
    assert by_name["c.pdf"]["band"] == "red"
    # The link sits in the work folder; its target is in PARA, so check the link's folder.
    assert seen
    assert all(not path.parent.resolve().is_relative_to(para.resolve()) for path in seen)
    assert snapshot(para) == before


def test_old_pipeline_runs_signals_one_to_three_only(load_script, monkeypatch):
    baseline = load_script("run_baseline")
    for name in (
        "PARA_FILES_MLX_SEMANTIC_ENABLED",
        "PARA_FILES_LLM_ENABLED",
        "PARA_FILES_OCR_RENAME__ENABLED",
    ):
        monkeypatch.setenv(name, "true")  # the function must switch these off
    built: list[object] = []

    class FakePipeline:
        def __init__(self, config: Config) -> None:
            self.config = config
            self._classifiers = ["book", object.__new__(ExtensionRouterClassifier), "rules"]
            built.append(self)

        def _ensure_initialized(self) -> None:
            return None

    def env_only_config() -> Config:
        # Built from os.environ alone: the real load_config would read the owner's personal
        # tree and .env files.
        return Config(
            _env_file=None,
            mlx=MLXConfig(_env_file=None),
            llm=LLMConfig(_env_file=None),
            logging=LoggingConfig(_env_file=None),
            extension_routing=ExtensionRoutingConfig(_env_file=None),
        )

    monkeypatch.setattr("para_files.config.load_config", env_only_config)
    monkeypatch.setattr("para_files.pipeline.ClassificationPipeline", FakePipeline)

    baseline.old_pipeline_classifier()

    (pipeline,) = built
    assert pipeline.config.mlx.semantic_enabled is False
    assert pipeline.config.llm.enabled is False
    assert pipeline.config.ocr_rename.enabled is False
    assert not any(isinstance(c, ExtensionRouterClassifier) for c in pipeline._classifiers)
    assert pipeline._classifiers == ["book", "rules"]


def test_out_inside_para_root_is_refused(load_script, tmp_path):
    baseline = load_script("run_baseline")
    para = tmp_path / "PARA"
    para.mkdir()
    # The config dir has no golden.jsonl: the refusal must come before the corpus is read.
    with pytest.raises(SystemExit) as refused:
        baseline.main(
            [
                "--para-root",
                str(para),
                "--config-dir",
                str(tmp_path / "cfg"),
                "--out",
                str(para / "x.jsonl"),
            ]
        )
    assert refused.value.code == 2


def test_link_failure_becomes_red_row(load_script, tmp_path):
    baseline = load_script("run_baseline")
    para = tmp_path / "PARA"
    source = para / "4_Archives/5y_factures/a.pdf"
    source.parent.mkdir(parents=True)
    source.write_text("x")
    workdir = tmp_path / "work"
    workdir.mkdir()
    (workdir / "0").write_text("not a folder")  # the link folder of row 0 cannot be created
    golden = [{"path": "4_Archives/5y_factures/a.pdf", "leaf": "invoices", "kind": "record"}]

    calls: list[Path] = []

    def classify(path: Path) -> tuple[str, float, str]:
        calls.append(path)
        return "4_Archives/factures/2024", 0.95, "rules_engine"

    preds = baseline.run_baseline(para, golden, TREE, canon, classify, workdir)
    assert calls == []  # classify must not run when the link cannot be made
    assert preds[0]["band"] == "red"
    assert preds[0]["signal"] == "error"
    assert preds[0]["leaf"] is None


def test_old_pipeline_switches_geocoding_off(load_script, monkeypatch):
    from para_files.classifiers import rules_engine
    from para_files.utils import geolocation

    baseline = load_script("run_baseline")
    fetched: list[tuple[float, float]] = []
    monkeypatch.setattr(
        geolocation, "_fetch_from_nominatim", lambda lat, lon: fetched.append((lat, lon))
    )  # any network lookup would be recorded here; none may happen
    monkeypatch.setattr(rules_engine, "reverse_geocode", rules_engine.reverse_geocode)  # undone

    class FakePipeline:
        def __init__(self, config: object) -> None:
            self._classifiers: list[object] = []

        def _ensure_initialized(self) -> None:
            return None

    monkeypatch.setattr("para_files.config.load_config", lambda: None)
    monkeypatch.setattr("para_files.pipeline.ClassificationPipeline", FakePipeline)
    baseline.old_pipeline_classifier()
    assert rules_engine.reverse_geocode(46.5197, 6.6323) is None
    assert fetched == []


def test_old_pipeline_disables_generic_pdf_rename(load_script, monkeypatch):
    baseline = load_script("run_baseline")
    built: list[object] = []

    class FakePipeline:
        def __init__(self, config: object) -> None:
            self._classifiers: list[object] = []
            built.append(self)

        def _ensure_initialized(self) -> None:
            return None

    monkeypatch.setattr("para_files.config.load_config", lambda: None)
    monkeypatch.setattr("para_files.pipeline.ClassificationPipeline", FakePipeline)
    baseline.old_pipeline_classifier()
    (pipeline,) = built
    sentinel = object()
    assert pipeline._maybe_rename_generic_pdf(sentinel) is sentinel


KNOWLEDGE_TREE = Tree.model_validate(
    {
        "leaves": {
            "notes": {"kind": "knowledge", "path": "3_Resources/notes", "describe": "Notes"},
            "etudes": {"kind": "library", "path": "3_Resources/e\u0301tudes", "describe": "Study"},
        }
    }
)


def test_knowledge_leaf_is_yellow_never_green(load_script, tmp_path: Path):
    baseline = load_script("run_baseline")
    para = tmp_path / "PARA"
    source = para / "3_Resources/notes/a.md"
    source.parent.mkdir(parents=True)
    source.write_text("x")
    golden = [{"path": "3_Resources/notes/a.md", "leaf": "notes", "kind": "knowledge"}]

    def classify(path: Path) -> tuple[str, float, str]:
        return "3_Resources/notes/x", 0.9, "taxonomy"

    preds = baseline.run_baseline(
        para, golden, KNOWLEDGE_TREE, lambda rel: rel, classify, tmp_path / "work"
    )
    assert preds[0]["leaf"] == "notes"
    assert preds[0]["band"] == "yellow"


def test_leaf_for_category_guards_inbox_explicitly(load_script):
    baseline = load_script("run_baseline")

    def to_inbox(rel: str) -> str:
        return "0_Inbox/Stuff" if rel == "4_Archives/moved" else rel

    assert baseline.leaf_for_category("4_Archives/moved/2024", KNOWLEDGE_TREE, to_inbox) is None


def test_leaf_for_category_normalises_both_sides_to_nfc(load_script):
    baseline = load_script("run_baseline")
    nfc_category = "3_Resources/\u00e9tudes/2024"  # composed accent; the leaf path is decomposed
    assert baseline.leaf_for_category(nfc_category, KNOWLEDGE_TREE, lambda r: r) == "etudes"


def test_read_golden_skips_blank_lines_and_reads_utf8(load_script, tmp_path: Path):
    shared = load_script("para_inventory")
    rows_file = tmp_path / "golden.jsonl"
    rows_file.write_text(
        '{"path": "3_Resources/\u00e9tudes/a.pdf"}\n\n   \n{"path": "b.pdf"}\n', encoding="utf-8"
    )
    rows = shared.read_jsonl(rows_file)
    assert [row["path"] for row in rows] == ["3_Resources/\u00e9tudes/a.pdf", "b.pdf"]


def test_default_documents_path_is_repo_relative(load_script):
    baseline = load_script("run_baseline")
    assert baseline.DEFAULT_DOCUMENTS.is_file()
    assert baseline.DEFAULT_DOCUMENTS.parent.name == "config"
