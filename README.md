# total-code-recall

Semantic code search for Claude Code. Index once, search instantly — no API keys, no cloud, everything runs locally.

---

## What it does

**The problem:** Every time an agent opens your codebase it reads dozens of files to understand the project. That burns context window and costs tokens.

**The solution:** Run `/code-onboard` once. The plugin splits your code into 50-line chunks, generates summaries with a local LLM (devstral), embeds both the summary and the raw code with a local embedding model (nomic-embed-text), and stores everything in a pgvector database. From then on, `/code-search "date filter"` finds the right file and line range in seconds — without reading a single source file.

Three commands. Zero API keys. All local.

---

## Quick Start

### Prerequisites

- [Ollama](https://ollama.ai) running locally (default: `http://localhost:11434`)
- PostgreSQL with pgvector extension (see Option A or B below)
- Python 3.10+ with `psycopg2-binary` and `requests` available to Claude Code

### Option A — Docker (recommended)

Spin up the pre-configured pgvector container included in this repo:

```bash
# 1. Clone and enter the repo
git clone https://github.com/BenjaminSchr/total-code-recall
cd total-code-recall

# 2. Copy the config
cp .env.example .env

# 3. Start the pgvector container
#    setup_db.sql runs automatically on first start
docker compose up -d

# 4. Pull the required Ollama models
ollama pull nomic-embed-text
ollama pull devstral:24b

# 5. Install the plugin
claude plugin add github:BenjaminSchr/total-code-recall
```

Done. The database is ready at `localhost:5433`.

### Option B — Bring your own pgvector

If you already have a pgvector-enabled PostgreSQL instance:

```bash
# 1. Create the database and user
psql -U postgres -c "CREATE USER code_index_user WITH PASSWORD 'code_index_pass';"
psql -U postgres -c "CREATE DATABASE code_index_db OWNER code_index_user;"

# 2. Run the setup script (requires superuser for CREATE EXTENSION)
psql -U postgres -d code_index_db -f scripts/setup_db.sql

# 3. Copy config and set DATABASE_URL to your instance
cp .env.example .env
# Edit .env: set DATABASE_URL=postgresql://code_index_user:code_index_pass@your-host:5432/code_index_db

# 4. Pull Ollama models
ollama pull nomic-embed-text
ollama pull devstral:24b

# 5. Install the plugin
claude plugin add github:BenjaminSchr/total-code-recall
```

---

## Usage

### `/code-onboard` — First-time indexing

Run this once when you start working on a new project. Must be executed from inside a Git repository.

```
/code-onboard
```

What happens:
1. Confirms you are inside a Git repo (no Git = stops with an error)
2. Discovers all indexable files (`.py`, `.html`, `.sql`, `.js`, `.css`, `.yaml`, `.json`, `.toml`, `.md`, `.sh`)
3. Splits each file into 50-line chunks with 15-line overlap
4. Generates a 2-3 sentence summary for each chunk using devstral
5. Embeds both the summary and the raw code using nomic-embed-text
6. Bulk-inserts everything into pgvector
7. Records the HEAD commit hash so `/code-update` knows where to resume

Example output:
```
Indexing complete!

Project:          my_project
Table:            my_project
Commit:           a3f8e21c — feat: add authentication middleware
Files:            42
Chunks:           387
Rows in DB:       774  (summary + code per chunk)
Embedding model:  nomic-embed-text
Summary model:    devstral:24b

You can now use /code-search to semantically search your code.
```

Re-running `/code-onboard` on an already-indexed project clears the existing index and rebuilds from scratch. Use `/code-update` for incremental updates.

---

### `/code-update` — Incremental updates after new commits

Run after you commit new code to keep the index current. Only re-indexes files that changed.

```
/code-update
```

What happens:
1. Reads the last indexed commit hash from the database
2. Runs `git diff` to find added, modified, deleted, and renamed files since then
3. Removes stale index rows for changed files
4. Re-indexes only the changed files
5. Updates the commit hash in the database

Example output:
```
Update complete!

Project:              my_project
Previous index:       a3f8e21c
Current HEAD:         b9d12f04 — refactor: split auth module
Files re-indexed:     3
Files removed:        1
New chunks:           28
Total chunks in DB:   398
```

If nothing changed since the last index, it exits cleanly: `No new commits since last index.`

---

### `/code-search "query"` — Semantic search

Search for code by meaning, not just keywords.

```
/code-search "date range filter for transactions"
```

Returns the top 10 most relevant chunks with file path, line numbers, type (summary or raw code), similarity score, and the full chunk content.

Example output:
```
Search results for: "date range filter for transactions"
Project: my_project
Found: 3 results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1] app/routes/transactions.py  Lines 45–94  Type: summary  Score: 0.9123
─────────────────────────────────────────────────
Filters transactions by date range using start_date and end_date query
parameters. Validates that start_date is before end_date and returns
a 422 error if the range is invalid.

[2] app/routes/transactions.py  Lines 45–94  Type: code  Score: 0.8841
─────────────────────────────────────────────────
@router.get("/transactions")
def list_transactions(start_date: str = None, end_date: str = None):
    ...
```

The `summary` type contains the AI-generated description. The `code` type contains the raw source. Both reference the same chunk — the score shows which matched better for your query.

---

## Configuration

Copy `.env.example` to `.env` and adjust as needed:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://code_index_user:code_index_pass@localhost:5433/code_index_db` | pgvector connection string |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API base URL |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Model used for embeddings (query + code + summaries) |
| `SUMMARY_MODEL` | `devstral:24b` | Model used to generate chunk summaries |
| `CHUNK_SIZE` | `50` | Lines per chunk |
| `CHUNK_OVERLAP` | `15` | Overlap lines between consecutive chunks |

The `.env` file is read from the current working directory at runtime. Place it in the project root you are indexing, or in the plugin directory.

---

## How it works

```
Source file
    │
    ▼
Fixed-size chunks (50 lines, 15-line overlap)
    │
    ▼
devstral:24b  ──►  2-3 sentence summary
    │
    ▼
nomic-embed-text
    ├──►  embed(summary)  ──►  row type="summary"  ──►  pgvector
    └──►  embed(code)     ──►  row type="code"     ──►  pgvector
                                                          │
                                                          ▼
/code-search "query"
    │
    ▼
nomic-embed-text  ──►  embed(query)
    │
    ▼
SELECT DISTINCT ON (chunk_id)
   1 - (embedding <=> query_vec) AS similarity
FROM project_table
ORDER BY similarity DESC LIMIT 10
```

Each chunk produces two rows in the database: one for the AI summary, one for the raw code. The search query is embedded with the same model and compared against both. Deduplication ensures a chunk appears at most once in the results, with the best-matching row winning.

The HNSW index on the embedding column makes queries fast even on large codebases.

---

## FAQ

**What languages are supported?**
Any text file. Chunking is fixed-size and language-agnostic — no parser required. The default allowlist covers: `.py`, `.html`, `.sql`, `.js`, `.css`, `.yaml`, `.json`, `.toml`, `.md`, `.sh`.

**Do I need an API key?**
No. Everything runs locally via Ollama. No data leaves your machine.

**How much disk space does the index use?**
Roughly 1 MB per 1,000 lines of code, depending on summary length. A 50,000-line project takes around 50 MB.

**Can I change the embedding model?**
Yes, update `EMBEDDING_MODEL` in `.env`. Note: the schema uses `vector(768)` which matches `nomic-embed-text`. If you switch to a model with different output dimensions, you must drop the project table (`DROP TABLE project_name`) and re-run `/code-onboard` to rebuild. The plugin detects model mismatches and will warn you before a search returns bad results.

**What about private code?**
Everything stays local. Summaries are generated by a local Ollama model, embeddings are computed locally, and the database runs on your machine. No code or metadata is sent to any external service.

**How do I update the index after new commits?**
Run `/code-update` from the project directory. It reads the last indexed commit hash, diffs against the current HEAD, and only re-indexes changed files.

**Can I index multiple projects?**
Yes. Each project gets its own table named after the Git repo (e.g., `my_project`, `tokenwatch`). All tables live in the same database. Run `/code-onboard` from each project directory.

---

## Requirements

- **Git** — all three skills require a Git repository (`git init` if needed)
- **Ollama** — local LLM server for summaries and embeddings (`ollama serve`)
- **PostgreSQL 14+ with pgvector** — via Docker (`docker compose up -d`) or your own instance
- **Python 3.10+** — with `psycopg2-binary` and `requests` (`pip install psycopg2-binary requests`)

---

## License

MIT — see [LICENSE](LICENSE).
