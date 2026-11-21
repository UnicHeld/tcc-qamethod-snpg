CREATE TABLE academic_catalog (
    document_id uuid PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
    title text NOT NULL CHECK (length(btrim(title)) BETWEEN 1 AND 500),
    document_type text CHECK (document_type IN ('thesis', 'dissertation', 'other')),
    publication_year integer CHECK (publication_year BETWEEN 1600 AND 2100),
    area text,
    institution text,
    program text,
    author text,
    advisor text,
    coadvisor text,
    source_url text,
    metadata_source text NOT NULL DEFAULT 'manual' CHECK (metadata_source = 'manual'),
    metadata_revision integer NOT NULL DEFAULT 1 CHECK (metadata_revision > 0),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX academic_catalog_year_type_idx
    ON academic_catalog (publication_year, document_type);
CREATE INDEX academic_catalog_institution_idx ON academic_catalog (lower(institution));
CREATE INDEX academic_catalog_program_idx ON academic_catalog (lower(program));
CREATE INDEX academic_catalog_area_idx ON academic_catalog (lower(area));
CREATE INDEX academic_catalog_advisor_idx ON academic_catalog (lower(advisor));
