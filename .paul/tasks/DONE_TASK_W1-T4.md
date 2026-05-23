**Task:** TASK_W1-T4 — Create docker-compose.yaml
**Status:** DONE

**File:** docker-compose.yaml
**Branch:** task/W1-T4-docker-compose
**Worker type:** Claude Code

**What changes:**
Creates a docker-compose.yaml providing a pgvector-enabled PostgreSQL container for external users.

**Pattern:**
```yaml
services:
  total-code-recall-db:
    image: pgvector/pgvector:pg16
    container_name: total-code-recall-db
    environment:
      POSTGRES_DB: code_index_db
      POSTGRES_USER: code_index_user
      POSTGRES_PASSWORD: code_index_pass
    ports:
      - "5433:5432"
    volumes:
      - code_index_data:/var/lib/postgresql/data
      - ./scripts/setup_db.sql:/docker-entrypoint-initdb.d/setup_db.sql
    restart: unless-stopped

volumes:
  code_index_data:
```

**Input/Output Contract:**
Depends on: TASK_W1-T3 (setup_db.sql must exist — mounted as init script)

**Verify:**
`cat docker-compose.yaml | python3 -c "import sys,yaml=__import__('yaml'); yaml.safe_load(sys.stdin); print('valid')"` or manually check YAML structure.

**Done when:**
docker-compose.yaml exists, mounts setup_db.sql as init script, exposes port 5433.

**Ben noob section:**
Für externe User: `docker compose up -d` und sie haben eine fertige DB mit pgvector. Wir brauchen das nicht — wir nutzen unsere DEV-DB.

---

---

## Execution Log

### Attempt 1
- Date: 2026-05-23
- Result: Created docker-compose.yaml with pgvector/pgvector:pg16 image, port 5433, setup_db.sql mounted as init script, and named volume code_index_data. YAML validated with python3.
- Files Changed: docker-compose.yaml
- Issues: none
- Status: DONE

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read the task file `.paul/tasks/TASK_W1-T4.md`. The Pattern section contains the exact content. Create the file, verify, write Execution Log, commit.
