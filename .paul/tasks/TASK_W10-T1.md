**Task:** TASK_W10-T1 — Add global config loader to all temp scripts in all SKILL.md files
**Status:** TODO

**File:** skills/tcr-onboard/SKILL.md, skills/tcr-update/SKILL.md, skills/tcr-search/SKILL.md, skills/tcr-overview/SKILL.md, skills/tcr-explain/SKILL.md
**Branch:** task/W10-T1-global-config-loader
**Worker type:** Claude Code

**What changes:**
Adds the three-layer config loader to the config/environment setup section of each SKILL.md's embedded Python script. Lookup order: 1) project `.env` → 2) global `~/.config/total-code-recall/config.json` → 3) system env vars / hardcoded defaults.

**Ben noob section:**
Bisher lesen die Scripts nur `.env` im aktuellen Ordner. Jetzt lesen sie zusätzlich die globale Config (`~/.config/total-code-recall/config.json`). Projekt-spezifische `.env` gewinnt immer über die globale Config.

**Pattern:**

Replace the existing config section at the top of each embedded Python script with this loader. Add it AFTER any existing `dotenv` loading and BEFORE the variable assignments:

```python
import json, os

# --- Config Loader (3-layer) ---
# Layer 1: project .env (already loaded via python-dotenv above)
# Layer 2: global config.json
_GLOBAL_CONFIG = {}
_CONFIG_PATH = os.path.expanduser("~/.config/total-code-recall/config.json")
if os.path.exists(_CONFIG_PATH):
    with open(_CONFIG_PATH) as _f:
        _GLOBAL_CONFIG = json.load(_f)

def _cfg(env_key, config_key, default):
    """Priority: env var > global config > default"""
    return os.environ.get(env_key) or _GLOBAL_CONFIG.get(config_key) or default

# Apply to variables:
DATABASE_URL      = _cfg("DATABASE_URL",   "database_url",         "postgresql://code_index_user:code_index_pass@localhost:5434/code_index_db")
OLLAMA_URL        = _cfg("OLLAMA_URL",     "ollama_url",           "http://localhost:11434")
EMBEDDING_MODEL   = _cfg("EMBEDDING_MODEL","embedding_model",      "nomic-embed-text")
SUMMARY_MODEL     = _cfg("SUMMARY_MODEL",  "ollama_summary_model", "devstral:24b")
CHUNK_SIZE        = int(_cfg("CHUNK_SIZE", "chunk_size",           "50"))
CHUNK_OVERLAP     = int(_cfg("CHUNK_OVERLAP","chunk_overlap",      "15"))
```

Apply this pattern to the config section in:
- `skills/tcr-onboard/SKILL.md` (tcr_index.py and tcr_build_summaries.py embedded scripts)
- `skills/tcr-update/SKILL.md`
- `skills/tcr-search/SKILL.md`
- `skills/tcr-overview/SKILL.md`
- `skills/tcr-explain/SKILL.md`

Do NOT change any SQL, embedding calls, or search logic — only the config loading section.

**Input/Output Contract:**
Depends on: TASK_W8-T1, TASK_W8-T2 (files exist at tcr-* paths with updated names)
Produces: All five SKILL.md files have the 3-layer config loader in their embedded scripts

**Verify:**
```bash
grep -l "_GLOBAL_CONFIG" skills/tcr-onboard/SKILL.md skills/tcr-update/SKILL.md skills/tcr-search/SKILL.md skills/tcr-overview/SKILL.md skills/tcr-explain/SKILL.md | wc -l
```
Must return 5.

**Done when:**
All five SKILL.md files contain `_GLOBAL_CONFIG` in their config section. The loader reads from `~/.config/total-code-recall/config.json` with env var override.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W10-T1.md`. Read each of the five SKILL.md files. In each one, find the config/variable section at the top of the embedded Python script and replace it with the 3-layer config loader pattern. Do not change SQL, embedding, or search logic. Run verify (must return 5). Write Execution Log, rename to `DONE_TASK_W10-T1.md`, commit: `feat: TASK_W10-T1 — add 3-layer config loader to all SKILL.md embedded scripts`.
