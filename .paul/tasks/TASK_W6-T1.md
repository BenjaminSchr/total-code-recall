**Task:** TASK_W6-T1 — Add summaries table creation to onboard
**Status:** TODO

**File:** skills/code-onboard/SKILL.md, scripts/setup_db.sql
**Branch:** task/W6-T1-summaries-table
**Worker type:** Claude Code

**What changes:**
Extends tcr_create_table.py in onboard Step 3 to create the `{project}_summaries` table. Also adds template comment to setup_db.sql.

**Pattern:**

Add to tcr_create_table.py:
```sql
CREATE TABLE IF NOT EXISTS {PROJECT_NAME}_summaries (
    id SERIAL PRIMARY KEY,
    level VARCHAR(10) NOT NULL CHECK (level IN ('file','module','repo')),
    scope TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),
    indexed_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS {PROJECT_NAME}_summaries_level_idx ON {PROJECT_NAME}_summaries (level);
CREATE INDEX IF NOT EXISTS {PROJECT_NAME}_summaries_embedding_idx ON {PROJECT_NAME}_summaries USING hnsw (embedding vector_cosine_ops);
```

Also: add `DELETE FROM {PROJECT_NAME}_summaries` alongside existing `DELETE FROM {PROJECT_NAME}` in the onboard re-run cleanup (tcr_index.py, added in W2.6-T4).

**Input/Output Contract:**
Depends on: W5-T1 (entity tables pattern already established)

**Verify:**
`grep -c "summaries" skills/code-onboard/SKILL.md` — should be >0.

**Done when:**
tcr_create_table.py creates _summaries table with level, scope, content, embedding columns + HNSW index. Onboard re-run cleanup also clears summaries. setup_db.sql has template comment.

**Ben noob section:**
Eine neue Tabelle für hierarchische Zusammenfassungen — auf Datei-, Modul- und Repo-Ebene. Wird von den nächsten Tasks befüllt.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W6-T1.md`. Read `skills/code-onboard/SKILL.md` Step 3 (tcr_create_table.py) and find the existing entity/relation CREATE TABLEs. Add the summaries table after them. Also find the DELETE cleanup (W2.6-T4 fix) and add summaries cleanup there. Update setup_db.sql template comments. Verify, write Execution Log, rename task, commit.
