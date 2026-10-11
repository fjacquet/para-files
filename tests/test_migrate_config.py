"""Tests for scripts/para_inventory.py and scripts/migrate_config.py (Stage 1 seeder)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from para_files.core.tree import load_tree_config


def _touch(root: Path, rel: str, content: str = "x") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@pytest.fixture
def para(tmp_path: Path) -> Path:
    root = tmp_path / "PARA"
    for rel in [
        "4_Archives/factures/2024/a.pdf",
        "4_Archives/5y_factures/2024/b.pdf",
        "4_Archives/5y_factures/2025/c.pdf",
        "4_Archives/2y_factures/d.pdf",
        "4_Archives/ctr_factures/e.pdf",
        "4_Archives/travail/2019/p.pdf",
        "4_Archives/10y_travail/2020/q.pdf",
        "4_Archives/10y_travail/2021/q.pdf",
        "4_Archives/5y_travail/{year}/r.pdf",
        "4_Archives/ret_prevoyance/lpp.pdf",
        "4_Archives/photos/2020/x.jpg",
        "4_Archives/evernote/note.enex",
        "3_Resources/docs/one.pdf",
        "3_Resources/docs/two.pdf",
        "3_Resources/documentation/three.pdf",
        "3_Resources/livres/book.epub",
        "3_Resources/administratif/identite/passport.pdf",
        "3_Resources/ret_prevoyance/avs.pdf",
        "3_Resources/prevoyance/avs-old.pdf",
        "3_Resources/5y_screenshots/s1.png",
        "3_Resources/5y_screenshots/s2.png",
        "3_Resources/screenshots/s3.png",
        "2_Areas/carriere/cv.pdf",
        "2_Areas/sante/a.txt",
        "2_Areas/sante/b.txt",
        "2_Areas/santé/c.txt",
        "1_Projets/alpha/readme.md",
        "5_others/kept.txt",
        "0_Inbox/2026-01-23_acme_facture.pdf",
        "0_Inbox/2026-02-23_acme_facture.pdf",
        "0_Inbox/random.txt",
    ]:
        _touch(root, rel)
    return root


@pytest.fixture
def legacy(tmp_path: Path) -> Path:
    rules = {
        "phone": {
            "patterns": ["*swisscom*"],
            "extensions": [".pdf"],
            "destination": "4_Archives/5y_factures/Telephonie/{YYYY}",
        },
        "phone_v2": {"patterns": ["*swisscom*"], "destination": "4_Archives/5y_factures"},
        "vmware_docs": {
            "patterns": ["*vmware*"],
            "destination": "3_Resources/documentation/{technology}",
            "known_vendors": ["VMware", "Broadcom"],
        },
        "old_bills": {"patterns": ["*bill*"], "destination": "4_Archives/factures"},
        "photos": {"extensions": [".jpg"], "destination": "4_Archives/photos/{YYYY}"},
        "tiny": {"patterns": ["*ab*", "*cv*.pdf"], "destination": "2_Areas/carriere"},
        "nowhere": {"patterns": ["*zzz*"], "destination": "9_Nowhere/x"},
        "flatten": {"patterns": ["*tmp*"], "action": "flatten_to_inbox"},
    }
    path = tmp_path / "legacy.yaml"
    path.write_text(yaml.safe_dump({"routing_rules": rules}, sort_keys=False))
    return path


def _doc(sub_id: str, retention: str, pattern: str, **extra: object) -> dict[str, object]:
    return {
        "sub_id": sub_id,
        "name": sub_id,
        "examples": [],
        "keywords": [],
        "retention": retention,
        "paper_required": False,
        "para_pattern": pattern,
        **extra,
    }


@pytest.fixture
def documents(tmp_path: Path) -> Path:
    issuers = [
        {"name": "Swisscom", "patterns": ["Swisscom"]},
        {"name": "Salt", "patterns": ["Salt Mobile", "swisscom"]},
    ]
    invoices = [
        _doc("telecom", "5_years", "4_Archives/5y_factures/{issuer}/{year}", issuers=issuers),
        _doc("warranty", "warranty_2_years", "4_Archives/2y_factures/{issuer}/{year}"),
        _doc("tenant", "contract_duration", "4_Archives/ctr_factures/{issuer}"),
    ]
    other = [
        _doc("payslips", "10_years", "4_Archives/10y_travail/{issuer}/{year}"),
        _doc("id", "permanent", "3_Resources/administratif/identite"),
    ]
    data = {
        "categories": [
            {"id": "A", "name": "Invoices", "description": "", "documents": invoices},
            {"id": "B", "name": "Other", "description": "", "documents": other},
        ]
    }
    path = tmp_path / "documents.json"
    path.write_text(json.dumps(data))
    return path


@pytest.fixture
def mapping(load_script, para, documents):
    inventory = load_script("para_inventory")
    taxonomy = inventory.retentions_by_stem(json.loads(documents.read_text()))
    return inventory.canonical_map(inventory.scan_folders(para), taxonomy)


@pytest.fixture
def draft(load_script, para, legacy, documents, tmp_path):
    migrate = load_script("migrate_config")
    out = tmp_path / "draft"
    argv = ["--para-root", str(para), "--legacy-tree", str(legacy)]
    argv += ["--documents", str(documents), "--out", str(out)]
    assert migrate.main(argv) == 0
    return out


class TestInventory:
    def test_count_files_stops_at_cap(self, load_script, tmp_path):
        inventory = load_script("para_inventory")
        for index in range(7):
            _touch(tmp_path, f"many/{index}.jpg")
        assert inventory.count_files(tmp_path / "many", cap=5) == 5

    def test_only_buckets_are_scanned_and_symlinks_are_skipped(self, load_script, para, tmp_path):
        _touch(tmp_path, "outside/secret.txt")
        (para / "3_Resources/linked").symlink_to(tmp_path / "outside", target_is_directory=True)
        inventory = load_script("para_inventory")
        rels = {folder.rel for folder in inventory.scan_folders(para)}
        assert "1_Projets/alpha" in rels
        assert "3_Resources/linked" not in rels
        assert not any(rel.startswith(("0_Inbox", "5_others")) for rel in rels)

    def test_retention_prefixes_never_merge(self, mapping):
        for prefix in ("2y", "5y", "ctr"):
            assert mapping[f"4_Archives/{prefix}_factures"] == f"4_Archives/{prefix}_factures"

    def test_split_stem_legacy_folder_is_doubtful(self, mapping):
        assert mapping["4_Archives/factures"] == "0_Inbox"

    def test_twin_and_stray_prefix_fold_into_the_taxonomy_prefix(self, mapping):
        assert mapping["4_Archives/travail"] == "4_Archives/10y_travail"
        assert mapping["4_Archives/5y_travail"] == "4_Archives/10y_travail"
        assert mapping["4_Archives/10y_travail"] == "4_Archives/10y_travail"

    def test_name_variants_fold_into_the_largest(self, mapping):
        assert mapping["2_Areas/santé"] == "2_Areas/sante"
        assert mapping["2_Areas/sante"] == "2_Areas/sante"

    def test_synonyms_fold_into_the_larger(self, mapping):
        assert mapping["3_Resources/documentation"] == "3_Resources/docs"
        assert mapping["2_Areas/carriere"] == "2_Areas/carriere"

    def test_prefixes_outside_archives(self, mapping):
        assert mapping["3_Resources/ret_prevoyance"] == "4_Archives/ret_prevoyance"
        assert mapping["3_Resources/prevoyance"] == "4_Archives/ret_prevoyance"
        assert mapping["3_Resources/5y_screenshots"] == "3_Resources/screenshots"
        assert mapping["3_Resources/screenshots"] == "3_Resources/screenshots"

    def test_canon_resolves_unknown_paths_by_variant_and_synonym(self, load_script, para):
        inventory = load_script("para_inventory")
        canon = inventory.make_canon(inventory.scan_folders(para))
        assert canon("3_Resources/books") == "3_Resources/livres"
        assert canon("3_Resources/Documentation") == "3_Resources/docs"
        assert canon("9_Nowhere/x") == "9_Nowhere/x"


class TestDraftTree:
    def test_draft_is_valid_and_kinds_are_proposed(self, draft):
        leaves = load_tree_config(draft).tree.leaves
        for absent in (
            "archives_factures",
            "archives_travail",
            "archives_5y_travail",
            "resources_documentation",
            "resources_ret_prevoyance",
            "resources_5y_screenshots",
        ):
            assert absent not in leaves
        invoices = leaves["archives_5y_factures"]
        assert (invoices.kind, invoices.retention) == ("record", "5y")
        assert invoices.subkey == "{issuer}/{year}"
        assert leaves["archives_2y_factures"].retention == "2y"
        assert leaves["archives_ctr_factures"].retention == "ctr"
        assert leaves["archives_10y_travail"].retention == "10y"
        assert leaves["archives_ret_prevoyance"].retention == "ret"
        assert leaves["resources_docs"].kind == "library"
        assert leaves["resources_livres"].subkey == "{thema}"
        assert leaves["resources_screenshots"].kind == "media"
        assert leaves["archives_photos"].kind == "media"
        identity = leaves["resources_administratif"]
        assert (identity.kind, identity.retention) == ("record", "permanent")
        assert leaves["archives_evernote"].retention == "permanent"
        assert leaves["areas_carriere"].kind == "knowledge"
        assert leaves["projects_alpha"].kind == "knowledge"
        assert not any(leaf.path.startswith("5_others") for leaf in leaves.values())

    def test_nfd_folder_names_become_nfc_leaves(self, load_script, tmp_path, legacy, documents):
        root = tmp_path / "PARA"
        _touch(root, "2_Areas/matière/notes.txt")
        out = tmp_path / "nfd-draft"
        migrate = load_script("migrate_config")
        argv = ["--para-root", str(root), "--legacy-tree", str(legacy)]
        argv += ["--documents", str(documents), "--out", str(out)]
        assert migrate.main(argv) == 0
        leaves = load_tree_config(out).tree.leaves
        assert leaves["areas_matiere"].path == "2_Areas/matière"


class TestDraftRules:
    def test_rules_keep_the_legacy_and_of_patterns_and_extensions(self, draft):
        rules = {rule.name: rule for rule in load_tree_config(draft).rules.rules}
        assert rules["phone"].leaf == "archives_5y_factures"
        assert rules["phone"].globs == ("*swisscom*.pdf",)
        assert rules["vmware_docs"].leaf == "resources_docs"
        assert rules["photos"].globs == ("*.jpg",)
        assert rules["tiny"].globs == ("*cv*.pdf",)
        assert {"phone_v2", "old_bills", "nowhere", "flatten"}.isdisjoint(rules)

    def test_extension_only_rules_come_last(self, draft):
        names = [rule.name for rule in load_tree_config(draft).rules.rules]
        assert names == ["phone", "vmware_docs", "tiny", "photos"]


class TestDraftIssuers:
    def test_issuers_come_from_documents_and_legacy_vendors(self, draft):
        issuers = load_tree_config(draft).issuers.issuers
        assert issuers["swisscom"].leaves == ("archives_5y_factures",)
        assert issuers["salt"].patterns == ("Salt Mobile",)
        assert issuers["vmware"].leaves == ("resources_docs",)
        assert issuers["broadcom"].patterns == ("Broadcom",)


class TestReview:
    def test_review_lists_merges_doubtful_conflicts_and_inbox_families(self, draft):
        review = (draft / "review.md").read_text()
        assert "merge: 4_Archives/5y_travail -> 4_Archives/10y_travail" in review
        assert "doubtful: 4_Archives/factures -> 0_Inbox" in review
        assert "rule old_bills: destination 4_Archives/factures is doubtful" in review
        assert "already used by swisscom" in review
        assert "acme facture.pdf: 2 files" in review
        assert "random" not in review


class TestReadOnly:
    def test_para_root_is_untouched(self, load_script, para, legacy, documents, tmp_path, snapshot):
        before = snapshot(para)
        migrate = load_script("migrate_config")
        argv = ["--para-root", str(para), "--legacy-tree", str(legacy)]
        argv += ["--documents", str(documents), "--out", str(tmp_path / "out")]
        assert migrate.main(argv) == 0
        assert snapshot(para) == before

    def test_out_inside_para_root_is_refused(self, load_script, para, legacy, documents):
        migrate = load_script("migrate_config")
        argv = ["--para-root", str(para), "--legacy-tree", str(legacy)]
        argv += ["--documents", str(documents), "--out", str(para / "draft")]
        with pytest.raises(SystemExit):
            migrate.main(argv)
