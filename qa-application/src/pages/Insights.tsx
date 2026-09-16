import { FormEvent, useEffect, useRef, useState } from 'react';
import { FaCheck, FaCopy, FaDownload, FaLightbulb } from 'react-icons/fa6';
import { Link, useSearchParams } from 'react-router-dom';

import Footer from '../components/Footer';
import Navbar from '../components/Navbar';
import {
  Capability,
  DocumentRecord,
  InsightResult,
  InsightRunRecord,
  RetrievalCapability,
  RetrievalMode,
  createInsight,
  getCapabilities,
  getInsight,
  getInsightResult,
  listDocuments,
  listInsights,
} from '../lib/api';

const STATUS_LABELS: Record<InsightRunRecord['status'], string> = {
  queued: 'Na fila',
  running: 'Em execução',
  succeeded: 'Concluído',
  failed: 'Falhou',
  interrupted: 'Interrompido',
};

interface CopyFeedback {
  evidenceId: string;
  evidenceKey: string;
  kind: 'success' | 'error';
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}

function newIdempotencyKey(): string {
  return globalThis.crypto?.randomUUID?.() ?? `insight-${Date.now()}-${Math.random()}`;
}

function download(name: string, content: string, type: string): void {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function Insights() {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedInsightId = searchParams.get('insight');
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [recentInsights, setRecentInsights] = useState<InsightRunRecord[]>([]);
  const [capabilities, setCapabilities] = useState<Capability[]>([]);
  const [vectorCapability, setVectorCapability] = useState<RetrievalCapability | null>(null);
  const [documentId, setDocumentId] = useState('');
  const [question, setQuestion] = useState('');
  const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>('lexical');
  const [generationMode, setGenerationMode] = useState<'demo' | 'real'>('demo');
  const [confirmExternal, setConfirmExternal] = useState(false);
  const [insight, setInsight] = useState<InsightRunRecord | null>(null);
  const [result, setResult] = useState<InsightResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copyFeedback, setCopyFeedback] = useState<CopyFeedback | null>(null);
  const submissionKey = useRef(newIdempotencyKey());

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    Promise.all([
      listDocuments(controller.signal),
      getCapabilities(controller.signal),
      listInsights(controller.signal),
    ])
      .then(([documentItems, configuration, insightItems]) => {
        if (!active) {
          return;
        }
        setDocuments(documentItems);
        setDocumentId((current) => current || documentItems[0]?.id || '');
        setCapabilities(configuration.capabilities);
        setVectorCapability(
          configuration.retrieval_capabilities.find((item) => item.mode === 'vector') ?? null,
        );
        setRecentInsights(insightItems.slice(0, 10));
      })
      .catch((requestError: unknown) => {
        if (active && !isAbortError(requestError)) {
          setError('Não foi possível carregar o laboratório de insights.');
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, []);

  useEffect(() => {
    if (!selectedInsightId) {
      return;
    }
    const insightId = selectedInsightId;

    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function poll(): Promise<void> {
      try {
        const current = await getInsight(insightId, controller.signal);
        setInsight(current);
        setRecentInsights((items) => {
          const remaining = items.filter((item) => item.id !== current.id);
          return [current, ...remaining].slice(0, 10);
        });
        if (current.status === 'succeeded') {
          setResult(await getInsightResult(current.id, controller.signal));
          return;
        }
        if (current.status === 'failed' || current.status === 'interrupted') {
          setResult(null);
          setError(current.error_message ?? 'O insight não foi concluído.');
          return;
        }
        timer = setTimeout(() => void poll(), 750);
      } catch (requestError: unknown) {
        if (!isAbortError(requestError)) {
          setError(
            requestError instanceof Error ? requestError.message : 'Falha ao consultar o insight.',
          );
        }
      }
    }

    void poll();
    return () => {
      controller.abort();
      if (timer) {
        clearTimeout(timer);
      }
    };
  }, [selectedInsightId]);

  const selectedCapability = capabilities.find((item) => item.mode === generationMode);
  const canSubmit = Boolean(
    documentId &&
      question.trim() &&
      selectedCapability?.available &&
      (retrievalMode === 'lexical' || vectorCapability?.available) &&
      (generationMode === 'demo' || confirmExternal) &&
      !submitting,
  );

  function resetSubmission(): void {
    submissionKey.current = newIdempotencyKey();
    setError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!canSubmit) {
      return;
    }
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const created = await createInsight(
        documentId,
        question.trim(),
        retrievalMode,
        5,
        generationMode,
        confirmExternal,
        submissionKey.current,
      );
      setInsight(created);
      setSearchParams({ insight: created.id });
      submissionKey.current = newIdempotencyKey();
    } catch (requestError: unknown) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao criar o insight.');
    } finally {
      setSubmitting(false);
    }
  }

  async function copyEvidenceOrigin(
    evidenceId: string,
    evidenceKey: string,
    unitId: string,
  ): Promise<void> {
    try {
      if (!navigator.clipboard?.writeText) {
        throw new Error('Clipboard API indisponível.');
      }
      await navigator.clipboard.writeText(unitId);
      setCopyFeedback({ evidenceId, evidenceKey, kind: 'success' });
    } catch {
      setCopyFeedback({ evidenceId, evidenceKey, kind: 'error' });
    }
  }

  const citedEvidence = result
    ? result.report.citation_ids.flatMap((citationId) => {
        const item = result.evidence_package.items.find((evidence) => evidence.id === citationId);
        return item ? [item] : [];
      })
    : [];

  return (
    <div className="flex min-h-screen flex-col bg-stone-50 text-stone-950">
      <Navbar />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6">
        <header className="max-w-3xl">
          <p className="text-sm font-semibold uppercase tracking-widest text-red-800">
            EV-03 · RAG rastreável
          </p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
            Gere um insight com fontes congeladas
          </h1>
          <p className="mt-4 leading-relaxed text-stone-600">
            Faça uma pergunta única. A resposta usa somente os trechos recuperados e cada citação
            continua ligada à página e à unidade de origem.
          </p>
        </header>

        {loading ? <p className="mt-8 text-stone-600">Carregando laboratório…</p> : null}

        {!loading && documents.length === 0 ? (
          <section className="mt-8 rounded-2xl border border-stone-200 bg-white p-6">
            <h2 className="text-xl font-bold">Nenhum documento disponível</h2>
            <p className="mt-2 text-stone-600">Admita primeiro um PDF digital no laboratório.</p>
            <Link className="mt-4 inline-flex font-semibold text-red-800 underline" to="/evaluation">
              Ir para avaliação
            </Link>
          </section>
        ) : null}

        {!loading && documents.length > 0 ? (
          <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(16rem,1fr)]">
            <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm sm:p-7">
              <h2 className="text-xl font-bold">Nova pergunta</h2>
              <form className="mt-5 space-y-5" onSubmit={handleSubmit}>
                <div>
                  <label className="block text-sm font-semibold" htmlFor="insight-document">
                    Documento
                  </label>
                  <select
                    className="mt-2 w-full rounded-lg border border-stone-300 bg-white px-3 py-2"
                    id="insight-document"
                    onChange={(event) => {
                      setDocumentId(event.target.value);
                      resetSubmission();
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
                  <label className="block text-sm font-semibold" htmlFor="insight-question">
                    Pergunta
                  </label>
                  <textarea
                    className="mt-2 min-h-28 w-full rounded-lg border border-stone-300 px-3 py-2"
                    id="insight-question"
                    maxLength={200}
                    onChange={(event) => {
                      setQuestion(event.target.value);
                      resetSubmission();
                    }}
                    placeholder="Ex.: Qual metodologia foi utilizada?"
                    value={question}
                  />
                  <p className="mt-1 text-xs text-stone-500">{question.length}/200 caracteres</p>
                </div>

                <fieldset>
                  <legend className="text-sm font-semibold">Recuperação</legend>
                  <div className="mt-2 grid gap-3 sm:grid-cols-2">
                    <label className="flex gap-3 rounded-xl border border-stone-300 p-4 has-[:checked]:border-red-700 has-[:checked]:bg-red-50">
                      <input
                        checked={retrievalMode === 'lexical'}
                        name="insight-retrieval"
                        onChange={() => {
                          setRetrievalMode('lexical');
                          resetSubmission();
                        }}
                        type="radio"
                      />
                      <span><strong className="block">Lexical</strong>Termos do texto.</span>
                    </label>
                    <label className="flex gap-3 rounded-xl border border-stone-300 p-4 has-[:checked]:border-red-700 has-[:checked]:bg-red-50 has-[:disabled]:opacity-60">
                      <input
                        checked={retrievalMode === 'vector'}
                        disabled={!vectorCapability?.available}
                        name="insight-retrieval"
                        onChange={() => {
                          setRetrievalMode('vector');
                          resetSubmission();
                        }}
                        type="radio"
                      />
                      <span>
                        <strong className="block">Vetorial local</strong>
                        {vectorCapability?.available
                          ? vectorCapability.model
                          : vectorCapability?.reason ?? 'Indisponível.'}
                      </span>
                    </label>
                  </div>
                </fieldset>

                <fieldset>
                  <legend className="text-sm font-semibold">Geração</legend>
                  <div className="mt-2 grid gap-3 sm:grid-cols-2">
                    {capabilities.map((capability) => (
                      <label
                        className="flex gap-3 rounded-xl border border-stone-300 p-4 has-[:checked]:border-red-700 has-[:checked]:bg-red-50 has-[:disabled]:opacity-60"
                        key={capability.mode}
                      >
                        <input
                          checked={generationMode === capability.mode}
                          disabled={!capability.available}
                          name="insight-generation"
                          onChange={() => {
                            setGenerationMode(capability.mode);
                            setConfirmExternal(false);
                            resetSubmission();
                          }}
                          type="radio"
                        />
                        <span>
                          <strong className="block">{capability.label}</strong>
                          {capability.available ? capability.model : capability.reason}
                        </span>
                      </label>
                    ))}
                  </div>
                </fieldset>

                {generationMode === 'real' ? (
                  <label className="flex gap-3 rounded-xl border border-amber-300 bg-amber-50 p-4">
                    <input
                      checked={confirmExternal}
                      onChange={(event) => setConfirmExternal(event.target.checked)}
                      type="checkbox"
                    />
                    <span>
                      Confirmo o envio da pergunta e dos trechos recuperados ao provedor externo.
                      O PDF completo não é enviado por este fluxo.
                    </span>
                  </label>
                ) : null}

                <button
                  className="inline-flex items-center gap-2 rounded-lg bg-red-800 px-5 py-2.5 font-semibold text-white disabled:bg-stone-400"
                  disabled={!canSubmit}
                  type="submit"
                >
                  <FaLightbulb aria-hidden="true" />
                  {submitting ? 'Criando…' : 'Gerar insight'}
                </button>
              </form>
            </section>

            <aside className="rounded-2xl border border-stone-200 bg-white p-5">
              <h2 className="font-bold">Insights recentes</h2>
              {recentInsights.length === 0 ? (
                <p className="mt-3 text-sm text-stone-600">Nenhum insight executado.</p>
              ) : (
                <ol className="mt-3 space-y-2">
                  {recentInsights.map((item) => (
                    <li key={item.id}>
                      <button
                        className="w-full rounded-lg border border-stone-200 p-3 text-left hover:bg-stone-50"
                        onClick={() => {
                          setError(null);
                          setSearchParams({ insight: item.id });
                        }}
                        type="button"
                      >
                        <span className="block line-clamp-2 text-sm font-medium">{item.question}</span>
                        <span className="mt-1 block text-xs text-stone-500">
                          {STATUS_LABELS[item.status]} · {item.retrieval_mode}
                        </span>
                      </button>
                    </li>
                  ))}
                </ol>
              )}
            </aside>
          </div>
        ) : null}

        <div aria-live="polite" className="mt-6">
          {error ? <p className="rounded-xl bg-red-50 p-4 text-red-900" role="alert">{error}</p> : null}
          {insight && !result && !error ? (
            <p className="rounded-xl border border-stone-200 bg-white p-4">
              {STATUS_LABELS[insight.status]}: preparando recuperação e resposta…
            </p>
          ) : null}
        </div>

        {result ? (
          <section className="mt-8 rounded-2xl border border-stone-200 bg-white p-5 shadow-sm sm:p-7">
            <p aria-live="polite" className="sr-only">
              {copyFeedback?.kind === 'success'
                ? `Origem ${copyFeedback.evidenceId} copiada.`
                : ''}
            </p>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-wide text-red-800">
                  {result.report.simulated ? 'Simulado — sem inferência LLM' : 'Insight RAG'}
                </p>
                <h2 className="mt-2 text-2xl font-bold">{result.report.question}</h2>
              </div>
              <div className="flex gap-2">
                <button
                  className="inline-flex items-center gap-2 rounded-lg border border-stone-300 px-3 py-2 text-sm font-semibold"
                  onClick={() => download(`insight-${result.insight_id}.md`, result.result_markdown, 'text/markdown')}
                  type="button"
                >
                  <FaDownload aria-hidden="true" /> Markdown
                </button>
                <button
                  className="inline-flex items-center gap-2 rounded-lg border border-stone-300 px-3 py-2 text-sm font-semibold"
                  onClick={() => download(`insight-${result.insight_id}.json`, JSON.stringify(result, null, 2), 'application/json')}
                  type="button"
                >
                  <FaDownload aria-hidden="true" /> JSON
                </button>
              </div>
            </div>
            <p className="mt-5 whitespace-pre-wrap leading-relaxed">{result.report.answer}</p>

            <h3 className="mt-8 text-xl font-bold">Evidências citadas</h3>
            <ol className="mt-4 space-y-4">
              {citedEvidence.map((item) => {
                const evidenceKey = `${result.insight_id}:${item.id}`;
                const feedback =
                  copyFeedback?.evidenceKey === evidenceKey ? copyFeedback : null;
                return (
                  <li
                    className="rounded-xl border border-stone-200 bg-stone-50 p-4"
                    key={item.id}
                  >
                    <p className="font-semibold">{item.id} · página {item.page}</p>
                    <p className="mt-2 whitespace-pre-wrap text-stone-700">{item.text}</p>
                    <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                      <p className="break-all text-xs text-stone-500">Origem: {item.unit_id}</p>
                      <button
                        className="inline-flex items-center gap-2 rounded-lg border border-stone-300 bg-white px-3 py-2 text-xs font-semibold hover:bg-stone-100"
                        onClick={() =>
                          void copyEvidenceOrigin(item.id, evidenceKey, item.unit_id)
                        }
                        type="button"
                      >
                        {feedback?.kind === 'success' ? (
                          <FaCheck aria-hidden="true" />
                        ) : (
                          <FaCopy aria-hidden="true" />
                        )}
                        {feedback?.kind === 'success' ? 'Origem copiada' : 'Copiar origem'}
                      </button>
                    </div>
                    {feedback?.kind === 'error' ? (
                      <p className="mt-2 text-sm text-red-800" role="alert">
                        Não foi possível copiar a origem. Selecione o identificador manualmente.
                      </p>
                    ) : null}
                  </li>
                );
              })}
            </ol>
            <p className="mt-5 text-sm text-stone-500">
              Recuperação {result.evidence_package.retrieval_mode}
              {result.evidence_package.embedding_model
                ? ` · ${result.evidence_package.embedding_model}`
                : ''}
              . A presença de uma citação não comprova por si só a correção da resposta.
            </p>
          </section>
        ) : null}
      </main>
      <Footer />
    </div>
  );
}
