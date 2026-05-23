**Task:** TASK_W11-T2 — Add live model list from OpenRouter API in tcr-config
**Status:** DONE

**File:** skills/tcr-config/SKILL.md
**Branch:** task/W11-T2-openrouter-model-list
**Worker type:** Claude Code

**What changes:**
Updates `skills/tcr-config/SKILL.md` to fetch the live model list from `GET https://openrouter.ai/api/v1/models` when the user selects OpenRouter as LLM provider, filtered to Anthropic/Google/OpenAI/Qwen/Kimi models. Shows the filtered list for the user to pick from.

**Ben noob section:**
Statt dem User zu sagen "tippe einen Model-Namen ein", holen wir die aktuelle Liste von OpenRouter und zeigen nur die wichtigen Modelle an. Der User wählt eine Nummer, nicht einen langen String.

**Pattern:**

In `skills/tcr-config/SKILL.md`, in the Setup Mode Toggle 1 section (when user picks Cloud/OpenRouter), add after asking for the API key:

```python
def fetch_openrouter_models(api_key):
    """Fetch and filter model list from OpenRouter."""
    import requests
    ALLOWED_PROVIDERS = ("anthropic/", "google/", "openai/", "qwen/", "kimi/")
    try:
        resp = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        resp.raise_for_status()
        models = resp.json().get("data", [])
        filtered = [
            m for m in models
            if any(m["id"].startswith(p) for p in ALLOWED_PROVIDERS)
        ]
        # Sort by provider then name
        filtered.sort(key=lambda m: m["id"])
        return filtered
    except Exception as e:
        print(f"Could not fetch model list: {e}")
        return []

# After user enters API key, show model list:
models = fetch_openrouter_models(api_key)
if models:
    print("\nAvailable models:")
    for i, m in enumerate(models[:30], 1):  # cap at 30
        print(f"  [{i:2d}] {m['id']}")
    print(f"\n  Enter number (1-{min(len(models),30)}) or type a model ID directly:")
    choice = input("> ").strip()
    if choice.isdigit():
        selected_model = models[int(choice)-1]["id"]
    else:
        selected_model = choice
else:
    # Fallback: manual entry
    selected_model = input("Enter model ID (e.g. google/gemini-flash-2.0): ").strip()
    if not selected_model:
        selected_model = "google/gemini-flash-2.0"
```

Replace the current static default model suggestion with this dynamic fetch.

**Input/Output Contract:**
Depends on: TASK_W9-T1 (tcr-config SKILL.md exists with Setup Mode structure)
Produces: tcr-config SKILL.md with live model list fetch from OpenRouter API

**Verify:**
```bash
grep -c "openrouter.ai/api/v1/models" skills/tcr-config/SKILL.md
```
Must return >= 1.

**Done when:**
`skills/tcr-config/SKILL.md` fetches the live model list from OpenRouter when the user picks Cloud LLM, filters to the 5 allowed provider prefixes, shows numbered list, and falls back to manual entry if the API call fails.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W11-T2.md`. Read `skills/tcr-config/SKILL.md`. Find the Toggle 1 (LLM Provider) section where the user picks OpenRouter. After the API key prompt, add the `fetch_openrouter_models()` function and the numbered selection UI. Replace the static default model entry with this dynamic fetch. Run verify. Write Execution Log, rename to `DONE_TASK_W11-T2.md`, commit: `feat: TASK_W11-T2 — live OpenRouter model list in tcr-config (filtered to 5 providers)`.

---

## Execution Log

### Attempt 1
- Date: 2026-05-23
- Result: Added fetch_openrouter_models() with 5-provider filter (anthropic/google/openai/qwen/kimi). Numbered selection UI replaces static model default. Falls back to manual entry if API call fails. Verify PASS.
- Files Changed: skills/tcr-config/SKILL.md
- Issues: none
- Status: DONE
