---
name: code-overview
description: Structural overview of indexed codebase via entity/relation graph. No LLM needed — pure SQL queries.
---

# /code-overview — Skill Instructions

You are executing the **code-overview** skill. Follow these 4 steps in order. Do not skip any step. At each step, report what you are doing.

Usage: `/code-overview` or `/code-overview <symbol_name>`

- No argument: high-level structural overview (entity counts, top-level files/classes/functions, top imports)
- With argument: recursive subgraph for that symbol (callers + callees, up to 2 hops)

---

## Config

Read configuration from environment variables. Use these defaults if not set:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql://code_index_user:code_index_pass@localhost:5433/code_index_db` | PostgreSQL connection string |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API base URL (not used for queries, available for future use) |

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
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://code_index_user:code_index_pass@localhost:5433/code_index_db")
OLLAMA_URL   = os.getenv("OLLAMA_URL",   "http://localhost:11434")
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

## Step 2: Check Entities Table Exists

**Goal:** Confirm the project has been onboarded and the entities table exists.

Write this to `/tmp/tcr_check_entities.py` and run it with `python3 /tmp/tcr_check_entities.py`:

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
    cur  = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = %s",
        (f"{PROJECT_NAME}_entities",)
    )
    count = cur.fetchone()[0]
    conn.close()

    if count == 0:
        print("NOT_FOUND")
        sys.exit(1)

    print("TABLE_OK")
except Exception as e:
    print(f"DB_FAIL: {e}")
    sys.exit(2)
```

Run it with:

```bash
TCR_PROJECT="{project_name}" python3 /tmp/tcr_check_entities.py
```

Parse the output:

- `NOT_FOUND` — print `"No entities found. Run /code-onboard first."` and **stop**.
- `DB_FAIL: ...` — print `"Database not reachable. Please check DATABASE_URL and start the DB."` and **stop**.
- `TABLE_OK` — continue.

Report: `"Entities table confirmed for '{project_name}'."`

---

## Step 3: Run Overview Query

**Goal:** Query the entity/relation tables and collect the overview data.

Write the following script to `/tmp/tcr_overview.py`. The script branches on whether `TCR_SYMBOL` is set:

- If `TCR_SYMBOL` is **not set** (or empty): run the high-level stats mode.
- If `TCR_SYMBOL` is **set**: run the symbol subgraph mode.

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
SYMBOL       = os.environ.get("TCR_SYMBOL", "").strip()

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()

    if not SYMBOL:
        # ── MODE 1: High-level overview ──────────────────────────────────────

        # Entity counts by type
        cur.execute(f"""
            SELECT type, COUNT(*) as cnt
            FROM {PROJECT_NAME}_entities
            GROUP BY type
            ORDER BY cnt DESC
        """)
        type_counts = [{"type": r[0], "count": r[1]} for r in cur.fetchall()]

        if not type_counts:
            print("NO_ENTITIES")
            conn.close()
            sys.exit(1)

        # Top-level structure: files with their classes and functions (depth 1)
        cur.execute(f"""
            SELECT e_parent.file_path, e_child.type, e_child.name
            FROM {PROJECT_NAME}_entities e_parent
            JOIN {PROJECT_NAME}_relations r ON r.from_id = e_parent.id
            JOIN {PROJECT_NAME}_entities e_child ON e_child.id = r.to_id
            WHERE e_parent.type = 'file'
              AND e_child.type IN ('class', 'function')
            ORDER BY e_parent.file_path, e_child.type, e_child.name
            LIMIT 200
        """)
        structure_rows = [{"file": r[0], "type": r[1], "name": r[2]} for r in cur.fetchall()]

        # Top 20 imports
        cur.execute(f"""
            SELECT name, COUNT(*) as cnt
            FROM {PROJECT_NAME}_entities
            WHERE type = 'import'
            GROUP BY name
            ORDER BY cnt DESC
            LIMIT 20
        """)
        top_imports = [{"name": r[0], "count": r[1]} for r in cur.fetchall()]

        result = {
            "mode": "overview",
            "project": PROJECT_NAME,
            "type_counts": type_counts,
            "structure": structure_rows,
            "top_imports": top_imports,
        }

    else:
        # ── MODE 2: Symbol subgraph (callers + callees, 2 hops) ─────────────

        # Verify the symbol exists
        cur.execute(f"""
            SELECT id, type, name, file_path
            FROM {PROJECT_NAME}_entities
            WHERE name = %s
            LIMIT 1
        """, (SYMBOL,))
        root_row = cur.fetchone()

        if root_row is None:
            print(f"SYMBOL_NOT_FOUND:{SYMBOL}")
            conn.close()
            sys.exit(2)

        # Recursive CTE: callers + callees up to 2 hops
        cur.execute(f"""
            WITH RECURSIVE subgraph AS (
                SELECT e.id, e.type, e.name, e.file_path, 0 AS depth, 'root' AS direction
                FROM {PROJECT_NAME}_entities e
                WHERE e.name = %s

                UNION ALL

                SELECT e2.id, e2.type, e2.name, e2.file_path, sg.depth + 1, 'callee'
                FROM subgraph sg
                JOIN {PROJECT_NAME}_relations r ON r.from_id = sg.id AND r.type = 'calls'
                JOIN {PROJECT_NAME}_entities e2 ON e2.id = r.to_id
                WHERE sg.depth < %s

                UNION ALL

                SELECT e2.id, e2.type, e2.name, e2.file_path, sg.depth + 1, 'caller'
                FROM subgraph sg
                JOIN {PROJECT_NAME}_relations r ON r.to_id = sg.id AND r.type = 'calls'
                JOIN {PROJECT_NAME}_entities e2 ON e2.id = r.from_id
                WHERE sg.depth < %s
            )
            SELECT DISTINCT id, type, name, file_path, depth, direction
            FROM subgraph
            ORDER BY depth, name
        """, (SYMBOL, 2, 2))

        subgraph_rows = [
            {"id": r[0], "type": r[1], "name": r[2], "file_path": r[3], "depth": r[4], "direction": r[5]}
            for r in cur.fetchall()
        ]

        result = {
            "mode": "subgraph",
            "project": PROJECT_NAME,
            "symbol": SYMBOL,
            "nodes": subgraph_rows,
        }

    conn.close()
    with open("/tmp/tcr_overview_result.json", "w") as f:
        json.dump(result, f)
    print("OK")

except Exception as e:
    print(f"QUERY_FAIL: {e}")
    sys.exit(3)
```

