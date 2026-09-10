import io
from dataclasses import dataclass
from hashlib import sha256

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class DocumentParseError(Exception):
    """Erro esperado durante a admissão ou leitura de um documento."""


class InvalidPdfError(DocumentParseError):
    pass


class PageLimitExceededError(DocumentParseError):
    pass


class PdfWithoutTextError(DocumentParseError):
    pass


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    text: str
    page_count: int
    sha256: str


class ParserService:
    def __init__(self, max_pages: int = 300) -> None:
        self.max_pages = max_pages

    def extract_text(self, pdf_content: bytes) -> ParsedDocument:
        if not pdf_content[:1024].lstrip().startswith(b"%PDF-"):
            raise InvalidPdfError("O arquivo não possui uma assinatura PDF válida.")

        try:
            reader = PdfReader(io.BytesIO(pdf_content), strict=False)
            if reader.is_encrypted and reader.decrypt("") == 0:
                raise InvalidPdfError("PDF protegido por senha não é suportado.")

            page_count = len(reader.pages)
            if page_count == 0:
                raise InvalidPdfError("O PDF não contém páginas.")
            if page_count > self.max_pages:
                raise PageLimitExceededError(
                    f"O PDF tem {page_count} páginas; o limite atual é {self.max_pages}."
                )

            extracted_pages: list[str] = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                extracted_pages.append(page_text.strip())
        except (PdfReadError, OSError, ValueError) as error:
            raise InvalidPdfError("O PDF está inválido ou não pôde ser lido.") from error

        text = "\n\n".join(page for page in extracted_pages if page).strip()
        if not text:
            raise PdfWithoutTextError(
                "O PDF não possui texto extraível. OCR está desabilitado neste perfil."
            )

        return ParsedDocument(
            text=text,
            page_count=page_count,
            sha256=sha256(pdf_content).hexdigest(),
        )
