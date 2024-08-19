# frontend/extract_content.py

import streamlit as st
import requests
import json

def extracao_conteudo():
    st.header("Extração de Conteúdo - Dissertação e Tese")
    base_path = "data/pdf/"
    uploaded_file = st.file_uploader("Escolha um arquivo PDF", type="pdf")

    if uploaded_file is not None:
        files = {'file': uploaded_file.getvalue()}
        file_name = uploaded_file.name
        original_path = base_path + file_name
        with st.spinner('Processando...'):
            print(original_path)
            response = requests.post("http://localhost:8000/documentos/", files=files, stream=True)

        if response.status_code == 200:
            st.write("### Conteúdo Extraído")
            content_area = st.empty()
            full_content = ""
            for chunk in response.iter_lines():
                if chunk:
                    full_content += chunk.decode('utf-8') + "\n"
                    content_area.write(full_content)
            
            if not full_content.strip():
                st.error("O conteúdo extraído está vazio.")
                return

            # Remove any extra markdown formatting if present
            clean_content = full_content.strip('```json').strip('```').strip()

            # Enviar o full_content para salvar como JSON padronizado
            payload = {"conteudo": clean_content, "original_path": original_path}
            headers = {'Content-Type': 'application/json'}
            save_response = requests.post("http://localhost:8000/documentos/salvar_json/", data=json.dumps(payload), headers=headers)
            if save_response.status_code == 200:
                st.success("Arquivo JSON salvo com sucesso!")
                st.write(save_response.json())
            else:
                st.error(f"Erro ao salvar o arquivo JSON: {save_response.status_code} - {save_response.text}")

        elif response.status_code == 403:
            st.error("Erro 403: Acesso proibido. Verifique as configurações da API.")
        else:
            st.error(f"Erro ao processar o documento: {response.status_code} - {response.text}")

