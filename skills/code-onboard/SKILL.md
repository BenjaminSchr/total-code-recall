---
name: code-onboard
description: Index a Git project into pgvector for semantic code search. Discovers files, chunks them, generates summaries via devstral, embeds both summary and code via nomic-embed-text, bulk-inserts into PostgreSQL.
---

# /code-onboard — Skill Instructions

You are executing the **code-onboard** skill. Follow these 8 steps in order. Do not skip any step. At each step, report what you are doing.

---

## Config

Read configuration from environment variables. Use these defaults if not set:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql://code_index_user:code_index_pass@localhost:5433/code_index_db` | PostgreSQL connection string |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API base URL |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Model for embeddings (summary + code) |
| `SUMMARY_MODEL` | `devstral:24b` | Model for generating summaries |
| `CHUNK_SIZE` | `50` | Lines per chunk |
| `CHUNK_OVERLAP` | `15` | Overlap lines between consecutive chunks |

At the start, read these from the environment:

```python
import os
# Load .env file if present
_env_path = os.path.join(os.getcwd(), ".env")
if not os.path.exists(_env_path):
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
DATABASE_URL   = os.getenv("DATABASE_URL",   "postgresql://code_index_user:code_index_pass@localhost:5433/code_index_db")
OLLAMA_URL     = os.getenv("OLLAMA_URL",     "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
SUMMARY_MODEL  = os.getenv("SUMMARY_MODEL",  "devstral:24b")
CHUNK_SIZE     = int(os.getenv("CHUNK_SIZE",   "50"))
CHUNK_OVERLAP  = int(os.getenv("CHUNK_OVERLAP", "15"))
```

---

## Step 1: Git Gate

**Goal:** Confirm we are inside a Git repository and extract the project name.

Run this shell command:

```bash
git rev-parse --is-inside-work-tree
```

- If it fails or returns nothing: print `"No git repository found. Please run 'git init' first."` and **stop immediately**.
- If it succeeds: extract the repo name:

```bash
basename $(git rev-parse --show-toplevel)
```

**Sanitize the repo name** using this Python logic:

```python
import re
raw_name = "<result of basename command>"
project_name = raw_name.lower()
project_name = project_name.replace("-", "_")
project_name = re.sub(r"[^a-z0-9_]", "", project_name)
```

Also extract the HEAD commit hash and most recent commit message for use in Step 6:

```bash
git log -1 --format="%H"
git log -1 --format="%s"
```

Store: `project_name`, `HEAD_HASH`, `HEAD_MESSAGE`.

Report: `"Project name: {project_name}, HEAD: {HEAD_HASH[:8]}"`

---

## Step 2: Check Prerequisites

**Goal:** Confirm Ollama is running, both models are available, and the DB is reachable.

### 2a. Check Ollama

```bash
curl -s {OLLAMA_URL}/api/tags
```

- If this fails: print `"Ollama not reachable at {OLLAMA_URL}. Please start Ollama."` and **stop**.
- Parse the JSON response and check if `EMBEDDING_MODEL` and `SUMMARY_MODEL` are listed under `"models"[].name`.

### 2b. Pull missing models

For each model that is NOT in the tags response, run:

```bash
ollama pull {model_name}
```

Wait for the pull to complete before continuing. Report: `"Model {model_name} pulled successfully."` or `"Model {model_name} already available."`

### 2c. Check DB

Write this to `/tmp/tcr_check_db.py` and run it with `python3 /tmp/tcr_check_db.py`:

```python
import sys, os
# Load .env file if present
_env_path = os.path.join(os.getcwd(), ".env")
if not os.path.exists(_env_path):
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://code_index_user:code_index_pass@localhost:5433/code_index_db")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT 1")
    conn.close()
    print("DB_OK")
except Exception as e:
    print(f"DB_FAIL: {e}")
    sys.exit(1)
```

- If output is `DB_OK`: continue.
- If output starts with `DB_FAIL`: print `"Database not reachable. Please check DATABASE_URL and start the DB."` and **stop**.

---

## Step 3: Create Project Table

**Goal:** Create the pgvector table for this project (idempotent — safe to re-run).

Write this to `/tmp/tcr_create_table.py` and run it with `python3 /tmp/tcr_create_table.py`:

