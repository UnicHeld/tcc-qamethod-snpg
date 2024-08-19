# backend/app/services/embedder.py

import json
from openai import OpenAI

class Embedder:
    """
    Uma classe para gerar embeddings para o conteúdo de um arquivo JSON usando a API da OpenAI.
    """
    def __init__(self, api_key, embedding_model="text-embedding-3-small"):
        """
        Inicializa a classe Embedder com a chave da API da OpenAI e o modelo de embedding especificado.

        Args:
            api_key (str): A chave da API para acessar a API da OpenAI.
            embedding_model (str): O modelo de embedding a ser usado. Padrão é "text-embedding-3-small".
        """
        self.client = OpenAI(api_key=api_key)
        self.embedding_model = embedding_model

    def _concatenate_json_content(self, json_content):
        """
        Concatena o conteúdo de um objeto JSON em uma única string.

        Args:
            json_content (dict): O conteúdo JSON a ser concatenado.

        Returns:
            str: A string concatenada a partir do conteúdo JSON.
        """
        content_to_embed = (
            "Título: " + json_content.get("titulo", "") + "\n" +
            "Área de concentração: " + json_content.get("area_de_concentracao", "") + "\n" +
            "Resumo: " + json_content.get("resumo", "") + "\n" +
            "Palavras-chave: " + ", ".join(json_content.get("palavras_chave", [])) + "\n" +
            "Abstract: " + json_content.get("abstract", "") + "\n" +
            "Keywords: " + ", ".join(json_content.get("keywords", [])) + "\n" +
            "Introdução - Contextualização: " + json_content.get("introducao", {}).get("contextualizacao", "") + "\n" +
            "Introdução - Problematica: " + json_content.get("introducao", {}).get("problematica", "") + "\n" +
            "Introdução - Ineditismo: " + json_content.get("introducao", {}).get("ineditismo", "") + "\n" +
            "Introdução - Contribuição: " + json_content.get("introducao", {}).get("contribuição", "") + "\n" +
            "Conclusão: " + json_content.get("conclusao", "")
        )
        return content_to_embed

    def get_embedding(self, text):
        """
        Gera um embedding para um determinado texto usando o modelo especificado.

        Args:
            text (str): O texto a ser embeddado.

        Returns:
            list: O vetor de embedding para o texto fornecido.
        """
        try:
            text = text.replace("\n", " ")
            embedding_response = self.client.embeddings.create(input=[text], model=self.embedding_model)
            return embedding_response.data[0].embedding
        except Exception as e:
            print(f"Erro ao gerar o embedding: {e}")
            return None

    def _read_json_file(self, file_path):
        """
        Lê um arquivo JSON do caminho especificado.

        Args:
            file_path (str): O caminho para o arquivo JSON.

        Returns:
            dict: O conteúdo do arquivo JSON.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as e:
            print(f"Erro ao ler o arquivo JSON: {e}")
            return None

    def _write_json_file(self, file_path, content):
        """
        Escreve o conteúdo em um arquivo JSON no caminho especificado.

        Args:
            file_path (str): O caminho para o arquivo JSON.
            content (dict): O conteúdo a ser escrito no arquivo JSON.
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(content, file, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Erro ao escrever no arquivo JSON: {e}")

    def add_embedding_to_json(self, file_path):
        """
        Adiciona um embedding ao conteúdo JSON no caminho de arquivo especificado. Se o embedding já existir
        no conteúdo JSON, ele pula a geração do embedding.

        Args:
            file_path (str): O caminho para o arquivo JSON.

        Returns:
            dict: O conteúdo JSON atualizado com o embedding.
        """
        json_content = self._read_json_file(file_path)
        if json_content is None:
            return None

        if "embedding" in json_content:
            print("Embedding já existe no conteúdo JSON. Pulando a geração do embedding.")
            return json_content

        content_to_embed = self._concatenate_json_content(json_content)
        embedding = self.get_embedding(content_to_embed)
        
        if embedding is not None:
            json_content["embedding"] = embedding
            self._write_json_file(file_path, json_content)

        return json_content
