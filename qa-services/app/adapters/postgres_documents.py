from collections.abc import Sequence
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from app.domain.evaluation import DocumentRevision, DocumentUnit
from app.domain.documents import (
    PageExtractionStatus,
    StoredDocument,
    StoredDocumentPage,
    StoredDocumentUnit,
)
from app.services.document_service import (
    DocumentNotFoundError,
    DocumentRepositoryError,
)
from app.services.parser_service import ParsedDocument


class PostgresDocumentRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def save(self, file_name: str, document: ParsedDocument) -> StoredDocument:
        document_id = uuid4()
        try:
            with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
                row = connection.execute(
                    """
                    INSERT INTO documents (
                        id, file_name, sha256, page_count, character_count
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (sha256) DO UPDATE SET sha256 = EXCLUDED.sha256
                    RETURNING id, file_name, sha256, page_count, character_count, created_at
                    """,
                    (
                        document_id,
                        file_name,
                        document.sha256,
                        document.page_count,
                        len(document.text),
                    ),
                ).fetchone()
                if row is None:
                    raise DocumentRepositoryError("O banco não retornou o documento salvo.")

                persisted_id = row["id"]
                with connection.cursor() as cursor:
                    cursor.executemany(
                        """
                        INSERT INTO document_units (id, document_id, page, text)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        [
                            (unit.id, persisted_id, unit.page, unit.text)
                            for unit in document.units
                        ],
                    )
                    cursor.executemany(
                        """
                        INSERT INTO document_pages (
                            document_id, page, status, character_count, has_images
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (document_id, page) DO UPDATE SET
                            status = EXCLUDED.status,
                            character_count = EXCLUDED.character_count,
                            has_images = EXCLUDED.has_images
                        """,
                        [
                            (
                                persisted_id,
                                page.page,
                                page.status.value,
                                page.character_count,
                                page.has_images,
                            )
                            for page in document.pages
                        ],
                    )
                return self._document_from_row(row)
        except psycopg.Error as error:
            raise DocumentRepositoryError("A persistência do documento falhou.") from error

    def list_documents(self) -> tuple[StoredDocument, ...]:
        rows = self._fetch_all(
            """
            SELECT id, file_name, sha256, page_count, character_count, created_at
            FROM documents
            ORDER BY created_at DESC, id DESC
            LIMIT 100
            """
        )
        return tuple(self._document_from_row(row) for row in rows)

    def get(self, document_id: str) -> StoredDocument:
        try:
            parsed_id = UUID(document_id)
        except ValueError as error:
            raise DocumentNotFoundError("Documento não encontrado.") from error

        rows = self._fetch_all(
            """
            SELECT id, file_name, sha256, page_count, character_count, created_at
            FROM documents
            WHERE id = %s
            """,
            (parsed_id,),
        )
        if not rows:
            raise DocumentNotFoundError("Documento não encontrado.")
        return self._document_from_row(rows[0])

    def list_units(self, document_id: str) -> tuple[StoredDocumentUnit, ...]:
        document = self.get(document_id)
        rows = self._fetch_all(
            """
            SELECT id, document_id, page, text
            FROM document_units
            WHERE document_id = %s
            ORDER BY page
            """,
            (document.id,),
        )
        return tuple(
            StoredDocumentUnit(
                id=row["id"],
                document_id=row["document_id"],
                page=row["page"],
                text=row["text"],
            )
            for row in rows
        )

    def list_pages(self, document_id: str) -> tuple[StoredDocumentPage, ...]:
        document = self.get(document_id)
        rows = self._fetch_all(
            """
            SELECT document_id, page, status, character_count, has_images
            FROM document_pages
            WHERE document_id = %s
            ORDER BY page
            """,
            (document.id,),
        )
        return tuple(
            StoredDocumentPage(
                document_id=row["document_id"],
                page=row["page"],
                status=PageExtractionStatus(row["status"]),
                character_count=row["character_count"],
                has_images=row["has_images"],
            )
            for row in rows
        )

    def get_revision(self, document_id: str) -> DocumentRevision:
        document = self.get(document_id)
        units = self.list_units(document_id)
        return DocumentRevision(
            sha256=document.sha256,
            page_count=document.page_count,
            units=tuple(
                DocumentUnit(id=unit.id, page=unit.page, text=unit.text)
                for unit in units
            ),
        )

    def _fetch_all(
        self, query: str, parameters: Sequence[object] | None = None
    ) -> list[dict[str, object]]:
        try:
            with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
                cursor = connection.execute(query, parameters or ())
                return list(cursor.fetchall())
        except psycopg.Error as error:
            raise DocumentRepositoryError("A consulta ao banco falhou.") from error

    @staticmethod
    def _document_from_row(row: dict[str, object]) -> StoredDocument:
        return StoredDocument(
            id=row["id"],
            file_name=row["file_name"],
            sha256=row["sha256"],
            page_count=row["page_count"],
            character_count=row["character_count"],
            created_at=row["created_at"],
        )
