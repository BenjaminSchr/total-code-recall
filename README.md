# total-code-recall

Semantic code search for Claude Code. Index once, search instantly — runs fully local or fully in the cloud.

---

## What it does

**The problem:** Every time an agent opens your codebase it reads dozens of files to understand the project. That burns context window and costs tokens.

**The solution:** Run `/tcr-onboard` once. The plugin splits your code into 50-line chunks, generates summaries with an LLM, embeds both the summary and the raw code, and stores everything in a pgvector database. From then on, `/tcr-search "date filter"` finds the right file and line range in seconds — without reading a single source file.

**Seven commands. Works local (Ollama + Docker) or cloud (OpenRouter + Supabase).**

---

## Quick Start

### Step 1 — Install the plugin

```bash
claude plugin add github:BenjaminSchr/total-code-recall
```

### Step 2 — Configure providers

Run `/tcr-config` inside Claude Code. It walks you through three choices:

1. **LLM Provider** — Ollama (local, free) or OpenRouter (cloud, fast)
2. **Embedding Provider** — Ollama (local, free) or OpenRouter (cloud)
3. **Database** — local pgvector via Docker or Supabase (cloud, no Docker)

### Step 3 — Set up your database

**Option A — Docker (local pgvector, recommended)**

```bash
git clone https://github.com/BenjaminSchr/total-code-recall
cd total-code-recall
pip install -r requirements.txt
docker compose up -d
```

Database ready at `localhost:5433`.

**Option B — Bring your own pgvector**

```bash
psql -U postgres -c "CREATE USER code_index_user WITH PASSWORD 'code_index_pass';"
psql -U postgres -c "CREATE DATABASE code_index_db;"
psql -U postgres -d code_index_db -f scripts/setup_db.sql
```

Then set the connection string in `/tcr-config` → Database → Local.

**Option C — Supabase (zero local infrastructure)**

