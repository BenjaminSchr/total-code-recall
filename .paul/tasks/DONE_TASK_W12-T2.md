**Task:** TASK_W12-T2 — Add OpenRouter embedding calls in tcr-onboard, tcr-update, tcr-search, tcr-explain
**Status:** DONE

**File:** skills/tcr-onboard/SKILL.md, skills/tcr-update/SKILL.md, skills/tcr-search/SKILL.md, skills/tcr-explain/SKILL.md
**Branch:** task/W12-T2-openrouter-embedding-calls
**Worker type:** Claude Code

**What changes:**
Adds an embedding provider if/else to each of the four SKILL.md files that generate embeddings. When `EMBEDDING_PROVIDER=openrouter`, calls the OpenRouter embeddings endpoint. The Ollama path remains the default.

**Ben noob section:**
Embeddings sind die "Zahlen-Darstellung" von Code-Chunks, die für die Suche genutzt werden. Bisher immer über Ollama. Jetzt kann man OpenRouter wählen. Das ist für den Fall, dass kein lokales Ollama verfügbar ist.

**Pattern:**

Add `EMBEDDING_PROVIDER` to the config section (after W10-T1 loader) in each of the four files:
```python
EMBEDDING_PROVIDER = _cfg("EMBEDDING_PROVIDER", "embedding_provider", "ollama")
```

Replace the embedding generation call with an if/else:
```python
def embed_text(text):
    """Generate embedding via configured provider."""
    if EMBEDDING_PROVIDER == "openrouter":
        import requests
        resp = requests.post(
            "https://openrouter.ai/api/v1/embeddings",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": EMBEDDING_MODEL,
                "input": text
            },
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]
    else:
        # Ollama (existing logic)
        import requests
        resp = requests.post(f"{OLLAMA_URL}/api/embeddings", json={
            "model": EMBEDDING_MODEL,
            "prompt": text
        }, timeout=60)
        resp.raise_for_status()
        return resp.json()["embedding"]
```

Apply to:
- `skills/tcr-onboard/SKILL.md` — chunk embedding generation
- `skills/tcr-update/SKILL.md` — chunk embedding generation for new chunks
- `skills/tcr-search/SKILL.md` — query embedding generation
- `skills/tcr-explain/SKILL.md` — query embedding generation

Do NOT change `skills/tcr-overview/SKILL.md` — overview does not generate embeddings.

**Input/Output Contract:**
Depends on: TASK_W10-T1 (config loader in all files), TASK_W12-T1 (embedding_provider config key defined)
Produces: Four SKILL.md files with OpenRouter embedding fallback via `embed_text()` if/else

**Verify:**
```bash
grep -l "openrouter.ai/api/v1/embeddings" skills/tcr-onboard/SKILL.md skills/tcr-update/SKILL.md skills/tcr-search/SKILL.md skills/tcr-explain/SKILL.md | wc -l
```
Must return 4.

**Done when:**
All four SKILL.md files have the `embed_text()` function with `EMBEDDING_PROVIDER` if/else. The OpenRouter path calls `/v1/embeddings`. The Ollama path is the unchanged fallback.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W12-T2.md`. Read each of the four SKILL.md files (tcr-onboard, tcr-update, tcr-search, tcr-explain). Add `EMBEDDING_PROVIDER` to the config section. Find the embedding generation call and replace it with the `embed_text()` function containing the OpenRouter/Ollama if/else. Do NOT touch tcr-overview. Run verify (must return 4). Write Execution Log, rename to `DONE_TASK_W12-T2.md`, commit: `feat: TASK_W12-T2 — add OpenRouter embedding provider in onboard/update/search/explain`.

---

## Execution Log

### Attempt 1
- Date: 2026-05-23
- Result: Added `EMBEDDING_PROVIDER = _cfg("EMBEDDING_PROVIDER", "embedding_provider", "ollama")` to the main config section of all 4 SKILL.md files. In tcr-onboard and tcr-update: replaced `get_embedding()` with `embed_text()` (with OpenRouter/Ollama if/else) in both the `tcr_index.py` and `tcr_build_summaries.py` sub-scripts, and added `EMBEDDING_PROVIDER = os.getenv(...)` to the sub-script config sections; updated all 5 callers in tcr-onboard (2 in tcr_index.py, 3 in tcr_build_summaries.py) and 2 callers in tcr-update. In tcr-search and tcr-explain: added `EMBEDDING_PROVIDER` and `OPENROUTER_API_KEY` to the main config section and replaced the inline Ollama embed call in `tcr_embed_query.py` with `embed_text()` containing the full if/else. Updated prose reference in tcr-update Step 5d from `get_embedding` to `embed_text`. Verify returned 4.
- Files Changed: skills/tcr-onboard/SKILL.md, skills/tcr-update/SKILL.md, skills/tcr-search/SKILL.md, skills/tcr-explain/SKILL.md
- Issues: none
- Status: DONE
