CREATE TABLE evaluation_runs (
    id uuid PRIMARY KEY,
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    idempotency_key text UNIQUE CHECK (
        idempotency_key IS NULL OR length(idempotency_key) BETWEEN 1 AND 128
    ),
    mode text NOT NULL CHECK (mode IN ('demo', 'real')),
    provider text NOT NULL CHECK (provider <> ''),
    model text NOT NULL CHECK (model <> ''),
    prompt_version text NOT NULL CHECK (prompt_version <> ''),
    status text NOT NULL CHECK (
        status IN ('queued', 'running', 'succeeded', 'failed', 'interrupted')
    ),
    usage_kind text CHECK (usage_kind IN ('simulated', 'actual', 'estimated', 'unknown')),
    credential_slot text CHECK (credential_slot IN ('primary', 'fallback')),
    input_tokens integer CHECK (input_tokens IS NULL OR input_tokens >= 0),
    output_tokens integer CHECK (output_tokens IS NULL OR output_tokens >= 0),
    report jsonb,
    result_markdown text,
    error_code text,
    error_message text,
    created_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    finished_at timestamptz,
    CHECK (
        (status = 'succeeded' AND report IS NOT NULL AND result_markdown IS NOT NULL
            AND error_code IS NULL AND error_message IS NULL)
        OR
        (status IN ('failed', 'interrupted') AND report IS NULL AND result_markdown IS NULL
            AND error_code IS NOT NULL AND error_message IS NOT NULL)
        OR
        (status IN ('queued', 'running') AND report IS NULL AND result_markdown IS NULL
            AND error_code IS NULL AND error_message IS NULL)
    )
);

CREATE INDEX evaluation_runs_queue_idx
    ON evaluation_runs (created_at, id)
    WHERE status = 'queued';

CREATE INDEX evaluation_runs_document_idx
    ON evaluation_runs (document_id, created_at DESC);
