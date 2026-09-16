CREATE TABLE judge_runs (
    id uuid PRIMARY KEY,
    source_run_id uuid NOT NULL REFERENCES evaluation_runs(id) ON DELETE RESTRICT,
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    idempotency_key text UNIQUE,
    mode text NOT NULL CHECK (mode = 'demo'),
    provider text NOT NULL,
    model text NOT NULL,
    prompt_version text NOT NULL,
    status text NOT NULL CHECK (
        status IN ('queued', 'running', 'succeeded', 'failed', 'interrupted')
    ),
    source_report_sha256 text NOT NULL CHECK (source_report_sha256 ~ '^[a-f0-9]{64}$'),
    source_report jsonb NOT NULL,
    usage_kind text CHECK (usage_kind IN ('simulated', 'actual', 'unknown')),
    input_tokens integer CHECK (input_tokens >= 0),
    output_tokens integer CHECK (output_tokens >= 0),
    report jsonb,
    result_markdown text,
    error_code text,
    error_message text,
    created_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    finished_at timestamptz,
    CHECK (
        (status = 'succeeded' AND report IS NOT NULL AND result_markdown IS NOT NULL
            AND error_code IS NULL AND error_message IS NULL AND finished_at IS NOT NULL)
        OR
        (status IN ('failed', 'interrupted') AND report IS NULL AND result_markdown IS NULL
            AND error_code IS NOT NULL AND error_message IS NOT NULL AND finished_at IS NOT NULL)
        OR
        (status IN ('queued', 'running') AND report IS NULL AND result_markdown IS NULL
            AND error_code IS NULL AND error_message IS NULL AND finished_at IS NULL)
    )
);

CREATE INDEX judge_runs_queue_idx
ON judge_runs (created_at, id) WHERE status = 'queued';

CREATE INDEX judge_runs_source_idx
ON judge_runs (source_run_id, created_at DESC);
