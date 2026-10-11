"""Entry points for the Stage 3 CLI: find files, classify them in parallel, apply a plan."""

from __future__ import annotations

import os
from collections.abc import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from para_files.core.apply import ApplyReport, Op, apply_ops
from para_files.core.cache import Cache, config_fingerprint
from para_files.core.clean import kept_folders
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
            keep=kept_folders(ctx.settings.para_root, ctx.config),
        )
    return run_id, report
