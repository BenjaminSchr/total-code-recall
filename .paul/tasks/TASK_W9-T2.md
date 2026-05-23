**Task:** TASK_W9-T2 — Create skills/tcr-info/SKILL.md — current config, indexed projects, command list
**Status:** TODO

**File:** skills/tcr-info/SKILL.md
**Branch:** task/W9-T2-create-tcr-info-skill
**Worker type:** Claude Code

**What changes:**
Creates the `/tcr-info` skill that displays the current config, all indexed projects (queried from `_index_meta` table), and a full command reference. Read-only skill — no writes.

**Ben noob section:**
Ein Dashboard-Command: `/tcr-info` zeigt dir was du hast — welche Provider konfiguriert sind, welche Projekte indexiert sind, und was alle Commands machen. Wie `git status` für total-code-recall.

**Pattern:**

```markdown
---
name: tcr-info
description: Show current total-code-recall config, indexed projects, and command reference.
---

# /tcr-info — Status and Help

You are executing the **tcr-info** skill. Read and display all status information.

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
    print("No config found. Run /tcr-config first.")
```

---

## Step 2 — Show config

```
=== total-code-recall v0.2.0 ===

Config: ~/.config/total-code-recall/config.json

  LLM Provider:       openrouter
  LLM Model:          google/gemini-flash-2.0
  Embedding Provider: ollama
  Embedding Model:    nomic-embed-text
  DB Provider:        local
  Database:           postgresql://...@localhost:5434/code_index_db
  Parallel Workers:   10
```

If no config: show defaults notice.

---

## Step 3 — Query indexed projects

Write `/tmp/tcr_info.py`:
```python
import psycopg2, json, os

CONFIG_PATH = os.path.expanduser("~/.config/total-code-recall/config.json")
with open(CONFIG_PATH) as f:
    cfg = json.load(f)

DATABASE_URL = os.environ.get("DATABASE_URL") or cfg.get("database_url")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Query all _index_meta tables to find indexed projects
cur.execute("""
    SELECT table_name FROM information_schema.tables
    WHERE table_name LIKE '%_index_meta'
    AND table_schema = 'public'
""")
meta_tables = [row[0] for row in cur.fetchall()]

projects = []
for tbl in meta_tables:
    project_name = tbl.replace("_index_meta", "")
    cur.execute(f"SELECT key, value FROM {tbl}")
    meta = dict(cur.fetchall())
    projects.append({
        "name": project_name,
        "path": meta.get("project_root", "unknown"),
        "last_commit": meta.get("last_commit", "unknown"),
        "indexed_at": meta.get("indexed_at", "unknown")
    })

cur.close()
conn.close()
print(json.dumps(projects))
```

Run script. Display:
```
Indexed Projects (3):

  1. benbank
     Path:       /home/bengpu/Schreibtisch/Workspace/projekte/benbank
     Last commit: a3f2c1d
     Indexed at: 2026-05-20 14:32

  2. cortex
     ...
```

If no projects: "No projects indexed yet. Run /tcr-onboard <path> to index your first project."

---

## Step 4 — Command reference

Print static command list:
```
Commands:
  /tcr-config    Configure providers (LLM, Embedding, DB). Run once.
  /tcr-onboard   Index a project for the first time.
  /tcr-update    Update index after new commits.
  /tcr-search    Semantic search over an indexed project.
  /tcr-overview  Structural overview via entity/relation graph.
  /tcr-explain   Hybrid search: vector + graph + summaries.
  /tcr-info      This command.
```
```

**Input/Output Contract:**
Depends on: TASK_W9-T1 (tcr-config created, for logical ordering — tcr-info references config format)
Produces: `skills/tcr-info/SKILL.md` (new file, new directory)

**Verify:**
```bash
test -f skills/tcr-info/SKILL.md && grep "name: tcr-info" skills/tcr-info/SKILL.md
```

**Done when:**
`skills/tcr-info/SKILL.md` exists with 4 steps: load config, show config, query `_index_meta` tables, print command list.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W9-T2.md`. Create directory `skills/tcr-info/` and write `skills/tcr-info/SKILL.md` following the pattern. The skill shows current config (from `~/.config/total-code-recall/config.json`), queries all `*_index_meta` tables for indexed projects, and prints the command reference. Run verify. Write Execution Log, rename to `DONE_TASK_W9-T2.md`, commit: `feat: TASK_W9-T2 — create tcr-info skill (config status + indexed projects + command list)`.
