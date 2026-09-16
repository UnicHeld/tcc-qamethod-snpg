CREATE TABLE rag_insight_runs (
    id uuid PRIMARY KEY,
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    idempotency_key text UNIQUE,
    question text NOT NULL CHECK (char_length(question) BETWEEN 1 AND 200),
    retrieval_mode text NOT NULL CHECK (retrieval_mode IN ('lexical', 'vector')),
    retrieval_limit integer NOT NULL CHECK (retrieval_limit BETWEEN 1 AND 10),
    mode text NOT NULL CHECK (mode IN ('demo', 'real')),
    provider text NOT NULL,
    model text NOT NULL,
    prompt_version text NOT NULL,
    status text NOT NULL CHECK (
        status IN ('queued', 'running', 'succeeded', 'failed', 'interrupted')
    ),
    usage_kind text CHECK (usage_kind IN ('simulated', 'actual', 'estimated', 'unknown')),
    credential_slot text CHECK (credential_slot IN ('primary', 'fallback')),
    input_tokens integer CHECK (input_tokens IS NULL OR input_tokens >= 0),
    output_tokens integer CHECK (output_tokens IS NULL OR output_tokens >= 0),
    evidence_package jsonb,
    report jsonb,
    result_markdown text,
    error_code text,
    error_message text,
    created_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    finished_at timestamptz,
    CHECK (
        (status = 'succeeded' AND evidence_package IS NOT NULL AND report IS NOT NULL
            AND result_markdown IS NOT NULL AND error_code IS NULL AND error_message IS NULL)
        OR
        (status IN ('failed', 'interrupted') AND evidence_package IS NULL AND report IS NULL
            AND result_markdown IS NULL AND error_code IS NOT NULL AND error_message IS NOT NULL)
        OR
        (status IN ('queued', 'running') AND evidence_package IS NULL AND report IS NULL
            AND result_markdown IS NULL AND error_code IS NULL AND error_message IS NULL)
    )
);

CREATE INDEX rag_insight_runs_queue_idx
ON rag_insight_runs (created_at, id) WHERE status = 'queued';

CREATE INDEX rag_insight_runs_document_idx
ON rag_insight_runs (document_id, created_at DESC);
