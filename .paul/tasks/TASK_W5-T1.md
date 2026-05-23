**Task:** TASK_W5-T1 — Add entity and relation table creation to onboard
**Status:** TODO

**File:** skills/code-onboard/SKILL.md, scripts/setup_db.sql
**Branch:** task/W5-T1-entity-relation-tables
**Worker type:** Claude Code

**What changes:**
Extends tcr_create_table.py in onboard Step 3 to create two additional tables: `{project}_entities` and `{project}_relations`. Also updates setup_db.sql with template comments for the new tables.

**Pattern:**

Add to tcr_create_table.py after the existing CREATE TABLE block:

```sql
CREATE TABLE IF NOT EXISTS {PROJECT_NAME}_entities (
    id SERIAL PRIMARY KEY,
    type VARCHAR(20) NOT NULL CHECK (type IN ('file','class','function','method','import')),
    name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    line_start INT NOT NULL,
    line_end INT NOT NULL,
    parent_id INT REFERENCES {PROJECT_NAME}_entities(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS {PROJECT_NAME}_entities_file_idx ON {PROJECT_NAME}_entities (file_path);
CREATE INDEX IF NOT EXISTS {PROJECT_NAME}_entities_type_idx ON {PROJECT_NAME}_entities (type);
CREATE INDEX IF NOT EXISTS {PROJECT_NAME}_entities_name_idx ON {PROJECT_NAME}_entities (name);

CREATE TABLE IF NOT EXISTS {PROJECT_NAME}_relations (
    id SERIAL PRIMARY KEY,
    from_id INT NOT NULL REFERENCES {PROJECT_NAME}_entities(id) ON DELETE CASCADE,
    to_id INT NOT NULL REFERENCES {PROJECT_NAME}_entities(id) ON DELETE CASCADE,
    type VARCHAR(20) NOT NULL CHECK (type IN ('calls','imports','extends','references','contains'))
);
CREATE INDEX IF NOT EXISTS {PROJECT_NAME}_relations_from_idx ON {PROJECT_NAME}_relations (from_id);
CREATE INDEX IF NOT EXISTS {PROJECT_NAME}_relations_to_idx ON {PROJECT_NAME}_relations (to_id);
CREATE INDEX IF NOT EXISTS {PROJECT_NAME}_relations_type_idx ON {PROJECT_NAME}_relations (type);
```

Also add the same as comment template in `scripts/setup_db.sql` (matching existing comment block style).

**Verify:**
`grep -c "entities" skills/code-onboard/SKILL.md` — should be >0.
`grep -c "entities" scripts/setup_db.sql` — should be >0.

**Done when:**
tcr_create_table.py creates _entities and _relations tables with all columns, constraints, and indexes. setup_db.sql has matching template comments.

**Ben noob section:**
Zwei neue Tabellen: eine für Code-Elemente (Funktionen, Klassen, Imports) und eine für Beziehungen dazwischen (wer ruft wen auf, wer importiert was).

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W5-T1.md`. Read `skills/code-onboard/SKILL.md` to find Step 3 (tcr_create_table.py). Add the entity and relation table DDL from the Pattern. Then read `scripts/setup_db.sql` and add the same as comment templates. Verify, write Execution Log, rename task, commit.
