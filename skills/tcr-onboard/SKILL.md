---
name: tcr-onboard
description: Index a Git project into pgvector for semantic code search. Discovers files, chunks them, generates summaries via devstral, embeds both summary and code via nomic-embed-text, bulk-inserts into PostgreSQL.
---

# /tcr-onboard — Skill Instructions

You are executing the **tcr-onboard** skill. Follow these 9 steps in order. Do not skip any step. At each step, report what you are doing.

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
import json
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
# --- Config Loader (3-layer) ---
# Layer 1: project .env (already loaded above)
# Layer 2: global config.json
_GLOBAL_CONFIG = {}
_CONFIG_PATH = os.path.expanduser("~/.config/total-code-recall/config.json")
if os.path.exists(_CONFIG_PATH):
    with open(_CONFIG_PATH) as _f:
        _GLOBAL_CONFIG = json.load(_f)

def _cfg(env_key, config_key, default):
    """Priority: env var > global config > default"""
    return os.environ.get(env_key) or _GLOBAL_CONFIG.get(config_key) or default

DATABASE_URL      = _cfg("DATABASE_URL",    "database_url",         "postgresql://code_index_user:code_index_pass@localhost:5434/code_index_db")
OLLAMA_URL        = _cfg("OLLAMA_URL",      "ollama_url",           "http://localhost:11434")
EMBEDDING_MODEL   = _cfg("EMBEDDING_MODEL", "embedding_model",      "nomic-embed-text")
SUMMARY_MODEL     = _cfg("SUMMARY_MODEL",   "ollama_summary_model", "devstral:24b")
CHUNK_SIZE        = int(_cfg("CHUNK_SIZE",  "chunk_size",           "50"))
CHUNK_OVERLAP     = int(_cfg("CHUNK_OVERLAP","chunk_overlap",       "15"))
LLM_PROVIDER         = _cfg("LLM_PROVIDER",         "llm_provider",          "ollama")
OPENROUTER_API_KEY   = _cfg("OPENROUTER_API_KEY",    "openrouter_api_key",    "")
OPENROUTER_MODEL     = _cfg("OPENROUTER_MODEL",      "openrouter_model",      "google/gemini-flash-2.0")
PARALLEL_WORKERS     = int(_cfg("PARALLEL_WORKERS",  "parallel_workers",      "10"))
EMBEDDING_PROVIDER   = _cfg("EMBEDDING_PROVIDER",    "embedding_provider",    "ollama")
DB_PROVIDER          = _cfg("DB_PROVIDER",           "db_provider",           "local")
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
if project_name and project_name[0].isdigit():
    project_name = "p_" + project_name
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

**Goal:** Confirm required services are running and the DB is reachable.

### 2a. Check Ollama (skip if using OpenRouter for both LLM and Embedding)

**Only run this check if `LLM_PROVIDER == "ollama"` OR `EMBEDDING_PROVIDER == "ollama"`.**
If both providers are set to `"openrouter"`, skip Steps 2a and 2b entirely.

```bash
curl -s {OLLAMA_URL}/api/tags
```

- If this fails: print `"Ollama not reachable at {OLLAMA_URL}. Please start Ollama."` and **stop**.
- Parse the JSON response and check if models needed for local providers are listed under `"models"[].name`:
  - If `EMBEDDING_PROVIDER == "ollama"`: check `EMBEDDING_MODEL`
  - If `LLM_PROVIDER == "ollama"`: check `SUMMARY_MODEL`

### 2b. Pull missing models (Ollama only)

For each Ollama model that is NOT in the tags response, run:

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
# Layer 2: supplement from global config.json (fills in what .env didn't set)
try:
    import json as _j2
    with open(os.path.expanduser("~/.config/total-code-recall/config.json")) as _f2:
        _gc = _j2.load(_f2)
    for _k2, _v2 in [
        ("EMBEDDING_PROVIDER", "embedding_provider"),
        ("OPENROUTER_API_KEY",  "openrouter_api_key"),
        ("OPENROUTER_MODEL",    "openrouter_model"),
        ("LLM_PROVIDER",        "llm_provider"),
        ("DATABASE_URL",        "database_url"),
        ("OLLAMA_URL",          "ollama_url"),
        ("EMBEDDING_MODEL",     "embedding_model"),
        ("SUMMARY_MODEL",       "ollama_summary_model"),
    ]:
        if not os.environ.get(_k2) and _v2 in _gc:
            os.environ[_k2] = str(_gc[_v2])
