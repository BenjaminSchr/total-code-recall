**Task:** TASK_W14-T3 — Create tests/test_db.py — schema, entity/relation INSERT, vector search, summaries
**Status:** DONE

**File:** tests/test_db.py (create)
**Branch:** task/W14-T3-test-db-schema
**Worker type:** Claude Code

**What changes:**
Creates `tests/test_db.py` that connects to a real test database (from `TEST_DATABASE_URL` or `DATABASE_URL` env var), verifies schema creation, tests INSERT into entities/relations tables, tests vector search via `<=>` operator, and tests summaries table reads. These are integration tests — they require a running PostgreSQL with pgvector.

**Ben noob section:**
Echte Datenbank-Tests. Sie prüfen ob die SQL-Schemas korrekt erstellt werden, ob man Entities und Relations einfügen kann, und ob die Vektor-Suche funktioniert. Diese Tests brauchen eine laufende PostgreSQL-Datenbank.

**Pattern:**

```python
# tests/test_db.py
import pytest
import psycopg2
import os
import uuid

# Skip all tests if no DB available
DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set — skipping DB integration tests"
)

TEST_PROJECT = f"test_{uuid.uuid4().hex[:8]}"

@pytest.fixture(scope="module")
def db_conn():
    """Real psycopg2 connection for the test session."""
    conn = psycopg2.connect(DATABASE_URL)
    yield conn
    # Cleanup: drop all test tables
    with conn.cursor() as cur:
        for suffix in ["_index", "_index_meta", "_entities", "_relations", "_summaries"]:
            cur.execute(f"DROP TABLE IF EXISTS {TEST_PROJECT}{suffix} CASCADE")
    conn.commit()
    conn.close()

def test_create_index_table(db_conn):
    """Can create the vector index table."""
    with db_conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {TEST_PROJECT}_index (
                id TEXT PRIMARY KEY,
                file_path TEXT,
                line_start INT,
                line_end INT,
                content TEXT,
                summary TEXT,
                embedding vector(768),
                summary_embedding vector(768)
            )
        """)
    db_conn.commit()
    with db_conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {TEST_PROJECT}_index")
        assert cur.fetchone()[0] == 0

def test_create_entities_table(db_conn):
    """Can create the entities table."""
    with db_conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {TEST_PROJECT}_entities (
                id TEXT PRIMARY KEY,
                file_path TEXT,
                entity_type TEXT,
                name TEXT,
                line_start INT,
                line_end INT
            )
        """)
    db_conn.commit()

def test_create_relations_table(db_conn):
    """Can create the relations table."""
    with db_conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {TEST_PROJECT}_relations (
                id TEXT PRIMARY KEY,
                from_entity TEXT,
                to_entity TEXT,
                relation_type TEXT
            )
        """)
    db_conn.commit()

def test_create_summaries_table(db_conn):
    """Can create the summaries table."""
    with db_conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {TEST_PROJECT}_summaries (
                id TEXT PRIMARY KEY,
                level TEXT,
                scope TEXT,
                content TEXT
            )
        """)
    db_conn.commit()

def test_insert_entity(db_conn):
    """Can insert an entity and read it back."""
    with db_conn.cursor() as cur:
        cur.execute(f"""
            INSERT INTO {TEST_PROJECT}_entities (id, file_path, entity_type, name, line_start, line_end)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, ("ent_1", "app/main.py", "function", "hello", 1, 5))
    db_conn.commit()
    with db_conn.cursor() as cur:
        cur.execute(f"SELECT name FROM {TEST_PROJECT}_entities WHERE id = %s", ("ent_1",))
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "hello"

def test_insert_relation(db_conn):
    """Can insert a relation between entities."""
    with db_conn.cursor() as cur:
        cur.execute(f"""
            INSERT INTO {TEST_PROJECT}_relations (id, from_entity, to_entity, relation_type)
            VALUES (%s, %s, %s, %s)
        """, ("rel_1", "ent_1", "ent_2", "calls"))
    db_conn.commit()
    with db_conn.cursor() as cur:
        cur.execute(f"SELECT relation_type FROM {TEST_PROJECT}_relations WHERE id = %s", ("rel_1",))
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "calls"

def test_insert_summary(db_conn):
    """Can insert a file-level summary."""
    with db_conn.cursor() as cur:
        cur.execute(f"""
            INSERT INTO {TEST_PROJECT}_summaries (id, level, scope, content)
            VALUES (%s, %s, %s, %s)
        """, ("sum_1", "file", "app/main.py", "Main entry point of the application."))
    db_conn.commit()
    with db_conn.cursor() as cur:
        cur.execute(f"SELECT content FROM {TEST_PROJECT}_summaries WHERE level = %s AND scope = %s",
                    ("file", "app/main.py"))
        row = cur.fetchone()
        assert row is not None
        assert "Main entry" in row[0]

def test_vector_extension_enabled(db_conn):
    """pgvector extension is installed and the <=> operator works."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT '[1,2,3]'::vector <=> '[1,2,3]'::vector")
        distance = cur.fetchone()[0]
        assert distance == pytest.approx(0.0, abs=1e-6)
```

**Input/Output Contract:**
Depends on: TASK_W14-T1 (tests/ dir and conftest.py exist)
Produces: `tests/test_db.py` with 9 integration tests

**Verify:**
```bash
cd /home/bengpu/Schreibtisch/Workspace/projekte/Toolproject/total-code-recall && python3 -m pytest tests/test_db.py -v 2>&1 | tail -20
```
All tests pass (or are skipped if `DATABASE_URL` not set — which is acceptable).

**Done when:**
`tests/test_db.py` exists. Tests either pass against a real DB or are skipped cleanly when `DATABASE_URL` is not set. No test errors (only PASS or SKIP).

---

## Start Prompt

You must not use GLM or the local Ollama LLM — you can start right away.

Read `.paul/tasks/TASK_W14-T3.md`. Write `tests/test_db.py` with the 9 integration tests. Run `python3 -m pytest tests/test_db.py -v` — tests must either PASS or SKIP cleanly (no errors). Write Execution Log, rename to `DONE_TASK_W14-T3.md`, commit: `test: TASK_W14-T3 — DB schema + entity/relation/summary/vector integration tests`.

---

## Execution Log

### Attempt 1
- Date: 2026-05-23
- Result: Created tests/test_db.py with 8 integration tests (task said 9, pattern has 8 — no discrepancy in functionality). Tests use `pytest.mark.skipif(not DATABASE_URL)` to skip cleanly when no DB is available. Result: `8 skipped in 0.04s` — all tests skip cleanly with correct reason message. No errors.
- Files Changed: tests/test_db.py (created)
- Issues: Pattern in task says "9 tests" but defines 8 — wrote all 8 defined tests
- Status: DONE
