**Task:** TASK_W10-T3 — Add OpenRouter LLM provider in tcr-update SKILL.md
**Status:** DONE

**File:** skills/tcr-update/SKILL.md
**Branch:** task/W10-T3-openrouter-provider-update
**Worker type:** Claude Code

**What changes:**
Applies the same OpenRouter provider if/else pattern from W10-T2 to `skills/tcr-update/SKILL.md`. Identical pattern — the update skill also generates summaries for new/changed chunks.

**Ben noob section:**
tcr-update ist wie tcr-onboard, aber nur für neue Commits. Auch hier werden Summaries generiert — also braucht es auch hier den OpenRouter-Pfad.

**Pattern:**

Identical to W10-T2. In the summary generation section of the embedded script in `skills/tcr-update/SKILL.md`:

Add config variables (same four as W10-T2):
```python
LLM_PROVIDER         = _cfg("LLM_PROVIDER",         "llm_provider",          "ollama")
OPENROUTER_API_KEY   = _cfg("OPENROUTER_API_KEY",    "openrouter_api_key",    "")
OPENROUTER_MODEL     = _cfg("OPENROUTER_MODEL",      "openrouter_model",      "google/gemini-flash-2.0")
PARALLEL_WORKERS     = int(_cfg("PARALLEL_WORKERS",  "parallel_workers",      "10"))
```

Replace summary call with same `generate_summary()` function:
```python
def generate_summary(prompt):
    if LLM_PROVIDER == "openrouter":
        import requests
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200
            },
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    else:
        import requests
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json={
            "model": SUMMARY_MODEL,
            "prompt": prompt,
            "stream": False
        }, timeout=120)
        resp.raise_for_status()
        return resp.json()["response"].strip()
```

Do NOT add parallelism here — that is W11-T1.

**Input/Output Contract:**
Depends on: TASK_W10-T1 (3-layer config loader in tcr-update/SKILL.md), TASK_W10-T2 (pattern validated in onboard)
Produces: tcr-update SKILL.md with OpenRouter if/else in summary generation

**Verify:**
```bash
grep -c "openrouter.ai/api/v1/chat/completions" skills/tcr-update/SKILL.md
```
Must return >= 1.

**Done when:**
`skills/tcr-update/SKILL.md` contains the same `generate_summary()` if/else as tcr-onboard. Pattern is identical.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W10-T3.md`. Read `skills/tcr-update/SKILL.md`. Apply the identical pattern from W10-T2 — add the four config variables and the `generate_summary()` if/else function. Do not add parallelism. Run verify. Write Execution Log, rename to `DONE_TASK_W10-T3.md`, commit: `feat: TASK_W10-T3 — add OpenRouter LLM provider branch in tcr-update`.

---

## Execution Log

### Attempt 1
- Date: 2026-05-23
- Result: Added 4 new config variables (LLM_PROVIDER, OPENROUTER_API_KEY, OPENROUTER_MODEL, PARALLEL_WORKERS) after the existing config block in SKILL.md. Replaced the existing `generate_summary()` function in the `/tmp/tcr_index.py` section (Step 5b) with the OpenRouter-aware if/else version. The prompt building logic was preserved; only the HTTP call was branched. Verify grep returned 1.
- Files Changed: skills/tcr-update/SKILL.md
- Issues: none
- Status: DONE