except Exception:
    pass  # config.json missing or malformed — use env/defaults
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

### 2d. Sanity Check — Existing Index

**Goal:** Detect if this project is already indexed and warn the user before any data is deleted.

Write this to `/tmp/tcr_check_existing.py` and run it with `TCR_PROJECT={project_name} python3 /tmp/tcr_check_existing.py`:

```python
import os, sys, json

# Layer 2: supplement from global config.json
try:
    import json as _j2
    with open(os.path.expanduser("~/.config/total-code-recall/config.json")) as _f2:
        _gc = _j2.load(_f2)
    for _k2, _v2 in [
        ("DATABASE_URL", "database_url"),
    ]:
        if not os.environ.get(_k2) and _v2 in _gc:
            os.environ[_k2] = str(_gc[_v2])
except Exception:
    pass

import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://code_index_user:code_index_pass@localhost:5433/code_index_db")
PROJECT_NAME = os.environ.get("TCR_PROJECT", "")

if not PROJECT_NAME:
    print("CHECK_FAIL: TCR_PROJECT not set")
    sys.exit(1)

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        "SELECT chunk_count, last_indexed_at, last_commit_hash, embedding_model FROM _index_meta WHERE project = %s",
        (PROJECT_NAME,)
    )
    row = cur.fetchone()
    conn.close()
    if row:
        chunk_count, last_indexed_at, last_commit_hash, embedding_model = row
        short_hash = last_commit_hash[:8] if last_commit_hash else "unknown"
        print(f"EXISTING_INDEX chunks={chunk_count} last_indexed={last_indexed_at} commit={short_hash} model={embedding_model}")
    else:
        print("NO_EXISTING_INDEX")
except Exception as e:
    print(f"CHECK_FAIL: {e}")
    sys.exit(1)
```

**Parse the output:**

- If `NO_EXISTING_INDEX`: continue to Step 3. No warning needed.
- If `CHECK_FAIL`: print the error and **stop**.
- If `EXISTING_INDEX chunks=... last_indexed=... commit=... model=...`:
  - **STOP and display this warning to the user:**
    ```
    ⚠️  WARNING: Project '{project_name}' is already indexed.

       Chunks indexed:  {chunk_count}
       Last indexed:    {last_indexed_at}
       Commit:          {commit}
       Embedding model: {embedding_model}

    Re-running /tcr-onboard will DELETE all existing index data and rebuild
    from scratch. This cannot be undone.

    Use /tcr-update for incremental updates instead.

    Type YES to confirm full re-index, or anything else to cancel:
    ```
  - Wait for the user's response.
  - If the user types exactly `YES` (case-sensitive): print `"Re-index confirmed. Proceeding..."` and continue to Step 3.
  - For any other response (including empty): print `"Re-index cancelled. Run /tcr-update to update incrementally."` and **stop immediately**.

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
# Layer 2: supplement from global config.json (fills in what .env didn't set)
try:
    import json as _j2
    with open(os.path.expanduser("~/.config/total-code-recall/config.json")) as _f2:
        _gc = _j2.load(_f2)
    for _k2, _v2 in [
        ("EMBEDDING_PROVIDER", "embedding_provider"),
        ("OPENROUTER_API_KEY",  "openrouter_api_key"),
        ("OPENROUTER_MODEL",    "openrouter_model"),
        ("LLM_PROVIDER",        "llm_provider"),
        ("DATABASE_URL",        "database_url"),
        ("OLLAMA_URL",          "ollama_url"),
        ("EMBEDDING_MODEL",     "embedding_model"),
        ("SUMMARY_MODEL",       "ollama_summary_model"),
    ]:
        if not os.environ.get(_k2) and _v2 in _gc:
            os.environ[_k2] = str(_gc[_v2])
except Exception:
    pass  # config.json missing or malformed — use env/defaults
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

Export the file list for use by the AST parsing step:

```python
import json
with open("/tmp/tcr_files.json", "w") as f:
    json.dump([fp for fp, _ in files_to_index], f)
```

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

