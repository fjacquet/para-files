"""The model reads the file and ranks the leaves (spec §4.2, model first).

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

from loguru import logger

from para_files.core.breaker import CircuitBreaker
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
MAX_LISTED_ENTRIES = 50
MAX_CHOICES = 3
MAX_ISBNS = 3
MAX_ABOUT = 80
# Bump on any change to SYSTEM, messages() or response_format(): it is part of the cache key.
PROMPT_VERSION = "2"
META_FIELDS = (("title", "Title"), ("author", "Author"), ("subject", "Subject"))
SYSTEM = (
    "You file documents into a person's PARA folder tree. Read the content first: the file "
    "name can be misleading. Hints come from the owner's filename rules and issuer patterns; "
    "they are often right but can be wrong, so follow a hint only when the content agrees. "
    "Under 4_Archives, a prefix such as 10y_, 5y_, 2y_, ctr_ or ret_ means records kept for "
    "that retention period; 3_Resources holds reference material, 2_Areas ongoing "
    "responsibilities, 1_Projects active projects. Rank the three most likely folder ids from "
    "the list, most likely first, each with the probability that it is the right folder, and "
    "say in at most 12 words what the document is. Reply only with JSON."
)
Complete = Callable[..., Any]
Ranked = list[tuple[str, float]]


def litellm_complete(**kwargs: Any) -> Any:  # noqa: ANN401 - litellm's keyword arguments and reply
    """litellm.completion, imported on first use: importing litellm takes seconds."""
    import litellm

    litellm.suppress_debug_info = True  # no "Give Feedback" banners on stdout
    return litellm.completion(**kwargs)


class FallbackError(RuntimeError):
    """A reply that cannot be used."""


@dataclass(frozen=True)
class Hint:
    """What a non-deciding rule, book heuristic or issuer suggests; shown to the model."""

    source: str
    leaf_id: str


@dataclass(frozen=True)
class FallbackChoice:
    """The model's first choice, which model answered, its ranked list and what the file is."""

    leaf_id: str
    confidence: float
    model: str
    ranked: tuple[tuple[str, float], ...]
    about: str = ""


def _without_secret_parts(describe: str) -> str:
    head, marker, tail = describe.partition(" (contains: ")
    if not marker:
        return describe
    kept = [part for part in tail.removesuffix(")").split(", ") if not secret_reason(part)]
    return f"{head} (contains: {', '.join(kept)})" if kept else head


def _is_secret_leaf(leaf_id: str, path: str, describe: str) -> bool:
    head = describe.partition(" (contains: ")[0]
    return any(secret_reason(name) for name in (leaf_id, head, *Path(path).parts))


def _keywords_part(keywords: Sequence[str]) -> str:
    kept = [keyword for keyword in keywords if not secret_reason(keyword)]
    return f" [keywords: {', '.join(kept)}]" if kept else ""


def leaf_menu(tree: Tree) -> dict[str, str]:
    """Leaf id -> describe, keywords and path: the model's only choices; no secret leaves."""
    return {
        leaf_id: (
            f"{_without_secret_parts(leaf.describe)}{_keywords_part(leaf.keywords)} ({leaf.path})"
        )
        for leaf_id, leaf in tree.leaves.items()
        if not _is_secret_leaf(leaf_id, leaf.path, leaf.describe)
    }


def _type_line(evidence: Evidence) -> str:
    pages = evidence.doc_meta.get("page_count", "")
    kind = evidence.ext or "(none)"
    return f"Type: {kind}, {pages} pages" if pages not in {"", "0"} else f"Type: {kind}"


def _meta_lines(evidence: Evidence) -> list[str]:
    lines = [_type_line(evidence)]
    for key, label in META_FIELDS:
        value = " ".join(evidence.doc_meta.get(key, "").split())
        if value and secret_reason(value, value) is None:
            lines.append(f"{label}: {value}")
    if evidence.isbns:
        lines.append(f"ISBN found: {', '.join(evidence.isbns[:MAX_ISBNS])}")
    if evidence.exif_date is not None:
        lines.append(f"Date taken: {evidence.exif_date.date().isoformat()}")
    return lines


def visible_hints(hints: Sequence[Hint], menu: dict[str, str]) -> list[Hint]:
    """Hints whose leaf the model may choose and whose wording is not secret."""
    return [hint for hint in hints if hint.leaf_id in menu and secret_reason(hint.source) is None]


