from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from ..services.parser_service import ParserService
from ..services.evaluation_service import EvalationService

# Inicializar os serviços
parser_service = ParserService()
evaluation_service = EvalationService()

router = APIRouter()

@router.post("/upload")
async def carregar_documento(file: UploadFile = File(...)):
    """
    Endpoint para carregar um arquivo PDF e gerar uma análise crítica
    """
    try:
        # Verificar se o arquivo é um PDF
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Apenas arquivos PDF são aceitos.")

        # Extrair o conteúdo do PDF
        original_path = file.filename
        pdf_content = await file.read()  # Ler o conteúdo do PDF
        texto = parser_service.extrair_texto(pdf_content)  # Extrair o texto do PDF
        
        # Gerar a análise crítica usando o EvalationService
        response_chunks = evaluation_service.evaluation_generate(texto)

        # Função para fazer o streaming da resposta em partes
        def stream_response():
            for chunk in response_chunks:
                yield chunk

        # Retornar a resposta como StreamingResponse
        return StreamingResponse(stream_response(), media_type="text/plain", headers={"Original-Path": original_path})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