## Step 5b: Extract Code Structure (AST)

**Goal:** Parse Python files with tree-sitter to extract entities (file, class, function, method, import) and relations (contains, calls, imports) into the project entity/relation tables. **Non-blocking** — if tree-sitter is not installed, this step is skipped with a warning and the onboard continues normally.

Write this entire script to `/tmp/tcr_parse_ast.py` and run it with `TCR_PROJECT="{project_name}" python3 /tmp/tcr_parse_ast.py`:

```python
import os, sys, json

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
# Layer 2: supplement from global config.json (fills in what .env didn't set)
try:
    import json as _j2
    with open(os.path.expanduser("~/.config/total-code-recall/config.json")) as _f2:
        _gc = _j2.load(_f2)
    for _k2, _v2 in [
        ("EMBEDDING_PROVIDER", "embedding_provider"),
        ("OPENROUTER_API_KEY",  "openrouter_api_key"),
        ("OPENROUTER_MODEL",    "openrouter_model"),
        ("LLM_PROVIDER",        "llm_provider"),
        ("DATABASE_URL",        "database_url"),
        ("OLLAMA_URL",          "ollama_url"),
        ("EMBEDDING_MODEL",     "embedding_model"),
        ("SUMMARY_MODEL",       "ollama_summary_model"),
    ]:
        if not os.environ.get(_k2) and _v2 in _gc:
            os.environ[_k2] = str(_gc[_v2])
except Exception:
    pass  # config.json missing or malformed — use env/defaults

try:
    from tree_sitter_languages import get_parser
except ImportError:
    print("AST_SKIP: tree-sitter not installed. Run: pip install tree-sitter tree-sitter-languages")
    sys.exit(0)

import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://code_index_user:code_index_pass@localhost:5433/code_index_db")
PROJECT_NAME = os.environ["TCR_PROJECT"]

# Read file list written by Step 4
with open("/tmp/tcr_files.json", "r") as f:
    all_files = json.load(f)

py_files = [fp for fp in all_files if fp.endswith(".py")]
if not py_files:
    print("AST_SKIP: no Python files found")
    sys.exit(0)

for fp in all_files:
    if not fp.endswith(".py"):
        print(f"AST_SKIP_FILE: {fp} (Phase 1 = Python only)")

parser = get_parser("python")

def get_node_text(node, source_bytes):
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

def get_name_from_node(node, source_bytes):
    """Extract the identifier name from a definition node."""
    for child in node.children:
        if child.type == "identifier":
            return get_node_text(child, source_bytes)
    return None

def walk_tree(node):
    """Yield all nodes in the tree depth-first."""
    yield node
    for child in node.children:
        yield from walk_tree(child)

# --- Pass 1: collect entities ---
entities = []  # list of dicts: type, name, file_path, line_start, line_end, parent_name

for fp in py_files:
    try:
        with open(fp, "rb") as f:
            source_bytes = f.read()
    except Exception as e:
        print(f"AST_WARN: cannot read {fp}: {e}")
        continue

    total_lines = source_bytes.count(b"\n") + 1
    entities.append({
        "type": "file",
        "name": fp,
        "file_path": fp,
        "line_start": 1,
        "line_end": total_lines,
        "parent_name": None,
        "parent_type": None,
    })

    tree = parser.parse(source_bytes)
    root = tree.root_node

    for node in walk_tree(root):
        if node.type in ("class_definition", "function_definition"):
            name = get_name_from_node(node, source_bytes)
            if not name:
                continue
            parent = node.parent
            if node.type == "function_definition" and parent and parent.type == "class_definition":
                entity_type = "method"
                parent_name = get_name_from_node(parent, source_bytes)
                parent_type = "class"
            elif node.type == "class_definition":
                entity_type = "class"
                parent_name = fp  # file is the parent
                parent_type = "file"
            else:
                entity_type = "function"
                parent_name = fp  # file is the parent
                parent_type = "file"

            entities.append({
                "type": entity_type,
                "name": name,
                "file_path": fp,
                "line_start": node.start_point[0] + 1,  # 1-based
                "line_end": node.end_point[0] + 1,
                "parent_name": parent_name,
                "parent_type": parent_type,
            })

        elif node.type in ("import_statement", "import_from_statement"):
            # Use the raw text of the import statement as the name
            name = get_node_text(node, source_bytes).split("\n")[0].strip()
            entities.append({
                "type": "import",
                "name": name,
                "file_path": fp,
                "line_start": node.start_point[0] + 1,
                "line_end": node.end_point[0] + 1,
                "parent_name": fp,
                "parent_type": "file",
            })

# --- Connect to DB ---
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Clear existing entities (CASCADE deletes relations)
cur.execute(f"DELETE FROM {PROJECT_NAME}_entities")
conn.commit()

# --- INSERT entities and collect name->id map ---
# Key format: "file_path::name" to avoid collisions (e.g. multiple __init__ functions)
name_to_id = {}  # "file_path::entity_name" -> db id
# Also keep a bare name lookup for cross-file call resolution
bare_name_to_id = {}  # "entity_name" -> db id (last wins, best-effort)

INSERT_ENTITY = f"""
INSERT INTO {PROJECT_NAME}_entities (type, name, file_path, line_start, line_end, parent_id)
VALUES (%s, %s, %s, %s, %s, %s)
RETURNING id
"""

for ent in entities:
    parent_key = f'{ent["file_path"]}::{ent["parent_name"]}' if ent["parent_name"] else None
    parent_id = name_to_id.get(parent_key) if parent_key else None
    cur.execute(INSERT_ENTITY, (
        ent["type"], ent["name"], ent["file_path"],
        ent["line_start"], ent["line_end"], parent_id
    ))
    row = cur.fetchall()
    ent_id = row[0][0]
    qualified_key = f'{ent["file_path"]}::{ent["name"]}'
    name_to_id[qualified_key] = ent_id
    bare_name_to_id[ent["name"]] = ent_id

conn.commit()
entity_count = len(entities)

# --- Pass 2: extract relations ---
relations = []  # list of (from_name, to_name, rel_type)

INSERT_RELATION = f"""
INSERT INTO {PROJECT_NAME}_relations (from_id, to_id, type)
VALUES (%s, %s, %s)
"""

relation_count = 0

# contains relations (already encoded via parent_id, also insert explicit relation rows)
for ent in entities:
    if ent["parent_name"] and ent["type"] in ("class", "function", "method", "import"):
        parent_key = f'{ent["file_path"]}::{ent["parent_name"]}'
        child_key = f'{ent["file_path"]}::{ent["name"]}'
        from_id = name_to_id.get(parent_key)
        to_id = name_to_id.get(child_key)
        if from_id and to_id:
            cur.execute(INSERT_RELATION, (from_id, to_id, "contains"))
            relation_count += 1

# calls and imports relations from AST
for fp in py_files:
    try:
        with open(fp, "rb") as f:
            source_bytes = f.read()
    except Exception:
        continue

    tree = parser.parse(source_bytes)

    for node in walk_tree(tree.root_node):
        # calls: function call nodes
        if node.type == "call":
            # get the function name from the first child (attribute or identifier)
            func_node = node.child_by_field_name("function")
            if func_node:
                if func_node.type == "identifier":
                    called_name = get_node_text(func_node, source_bytes)
                elif func_node.type == "attribute":
                    # e.g. obj.method — take the attribute name
                    attr = func_node.child_by_field_name("attribute")
                    called_name = get_node_text(attr, source_bytes) if attr else None
                else:
                    called_name = None

                if called_name and called_name in bare_name_to_id:
                    # find the enclosing function/method
                    caller = node.parent
                    while caller and caller.type not in ("function_definition",):
                        caller = caller.parent
                    if caller:
                        caller_name = get_name_from_node(caller, source_bytes)
                        from_id = bare_name_to_id.get(caller_name)
                        to_id = bare_name_to_id.get(called_name)
                        if from_id and to_id and from_id != to_id:
                            cur.execute(INSERT_RELATION, (from_id, to_id, "calls"))
                            relation_count += 1

        # imports relations
        elif node.type in ("import_statement", "import_from_statement"):
            import_text = get_node_text(node, source_bytes).split("\n")[0].strip()
            from_id = bare_name_to_id.get(import_text)
            if from_id:
                # match imported names against known entities
                for child in walk_tree(node):
                    if child.type == "dotted_name" or child.type == "identifier":
                        imported = get_node_text(child, source_bytes)
                        to_id = bare_name_to_id.get(imported)
                        if to_id and to_id != from_id:
                            cur.execute(INSERT_RELATION, (from_id, to_id, "imports"))
                            relation_count += 1
                            break  # one imports relation per import statement is enough

conn.commit()
cur.close()
conn.close()

print(f"AST_OK: {entity_count} entities, {relation_count} relations")
```