```python
import os, sys
# Load .env file if present
_env_path = os.path.join(os.getcwd(), ".env")
if not os.path.exists(_env_path):
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
import psycopg2

DATABASE_URL  = os.getenv("DATABASE_URL",   "postgresql://code_index_user:code_index_pass@localhost:5433/code_index_db")
PROJECT_NAME  = os.environ["TCR_PROJECT"]   # passed via env

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {PROJECT_NAME} (
    id              SERIAL PRIMARY KEY,
    chunk_id        INT NOT NULL,
    type            VARCHAR(10) NOT NULL CHECK (type IN ('summary', 'code')),
    file_path       TEXT NOT NULL,
    line_start      INT NOT NULL,
    line_end        INT NOT NULL,
    content         TEXT NOT NULL,
    commit_hash     VARCHAR(40) NOT NULL,
    commit_message  TEXT,
    embedding_model VARCHAR(100) NOT NULL,
    embedding       vector(768),
    indexed_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS {PROJECT_NAME}_embedding_idx
    ON {PROJECT_NAME} USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS {PROJECT_NAME}_chunk_id_idx
    ON {PROJECT_NAME} (chunk_id);

CREATE INDEX IF NOT EXISTS {PROJECT_NAME}_file_path_idx
    ON {PROJECT_NAME} (file_path);

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
"""

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(CREATE_TABLE_SQL)
    conn.commit()
    conn.close()
    print(f"TABLE_OK: {PROJECT_NAME}")
except Exception as e:
    print(f"TABLE_FAIL: {e}")
    sys.exit(1)
```

Run it with the project name passed as an environment variable:

```bash
TCR_PROJECT={project_name} python3 /tmp/tcr_create_table.py
```

- If output starts with `TABLE_OK`: continue.
- If output starts with `TABLE_FAIL`: print the error and **stop**.

Report: `"Table '{project_name}' created (or already exists)."`

---

## Step 4: Discover Files

**Goal:** Build the list of files to index using allowlist + blocklist + minimum size filter.

### Allowlist (only these extensions)

`.py`, `.html`, `.sql`, `.js`, `.css`, `.yaml`, `.json`, `.toml`, `.md`, `.sh`

### Blocklist (always skip — path contains any of these)

`venv/`, `__pycache__/`, `.git/`, `node_modules/`, `data/`, `.paul/`, `.env`

Also skip any file matching these patterns:
- `*.min.css`
- `*.min.js`
- `*.pyc`
- `*.png`, `*.jpg`, `*.pdf`
- `*.woff`, `*.ttf`, `*.ico`

### Discovery command

Run `find` from the project root to get all candidate files:

```bash
find . -type f \( \
  -name "*.py" -o -name "*.html" -o -name "*.sql" \
  -o -name "*.js" -o -name "*.css" -o -name "*.yaml" \
  -o -name "*.json" -o -name "*.toml" -o -name "*.md" \
  -o -name "*.sh" \
\)
```

Then filter out blocklist paths and files with fewer than 3 lines using Python:

```python
BLOCKLIST_DIRS = ["venv/", "__pycache__/", ".git/", "node_modules/", "data/", ".paul/", ".env"]
BLOCKLIST_SUFFIXES = [".min.css", ".min.js", ".pyc", ".png", ".jpg", ".pdf", ".woff", ".ttf", ".ico"]

def is_blocked(path):
    for b in BLOCKLIST_DIRS:
        if b in path:
            return True
    for s in BLOCKLIST_SUFFIXES:
        if path.endswith(s):
            return True
    return False

files_to_index = []
for path in raw_find_output.splitlines():
    path = path.strip()
    if path.startswith("./"):
        path = path[2:]
    if not path:
        continue
    if is_blocked(path):
        continue
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        if len(lines) < 3:
            continue
        files_to_index.append((path, lines))
    except Exception:
        continue
```

Report: `"Found {len(files_to_index)} files to index."`

---

## Step 5: Chunk Files

**Goal:** Split each file into fixed-size chunks with overlap. Assign a global sequential `chunk_id`.

```python
CHUNK_SIZE    = int(os.getenv("CHUNK_SIZE", "50"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "15"))

chunks = []       # list of dicts
chunk_id = 0      # global counter, sequential across ALL files

for file_path, lines in files_to_index:
    start = 0
    total = len(lines)
    while start < total:
        end = min(start + CHUNK_SIZE, total)
        chunk_lines = lines[start:end]
        chunk_text  = "".join(chunk_lines)
        if chunk_text.strip():   # skip empty chunks
            chunks.append({
                "chunk_id":   chunk_id,
                "file_path":  file_path,
                "line_start": start + 1,        # 1-based
                "line_end":   end,              # 1-based inclusive
                "content":    chunk_text,
            })
            chunk_id += 1
        if end == total:
            break
        start += CHUNK_SIZE - CHUNK_OVERLAP
```

Report: `"Created {len(chunks)} chunks from {len(files_to_index)} files."`

---

