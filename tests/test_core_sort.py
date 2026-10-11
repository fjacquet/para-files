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
