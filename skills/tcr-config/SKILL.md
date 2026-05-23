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

```python
# Toggle 2 — Embedding Provider
print("""
Embedding Provider:
  [1] Local — Ollama nomic-embed-text (recommended, fast, free)
  [2] Cloud — OpenRouter embeddings (costs per token, needs API key)

Enter 1 or 2 [default: 1]:
""")
emb_choice = input("> ").strip() or "1"

if emb_choice == "2":
    # OpenRouter embedding
    cfg["embedding_provider"] = "openrouter"
    # Reuse openrouter_api_key if already set in this session
    if not cfg.get("openrouter_api_key"):
        cfg["openrouter_api_key"] = input("OpenRouter API key (sk-or-...): ").strip()
    print("OpenRouter embedding models:")
    print("  ⚠️  IMPORTANT: The default schema uses vector(768).")
    print("     Only 768-dimensional models are compatible:")
    print("  [1] google/text-embedding-004       (768 dims) ← RECOMMENDED")
    print("  [2] openai/text-embedding-3-small   (1536 dims) — requires schema change")
    print("  [3] openai/text-embedding-3-large   (3072 dims) — requires schema change")
    emb_model = input("Enter model ID [default: google/text-embedding-004]: ").strip()
    cfg["embedding_model"] = emb_model or "google/text-embedding-004"
else:
    # Local Ollama embedding
    cfg["embedding_provider"] = "ollama"
    cfg["embedding_model"] = "nomic-embed-text"
    print("Using local Ollama embedding: nomic-embed-text")
```

---

**Toggle 3 — Database:**

```python
# Toggle 3 — Database
print("""
Database:
  [1] Local — pgvector via Docker (full control, needs Docker)
  [2] Cloud — Supabase (no Docker, needs connection string)

Enter 1 or 2 [default: 1]:
""")
db_choice = input("> ").strip() or "1"

if db_choice == "2":
    print("""
Supabase connection string (use the pooler URL for session mode):
Format: postgresql://[user].[project-ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres

Find it in: Supabase dashboard → Settings → Database → Connection string → Session mode
""")
    db_url = input("Supabase connection string: ").strip()
    if not db_url:
        print("ERROR: Connection string required for Supabase. Config not saved for database.")
    else:
        # Ensure SSL is appended if missing — use & if URL already has query params
        if "sslmode=" not in db_url:
            sep = "&" if "?" in db_url else "?"
            db_url = db_url + sep + "sslmode=require"
        cfg["db_provider"] = "supabase"
        cfg["database_url"] = db_url
        print("Supabase URL saved (SSL enforced).")
else:
    cfg["db_provider"] = "local"
    default_url = "postgresql://code_index_user:code_index_pass@localhost:5434/code_index_db"
    print(f"Local pgvector default: {default_url}")
    custom = input("Press Enter to use default, or type custom URL: ").strip()
    cfg["database_url"] = custom or default_url
```

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

- For `[1]`: run the Toggle 1 logic from Step 2, then jump to Step 4.
- For `[2]`: run the Toggle 2 (Embedding Provider) logic below, then jump to Step 4.
- For `[3]`: run the Toggle 3 logic from Step 2, then jump to Step 4.
- For `[4]`: print `"Config unchanged."` and stop.
- For `[5]`: delete config file, print `"Config reset. Run /tcr-config again to set up."`, and stop.

```python
# Handle [2] — Embedding Provider change
if change_choice == "2":
    print("""
Embedding Provider:
  [1] Local — Ollama nomic-embed-text (recommended, fast, free)
  [2] Cloud — OpenRouter embeddings (costs per token, needs API key)

Enter 1 or 2 [default: 1]:
""")
    emb_choice = input("> ").strip() or "1"

    if emb_choice == "2":
        # OpenRouter embedding
        cfg["embedding_provider"] = "openrouter"
        # Reuse openrouter_api_key if already set in config
        if not cfg.get("openrouter_api_key"):
            cfg["openrouter_api_key"] = input("OpenRouter API key (sk-or-...): ").strip()
        print("OpenRouter embedding models (common choices):")
        print("  openai/text-embedding-3-small")
        print("  openai/text-embedding-3-large")
        print("  google/text-embedding-004")
        emb_model = input("Enter model ID [default: openai/text-embedding-3-small]: ").strip()
        cfg["embedding_model"] = emb_model or "openai/text-embedding-3-small"
    else:
        # Local Ollama embedding
        cfg["embedding_provider"] = "ollama"
        cfg["embedding_model"] = "nomic-embed-text"
        print("Using local Ollama embedding: nomic-embed-text")

# Handle [3] — Database change
if change_choice == "3":
    print("""
Database:
  [1] Local — pgvector via Docker (full control, needs Docker)
  [2] Cloud — Supabase (no Docker, needs connection string)

Enter 1 or 2 [default: 1]:
""")
    db_change_choice = input("> ").strip() or "1"

    if db_change_choice == "2":
        print("""
Supabase connection string (use the pooler URL for session mode):
Format: postgresql://[user].[project-ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres

Find it in: Supabase dashboard → Settings → Database → Connection string → Session mode
""")
        db_url = input("Supabase connection string: ").strip()
        if not db_url:
            print("ERROR: Connection string required for Supabase. Config not saved for database.")
        else:
            if "sslmode=" not in db_url:
                sep = "&" if "?" in db_url else "?"
                db_url = db_url + sep + "sslmode=require"
            cfg["db_provider"] = "supabase"
            cfg["database_url"] = db_url
            print("Supabase URL saved (SSL enforced).")
    else:
        cfg["db_provider"] = "local"
        default_url = "postgresql://code_index_user:code_index_pass@localhost:5434/code_index_db"
        print(f"Local pgvector default: {default_url}")
        custom = input("Press Enter to use default, or type custom URL: ").strip()
        cfg["database_url"] = custom or default_url

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