## Step 6: Generate Summaries + Embeddings — Batch INSERT

**Goal:** For each chunk, generate a summary (devstral), embed both summary and code (embedding model), insert two rows into the DB.

Write this entire script to `/tmp/tcr_index.py` and run it with `python3 /tmp/tcr_index.py`:

```python
import os, sys, json, time
# Load .env file if present
_env_path = os.path.join(os.getcwd(), ".env")
if not os.path.exists(_env_path):
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
import requests
import psycopg2

DATABASE_URL    = os.getenv("DATABASE_URL",    "postgresql://code_index_user:code_index_pass@localhost:5433/code_index_db")
OLLAMA_URL      = os.getenv("OLLAMA_URL",      "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
SUMMARY_MODEL   = os.getenv("SUMMARY_MODEL",   "devstral:24b")
PROJECT_NAME    = os.environ["TCR_PROJECT"]
HEAD_HASH       = os.environ["TCR_HEAD_HASH"]

# --- chunks and meta are passed via JSON file to avoid shell injection ---
with open("/tmp/tcr_chunks.json", "r") as f:
    data = json.load(f)
HEAD_MESSAGE = data["meta"]["head_message"]
chunks = data["chunks"]

INSERT_SQL = f"""
INSERT INTO {PROJECT_NAME}
    (chunk_id, type, file_path, line_start, line_end, content,
     commit_hash, commit_message, embedding_model, embedding)
VALUES
    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
"""

def generate_summary(code_text):
    """Call devstral via Ollama generate API to produce a summary."""
    prompt = (
        "You are a code documentation assistant. "
        "Write a concise 2-3 sentence summary of what the following code does. "
        "Focus on purpose and behavior, not syntax.\n\n"
        f"```\n{code_text[:3000]}\n```"
    )
    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": SUMMARY_MODEL, "prompt": prompt, "stream": False},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()

def get_embedding(text):
    """Call embedding model via Ollama embed API."""
    resp = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBEDDING_MODEL, "input": text},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    # Ollama embed returns {"embeddings": [[...]]} (list of lists)
    return data["embeddings"][0]

conn = psycopg2.connect(DATABASE_URL)
cur  = conn.cursor()

# Clear existing data for idempotent re-onboard
cur.execute(f"DELETE FROM {PROJECT_NAME}")
conn.commit()
print(f"CLEARED: Removed existing data from {PROJECT_NAME}")

total = len(chunks)
for i, chunk in enumerate(chunks):
    print(f"  [{i+1}/{total}] chunk_id={chunk['chunk_id']} {chunk['file_path']} lines {chunk['line_start']}-{chunk['line_end']}", flush=True)

    # --- Summary ---
    try:
        summary_text = generate_summary(chunk["content"])
    except Exception as e:
        print(f"    WARN: summary failed: {e} — using fallback")
        summary_text = f"Code chunk from {chunk['file_path']} lines {chunk['line_start']}-{chunk['line_end']}"

    # --- Embeddings ---
    try:
        summary_vec = get_embedding(summary_text)
    except Exception as e:
        print(f"    WARN: summary embedding failed: {e} — skipping chunk")
        continue

    try:
        code_vec = get_embedding(chunk["content"])
    except Exception as e:
        print(f"    WARN: code embedding failed: {e} — skipping chunk")
        continue

    # Convert list to pgvector string format
    summary_vec_str = "[" + ",".join(str(x) for x in summary_vec) + "]"
    code_vec_str    = "[" + ",".join(str(x) for x in code_vec) + "]"

    # --- Insert summary row ---
    cur.execute(INSERT_SQL, (
        chunk["chunk_id"], "summary",
        chunk["file_path"], chunk["line_start"], chunk["line_end"],
        summary_text,
        HEAD_HASH, HEAD_MESSAGE, EMBEDDING_MODEL,
        summary_vec_str,
    ))

    # --- Insert code row ---
    cur.execute(INSERT_SQL, (
        chunk["chunk_id"], "code",
        chunk["file_path"], chunk["line_start"], chunk["line_end"],
        chunk["content"],
        HEAD_HASH, HEAD_MESSAGE, EMBEDDING_MODEL,
        code_vec_str,
    ))

    # Commit every 10 chunks to avoid long transactions
    if (i + 1) % 10 == 0:
        conn.commit()

conn.commit()
cur.close()
conn.close()
print(f"INDEX_OK: {total} chunks processed")
```

**Before running** the script, you must:

1. Serialize the chunks list to JSON and write it to `/tmp/tcr_chunks.json`:

```python
import json
with open("/tmp/tcr_chunks.json", "w") as f:
    json.dump({"meta": {"head_message": HEAD_MESSAGE}, "chunks": chunks}, f)
```

