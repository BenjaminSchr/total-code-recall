---
name: tcr-update
description: Incrementally update the pgvector index for a Git project. Reads last indexed commit from _index_meta, finds changed/added/deleted/renamed files since then, removes stale chunks, re-indexes changed files, and updates _index_meta with the new HEAD hash.
---

# /tcr-update — Skill Instructions

You are executing the **tcr-update** skill. Follow these 7 steps in order. Do not skip any step. At each step, report what you are doing.

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

Also extract the current HEAD commit hash and commit message:

```bash
git log -1 --format="%H"
git log -1 --format="%s"
```

Store: `project_name`, `HEAD_HASH`, `HEAD_MESSAGE`.

Report: `"Project name: {project_name}, HEAD: {HEAD_HASH[:8]}"`

---

## Step 2: Check Index Exists

**Goal:** Confirm the project has been previously indexed and the embedding model matches.

Write this to `/tmp/tcr_check_meta.py` and run it with `python3 /tmp/tcr_check_meta.py`:

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

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()
    cur.execute(
        "SELECT last_commit_hash, embedding_model FROM _index_meta WHERE project = %s",
        (PROJECT_NAME,)
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        print(f"NOT_INDEXED")
        sys.exit(1)

    last_hash, indexed_model = row
    if indexed_model != EMBEDDING_MODEL:
        print(f"MODEL_MISMATCH:{indexed_model}")
        sys.exit(2)

    print(f"META_OK:{last_hash}")
except Exception as e:
    print(f"DB_FAIL: {e}")
    sys.exit(3)
```

Run it with:

```bash
TCR_PROJECT="{project_name}" python3 /tmp/tcr_check_meta.py
```

Parse the output:

- `NOT_INDEXED` — print `"Project '{project_name}' has not been indexed yet. Please run /tcr-onboard first."` and **stop**.
- `MODEL_MISMATCH:{old_model}` — print `"Embedding model has changed (was: {old_model}, now: {EMBEDDING_MODEL}). Please run /tcr-onboard again to fully re-index."` and **stop**.
- `DB_FAIL: ...` — print `"Database not reachable. Please check DATABASE_URL and start the DB."` and **stop**.
- `META_OK:{last_hash}` — extract `LAST_HASH` from the output and continue.

Store: `LAST_HASH`.

Report: `"Last indexed commit: {LAST_HASH[:8]}. Current HEAD: {HEAD_HASH[:8]}"`

---

## Step 3: Find Changes

**Goal:** Determine which files changed between the last indexed commit and the current HEAD.

Run this git diff command:

```bash
git diff --name-status {LAST_HASH}..HEAD
```

If the output is empty (no changes since last index): print `"No new commits since last index ({LAST_HASH[:8]}). Nothing to do."` and **stop** (this is a successful no-op, not an error).

**Categorize each line** of the output by status letter using this Python logic:

```python
added    = []   # A — new file
modified = []   # M — modified file
deleted  = []   # D — deleted file
renamed  = []   # R — renamed file (tab-separated: R100\told_path\tnew_path)

for line in git_diff_output.splitlines():
    line = line.strip()
    if not line:
        continue
    parts = line.split("\t")
    status = parts[0]

    if status == "A":
        added.append(parts[1])
    elif status == "M":
        modified.append(parts[1])
    elif status == "D":
        deleted.append(parts[1])
    elif status.startswith("R"):
        # parts[1] = old path, parts[2] = new path
        renamed.append((parts[1], parts[2]))

# Note: git diff --name-status paths are already bare-relative (e.g. "app/main.py") — no ./ stripping needed.
```

**Apply the same allowlist/blocklist as onboard.** Filter out paths that do not belong in the index:

```python
ALLOWLIST_EXTS   = {".py", ".html", ".sql", ".js", ".css", ".yaml", ".json", ".toml", ".md", ".sh"}
BLOCKLIST_DIRS   = ["venv/", "__pycache__/", ".git/", "node_modules/", "data/", ".paul/", ".env"]
BLOCKLIST_SUFFIXES = [".min.css", ".min.js", ".pyc", ".png", ".jpg", ".pdf", ".woff", ".ttf", ".ico"]

import os as _os

def is_allowed(path):
    _, ext = _os.path.splitext(path)
    if ext not in ALLOWLIST_EXTS:
        return False
    for b in BLOCKLIST_DIRS:
        if b in path:
            return False
    for s in BLOCKLIST_SUFFIXES:
        if path.endswith(s):
            return False
    return True

added    = [p for p in added    if is_allowed(p)]
modified = [p for p in modified if is_allowed(p)]
deleted  = [p for p in deleted  if is_allowed(p)]
renamed  = [(old, new) for old, new in renamed if is_allowed(old) or is_allowed(new)]
```

Build the work lists:

- `files_to_delete` = deleted paths + old paths of renamed files (rows to remove from DB)
- `files_to_reindex` = added paths + modified paths + new paths of renamed files that still exist on disk

```python
files_to_delete  = deleted + modified + [old for old, _new in renamed]
files_to_reindex = added + modified + [new for _old, new in renamed if _os.path.isfile(new)]
```

Report: `"Changes since {LAST_HASH[:8]}: {len(added)} added, {len(modified)} modified, {len(deleted)} deleted, {len(renamed)} renamed. Re-indexing {len(files_to_reindex)} files, removing {len(files_to_delete)} stale paths."`

---

## Step 4: Remove Stale Data

**Goal:** Delete all existing index rows for files that are modified, deleted, or renamed (old path).

Write this to `/tmp/tcr_delete_stale.py` and run it with `python3 /tmp/tcr_delete_stale.py`:

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
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://code_index_user:code_index_pass@localhost:5433/code_index_db")
PROJECT_NAME = os.environ["TCR_PROJECT"]

with open("/tmp/tcr_stale_paths.json", "r") as f:
    stale_paths = json.load(f)

if not stale_paths:
    print("DELETE_OK:0")
    sys.exit(0)

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()
    deleted_total = 0
    for path in stale_paths:
        cur.execute(f"DELETE FROM {PROJECT_NAME} WHERE file_path = %s", (path,))
        deleted_total += cur.rowcount
        cur.execute(f"DELETE FROM {PROJECT_NAME}_entities WHERE file_path = %s", (path,))
        # Relations auto-cascade via ON DELETE CASCADE
    conn.commit()
    conn.close()
    print(f"DELETE_OK:{deleted_total}")
except Exception as e:
    print(f"DELETE_FAIL: {e}")
    sys.exit(1)
```

**Before running**, serialize `files_to_delete` to JSON:

```python
import json
with open("/tmp/tcr_stale_paths.json", "w") as f:
    json.dump(files_to_delete, f)
```

Run it with:

```bash
TCR_PROJECT="{project_name}" python3 /tmp/tcr_delete_stale.py
```

- If output starts with `DELETE_OK:{n}`: extract the row count and continue.
- If output starts with `DELETE_FAIL`: print the error and **stop**.

Report: `"Removed {n} stale rows from '{project_name}' for {len(files_to_delete)} paths."`

---

## Step 5: Re-Index Changed Files

**Goal:** Chunk, summarize, and embed all files in `files_to_reindex`. Insert two rows per chunk (summary + code) — identical pipeline to onboard.

### 5a. Read and chunk the files

```python
CHUNK_SIZE    = int(os.getenv("CHUNK_SIZE", "50"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "15"))

chunks = []

# Get max existing chunk_id to avoid collisions
import psycopg2 as _pg
_conn = _pg.connect(os.getenv("DATABASE_URL", "postgresql://code_index_user:code_index_pass@localhost:5433/code_index_db"))
_cur = _conn.cursor()
_cur.execute(f"SELECT COALESCE(MAX(chunk_id), -1) FROM {os.environ['TCR_PROJECT']}")
chunk_id = _cur.fetchone()[0] + 1
_conn.close()

for file_path in files_to_reindex:
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"  WARN: cannot read {file_path}: {e} — skipping")
        continue

    if len(lines) < 3:
        continue  # skip files under minimum size

    start = 0
    total = len(lines)
    while start < total:
        end = min(start + CHUNK_SIZE, total)
        chunk_text = "".join(lines[start:end])
        if chunk_text.strip():
            chunks.append({
                "chunk_id":   chunk_id,
                "file_path":  file_path,
                "line_start": start + 1,
                "line_end":   end,
                "content":    chunk_text,
            })
            chunk_id += 1
        if end == total:
            break
        start += CHUNK_SIZE - CHUNK_OVERLAP
```

If `files_to_reindex` is empty (only deletions): skip to Step 6 directly.

Report: `"Created {len(chunks)} chunks from {len(files_to_reindex)} files to re-index."`

### 5b. Generate summaries + embeddings — batch INSERT

Write the chunks to `/tmp/tcr_chunks.json`, then write `/tmp/tcr_index.py` and run it:

```python
import json
with open("/tmp/tcr_chunks.json", "w") as f:
    json.dump({"meta": {"head_message": HEAD_MESSAGE}, "chunks": chunks}, f)
```

Write this to `/tmp/tcr_index.py` and run it with `python3 /tmp/tcr_index.py`:

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
import requests
import psycopg2

DATABASE_URL         = os.getenv("DATABASE_URL",         "postgresql://code_index_user:code_index_pass@localhost:5434/code_index_db")
OLLAMA_URL           = os.getenv("OLLAMA_URL",           "http://localhost:11434")
EMBEDDING_MODEL      = os.getenv("EMBEDDING_MODEL",      "nomic-embed-text")
SUMMARY_MODEL        = os.getenv("SUMMARY_MODEL",        "devstral:24b")
LLM_PROVIDER         = os.getenv("LLM_PROVIDER",         "ollama")
OPENROUTER_API_KEY   = os.getenv("OPENROUTER_API_KEY",   "")
OPENROUTER_MODEL     = os.getenv("OPENROUTER_MODEL",     "google/gemini-flash-2.0")
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
    prompt = (
        "You are a code documentation assistant. "
        "Write a concise 2-3 sentence summary of what the following code does. "
        "Focus on purpose and behavior, not syntax.\n\n"
        f"```\n{code_text[:3000]}\n```"
    )
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
        import requests
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json={
            "model": SUMMARY_MODEL,
            "prompt": prompt,
            "stream": False
        }, timeout=120)
        resp.raise_for_status()
        return resp.json()["response"].strip()

