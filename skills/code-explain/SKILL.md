---
name: code-explain
description: Hybrid code search combining vector similarity, entity graph traversal, and hierarchical file summaries. Returns enriched results with entity context, callers/callees, and file-level summaries alongside matching code chunks.
---

# /code-explain — Skill Instructions

You are executing the **code-explain** skill. Follow these 5 steps in order. Do not skip any step. At each step, report what you are doing.

Usage: `/code-explain <query>`

Example: `/code-explain "how does the authentication middleware work"`

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
DATABASE_URL    = os.getenv("DATABASE_URL",    "postgresql://code_index_user:code_index_pass@localhost:5433/code_index_db")
OLLAMA_URL      = os.getenv("OLLAMA_URL",      "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
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

Store: `project_name`.

Report: `"Project name: {project_name}"`

---

## Step 2: Check Tables Exist

**Goal:** Confirm the project has been indexed and all required tables exist (index meta, entities, summaries).

Write this to `/tmp/tcr_check_explain_meta.py` and run it with `python3 /tmp/tcr_check_explain_meta.py`:

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

    # Check index meta
    cur.execute(
        "SELECT chunk_count, embedding_model FROM _index_meta WHERE project = %s",
        (PROJECT_NAME,)
    )
    row = cur.fetchone()
    if row is None:
        print("NOT_INDEXED")
        sys.exit(1)

    chunk_count, indexed_model = row
    if indexed_model != EMBEDDING_MODEL:
        print(f"MODEL_MISMATCH:{indexed_model}")
        sys.exit(2)

    # Check entities table
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = %s",
        (f"{PROJECT_NAME}_entities",)
    )
    if cur.fetchone()[0] == 0:
        print("NO_ENTITIES")
        sys.exit(3)

    # Check summaries table
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = %s",
        (f"{PROJECT_NAME}_summaries",)
    )
    if cur.fetchone()[0] == 0:
        print("NO_SUMMARIES")
        sys.exit(4)

    conn.close()
    print(f"META_OK:{chunk_count}")
except Exception as e:
    print(f"DB_FAIL: {e}")
    sys.exit(5)
```

Run it with:

```bash
TCR_PROJECT="{project_name}" python3 /tmp/tcr_check_explain_meta.py
```

Parse the output:

- `NOT_INDEXED` — print `"Project '{project_name}' has not been indexed yet. Please run /code-onboard first."` and **stop**.
- `MODEL_MISMATCH:{old_model}` — print `"Embedding model mismatch (index: {old_model}, current: {EMBEDDING_MODEL}). Please run /code-onboard again."` and **stop**.
- `NO_ENTITIES` — print `"Entities table not found for '{project_name}'. Please run /code-onboard to index entities."` and **stop**.
- `NO_SUMMARIES` — print `"Summaries table not found for '{project_name}'. Please run /code-onboard to generate summaries."` and **stop**.
- `DB_FAIL: ...` — print `"Database not reachable. Please check DATABASE_URL and start the DB."` and **stop**.
- `META_OK:{chunk_count}` — extract `chunk_count` and continue.

Store: `chunk_count`.

Report: `"Index OK: {chunk_count} chunks, entities and summaries confirmed for '{project_name}'."`

---

## Step 3: Embed Query

**Goal:** Convert the user's query text into a vector embedding using the same model as the index.

The query text is whatever the user typed after `/code-explain`.

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

- If the script exits with a non-zero code: print `"Embedding error. Please make sure Ollama is running and {EMBEDDING_MODEL} is available."` and **stop**.
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

## Step 4: Hybrid Search

**Goal:** Run vector search, expand each result with entity context and callers/callees, enrich with file summaries, then return top 10.

Write this to `/tmp/tcr_explain.py` and run it with `python3 /tmp/tcr_explain.py`:

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

# ── Vector pass: top 20 chunks ─────────────────────────────────────────────
VECTOR_SQL = f"""
SELECT * FROM (
    SELECT DISTINCT ON (chunk_id)
        chunk_id, type, file_path, line_start, line_end, content, commit_hash,
        1 - (embedding <=> %s::vector) AS similarity
    FROM {PROJECT_NAME}
    ORDER BY chunk_id, 1 - (embedding <=> %s::vector) DESC
) sub
ORDER BY similarity DESC
LIMIT 20
"""

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()

    cur.execute(VECTOR_SQL, (vec_str, vec_str))
    columns = [d[0] for d in cur.description]
    top_chunks = [dict(zip(columns, row)) for row in cur.fetchall()]

    enriched = []

    for chunk in top_chunks:
        result = {
            "chunk_id":   chunk["chunk_id"],
            "type":       chunk["type"],
            "file_path":  chunk["file_path"],
            "line_start": chunk["line_start"],
            "line_end":   chunk["line_end"],
            "content":    chunk["content"],
            "similarity": float(chunk["similarity"]),
            "entities":   [],
            "callers":    [],
            "callees":    [],
            "file_summary": None,
        }

        # ── Graph expansion: find entities whose line range overlaps this chunk ──
        cur.execute(f"""
            SELECT id, type, name
            FROM {PROJECT_NAME}_entities
            WHERE file_path = %s AND line_start <= %s AND line_end >= %s
        """, (chunk["file_path"], chunk["line_end"], chunk["line_start"]))
        entity_rows = cur.fetchall()

        for ent_id, ent_type, ent_name in entity_rows:
            result["entities"].append({"type": ent_type, "name": ent_name})

            # ── 1-hop callers and callees via UNION ───────────────────────────
            cur.execute(f"""
                SELECT e2.name, e2.type, r.type as rel_type
                FROM {PROJECT_NAME}_relations r
                JOIN {PROJECT_NAME}_entities e2 ON e2.id = r.to_id
                WHERE r.from_id = %s AND r.type = 'calls'
                UNION
                SELECT e2.name, e2.type, 'called_by' as rel_type
                FROM {PROJECT_NAME}_relations r
                JOIN {PROJECT_NAME}_entities e2 ON e2.id = r.from_id
                WHERE r.to_id = %s AND r.type = 'calls'
            """, (ent_id, ent_id))

            for rel_name, rel_type, rel_kind in cur.fetchall():
                entry = {"name": rel_name, "type": rel_type}
                if rel_kind == "called_by":
                    if entry not in result["callers"]:
                        result["callers"].append(entry)
                else:
                    if entry not in result["callees"]:
                        result["callees"].append(entry)

        # ── Summary enrichment: file-level summary ───────────────────────────
        cur.execute(f"""
            SELECT content FROM {PROJECT_NAME}_summaries
            WHERE level = 'file' AND scope = %s
            LIMIT 1
        """, (chunk["file_path"],))
        summary_row = cur.fetchone()
        if summary_row:
            result["file_summary"] = summary_row[0]

        enriched.append(result)

    conn.close()

    # Deduplicate by chunk_id (keep highest similarity), take top 10
    seen = {}
    for item in enriched:
        cid = item["chunk_id"]
        if cid not in seen or item["similarity"] > seen[cid]["similarity"]:
            seen[cid] = item

    final = sorted(seen.values(), key=lambda x: x["similarity"], reverse=True)[:10]

    with open("/tmp/tcr_explain_results.json", "w") as f:
        json.dump(final, f)

    print(f"EXPLAIN_OK:{len(final)}")

except Exception as e:
    print(f"EXPLAIN_FAIL: {e}")
    sys.exit(1)
```