2. Run the script with all required env vars:

```bash
TCR_PROJECT="{project_name}" \
TCR_HEAD_HASH="{HEAD_HASH}" \
python3 /tmp/tcr_index.py
```

- Watch for `INDEX_OK` at the end to confirm success.
- If the script exits with a non-zero code: print the error output and **stop**.

Report: `"Indexed {len(chunks)} chunks ({len(chunks)*2} rows inserted)."`

---

## Step 7: Update _index_meta

**Goal:** Record the HEAD commit hash, chunk count, and embedding model in `_index_meta`.

Write this to `/tmp/tcr_update_meta.py` and run it with `python3 /tmp/tcr_update_meta.py`:

```python
import os, sys
# Load .env file if present
_env_path = os.path.join(os.getcwd(), ".env")
if not os.path.exists(_env_path):
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
import psycopg2

DATABASE_URL    = os.getenv("DATABASE_URL",    "postgresql://code_index_user:code_index_pass@localhost:5433/code_index_db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
PROJECT_NAME    = os.environ["TCR_PROJECT"]
HEAD_HASH       = os.environ["TCR_HEAD_HASH"]
CHUNK_COUNT     = int(os.environ["TCR_CHUNK_COUNT"])

UPSERT_SQL = """
INSERT INTO _index_meta (project, last_commit_hash, last_indexed_at, chunk_count, embedding_model)
VALUES (%s, %s, NOW(), %s, %s)
ON CONFLICT (project) DO UPDATE SET
    last_commit_hash = EXCLUDED.last_commit_hash,
    last_indexed_at  = NOW(),
    chunk_count      = EXCLUDED.chunk_count,
    embedding_model  = EXCLUDED.embedding_model
"""

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()
    cur.execute(UPSERT_SQL, (PROJECT_NAME, HEAD_HASH, CHUNK_COUNT, EMBEDDING_MODEL))
    conn.commit()
    conn.close()
    print("META_OK")
except Exception as e:
    print(f"META_FAIL: {e}")
    sys.exit(1)
```

Run it with:

```bash
TCR_PROJECT="{project_name}" \
TCR_HEAD_HASH="{HEAD_HASH}" \
TCR_CHUNK_COUNT="{len(chunks)}" \
python3 /tmp/tcr_update_meta.py
```

- If output is `META_OK`: continue.
- If output starts with `META_FAIL`: print the error and **stop**.

Report: `"_index_meta updated for project '{project_name}'."`

---

## Step 8: Report

**Goal:** Print a final summary to the user.

Print the following:

```
Indexing complete!

Project:          {project_name}
Table:            {project_name}
Commit:           {HEAD_HASH[:8]} — {HEAD_MESSAGE}
Files:            {len(files_to_index)}
Chunks:           {len(chunks)}
Rows in DB:       {len(chunks) * 2}  (summary + code per chunk)
Embedding model:  {EMBEDDING_MODEL}
Summary model:    {SUMMARY_MODEL}

You can now use /code-search to semantically search your code.
```

---

## Error Handling

### If any step fails, stop immediately

Do not continue to the next step if a critical error occurred. Print the error clearly and explain which step failed.

### Ollama timeout

- Summary generation (`devstral:24b`) can take 30–120 seconds per chunk on slower hardware.
- If a summary call times out after 120 seconds: use the fallback summary `"Code chunk from {file_path} lines {line_start}-{line_end}"` and continue.
- If an embedding call fails: skip that chunk entirely, log a warning, continue with the next chunk.

### DB connection failure

- If psycopg2 cannot connect: check that `DATABASE_URL` is correct and the PostgreSQL container is running.
- For the pgvector Docker setup from this project: `docker compose up -d` in the project root.

### Model not available

- If `ollama pull` fails (no internet, wrong model name): print `"Model {model_name} could not be pulled. Please run manually: ollama pull {model_name}"` and **stop**.

### Re-indexing an existing project

- Step 3 uses `CREATE TABLE IF NOT EXISTS` — safe to re-run.
- Re-running `/code-onboard` on an already-indexed project will auto-delete existing data before re-indexing. This is safe and idempotent. Use `/code-update` for incremental updates instead.

### Embedding dimension mismatch

- The schema uses `vector(768)` which matches `nomic-embed-text` output (768 dimensions).
- If you change `EMBEDDING_MODEL` to a model with different dimensions (e.g., 1024), you must drop and recreate the table: `DROP TABLE {project_name}` then re-run `/code-onboard`.
- The `embedding_model` column in `_index_meta` lets you detect this situation.
