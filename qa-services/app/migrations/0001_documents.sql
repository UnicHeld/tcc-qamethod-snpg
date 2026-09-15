CREATE TABLE documents (
    id uuid PRIMARY KEY,
    file_name text NOT NULL CHECK (file_name <> ''),
    sha256 text NOT NULL UNIQUE CHECK (sha256 ~ '^[a-f0-9]{64}$'),
    page_count integer NOT NULL CHECK (page_count > 0),
    character_count integer NOT NULL CHECK (character_count > 0),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE document_units (
    id text PRIMARY KEY,
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page integer NOT NULL CHECK (page > 0),
    text text NOT NULL CHECK (text <> ''),
    UNIQUE (document_id, page)
);

CREATE INDEX document_units_document_id_idx ON document_units (document_id, page);
