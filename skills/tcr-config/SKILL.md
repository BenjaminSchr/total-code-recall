---
name: tcr-config
description: Configure total-code-recall providers — LLM, Embedding, Database. Run once to set up, run again to change.
---

# /tcr-config — Configuration Wizard

You are executing the **tcr-config** skill. Follow these steps in order.

---

## Step 1 — Check existing config

```python
import json, os

CONFIG_PATH = os.path.expanduser("~/.config/total-code-recall/config.json")

if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    mode = "change"  # config exists — offer to change individual values
else:
    cfg = {}
    mode = "setup"   # no config — run fresh wizard
```

---

## Step 2 — Setup mode (first run)

If `mode == "setup"`, ask these 3 questions in order. Wait for user input after each.

**Toggle 1 — LLM Provider:**

```
LLM Provider for generating summaries:
  [1] Local — Ollama (free, slow, works offline)
  [2] Cloud — OpenRouter (fast, costs ~$0.001/summary, needs API key)

Enter 1 or 2:
```

- If `[1]` Local:
  - Ask: `Ollama URL [default: http://localhost:11434]:`
  - Ask: `Ollama summary model [default: devstral:24b]:`
  - Set: `cfg["llm_provider"] = "ollama"`, `cfg["ollama_url"] = <url>`, `cfg["ollama_summary_model"] = <model>`

- If `[2]` Cloud:
  - Ask: `OpenRouter API key (sk-or-...):`
  - After key is entered, fetch the live model list and show numbered selection:

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
        filtered.sort(key=lambda m: m["id"])
        return filtered
    except Exception as e:
        print(f"Could not fetch model list: {e}")
        return []

# Show numbered model list
models = fetch_openrouter_models(api_key)
if models:
    print("\nAvailable models:")
    for i, m in enumerate(models[:30], 1):  # cap at 30
        print(f"  [{i:2d}] {m['id']}")
    print(f"\n  Enter number (1-{min(len(models),30)}) or type a model ID directly:")
    choice = input("> ").strip()
    if choice.isdigit() and 1 <= int(choice) <= min(len(models), 30):
        selected_model = models[int(choice)-1]["id"]
    else:
        selected_model = choice if choice else "google/gemini-flash-2.0"
else:
    # Fallback: manual entry
    selected_model = input("Enter model ID (e.g. google/gemini-flash-2.0): ").strip()
    if not selected_model:
        selected_model = "google/gemini-flash-2.0"
```

  - Set: `cfg["llm_provider"] = "openrouter"`, `cfg["openrouter_api_key"] = <key>`, `cfg["openrouter_model"] = selected_model`

---

**Toggle 2 — Embedding Provider:**

```
Embedding Provider:
  [1] Local — Ollama nomic-embed-text (recommended, fast, free)
  [2] Cloud — OpenRouter (requires API key)

Enter 1 or 2:
```

- If `[1]` Local:
  - Ask: `Embedding model [default: nomic-embed-text]:`
  - Set: `cfg["embedding_provider"] = "ollama"`, `cfg["embedding_model"] = <model>`

- If `[2]` Cloud:
  - Ask: `OpenRouter embedding model [default: text-embedding-3-small]:`
  - Set: `cfg["embedding_provider"] = "openrouter"`, `cfg["embedding_model"] = <model>`
  - Note: uses same `openrouter_api_key` set in Toggle 1. If LLM was set to Local, ask for the API key now.

---

**Toggle 3 — Database:**

```
Database:
  [1] Local — pgvector (Docker, full control)
  [2] Cloud — Supabase (no Docker needed, needs connection string)

Enter 1 or 2:
```

- If `[1]` Local:
  - Ask: `DATABASE_URL [default: postgresql://code_index_user:code_index_pass@localhost:5434/code_index_db]:`
  - Set: `cfg["db_provider"] = "local"`, `cfg["database_url"] = <url>`

- If `[2]` Cloud:
  - Ask: `Supabase connection string (pooler URL with SSL):`
  - Set: `cfg["db_provider"] = "supabase"`, `cfg["database_url"] = <url>`

---

## Step 3 — Change mode (config already exists)

If `mode == "change"`, display current config:

```
Current config:
  LLM Provider:       <llm_provider> (<ollama_summary_model or openrouter_model>)
  Embedding Provider: <embedding_provider> (<embedding_model>)
  Database:           <db_provider> (<database_url truncated to 50 chars>)

What would you like to change?
  [1] LLM Provider
  [2] Embedding Provider
  [3] Database
  [4] Nothing — exit
  [5] Reset (wipe config, start fresh)
```

- For `[1]`, `[2]`, `[3]`: run the corresponding Toggle from Step 2, then jump to Step 4.
- For `[4]`: print `"Config unchanged."` and stop.
- For `[5]`: delete config file, print `"Config reset. Run /tcr-config again to set up."`, and stop.

```python
# Reset:
os.remove(CONFIG_PATH)
```

---

## Step 4 — Write config

```python
os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
with open(CONFIG_PATH, "w") as f:
    json.dump(cfg, f, indent=2)
print(f"Config saved to {CONFIG_PATH}")
```

Config JSON format:
```json
{
  "llm_provider": "openrouter",
  "openrouter_api_key": "sk-or-...",
  "openrouter_model": "google/gemini-flash-2.0",
  "ollama_url": "http://localhost:11434",
  "ollama_summary_model": "devstral:24b",
  "embedding_provider": "ollama",
  "embedding_model": "nomic-embed-text",
  "db_provider": "local",
  "database_url": "postgresql://code_index_user:code_index_pass@localhost:5434/code_index_db",
  "chunk_size": 50,
  "chunk_overlap": 15,
  "parallel_workers": 10
}
```

Only the keys relevant to the chosen providers are written. Keys for unused providers are omitted.

---

## Step 5 — Confirm

Print a summary of the saved configuration and next steps:

```
Configuration saved to ~/.config/total-code-recall/config.json

Summary:
  LLM:        <provider> — <model>
  Embeddings: <provider> — <model>
  Database:   <provider>

Next step: Run /tcr-onboard <path-to-project> to index your first project.
```

---

## Notes

- Config is stored globally at `~/.config/total-code-recall/config.json` — shared across all projects.
- The config is read by `/tcr-onboard`, `/tcr-update`, `/tcr-search`, `/tcr-explain`, and `/tcr-info` at runtime.
- `chunk_size` and `chunk_overlap` are not asked during setup — they use hardcoded defaults. Advanced users can edit config.json directly.
- If `embedding_provider` is changed after indexing, the existing vector index is incompatible. You must drop the project table and re-run `/tcr-onboard`.
