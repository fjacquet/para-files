# Documentation Audit Checklist

Comprehensive checklists for ensuring documentation quality and completeness.

## Quick Audit (After Each PR)

### Code-to-Doc Sync

- [ ] CHANGELOG.md has entry under `[Unreleased]`
- [ ] Entry includes PR/issue number
- [ ] Entry is in correct category (Added/Changed/Fixed/Removed)

### README.md Check (if CLI changed)

- [ ] New commands documented in CLI Commands section
- [ ] New options listed with descriptions
- [ ] Examples work when copy-pasted

### CLAUDE.md Check (if architecture changed)

- [ ] Command table updated
- [ ] Architecture section reflects changes
- [ ] Key files table updated if files added/removed

## Weekly Audit (15 minutes)

### CHANGELOG Status

```bash
# Check unreleased section
head -50 CHANGELOG.md
```

- [ ] `[Unreleased]` section exists and has content
- [ ] Entries are properly categorized
- [ ] No entries missing for recent commits

### README Freshness

```bash
# Test all CLI commands from README
uv run para-files --version
uv run para-files classify --help
uv run para-files move --help
uv run para-files scan --help
uv run para-files clean --help
```

- [ ] All documented commands work
- [ ] Help output matches documented options
- [ ] Examples produce expected results

### Quick Code Scan

```bash
# Find TODO comments in docs
grep -r "TODO" *.md docs/
grep -r "FIXME" *.md docs/
grep -r "WIP" *.md docs/
```

- [ ] No stale TODOs in documentation
- [ ] No "coming soon" for features that exist

## Monthly Deep Audit (1 hour)

### README.md Comprehensive Check

#### Installation Section
- [ ] Clone command works
- [ ] `uv sync --all-extras` installs successfully
- [ ] Prerequisites are accurate

#### Configuration Section
- [ ] All env vars documented
- [ ] Default values are current
- [ ] Example `.env` file is valid

#### CLI Commands Section
- [ ] Every command has documentation
- [ ] Every option is listed
- [ ] Examples are tested and work

#### Architecture Section
- [ ] Pipeline description matches implementation
- [ ] Signal list is accurate with correct confidences
- [ ] Model information is current

### CLAUDE.md Comprehensive Check

#### Commands Table
```bash
# Get actual commands
uv run para-files --help
```
- [ ] Table matches actual CLI commands
- [ ] All options mentioned

#### Architecture Overview
- [ ] Matches current codebase structure
- [ ] File paths in tables exist
- [ ] Diagrams reflect reality

#### Code Style Section
- [ ] Line length matches ruff config
- [ ] Import style matches reality
- [ ] Type checking rules accurate

### Cross-Reference Check

- [ ] README and CLAUDE.md don't contradict each other
- [ ] Configuration described consistently
- [ ] Command names match between docs

### Test Documentation

```bash
# Check test file coverage
ls tests/
wc -l tests/test_*.py
```

- [ ] Major modules have corresponding tests
- [ ] Test files have module docstrings
- [ ] Test functions have descriptive names

## Pre-Release Audit

### Version Preparation

- [ ] CHANGELOG.md: `[Unreleased]` changed to version number
- [ ] CHANGELOG.md: Date added to version header
- [ ] README badges show correct version (if hardcoded)
- [ ] `__version__` in code matches (if applicable)

### Feature Completeness

For each feature in release:
- [ ] Feature documented in CHANGELOG
- [ ] Feature documented in README (if user-facing)
- [ ] Feature has docstrings
- [ ] Feature has tests

### Breaking Change Review

For each breaking change:
- [ ] Migration path documented in CHANGELOG
- [ ] Old behavior noted with new behavior
- [ ] Related docs updated

### Examples Verification

```bash
# Test every code example in README
# Copy-paste each example and verify output
```

- [ ] All bash examples work
- [ ] All Python examples work
- [ ] Output matches expected

### Link Verification

```bash
# Check for broken links (if you have a tool)
# Or manually verify key links
```

- [ ] GitHub badges resolve
- [ ] External links work
- [ ] Internal references (#section) work

## Documentation Debt Tracker

### Known Issues

| Issue | Severity | Location | Status |
|-------|----------|----------|--------|
| Example: Stale screenshot | Low | README.md | TODO |

### Documentation Wishlist

| Enhancement | Priority | Notes |
|-------------|----------|-------|
| API documentation | Medium | Generate from docstrings |
| Video tutorial | Low | Nice to have |

## Automated Checks (CI/CD)

### Currently Implemented

- [ ] Ruff checks Python code style
- [ ] Mypy checks type annotations
- [ ] Tests run on CI

### Potential Additions

- [ ] Markdown linting (markdownlint)
- [ ] Link checking (markdown-link-check)
- [ ] Spell checking (cspell)
- [ ] Example testing (doctest or similar)

## Audit Rotation Schedule

| Week | Focus |
|------|-------|
| 1st of month | Quick audit + README review |
| 2nd of month | Quick audit + CLAUDE.md review |
| 3rd of month | Quick audit + Tests review |
| 4th of month | Deep audit if time allows |
| Pre-release | Full pre-release audit |

## Audit Log Template

```markdown
## Audit - YYYY-MM-DD

### Type
- [x] Quick (PR)
- [ ] Weekly
- [ ] Monthly
- [ ] Pre-release

### Findings

| Issue | Severity | Action |
|-------|----------|--------|
| None | - | - |

### Actions Taken

- Updated X in README
- Fixed Y in CHANGELOG

### Next Review

YYYY-MM-DD
```
