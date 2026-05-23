**Task:** TASK_W12-T1 — Add EMBEDDING_PROVIDER toggle in tcr-config + config.json
**Status:** TODO

**File:** skills/tcr-config/SKILL.md
**Branch:** task/W12-T1-embedding-provider-toggle
**Worker type:** Claude Code

**What changes:**
Updates the tcr-config wizard to explicitly handle the Embedding Provider toggle. Currently Toggle 2 exists as a placeholder; this task makes it fully functional — asks Ollama vs OpenRouter, if OpenRouter asks for embedding model name, writes `embedding_provider` and `embedding_model` to config.json.

**Ben noob section:**
Bisher ist der Embedding-Toggle in der Config-Wizard schon sichtbar aber macht nichts. Jetzt wird er wirklich funktional — der User kann zwischen lokalem Ollama und OpenRouter Embeddings wählen. Die Wahl wird in config.json gespeichert.

**Pattern:**

In `skills/tcr-config/SKILL.md`, update the Toggle 2 section to be fully functional:

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
```

Ensure `embedding_provider` and `embedding_model` are included in the written config.json.

Also update the Change Mode (Step 3) to allow changing Embedding Provider individually.

**Input/Output Contract:**
Depends on: TASK_W9-T1 (tcr-config SKILL.md exists), TASK_W11-T2 (Toggle 1 model list done)
Produces: tcr-config Toggle 2 is fully functional, writes embedding_provider to config.json

**Verify:**
```bash
grep -c "embedding_provider" skills/tcr-config/SKILL.md
```
Must return >= 2 (once for write, once for display in change mode).

**Done when:**
Toggle 2 in tcr-config wizard asks Ollama vs OpenRouter, handles OpenRouter embedding model name, writes `embedding_provider` key to config.json. Change mode also handles updating embedding provider.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W12-T1.md`. Read `skills/tcr-config/SKILL.md`. Find Toggle 2 (Embedding Provider). Replace the current placeholder with the fully functional code that asks the user, handles both paths, and writes `embedding_provider` and `embedding_model` to the config. Also update the change mode section to allow changing embedding provider. Run verify. Write Execution Log, rename to `DONE_TASK_W12-T1.md`, commit: `feat: TASK_W12-T1 — functional embedding provider toggle in tcr-config`.
