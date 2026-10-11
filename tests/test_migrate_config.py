"""Tests for scripts/para_inventory.py and scripts/migrate_config.py (Stage 1 seeder)."""

from __future__ import annotations

import json
import unicodedata
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
        _touch(root, unicodedata.normalize("NFD", "2_Areas/matière/notes.txt"))
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


class TestTargetsWithoutFolders:
    def _draft(self, load_script, tmp_path, documents, legacy, rels):
        root = tmp_path / "PARA"
        for rel in rels:
            _touch(root, rel)
        out = tmp_path / "draft-small"
        migrate = load_script("migrate_config")
        argv = ["--para-root", str(root), "--legacy-tree", str(legacy)]
        argv += ["--documents", str(documents), "--out", str(out)]
        assert migrate.main(argv) == 0
        return load_tree_config(out).tree.leaves

    def test_stray_prefix_alone_gets_the_taxonomy_leaf(
        self, load_script, tmp_path, documents, legacy
    ):
        leaves = self._draft(
            load_script, tmp_path, documents, legacy, ["4_Archives/5y_travail/r.pdf"]
        )
        assert "archives_5y_travail" not in leaves
        assert leaves["archives_10y_travail"].retention == "10y"

    def test_prefixed_folders_outside_archives_alone_get_leaves(
        self, load_script, tmp_path, documents, legacy
    ):
        rels = ["3_Resources/5y_screenshots/s.png", "3_Resources/ret_prevoyance/avs.pdf"]
        leaves = self._draft(load_script, tmp_path, documents, legacy, rels)
        assert leaves["resources_screenshots"].kind == "media"
        assert leaves["archives_ret_prevoyance"].retention == "ret"


def test_distinct_prefixes_outside_archives_keep_their_identity(load_script, tmp_path):
    root = tmp_path / "PARA"
    for rel in [
        "3_Resources/5y_mobilite/a.pdf",
        "3_Resources/5y_mobilite/b.pdf",
        "3_Resources/ctr_mobilite/c.pdf",
        "3_Resources/mobilite/d.pdf",
    ]:
        _touch(root, rel)
    inventory = load_script("para_inventory")
    mapping = inventory.canonical_map(inventory.scan_folders(root))
    assert mapping["3_Resources/5y_mobilite"] == "4_Archives/5y_mobilite"
    assert mapping["3_Resources/ctr_mobilite"] == "4_Archives/ctr_mobilite"
    assert mapping["3_Resources/mobilite"] == "0_Inbox"


def test_review_is_written_when_the_draft_does_not_load(
    load_script, para, legacy, documents, tmp_path, monkeypatch
):
    migrate = load_script("migrate_config")

    def refuse(_path):
        msg = "boom"
        raise migrate.TreeError(msg)

    monkeypatch.setattr(migrate, "load_tree_config", refuse)
    out = tmp_path / "bad-draft"
    argv = ["--para-root", str(para), "--legacy-tree", str(legacy)]
    argv += ["--documents", str(documents), "--out", str(out)]
    assert migrate.main(argv) == 1
    assert "the draft does not load: boom" in (out / "review.md").read_text()


@pytest.mark.parametrize(
    ("rels", "taxonomy", "expected"),
    [
        (
            ["3_Resources/5y_mobilite/a.pdf", "3_Resources/mobilite/b.pdf"],
            {"mobilite": {"5y", "ctr"}},
            {
                "3_Resources/5y_mobilite": "4_Archives/5y_mobilite",
                "3_Resources/mobilite": "0_Inbox",
            },
        ),
        (
            ["3_Resources/5y_travail/a.pdf"],
            {"travail": {"10y"}},
            {"3_Resources/5y_travail": "4_Archives/10y_travail"},
        ),
        (
            [
                "3_Resources/5y_photos/a.jpg",
                "3_Resources/5y_photos/b.jpg",
                "3_Resources/ctr_photos/c.jpg",
            ],
            {},
            {
                "3_Resources/5y_photos": "3_Resources/photos",
                "3_Resources/ctr_photos": "3_Resources/photos",
            },
        ),
    ],
)
def test_records_outside_archives_follow_the_taxonomy(
    load_script, tmp_path, rels, taxonomy, expected
):
    root = tmp_path / "PARA"
    for rel in rels:
        _touch(root, rel)
    inventory = load_script("para_inventory")
    mapping = inventory.canonical_map(inventory.scan_folders(root), taxonomy)
    for rel, target in expected.items():
        assert mapping[rel] == target


def _write_documents(tmp_path: Path, name: str, documents: list[dict[str, object]]) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps({"categories": [{"id": "A", "name": "A", "documents": documents}]}))
    return path


def _run(load_script, root: Path, legacy: Path, documents: Path, out: Path) -> int:
    migrate = load_script("migrate_config")
    argv = ["--para-root", str(root), "--legacy-tree", str(legacy)]
    argv += ["--documents", str(documents), "--out", str(out)]
    return migrate.main(argv)


