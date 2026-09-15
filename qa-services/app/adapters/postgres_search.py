import psycopg
from psycopg.rows import dict_row

from app.adapters.postgres_documents import PostgresDocumentRepository
from app.domain.search import LexicalMatch
from app.services.document_service import DocumentRepositoryError


class PostgresSearchRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def search_lexical(
        self, document_id: str, query: str, limit: int
    ) -> tuple[LexicalMatch, ...]:
        document = PostgresDocumentRepository(self.database_url).get(document_id)
        try:
            with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
                rows = connection.execute(
                    """
                    WITH search_query AS (
                        SELECT websearch_to_tsquery('portuguese', %s) AS value
                    )
                    SELECT
                        unit.id AS unit_id,
                        unit.document_id,
                        unit.page,
                        unit.text,
                        ts_rank_cd(
                            to_tsvector('portuguese', unit.text),
                            search_query.value,
                            32
                        )::double precision AS score
                    FROM document_units AS unit
                    CROSS JOIN search_query
                    WHERE unit.document_id = %s
                      AND search_query.value @@ to_tsvector('portuguese', unit.text)
                    ORDER BY score DESC, unit.page ASC, unit.id ASC
                    LIMIT %s
                    """,
                    (query, document.id, limit),
                ).fetchall()
        except psycopg.Error as error:
            raise DocumentRepositoryError("A busca no banco falhou.") from error

        return tuple(
            LexicalMatch(
                unit_id=row["unit_id"],
                document_id=row["document_id"],
                page=row["page"],
                text=row["text"],
                score=row["score"],
            )
            for row in rows
        )
