CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE document_unit_embeddings (
    unit_id text NOT NULL REFERENCES document_units(id) ON DELETE CASCADE,
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page integer NOT NULL CHECK (page > 0),
    model text NOT NULL CHECK (model <> ''),
    dimension integer NOT NULL CHECK (dimension = 384),
    chunk_version text NOT NULL CHECK (chunk_version <> ''),
    chunk_index integer NOT NULL CHECK (chunk_index >= 0),
    chunk_text text NOT NULL CHECK (chunk_text <> ''),
    embedding vector(384) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (unit_id, model, chunk_version, chunk_index)
);

CREATE TABLE document_embedding_indexes (
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    model text NOT NULL CHECK (model <> ''),
    dimension integer NOT NULL CHECK (dimension = 384),
    chunk_version text NOT NULL CHECK (chunk_version <> ''),
    max_tokens integer NOT NULL CHECK (max_tokens > 0),
    overlap_tokens integer NOT NULL CHECK (overlap_tokens >= 0),
    chunk_count integer NOT NULL CHECK (chunk_count > 0),
    indexed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (document_id, model, chunk_version)
);

CREATE INDEX document_unit_embeddings_document_profile_idx
ON document_unit_embeddings (document_id, model, chunk_version);

CREATE INDEX document_unit_embeddings_cosine_hnsw_idx
ON document_unit_embeddings
USING hnsw (embedding vector_cosine_ops);
