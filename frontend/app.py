# frontend/app.py

import streamlit as st

from db_view import visualizacao_database
from extract_content import extracao_conteudo
from introduction import show_introduction
from graph_generation import geracao_grafos
from semantic_research import recuperacao_semantica
from text_summarization import sumarizacao_textos

st.set_page_config(page_title="D&T Retrieval System", layout="wide")

def main():
    with st.sidebar:
        st.title("Navegação")
        service = st.radio("Escolha um serviço:", [
            "Introdução",
            "Extração de Conteúdo (D&T)",
            "Visualização do Database",
            "Sumarização de Textos",
            "Recuperação Semântica",
            "Geração de Grafos"
        ])

    if service == "Introdução":
        show_introduction()
    elif service == "Extração de Conteúdo (D&T)":
        extracao_conteudo()
    elif service == "Visualização do Database":
        visualizacao_database()
    elif service == "Sumarização de Textos":
        sumarizacao_textos()
    elif service == "Recuperação Semântica":
        recuperacao_semantica()
    elif service == "Geração de Grafos":
        geracao_grafos()

if __name__ == "__main__":
    main()
