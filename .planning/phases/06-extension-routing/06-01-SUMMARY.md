---
phase: 06-extension-routing
plan: 01
subsystem: classification
tags: [extension-routing, para-files, classifier, config, pydantic-settings]

# Dependency graph
requires: []
provides:
  - ExtensionRoutingConfig BaseSettings with 6 configurable folder-path fields
  - ExtensionRouterClassifier implementing BaseClassifier for extension-based routing
  - ClassificationSource.EXTENSION_ROUTER enum member in types.py
  - Config.extension_routing nested field with env-var override support
affects:
  - 06-extension-routing (subsequent plans integrating this classifier into pipeline)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - BaseSettings subclass with env_prefix for nested config (matches MLXConfig/LLMConfig pattern)
    - Module-level EXTENSION_GROUPS dict mapping extensions to (folder_attr, confidence) tuples
    - BaseClassifier implementation returning None for no-extension files (pipeline continues)

key-files:
  created:
    - src/para_files/classifiers/extension_router.py
  modified:
    - src/para_files/config.py
    - src/para_files/types.py

key-decisions:
  - "Extension catch-all routing for media/exotic types: extension is definitive, content is unreadable"
  - "catch-all confidence set to 0.80 (lower than known groups 0.97-0.98) to allow pipeline override if needed"
  - "Empty extension returns None so pipeline can continue to LLM fallback"

patterns-established:
  - "Classifier pattern: inject config in __init__, lookup in module-level dict, getattr for dynamic folder resolution"

requirements-completed: [ROUTE-01, ROUTE-02, ROUTE-03, ROUTE-04, ROUTE-05, ROUTE-06]

# Metrics
duration: 8min
completed: 2026-03-01
---

# Phase 6 Plan 01: Extension Routing Classifier Summary

**ExtensionRouterClassifier with 17-extension routing map (video/audio/images/security/scripts) and catchall, backed by ExtensionRoutingConfig with 6 env-var-overridable folder paths**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-01T08:12:00Z
- **Completed:** 2026-03-01T08:20:57Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `ExtensionRoutingConfig` BaseSettings with 6 folder fields and `PARA_FILES_EXT_ROUTING_` env prefix
- Added `Config.extension_routing` nested field (matching `MLXConfig`/`LLMConfig`/`LLMConfig` pattern)
- Created `ExtensionRouterClassifier` with module-level `EXTENSION_GROUPS` dict covering 17 extensions across 5 groups
- Added `ClassificationSource.EXTENSION_ROUTER` enum member to `types.py`
- Catch-all for unknown extensions (0.80 confidence), None return for no-extension files

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ExtensionRoutingConfig to config.py** - `f32acfe` (feat)
2. **Task 2: Implement ExtensionRouterClassifier** - `d7fef38` (feat)

## Files Created/Modified

- `src/para_files/classifiers/extension_router.py` - New classifier with EXTENSION_GROUPS map and BaseClassifier implementation
- `src/para_files/config.py` - Added ExtensionRoutingConfig class and Config.extension_routing field
- `src/para_files/types.py` - Added ClassificationSource.EXTENSION_ROUTER enum member

## Decisions Made

- Extension routing confidence: known groups at 0.97-0.98 (deterministic), catch-all at 0.80 (softer, pipeline can override)
- Empty extension returns None: files without extensions (e.g., `Makefile`) should not go to misc
- `getattr(self._config, folder_attr)` pattern avoids large if/elif chains for 6 folder types

## Deviations from Plan

**[Rule 3 - Blocking] Auto-fixed import ordering for ruff I001**
- **Found during:** Task 2 (implementation)
- **Issue:** Ruff I001 flagged import block ordering in new extension_router.py
- **Fix:** Ran `uv run ruff check --fix` to auto-sort imports
- **Files modified:** src/para_files/classifiers/extension_router.py
- **Verification:** `ruff check` passes with no errors
- **Committed in:** d7fef38 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking — import ordering)
**Impact on plan:** Trivial auto-fix. No scope creep.

## Issues Encountered

- Pre-existing mypy `unused-ignore` errors in 4 unrelated files (`isbn_lookup.py`, `mlx_encoder.py`, `geolocation.py`, `pdf_metadata.py`) — out of scope, not caused by this plan's changes.

## Next Phase Readiness

- ExtensionRouterClassifier is importable and fully functional
- Ready to be integrated into the classification pipeline (subsequent plan in this phase)
- Config.extension_routing field available for pipeline instantiation

---
*Phase: 06-extension-routing*
*Completed: 2026-03-01*