Run it with:

```bash
TCR_PROJECT="{project_name}" python3 /tmp/tcr_parse_ast.py
```

- If output starts with `AST_OK`: continue normally.
- If output starts with `AST_SKIP`: log the skip reason and continue — this step is **non-blocking**.
- If output starts with `AST_WARN`: log the warning and continue.
- If the script exits with a non-zero code: print the error and **stop**.

Report: `"AST parsing complete: {entity_count} entities, {relation_count} relations extracted."` or `"AST parsing skipped: {reason}."`

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
# Layer 2: supplement from global config.json (fills in what .env didn't set)
try:
    import json as _j2
    with open(os.path.expanduser("~/.config/total-code-recall/config.json")) as _f2:
        _gc = _j2.load(_f2)
    for _k2, _v2 in [
        ("EMBEDDING_PROVIDER", "embedding_provider"),
        ("OPENROUTER_API_KEY",  "openrouter_api_key"),
        ("OPENROUTER_MODEL",    "openrouter_model"),
        ("LLM_PROVIDER",        "llm_provider"),
        ("DATABASE_URL",        "database_url"),
        ("OLLAMA_URL",          "ollama_url"),
        ("EMBEDDING_MODEL",     "embedding_model"),
        ("SUMMARY_MODEL",       "ollama_summary_model"),
    ]:
        if not os.environ.get(_k2) and _v2 in _gc:
            os.environ[_k2] = str(_gc[_v2])