Run it with:

```bash
TCR_PROJECT="{project_name}" python3 /tmp/tcr_explain.py
```

Parse the output:

- `EXPLAIN_OK:{n}` — extract result count and continue.
- `EXPLAIN_FAIL: ...` — print the error and **stop**.

Read the results:

```python
import json
with open("/tmp/tcr_explain_results.json", "r") as f:
    results = json.load(f)
```

Store: `results`.

Report: `"Hybrid search complete: {len(results)} enriched results found."`

---

## Step 5: Format Results

**Goal:** Display the enriched results clearly, showing entity context, callers/callees, file summary, and code content.

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
Explain results for: "{query_text}"
Project: {project_name}
Found: {len(results)} enriched results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Then for each result, print the following format:

```
━━━ Match {rank} (Score: {similarity:.4f}) ━━━
File: {file_path}  Lines: {line_start}–{line_end}  Type: {type}
```

If `entities` is non-empty, print (one entity per line):

```
Entity: {entity_type} {entity_name}
```

If `callers` is non-empty, print the list on one line:

```
Callers: {caller_name_1}, {caller_name_2}, ...
```

If `callees` is non-empty, print the list on one line:

```
Callees: {callee_name_1}, {callee_name_2}, ...
```

If `file_summary` is not None, print (truncated to 200 chars if longer):

```
File Summary: {file_summary_truncated}
```

Then print the code content with a separator:

```
─────────────────────────────────────────────────
{content}

```

After the last result, print:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tip: Use /code-overview <symbol_name> to explore the full call graph for any entity shown above.
```

Where:
- `{rank}` is the 1-based result number (1 = highest similarity)
- `{similarity:.4f}` is the cosine similarity score formatted to 4 decimal places
- `{type}` is `summary` (AI description) or `code` (raw source)
- `{content}` is the full chunk text (do not truncate)
- Entity, Callers, Callees, and File Summary lines are omitted entirely when their data is empty

---

## Error Handling

### If any step fails, stop immediately

Do not continue to the next step if a critical error occurred. Print the error clearly and explain which step failed.

### Ollama not running or model unavailable

- If the embed call fails in Step 3: check that Ollama is running (`curl -s {OLLAMA_URL}/api/tags`) and that `{EMBEDDING_MODEL}` is listed.
- To pull the model if missing: `ollama pull {EMBEDDING_MODEL}`

### Embedding model mismatch

- If Step 2 returns `MODEL_MISMATCH`: the index was built with a different model. Searching with a different model produces meaningless results because the vector spaces are incompatible.
- Solution: set `EMBEDDING_MODEL` to match the indexed model, or run `/code-onboard` to rebuild the index with the new model.

### DB connection failure

- If psycopg2 cannot connect: check that `DATABASE_URL` is correct and the PostgreSQL container is running.
- For the pgvector Docker setup from this project: `docker compose up -d` in the project root.

### Missing tables

- If Step 2 returns `NO_ENTITIES` or `NO_SUMMARIES`: the entity or summary tables have not been populated.
- Run `/code-onboard` to index entities and generate summaries before using `/code-explain`.

### Project not indexed

- If Step 2 returns `NOT_INDEXED`: the project table does not exist in `_index_meta`. Run `/code-onboard` first to build the index before searching.

### Empty results

- Zero results is not an error — it means no chunks matched the query above the similarity threshold.
- Try rephrasing the query, using different keywords, or checking that the relevant files were included in the allowlist.

### Similarity score interpretation

- `1.0` = identical vector (perfect match)
- `0.8–1.0` = highly relevant
- `0.6–0.8` = moderately relevant
- Below `0.5` = likely noise — low confidence match
