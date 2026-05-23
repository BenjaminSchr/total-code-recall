**Task:** TASK_W10-T2 — Add OpenRouter LLM provider in tcr-onboard SKILL.md
**Status:** TODO

**File:** skills/tcr-onboard/SKILL.md
**Branch:** task/W10-T2-openrouter-provider-onboard
**Worker type:** Claude Code

**What changes:**
Adds OpenRouter as an alternative LLM provider for summary generation in tcr-onboard. The embedded `tcr_build_summaries.py` script gets an if/else branch: when `LLM_PROVIDER=openrouter`, calls the OpenAI-compatible OpenRouter API; otherwise uses existing Ollama logic.

**Ben noob section:**
tcr-onboard generiert für jeden Code-Chunk eine Zusammenfassung. Bisher immer über Ollama (lokal, langsam). Jetzt kann man OpenRouter wählen und es geht viel schneller — sequential hier, parallel kommt in W11.

**Pattern:**

In the `tcr_build_summaries.py` embedded script section of `skills/tcr-onboard/SKILL.md`, add config variables and replace the summary generation call:

Add to config section (after W10-T1 loader):
```python
LLM_PROVIDER         = _cfg("LLM_PROVIDER",         "llm_provider",          "ollama")
OPENROUTER_API_KEY   = _cfg("OPENROUTER_API_KEY",    "openrouter_api_key",    "")
OPENROUTER_MODEL     = _cfg("OPENROUTER_MODEL",      "openrouter_model",      "google/gemini-flash-2.0")
PARALLEL_WORKERS     = int(_cfg("PARALLEL_WORKERS",  "parallel_workers",      "10"))
```

Replace the summary generation function with an if/else:
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
        # Ollama (existing logic)
        import requests
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json={
            "model": SUMMARY_MODEL,
            "prompt": prompt,
            "stream": False
        }, timeout=120)
        resp.raise_for_status()
        return resp.json()["response"].strip()
```

Do NOT add parallelism here — that is W11-T1. This task adds the provider branch only.

**Input/Output Contract:**
Depends on: TASK_W10-T1 (3-layer config loader present in tcr-onboard/SKILL.md)
Produces: tcr-onboard SKILL.md with OpenRouter if/else in summary generation

**Verify:**
```bash
grep -c "openrouter.ai/api/v1/chat/completions" skills/tcr-onboard/SKILL.md
```
Must return >= 1.

**Done when:**
`skills/tcr-onboard/SKILL.md` contains an `if LLM_PROVIDER == "openrouter":` branch that calls OpenRouter, and an `else:` branch with the existing Ollama call.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W10-T2.md`. Read `skills/tcr-onboard/SKILL.md`. Find the summary generation section in the embedded `tcr_build_summaries.py` script. Add the four new config variables after the existing config loader. Replace the summary generation call with the `generate_summary()` function that has the if/else OpenRouter/Ollama branch. Do NOT add parallelism. Run verify. Write Execution Log, rename to `DONE_TASK_W10-T2.md`, commit: `feat: TASK_W10-T2 — add OpenRouter LLM provider branch in tcr-onboard`.
