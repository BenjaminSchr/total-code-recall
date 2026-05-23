---
name: code-onboard
description: Index a Git project into pgvector for semantic code search. Discovers files, chunks them, generates summaries via devstral, embeds both summary and code via nomic-embed-text, bulk-inserts into PostgreSQL.
---

# /code-onboard — Skill Instructions

You are executing the **code-onboard** skill. Follow these 9 steps in order. Do not skip any step. At each step, report what you are doing.

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
cur.execute(f"DELETE FROM {PROJECT_NAME}_summaries")
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
import requests
import psycopg2

DATABASE_URL    = os.getenv("DATABASE_URL",    "postgresql://code_index_user:code_index_pass@localhost:5433/code_index_db")
OLLAMA_URL      = os.getenv("OLLAMA_URL",      "http://localhost:11434")
SUMMARY_MODEL   = os.getenv("SUMMARY_MODEL",   "devstral:24b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
PROJECT_NAME    = os.environ["TCR_PROJECT"]

def generate_summary(prompt):
    """Call devstral via Ollama generate API to produce a summary."""
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
    return resp.json()["embeddings"][0]

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
        vec = get_embedding(file_summary)
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
        module_vec = get_embedding(module_summary)
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
    repo_vec = get_embedding(repo_summary)
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
