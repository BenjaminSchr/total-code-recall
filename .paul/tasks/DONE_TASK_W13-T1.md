**Task:** TASK_W13-T1 — Add DB_PROVIDER toggle in tcr-config + config.json, Supabase connection handling
**Status:** DONE

**File:** skills/tcr-config/SKILL.md
**Branch:** task/W13-T1-supabase-config-toggle
**Worker type:** Claude Code

**What changes:**
Makes Toggle 3 (Database) in tcr-config fully functional. Handles Supabase connection string specifics: SSL required, pooler URL format, optional API key auth. Writes `db_provider` and `database_url` to config.json.

**Ben noob section:**
Supabase ist eine Cloud-Datenbank. Statt einem lokalen Docker-Container kann man einfach eine Supabase-URL eingeben und total-code-recall nutzt das. Für Leute die kein Docker wollen.

**Pattern:**

In `skills/tcr-config/SKILL.md`, replace the Toggle 3 placeholder with fully functional code:

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
    cfg["db_provider"] = "supabase"
    print("""
Supabase connection string (use the pooler URL for session mode):
Format: postgresql://[user].[project-ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres

Find it in: Supabase dashboard → Settings → Database → Connection string → Session mode
""")
    db_url = input("Supabase connection string: ").strip()
    if not db_url:
        print("ERROR: Connection string required for Supabase.")
    else:
        # Ensure SSL is appended if missing
        if "sslmode=" not in db_url:
            db_url = db_url + "?sslmode=require"
        cfg["database_url"] = db_url
        print(f"Supabase URL saved (SSL enforced).")
else:
    cfg["db_provider"] = "local"
    default_url = "postgresql://code_index_user:code_index_pass@localhost:5434/code_index_db"
    print(f"Local pgvector default: {default_url}")
    custom = input("Press Enter to use default, or type custom URL: ").strip()
    cfg["database_url"] = custom or default_url
```

Also update the Change Mode section to allow changing DB provider.

**Input/Output Contract:**
Depends on: TASK_W9-T1 (tcr-config SKILL.md exists), TASK_W12-T1 (Toggle 2 done, pattern established)
Produces: tcr-config Toggle 3 fully functional, writes `db_provider` and `database_url` (with SSL) to config.json

**Verify:**
```bash
grep -c "db_provider" skills/tcr-config/SKILL.md && grep -c "sslmode=require" skills/tcr-config/SKILL.md
```
Both must return >= 1.

**Done when:**
Toggle 3 in tcr-config asks Local vs Supabase, handles Supabase pooler URL with SSL enforcement, writes `db_provider` key to config.json. Local path uses default pgvector URL with custom override option.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W13-T1.md`. Read `skills/tcr-config/SKILL.md`. Find Toggle 3 (Database). Replace the current placeholder with the fully functional code. Ensure the Supabase path appends `?sslmode=require` if not already present. Update the change mode section to allow changing DB provider. Run verify. Write Execution Log, rename to `DONE_TASK_W13-T1.md`, commit: `feat: TASK_W13-T1 — functional DB provider toggle in tcr-config with Supabase SSL handling`.

---

## Execution Log

### Attempt 1
- Date: 2026-05-23
- Result: Replaced Toggle 3 placeholder with functional Python code. Supabase path: prompts for pooler URL, enforces `?sslmode=require` if missing, errors on empty input. Local path: shows default URL, allows custom override. Added Handle [3] Database change block in Change Mode section (matching Toggle 2 pattern).
- Files Changed: skills/tcr-config/SKILL.md
- Issues: none
- Status: DONE
