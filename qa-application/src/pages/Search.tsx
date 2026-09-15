import { FormEvent, useEffect, useState } from 'react';
import { FaMagnifyingGlass } from 'react-icons/fa6';
import { Link } from 'react-router-dom';

import Footer from '../components/Footer';
import Navbar from '../components/Navbar';
import {
  DocumentRecord,
  SearchResponse,
  listDocuments,
  searchDocument,
} from '../lib/api';

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}

export default function Search() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [documentId, setDocumentId] = useState('');
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [loadingDocuments, setLoadingDocuments] = useState(true);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    listDocuments(controller.signal)
      .then((items) => {
        if (!active) {
          return;
        }
        setDocuments(items);
        setDocumentId((current) => current || items[0]?.id || '');
      })
      .catch((requestError: unknown) => {
        if (active && !isAbortError(requestError)) {
          setError('Não foi possível carregar os documentos persistidos.');
        }
      })
      .finally(() => {
        if (active) {
          setLoadingDocuments(false);
        }
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const normalizedQuery = query.trim();
    if (!documentId || !normalizedQuery) {
      setError('Selecione um documento e informe o que deseja encontrar.');
      return;
    }

    setSearching(true);
    setError(null);
    setResult(null);
    try {
      setResult(await searchDocument(documentId, normalizedQuery));
    } catch (requestError: unknown) {
      setError(requestError instanceof Error ? requestError.message : 'Falha desconhecida.');
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-stone-50 text-stone-950">
      <Navbar />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10 sm:px-6">
        <header className="max-w-3xl">
          <p className="text-sm font-semibold uppercase tracking-widest text-red-800">
            Busca verificável
          </p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
            Encontre evidências no documento
          </h1>
          <p className="mt-4 leading-relaxed text-stone-600">
            A busca lexical consulta somente o documento escolhido. Ela não usa LLM, embedding ou
            geração de resposta; cada resultado aponta para uma página extraída.
          </p>
        </header>

        <section aria-labelledby="search-form-title" className="mt-8 rounded-2xl border border-stone-200 bg-white p-5 shadow-sm sm:p-7">
          <h2 className="text-xl font-bold" id="search-form-title">
            Consultar documento
          </h2>

          {loadingDocuments ? (
            <p aria-live="polite" className="mt-4 text-stone-600">
              Carregando documentos…
            </p>
          ) : documents.length === 0 ? (
            <div className="mt-4 rounded-xl bg-stone-100 p-5">
              <p className="font-medium">Nenhum documento disponível.</p>
              <p className="mt-1 text-sm text-stone-600">
                Faça primeiro uma avaliação para admitir um PDF no laboratório.
              </p>
              <Link className="mt-4 inline-flex font-semibold text-red-800 underline" to="/evaluation">
                Ir para avaliação
              </Link>
            </div>
          ) : (
            <form className="mt-5 space-y-5" onSubmit={handleSubmit}>
              <div>
                <label className="block text-sm font-semibold" htmlFor="search-document">
                  Documento
                </label>
                <select
                  className="mt-2 w-full rounded-lg border border-stone-300 bg-white px-3 py-2 focus:border-red-700 focus:outline-none focus:ring-2 focus:ring-red-200"
                  id="search-document"
                  onChange={(event) => {
                    setDocumentId(event.target.value);
                    setResult(null);
                    setError(null);
                  }}
                  value={documentId}
                >
                  {documents.map((document) => (
                    <option key={document.id} value={document.id}>
                      {document.file_name} · {document.page_count} página(s)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-semibold" htmlFor="search-query">
                  O que deseja encontrar?
                </label>
                <input
                  className="mt-2 w-full rounded-lg border border-stone-300 px-3 py-2 focus:border-red-700 focus:outline-none focus:ring-2 focus:ring-red-200"
                  id="search-query"
                  maxLength={200}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Ex.: metodologia utilizada"
                  type="search"
                  value={query}
                />
              </div>

              <button
                className="inline-flex items-center gap-2 rounded-lg bg-red-800 px-5 py-2.5 font-semibold text-white transition hover:bg-red-900 focus:outline-none focus:ring-2 focus:ring-red-700 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-stone-400"
                disabled={searching}
                type="submit"
              >
                <FaMagnifyingGlass aria-hidden="true" />
                {searching ? 'Buscando…' : 'Buscar evidências'}
              </button>
            </form>
          )}
        </section>

        <div aria-live="polite" className="mt-6">
          {error ? (
            <p className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-900" role="alert">
              {error}
            </p>
          ) : null}

          {result ? (
            <section aria-labelledby="search-results-title">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-wide text-stone-500">
                    Modo lexical · sem geração
                  </p>
                  <h2 className="mt-1 text-2xl font-bold" id="search-results-title">
                    Evidências para “{result.query}”
                  </h2>
                </div>
                <p className="text-sm text-stone-600">
                  {result.hits.length} resultado(s)
                </p>
              </div>

              {result.hits.length === 0 ? (
                <p className="mt-5 rounded-xl border border-stone-200 bg-white p-5 text-stone-600">
                  Nenhuma unidade deste documento corresponde à consulta.
                </p>
              ) : (
                <ol className="mt-5 space-y-4">
                  {result.hits.map((hit) => (
                    <li key={hit.unit_id}>
                      <article className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <h3 className="font-bold">Página {hit.page}</h3>
                          <span className="text-xs text-stone-500">
                            Ordenação lexical: {hit.score.toFixed(3)}
                          </span>
                        </div>
                        <p className="mt-3 whitespace-pre-wrap leading-relaxed text-stone-700">
                          {hit.snippet}
                        </p>
                        <p className="mt-3 break-all text-xs text-stone-500">
                          Evidência: {hit.unit_id}
                        </p>
                      </article>
                    </li>
                  ))}
                </ol>
              )}
            </section>
          ) : null}
        </div>
      </main>
      <Footer />
    </div>
  );
}
