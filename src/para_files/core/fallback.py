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
        ranked = parse_choices(content, menu)
        if not ranked:
            msg = "reply has no usable choice"
            raise FallbackError(msg)
        return ranked

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
