import io
import pikepdf
from PyPDF2 import PdfReader

class ParserService:
    def __init__(self):
        pass
    
    def extrair_texto(self, pdf_content: bytes) -> str:
        try:
            # Tenta carregar o PDF a partir do conteúdo em bytes
            reader = PdfReader(io.BytesIO(pdf_content))
            texto_extraido = []
            for page in reader.pages:
                texto_extraido.append(page.extract_text())
            
            return "\n".join(texto_extraido)
        except Exception as e:
            print(f"Erro ao extrair texto: {e}")
            print("Tentando reparar o PDF...")
            
            # Se ocorrer um erro, tenta reparar o PDF
            pdf_content_reparado = self.reparar_pdf(pdf_content)
            if pdf_content_reparado:
                # Tenta novamente extrair o texto do PDF reparado
                reader = PdfReader(io.BytesIO(pdf_content_reparado))
                texto_extraido = []
                for page in reader.pages:
                    texto_extraido.append(page.extract_text())
                return "\n".join(texto_extraido)
            else:
                raise Exception("PDF corrompido e não foi possível repará-lo.")
    
    def reparar_pdf(self, pdf_content: bytes) -> bytes:
        try:
            # Repara o PDF em memória sem salvar em disco
            with pikepdf.open(io.BytesIO(pdf_content)) as pdf:
                reparado_stream = io.BytesIO()
                pdf.save(reparado_stream)
                print("PDF reparado com sucesso.")
                return reparado_stream.getvalue()
        except pikepdf.PdfError as e:
            print(f"Erro ao reparar PDF: {e}")
            return None