class TestInventoryAccentsAndSeparators:
    @pytest.mark.parametrize(
        ("folder", "target"),
        [
            ("3_Resources/5y_Vidéos", "3_Resources/Vidéos"),
            ("3_Resources/5y_Médias", "3_Resources/Médias"),
            ("3_Resources/5y_Livres", "3_Resources/Livres"),
        ],
    )
    def test_accented_media_and_library_names_drop_the_prefix(
        self, load_script, tmp_path, folder, target
    ):
        _touch(tmp_path, f"PARA/{folder}/a.pdf")
        inventory = load_script("para_inventory")
        mapping = inventory.canonical_map(inventory.scan_folders(tmp_path / "PARA"))
        assert mapping[folder] == target

    def test_prefix_accepts_a_dash_or_a_space_as_separator(self, load_script):
        inventory = load_script("para_inventory")
        assert inventory.retention_of("5y-factures") == "5y"
        assert inventory.retention_of("5y factures") == "5y"
        assert inventory.strip_prefix("5y factures") == "factures"
        assert inventory.strip_prefix("ctr-factures") == "factures"

    def test_separated_prefix_keeps_its_identity_and_stray_one_is_remapped(
        self, load_script, tmp_path
    ):
        _touch(tmp_path, "PARA/4_Archives/5y factures/a.pdf")
        _touch(tmp_path, "PARA/4_Archives/5y factures/b.pdf")
        _touch(tmp_path, "PARA/4_Archives/2y-factures/c.pdf")
        inventory = load_script("para_inventory")
        mapping = inventory.canonical_map(
            inventory.scan_folders(tmp_path / "PARA"), {"facture": {"5y"}}
        )
        assert mapping["4_Archives/5y factures"] == "4_Archives/5y factures"
        assert mapping["4_Archives/2y-factures"] == "4_Archives/5y factures"


class TestInventoryRoots:
    def test_symlinked_bucket_root_is_not_scanned(self, load_script, tmp_path):
        _touch(tmp_path, "elsewhere/bucket/alpha/a.txt")
        root = tmp_path / "PARA"
        root.mkdir()
        (root / "2_Areas").symlink_to(tmp_path / "elsewhere" / "bucket", target_is_directory=True)
        inventory = load_script("para_inventory")
        assert inventory.scan_folders(root) == []

    def test_synonyms_in_different_buckets_are_not_merged(self, load_script, tmp_path):
        _touch(tmp_path, "PARA/2_Areas/docs/a.pdf")
        _touch(tmp_path, "PARA/2_Areas/docs/b.pdf")
        _touch(tmp_path, "PARA/2_Areas/docs/c.pdf")
        _touch(tmp_path, "PARA/3_Resources/documentation/d.pdf")
        inventory = load_script("para_inventory")
        mapping = inventory.canonical_map(inventory.scan_folders(tmp_path / "PARA"))
        assert mapping["2_Areas/docs"] == "2_Areas/docs"
        assert mapping["3_Resources/documentation"] == "3_Resources/documentation"

    def test_tie_at_the_count_cap_prefers_the_folder_with_more_entries(self, load_script):
        inventory = load_script("para_inventory")
        folders = [
            inventory.Folder("4_Archives", "5y_factures", inventory.COUNT_CAP, ["a", "b", "c"]),
            inventory.Folder("4_Archives", "5y-factures", inventory.COUNT_CAP, ["a"]),
        ]
        mapping = inventory.canonical_map(folders, {"facture": {"5y"}})
        assert mapping["4_Archives/5y-factures"] == "4_Archives/5y_factures"


