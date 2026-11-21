from dataclasses import fields
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from app.adapters.postgres_documents import PostgresDocumentRepository
from app.domain.catalog import (
    AcademicMetadata,
    CatalogEntry,
    CatalogEvidence,
    CatalogFilters,
    CatalogMatch,
    CatalogMatches,
    CatalogPage,
)
from app.services.catalog_service import (
    CatalogEntryNotFoundError,
    CatalogRevisionConflictError,
)
from app.services.document_service import DocumentNotFoundError, DocumentRepositoryError

METADATA_FIELDS = tuple(field.name for field in fields(AcademicMetadata))
TEXT_FILTERS = ("area", "institution", "program", "author", "advisor", "coadvisor")
ENTRY_COLUMNS = """
    document.id, document.file_name, document.sha256, document.page_count,
    document.character_count, document.created_at,
    catalog.title, catalog.document_type, catalog.publication_year,
    catalog.area, catalog.institution, catalog.program, catalog.author,
    catalog.advisor, catalog.coadvisor, catalog.source_url,
    catalog.metadata_revision, catalog.metadata_source, catalog.updated_at
"""
ENTRY_TABLES = """
    academic_catalog AS catalog
    JOIN documents AS document ON document.id = catalog.document_id
"""


class PostgresCatalogRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    @staticmethod
    def _entry(row: dict) -> CatalogEntry:
        return CatalogEntry(
            document=PostgresDocumentRepository._document_from_row(row),
            metadata=AcademicMetadata(**{name: row[name] for name in METADATA_FIELDS}),
            metadata_revision=row["metadata_revision"],
            metadata_source=row["metadata_source"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _filters(filters: CatalogFilters) -> tuple[str, list[object]]:
        clauses = ["TRUE"]
        values: list[object] = []
        for name in ("document_type", *TEXT_FILTERS):
            value = getattr(filters, name)
            if value is not None:
                # Identifiers originate only from the fixed allowlist above.
                clauses.append(f"lower(catalog.{name}) = lower(%s)")
                values.append(value)
        if filters.year_from is not None:
            clauses.append("catalog.publication_year >= %s")
            values.append(filters.year_from)
        if filters.year_to is not None:
            clauses.append("catalog.publication_year <= %s")
            values.append(filters.year_to)
        return " AND ".join(clauses), values

    def save(
        self, document_id: UUID, metadata: AcademicMetadata, expected_revision: int
    ) -> CatalogEntry:
        values = [getattr(metadata, name) for name in METADATA_FIELDS]
        try:
            with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
                document = connection.execute(
                    "SELECT id FROM documents WHERE id = %s", (document_id,)
                ).fetchone()
                if document is None:
                    raise DocumentNotFoundError("Documento não encontrado.")
                if expected_revision == 0:
                    columns = ", ".join(METADATA_FIELDS)
                    placeholders = ", ".join(["%s"] * len(METADATA_FIELDS))
                    changed = connection.execute(
                        f"""
                        INSERT INTO academic_catalog (document_id, {columns})
                        VALUES (%s, {placeholders})
                        ON CONFLICT (document_id) DO NOTHING
                        RETURNING document_id
                        """,
                        [document_id, *values],
                    ).fetchone()
                else:
                    assignments = ", ".join(f"{name} = %s" for name in METADATA_FIELDS)
                    changed = connection.execute(
                        f"""
                        UPDATE academic_catalog SET {assignments},
                            metadata_revision = metadata_revision + 1, updated_at = now()
                        WHERE document_id = %s AND metadata_revision = %s
                        RETURNING document_id
                        """,
                        [*values, document_id, expected_revision],
                    ).fetchone()
                if changed is None:
                    raise CatalogRevisionConflictError(
                        "Os metadados foram alterados. Reabra o cadastro antes de salvar."
                    )
                row = connection.execute(
                    f"SELECT {ENTRY_COLUMNS} FROM {ENTRY_TABLES} WHERE document.id = %s",
                    (document_id,),
                ).fetchone()
                return self._entry(row)
        except psycopg.Error as error:
            raise DocumentRepositoryError(
                "Não foi possível salvar o cadastro acadêmico."
            ) from error

    def get(self, document_id: UUID) -> CatalogEntry:
        try:
            with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
                row = connection.execute(
                    f"SELECT {ENTRY_COLUMNS} FROM {ENTRY_TABLES} WHERE document.id = %s",
                    (document_id,),
                ).fetchone()
        except psycopg.Error as error:
            raise DocumentRepositoryError("Não foi possível consultar o acervo.") from error
        if row is None:
            raise CatalogEntryNotFoundError("Trabalho não encontrado no acervo.")
        return self._entry(row)

    def list_entries(self, filters: CatalogFilters, limit: int, offset: int) -> CatalogPage:
        condition, parameters = self._filters(filters)
        try:
            with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
                rows = connection.execute(
                    f"""
                    WITH eligible AS (
                        SELECT {ENTRY_COLUMNS} FROM {ENTRY_TABLES} WHERE {condition}
                    ), totals AS (
                        SELECT count(*) AS total FROM eligible
                    ), paged AS (
                        SELECT * FROM eligible
                        ORDER BY updated_at DESC, id ASC LIMIT %s OFFSET %s
                    )
                    SELECT paged.*, totals.total FROM totals LEFT JOIN paged ON TRUE
                    ORDER BY paged.updated_at DESC, paged.id ASC
                    """,
                    [*parameters, limit, offset],
                ).fetchall()
        except psycopg.Error as error:
            raise DocumentRepositoryError("Não foi possível listar o acervo.") from error
        return CatalogPage(
            entries=tuple(self._entry(row) for row in rows if row["id"] is not None),
            total=rows[0]["total"],
        )

    def search(
        self, query: str, filters: CatalogFilters, limit: int, offset: int
    ) -> CatalogMatches:
        condition, parameters = self._filters(filters)
        try:
            with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
                rows = connection.execute(
                    f"""
                    WITH search_query AS (
                        SELECT websearch_to_tsquery('portuguese', %s) AS value
                    ), matches AS (
                        SELECT {ENTRY_COLUMNS}, unit.id AS unit_id, unit.page, unit.text,
                            ts_rank_cd(to_tsvector('portuguese', unit.text),
                                search_query.value, 32)::double precision AS score
                        FROM {ENTRY_TABLES}
                        JOIN document_units AS unit ON unit.document_id = document.id
                        CROSS JOIN search_query
                        WHERE {condition}
                            AND search_query.value @@ to_tsvector('portuguese', unit.text)
                    ), totals AS (
                        SELECT count(*) AS total_hits, count(DISTINCT id) AS total_documents
                        FROM matches
                    ), paged AS (
                        SELECT * FROM matches
                        ORDER BY score DESC, id ASC, page ASC, unit_id ASC
                        LIMIT %s OFFSET %s
                    )
                    SELECT paged.*, totals.total_hits, totals.total_documents
                    FROM totals LEFT JOIN paged ON TRUE
                    ORDER BY paged.score DESC, paged.id ASC, paged.page ASC, paged.unit_id ASC
                    """,
                    [query, *parameters, limit, offset],
                ).fetchall()
        except psycopg.Error as error:
            raise DocumentRepositoryError("Não foi possível pesquisar o acervo.") from error
        return CatalogMatches(
            hits=tuple(
                CatalogMatch(
                    entry=self._entry(row),
                    unit_id=row["unit_id"],
                    page=row["page"],
                    text=row["text"],
                    score=row["score"],
                )
                for row in rows
                if row["id"] is not None
            ),
            total_hits=rows[0]["total_hits"],
            total_documents=rows[0]["total_documents"],
        )

    def get_evidence(self, document_id: UUID, unit_id: str) -> CatalogEvidence:
        try:
            with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
                row = connection.execute(
                    f"""
                    SELECT {ENTRY_COLUMNS}, unit.id AS unit_id, unit.page, unit.text
                    FROM {ENTRY_TABLES}
                    JOIN document_units AS unit ON unit.document_id = document.id
                    WHERE document.id = %s AND unit.id = %s
                    """,
                    (document_id, unit_id),
                ).fetchone()
        except psycopg.Error as error:
            raise DocumentRepositoryError("Não foi possível abrir a evidência.") from error
        if row is None:
            raise CatalogEntryNotFoundError("Evidência não encontrada neste trabalho.")
        return CatalogEvidence(
            entry=self._entry(row), unit_id=row["unit_id"], page=row["page"], text=row["text"]
        )
