// src/pages/Home.tsx
import React from 'react';
import ServiceCard from '../components/ServiceCard';
import Footer from '../components/Footer';
import Navbar from '../components/Navbar';

const Home: React.FC = () => {
    return (
        <div className="flex flex-col min-h-screen bg-white text-black">
            {/* Navbar */}
            <Navbar />

            {/* Main Content */}
            <main className="flex flex-grow items-center justify-center">
                <div className="container mx-auto py-10">
                    <h2 className="text-2xl font-bold text-center text-red-600 mb-8">Serviços Oferecidos</h2>

                    {/* Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <ServiceCard
                            title="Extração de Conteúdo"
                            description="Extraia informações detalhadas de teses e dissertações com facilidade."
                            icon="📄"
                        />
                        <ServiceCard
                            title="Criação de Grafos"
                            description="Gere grafos de relações entre documentos acadêmicos."
                            icon="📊"
                        />
                        <ServiceCard
                            title="Avaliação de Dissertações e Teses"
                            description="Obtenha uma avaliação automatizada de trabalhos acadêmicos."
                            icon="📝"
                            link="/evaluation"
                        />
                        <ServiceCard
                            title="Converse com Nossa IA Especializada"
                            description="Fale diretamente com nossa IA para obter respostas e insights sobre pesquisas acadêmicas."
                            icon="🤖"
                        />
                    </div>
                </div>
            </main>

            {/* Footer */}
            <Footer />
        </div>
    );
}

export default Home;
