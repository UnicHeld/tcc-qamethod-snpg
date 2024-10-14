import React, { useState } from 'react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { FaPaperclip } from 'react-icons/fa';  // Importar o ícone de anexo
import ReactMarkdown from 'react-markdown';  // Importar o react-markdown

const Evaluation: React.FC = () => {
    const [fileName, setFileName] = useState<string | null>(null);
    const [analysisResult, setAnalysisResult] = useState<string>("");  // Inicializa com uma string vazia
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    // Função para lidar com o upload de arquivos
    const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (file) {
            setFileName(file.name);
            setAnalysisResult("");  // Limpar o resultado da análise anterior
            setIsLoading(true);
            setError(null);  // Resetar erro antes do upload
            const formData = new FormData();
            formData.append("file", file);

            try {
                // Enviar o arquivo para o backend
                const response = await fetch("http://localhost:8000/evaluation/upload", {
                    method: "POST",
                    body: formData,
                });

                if (!response.ok) {
                    // Exibir o código de status HTTP e a mensagem
                    const errorMessage = await response.text();
                    throw new Error(`Erro no upload: ${response.status} - ${errorMessage}`);
                }

                const reader = response.body?.getReader();
                const decoder = new TextDecoder();
                // Ler a resposta em streaming e atualizar o estado conforme os dados são recebidos
                while (reader) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    setAnalysisResult((prevResult) => prevResult + decoder.decode(value));  // Atualiza em tempo real
                }

            } catch (error: any) {
                console.error("Erro ao fazer upload:", error.message);
                setError(error.message);  // Armazenar e exibir o erro no frontend
            } finally {
                setIsLoading(false);
            }
        }
    };

    return (
        <div className="flex flex-col min-h-screen">
            {/* Navbar */}
            <Navbar />

            {/* Chatbox */}
            <main className="flex-grow flex flex-col px-4 py-10">
                <div className="flex-grow h-96 bg-gray-100 rounded-lg shadow-lg overflow-y-auto p-6">
                    <div className="text-justify">
                        {/* Introdução sobre a avaliação */}
                        <p>
                            Bem-vindo ao serviço de Avaliação de Dissertações e Teses! Aqui você pode subir sua dissertação ou tese e o sistema fará uma avaliação considerando as seguintes dimensões de análise.
                        </p>
                            
                            {/* Lista de dimensões de análise */}
                            <ul className="list-disc list-inside mt-4">
                                <li>Originalidade do trabalho;</li>
                                <li>Relevância para o desenvolvimento científico, tecnológico, cultural e social;</li>
                                <li>Metodologia utilizada;</li>
                                <li>Qualidade da redação;</li>
                                <li>Estrutura/organização do texto;</li>
                                <li>Interdisciplinaridade.</li>
                            </ul>


                        <p className="mt-4">
                            Para iniciar, faça o upload do seu arquivo no botão abaixo.
                        </p>

                        {/* Botão de Upload */}
                        <div className="mt-6 flex items-center space-x-2">
                            <label className="flex items-center cursor-pointer bg-red-500 text-white px-4 py-2 rounded-lg shadow-md hover:bg-red-600 transition duration-300">
                                <FaPaperclip className="mr-2" /> {/* Ícone de Anexo */}
                                <span>Upload</span>
                                <input
                                    type="file"
                                    className="hidden"
                                    onChange={handleFileUpload}
                                    accept=".pdf"
                                />
                            </label>
                        </div>

                        {/* Exibir o nome do arquivo selecionado */}
                        {fileName && (
                            <p className="mt-4 text-sm text-gray-600">
                                Arquivo selecionado: {fileName}
                            </p>
                        )}

                        {/* Exibir o status do upload */}
                        {isLoading && <p className="mt-4 text-sm text-gray-600">Avaliando o arquivo...</p>}
                        {error && <p className="mt-4 text-sm text-red-600">Erro: {error}</p>}
                        
                        {/* Exibir o resultado da análise como Markdown */}
                        {analysisResult && (
                            <div className="mt-4 bg-white p-4 rounded-lg shadow">
                                <ReactMarkdown className="text-sm whitespace-pre-wrap">
                                    {analysisResult}
                                </ReactMarkdown>
                            </div>
                        )}
                    </div>
                </div>
            </main>

            {/* Footer */}
            <Footer />
        </div>
    );
};

export default Evaluation;