def get_embedding(text):
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

Run it with:

```bash
TCR_PROJECT="{project_name}" \
TCR_HEAD_HASH="{HEAD_HASH}" \
python3 /tmp/tcr_index.py
```

- Watch for `INDEX_OK` at the end to confirm success.
- If the script exits with a non-zero code: print the error output and **stop**.

Report: `"Re-indexed {len(chunks)} chunks ({len(chunks)*2} rows inserted)."`

### 5c. Re-parse AST for changed files

**Goal:** Update entity and relation records for files in `files_to_reindex`. Same script as onboard Step 5b — inline duplicate, accepted drift risk.

**Before running**, write the reindex file list to `/tmp/tcr_files.json`:

```python
import json
with open("/tmp/tcr_files.json", "w") as f:
    json.dump(files_to_reindex, f)
```

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

# Read file list written before this step
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

# NOTE: No full DELETE here — Step 4 already selectively deleted entities
# for changed/deleted files. We only INSERT entities for files_to_reindex.

# --- Pre-load existing entity IDs for cross-file call resolution ---
# Without this, functions in unchanged files are invisible to relation lookups
name_to_id = {}
bare_name_to_id = {}
cur.execute(f"SELECT id, name, file_path FROM {PROJECT_NAME}_entities")
for row in cur.fetchall():
    eid, ename, efp = row
    name_to_id[f"{efp}::{ename}"] = eid
    bare_name_to_id[ename] = eid

