import pytest
import psycopg2
import os
import uuid


# Skip all tests if no DB available
DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set — skipping DB integration tests",
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
        cur.execute(
            f"""
            INSERT INTO {TEST_PROJECT}_entities (id, file_path, entity_type, name, line_start, line_end)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            ("ent_1", "app/main.py", "function", "hello", 1, 5),
        )
    db_conn.commit()
    with db_conn.cursor() as cur:
        cur.execute(
            f"SELECT name FROM {TEST_PROJECT}_entities WHERE id = %s",
            ("ent_1",),
        )
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "hello"


def test_insert_relation(db_conn):
    """Can insert a relation between entities."""
    with db_conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO {TEST_PROJECT}_relations (id, from_entity, to_entity, relation_type)
            VALUES (%s, %s, %s, %s)
            """,
            ("rel_1", "ent_1", "ent_2", "calls"),
        )
    db_conn.commit()
    with db_conn.cursor() as cur:
        cur.execute(
            f"SELECT relation_type FROM {TEST_PROJECT}_relations WHERE id = %s",
            ("rel_1",),
        )
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "calls"


def test_insert_summary(db_conn):
    """Can insert a file-level summary."""
    with db_conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO {TEST_PROJECT}_summaries (id, level, scope, content)
            VALUES (%s, %s, %s, %s)
            """,
            ("sum_1", "file", "app/main.py", "Main entry point of the application."),
        )
    db_conn.commit()
    with db_conn.cursor() as cur:
        cur.execute(
            f"SELECT content FROM {TEST_PROJECT}_summaries WHERE level = %s AND scope = %s",
            ("file", "app/main.py"),
        )
        row = cur.fetchone()
        assert row is not None
        assert "Main entry" in row[0]


def test_vector_extension_enabled(db_conn):
    """pgvector extension is installed and the <=> operator works."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT '[1,2,3]'::vector <=> '[1,2,3]'::vector")
        distance = cur.fetchone()[0]
        assert distance == pytest.approx(0.0, abs=1e-6)