except Exception:
    pass  # config.json missing or malformed — use env/defaults
import requests
import psycopg2

DATABASE_URL         = os.getenv("DATABASE_URL",         "postgresql://code_index_user:code_index_pass@localhost:5434/code_index_db")
OLLAMA_URL           = os.getenv("OLLAMA_URL",           "http://localhost:11434")
EMBEDDING_MODEL      = os.getenv("EMBEDDING_MODEL",      "nomic-embed-text")
SUMMARY_MODEL        = os.getenv("SUMMARY_MODEL",        "devstral:24b")
LLM_PROVIDER         = os.getenv("LLM_PROVIDER",         "ollama")
OPENROUTER_API_KEY   = os.getenv("OPENROUTER_API_KEY",   "")
OPENROUTER_MODEL     = os.getenv("OPENROUTER_MODEL",     "google/gemini-flash-2.0")
EMBEDDING_PROVIDER   = os.getenv("EMBEDDING_PROVIDER",   "ollama")
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

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def _call_openrouter_with_retry(prompt, max_retries=5):
    """Call OpenRouter with exponential backoff on 429."""
    import requests
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200
                },
                timeout=30
            )
            if resp.status_code == 429:
                wait = (2 ** attempt) + 1
                print(f"  Rate limited, waiting {wait}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("OpenRouter: max retries exceeded")

def generate_summary(code_text):
    """Generate a summary via OpenRouter or Ollama depending on LLM_PROVIDER."""
    prompt = (
        "You are a code documentation assistant. "
        "Write a concise 2-3 sentence summary of what the following code does. "
        "Focus on purpose and behavior, not syntax.\n\n"
        f"```\n{code_text[:3000]}\n```"
    )
    if LLM_PROVIDER == "openrouter":
        return _call_openrouter_with_retry(prompt)
    else:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": SUMMARY_MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()

def embed_text(text):
    """Generate embedding via configured provider."""
    if EMBEDDING_PROVIDER == "openrouter":
        import requests
        resp = requests.post(
            "https://openrouter.ai/api/v1/embeddings",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": EMBEDDING_MODEL,
                "input": text
            },
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]
    else:
        # Ollama (existing logic)
        import requests
        resp = requests.post(f"{OLLAMA_URL}/api/embeddings", json={
            "model": EMBEDDING_MODEL,
            "prompt": text
        }, timeout=60)
        resp.raise_for_status()
        return resp.json()["embedding"]