# --- INSERT new entities and update name maps ---
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

Report: `"AST re-parse complete: {entity_count} entities, {relation_count} relations extracted."` or `"AST re-parse skipped: {reason}."`

---

### 5d. Rebuild Summaries

**Goal:** Wipe all existing summaries for this project and regenerate file, module, and repo summaries using the updated index. Uses the same `tcr_build_summaries.py` as onboard Step 7.

**Delete all existing summaries** (all levels — file, module, repo) before regenerating:

Write this to `/tmp/tcr_delete_summaries.py` and run it with `python3 /tmp/tcr_delete_summaries.py`:

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

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://code_index_user:code_index_pass@localhost:5433/code_index_db")
PROJECT_NAME = os.environ["TCR_PROJECT"]

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(f"DELETE FROM {PROJECT_NAME}_summaries")
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    print(f"SUMMARIES_CLEARED:{deleted}")
except Exception as e:
    print(f"SUMMARIES_CLEAR_FAIL: {e}")
    sys.exit(1)
```

Run it with:

```bash
TCR_PROJECT="{project_name}" python3 /tmp/tcr_delete_summaries.py
```

- If output starts with `SUMMARIES_CLEARED`: continue.
- If output starts with `SUMMARIES_CLEAR_FAIL`: print the error and **stop**.

**Then regenerate all summaries** by writing and running the same `tcr_build_summaries.py` from onboard Step 7 (copy the full script verbatim, including the `generate_summary` and `get_embedding` helper functions):

```bash
TCR_PROJECT="{project_name}" python3 /tmp/tcr_build_summaries.py
```

- If output ends with `SUMMARIES_OK`: continue.
- If the script exits with a non-zero code: print the error and **stop**.

Report: `"Summaries rebuilt: {file_count} file, {module_count} module, 1 repo summaries generated."`

---

## Step 6: Update _index_meta

**Goal:** Update `_index_meta` with the new HEAD commit hash and the updated total chunk count.

First, calculate the current total chunk count for this project (existing rows plus newly inserted):

```bash
# Query the DB to get the current row count, divided by 2 (two rows per chunk)
```

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

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()

    # Count distinct chunk_ids to get the true chunk count
    cur.execute(f"SELECT COUNT(DISTINCT chunk_id) FROM {PROJECT_NAME}")
    chunk_count = cur.fetchone()[0]

    cur.execute("""
        INSERT INTO _index_meta (project, last_commit_hash, last_indexed_at, chunk_count, embedding_model)
        VALUES (%s, %s, NOW(), %s, %s)
        ON CONFLICT (project) DO UPDATE SET
            last_commit_hash = EXCLUDED.last_commit_hash,
            last_indexed_at  = NOW(),
            chunk_count      = EXCLUDED.chunk_count,
            embedding_model  = EXCLUDED.embedding_model
    """, (PROJECT_NAME, HEAD_HASH, chunk_count, EMBEDDING_MODEL))

    conn.commit()
    conn.close()
    print(f"META_OK:{chunk_count}")
except Exception as e:
    print(f"META_FAIL: {e}")
    sys.exit(1)
```

