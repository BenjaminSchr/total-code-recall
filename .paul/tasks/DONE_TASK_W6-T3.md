**Task:** TASK_W6-T3 — Add module and repo summary aggregation
**Status:** DONE

**File:** skills/code-onboard/SKILL.md, skills/code-update/SKILL.md
**Branch:** task/W6-T3-module-repo-summaries
**Worker type:** Claude Code

**What changes:**
Extends the summary step (from W6-T2) to add module-level and repo-level summaries. Also adds summary rebuild logic to the update skill.

**Pattern:**

In onboard SKILL.md, extend tcr_build_summaries.py:

After file summaries, add:

```python
# Module summaries (one per directory with 2+ files)
dirs = {}
for file_path in file_paths:
    d = os.path.dirname(file_path) or "."
    dirs.setdefault(d, []).append(file_path)

for dir_path, files in dirs.items():
    if len(files) < 2:
        continue
    cur.execute(f"SELECT content FROM {PROJECT}_summaries WHERE level='file' AND scope IN ({','.join(['%s']*len(files))})", files)
    file_sums = [r[0] for r in cur.fetchall()]
    module_summary = call_devstral(f"Summarize this module (directory: {dir_path}). These are its files:\n\n" + "\n\n".join(file_sums))
    module_vec = get_embedding(module_summary)
    cur.execute(f"INSERT INTO {PROJECT}_summaries (level, scope, content, embedding) VALUES ('module', %s, %s, %s::vector)", (dir_path, module_summary, vec_to_str(module_vec)))

# Repo summary
cur.execute(f"SELECT content FROM {PROJECT}_summaries WHERE level IN ('module', 'file')")
all_sums = [r[0] for r in cur.fetchall()]
repo_summary = call_devstral(f"Summarize this entire codebase:\n\n" + "\n\n".join(all_sums[:20]))
repo_vec = get_embedding(repo_summary)
cur.execute(f"INSERT INTO {PROJECT}_summaries (level, scope, content, embedding) VALUES ('repo', %s, %s, %s::vector)", (PROJECT, repo_summary, vec_to_str(repo_vec)))
```

In update SKILL.md, after chunk re-indexing + AST re-parse:
- Delete summaries for affected file_paths: `DELETE FROM {project}_summaries WHERE level='file' AND scope = %s`
- Regenerate file summaries for affected files
- Regenerate module summaries for affected directories
- Regenerate repo summary

**Input/Output Contract:**
Depends on: TASK_W6-T2 (file summaries and tcr_build_summaries.py exist)

**Verify:**
`grep -c "module" skills/code-onboard/SKILL.md | head -5` — should show module summary references.
`grep -c "summaries" skills/code-update/SKILL.md` — should be >0.

**Done when:**
Onboard generates file→module→repo summaries. Update rebuilds affected summaries on file change. All summaries are embedded and stored in _summaries table.

**Ben noob section:**
Neben Datei-Zusammenfassungen gibt es jetzt auch Modul-Zusammenfassungen (pro Ordner) und eine Gesamt-Zusammenfassung des Repos. So versteht ein Agent das Projekt auf jeder Ebene.

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W6-T3.md`. Read `skills/code-onboard/SKILL.md` for the file-summary step (W6-T2). Extend it with module and repo summaries. Then read `skills/code-update/SKILL.md` and add summary rebuild for affected files/modules/repo after chunk re-indexing. Verify, write Execution Log, rename task, commit.

---

## Execution Log

### Attempt 1
- Date: 2026-05-23
- Result: Extended `tcr_build_summaries.py` in onboard SKILL.md Step 7 with: (1) `generate_summary` and `get_embedding` helper functions, (2) module-level summary loop (one per directory with 2+ indexed files), (3) repo-level summary aggregating up to 20 module/file summaries, (4) updated final print to report all three counts. Added Step 5d to update SKILL.md that deletes all summaries via `tcr_delete_summaries.py` then regenerates all three levels via `tcr_build_summaries.py`.
- Files Changed: skills/code-onboard/SKILL.md, skills/code-update/SKILL.md
- Issues: none
- Status: DONE
