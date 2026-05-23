**Task:** TASK_W5-T2 — Add AST parsing step to onboard
**Status:** TODO

**File:** skills/code-onboard/SKILL.md
**Branch:** task/W5-T2-ast-parsing-onboard
**Worker type:** Claude Code

**What changes:**
Adds a new Step 5b between chunking (Step 5) and embedding (Step 6). This step writes `/tmp/tcr_parse_ast.py` and executes it. The script uses tree-sitter to parse Python files, extract entities (files, classes, functions, methods, imports) and relations (contains, calls, imports), and INSERT them into the entity/relation tables.

**Pattern:**

New Step 5b in SKILL.md:

```
## Step 5b: Extract Code Structure (AST)

Write `/tmp/tcr_parse_ast.py` and run it.
```

The script must:
1. Check tree-sitter availability:
   ```python
   try:
       from tree_sitter_languages import get_parser
   except ImportError:
       print("AST_SKIP: tree-sitter not installed. Run: pip install tree-sitter tree-sitter-languages")
       sys.exit(0)  # non-blocking, continue without AST
   ```

2. Read file list from `/tmp/tcr_files.json` (written by orchestrator after Step 4)

3. Map extensions to tree-sitter languages: `.py` → `python` (only Python in Phase 1, skip others)

4. For each Python file, parse and extract:
   - `file` entity (one per file)
   - `class_definition` nodes → `class` entity
   - `function_definition` nodes → `function` entity (or `method` if parent is class)
   - `import_statement`/`import_from_statement` → `import` entity
   - `contains` relations: file→class, file→function, class→method
   - `calls` relations: scan function bodies for `call_expression`, match against known entity names
   - `imports` relations: from import statements

5. INSERT entities first (to get IDs via RETURNING), then INSERT relations using those IDs

6. Use env vars: `TCR_PROJECT`, `DATABASE_URL`

7. Output: `AST_OK: {entity_count} entities, {relation_count} relations`

Also: write the file list to `/tmp/tcr_files.json` after Step 4 (file discovery), before Step 5.

**Input/Output Contract:**
Depends on: TASK_W5-T1 (entity/relation tables must exist)
Input: file list from Step 4 discovery
Output: populated _entities and _relations tables

**Verify:**
`grep -c "parse_ast" skills/code-onboard/SKILL.md` — should be >0.
`grep -c "tree_sitter" skills/code-onboard/SKILL.md` — should be >0.

**Done when:**
Step 5b exists in onboard SKILL.md. The tcr_parse_ast.py script handles: tree-sitter import check (non-blocking skip), Python file parsing, entity extraction (file/class/function/method/import), relation extraction (contains/calls/imports), DB INSERT. Script is inline in SKILL.md (temp script pattern).

**Ben noob section:**
Dieser Step liest den Code wie ein Compiler — erkennt Funktionen, Klassen, Imports und wer wen aufruft. Das ist die Basis für strukturelle Code-Suche.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W5-T2.md`. Read `skills/code-onboard/SKILL.md` to understand the current step flow. Read `.paul/CONCEPT.md` for the entity/relation schema. Insert a new Step 5b after Step 5 (chunking) that writes and executes tcr_parse_ast.py. Also add a file list export after Step 4. The tree-sitter parsing must be non-blocking (skip with warning if not installed). Verify, write Execution Log, rename task, commit.
