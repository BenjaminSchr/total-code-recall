---
name: tcr-search
description: Semantically search an indexed Git project. Embeds the user query via Ollama, runs a vector similarity search with dedup against the pgvector table, and returns the top 10 most relevant code chunks with file, lines, type, score, and full content.
---

# /tcr-search — Skill Instructions

You are executing the **tcr-search** skill. Follow these 5 steps in order. Do not skip any step. At each step, report what you are doing.

Usage: `/tcr-search <query>`

---

## Config

Read configuration from environment variables. Use these defaults if not set:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql://code_index_user:code_index_pass@localhost:5433/code_index_db` | PostgreSQL connection string |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API base URL |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Model for embeddings — must match the model used at index time |

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

DATABASE_URL      = _cfg("DATABASE_URL",    "database_url",    "postgresql://code_index_user:code_index_pass@localhost:5434/code_index_db")
OLLAMA_URL        = _cfg("OLLAMA_URL",      "ollama_url",      "http://localhost:11434")
EMBEDDING_MODEL   = _cfg("EMBEDDING_MODEL", "embedding_model", "nomic-embed-text")
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

Store: `project_name`.

Report: `"Project name: {project_name}"`

---

## Step 2: Check Index Exists

**Goal:** Confirm the project has been indexed and the embedding model matches.

Write this to `/tmp/tcr_check_search_meta.py` and run it with `python3 /tmp/tcr_check_search_meta.py`:

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
        "SELECT chunk_count, embedding_model FROM _index_meta WHERE project = %s",
        (PROJECT_NAME,)
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        print("NOT_INDEXED")
        sys.exit(1)

    chunk_count, indexed_model = row
    if indexed_model != EMBEDDING_MODEL:
        print(f"MODEL_MISMATCH:{indexed_model}")
        sys.exit(2)

    print(f"META_OK:{chunk_count}")
except Exception as e:
    print(f"DB_FAIL: {e}")
    sys.exit(3)
```

Run it with:

```bash
TCR_PROJECT="{project_name}" python3 /tmp/tcr_check_search_meta.py
```

Parse the output:

- `NOT_INDEXED` — print `"Project '{project_name}' has not been indexed yet. Please run /tcr-onboard first."` and **stop**.
- `MODEL_MISMATCH:{old_model}` — print `"Embedding model mismatch (index: {old_model}, current: {EMBEDDING_MODEL}). Please run /tcr-onboard again."` and **stop**.
- `DB_FAIL: ...` — print `"Database not reachable. Please check DATABASE_URL and start the DB."` and **stop**.
- `META_OK:{chunk_count}` — extract `chunk_count` and continue.

Store: `chunk_count`.

Report: `"Index OK: {chunk_count} chunks in '{project_name}'."`

---

## Step 3: Embed Query

**Goal:** Convert the user's query text into a vector embedding using the same model as the index.

The query text is whatever the user typed after `/tcr-search`. For example, if the user typed `/tcr-search "Datumsfilter"`, the query text is `Datumsfilter`.

Write this to `/tmp/tcr_embed_query.py` and run it with `python3 /tmp/tcr_embed_query.py`:

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

OLLAMA_URL      = os.getenv("OLLAMA_URL",      "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
QUERY_TEXT      = os.environ["TCR_QUERY"]

try:
    resp = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBEDDING_MODEL, "input": QUERY_TEXT},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    # Ollama embed returns {"embeddings": [[...]]} (list of lists)
    vec = data["embeddings"][0]
    print(json.dumps(vec))
except Exception as e:
    print(f"EMBED_FAIL: {e}", file=sys.stderr)
    sys.exit(1)
```

Run it with:

```bash
TCR_QUERY="{query_text}" python3 /tmp/tcr_embed_query.py > /tmp/tcr_query_vec.json
```

- If the script exits with a non-zero code: print `"Embedding error: {error}. Please make sure Ollama is running and {EMBEDDING_MODEL} is available."` and **stop**.
- If it succeeds: read the vector from `/tmp/tcr_query_vec.json`.

```python
import json
with open("/tmp/tcr_query_vec.json", "r") as f:
    query_vec = json.load(f)
```

**Format the vector as a string** for the pgvector `%s::vector` cast:

```python
vec_str = "[" + ",".join(str(x) for x in query_vec) + "]"
```

Store: `vec_str`.

Report: `"Query embedded: {len(query_vec)}-dimensional vector."`

---

## Step 4: Search

**Goal:** Run a vector similarity search against the project table, deduplicating by `chunk_id` so each chunk appears at most once.

