**Task:** TASK_W5-T4 — Create code-overview skill
**Status:** DONE

**File:** skills/code-overview/SKILL.md, plugin.json
**Branch:** task/W5-T4-code-overview-skill
**Worker type:** Claude Code

**What changes:**
Creates a new skill `/code-overview` that queries entity/relation tables to show structural overviews. Pure SQL — no embedding, no LLM needed. Also registers the skill in plugin.json.

**Pattern:**

SKILL.md structure:
```markdown
---
name: code-overview
description: Structural overview of indexed codebase via entity/relation graph. No LLM needed — pure SQL queries.
---

# /code-overview

Usage: `/code-overview` or `/code-overview <symbol_name>`
```

Steps:
1. Git Gate (same as other skills)
2. Check entities table exists: `SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{project}_entities'`
3. If no argument — write `/tmp/tcr_overview.py`:
   - High-level stats: `SELECT type, COUNT(*) FROM {project}_entities GROUP BY type`
   - Top-level structure: files with their classes and functions (depth 1)
   - Import summary: `SELECT name, COUNT(*) FROM {project}_entities WHERE type='import' GROUP BY name ORDER BY count DESC LIMIT 20`
4. If symbol argument — write `/tmp/tcr_overview.py`:
   - Find entity: `SELECT * FROM {project}_entities WHERE name = %s`
   - Recursive CTE for subgraph (callers + callees, 2 hops):
   ```sql
   WITH RECURSIVE subgraph AS (
       SELECT e.id, e.type, e.name, e.file_path, 0 as depth, 'root' as direction
       FROM {project}_entities e WHERE e.name = %s
       UNION ALL
       SELECT e2.id, e2.type, e2.name, e2.file_path, sg.depth + 1, 'callee'
       FROM subgraph sg
       JOIN {project}_relations r ON r.from_id = sg.id
       JOIN {project}_entities e2 ON e2.id = r.to_id
       WHERE sg.depth < %s
       UNION ALL
       SELECT e2.id, e2.type, e2.name, e2.file_path, sg.depth + 1, 'caller'
       FROM subgraph sg
       JOIN {project}_relations r ON r.to_id = sg.id
       JOIN {project}_entities e2 ON e2.id = r.from_id
       WHERE sg.depth < %s
   ) SELECT DISTINCT id, type, name, file_path, depth, direction FROM subgraph ORDER BY depth, name;
   ```
5. Format results as tree/table output

Add to plugin.json:
```json
{
    "name": "code-overview",
    "path": "skills/code-overview/SKILL.md",
    "description": "Structural overview of indexed codebase via entity/relation graph"
}
```

Config: only DATABASE_URL and OLLAMA_URL (for .env loading pattern).
Error handling: "No entities found. Run /code-onboard first." if tables empty.

**Verify:**
`test -f skills/code-overview/SKILL.md && grep "code-overview" plugin.json`

**Done when:**
code-overview SKILL.md exists with both modes (no-arg overview + symbol subgraph). plugin.json has 4 skills registered. Recursive CTE for graph traversal is included.

**Ben noob section:**
Neuer Command: `/code-overview` zeigt dir die Struktur deines Projekts — welche Klassen, Funktionen, wer ruft wen auf. Alles aus der Datenbank, kein LLM nötig.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W5-T4.md`. Create `skills/code-overview/SKILL.md` with both query modes (overview + symbol subgraph). Use the recursive CTE from the Pattern. Read `skills/code-search/SKILL.md` for consistent style (Git Gate, .env loading, error handling). Edit `plugin.json` to add the new skill. Verify, write Execution Log, rename task, commit.

---

## Execution Log

### Attempt 1
- Date: 2026-05-23
- Result: Created skills/code-overview/SKILL.md with 4-step structure matching code-search style. Step 1: Git Gate (verbatim from code-search). Step 2: information_schema check for entities table. Step 3: single /tmp/tcr_overview.py script branching on TCR_SYMBOL — overview mode (entity counts by type, top-level file/class/function structure, top 20 imports) and subgraph mode (recursive CTE with callers + callees at 2 hops). Step 4: tree/table formatting for both modes. Added code-overview entry to plugin.json (now 4 skills total).
- Files Changed: skills/code-overview/SKILL.md (created), plugin.json (edited)
- Issues: none
- Status: DONE
