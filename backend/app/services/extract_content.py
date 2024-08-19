# backend/app/services/extract_content.py

import google.generativeai as genai
import os
import json

class ExtractContentService:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def extrair_dados_llm(self, texto: str):
        prompt = f"""
        Extraia o conteúdo da dissertação/tese colocando-o em um JSON estruturado seguindo as {{REGRAS}}. As informações extraídas devem ser exatas e precisas, como constam no documento, além disso, o documento não pode ultrapassar 8000 tokens.

        {{ROTEIRO}}
        {{
            "autor": "",
            "titulo": "",
            "tipo": "",
            "area_de_concentracao": "",
            "ano_de_publicacao": "",
            "local": "",
            "orientador": "",
            "coorientador": "",
            "resumo": "",
            "palavras_chave": [],
            "abstract": "",
            "keywords": [],
            "introducao": {{
                "contextualizacao": "",
                "problematica": "",
                "ineditismo": "",
                "contribuição": ""
            }},
            "conclusao": ""
        }}

        {{REGRAS}}
        > O conteúdo extraído deve ser retornado em JSON no formato do {{ROTEIRO}}, sem alterações em suas chaves.
        > Tipo é tese ou dissertação.
        > Área de concentração é a área principal da tese/dissertação que pode ser obtida na subseção de aderência.
        > Ano de publicação é o ano no formato de 4 dígitos, por exemplo, 2023.
        > Local é a cidade que consta no documento.
        > Orientador, Coorientador, Resumo, Abstract, Palavras-Chave, Keywords devem ser exatamente iguais ao que consta no documento.
        > Introdução e Conclusão devem ser sumarizados não excedendo 4000 tokens.
        > Introdução deve retornar uma síntese do texto da introdução, separada em Contextualização e Problemática.
        > Somente se o documento for uma tese, a introdução deve apresentar ainda o Ineditismo e a Contribuição, caso contrário, esses campos devem ser vazios.
        > Conclusão deve retornar uma síntese detalhada do texto que se encontra na seção "conclusao" ou "CONSIDERAÇÕES FINAIS" e antes da seção de "REFERÊNCIAS BIBLIOGRÁFICAS".
        """
        
        response = self.model.generate_content(contents=prompt + '\n\nDocumento: ' + texto, stream=True)
        for chunk in response:
            yield chunk.text
        
    def convert_to_json(self, content: str) -> dict:
        if not content.strip():
            print("Conteúdo está vazio ou em branco.")
            return {}

        try:
            json_content = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Erro ao converter o conteúdo para JSON: {e}")
            json_content = {}
        return json_content

    def padronizar_conteudo(self, content: dict) -> dict:
        padrao = {
            "autor": "",
            "titulo": "",
            "tipo": "",
            "area_de_concentracao": "",
            "ano_de_publicacao": "",
            "local": "",
            "orientador": "",
            "coorientador": "",
            "resumo": "",
            "palavras_chave": [],
            "abstract": "",
            "keywords": [],
            "introducao": {
                "contextualizacao": "",
                "problematica": "",
                "ineditismo": "",
                "contribuição": ""
            },
            "conclusao": ""
        }

        def padronizar(d, padrao):
            if isinstance(padrao, dict):
                return {k: padronizar(d.get(k, v), v) for k, v in padrao.items()}
            else:
                return d if d else padrao

        return padronizar(content, padrao)

    def save_default_json(self, content: str, output_path: str) -> None:
        json_content = self.convert_to_json(content)
        padronizado_content = self.padronizar_conteudo(json_content)
        self.save_json_file(output_path, padronizado_content)

    def save_json_file(self, output_path: str, json_content: dict) -> None:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as file:
            json.dump(json_content, file, indent=4, ensure_ascii=False)
