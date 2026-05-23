**Task:** TASK_W1-T1 — Create plugin.json manifest
**Status:** DONE

**File:** plugin.json
**Branch:** task/W1-T1-plugin-json
**Worker type:** Claude Code

**What changes:**
Creates the Claude Code plugin manifest that defines the plugin name, version, description, and registers the three skills (code-onboard, code-update, code-search).

**Pattern:**
```json
{
  "name": "total-code-recall",
  "version": "0.1.0",
  "description": "Semantic code search plugin for Claude Code. Index, update, and search your codebase with local embeddings via Ollama + pgvector.",
  "author": "BenjaminSchr",
  "skills": [
    {
      "name": "code-onboard",
      "path": "skills/code-onboard/SKILL.md",
      "description": "Index a project's codebase into pgvector for semantic search"
    },
    {
      "name": "code-update",
      "path": "skills/code-update/SKILL.md",
      "description": "Update index with new commits since last onboard/update"
    },
    {
      "name": "code-search",
      "path": "skills/code-search/SKILL.md",
      "description": "Semantic search over indexed codebase"
    }
  ]
}
```

**Input/Output Contract:**
None — this is the root manifest, no dependencies.

**Verify:**
`cat plugin.json | python3 -c "import sys,json; json.load(sys.stdin); print('valid JSON')"` returns "valid JSON".

**Done when:**
plugin.json exists at project root and is valid JSON with name, version, description, author, and three skill entries.

**Ben noob section:**
Das ist die "Visitenkarte" des Plugins — Claude Code liest diese Datei und weiß dadurch welche Skills verfügbar sind.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read the task file `.paul/tasks/TASK_W1-T1.md`. The Pattern section contains the exact content to write. Create the file, verify, write Execution Log, commit.

---

## Execution Log

### Attempt 1
- Date: 2026-05-23
- Result: Created plugin.json at project root with exact content from Pattern section. JSON validation passed.
- Files Changed: plugin.json (created)
- Issues: none
- Status: DONE
