**Task:** TASK_W1-T2 — Create .env.example and .gitignore
**Status:** TODO

**File:** .env.example, .gitignore
**Branch:** task/W1-T2-env-gitignore
**Worker type:** Claude Code

**What changes:**
Creates configuration template (.env.example) with all required environment variables and .gitignore to exclude venv, cache, .env, and IDE files.

**Pattern:**

`.env.example`:
```
# Database — pgvector-enabled PostgreSQL
DATABASE_URL=postgresql://code_index_user:code_index_pass@localhost:5433/code_index_db

# Ollama — local LLM server
OLLAMA_URL=http://localhost:11434

# Models — configurable
EMBEDDING_MODEL=nomic-embed-text
SUMMARY_MODEL=devstral:24b

# Chunking
CHUNK_SIZE=50
CHUNK_OVERLAP=15
```

`.gitignore`:
```
.env
__pycache__/
*.pyc
venv/
.venv/
node_modules/
.idea/
.vscode/
*.egg-info/
dist/
build/
```

**Input/Output Contract:**
None — standalone config files.

**Verify:**
`test -f .env.example && test -f .gitignore && echo "OK"` returns "OK".

**Done when:**
Both files exist at project root. .env.example has DATABASE_URL, OLLAMA_URL, EMBEDDING_MODEL, SUMMARY_MODEL, CHUNK_SIZE, CHUNK_OVERLAP. .gitignore excludes .env and common dev artifacts.

**Ben noob section:**
.env.example zeigt dem User welche Einstellungen er braucht. .gitignore verhindert dass sensible Daten oder Müll ins Repo kommen.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read the task file `.paul/tasks/TASK_W1-T2.md`. The Pattern section contains the exact content. Create both files, verify, write Execution Log, commit.
