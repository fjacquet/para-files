"""Authoritative bake-off for signal 4 (spec §4.5). Throwaway developer tool.

Scope (a): golden record/library/media files the baseline left non-green.
Scope (b): golden knowledge files, scored as top-3 suggestions.

Every cloud request carries provider.zdr=true. A prediction is yellow when a leaf came back;
failed and empty answers are red. Files outside the PARA root, and files the secrets guard
flags by name (file or folder) or by content, are red and never sent. The verdict is eval.py's
curve (max coverage at >= 98% precision).

Usage:
    uv run python scripts/bakeoff.py --candidate jev --para-root "$PARA"
    uv run python scripts/eval.py --pred ~/.config/para-files/pred_jev.jsonl --only-predicted
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values
from para_inventory import nfc, read_jsonl

from para_files.core.secrets import secret_reason
from para_files.core.tree import Tree, config_dir, load_tree_config


OPENROUTER = "https://openrouter.ai"
GEMINI = "google/gemini-3.8-flash"
SONNET = "anthropic/claude-sonnet-5.5"
JEV = "typesafe/jev-1.13"
PRIVACY = {"zdr": True, "data_collection": "deny"}
# Gemini 3.8 Flash and Sonnet 5.5 reject reasoning.enabled=false; reasoning tokens need room.
REASONING = {"effort": "low"}
MAX_TOKENS = 4000
RETRY_STATUS = frozenset({429, 502, 503, 524, 529})
SYSTEM = (
    "You file documents into a person's PARA folder tree. Rank the three most likely folder "
    "ids from the list for this file, most likely first, each with the probability that it is "
    "the right folder. Reply only with JSON."
)
Post = Callable[..., httpx.Response]
Ranked = list[tuple[str, float]]
PREVIEW_CHARS = 2000
RETRY_AFTER_CAP = 60.0


class ReplyError(RuntimeError):
    """A failed call that still reported what it cost (its body's usage.cost)."""

    def __init__(self, message: str, cost: float) -> None:
        super().__init__(message)
        self.cost = cost


def _without_secret_parts(describe: str) -> str:
    """The describe with every secret-named part of its "(contains: ...)" list left out."""
    head, marker, tail = describe.partition(" (contains: ")
    if not marker:
        return describe
    kept = [part for part in tail.removesuffix(")").split(", ") if not secret_reason(part)]
    return f"{head} (contains: {', '.join(kept)})" if kept else head


def leaf_menu(tree: Tree) -> dict[str, str]:
    """Leaf id -> describe, the choice list every candidate sees (no secret-named folders)."""
    return {leaf_id: _without_secret_parts(leaf.describe) for leaf_id, leaf in tree.leaves.items()}


def evidence_text(name: str, preview: str) -> str:
    """Identical evidence for every candidate: filename + preview."""
    preview = preview[:PREVIEW_CHARS]
    body = preview if preview.strip() and preview.strip() != name else "(no text)"
    return f"Filename: {name}\n\nContent preview:\n{body}"


def llm_schema(menu: dict[str, str]) -> dict[str, Any]:
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
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["choices"],
        "properties": {"choices": {"type": "array", "items": choice, "minItems": 1, "maxItems": 3}},
    }


def llm_messages(menu: dict[str, str], name: str, preview: str) -> list[dict[str, str]]:
    """System + user messages listing the leaves and the file evidence."""
    folders = "\n".join(f"- {leaf_id}: {describe}" for leaf_id, describe in menu.items())
    user = f"Folders:\n{folders}\n\nFile:\n{evidence_text(name, preview)}"
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def parse_choices(text: str | None, menu: dict[str, str]) -> Ranked:
    """Ranked (leaf, probability) pairs from an LLM reply; unknown or repeated leaves dropped."""
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    try:
        data = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        return []
    ranked: Ranked = []
    for item in data.get("choices", []) if isinstance(data, dict) else []:
        leaf, confidence = item.get("leaf"), item.get("confidence")
        known = leaf in menu and leaf not in [seen for seen, _ in ranked]
        valid = isinstance(confidence, (int, float)) and not isinstance(confidence, bool)
        if known and valid and math.isfinite(confidence):
            ranked.append((leaf, max(0.0, min(1.0, float(confidence)))))
    return ranked[:3]


def post_with_retry(post: Post, url: str, **kwargs: object) -> httpx.Response:
    """POST, retrying rate limits and transient provider errors (Retry-After honoured)."""
    response = post(url, **kwargs)
    for attempt in range(4):
        if response.status_code not in RETRY_STATUS:
            return response
        retry_after = response.headers.get("Retry-After", "")
        delay = (
            min(RETRY_AFTER_CAP, float(retry_after))
            if retry_after.isdigit()
            else min(30.0, 2**attempt + random.random())  # noqa: S311 - jitter, not security
        )
        time.sleep(delay)
        response = post(url, **kwargs)
    return response