Run it with:

```bash
TCR_PROJECT="{project_name}" \
TCR_HEAD_HASH="{HEAD_HASH}" \
python3 /tmp/tcr_update_meta.py
```

- If output starts with `META_OK:{chunk_count}`: extract `chunk_count` and continue.
- If output starts with `META_FAIL`: print the error and **stop**.

Report: `"_index_meta updated for project '{project_name}': HEAD={HEAD_HASH[:8]}, total chunks={chunk_count}"`

---

## Step 7: Report

**Goal:** Print a final summary to the user.

Print the following:

```
Update complete!

Project:              {project_name}
Previous index:       {LAST_HASH[:8]}
Current HEAD:         {HEAD_HASH[:8]} — {HEAD_MESSAGE}
Files re-indexed:     {len(files_to_reindex)}
Files removed:        {len(files_to_delete)}
New chunks:           {len(chunks)}
Total chunks in DB:   {chunk_count}
Embedding model:      {EMBEDDING_MODEL}

Commits processed: from {LAST_HASH[:8]} to {HEAD_HASH[:8]}
Next step: use /tcr-search to semantically search your code.
```

---

## Error Handling

### If any step fails, stop immediately

Do not continue to the next step if a critical error occurred. Print the error clearly and explain which step failed.

### Project not yet indexed

- If Step 2 returns `NOT_INDEXED`: instruct the user to run `/tcr-onboard` first. Do not attempt to create the table or index — that is the onboard skill's responsibility.

### Embedding model mismatch

- If Step 2 returns `MODEL_MISMATCH`: the current `EMBEDDING_MODEL` env var differs from what was used when the index was built. Vectors are incomparable across models. The user must run `/tcr-onboard` to rebuild the index from scratch with the new model.

### No changes since last index

- If Step 3 finds no diff output: this is a successful no-op. Print the message and stop cleanly — do not treat it as an error.

### Ollama timeout

- Summary generation (`devstral:24b`) can take 30–120 seconds per chunk on slower hardware.
- If a summary call times out: use the fallback summary `"Code chunk from {file_path} lines {line_start}-{line_end}"` and continue.
- If an embedding call fails: skip that chunk entirely, log a warning, continue with the next chunk.

### DB connection failure

- If psycopg2 cannot connect: check that `DATABASE_URL` is correct and the PostgreSQL container is running.
- For the pgvector Docker setup from this project: `docker compose up -d` in the project root.

### Renamed files

- For a renamed file: the old path is deleted from the DB (Step 4), the new path is re-indexed (Step 5).
- If the rename target does not exist on disk (e.g., the rename was later reverted): skip it silently.

### Deleted files with no existing index rows

- `DELETE FROM {project} WHERE file_path = %s` is a no-op if no rows exist for that path. This is safe — the DB will report 0 rows affected, which is not an error.