No Docker needed. Create a free project at [supabase.com](https://supabase.com), paste the pooler connection string (Session mode) into `/tcr-config` → Database → Cloud.

Full cloud setup (OpenRouter + Supabase): ~2-5 minutes to onboard a 10k line project. Cost: ~$0.05 per 500 chunks.

### Step 4 — Pull Ollama models (local mode only)

```bash
ollama pull nomic-embed-text   # ~274 MB, embedding model
ollama pull devstral:24b       # ~14 GB, summary model (needs ~16 GB VRAM)
```

Skip this step if you chose OpenRouter for both LLM and Embedding.

### Step 5 — Index your project

Open a Claude Code session in your project directory and run:

```
/tcr-onboard
```

---

## Commands

| Command | What it does |
|---------|-------------|
| `/tcr-config` | Configure providers (LLM, Embedding, DB). Run once before first use. |
| `/tcr-onboard` | Index a project for the first time. |
| `/tcr-update` | Update index after new commits. |
| `/tcr-search` | Semantic search over an indexed project. |
| `/tcr-overview` | Structural overview via entity/relation graph (requires tree-sitter). |
| `/tcr-explain` | Hybrid search: vector + graph context + file summaries. |
| `/tcr-info` | Show current config, indexed projects, and command reference. |

---

## Usage

### `/tcr-config` — Configure providers

Run this once before using any other command. It saves your config to `~/.config/total-code-recall/config.json` — shared across all projects.

```
/tcr-config
```

To change a single setting later, run it again — it detects an existing config and offers to change individual values.

---

### `/tcr-onboard` — First-time indexing

Run from inside a Git repository. Must be run once per project before searching.

```
/tcr-onboard
```

What happens:
1. Confirms you are inside a Git repo (no Git = stops with an error)
2. Checks that Ollama (if local mode) or OpenRouter (if cloud mode) is reachable
3. Discovers all indexable files (`.py`, `.html`, `.sql`, `.js`, `.css`, `.yaml`, `.json`, `.toml`, `.md`, `.sh`)
4. Splits each file into 50-line chunks with 15-line overlap
5. Generates a 2-3 sentence summary for each chunk using your configured LLM
6. Embeds both the summary and the raw code using your configured embedding model
7. Bulk-inserts everything into pgvector
8. Records the HEAD commit hash so `/tcr-update` knows where to resume

Example output:
```
Indexing complete!

Project:          my_project
Commit:           a3f8e21c — feat: add authentication middleware
Files:            42
Chunks:           387
Rows in DB:       774  (summary + code per chunk)
Embedding model:  nomic-embed-text
Summary model:    devstral:24b
```

Re-running `/tcr-onboard` on an already-indexed project clears the existing index and rebuilds from scratch. Use `/tcr-update` for incremental updates.

---

### `/tcr-update` — Incremental updates after new commits

Run after committing new code to keep the index current. Only re-indexes files that changed.

```
/tcr-update
```

What happens:
1. Reads the last indexed commit hash from the database
2. Runs `git diff` to find added, modified, deleted, and renamed files since then
3. Removes stale index rows for changed files
4. Re-indexes only the changed files
5. Updates the commit hash in the database

If nothing changed since the last index, it exits cleanly: `No new commits since last index.`

---

### `/tcr-search "query"` — Semantic search

Search for code by meaning, not just keywords.

```
/tcr-search "date range filter for transactions"
```

Returns the top 10 most relevant chunks with file path, line numbers, similarity score, and full chunk content.

Example output:
```
Search results for: "date range filter for transactions"
Project: my_project  |  Found: 3 results

[1] app/routes/transactions.py  Lines 45–94  Type: summary  Score: 0.9123
Filters transactions by date range using start_date and end_date query
parameters. Validates that start_date is before end_date.

[2] app/routes/transactions.py  Lines 45–94  Type: code  Score: 0.8841
@router.get("/transactions")
def list_transactions(start_date: str = None, end_date: str = None):
    ...
```

---

### `/tcr-overview` — Structural overview

Shows your project's structure: classes, functions, imports, and call relationships. No LLM — pure database queries.

```
/tcr-overview                   # Full project overview
/tcr-overview MyClassName       # Show callers and callees for a specific symbol
```

Requires tree-sitter to have been installed when `/tcr-onboard` ran. If the entity tables are empty, the skill reports that structural analysis is unavailable.

---

### `/tcr-explain "query"` — Hybrid search

Combines vector similarity with structural graph analysis. Results are enriched with entity context, callers/callees, and file summaries.

```
/tcr-explain "how does authentication work"
```

Works best when tree-sitter was installed during `/tcr-onboard`. Without it, entity/graph context is empty but vector search and file summaries still work.

---

### `/tcr-info` — Status and help

Shows your current configuration, all indexed projects, and a command reference.

```
/tcr-info
```

Example output:
```
=== total-code-recall v0.2.0 ===

Config: ~/.config/total-code-recall/config.json

  LLM Provider:       ollama  (devstral:24b)
  Embedding Provider: ollama  (nomic-embed-text)
  DB Provider:        local
  Parallel Workers:   10
  Chunk Size:         50 lines  (overlap: 15)

Indexed Projects (2):

  1. my_project
     Path:        /home/user/projects/my_project
     Last commit: a3f8e21c
     Indexed at:  2026-05-23T14:32:00

Commands:
  /tcr-config   /tcr-onboard   /tcr-update
  /tcr-search   /tcr-overview  /tcr-explain  /tcr-info
```

---

## Provider Matrix

| Feature | Local | Cloud |
|---------|-------|-------|
| **LLM (summaries)** | Ollama — devstral:24b | OpenRouter — any model |
| **Embeddings** | Ollama — nomic-embed-text (768-dim) | OpenRouter — google/text-embedding-004 (768-dim) |
| **Database** | pgvector via Docker (port 5433) | Supabase pooler (session mode) |

---

## Configuration

`/tcr-config` saves to `~/.config/total-code-recall/config.json`. This file is shared across all projects.

**Config priority (highest to lowest):**
1. Project `.env` file (environment variables)
2. `~/.config/total-code-recall/config.json` (set by `/tcr-config`)
3. Hardcoded defaults

Environment variable overrides (place in `.env` in your project root):

| Variable | Config key | Default |
|---|---|---|
| `DATABASE_URL` | `database_url` | `postgresql://code_index_user:code_index_pass@localhost:5433/code_index_db` |
| `OLLAMA_URL` | `ollama_url` | `http://localhost:11434` |
| `EMBEDDING_MODEL` | `embedding_model` | `nomic-embed-text` |
| `SUMMARY_MODEL` | `ollama_summary_model` | `devstral:24b` |
| `LLM_PROVIDER` | `llm_provider` | `ollama` |
| `EMBEDDING_PROVIDER` | `embedding_provider` | `ollama` |
| `OPENROUTER_API_KEY` | `openrouter_api_key` | — |
| `OPENROUTER_MODEL` | `openrouter_model` | `google/gemini-flash-2.0` |
| `CHUNK_SIZE` | `chunk_size` | `50` |
| `CHUNK_OVERLAP` | `chunk_overlap` | `15` |
| `PARALLEL_WORKERS` | `parallel_workers` | `10` |

---

## How it works

```
Source file
    │
    ▼
Fixed-size chunks (50 lines, 15-line overlap)
    │
    ├──► LLM (devstral or OpenRouter)  ──►  2-3 sentence summary
    │        │
    │        ▼
    │    Embedding model (nomic-embed-text or google/text-embedding-004)
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

/tcr-search "query"  ──►  embed query  ──►  cosine similarity  ──►  top 10 chunks

/tcr-explain "query"  ──►  vector search + graph lookup
    ├──►  matched chunks
    ├──►  entity context (callers, callees)
    └──►  file summary context

/tcr-overview  ──►  pure DB queries on _entities + _relations (no LLM)
```

Each chunk produces two rows: one for the AI summary, one for the raw code. Deduplication ensures a chunk appears at most once in results, with the best-matching row winning.

---

## FAQ

**Do I need an API key?**
No for local mode (Ollama + pgvector via Docker) — everything runs on your machine. Yes for cloud mode: [OpenRouter](https://openrouter.ai) for LLM/embeddings, and a [Supabase](https://supabase.com) project for the database.

**What about private code?**
Local mode: fully private. No code leaves your machine. Cloud mode: code chunks and embeddings are sent to OpenRouter (for embedding/summarization) and stored in Supabase. Check your provider's data policies.

**Which embedding model should I use?**
Local: `nomic-embed-text` (768-dim, fast, free). Cloud: `google/text-embedding-004` (768-dim, via OpenRouter). Important: the schema hardcodes `vector(768)` — only 768-dimensional models are compatible. If you switch models, drop the project table and re-run `/tcr-onboard`.

**What is the relational layer?**
When tree-sitter is installed, `/tcr-onboard` parses Python files to extract entities (files, classes, functions) and relations (calls, imports, contains). Stored in `_entities` and `_relations` tables. Powers `/tcr-overview` and enriches `/tcr-explain`. Without it, vector search works normally.

**Do I need tree-sitter?**
No. It is optional. Install with `pip install tree-sitter tree-sitter-languages` to enable `/tcr-overview` and graph-augmented `/tcr-explain`.

**What languages are supported?**
Any text file — chunking is fixed-size and language-agnostic. Default allowlist: `.py`, `.html`, `.sql`, `.js`, `.css`, `.yaml`, `.json`, `.toml`, `.md`, `.sh`. Structural analysis (tree-sitter) currently covers Python only.

**Can I index multiple projects?**
Yes. Each project gets its own table named after the sanitized Git repo name. Run `/tcr-onboard` from each project directory. All tables share the same database.

**How much disk space does the index use?**
Roughly 1 MB per 1,000 lines of code. A 50,000-line project takes ~50 MB.

**How do I update the index after new commits?**
Run `/tcr-update` from the project directory.

---

## Requirements

| Requirement | When needed |
|---|---|
| **Git** | Always — all skills require a Git repository |
| **Python 3.10+** with `psycopg2-binary`, `requests` | Always |
| **PostgreSQL 14+ with pgvector 0.5+** | Local mode (via Docker or own instance) |
| **Ollama 0.3+** | Local mode for LLM and/or embeddings |
| **OpenRouter API key** | Cloud mode for LLM and/or embeddings |
| **Supabase project** | Cloud mode for database |
| **tree-sitter + tree-sitter-languages** | Optional — enables `/tcr-overview` and graph-augmented `/tcr-explain` |

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `Ollama not reachable` | Ollama not running | `ollama serve` |
| `Model not found` | Model not pulled | `ollama pull nomic-embed-text && ollama pull devstral:24b` |
| `DB connection failed` | PostgreSQL not running | Check `DATABASE_URL`, verify DB is up |
| `permission denied for extension vector` | setup_db.sql not run as superuser | `psql -U postgres -d code_index_db -f scripts/setup_db.sql` |
| `No git repository found` | Not inside a git repo | `cd` into your project or run `git init` |
| `Embedding model mismatch` | Model changed since last index | Re-run `/tcr-onboard` to rebuild |
| `AST_SKIP: tree-sitter not installed` | tree-sitter not available (non-blocking) | `pip install tree-sitter tree-sitter-languages` |
| `OpenRouter auth error` | Invalid or missing API key | Run `/tcr-config` and re-enter your OpenRouter key |
| `OpenRouter rate limit` | Too many requests | Reduce `PARALLEL_WORKERS` in config (default 10) |
| `Supabase connection failed` | Wrong pooler URL or missing SSL | Use Session mode URL; `/tcr-config` auto-appends `?sslmode=require` |
| `vector dimension mismatch` | Switched embedding models | Drop the project table and re-run `/tcr-onboard` |

---

## License

MIT — see [LICENSE](LICENSE).
