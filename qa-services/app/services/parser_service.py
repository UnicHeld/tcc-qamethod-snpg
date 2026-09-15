import io
from dataclasses import dataclass
from hashlib import sha256

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.domain.documents import PageExtractionStatus
from app.domain.evaluation import DocumentRevision, DocumentUnit


class DocumentParseError(Exception):
    """Erro esperado durante a admissão ou leitura de um documento."""


class InvalidPdfError(DocumentParseError):
    pass


class PageLimitExceededError(DocumentParseError):
    pass


class PdfWithoutTextError(DocumentParseError):
    pass


@dataclass(frozen=True, slots=True)
class ParsedDocumentPage:
    page: int
    status: PageExtractionStatus
    character_count: int
    has_images: bool


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    text: str
    page_count: int
    sha256: str
    units: tuple[DocumentUnit, ...] = ()
    pages: tuple[ParsedDocumentPage, ...] = ()

    def as_revision(self) -> DocumentRevision:
        return DocumentRevision(sha256=self.sha256, page_count=self.page_count, units=self.units)


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
            parsed_pages: list[ParsedDocumentPage] = []
            for page_number, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                page_text = page_text.strip()
                extracted_pages.append(page_text)
                has_images = self._has_raster_images(page)
                status = PageExtractionStatus.EXTRACTED
                if not page_text:
                    status = (
                        PageExtractionStatus.OCR_CANDIDATE
                        if has_images
                        else PageExtractionStatus.NO_TEXT
                    )
                parsed_pages.append(
                    ParsedDocumentPage(
                        page=page_number,
                        status=status,
                        character_count=len(page_text),
                        has_images=has_images,
                    )
                )
        except (PdfReadError, OSError, ValueError) as error:
            raise InvalidPdfError("O PDF está inválido ou não pôde ser lido.") from error

        text = "\n\n".join(page for page in extracted_pages if page).strip()
        if not text:
            ocr_candidates = sum(
                page.status is PageExtractionStatus.OCR_CANDIDATE for page in parsed_pages
            )
            if ocr_candidates:
                raise PdfWithoutTextError(
                    "O PDF não possui texto extraível e contém "
                    f"{ocr_candidates} página(s) candidata(s) a OCR. "
                    "OCR está desabilitado neste perfil."
                )
            raise PdfWithoutTextError(
                "O PDF não possui texto extraível nem imagem raster detectável. "
                "OCR está desabilitado neste perfil."
            )

        document_hash = sha256(pdf_content).hexdigest()
        units = tuple(
            DocumentUnit(id=f"{document_hash}:page:{number}", page=number, text=page_text)
            for number, page_text in enumerate(extracted_pages, start=1)
            if page_text
        )
        return ParsedDocument(
            text=text,
            page_count=page_count,
            sha256=document_hash,
            units=units,
            pages=tuple(parsed_pages),
        )

    @staticmethod
    def _has_raster_images(page: object) -> bool:
        try:
            resources = page.get("/Resources")
            if resources is None:
                return False
            resources = resources.get_object()
            xobjects = resources.get("/XObject")
            if xobjects is None:
                return False
            xobjects = xobjects.get_object()
            return any(
                reference.get_object().get("/Subtype") == "/Image"
                for reference in xobjects.values()
            )
        except (AttributeError, KeyError, TypeError, ValueError):
            return False
