# Phase 9: LLM + Service Reliability - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Ollama-dependent classifiers never hang the pipeline, never crash on Ctrl+C, and recover gracefully when the Ollama server is absent or flaking. Adds API key config for cloud provider swappability via litellm.

</domain>

<decisions>
## Implementation Decisions

### Circuit Breaker
- Shared circuit breaker across semantic + LLM classifiers (both use the same Ollama server)
- Trip threshold: 3 consecutive failures
- Reset strategy: per batch (new `inbox` or `scan` invocation resets the breaker)
- Health check at pipeline init: quick HTTP ping to Ollama; if unreachable, pre-disable semantic and LLM classifiers before any file processing (SVC-03)
- Once tripped, skip remaining Ollama calls for the batch — no further connection attempts (SVC-01)

### Timeout & Interruption
- OllamaEncoder gets a configurable timeout matching LLM (same 15s default, same PARA_FILES_LLM_TIMEOUT config key)
- SemanticClassifier._do_initialize() wraps its embedding computation in try/except KeyboardInterrupt — if interrupted, disable semantic classifier and continue pipeline without it
- Ctrl+C caught at pipeline.classify() level so any classifier interruption returns cleanly (covers both LLM and embedding calls)
- Existing LLM classifier KeyboardInterrupt handling (llm_classifier.py:211) remains as defense-in-depth

### LLM Response Parsing
- JSON-first parsing: try json.loads(text) first, fall back to regex extraction for markdown-wrapped or chatty responses (LLM-04)
- Confidence coercion: handle '0.8', '80%', '80' gracefully — convert '80' to 0.8, strip '%', log debug warning (TEST-04)
- Category validation: after PARA prefix check, also verify the base pattern exists in valid_categories allowlist — catches hallucinated paths (LLM-05)
- URL-decoding check on category paths before validation

### Embedding Cache
- In-memory LRU cache keyed by hash of first 2000 chars of content
- Max ~500 entries, lives for the process lifetime (batch boundary)
- No disk persistence — simple, no I/O overhead (SVC-02)

### Encoder Retry Behavior
- OllamaEncoder stops progressive truncation retry immediately on ConnectionError — shorter text won't fix a dead server (SVC-04)
- Only retry truncation on ValueError/RuntimeError (payload-related errors)

### ISBN Error Distinction
- isbn_lookup.py separates "invalid ISBN" (ValueError) from "service unavailable" (ConnectionError/TimeoutError)
- Retry transient errors (connection/timeout) once before giving up
- Log different messages for each error type (SVC-05)

### Provider Swappability (Ollama/OpenRouter)
- Add PARA_FILES_LLM_API_KEY field to LLMConfig (passed to litellm as api_key)
- Document that users can set PARA_FILES_LLM_MODEL='openrouter/meta-llama/llama-3' (or any litellm-supported prefix) and provide their API key
- No code changes to litellm calls needed — litellm routes by model prefix natively
- Auto-fallback (Ollama → cloud) deferred to future phase

### Claude's Discretion
- Exact LRU cache implementation (functools.lru_cache vs manual dict)
- Circuit breaker data structure (simple counter vs dedicated class)
- Health check implementation details (HTTP endpoint, timeout for the probe itself)
- Pipeline short-circuit optimization details (LLM-03 — already breaking after first match in pipeline.py:265)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — LLM-01 through LLM-05, SVC-01 through SVC-05, TEST-04 requirement definitions

### Phase 8 context (prior decisions)
- `.planning/phases/08-foundation-hardening/08-CONTEXT.md` — Exception narrowing policy, which exception types per module role

### Key source files
- `src/para_files/pipeline.py` — Classification pipeline orchestrator, classifier loop (line 244-287)
- `src/para_files/classifiers/llm_classifier.py` — LLM fallback, existing timeout + KeyboardInterrupt handling
- `src/para_files/classifiers/semantic_classifier.py` — SemanticClassifier with lazy init embedding computation
- `src/para_files/encoders/ollama_encoder.py` — OllamaEncoder with progressive truncation retry
- `src/para_files/config.py` — LLMConfig class (line 116-148), needs API_KEY field
- `src/para_files/utils/isbn_lookup.py` — ISBN lookup, needs error type distinction

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `LLMConfig` in config.py: already has timeout field, just needs api_key addition
- `pipeline.py` classify loop (line 244-287): already breaks on first match, already catches specific exception types — good base for Ctrl+C and circuit breaker integration
- `llm_classifier.py:211`: existing KeyboardInterrupt + RuntimeError handling pattern to replicate
- `OllamaEncoder._encode_single()`: progressive truncation retry — needs ConnectionError short-circuit

### Established Patterns
- Double-checked locking for lazy init (pipeline.py, semantic_classifier.py) — circuit breaker state can use same pattern
- Exception tuple pattern: `except (ConnectionError, TimeoutError, OSError, ValueError, RuntimeError)` — established in Phase 8
- Config via pydantic-settings with env prefix `PARA_FILES_LLM_*` — api_key fits naturally

### Integration Points
- Circuit breaker state needs to be accessible from pipeline.classify() and passed to/shared with SemanticClassifier and LLMClassifier
- Health check runs during `_do_initialize()` in pipeline.py, before appending Ollama-dependent classifiers
- Embedding cache lives in OllamaEncoder or SemanticClassifier (where content is available)

</code_context>

<specifics>
## Specific Ideas

- User wants the ability to swap Ollama for OpenRouter (or other cloud providers) by changing config — litellm already supports this via model prefix, just needs API key config field
- Auto-fallback (Ollama down → automatic switch to cloud) is desired but deferred to keep Phase 9 focused on reliability

</specifics>

<deferred>
## Deferred Ideas

- **Auto-fallback chain** (Ollama → OpenRouter): If Ollama health check fails and API key is set, automatically switch to cloud provider — future phase
- **Disk-persistent embedding cache**: SQLite-based cache for cross-session embedding reuse — future phase if needed
- **Per-classifier independent circuit breakers**: If semantic and LLM ever use different servers — future phase

</deferred>

---

*Phase: 09-llm-service-reliability*
*Context gathered: 2026-03-22*
