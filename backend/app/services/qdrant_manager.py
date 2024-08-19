# backend/app/services/qdrant_manager.py

import os
import json
import hashlib
import uuid
from qdrant_client import models, QdrantClient
from .embedder import Embedder

class QdrantManager:
    """
    QdrantManager class é responsável por gerenciar a conexão com o Qdrant e realizar operações de inserção, remoção e busca de vetores.
    """
    def __init__(self, url: str, api_key: str):
        """
        Inicializa o QdrantManager com o host e porta do Qdrant.
        
        Args:
            url (str): O endereço do Qdrant.
            api_key (str): A chave de API do Qdrant.
        """
        self.client = QdrantClient(url=url, api_key=api_key)
        self.embedder = Embedder(api_key=os.environ.get("OPENAI_API_KEY"))
    
    def create_collection(self, collection_name, vector_size, distance_metric='Cosine'):
        """
        Cria uma coleção no Qdrant.

        Args:
            collection_name (str): O nome da coleção.
            vector_size (int): O tamanho dos vetores de embedding.
            distance_metric (str): A métrica de distância (Cosine, Euclid, Dot).
        """
        distance = getattr(models.Distance, distance_metric.upper())
        self.client.recreate_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=distance
            )
        )

    def insert_document(self, collection_name, json_path):
        """
        Insere documentos na coleção do Qdrant.

        Args:
            collection_name (str): O nome da coleção.
            json_path (str): O caminho para o arquivo JSON.
        """
        document = self.__get_document(json_path)
        if document is None:
            print(f"Erro ao carregar o documento: {json_path}")
            return

        unique_id = self.__generate_unique_id(document)
        
        point = models.PointStruct(
            id=unique_id,
            vector=document["embedding"],
            payload={
                "modalidade": document["modalidade"],
                "autor": document["autor"],
                "titulo": document["titulo"],
                "tipo": document["tipo"],
                "area_de_concentracao": document["area_de_concentracao"],
                "ano_de_publicacao": document["ano_de_publicacao"],
                "local": document["local"],
                "orientador": document["orientador"],
                "coorientador": document["coorientador"],
                "resumo": document["resumo"],
                "palavras_chave": document["palavras_chave"],
                "abstract": document["abstract"],
                "keywords": document["keywords"],
                "introducao_contextualizacao": document["introducao"]["contextualizacao"],
                "introducao_problematica": document["introducao"]["problematica"],
                "introducao_ineditismo": document["introducao"]["ineditismo"],
                "introducao_contribuicao": document["introducao"]["contribuição"],
                "conclusao": document["conclusao"]
            }
        )
        self.client.upsert(
            collection_name=collection_name,
            points=[point]
        )

    def search_documents(self, collection_name, query_text, filters=None, limit=10):
        """
        Realiza uma busca genérica na coleção do Qdrant.

        Args:
            collection_name (str): O nome da coleção.
            query_text (str): Texto de consulta que será transformado em embedding.
            filters (Filter): Filtros para a consulta.
            limit (int): Limite de resultados.

        Returns:
            list: Lista de documentos encontrados com scores.
        """
        query_vector = self.embedder.get_embedding(query_text)

        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=filters,
            limit=limit,
            with_payload=True
        )
        return results

    def __get_document(self, json_path: str):
        """
        Carrega um documento JSON.

        Args:
            json_path (str): O caminho do arquivo JSON.

        Returns:
            dict: O documento JSON.
        """
        try:
            with open(json_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            print(f"Arquivo {json_path} não encontrado.")
            return None

    def __generate_unique_id(self, document):
        """
        Gera um identificador único para um documento baseado em um hash.

        Args:
            document (dict): O documento para o qual gerar o ID.

        Returns:
            uuid.UUID: O identificador único.
        """
        unique_string = f"{document['titulo']}-{document['autor']}"
        unique_id = hashlib.sha256(unique_string.encode('utf-8')).hexdigest()
        return str(uuid.UUID(unique_id[:32]))