class TestSeederReview:
    def test_main_refuses_to_overwrite_a_draft_without_force(
        self, load_script, para, legacy, documents, tmp_path
    ):
        out = tmp_path / "draft"
        assert _run(load_script, para, legacy, documents, out) == 0
        (out / "tree.yaml").write_text("# my edits\n")
        migrate = load_script("migrate_config")
        argv = ["--para-root", str(para), "--legacy-tree", str(legacy)]
        argv += ["--documents", str(documents), "--out", str(out)]
        with pytest.raises(SystemExit):
            migrate.main(argv)
        assert (out / "tree.yaml").read_text() == "# my edits\n"
        assert migrate.main([*argv, "--force"]) == 0
        assert (out / "tree.yaml").read_text() != "# my edits\n"

    def test_main_rejects_a_para_root_that_is_not_a_directory(
        self, load_script, legacy, documents, tmp_path
    ):
        out = tmp_path / "draft"
        with pytest.raises(SystemExit):
            _run(load_script, tmp_path / "missing", legacy, documents, out)
        assert not out.exists()

    def test_padded_folder_names_get_a_rename_note(self, load_script, legacy, documents, tmp_path):
        root = tmp_path / "PARA"
        _touch(root, "2_Areas/ carriere /cv.pdf")
        out = tmp_path / "draft"
        assert _run(load_script, root, legacy, documents, out) == 0
        review = (out / "review.md").read_text()
        assert (
            "padded folder name on disk: '2_Areas/ carriere ' — rename it to the trimmed name "
            "before building the golden corpus" in review
        )

    def test_skipped_folders_and_loose_files_are_listed(
        self, load_script, legacy, documents, tmp_path
    ):
        root = tmp_path / "PARA"
        _touch(root, "2_Areas/carriere/cv.pdf")
        _touch(root, "2_Areas/_drafts/x.txt")
        _touch(root, "2_Areas/.cache/y.txt")
        _touch(root, "2_Areas/readme.txt")
        out = tmp_path / "draft"
        assert _run(load_script, root, legacy, documents, out) == 0
        review = (out / "review.md").read_text()
        assert "skipped folder: 2_Areas/_drafts (name starts with . or _)" in review
        assert "skipped folder: 2_Areas/.cache (name starts with . or _)" in review
        assert "loose files in 2_Areas: 1" in review
        assert "loose files in 4_Archives: 0" in review

    def test_unknown_retention_gets_a_note_and_is_proposed_permanent(
        self, load_script, para, legacy, tmp_path
    ):
        docs = _write_documents(
            tmp_path,
            "odd.json",
            [_doc("odd", "weird_value", "3_Resources/administratif/identite")],
        )
        out = tmp_path / "draft"
        assert _run(load_script, para, legacy, docs, out) == 0
        review = (out / "review.md").read_text()
        assert (
            "unknown retention 'weird_value' in documents.json for 3_Resources/administratif; "
            "proposed permanent" in review
        )

    def test_non_ascii_folder_name_gets_a_numbered_leaf_and_a_note(
        self, load_script, legacy, documents, tmp_path
    ):
        root = tmp_path / "PARA"
        _touch(root, "2_Areas/仕事/a.txt")
        out = tmp_path / "draft"
        assert _run(load_script, root, legacy, documents, out) == 0
        leaves = load_tree_config(out).tree.leaves
        assert leaves["leaf_1"].path == "2_Areas/仕事"
        review = (out / "review.md").read_text()
        assert "folder name 2_Areas/仕事 has no ASCII letters or digits; leaf id leaf_1" in review

    def test_issuers_of_a_dropped_rule_are_not_collected(
        self, load_script, para, documents, tmp_path
    ):
        legacy = tmp_path / "legacy-ghost.yaml"
        rules = {
            "ghost": {
                "patterns": ["*ab*"],
                "destination": "2_Areas/carriere",
                "issuers": [{"name": "Ghost Corp", "patterns": ["Ghostco"]}],
            }
        }
        legacy.write_text(yaml.safe_dump({"routing_rules": rules}))
        out = tmp_path / "draft"
        assert _run(load_script, para, legacy, documents, out) == 0
        issuers = yaml.safe_load((out / "issuers.yaml").read_text())["issuers"]
        assert "ghost_corp" not in issuers

    def test_documents_default_resolves_from_the_repo_not_the_working_directory(
        self, load_script, para, legacy, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        migrate = load_script("migrate_config")
        argv = ["--para-root", str(para), "--legacy-tree", str(legacy)]
        assert migrate.main([*argv, "--out", str(tmp_path / "draft")]) == 0


@pytest.mark.parametrize("kept", ["rules.yaml", "issuers.yaml", "review.md"])
def test_main_refuses_without_force_when_any_draft_file_exists(
    load_script, para, legacy, documents, tmp_path, kept
):
    out = tmp_path / "draft"
    assert _run(load_script, para, legacy, documents, out) == 0
    (out / "tree.yaml").unlink()
    (out / kept).write_text("# my edits\n")
    with pytest.raises(SystemExit):
        _run(load_script, para, legacy, documents, out)
    assert (out / kept).read_text() == "# my edits\n"


def test_unknown_retention_is_noted_once_per_folder(load_script):
    migrate = load_script("migrate_config")
    documents = {
        "categories": [
            {
                "documents": [
                    _doc("a", "weird", "4_Archives/5y_factures/{issuer}"),
                    _doc("b", "weird", "4_Archives/5y_factures/{year}"),
                ]
            }
        ]
    }
    notes: list[str] = []
    migrate.document_folders(documents, lambda rel: rel, notes)
    unknown = [note for note in notes if "unknown retention" in note]
    assert len(unknown) == 1
    assert "4_Archives/5y_factures" in unknown[0]


def test_merge_into_a_twin_name_asks_for_a_rename_on_disk(load_script):
    migrate = load_script("migrate_config")
    folder = migrate.Folder("4_Archives", "5y factures", 1)
    notes: list[str] = []
    migrate.draft_tree([folder], lambda rel: "4_Archives/5y_factures", {}, notes)
    assert (
        "merge: 4_Archives/5y factures -> 4_Archives/5y_factures; rename on disk before "
        "building the golden corpus (golden samples leaf paths only)"
    ) in notes


def test_merge_into_an_unrelated_name_gets_no_rename_note(load_script):
    migrate = load_script("migrate_config")
    folder = migrate.Folder("2_Areas", "carriere", 1)
    notes: list[str] = []
    migrate.draft_tree([folder], lambda rel: "2_Areas/career", {}, notes)
    assert "merge: 2_Areas/carriere -> 2_Areas/career" in notes
    assert not any("rename on disk" in note for note in notes)
