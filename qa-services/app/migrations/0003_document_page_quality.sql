CREATE TABLE document_pages (
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page integer NOT NULL CHECK (page > 0),
    status text NOT NULL CHECK (status IN ('extracted', 'ocr_candidate', 'no_text')),
    character_count integer NOT NULL CHECK (character_count >= 0),
    has_images boolean NOT NULL,
    PRIMARY KEY (document_id, page),
    CHECK (
        (status = 'extracted' AND character_count > 0)
        OR (status IN ('ocr_candidate', 'no_text') AND character_count = 0)
    ),
    CHECK (status <> 'ocr_candidate' OR has_images)
);

INSERT INTO document_pages (document_id, page, status, character_count, has_images)
SELECT
    document.id,
    page_number,
    CASE WHEN unit.id IS NULL THEN 'no_text' ELSE 'extracted' END,
    COALESCE(length(unit.text), 0),
    false
FROM documents AS document
CROSS JOIN LATERAL generate_series(1, document.page_count) AS generated(page_number)
LEFT JOIN document_units AS unit
    ON unit.document_id = document.id AND unit.page = page_number;

CREATE INDEX document_pages_status_idx ON document_pages (document_id, status, page);