conn = psycopg2.connect(DATABASE_URL)
cur  = conn.cursor()

# Clear existing data for idempotent re-onboard
cur.execute(f"DELETE FROM {PROJECT_NAME}")
cur.execute(f"DELETE FROM {PROJECT_NAME}_summaries")
conn.commit()
print(f"CLEARED: Removed existing data from {PROJECT_NAME}")

total = len(chunks)

# --- Pre-fetch all summaries (parallel for OpenRouter, sequential for Ollama) ---
if LLM_PROVIDER == "openrouter":
    def _process_chunk(chunk):
        prompt = (
            "You are a code documentation assistant. "
            "Write a concise 2-3 sentence summary of what the following code does. "
            "Focus on purpose and behavior, not syntax.\n\n"
            f"```\n{chunk['content'][:3000]}\n```"
        )
        summary = _call_openrouter_with_retry(prompt)
        return chunk["chunk_id"], summary

    summaries = {}
    with ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as executor:
        futures = {executor.submit(_process_chunk, c): c for c in chunks}
        for i, future in enumerate(as_completed(futures), 1):
            try:
                chunk_id, summary = future.result()
                summaries[chunk_id] = summary
            except Exception as e:
                c = futures[future]
                print(f"    WARN: summary failed for chunk {c['chunk_id']}: {e} — using fallback")
                summaries[c["chunk_id"]] = f"Code chunk from {c['file_path']} lines {c['line_start']}-{c['line_end']}"
            if i % 10 == 0:
                print(f"  {i}/{total} summaries generated")
else:
    # Ollama: sequential (unchanged)
    summaries = {}
    for chunk in chunks:
        try:
            summaries[chunk["chunk_id"]] = generate_summary(chunk["content"])
        except Exception as e:
            print(f"    WARN: summary failed: {e} — using fallback")
            summaries[chunk["chunk_id"]] = f"Code chunk from {chunk['file_path']} lines {chunk['line_start']}-{chunk['line_end']}"

for i, chunk in enumerate(chunks):
    print(f"  [{i+1}/{total}] chunk_id={chunk['chunk_id']} {chunk['file_path']} lines {chunk['line_start']}-{chunk['line_end']}", flush=True)

    summary_text = summaries.get(chunk["chunk_id"], f"Code chunk from {chunk['file_path']} lines {chunk['line_start']}-{chunk['line_end']}")

    # --- Embeddings ---
    try:
        summary_vec = embed_text(summary_text)
    except Exception as e:
        print(f"    WARN: summary embedding failed: {e} — skipping chunk")
        continue

    try:
        code_vec = embed_text(chunk["content"])
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

## Step 7: Generate Hierarchical Summaries

**Goal:** For each indexed file, aggregate its chunk-level summaries into a file-level summary (via devstral), embed it, and store it in the `_summaries` table with `level='file'`. Then aggregate file summaries per directory into module-level summaries (`level='module'`), and aggregate those into a single repo-level summary (`level='repo'`).

Write this entire script to `/tmp/tcr_build_summaries.py` and run it with `python3 /tmp/tcr_build_summaries.py`:

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
# Layer 2: supplement from global config.json (fills in what .env didn't set)
try:
    import json as _j2
    with open(os.path.expanduser("~/.config/total-code-recall/config.json")) as _f2:
        _gc = _j2.load(_f2)
    for _k2, _v2 in [
        ("EMBEDDING_PROVIDER", "embedding_provider"),
        ("OPENROUTER_API_KEY",  "openrouter_api_key"),
        ("OPENROUTER_MODEL",    "openrouter_model"),
        ("LLM_PROVIDER",        "llm_provider"),
        ("DATABASE_URL",        "database_url"),
        ("OLLAMA_URL",          "ollama_url"),
        ("EMBEDDING_MODEL",     "embedding_model"),
        ("SUMMARY_MODEL",       "ollama_summary_model"),
    ]:
        if not os.environ.get(_k2) and _v2 in _gc:
            os.environ[_k2] = str(_gc[_v2])
