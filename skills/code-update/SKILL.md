---
name: code-update
description: Incrementally update the pgvector index for a Git project. Reads last indexed commit from _index_meta, finds changed/added/deleted/renamed files since then, removes stale chunks, re-indexes changed files, and updates _index_meta with the new HEAD hash.
---

# /code-update — Skill Instructions

You are executing the **code-update** skill. Follow these 7 steps in order. Do not skip any step. At each step, report what you are doing.

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
DATABASE_URL    = os.getenv("DATABASE_URL",    "postgresql://code_index_user:code_index_pass@localhost:5433/code_index_db")
OLLAMA_URL      = os.getenv("OLLAMA_URL",      "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
SUMMARY_MODEL   = os.getenv("SUMMARY_MODEL",   "devstral:24b")
CHUNK_SIZE      = int(os.getenv("CHUNK_SIZE",   "50"))
CHUNK_OVERLAP   = int(os.getenv("CHUNK_OVERLAP", "15"))
```

---

## Step 1: Git Gate

**Goal:** Confirm we are inside a Git repository and extract the project name.

Run this shell command:

```bash
git rev-parse --is-inside-work-tree
```

- If it fails or returns nothing: print `"Kein Git-Repo gefunden. Bitte erst 'git init' ausführen."` and **stop immediately**.
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

- `NOT_INDEXED` — print `"Projekt '{project_name}' ist noch nicht indexiert. Bitte erst /code-onboard ausführen."` and **stop**.
- `MODEL_MISMATCH:{old_model}` — print `"Embedding-Modell hat sich geändert (war: {old_model}, jetzt: {EMBEDDING_MODEL}). Bitte /code-onboard erneut ausführen um vollständig neu zu indexieren."` and **stop**.
- `DB_FAIL: ...` — print `"Datenbank nicht erreichbar. Bitte DATABASE_URL prüfen und DB starten."` and **stop**.
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

If the output is empty (no changes since last index): print `"Keine neuen Commits seit letztem Index ({LAST_HASH[:8]}). Nichts zu tun."` and **stop** (this is a successful no-op, not an error).

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
    json.dump(chunks, f)
```

Write this to `/tmp/tcr_index.py` and run it with `python3 /tmp/tcr_index.py`:

```python
import os, sys, json
import requests
import psycopg2

DATABASE_URL    = os.getenv("DATABASE_URL",    "postgresql://code_index_user:code_index_pass@localhost:5433/code_index_db")
OLLAMA_URL      = os.getenv("OLLAMA_URL",      "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
SUMMARY_MODEL   = os.getenv("SUMMARY_MODEL",   "devstral:24b")
PROJECT_NAME    = os.environ["TCR_PROJECT"]
HEAD_HASH       = os.environ["TCR_HEAD_HASH"]
HEAD_MESSAGE    = os.environ.get("TCR_HEAD_MESSAGE", "")

with open("/tmp/tcr_chunks.json", "r") as f:
    chunks = json.load(f)

INSERT_SQL = f"""
INSERT INTO {PROJECT_NAME}
    (chunk_id, type, file_path, line_start, line_end, content,
     commit_hash, commit_message, embedding_model, embedding)
VALUES
    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

def generate_summary(code_text):
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

    # --- Insert summary row ---
    cur.execute(INSERT_SQL, (
        chunk["chunk_id"], "summary",
        chunk["file_path"], chunk["line_start"], chunk["line_end"],
        summary_text,
        HEAD_HASH, HEAD_MESSAGE, EMBEDDING_MODEL,
        summary_vec,
    ))

    # --- Insert code row ---
    cur.execute(INSERT_SQL, (
        chunk["chunk_id"], "code",
        chunk["file_path"], chunk["line_start"], chunk["line_end"],
        chunk["content"],
        HEAD_HASH, HEAD_MESSAGE, EMBEDDING_MODEL,
        code_vec,
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
TCR_HEAD_MESSAGE="{HEAD_MESSAGE}" \
python3 /tmp/tcr_index.py
```

- Watch for `INDEX_OK` at the end to confirm success.
- If the script exits with a non-zero code: print the error output and **stop**.

Report: `"Re-indexed {len(chunks)} chunks ({len(chunks)*2} rows inserted)."`

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

Print the following (in German — user-facing text):

```
Update abgeschlossen!

Projekt:              {project_name}
Letzter Index:        {LAST_HASH[:8]}
Neuer Stand:          {HEAD_HASH[:8]} — {HEAD_MESSAGE}
Dateien neu indexiert:{len(files_to_reindex)}
Dateien gelöscht:     {len(files_to_delete)}
Chunks neu:           {len(chunks)}
Gesamt Chunks in DB:  {chunk_count}
Embedding-Modell:     {EMBEDDING_MODEL}

Commits verarbeitet: von {LAST_HASH[:8]} bis {HEAD_HASH[:8]}
Nächster Schritt: /code-search verwenden um deinen Code semantisch zu durchsuchen.
```

---

## Error Handling

### If any step fails, stop immediately

Do not continue to the next step if a critical error occurred. Print the error clearly and explain which step failed.

### Project not yet indexed

- If Step 2 returns `NOT_INDEXED`: instruct the user to run `/code-onboard` first. Do not attempt to create the table or index — that is the onboard skill's responsibility.

### Embedding model mismatch

- If Step 2 returns `MODEL_MISMATCH`: the current `EMBEDDING_MODEL` env var differs from what was used when the index was built. Vectors are incomparable across models. The user must run `/code-onboard` to rebuild the index from scratch with the new model.

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
