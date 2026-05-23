**Task:** TASK_W1-T3 — Create setup_db.sql
**Status:** TODO

**File:** scripts/setup_db.sql
**Branch:** task/W1-T3-setup-db-sql
**Worker type:** Claude Code

**What changes:**
Creates the SQL setup script that enables pgvector extension, creates the _index_meta table, and provides a template comment for project tables.

**Pattern:**
```sql
-- total-code-recall: Database Setup
-- Run this once against your pgvector-enabled PostgreSQL:
--   psql -U code_index_user -d code_index_db -f scripts/setup_db.sql

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Meta table: tracks indexing state per project
CREATE TABLE IF NOT EXISTS _index_meta (
    project VARCHAR(100) PRIMARY KEY,
    last_commit_hash VARCHAR(40),
    last_indexed_at TIMESTAMP DEFAULT NOW(),
    chunk_count INT DEFAULT 0,
    embedding_model VARCHAR(100)
);

-- Project tables are created dynamically by /code-onboard.
-- Template for reference:
--
-- CREATE TABLE {project_name} (
--     id SERIAL PRIMARY KEY,
--     chunk_id INT NOT NULL,
--     type VARCHAR(10) NOT NULL CHECK (type IN ('summary', 'code')),
--     file_path TEXT NOT NULL,
--     line_start INT NOT NULL,
--     line_end INT NOT NULL,
--     content TEXT NOT NULL,
--     commit_hash VARCHAR(40) NOT NULL,
--     commit_message TEXT,
--     embedding_model VARCHAR(100) NOT NULL,
--     embedding vector(768),
--     indexed_at TIMESTAMP DEFAULT NOW()
-- );
--
-- CREATE INDEX ON {project_name} USING hnsw (embedding vector_cosine_ops);
-- CREATE INDEX ON {project_name} (chunk_id);
-- CREATE INDEX ON {project_name} (file_path);
```

**Input/Output Contract:**
None — standalone setup script.

**Verify:**
`cat scripts/setup_db.sql | grep "CREATE EXTENSION" && echo "OK"` returns the CREATE EXTENSION line + "OK".

**Done when:**
scripts/setup_db.sql exists with CREATE EXTENSION vector, CREATE TABLE _index_meta with all columns, and project table template as comment.

**Ben noob section:**
Dieses SQL-Script richtet die Datenbank ein — einmal ausführen und die DB ist bereit.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read the task file `.paul/tasks/TASK_W1-T3.md`. The Pattern section contains the exact SQL. Create the file, verify, write Execution Log, commit.
