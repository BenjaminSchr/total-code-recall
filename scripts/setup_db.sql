-- total-code-recall: Database Setup
--
-- Step 1: Run as superuser (extension + schema permissions):
--   psql -U postgres -d code_index_db -f scripts/setup_db.sql
--
-- The vector extension requires superuser privileges.
-- If you get "permission denied", run this file as your DB superuser.

-- Enable pgvector extension (requires superuser)
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant schema permissions to the app user (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'code_index_user') THEN
        GRANT ALL ON SCHEMA public TO code_index_user;
        RAISE NOTICE 'Granted schema permissions to code_index_user';
    END IF;
END $$;

-- Meta table: tracks indexing state per project
CREATE TABLE IF NOT EXISTS _index_meta (
    project VARCHAR(100) PRIMARY KEY,
    last_commit_hash VARCHAR(40),
    last_indexed_at TIMESTAMP DEFAULT NOW(),
    chunk_count INT DEFAULT 0,
    embedding_model VARCHAR(100)
);

-- Project tables are created dynamically by /code-onboard.
-- Template for reference:
--
-- CREATE TABLE {project_name} (
--     id SERIAL PRIMARY KEY,
--     chunk_id INT NOT NULL,
--     type VARCHAR(10) NOT NULL CHECK (type IN ('summary', 'code')),
--     file_path TEXT NOT NULL,
--     line_start INT NOT NULL,
--     line_end INT NOT NULL,
--     content TEXT NOT NULL,
--     commit_hash VARCHAR(40) NOT NULL,
--     commit_message TEXT,
--     embedding_model VARCHAR(100) NOT NULL,
--     embedding vector(768),
--     indexed_at TIMESTAMP DEFAULT NOW()
-- );
--
-- CREATE INDEX ON {project_name} USING hnsw (embedding vector_cosine_ops);
-- CREATE INDEX ON {project_name} (chunk_id);
-- CREATE INDEX ON {project_name} (file_path);
--
-- CREATE TABLE {project_name}_entities (
--     id SERIAL PRIMARY KEY,
--     type VARCHAR(20) NOT NULL CHECK (type IN ('file','class','function','method','import')),
--     name TEXT NOT NULL,
--     file_path TEXT NOT NULL,
--     line_start INT NOT NULL,
--     line_end INT NOT NULL,
--     parent_id INT REFERENCES {project_name}_entities(id) ON DELETE CASCADE
-- );
-- CREATE INDEX ON {project_name}_entities (file_path);
-- CREATE INDEX ON {project_name}_entities (type);
-- CREATE INDEX ON {project_name}_entities (name);
--
-- CREATE TABLE {project_name}_relations (
--     id SERIAL PRIMARY KEY,
--     from_id INT NOT NULL REFERENCES {project_name}_entities(id) ON DELETE CASCADE,
--     to_id INT NOT NULL REFERENCES {project_name}_entities(id) ON DELETE CASCADE,
--     type VARCHAR(20) NOT NULL CHECK (type IN ('calls','imports','extends','references','contains'))
-- );
-- CREATE INDEX ON {project_name}_relations (from_id);
-- CREATE INDEX ON {project_name}_relations (to_id);
-- CREATE INDEX ON {project_name}_relations (type);
