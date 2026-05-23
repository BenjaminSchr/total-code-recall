**Task:** TASK_W7-T1 — Create code-explain skill
**Status:** DONE

**File:** skills/code-explain/SKILL.md, plugin.json
**Branch:** task/W7-T1-code-explain-skill
**Worker type:** Claude Code

**What changes:**
Creates the hybrid query skill `/code-explain` that combines vector search + graph traversal + hierarchical summaries. Also registers in plugin.json.

**Pattern:**

SKILL.md structure:
```markdown
---
name: code-explain
description: Hybrid code search combining vector similarity, entity graph, and hierarchical summaries. Returns enriched results with structural context.
---

# /code-explain

Usage: `/code-explain <query>`
Example: `/code-explain "how does the authentication middleware work"`
```

Steps:
1. Git Gate
2. Check index + entities + summaries tables exist
3. Embed query via Ollama (same as code-search)
4. Hybrid search — write `/tmp/tcr_explain.py`:
   - **Vector pass**: Top 20 chunks via cosine similarity (same SQL as code-search)
   - **Graph expansion**: For each top chunk, find entities whose line range overlaps:
     ```sql
     SELECT * FROM {project}_entities
     WHERE file_path = %s AND line_start <= %s AND line_end >= %s
     ```
     For each matched entity, 1-2 hop traversal via recursive CTE (same as code-overview)
   - **Summary enrichment**: For each unique file_path in results:
     ```sql
     SELECT content FROM {project}_summaries WHERE level='file' AND scope = %s
     ```
     Also fetch module summary for the directory
   - **Re-rank**: `final_score = 0.6 * vector_similarity + 0.2 * graph_relevance + 0.2 * summary_similarity`
     - graph_relevance: 1.0 if entity within 2 hops of query-related entity, else 0.0
     - summary_similarity: cosine distance of query embedding vs file/module summary embedding
   - Return top 10
5. Format results — enhanced format:
   ```
   ━━━ Match 1 (Score: 0.94) ━━━
   File: app/auth.py (Lines: 45-95)
   Entity: AuthMiddleware.validate_token (method)
   Callers: app.main.handle_request, app.api.check_auth
   File Summary: Handles JWT token validation and session management...

   def validate_token(self, token):
       ...
   ```

Register in plugin.json:
```json
{
    "name": "code-explain",
    "path": "skills/code-explain/SKILL.md",
    "description": "Hybrid code search with entity graph and hierarchical summaries"
}
```

Target: under 4k tokens per result in Claude context.

**Input/Output Contract:**
Depends on: All W5 + W6 tasks (entities, relations, summaries populated)

**Verify:**
`test -f skills/code-explain/SKILL.md && grep "code-explain" plugin.json`

**Done when:**
code-explain SKILL.md exists with hybrid search pipeline (vector + graph + summaries). plugin.json has 5 skills. Output format shows entity context, callers, and file summary alongside code.

**Ben noob section:**
Der mächtigste Command: du fragst "wie funktioniert X?" und bekommst nicht nur den relevanten Code, sondern auch wer ihn aufruft, was er importiert, und eine Zusammenfassung der ganzen Datei.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W7-T1.md`. Read `skills/code-search/SKILL.md` for the vector search pattern. Read `skills/code-overview/SKILL.md` for the recursive CTE pattern. Combine both into the hybrid search. Create `skills/code-explain/SKILL.md`. Edit `plugin.json` to register. Verify, write Execution Log, rename task, commit.

---

## Execution Log

### Attempt 1
- Date: 2026-05-23
- Result: Created skills/code-explain/SKILL.md with 5-step hybrid search pipeline (Git Gate, check index+entities+summaries tables, embed query via Ollama, run hybrid search script /tmp/tcr_explain.py combining vector top-20 + entity graph expansion + 1-hop callers/callees + file summary enrichment, format enriched results). Added code-explain entry to plugin.json. Plugin now has 5 skills.
- Files Changed: skills/code-explain/SKILL.md (created), plugin.json (edited)
- Issues: none
- Status: DONE