except Exception:
    pass  # config.json missing or malformed — use env/defaults
import requests
import psycopg2

DATABASE_URL    = os.getenv("DATABASE_URL",    "postgresql://code_index_user:code_index_pass@localhost:5433/code_index_db")
OLLAMA_URL      = os.getenv("OLLAMA_URL",      "http://localhost:11434")
SUMMARY_MODEL   = os.getenv("SUMMARY_MODEL",   "devstral:24b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
PROJECT_NAME    = os.environ["TCR_PROJECT"]
LLM_PROVIDER         = os.getenv("LLM_PROVIDER",       "ollama")
OPENROUTER_API_KEY   = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL     = os.getenv("OPENROUTER_MODEL",   "google/gemini-flash-2.0")
EMBEDDING_PROVIDER   = os.getenv("EMBEDDING_PROVIDER", "ollama")

def generate_summary(prompt):
    if LLM_PROVIDER == "openrouter":
        import requests
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200
            },
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    else:
        # Ollama (existing logic)
        import requests
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json={
            "model": SUMMARY_MODEL,
            "prompt": prompt,
            "stream": False
        }, timeout=120)
        resp.raise_for_status()
        return resp.json()["response"].strip()

def embed_text(text):
    """Generate embedding via configured provider."""
    if EMBEDDING_PROVIDER == "openrouter":
        import requests
        resp = requests.post(
            "https://openrouter.ai/api/v1/embeddings",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": EMBEDDING_MODEL,
                "input": text
            },
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]
    else:
        # Ollama (existing logic)
        import requests
        resp = requests.post(f"{OLLAMA_URL}/api/embeddings", json={
            "model": EMBEDDING_MODEL,
            "prompt": text
        }, timeout=60)
        resp.raise_for_status()
        return resp.json()["embedding"]

conn = psycopg2.connect(DATABASE_URL)
cur  = conn.cursor()

# Idempotency: clear existing summaries before regenerating
cur.execute(f"DELETE FROM {PROJECT_NAME}_summaries")
conn.commit()

# Get all distinct file paths that have chunk summaries
cur.execute(f"SELECT DISTINCT file_path FROM {PROJECT_NAME} WHERE type = 'summary'")
file_paths = [row[0] for row in cur.fetchall()]

# --- File summaries ---
file_count = 0
for file_path in file_paths:
    # Collect all chunk summaries for this file, ordered by line_start
    cur.execute(
        f"SELECT content FROM {PROJECT_NAME} WHERE file_path = %s AND type = 'summary' ORDER BY line_start",
        (file_path,)
    )
    chunk_summaries = [row[0] for row in cur.fetchall()]
    if not chunk_summaries:
        continue

    concatenated = "\n\n".join(chunk_summaries)

    # Generate file-level summary via devstral
    try:
        file_summary = generate_summary(
            f"Summarize this file's purpose and key components in 2-3 sentences:\n\n{concatenated}"
        )
    except Exception as e:
        print(f"  WARN: summary failed for {file_path}: {e} — skipping")
        continue

    # Embed the file summary
    try:
        vec = embed_text(file_summary)
    except Exception as e:
        print(f"  WARN: embedding failed for {file_path}: {e} — skipping")
        continue

    vec_str = "[" + ",".join(str(x) for x in vec) + "]"

    cur.execute(
        f"INSERT INTO {PROJECT_NAME}_summaries (level, scope, content, embedding) VALUES ('file', %s, %s, %s::vector)",
        (file_path, file_summary, vec_str)
    )
    file_count += 1
    print(f"  [file {file_count}] {file_path}", flush=True)

# --- Module summaries (one per directory with 2+ indexed files) ---
dirs = {}
for fp in file_paths:
    d = os.path.dirname(fp) or "."
    dirs.setdefault(d, []).append(fp)

