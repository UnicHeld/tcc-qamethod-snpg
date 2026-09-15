CREATE INDEX document_units_portuguese_fts_idx
ON document_units
USING gin (to_tsvector('portuguese', text));
