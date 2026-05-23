# total-code-recall

Semantic code search for Claude Code. Index once, search instantly — no API keys, no cloud, everything runs locally.

---

## What it does

**The problem:** Every time an agent opens your codebase it reads dozens of files to understand the project. That burns context window and costs tokens.

**The solution:** Run `/tcr-onboard` once. The plugin splits your code into 50-line chunks, generates summaries with a local LLM (devstral), embeds both the summary and the raw code with a local embedding model (nomic-embed-text), and stores everything in a pgvector database. From then on, `/tcr-search "date filter"` finds the right file and line range in seconds — without reading a single source file.

Five commands. Zero API keys. All local.

---

## Quick Start

### Prerequisites

- [Ollama](https://ollama.ai) running locally (default: `http://localhost:11434`)
- PostgreSQL with pgvector extension (see Option A or B below)
- Python 3.10+ with `psycopg2-binary` and `requests` available to Claude Code
- `tree-sitter` and `tree-sitter-languages` (optional — enables structural analysis via `/tcr-overview` and `/tcr-explain`)

### Option A — Docker (recommended)

Spin up the pre-configured pgvector container included in this repo:

```bash
# 1. Clone and enter the repo
git clone https://github.com/BenjaminSchr/total-code-recall
cd total-code-recall

# 2. Copy the config
cp .env.example .env

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Start the pgvector container
#    setup_db.sql runs automatically on first start
docker compose up -d

# 5. Pull the required Ollama models
ollama pull nomic-embed-text          # ~274 MB, embedding model
ollama pull devstral:24b              # ~14 GB download, needs ~16 GB VRAM (GPU recommended)

# 6. Install the plugin
claude plugin add github:BenjaminSchr/total-code-recall
```

Done. The database is ready at `localhost:5433`.

### Option B — Bring your own pgvector

If you already have a pgvector-enabled PostgreSQL instance:

```bash
# 1. Create the database and user
psql -U postgres -c "CREATE USER code_index_user WITH PASSWORD 'code_index_pass';"
psql -U postgres -c "CREATE DATABASE code_index_db;"

# 2. Run the setup script as superuser (creates extension + tables + grants permissions)
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

### Option C — Cloud Setup (Zero Local Infrastructure)

Run total-code-recall entirely in the cloud — no Docker, no Ollama required.

**Requirements:**
- OpenRouter account + API key (https://openrouter.ai)
- Supabase project + connection string (https://supabase.com, free tier works)
- Claude Code with this plugin installed

**Setup:**
1. Install the plugin: `claude plugin add github:BenjaminSchr/total-code-recall`
2. Run `/tcr-config`
3. LLM Provider → Cloud (OpenRouter) → paste API key → pick model
4. Embedding Provider → Cloud (OpenRouter) → pick embedding model (use `google/text-embedding-004` for 768-dim compatibility)
5. Database → Cloud (Supabase) → paste pooler connection string (Session mode)

**Finding your Supabase connection string:**
Supabase dashboard → Settings → Database → Connection string → Session mode

**Onboard time:** ~2-5 minutes for a 10k line project (parallel OpenRouter calls).

**Cost estimate:** ~$0.001 per summary, ~$0.0001 per embedding. 500-chunk project ≈ $0.05.

---

## Usage

### `/tcr-onboard` — First-time indexing

Run this once when you start working on a new project. Must be executed from inside a Git repository.

```
/tcr-onboard
```

What happens:
1. Confirms you are inside a Git repo (no Git = stops with an error)
2. Discovers all indexable files (`.py`, `.html`, `.sql`, `.js`, `.css`, `.yaml`, `.json`, `.toml`, `.md`, `.sh`)
3. Splits each file into 50-line chunks with 15-line overlap
4. Generates a 2-3 sentence summary for each chunk using devstral
5. Embeds both the summary and the raw code using nomic-embed-text
6. Bulk-inserts everything into pgvector
7. Records the HEAD commit hash so `/tcr-update` knows where to resume

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

You can now use /tcr-search to semantically search your code.
```

Re-running `/tcr-onboard` on an already-indexed project clears the existing index and rebuilds from scratch. Use `/tcr-update` for incremental updates.

---

### `/tcr-update` — Incremental updates after new commits

Run after you commit new code to keep the index current. Only re-indexes files that changed.

```
/tcr-update
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

### `/tcr-search "query"` — Semantic search

Search for code by meaning, not just keywords.

```
/tcr-search "date range filter for transactions"
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

### `/tcr-overview` — Structural overview

Shows your project's structure: classes, functions, imports, and call relationships. No LLM needed — pure database queries.

```
/tcr-overview                    # Full project overview
/tcr-overview MyClassName        # Show callers and callees for a specific symbol
```

Requires tree-sitter to have been installed when `/tcr-onboard` was run. If the entity tables are empty, the skill reports that structural analysis is unavailable.

---

### `/tcr-explain "query"` — Hybrid search

Combines vector similarity search with structural graph analysis. Returns code chunks enriched with entity context, callers/callees, and file summaries.

```
/tcr-explain "how does authentication work"
```

Differs from `/tcr-search` in that results are augmented with structural context: which functions call the matched code, what the file summary says, and which entities are involved. Works best when tree-sitter was installed during `/tcr-onboard`; without it, entity/graph context will be empty but vector search and file summaries still work.

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

The `.env` file is read from the current working directory at runtime. Place it in the root of the project you are indexing — the skills look for `.env` in the directory where you run the command.

---

## How it works

```
Source file
    │
    ▼
Fixed-size chunks (50 lines, 15-line overlap)
    │
    ├──► devstral:24b  ──►  2-3 sentence summary
    │        │
    │        ▼
    │    nomic-embed-text
    │        ├──►  embed(summary)  ──►  row type="summary"  ──►  pgvector
    │        └──►  embed(code)     ──►  row type="code"     ──►  pgvector
    │
    └──► tree-sitter AST (optional)
             ├──►  entities (file, class, function, method, import)  ──►  _entities table
             └──►  relations (calls, imports, contains)              ──►  _relations table

Hierarchical summaries (built after chunking):
    file chunks  ──►  file-level summary  ──►  _summaries (level='file')
    file summaries  ──►  module summary   ──►  _summaries (level='module')
    module summaries  ──►  repo summary   ──►  _summaries (level='repo')

/tcr-search "query"  ──►  vector search  ──►  top 10 chunks by cosine similarity

/tcr-explain "query"  ──►  vector search + graph lookup
    ├──►  matched chunks
    ├──►  entity context (callers, callees)
    └──►  file summary context

/tcr-overview  ──►  pure DB queries on _entities + _relations (no LLM)
```

Each chunk produces two rows in the database: one for the AI summary, one for the raw code. The search query is embedded with the same model and compared against both. Deduplication ensures a chunk appears at most once in the results, with the best-matching row winning.

The relational layer (entity and relation tables, built via tree-sitter AST parsing) is optional and non-blocking: if tree-sitter is not installed, `/tcr-onboard` skips it with a warning and the vector search pipeline continues normally. Installing tree-sitter unlocks `/tcr-overview` and the graph-augmented `/tcr-explain`.

The HNSW index on the embedding column makes vector queries fast even on large codebases.

---

## FAQ

**What is the relational layer?**
When tree-sitter is installed, `/tcr-onboard` parses Python files to extract a structural model of the codebase: entities (files, classes, functions, methods, imports) and relations between them (calls, imports, contains). This data is stored in `_entities` and `_relations` tables alongside the vector index. The relational layer powers `/tcr-overview` (structure browsing) and enriches `/tcr-explain` results with caller/callee context. Without it, vector search still works normally.

**Do I need tree-sitter?**
No. It is optional. Without it, `/tcr-onboard` and `/tcr-update` work fully for vector search (`/tcr-search`). Installing it (`pip install tree-sitter tree-sitter-languages`) adds structural analysis: entity/relation extraction, the `/tcr-overview` command, and graph-augmented results in `/tcr-explain`.

**What languages are supported?**
Any text file. Chunking is fixed-size and language-agnostic — no parser required. The default allowlist covers: `.py`, `.html`, `.sql`, `.js`, `.css`, `.yaml`, `.json`, `.toml`, `.md`, `.sh`. Structural analysis (tree-sitter) currently covers Python only.

**Do I need an API key?**
No. Everything runs locally via Ollama. No data leaves your machine.

**How much disk space does the index use?**
Roughly 1 MB per 1,000 lines of code, depending on summary length. A 50,000-line project takes around 50 MB.

**Can I change the embedding model?**
Yes, update `EMBEDDING_MODEL` in `.env`. Note: the schema uses `vector(768)` which matches `nomic-embed-text`. If you switch to a model with different output dimensions, you must drop the project table (`DROP TABLE project_name`) and re-run `/tcr-onboard` to rebuild. The plugin detects model mismatches and will warn you before a search returns bad results.

**What about private code?**
Everything stays local. Summaries are generated by a local Ollama model, embeddings are computed locally, and the database runs on your machine. No code or metadata is sent to any external service.

**How do I update the index after new commits?**
Run `/tcr-update` from the project directory. It reads the last indexed commit hash, diffs against the current HEAD, and only re-indexes changed files.

**Can I index multiple projects?**
Yes. Each project gets its own table named after the Git repo (e.g., `my_project`, `tokenwatch`). All tables live in the same database. Run `/tcr-onboard` from each project directory.

---

## Requirements

- **Git** — all five skills require a Git repository (`git init` if needed)
- **Ollama 0.3+** — local LLM server for summaries and embeddings (`ollama serve`). `devstral:24b` requires ~16 GB VRAM (GPU recommended).
- **PostgreSQL 14+ with pgvector 0.5+** — via Docker (`docker compose up -d`) or your own instance
- **Python 3.10+** — with `psycopg2-binary` and `requests` (`pip install -r requirements.txt`)
- **tree-sitter and tree-sitter-languages** (optional) — enables structural analysis for `/tcr-overview` and `/tcr-explain` (`pip install tree-sitter tree-sitter-languages`)

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `Ollama not reachable` | Ollama not running | `ollama serve` |
| `Model not found` | Embedding/summary model not pulled | `ollama pull nomic-embed-text && ollama pull devstral:24b` |
| `DB connection failed` | PostgreSQL not running or wrong URL | Check `DATABASE_URL` in `.env`, verify DB is up |
| `permission denied for extension vector` | setup_db.sql not run as superuser | Run as postgres user: `psql -U postgres -d code_index_db -f scripts/setup_db.sql` |
| `No git repository found` | Not inside a git repo | `cd` into your project and run `git init` if needed |
| `Embedding model mismatch` | `.env` model changed since last index | Re-run `/tcr-onboard` to rebuild with new model |
| `AST_SKIP: tree-sitter not installed` | tree-sitter not available (non-blocking) | `pip install tree-sitter tree-sitter-languages` for structural analysis |

---

## License

MIT — see [LICENSE](LICENSE).
