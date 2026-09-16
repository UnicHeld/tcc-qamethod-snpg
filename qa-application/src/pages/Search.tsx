import { FormEvent, useEffect, useState } from 'react';
import { FaMagnifyingGlass } from 'react-icons/fa6';
import { Link } from 'react-router-dom';

import Footer from '../components/Footer';
import Navbar from '../components/Navbar';
import {
  DocumentRecord,
  RetrievalCapability,
  RetrievalMode,
  SearchResponse,
  getCapabilities,
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
  const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>('lexical');
  const [vectorCapability, setVectorCapability] = useState<RetrievalCapability | null>(null);
  const [results, setResults] = useState<Partial<Record<RetrievalMode, SearchResponse>>>({});
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

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    getCapabilities(controller.signal)
      .then((capabilities) => {
        if (!active) {
          return;
        }
        const vector = capabilities.retrieval_capabilities.find(
          (capability) => capability.mode === 'vector',
        );
        setVectorCapability(
          vector ?? {
            mode: 'vector',
            label: 'Vetorial — embedding local',
            available: false,
            reason: 'A API não informou a capacidade de busca vetorial.',
            model: null,
            dimension: null,
          },
        );
      })
      .catch((requestError: unknown) => {
        if (active && !isAbortError(requestError)) {
          setVectorCapability({
            mode: 'vector',
            label: 'Vetorial — embedding local',
            available: false,
            reason: 'Não foi possível verificar a disponibilidade da busca vetorial.',
            model: null,
            dimension: null,
          });
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
    try {
      const response = await searchDocument(documentId, normalizedQuery, retrievalMode);
      setResults((current) => ({ ...current, [retrievalMode]: response }));
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
            Compare correspondência lexical e semântica no documento escolhido. Nenhum modo gera
            resposta: cada resultado continua apontando para uma página e unidade extraídas.
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
                    setResults({});
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
                  onChange={(event) => {
                    setQuery(event.target.value);
                    setResults({});
                  }}
                  placeholder="Ex.: metodologia utilizada"
                  type="search"
                  value={query}
                />
              </div>

              <fieldset>
                <legend className="text-sm font-semibold">Modo de recuperação</legend>
                <div className="mt-2 grid gap-3 sm:grid-cols-2">
                  <label className="flex cursor-pointer gap-3 rounded-xl border border-stone-300 p-4 has-[:checked]:border-red-700 has-[:checked]:bg-red-50">
                    <input
                      checked={retrievalMode === 'lexical'}
                      className="mt-1"
                      name="retrieval-mode"
                      onChange={() => setRetrievalMode('lexical')}
                      type="radio"
                    />
                    <span>
                      <span className="block font-semibold">Lexical</span>
                      <span className="text-sm text-stone-600">Termos do texto, sem embedding.</span>
                    </span>
                  </label>
                  <label className="flex gap-3 rounded-xl border border-stone-300 p-4 has-[:checked]:border-red-700 has-[:checked]:bg-red-50 has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-60">
                    <input
                      checked={retrievalMode === 'vector'}
                      className="mt-1"
                      disabled={!vectorCapability?.available}
                      name="retrieval-mode"
                      onChange={() => {
                        setRetrievalMode('vector');
                        setError(null);
                      }}
                      type="radio"
                    />
                    <span>
                      <span className="block font-semibold">Vetorial local</span>
                      <span className="text-sm text-stone-600">
                        {vectorCapability?.available
                          ? `${vectorCapability.model} · ${vectorCapability.dimension} dimensões.`
                          : vectorCapability?.reason ?? 'Verificando disponibilidade…'}
                      </span>
                    </span>
                  </label>
                </div>
              </fieldset>

              <button
                className="inline-flex items-center gap-2 rounded-lg bg-red-800 px-5 py-2.5 font-semibold text-white transition hover:bg-red-900 focus:outline-none focus:ring-2 focus:ring-red-700 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-stone-400"
                disabled={searching}
                type="submit"
              >
                <FaMagnifyingGlass aria-hidden="true" />
                {searching
                  ? 'Buscando…'
                  : `Buscar no modo ${retrievalMode === 'lexical' ? 'lexical' : 'vetorial'}`}
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

          {(['lexical', 'vector'] as const).map((mode) => {
            const result = results[mode];
            if (!result) {
              return null;
            }
            return (
              <section
                aria-labelledby={`search-results-title-${mode}`}
                className="mt-6"
                key={mode}
              >
                <div className="flex flex-wrap items-end justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-wide text-stone-500">
                      Modo {mode === 'lexical' ? 'lexical' : 'vetorial local'} · sem geração
                    </p>
                    <h2 className="mt-1 text-2xl font-bold" id={`search-results-title-${mode}`}>
                      Evidências para “{result.query}”
                    </h2>
                    {mode === 'vector' ? (
                      <p className="mt-2 text-sm text-stone-600">
                        {result.embedding_model} · {result.embedding_dimension} dimensões ·{' '}
                        {result.chunk_version}
                      </p>
                    ) : null}
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
                      <li key={`${hit.unit_id}-${hit.snippet}`}>
                        <article className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <h3 className="font-bold">Página {hit.page}</h3>
                            <span className="text-xs text-stone-500">
                              Relevância {mode === 'lexical' ? 'lexical' : 'vetorial'}:{' '}
                              {hit.score.toFixed(3)}
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
            );
          })}
        </div>
      </main>
      <Footer />
    </div>
  );
}