def _reply(response: httpx.Response) -> tuple[Any, float]:
    """Body and cost of a reply; an HTTP error raises ReplyError carrying the cost."""
    try:
        body: Any = response.json()
    except ValueError:
        body = None
    usage = body.get("usage") if isinstance(body, dict) else None
    raw = usage.get("cost") if isinstance(usage, dict) else None
    numeric = isinstance(raw, (int, float)) and not isinstance(raw, bool) and math.isfinite(raw)
    cost = float(raw) if numeric else 0.0
    if response.is_error:
        message = f"HTTP {response.status_code}"
        raise ReplyError(message, cost)
    return body, cost


def ask_llm(
    model: str, post: Post, key: str, menu: dict[str, str], name: str, preview: str
) -> tuple[Ranked, float]:
    """An OpenRouter chat model: enum-constrained, low reasoning effort, ZDR enforced."""
    response = post_with_retry(
        post,
        f"{OPENROUTER}/api/v1/chat/completions",
        timeout=120,
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": model,
            "messages": llm_messages(menu, name, preview),
            "temperature": 0,
            "max_tokens": MAX_TOKENS,
            "reasoning": REASONING,
            "provider": PRIVACY,
            "usage": {"include": True},
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "filing", "strict": True, "schema": llm_schema(menu)},
            },
        },
    )
    body, cost = _reply(response)
    try:
        content = body["choices"][0]["message"].get("content")
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        msg = f"malformed reply: {type(exc).__name__}"
        raise ReplyError(msg, cost) from exc
    return parse_choices(content, menu), cost


def ask_gemini(
    post: Post, key: str, menu: dict[str, str], name: str, preview: str
) -> tuple[Ranked, float]:
    """Gemini 3.8 Flash, the owner's first choice."""
    return ask_llm(GEMINI, post, key, menu, name, preview)


def ask_sonnet(
    post: Post, key: str, menu: dict[str, str], name: str, preview: str
) -> tuple[Ranked, float]:
    """Claude Sonnet 5.5, the owner's second choice."""
    return ask_llm(SONNET, post, key, menu, name, preview)


def ask_jev(
    post: Post, key: str, menu: dict[str, str], name: str, preview: str
) -> tuple[Ranked, float]:
    """Jev 1.13 via the Decisions API: one choice question, probability per leaf, ZDR enforced."""
    response = post_with_retry(
        post,
        f"{OPENROUTER}/api/alpha/decisions",
        timeout=120,
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": JEV,
            "provider": PRIVACY,
            "questions": {
                "leaf": {
                    "type": "choice",
                    "criteria": menu,
                    "instructions": "Which folder of this person's PARA file tree should "
                    "this file be filed in?",
                }
            },
            "state": {"filename": name, "content_preview": evidence_text(name, preview)},
        },
    )
    body, cost = _reply(response)
    try:
        probabilities = body["answers"]["leaf"].get("probabilities", {})
        ranked = sorted(
            ((leaf, float(p)) for leaf, p in probabilities.items() if leaf in menu),
            key=lambda pair: -pair[1],
        )
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        msg = f"malformed reply: {type(exc).__name__}"
        raise ReplyError(msg, cost) from exc
    return ranked[:3], cost


# Insertion order is the owner's preference; it breaks ties between equal results (spec §4.5).
CANDIDATES: dict[str, tuple[Callable[..., tuple[Ranked, float]], int]] = {
    "gemini": (ask_gemini, 6),
    "sonnet": (ask_sonnet, 6),
    "jev": (ask_jev, 8),
}


