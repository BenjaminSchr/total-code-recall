**Task:** TASK_W13-T2 — Update tcr-onboard + tcr-update for Supabase-compatible SQL
**Status:** TODO

**File:** skills/tcr-onboard/SKILL.md, skills/tcr-update/SKILL.md
**Branch:** task/W13-T2-supabase-sql-compat
**Worker type:** Claude Code

**What changes:**
Audits the SQL in tcr-onboard and tcr-update for Supabase pgvector compatibility. Adds the `DB_PROVIDER` config variable and any needed SQL adjustments (e.g. `CREATE EXTENSION IF NOT EXISTS vector` — Supabase already has it but the call is idempotent; schema checks using `information_schema` are compatible; `COPY` bulk insert should use `INSERT` batches for Supabase pooler connections).

**Ben noob section:**
Supabase ist fast identisch zu normalen PostgreSQL, aber ein paar Dinge unterscheiden sich (z.B. kein direktes COPY über die Pooler-Verbindung). Dieser Task prüft die SQL-Statements und passt sie an wo nötig.

**Pattern:**

Add `DB_PROVIDER` to config section (after W10-T1 loader):
```python
DB_PROVIDER = _cfg("DB_PROVIDER", "db_provider", "local")
```

Audit these SQL patterns for Supabase compatibility:

1. **COPY bulk insert** — if used, Supabase pooler connections don't support COPY. Replace with batched INSERTs:
```python
# BEFORE (local pgvector):
# COPY table FROM STDIN ...

# AFTER (compatible with both):
BATCH_SIZE = 100
for i in range(0, len(rows), BATCH_SIZE):
    batch = rows[i:i+BATCH_SIZE]
    args = [(r["col1"], r["col2"]) for r in batch]
    cur.executemany("INSERT INTO table (col1, col2) VALUES (%s, %s) ON CONFLICT DO NOTHING", args)
```

2. **CREATE EXTENSION** — already idempotent, no change needed.

3. **Vector distance syntax** — `<=>` operator is supported in Supabase pgvector, no change needed.

4. **Connection** — Supabase pooler is Session mode, psycopg2 `ThreadedConnectionPool` works fine.

5. **SSL** — the URL from config.json already has `sslmode=require` appended by tcr-config. psycopg2 picks it up from the DSN. No code change needed.

If no COPY statements exist in the SKILL.md scripts → document "no COPY found, SQL is Supabase-compatible" in Execution Log and mark DONE.

**Input/Output Contract:**
Depends on: TASK_W13-T1 (DB_PROVIDER config key defined), TASK_W10-T1 (config loader in both files)
Produces: tcr-onboard and tcr-update SKILL.md SQL is verified Supabase-compatible; COPY replaced with batched INSERT if found

**Verify:**
```bash
grep -n "COPY" skills/tcr-onboard/SKILL.md skills/tcr-update/SKILL.md && echo "COPY FOUND — check if replaced" || echo "No COPY statements — Supabase compatible"
grep -c "DB_PROVIDER" skills/tcr-onboard/SKILL.md
```
Second command must return >= 1.

**Done when:**
`DB_PROVIDER` variable exists in both SKILL.md config sections. No raw `COPY` statements remain in the embedded Python scripts. SQL is verified compatible with Supabase pooler connections.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W13-T2.md`. Read `skills/tcr-onboard/SKILL.md` and `skills/tcr-update/SKILL.md`. Add `DB_PROVIDER` to the config section of each. Search for any `COPY` statements in the embedded Python scripts. If found, replace with batched `executemany` INSERTs. Document findings in Execution Log. Run verify. Rename to `DONE_TASK_W13-T2.md`, commit: `feat: TASK_W13-T2 — audit and fix SQL for Supabase pooler compatibility in tcr-onboard + tcr-update`.
