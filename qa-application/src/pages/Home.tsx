import Footer from '../components/Footer';
import Navbar from '../components/Navbar';
import ServiceCard from '../components/ServiceCard';

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-stone-50 text-stone-950">
      <Navbar />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-12 sm:px-6 lg:py-20">
        <header className="max-w-3xl">
          <p className="text-sm font-semibold uppercase tracking-widest text-red-800">
            Laboratório local
          </p>
          <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">
            Avalie documentos com limites e evidências explícitos
          </h1>
          <p className="mt-5 text-lg leading-relaxed text-stone-600">
            A retomada começa por PDF digital e um modo de demonstração sem credenciais. Recursos
            futuros permanecem identificados como planejados até terem implementação verificável.
          </p>
        </header>

        <section aria-labelledby="capabilities-title" className="mt-12">
          <h2 className="text-2xl font-bold" id="capabilities-title">
            Capacidades
          </h2>
          <div className="mt-6 grid grid-cols-1 gap-5 md:grid-cols-2">
            <ServiceCard
              description="Envie um PDF digital, escolha entre simulação e inferência autorizada e exporte o resultado."
              icon="📝"
              link="/evaluation"
              status="available"
              title="Avaliação de dissertações e teses"
            />
            <ServiceCard
              description="Inspeção de texto, tabelas, páginas e qualidade de extração será liberada em uma fase posterior."
              icon="📄"
              title="Documentos e extração"
            />
            <ServiceCard
              description="Busca lexical e recuperação vetorial local ainda não participam da avaliação atual."
              icon="🔎"
              title="Busca e RAG"
            />
            <ServiceCard
              description="Comparação de execuções e judge separado do parecer estão no roteiro experimental."
              icon="🧪"
              title="Experimentos"
            />
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