**Run in overview mode** (no symbol):

```bash
TCR_PROJECT="{project_name}" python3 /tmp/tcr_overview.py
```

**Run in subgraph mode** (with symbol):

```bash
TCR_PROJECT="{project_name}" TCR_SYMBOL="{symbol_name}" python3 /tmp/tcr_overview.py
```

Parse the output:

- `NO_ENTITIES` — print `"No entities found. Run /code-onboard first."` and **stop**.
- `SYMBOL_NOT_FOUND:{name}` — print `"Symbol '{name}' not found in project '{project_name}'. Check spelling or run /code-search to find the exact name."` and **stop**.
- `QUERY_FAIL: ...` — print the error and **stop**.
- `OK` — read results from `/tmp/tcr_overview_result.json` and continue to Step 4.

```python
import json
with open("/tmp/tcr_overview_result.json", "r") as f:
    result = json.load(f)
```

---

## Step 4: Format Results

**Goal:** Display the results clearly.

### Mode 1 — Overview (no argument)

Print this header:

```
Project: {project_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Entity counts by type:
```

Then a table of type counts:

```
  function     : 142
  class        :  18
  import       :  87
  file         :  12
```

Then the top-level structure section. Group by file and print a tree:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Top-level structure (files → classes and functions):

  app/main.py
    [function]  health
    [function]  startup
  app/routes/api.py
    [function]  get_items
    [function]  create_item
  app/models/user.py
    [class]     User
    [function]  get_by_id
```

Then the top imports section:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Top 20 imports (by frequency):

  os                :  34
  sys               :  28
  psycopg2          :  19
  fastapi           :  12
```

Finish with:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tip: Run '/code-overview <symbol_name>' to see the call graph for a specific function or class.
```

### Mode 2 — Symbol Subgraph (with argument)

Print this header:

```
Subgraph for: {symbol_name}
Project: {project_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Then format the nodes grouped by depth:

```
[depth 0 — root]
  {type:<12} {name}  ({file_path})

[depth 1 — callees]
  {type:<12} {name}  ({file_path})
  ...

[depth 1 — callers]
  {type:<12} {name}  ({file_path})
  ...

[depth 2 — callees]
  ...
```

Where:
- `{type}` is the entity type (function, class, import, etc.)
- `{name}` is the entity name
- `{file_path}` is the relative path from the project root
- `{direction}` is `root`, `callee`, or `caller`

If no callers or callees are found at a depth, omit that group rather than printing an empty section.

Finish with:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total nodes: {len(nodes)}  (root + {len(nodes)-1} connected)
```

---

## Error Handling

### If any step fails, stop immediately

Do not continue to the next step if a critical error occurred. Print the error clearly and explain which step failed.

### No entities found

- If Step 2 or Step 3 returns `NOT_FOUND` or `NO_ENTITIES`: the entities table either does not exist or is empty.
- Solution: run `/code-onboard` to index the project first.

### Symbol not found

- If Step 3 returns `SYMBOL_NOT_FOUND`: the symbol name does not match any entity in the index.
- Try `/code-search <symbol_name>` to find the closest matching name.
- Symbol names are case-sensitive — check exact spelling.

### DB connection failure

- If psycopg2 cannot connect: check that `DATABASE_URL` is correct and the PostgreSQL container is running.
- For the pgvector Docker setup from this project: `docker compose up -d` in the project root.

### Empty structure

- If type counts show entities but structure is empty: the relations table may not have `file → class/function` edges. This can happen if the project was onboarded with a version that did not index relation edges. Re-run `/code-onboard` to rebuild.
