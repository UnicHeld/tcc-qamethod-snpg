import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from ..services.parser_service import ParserService
from ..services.extract_content import ExtractContentService
from pydantic import BaseModel

class Conteudo(BaseModel):
    conteudo: str
    original_path: str

router = APIRouter()

parser_service = ParserService()
extract_content_service = ExtractContentService()

@router.post("/")
async def carregar_documento(file: UploadFile = File(...)):
    try:
        original_path = file.filename
        content = await file.read()
        texto = parser_service.extrair_texto(content)
        response_chunks = extract_content_service.extrair_dados_llm(texto)
        
        def stream_response():
            for chunk in response_chunks:
                yield chunk

        return StreamingResponse(stream_response(), media_type="text/plain", headers={"Original-Path": original_path})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/salvar_json/")
async def salvar_json(conteudo: Conteudo):
    try:
        # Remove extra markdown formatting if present
        clean_content = conteudo.conteudo.strip('```json').strip('```').strip()

        original_path = conteudo.original_path
        base_dir = original_path.replace("data/pdf/", "data/json/")
        output_path = f"{os.path.splitext(base_dir)[0]}.json"
        
        extract_content_service.save_default_json(clean_content, output_path)
        return {"message": "Arquivo JSON salvo com sucesso!", "path": output_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))