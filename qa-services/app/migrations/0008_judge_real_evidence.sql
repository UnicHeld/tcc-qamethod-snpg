ALTER TABLE judge_runs
ADD COLUMN source_evidence jsonb,
ADD COLUMN credential_slot text CHECK (credential_slot IN ('primary', 'fallback'));

ALTER TABLE judge_runs
DROP CONSTRAINT judge_runs_mode_check;

ALTER TABLE judge_runs
ADD CONSTRAINT judge_runs_mode_check CHECK (mode IN ('demo', 'real'));

UPDATE judge_runs AS judge
SET source_evidence = jsonb_build_object(
    'document_id', judge.document_id,
    'revision_sha256', judge.source_report->>'revision_sha256',
    'source_report_sha256', judge.source_report_sha256,
    'items', COALESCE(
        (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'unit_id', unit.id,
                    'page', unit.page,
                    'text', unit.text
                )
                ORDER BY unit.page, unit.id
            )
            FROM document_units AS unit
            WHERE unit.document_id = judge.document_id
              AND unit.id IN (
                  SELECT jsonb_array_elements_text(dimension.item->'evidence_ids')
                  FROM jsonb_array_elements(judge.source_report->'dimensions') AS dimension(item)
              )
        ),
        '[]'::jsonb
    )
);

ALTER TABLE judge_runs
ALTER COLUMN source_evidence SET NOT NULL;
