-- total-code-recall: Database Setup
-- Run this once against your pgvector-enabled PostgreSQL:
--   psql -U code_index_user -d code_index_db -f scripts/setup_db.sql

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

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