module_count = 0
for dir_path, dir_files in dirs.items():
    if len(dir_files) < 2:
        continue
    placeholders = ",".join(["%s"] * len(dir_files))
    cur.execute(
        f"SELECT content FROM {PROJECT_NAME}_summaries WHERE level='file' AND scope IN ({placeholders})",
        dir_files
    )
    file_sums = [r[0] for r in cur.fetchall()]
    if not file_sums:
        continue
    try:
        module_summary = generate_summary(
            f"Summarize this module (directory: {dir_path}). These are its files:\n\n" + "\n\n".join(file_sums)
        )
    except Exception as e:
        print(f"  WARN: module summary failed for {dir_path}: {e} — skipping")
        continue
    try:
        module_vec = embed_text(module_summary)
    except Exception as e:
        print(f"  WARN: module embedding failed for {dir_path}: {e} — skipping")
        continue
    module_vec_str = "[" + ",".join(str(x) for x in module_vec) + "]"
    cur.execute(
        f"INSERT INTO {PROJECT_NAME}_summaries (level, scope, content, embedding) VALUES ('module', %s, %s, %s::vector)",
        (dir_path, module_summary, module_vec_str)
    )
    module_count += 1
    print(f"  [module {module_count}] {dir_path}", flush=True)

# --- Repo summary ---
cur.execute(
    f"SELECT content FROM {PROJECT_NAME}_summaries WHERE level IN ('module', 'file') ORDER BY level DESC"
)
all_sums = [r[0] for r in cur.fetchall()][:20]  # cap at 20 to fit devstral context
try:
    repo_summary = generate_summary(
        "Summarize this entire codebase in 3-5 sentences:\n\n" + "\n\n".join(all_sums)
    )
except Exception as e:
    print(f"  WARN: repo summary failed: {e} — using fallback")
    repo_summary = f"Codebase index for project {PROJECT_NAME}."
try:
    repo_vec = embed_text(repo_summary)
except Exception as e:
    print(f"  WARN: repo embedding failed: {e} — skipping repo summary")
    repo_vec = None

if repo_vec is not None:
    repo_vec_str = "[" + ",".join(str(x) for x in repo_vec) + "]"
    cur.execute(
        f"INSERT INTO {PROJECT_NAME}_summaries (level, scope, content, embedding) VALUES ('repo', %s, %s, %s::vector)",
        (PROJECT_NAME, repo_summary, repo_vec_str)
    )

conn.commit()
cur.close()
conn.close()
print(f"SUMMARIES_OK: {file_count} file, {module_count} module, 1 repo summaries generated")
```

Run it with:

```bash
TCR_PROJECT="{project_name}" python3 /tmp/tcr_build_summaries.py
```

- If output ends with `SUMMARIES_OK`: continue.
- If the script exits with a non-zero code: print the error and **stop**.

Report: `"Generated {file_count} file, {module_count} module, and 1 repo summary in {project_name}_summaries."`

---

## Step 8: Update _index_meta

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
# Layer 2: supplement from global config.json (fills in what .env didn't set)
try:
    import json as _j2
    with open(os.path.expanduser("~/.config/total-code-recall/config.json")) as _f2:
        _gc = _j2.load(_f2)
    for _k2, _v2 in [
        ("EMBEDDING_PROVIDER", "embedding_provider"),
        ("OPENROUTER_API_KEY",  "openrouter_api_key"),
        ("OPENROUTER_MODEL",    "openrouter_model"),
        ("LLM_PROVIDER",        "llm_provider"),
        ("DATABASE_URL",        "database_url"),
        ("OLLAMA_URL",          "ollama_url"),
        ("EMBEDDING_MODEL",     "embedding_model"),
        ("SUMMARY_MODEL",       "ollama_summary_model"),
    ]:
        if not os.environ.get(_k2) and _v2 in _gc:
            os.environ[_k2] = str(_gc[_v2])
except Exception:
    pass  # config.json missing or malformed — use env/defaults
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

## Step 9: Report

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

You can now use /tcr-search to semantically search your code.
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
- Re-running `/tcr-onboard` on an already-indexed project will auto-delete existing data before re-indexing. This is safe and idempotent. Use `/tcr-update` for incremental updates instead.

### Embedding dimension mismatch

- The schema uses `vector(768)` which matches `nomic-embed-text` output (768 dimensions).
- If you change `EMBEDDING_MODEL` to a model with different dimensions (e.g., 1024), you must drop and recreate the table: `DROP TABLE {project_name}` then re-run `/tcr-onboard`.
- The `embedding_model` column in `_index_meta` lets you detect this situation.