def select_scope(
    golden: list[dict[str, Any]], baseline: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Scope (a): non-knowledge files the baseline left non-green. Scope (b): knowledge files."""
    base = {nfc(p["path"]): p for p in baseline}
    scoped: list[dict[str, Any]] = []
    for row in golden:
        if row["kind"] == "knowledge":
            scoped.append({**row, "scope": "b"})
        elif base.get(nfc(row["path"]), {}).get("band") != "green":
            scoped.append({**row, "scope": "a"})
    return scoped


def read_preview(path: Path) -> str:
    """First 2000 characters of text, using the existing extractors (read-only)."""
    from para_files.utils.file_utils import read_content_preview

    return read_content_preview(path, max_chars=2000)


def resolve_inside(para_root: Path, rel: str) -> Path | None:
    """The file a PARA-relative path points at, or None when it resolves outside the root."""
    root = para_root.resolve()
    path = (root / rel).resolve()
    return path if path.is_relative_to(root) else None


def _is_secret(rel: str, preview: str) -> bool:
    """A secret name in the file or any folder above it, or secret content in the preview."""
    parts = Path(rel).parts
    return secret_reason(parts[-1], preview) is not None or any(
        secret_reason(part) is not None for part in parts
    )


def _refused(row: dict[str, Any], signal: str) -> dict[str, Any]:
    """A red row for a file that was never sent: no leaf, no cost."""
    return {
        "path": row["path"],
        "scope": row["scope"],
        "leaf": None,
        "confidence": 0.0,
        "band": "red",
        "signal": signal,
        "secs": 0.0,
        "cost": 0.0,
    }


def predict(  # noqa: PLR0913, PLR0917 - the seven inputs are pinned by the tests' call sites
    row: dict[str, Any],
    para_root: Path,
    menu: dict[str, str],
    ask: Callable[..., tuple[Ranked, float]],
    post: Post,
    key: str,
    preview_of: Callable[[Path], str],
) -> dict[str, Any]:
    """One prediction row; secret files are never sent; one bad file never stops the run."""
    start = time.monotonic()
    try:
        path = resolve_inside(para_root, row["path"])
        if path is None:
            return _refused(row, "outside")
        try:
            preview = preview_of(path)
        except Exception:  # noqa: BLE001 - unreadable or online-only: classify by name alone
            preview = ""
        if _is_secret(row["path"], preview):
            return _refused(row, "secret")
    except Exception as exc:  # noqa: BLE001 - a file that cannot be checked is never sent
        return {**_refused(row, "error"), "error": f"{type(exc).__name__}: {exc}"[:200]}
    error = None
    try:
        ranked, cost = ask(post, key, menu, Path(row["path"]).name, preview)
    except Exception as exc:  # noqa: BLE001 - one bad reply must not stop the run
        ranked, error = [], f"{type(exc).__name__}: {exc}"[:200]
        cost = exc.cost if isinstance(exc, ReplyError) else 0.0
    if error is None and not ranked:
        error = "empty answer"
    leaf = ranked[0][0] if ranked else None
    pred = {
        "path": row["path"],
        "scope": row["scope"],
        "leaf": leaf,
        "confidence": ranked[0][1] if ranked else 0.0,
        "band": "yellow" if leaf else "red",
        "top3": [candidate for candidate, _ in ranked],
        "signal": "fallback",
        "secs": round(time.monotonic() - start, 3),
        "cost": cost,
    }
    if error:
        pred["error"] = error
    return pred


def _finished(futures: list[Future[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Results of the calls that completed without an error, in row order."""
    return [f.result() for f in futures if f.done() and not f.cancelled() and f.exception() is None]


def predict_all(
    rows: list[dict[str, Any]],
    run: Callable[[dict[str, Any]], dict[str, Any]],
    workers: int,
    out: Path,
) -> list[dict[str, Any]]:
    """Predict rows in order. On Ctrl+C or any error: cancel pending calls, keep every finished
    prediction, write them, and re-raise."""
    pool = ThreadPoolExecutor(workers)
    futures = [pool.submit(run, row) for row in rows]
    try:
        preds = [future.result() for future in futures]
    except BaseException as exc:
        pool.shutdown(wait=False, cancel_futures=True)
        preds = _finished(futures)
        _write_preds(out, preds)
        if isinstance(exc, KeyboardInterrupt):
            print(f"interrupted: kept {len(preds)} of {len(rows)} predictions -> {out}")
        raise
    pool.shutdown()
    _write_preds(out, preds)
    return preds


def _write_preds(out: Path, preds: list[dict[str, Any]]) -> None:
    out.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in preds), "utf-8")


def main(argv: list[str] | None = None) -> int:
    """Run one candidate over the bake-off scope and write its predictions; return 0."""
    parser = argparse.ArgumentParser(description="Run one signal-4 candidate.")
    parser.add_argument("--candidate", choices=sorted(CANDIDATES), required=True)
    parser.add_argument("--para-root", type=Path, required=True)
    parser.add_argument("--config-dir", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--baseline", type=Path, default=None, help="default: <config dir>/pred_baseline.jsonl"
    )
    args = parser.parse_args(argv)
    cfg_dir = args.config_dir or config_dir()
    para_root = args.para_root.expanduser().resolve()
    key = (
        os.environ.get("OPENROUTER_API_KEY")
        or dotenv_values(".env").get("PARA_FILES_LLM_API_KEY")
        or dotenv_values(cfg_dir / ".env").get("PARA_FILES_LLM_API_KEY")
        or ""
    )
    if not key:
        parser.error("set OPENROUTER_API_KEY or PARA_FILES_LLM_API_KEY in .env")
    baseline_path = args.baseline or cfg_dir / "pred_baseline.jsonl"
    rows = select_scope(read_jsonl(cfg_dir / "golden.jsonl"), read_jsonl(baseline_path))
    rows = rows[: args.limit]
    menu = leaf_menu(load_tree_config(cfg_dir).tree)
    ask, workers = CANDIDATES[args.candidate]
    out = cfg_dir / f"pred_{args.candidate}.jsonl"
    preds = predict_all(
        rows,
        lambda r: predict(r, para_root, menu, ask, httpx.post, key, read_preview),
        workers,
        out,
    )
    errors = sum(1 for p in preds if "error" in p)
    secrets = sum(1 for p in preds if p["signal"] == "secret")
    print(
        f"{args.candidate}: {len(preds)} files, {errors} errors, "
        f"{secrets} secrets kept local -> {out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