Write this to `/tmp/tcr_search.py` and run it with `python3 /tmp/tcr_search.py`:

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

with open("/tmp/tcr_query_vec.json", "r") as f:
    query_vec = json.load(f)

vec_str = "[" + ",".join(str(x) for x in query_vec) + "]"

SEARCH_SQL = f"""
SELECT * FROM (
    SELECT DISTINCT ON (chunk_id)
        chunk_id, type, file_path, line_start, line_end, content, commit_hash,
        1 - (embedding <=> %s::vector) AS similarity
    FROM {PROJECT_NAME}
    ORDER BY chunk_id, 1 - (embedding <=> %s::vector) DESC
) sub
ORDER BY similarity DESC
LIMIT 10
"""

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()
    cur.execute(SEARCH_SQL, (vec_str, vec_str))
    columns = [d[0] for d in cur.description]
    rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    conn.close()

    with open("/tmp/tcr_results.json", "w") as f:
        # similarity is a Decimal from psycopg2 — convert to float for JSON
        for row in rows:
            row["similarity"] = float(row["similarity"])
        json.dump(rows, f)

    print(f"SEARCH_OK:{len(rows)}")
except Exception as e:
    print(f"SEARCH_FAIL: {e}")
    sys.exit(1)
```

Run it with:

```bash
TCR_PROJECT="{project_name}" python3 /tmp/tcr_search.py
```

Parse the output:

- `SEARCH_OK:{n}` — extract result count and continue.
- `SEARCH_FAIL: ...` — print the error and **stop**.

Read the results:

```python
import json
with open("/tmp/tcr_results.json", "r") as f:
    results = json.load(f)
```

Store: `results`.

Report: `"Search complete: {len(results)} results found."`

---

## Step 5: Format Results

**Goal:** Display the search results clearly so the agent can read and act on the matching code chunks.

If `results` is empty: print the following and stop (this is not an error):

```
No results found for: "{query_text}"

Possible reasons:
- The search term is too specific — try different wording
- The project has not been fully indexed yet
- The code you are looking for does not exist in the project
```

If results are found, print the following header:

```
Search results for: "{query_text}"
Project: {project_name}
Found: {len(results)} results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Then for each result, print:

```
[{rank}] {file_path}  Lines {line_start}–{line_end}  Type: {type}  Score: {similarity:.4f}
─────────────────────────────────────────────────
{content}

```

Where:
- `{rank}` is the 1-based result number (1 = most similar)
- `{file_path}` is the relative path from the project root
- `{line_start}` and `{line_end}` are 1-based line numbers
- `{type}` is either `summary` (AI-generated description) or `code` (raw source)
- `{similarity:.4f}` is the cosine similarity score, formatted to 4 decimal places (1.0 = perfect match)
- `{content}` is the full chunk text (do not truncate)

After the last result, print:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tip: Type "summary" = AI-generated description of the chunk. Type "code" = raw source.
Both types can reference the same chunk_id — the score determines which type is a better match.
```

---

## Error Handling

### If any step fails, stop immediately

Do not continue to the next step if a critical error occurred. Print the error clearly and explain which step failed.

### Ollama not running or model unavailable

- If the embed call fails in Step 3: check that Ollama is running (`curl -s {OLLAMA_URL}/api/tags`) and that `{EMBEDDING_MODEL}` is listed.
- To pull the model if missing: `ollama pull {EMBEDDING_MODEL}`

### Embedding model mismatch

- If Step 2 returns `MODEL_MISMATCH`: the index was built with a different model. Searching with a different model produces meaningless results because the vector spaces are incompatible.
- Solution: set `EMBEDDING_MODEL` to match the indexed model, or run `/tcr-onboard` to rebuild the index with the new model.

### DB connection failure

- If psycopg2 cannot connect: check that `DATABASE_URL` is correct and the PostgreSQL container is running.
- For the pgvector Docker setup from this project: `docker compose up -d` in the project root.

### Project not indexed

- If Step 2 returns `NOT_INDEXED`: the project table does not exist in `_index_meta`. Run `/tcr-onboard` first to build the index before searching.

### Empty results

- Zero results is not an error — it means no chunks matched the query above the similarity threshold.
- Try rephrasing the query, using different keywords, or checking that the relevant files were included in the allowlist.

### Similarity score interpretation

- `1.0` = identical vector (perfect match)
- `0.8–1.0` = highly relevant
- `0.6–0.8` = moderately relevant
- Below `0.5` = likely noise — low confidence match
