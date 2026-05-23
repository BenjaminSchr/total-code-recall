**Task:** TASK_W9-T1 — Create skills/tcr-config/SKILL.md — setup wizard + config change + reset
**Status:** TODO

**File:** skills/tcr-config/SKILL.md
**Branch:** task/W9-T1-create-tcr-config-skill
**Worker type:** Claude Code

**What changes:**
Creates the `/tcr-config` skill that guides the user through a 3-toggle setup wizard (LLM / Embedding / DB provider), handles config-change mode when a config already exists, and supports reset mode. Reads and writes `~/.config/total-code-recall/config.json`.

**Ben noob section:**
Einmalige Konfiguration: Der User wird durch 3 Fragen geführt — "Welchen LLM willst du? Welche Embeddings? Welche Datenbank?" Die Antworten werden global gespeichert. Beim nächsten Aufruf sieht er die aktuelle Config und kann sie ändern.

**Pattern:**

```markdown
---
name: tcr-config
description: Configure total-code-recall providers — LLM, Embedding, Database. Run once to set up, run again to change.
---

# /tcr-config — Configuration Wizard

You are executing the **tcr-config** skill. Follow these steps.

---

## Step 1 — Check existing config

```python
import json, os

CONFIG_PATH = os.path.expanduser("~/.config/total-code-recall/config.json")

if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    # Show current config
    mode = "change"  # offer to change individual values
else:
    cfg = {}
    mode = "setup"   # fresh wizard
```

---

## Step 2 — Setup mode (first run)

If mode == "setup", ask these 3 questions in order:

**Toggle 1 — LLM Provider:**
```
LLM Provider for generating summaries:
  [1] Local — Ollama (free, slow, works offline)
  [2] Cloud — OpenRouter (fast, costs ~$0.001/summary, needs API key)

Enter 1 or 2:
```
If Cloud: ask for OpenRouter API key and model (show model list from W11-T2, or default `google/gemini-flash-2.0`).
If Local: ask for Ollama URL (default: `http://localhost:11434`) and model (default: `devstral:24b`).

**Toggle 2 — Embedding Provider:**
```
Embedding Provider:
  [1] Local — Ollama nomic-embed-text (recommended, fast, free)
  [2] Cloud — OpenRouter (requires API key)

Enter 1 or 2:
```
Default: [1] Local.

**Toggle 3 — Database:**
```
Database:
  [1] Local — pgvector (Docker, full control)
  [2] Cloud — Supabase (no Docker needed, needs connection string)

Enter 1 or 2:
```
If Cloud: ask for Supabase connection string (pooler URL with SSL).
If Local: ask for DATABASE_URL (default: `postgresql://code_index_user:code_index_pass@localhost:5434/code_index_db`).

---

## Step 3 — Change mode (config exists)

Show current config:
```
Current config:
  LLM Provider:       openrouter (google/gemini-flash-2.0)
  Embedding Provider: ollama (nomic-embed-text)
  Database:           local (postgresql://...@localhost:5434/...)

What would you like to change?
  [1] LLM Provider
  [2] Embedding Provider
  [3] Database
  [4] Nothing — exit
  [5] Reset (wipe config, start fresh)
```

Handle each selection. For [5] Reset: delete config file, confirm deletion, exit.

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

---

## Step 5 — Confirm

Print summary of saved config. Tell the user to run `/tcr-onboard <project-path>` next.
```

**Input/Output Contract:**
Depends on: TASK_W8-T1 (tcr-* dirs exist, for consistency — tcr-config is a new directory)
Produces: `skills/tcr-config/SKILL.md` (new file, new directory)

**Verify:**
```bash
test -f skills/tcr-config/SKILL.md && grep "name: tcr-config" skills/tcr-config/SKILL.md
```

**Done when:**
`skills/tcr-config/SKILL.md` exists with the 5-step wizard (check config, setup mode, change mode, write config, confirm). Contains the config JSON schema.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W9-T1.md`. Create directory `skills/tcr-config/` and write `skills/tcr-config/SKILL.md` following the pattern exactly. The skill must cover all three modes: setup (first run), change (existing config), and reset. Run verify. Write Execution Log, rename to `DONE_TASK_W9-T1.md`, commit: `feat: TASK_W9-T1 — create tcr-config skill (wizard + change + reset)`.
