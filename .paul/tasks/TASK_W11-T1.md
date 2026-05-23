**Task:** TASK_W11-T1 — Add ThreadPoolExecutor parallel OpenRouter calls in tcr-onboard + tcr-update
**Status:** TODO

**File:** skills/tcr-onboard/SKILL.md, skills/tcr-update/SKILL.md
**Branch:** task/W11-T1-parallel-openrouter-calls
**Worker type:** Claude Code

**What changes:**
Wraps the OpenRouter branch of `generate_summary()` in a ThreadPoolExecutor with 10 workers and exponential backoff on 429 responses. The Ollama branch stays sequential (Ollama doesn't need parallel calls). Only applies when `LLM_PROVIDER == "openrouter"`.

**Ben noob section:**
Mit OpenRouter können wir 10 Summaries gleichzeitig generieren statt eine nach der anderen. Das macht Onboard von 40 Minuten auf unter 5 Minuten. Bei zu vielen Requests auf einmal (429 Error) warten wir kurz und probieren nochmal.

**Pattern:**

In `skills/tcr-onboard/SKILL.md` and `skills/tcr-update/SKILL.md`, replace the sequential chunk-processing loop in the OpenRouter path with a parallel version.

Add retry wrapper around the OpenRouter call:
```python
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def _call_openrouter_with_retry(prompt, max_retries=5):
    """Call OpenRouter with exponential backoff on 429."""
    import requests
    for attempt in range(max_retries):
        try:
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
            if resp.status_code == 429:
                wait = (2 ** attempt) + 1  # 2s, 5s, 9s, 17s, 33s
                print(f"  Rate limited, waiting {wait}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("OpenRouter: max retries exceeded")
```

Replace the chunk loop in the OpenRouter path with:
```python
if LLM_PROVIDER == "openrouter":
    def _process_chunk(chunk):
        prompt = f"Summarize this code in 1-2 sentences:\n\n{chunk['content']}"
        summary = _call_openrouter_with_retry(prompt)
        return chunk["id"], summary

    results = {}
    with ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as executor:
        futures = {executor.submit(_process_chunk, c): c for c in chunks_needing_summary}
        for i, future in enumerate(as_completed(futures), 1):
            chunk_id, summary = future.result()
            results[chunk_id] = summary
            if i % 10 == 0:
                print(f"  {i}/{len(chunks_needing_summary)} summaries generated")
else:
    # Ollama: sequential (unchanged)
    results = {}
    for chunk in chunks_needing_summary:
        prompt = f"Summarize this code in 1-2 sentences:\n\n{chunk['content']}"
        results[chunk["id"]] = generate_summary(prompt)
```

Apply identically to both tcr-onboard and tcr-update SKILL.md files.

**Input/Output Contract:**
Depends on: TASK_W10-T2 (OpenRouter branch in onboard), TASK_W10-T3 (OpenRouter branch in update)
Produces: Both SKILL.md files use ThreadPoolExecutor for OpenRouter calls, with retry logic

**Verify:**
```bash
grep -c "ThreadPoolExecutor" skills/tcr-onboard/SKILL.md && grep -c "ThreadPoolExecutor" skills/tcr-update/SKILL.md
```
Must return >= 1 for each file.

**Done when:**
Both `skills/tcr-onboard/SKILL.md` and `skills/tcr-update/SKILL.md` contain `ThreadPoolExecutor` with `max_workers=PARALLEL_WORKERS` in the OpenRouter code path, and `_call_openrouter_with_retry` with exponential backoff on 429.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W11-T1.md`. Read `skills/tcr-onboard/SKILL.md` and `skills/tcr-update/SKILL.md`. In both files, find the OpenRouter summary generation section added in W10. Add the `_call_openrouter_with_retry` function with exponential backoff. Replace the sequential OpenRouter call with the ThreadPoolExecutor parallel version. Leave the Ollama path sequential. Run verify for both files. Write Execution Log, rename to `DONE_TASK_W11-T1.md`, commit: `feat: TASK_W11-T1 — parallel OpenRouter calls with retry in tcr-onboard + tcr-update`.
