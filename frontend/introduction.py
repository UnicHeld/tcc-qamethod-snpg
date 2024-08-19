# frontend/introduction.py

import streamlit as st

def show_introduction():
    st.markdown(
        "<h1 style='text-align: center;'>D&T Retrieval System</h1>",
        unsafe_allow_html=True
    )
    st.write("""
    Bem-vindo ao D&T Retrieval System, uma ferramenta inovadora desenvolvida para otimizar a recuperação de informações de teses e dissertações no contexto do Sistema Nacional de Pós-Graduação (SNPG) brasileiro.
    
    ### Sobre o Projeto
    Este projeto foi idealizado para enfrentar os desafios de acesso e análise de informações específicas em um vasto repositório de conhecimento especializado, frequentemente disponibilizado em formatos como PDF. A dificuldade em acessar e analisar esses documentos acadêmicos é um problema significativo devido à limitação dos sistemas de busca convencionais.

    ### Solução
    O D&T Retrieval System utiliza modelos de linguagem de grande escala (Large Language Models - LLMs), especificamente o **Gemini da Google**, para proporcionar uma busca eficiente e respostas contextualizadas às perguntas formuladas em linguagem natural. Nossa abordagem combina o poder dos LLMs com técnicas avançadas de Processamento de Linguagem Natural (PLN) para transformar a maneira como interagimos com grandes volumes de textos acadêmicos.

    ### Gemini: A Tecnologia por Trás do Sistema
    Desenvolvidos pela Google DeepMind, os modelos Gemini são alguns dos mais avançados e versáteis disponíveis atualmente. O **Gemini 1.5 Flash**, por exemplo, é otimizado para velocidade e eficiência, permitindo um processamento rápido e custo-efetivo. Ele suporta uma janela de contexto de até um milhão de tokens, possibilitando o processamento de grandes quantidades de dados textuais, como longos documentos acadêmicos, códigos extensos e horas de áudio e vídeo.

    O **Gemini 1.5 Pro** expande ainda mais essas capacidades com uma janela de contexto de até dois milhões de tokens, o que é ideal para tarefas que exigem alta precisão e entendimento de contexto prolongado. Estes modelos são nativamente multimodais, combinando e entendendo texto, código, imagens, áudio e vídeo&.

    ### Funcionalidades
    Explore os diversos serviços que oferecemos na barra lateral:
    - **Extração de Conteúdo (D&T)**: Carregue um PDF de dissertação ou tese e obtenha uma extração detalhada do conteúdo.
    - **Visualização do Database**: Veja todos os dados armazenados no nosso banco de dados vetorial.
    - **Sumarização de Textos**: Receba resumos concisos e informativos de documentos extensos.
    - **Recuperação Semântica**: Faça buscas semânticas avançadas e obtenha resultados relevantes.
    - **Geração de Grafos**: Visualize relações e conexões entre diferentes tópicos e documentos.

    ### Vantagens do Sistema
    - **Precisão e Relevância**: Utilizamos o Gemini da Google para fornecer resultados precisos e relevantes.
    - **Eficiência**: Nossa ferramenta foi desenvolvida para maximizar a eficiência na busca por informações acadêmicas.
    - **Inovação**: Aplicamos técnicas de vanguarda em PLN para superar as limitações dos sistemas de busca tradicionais.

    ### Objetivos do Projeto
    O objetivo central do D&T Retrieval System é simplificar o acesso e a gestão de informações acadêmicas, promovendo a disseminação do conhecimento e a eficiência das pesquisas dentro do SNPG. Este projeto não só facilita a localização de informações específicas como também oferece respostas detalhadas e contextualmente relevantes, melhorando significativamente a experiência do usuário.

    Explore nossas funcionalidades e descubra como o D&T Retrieval System pode transformar a maneira como você interage com teses e dissertações acadêmicas.
    """)

