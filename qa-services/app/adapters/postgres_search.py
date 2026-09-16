import math

import psycopg
from psycopg.rows import dict_row

from app.adapters.postgres_documents import PostgresDocumentRepository
from app.domain.search import (
    EmbeddedChunk,
    EmbeddingProfile,
    LexicalMatch,
    VectorMatch,
)
from app.services.document_service import DocumentRepositoryError
from app.services.search_service import VectorSearchUnavailableError


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

    def list_units(self, document_id: str):
        return PostgresDocumentRepository(self.database_url).list_units(document_id)

    def is_vector_indexed(
        self, document_id: str, profile: EmbeddingProfile
    ) -> bool:
        document = PostgresDocumentRepository(self.database_url).get(document_id)
        try:
            with psycopg.connect(self.database_url) as connection:
                row = connection.execute(
                    """
                    SELECT chunk_count
                    FROM document_embedding_indexes
                    WHERE document_id = %s
                      AND model = %s
                      AND dimension = %s
                      AND chunk_version = %s
                      AND max_tokens = %s
                      AND overlap_tokens = %s
                    """,
                    (
                        document.id,
                        profile.model,
                        profile.dimension,
                        profile.chunk_version,
                        profile.max_tokens,
                        profile.overlap_tokens,
                    ),
                ).fetchone()
                return row is not None and row[0] > 0
        except (psycopg.errors.UndefinedTable, psycopg.errors.UndefinedObject) as error:
            raise VectorSearchUnavailableError(
                "A extensão pgvector ou a migração vetorial não está disponível."
            ) from error
        except psycopg.Error as error:
            raise DocumentRepositoryError("A consulta ao índice vetorial falhou.") from error

    def replace_vector_index(
        self,
        document_id: str,
        profile: EmbeddingProfile,
        chunks: tuple[EmbeddedChunk, ...],
    ) -> None:
        document = PostgresDocumentRepository(self.database_url).get(document_id)
        if not chunks:
            raise VectorSearchUnavailableError(
                "O documento não contém texto suficiente para indexação vetorial."
            )
        try:
            with psycopg.connect(self.database_url) as connection:
                connection.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s))", (str(document.id),)
                )
                connection.execute(
                    """
                    DELETE FROM document_unit_embeddings
                    WHERE document_id = %s AND model = %s AND chunk_version = %s
                    """,
                    (document.id, profile.model, profile.chunk_version),
                )
                with connection.cursor() as cursor:
                    cursor.executemany(
                        """
                        INSERT INTO document_unit_embeddings (
                            unit_id, document_id, page, model, dimension, chunk_version,
                            chunk_index, chunk_text, embedding
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
                        """,
                        [
                            (
                                chunk.unit_id,
                                document.id,
                                chunk.page,
                                profile.model,
                                profile.dimension,
                                profile.chunk_version,
                                chunk.chunk_index,
                                chunk.text,
                                self._vector_literal(chunk.embedding, profile.dimension),
                            )
                            for chunk in chunks
                        ],
                    )
                connection.execute(
                    """
                    INSERT INTO document_embedding_indexes (
                        document_id, model, dimension, chunk_version, max_tokens,
                        overlap_tokens, chunk_count, indexed_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (document_id, model, chunk_version) DO UPDATE SET
                        dimension = EXCLUDED.dimension,
                        max_tokens = EXCLUDED.max_tokens,
                        overlap_tokens = EXCLUDED.overlap_tokens,
                        chunk_count = EXCLUDED.chunk_count,
                        indexed_at = EXCLUDED.indexed_at
                    """,
                    (
                        document.id,
                        profile.model,
                        profile.dimension,
                        profile.chunk_version,
                        profile.max_tokens,
                        profile.overlap_tokens,
                        len(chunks),
                    ),
                )
        except (psycopg.errors.UndefinedTable, psycopg.errors.UndefinedObject) as error:
            raise VectorSearchUnavailableError(
                "A extensão pgvector ou a migração vetorial não está disponível."
            ) from error
        except psycopg.Error as error:
            raise DocumentRepositoryError("A gravação do índice vetorial falhou.") from error

    def search_vector(
        self,
        document_id: str,
        profile: EmbeddingProfile,
        query_embedding: tuple[float, ...],
        limit: int,
    ) -> tuple[VectorMatch, ...]:
        document = PostgresDocumentRepository(self.database_url).get(document_id)
        vector = self._vector_literal(query_embedding, profile.dimension)
        try:
            with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
                rows = connection.execute(
                    """
                    SELECT
                        unit_id,
                        document_id,
                        page,
                        chunk_index,
                        chunk_text,
                        GREATEST(0, 1 - (embedding <=> %s::vector))::double precision AS score
                    FROM document_unit_embeddings
                    WHERE document_id = %s AND model = %s AND chunk_version = %s
                    ORDER BY embedding <=> %s::vector, page ASC, chunk_index ASC, unit_id ASC
                    LIMIT %s
                    """,
                    (
                        vector,
                        document.id,
                        profile.model,
                        profile.chunk_version,
                        vector,
                        limit,
                    ),
                ).fetchall()
        except (psycopg.errors.UndefinedTable, psycopg.errors.UndefinedObject) as error:
            raise VectorSearchUnavailableError(
                "A extensão pgvector ou a migração vetorial não está disponível."
            ) from error
        except psycopg.Error as error:
            raise DocumentRepositoryError("A busca vetorial no banco falhou.") from error

        return tuple(
            VectorMatch(
                unit_id=row["unit_id"],
                document_id=row["document_id"],
                page=row["page"],
                chunk_index=row["chunk_index"],
                text=row["chunk_text"],
                score=row["score"],
            )
            for row in rows
        )

    @staticmethod
    def _vector_literal(values: tuple[float, ...], dimension: int) -> str:
        if len(values) != dimension or not all(math.isfinite(value) for value in values):
            raise VectorSearchUnavailableError("O modelo retornou um embedding inválido.")
        return "[" + ",".join(format(value, ".9g") for value in values) + "]"
