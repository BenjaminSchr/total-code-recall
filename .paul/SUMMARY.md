# SUMMARY — total-code-recall V2

**Date:** 2026-05-23
**Milestone:** V2 — Provider Switch + Config + Rename + Supabase + Test Suite
**Waves:** W8 through W14 (7 waves)
**Tasks:** 21 tasks total, all DONE
**Final test result:** 17 passed, 13 skipped, 0 errors

---

## Plan vs Actual

### Wave 8 — Rename (4 tasks) ✓
**Plan:** Rename all skill directories from `code-*` to `tcr-*`, update plugin.json, update README.
**Actual:** Completed as planned. Plugin bumped to v0.2.0 (discovered version mismatch during Wave Review).

### Wave 9 — Config + Info (3 tasks) ✓
**Plan:** Create `tcr-config` (wizard) and `tcr-info` (status page) skills.
**Actual:** Completed as planned. Wave Review caught f-string SQL in tcr-info — fixed to use `psycopg2.sql.Identifier`.

### Wave 10 — Provider Switch (3 tasks) ✓
**Plan:** Add 3-layer config loader to all 5 SKILL.md files + OpenRouter LLM provider in onboard + update.
**Actual:** Completed. Wave Review caught sub-scripts referencing undefined `LLM_PROVIDER` → fixed.

### Wave 11 — Parallel + Model List (2 tasks) ✓
**Plan:** ThreadPoolExecutor parallel OpenRouter calls + live model list from OpenRouter API.
**Actual:** Completed as planned. `_call_openrouter_with_retry()` with exponential backoff added.

### Wave 12 — Embedding Provider (2 tasks) ✓
**Plan:** EMBEDDING_PROVIDER toggle in tcr-config + OpenRouter embedding calls in 4 skills.
**Actual:** 3 HIGH bugs caught by Wave Review:
- Sub-scripts isolated from config.json → added Layer 2 supplement to 12 sub-scripts
- Ollama health check unconditional → made conditional on provider
- Wrong default embedding model (1536-dim) → changed to google/text-embedding-004 (768-dim)

### Wave 13 — Supabase (3 tasks) ✓
**Plan:** DB_PROVIDER toggle in tcr-config, SQL audit, cloud setup docs.
**Actual:** Completed. 2 bugs fixed:
- Empty Supabase URL corrupted config state → guard added
- SSL separator double-? → fixed with `"&" if "?" in url else "?"`

### Wave 14 — Test Suite (4 tasks) ✓
**Plan:** 4 test files covering sanitize, config loader, DB integration, E2E.
**Actual:** Completed. sanitize_project_name in tests diverged from SKILL.md → rewrote to exact logic.

---

## Architecture Summary

### Skills (7 total, all functional)
| Skill | Purpose |
|-------|---------|
| `/tcr-config` | Setup wizard: LLM, Embedding, DB provider selection |
| `/tcr-onboard` | Index a project: chunking, summary generation, embedding, pgvector storage |
| `/tcr-update` | Incremental index update after new commits |
| `/tcr-search` | Semantic search over indexed project |
| `/tcr-overview` | Structural overview via entity/relation graph |
| `/tcr-explain` | Hybrid search: vector + graph context + summaries |
| `/tcr-info` | Show current config, indexed projects, command reference |

### Provider Matrix
| Feature | Local Option | Cloud Option |
|---------|-------------|--------------|
| LLM (summaries) | Ollama (devstral:24b) | OpenRouter (any model) |
| Embeddings | Ollama (nomic-embed-text, 768-dim) | OpenRouter (google/text-embedding-004, 768-dim) |
| Database | pgvector via Docker | Supabase (pooler, session mode, SSL) |

### Config Layers (priority order)
1. Project `.env` file → `os.environ`
2. Global `~/.config/total-code-recall/config.json`
3. Hardcoded defaults

### Test Suite
- `tests/conftest.py` — shared fixtures (sample_project_path, sample_chunks)
- `tests/test_sanitize.py` — 10 tests (sanitize_project_name exact SKILL.md logic + chunking)
- `tests/test_config.py` — 7 tests (3-layer config loader priority: env > config.json > default)
- `tests/test_db.py` — 8 integration tests (skip if DATABASE_URL not set)
- `tests/test_e2e.py` — 5 E2E tests (skip if Ollama or DB unavailable)

---

## Recurring Issues Documented

1. **STATE.md not updated after tasks** — occurred in every wave (W9–W14). Workflow discipline gap, caught by Wave Review each time.
2. **Sub-script isolation** — Sub-scripts run as isolated Python processes. New config variables in the main context must be manually propagated to 6 sub-scripts in each of tcr-onboard and tcr-update. Root cause of most HIGH bugs in V2.

---

## Accepted Risks

- Logic duplicated in onboard + update (drift risk) — documented in STATE.md
- BUG-004 W12: Stale Ollama error messages — LOW severity, accepted
- DB/E2E tests skip without live infrastructure — by design

---

## Status

**V2 COMPLETE — All waves W8–W14 executed and merged to dev.**

Plugin version: 0.2.0
Git tags: W8_done W9_done W10_done W11_done W12_done W13_done W14_done
Final pytest: 17 passed, 13 skipped, 0 errors
