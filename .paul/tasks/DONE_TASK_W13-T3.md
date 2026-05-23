**Task:** TASK_W13-T3 — Update README.md + tcr-info for Supabase setup and zero-infra use case
**Status:** DONE

**File:** README.md, skills/tcr-info/SKILL.md
**Branch:** task/W13-T3-supabase-docs
**Worker type:** Claude Code

**What changes:**
Adds a "Cloud Setup" section to README.md describing the zero-infra path (OpenRouter + Supabase + no local Docker). Updates tcr-info to show the db_provider in the config display.

**Ben noob section:**
Dokumentation für den "ich will gar nichts lokal installieren" Use Case: OpenRouter für LLM, Supabase für die Datenbank, Ollama optional. README bekommt eine neue Sektion, tcr-info zeigt den DB Provider an.

**Pattern:**

**README.md** — add new section after the existing "Quick Start" section:

```markdown
## Cloud Setup (Zero Local Infrastructure)

Run total-code-recall entirely in the cloud — no Docker, no Ollama required.

**Requirements:**
- OpenRouter account + API key (https://openrouter.ai)
- Supabase project + connection string (https://supabase.com, free tier works)
- Claude Code with this plugin installed

**Setup:**
1. Run `/tcr-config`
2. LLM Provider → Cloud (OpenRouter) → paste API key → pick model
3. Embedding Provider → Cloud (OpenRouter) → pick embedding model
4. Database → Cloud (Supabase) → paste pooler connection string

**Onboard time:** ~2-5 minutes for a 10k line project (parallel OpenRouter calls).

**Cost estimate:** ~$0.001 per summary, ~$0.0001 per embedding. 500-chunk project ≈ $0.05.
```

**skills/tcr-info/SKILL.md** — update Step 2 (Show config) to include db_provider:

```
Config: ~/.config/total-code-recall/config.json

  LLM Provider:       openrouter (google/gemini-flash-2.0)
  Embedding Provider: ollama (nomic-embed-text)
  DB Provider:        supabase (postgresql://...@pooler.supabase.com/postgres)
  Parallel Workers:   10
```

Update the embedded display code to read `cfg.get("db_provider", "local")` and `cfg.get("database_url", "not set")[:50] + "..."` (truncate for display).

**Input/Output Contract:**
Depends on: TASK_W13-T1 (db_provider key defined), TASK_W9-T2 (tcr-info SKILL.md exists)
Produces: README.md has Cloud Setup section; tcr-info shows db_provider in config display

**Verify:**
```bash
grep -c "Zero Local Infrastructure" README.md && grep -c "db_provider" skills/tcr-info/SKILL.md
```
Both must return >= 1.

**Done when:**
README.md has the "Cloud Setup" section with Supabase instructions and cost estimate. `skills/tcr-info/SKILL.md` shows `DB Provider` in the config display output.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W13-T3.md`. Read `README.md` and `skills/tcr-info/SKILL.md`. Add the "Cloud Setup (Zero Local Infrastructure)" section to README.md after Quick Start. Update the config display in tcr-info to include DB Provider and truncated database_url. Run verify. Write Execution Log, rename to `DONE_TASK_W13-T3.md`, commit: `feat: TASK_W13-T3 — add Supabase cloud setup docs to README and tcr-info`.

---

## Execution Log

### Attempt 1
- Date: 2026-05-23
- Result: Added "Option C — Cloud Setup (Zero Local Infrastructure)" section to README.md after Option B (before Usage). Section includes requirements (OpenRouter + Supabase), step-by-step setup via /tcr-config, Supabase dashboard navigation tip, onboard time estimate, and cost estimate. Updated tcr-info Step 2 display template to show DB Provider with truncated database_url on same line, removed separate Database URL line, added Python display helper snippet for cfg.get("db_provider") and URL truncation.
- Files Changed: README.md, skills/tcr-info/SKILL.md
- Issues: db_provider was already in tcr-info display template (1 occurrence); added code example for explicit truncation
- Status: DONE