def evidence_text(evidence: Evidence, hints: Sequence[Hint] = ()) -> str:
    """Name, type, metadata, hints, the whole preview and archive entries; never the path."""
    lines = [f"Filename: {evidence.name}", *_meta_lines(evidence)]
    if hints:
        lines.append("Hints (from the owner's rules; may be wrong):")
        lines += [f"- {hint.source} -> {hint.leaf_id}" for hint in hints]
    body = evidence.text_preview if evidence.text_preview.strip() else "(no text)"
    text = "\n".join(lines) + f"\n\nContent preview (may come from OCR):\n{body}"
    if evidence.archive_listing:
        entries = "\n".join(evidence.archive_listing[:MAX_LISTED_ENTRIES])
        text += f"\n\nArchive entries:\n{entries}"
    return text


def messages(
    menu: dict[str, str], evidence: Evidence, hints: Sequence[Hint] = ()
) -> list[dict[str, str]]:
    """System prompt, then the folder list (stable, so providers can cache it), then the file."""
    folders = "\n".join(f"- {leaf_id}: {describe}" for leaf_id, describe in menu.items())
    file_part = evidence_text(evidence, visible_hints(hints, menu))
    user = f"Folders:\n{folders}\n\nFile:\n{file_part}"
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def response_format(menu: dict[str, str]) -> dict[str, Any]:
    """JSON schema: a short 'about' and up to 3 choices, each an enum leaf id with a confidence."""
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
        "required": ["about", "choices"],
        "properties": {
            "about": {"type": "string"},
            "choices": {"type": "array", "items": choice, "minItems": 1, "maxItems": MAX_CHOICES},
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


def parse_reply(content: str | None, menu: dict[str, str]) -> tuple[Ranked, str]:
    """Ranked (leaf, probability) and the model's one-line 'about'; bad choices dropped."""
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
    about = data.get("about") if isinstance(data, dict) else None
    text = " ".join(about.split())[:MAX_ABOUT] if isinstance(about, str) else ""
    return ranked[:MAX_CHOICES], text


class OpenRouterFallback:
    """The model signal: primary model, then backup, through litellm; behind a circuit breaker."""

    def __init__(
        self,
        key: str,
        models: Sequence[str],
        *,
        complete: Complete = litellm_complete,
        breaker: CircuitBreaker | None = None,
    ) -> None:
        self._key = key
        self._models = tuple(models)
        self._complete = complete
        self._breaker = breaker or CircuitBreaker()

    def _ask(
        self, model: str, menu: dict[str, str], evidence: Evidence, hints: Sequence[Hint]
    ) -> tuple[Ranked, str]:
        response = self._complete(
            model=f"{OPENROUTER}{model}",
            messages=messages(menu, evidence, hints),
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
        ranked, about = parse_reply(content, menu)
        if not ranked:
            msg = "reply has no usable choice"
            raise FallbackError(msg)
        return ranked, about

    def decide(
        self, evidence: Evidence, tree: Tree, hints: Sequence[Hint] = ()
    ) -> FallbackChoice | None:
        """First choice of the first model that answers; None for secrets or failures."""
        if evidence.secret is not None or self._breaker.is_open:
            return None
        menu = leaf_menu(tree)
        if not menu:
            return None
        for model in self._models:
            try:
                ranked, about = self._ask(model, menu, evidence, hints)
            except Exception as exc:  # noqa: BLE001 - any provider error moves on to the backup
                logger.warning("model {} failed on {}: {}", model, evidence.name, exc)
                continue
            self._breaker.record_success()
            leaf_id, confidence = ranked[0]
            return FallbackChoice(leaf_id, confidence, model, tuple(ranked), about)
        self._breaker.record_failure()
        return None


def make_fallback(
    settings: CoreSettings, *, complete: Complete = litellm_complete
) -> OpenRouterFallback | None:
    """The configured fallback, or None when it is off or no key is set."""
    if not settings.fallback_enabled or settings.openrouter_api_key is None:
        return None
    return OpenRouterFallback(
        settings.openrouter_api_key.get_secret_value(),
        (settings.fallback_model, settings.fallback_backup_model),
        complete=complete,
    )
