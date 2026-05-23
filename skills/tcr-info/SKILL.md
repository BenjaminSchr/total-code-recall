---
name: tcr-info
description: Show current total-code-recall config, indexed projects, and command reference.
---

# /tcr-info — Status and Help

You are executing the **tcr-info** skill. Read and display all status information. Do not modify any files.

---

## Step 1 — Load config

```python
import json, os

CONFIG_PATH = os.path.expanduser("~/.config/total-code-recall/config.json")

if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
else:
    cfg = None
```

If `cfg is None`: print `"No config found. Run /tcr-config first to set up your providers."` and continue to Step 4 (skip Steps 2 and 3).

---

## Step 2 — Show config

Display the current configuration:

```
=== total-code-recall v0.2.0 ===

Config: ~/.config/total-code-recall/config.json

  LLM Provider:       <llm_provider>  (<ollama_summary_model or openrouter_model>)
  Embedding Provider: <embedding_provider>  (<embedding_model>)
  DB Provider:        <db_provider>
  Database URL:       <database_url, truncated to 60 chars if longer>
  Parallel Workers:   <parallel_workers, default 10>
  Chunk Size:         <chunk_size, default 50> lines  (overlap: <chunk_overlap, default 15>)
```

Use `cfg.get("key", "not set")` for all fields to handle partial configs gracefully.

---

## Step 3 — Query indexed projects

Write `/tmp/tcr_info.py`:

```python
import psycopg2, psycopg2.sql, json, os, sys

CONFIG_PATH = os.path.expanduser("~/.config/total-code-recall/config.json")
try:
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
except FileNotFoundError:
    print(json.dumps({"error": "no_config"}))
    sys.exit(0)

DATABASE_URL = os.environ.get("DATABASE_URL") or cfg.get("database_url")
if not DATABASE_URL:
    print(json.dumps({"error": "no_database_url"}))
    sys.exit(0)

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Find all _index_meta tables
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_name LIKE '%_index_meta'
        AND table_schema = 'public'
        ORDER BY table_name
    """)
    meta_tables = [row[0] for row in cur.fetchall()]

    projects = []
    for tbl in meta_tables:
        project_name = tbl.replace("_index_meta", "")
        cur.execute(psycopg2.sql.SQL("SELECT key, value FROM {}").format(psycopg2.sql.Identifier(tbl)))
        meta = dict(cur.fetchall())
        projects.append({
            "name": project_name,
            "path": meta.get("project_root", "unknown"),
            "last_commit": meta.get("last_commit", "unknown"),
            "indexed_at": meta.get("indexed_at", "unknown"),
            "embedding_model": meta.get("embedding_model", "unknown")
        })

    cur.close()
    conn.close()
    print(json.dumps({"projects": projects}))

except Exception as e:
    print(json.dumps({"error": str(e)}))
```

Run: `python3 /tmp/tcr_info.py`

Parse JSON output and display:

```
Indexed Projects (<count>):

  1. <project_name>
     Path:            <path>
     Last commit:     <last_commit>
     Indexed at:      <indexed_at>
     Embedding model: <embedding_model>

  2. ...
```

If `projects` is empty: `"No projects indexed yet. Run /tcr-onboard <path> to index your first project."`

If error `no_config`: `"Database not configured. Run /tcr-config first."`

If error `no_database_url`: `"DATABASE_URL not set. Run /tcr-config to configure your database."`

If connection error: `"Could not connect to database: <error>. Check your database URL in /tcr-config."`

---

## Step 4 — Command reference

Print the full command list:

```
Commands:
  /tcr-config    Configure providers (LLM, Embedding, DB). Run once before first use.
  /tcr-onboard   Index a project for the first time.
  /tcr-update    Update index after new commits.
  /tcr-search    Semantic search over an indexed project.
  /tcr-overview  Structural overview via entity/relation graph (requires tree-sitter).
  /tcr-explain   Hybrid search: vector + graph context + file summaries.
  /tcr-info      Show this status page.
```

---

## Notes

- `/tcr-info` is read-only. It does not write any files or modify the database.
- Config is read from `~/.config/total-code-recall/config.json` (global, shared across all projects).
- The database query uses `information_schema.tables` — it works with both local pgvector and Supabase.
- If the DB is unreachable, Steps 2 and 4 still run successfully — only Step 3 shows an error message.
