import google.generativeai as genai
import os

class EvalationService:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name='gemini-1.5-flash',
                                        generation_config={"temperature": 0.1})
        
    
    def evaluation_generate(self, content: str):
        template = f"""
        Você foi convidado(a) a avaliar um documento acadêmico.
        
        Considerando o documento de dissertação de mestrado ou tese de doutorado que será mostrado a seguir, elabore um resumo considerando as seguintes dimensões de análise:
        a) Originalidade do trabalho;
        b) Relevância para o desenvolvimento científico, tecnológico, cultural e social;
        c) Metodologia utilizada;
        d) Qualidade da redação;
        e) Estrutura/organização do texto;
        f) Interdisciplinaridade.
        
        Ainda, ao final de cada dimensão analisada, atribua uma nota entre 0 (zero) e 10 (dez).
        
        {{REGRAS}}
        > Apresente primeiro o título do documento. Exemplo: "Título: Análise de Sentimentos em Redes Sociais".
        > Em seguida, apresente o resumo do documento. Exemplo: "Resumo: Este trabalho apresenta uma análise de sentimentos em redes sociais, com foco em..."
        > Após cada dimensão analisada, pule uma linha e atribua a nota em negrito. Exemplo: **Nota: X.X**
        > Omita informações pessoais do autor e do orientador.
        > Seja o mais objetivo e imparcial possível.
        > Não use adjetivos ou advérbios que possam indicar a sua opinião pessoal.
        """
        
        try:
            response = self.model.generate_content(contents=template + '\n\nDocumento: ' + content, stream=True)
            for chunk in response:
                yield chunk.text
        except Exception as e:
            print(f"Erro ao gerar a análise: {e}")

