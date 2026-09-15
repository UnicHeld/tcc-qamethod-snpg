import { ChangeEvent, FormEvent, useEffect, useRef, useState } from 'react';
import { FaArrowRotateRight, FaFileArrowDown, FaPaperclip } from 'react-icons/fa6';
import ReactMarkdown from 'react-markdown';
import { useSearchParams } from 'react-router-dom';

import Footer from '../components/Footer';
import Navbar from '../components/Navbar';
import {
  Capability,
  CapabilitiesResponse,
  DocumentRecord,
  DocumentPageRecord,
  EvaluationMode,
  RunRecord,
  RunResult,
  createDocument,
  createRun,
  getCapabilities,
  getDocument,
  getDocumentPages,
  getRun,
  getRunResult,
  listDocuments,
  listRuns,
} from '../lib/api';
import { downloadRunJson, downloadRunMarkdown } from '../lib/runExport';

type Activity = 'idle' | 'uploading' | 'waiting';
type ComparisonData = {
  leftRun: RunRecord;
  leftResult: RunResult;
  rightRun: RunRecord;
  rightResult: RunResult;
};

const statusLabels: Record<RunRecord['status'], string> = {
  queued: 'Na fila',
  running: 'Em execução',
  succeeded: 'Concluída',
  failed: 'Falhou',
  interrupted: 'Interrompida',
};

const dimensionLabels: Record<
  RunResult['report']['dimensions'][number]['dimension'],
  string
> = {
  originality: 'Originalidade',
  relevance: 'Relevância',
  methodology: 'Metodologia',
  writing: 'Escrita',
  structure: 'Estrutura',
  interdisciplinarity: 'Interdisciplinaridade',
};

function formatBytes(bytes: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'unit',
    unit: 'megabyte',
    maximumFractionDigits: 0,
  }).format(bytes / (1024 * 1024));
}

function formatDate(value: string | null): string {
  if (!value) {
    return '—';
  }
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'medium',
  }).format(new Date(value));
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}

function newIdempotencyKey(): string {
  return globalThis.crypto.randomUUID();
}

function formatDuration(run: RunRecord): string {
  if (!run.started_at || !run.finished_at) {
    return '—';
  }
  const durationSeconds = Math.max(
    0,
    (new Date(run.finished_at).getTime() - new Date(run.started_at).getTime()) / 1000,
  );
  return `${durationSeconds.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} s`;
}

export default function Evaluation() {
  const [searchParams, setSearchParams] = useSearchParams();
  const runId = searchParams.get('run');
  const [configuration, setConfiguration] = useState<CapabilitiesResponse | null>(null);
  const [mode, setMode] = useState<EvaluationMode>('demo');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [confirmExternal, setConfirmExternal] = useState(false);
  const [documentRecord, setDocumentRecord] = useState<DocumentRecord | null>(null);
  const [documentPages, setDocumentPages] = useState<DocumentPageRecord[]>([]);
  const [run, setRun] = useState<RunRecord | null>(null);
  const [result, setResult] = useState<RunResult | null>(null);
  const [recentRuns, setRecentRuns] = useState<RunRecord[]>([]);
  const [recentDocuments, setRecentDocuments] = useState<DocumentRecord[]>([]);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyVersion, setHistoryVersion] = useState(0);
  const [leftRunId, setLeftRunId] = useState('');
  const [rightRunId, setRightRunId] = useState('');
  const [comparison, setComparison] = useState<ComparisonData | null>(null);
  const [comparisonError, setComparisonError] = useState<string | null>(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [activity, setActivity] = useState<Activity>('idle');
  const [error, setError] = useState<string | null>(null);
  const submissionKey = useRef(newIdempotencyKey());
  const retryIntent = useRef({ sourceRunId: '', key: '' });

  useEffect(() => {
    const controller = new AbortController();
    getCapabilities(controller.signal)
      .then((response) => {
        setConfiguration(response);
        if (!new URLSearchParams(window.location.search).has('run')) {
          setMode(response.default_mode);
        }
      })
      .catch((requestError: unknown) => {
        if (!isAbortError(requestError)) {
          setError('Não foi possível consultar as capacidades da API local.');
        }
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([listRuns(controller.signal), listDocuments(controller.signal)])
      .then(([runs, documents]) => {
        setRecentRuns(runs);
        setRecentDocuments(documents);
        setHistoryError(null);
      })
      .catch((requestError: unknown) => {
        if (!isAbortError(requestError)) {
          setHistoryError('Não foi possível carregar o histórico persistente.');
        }
      });
    return () => controller.abort();
  }, [historyVersion]);

  useEffect(() => {
    if (!runId) {
      return;
    }

    const requestedRunId = runId;
    const controller = new AbortController();
    let pollTimer: number | undefined;
    let documentLoaded = false;
    let initialized = false;

    async function loadPersistedRun(): Promise<void> {
      if (!initialized) {
        initialized = true;
        setActivity('waiting');
        setError(null);
        setRun(null);
        setDocumentRecord(null);
        setDocumentPages([]);
        setResult(null);
      }
      try {
        const persistedRun = await getRun(requestedRunId, controller.signal);
        setRun(persistedRun);
        setMode(persistedRun.mode);

        if (!documentLoaded) {
          const [persistedDocument, persistedPages] = await Promise.all([
            getDocument(persistedRun.document_id, controller.signal),
            getDocumentPages(persistedRun.document_id, controller.signal),
          ]);
          documentLoaded = true;
          setDocumentRecord(persistedDocument);
          setDocumentPages(persistedPages);
        }

        if (persistedRun.status === 'succeeded') {
          const persistedResult = await getRunResult(persistedRun.id, controller.signal);
          setResult(persistedResult);
          setActivity('idle');
          setHistoryVersion((version) => version + 1);
          return;
        }
        if (persistedRun.status === 'failed' || persistedRun.status === 'interrupted') {
          setActivity('idle');
          setHistoryVersion((version) => version + 1);
          return;
        }
        pollTimer = window.setTimeout(() => void loadPersistedRun(), 750);
      } catch (requestError: unknown) {
        if (!isAbortError(requestError)) {
          const message =
            requestError instanceof Error ? requestError.message : 'Falha desconhecida.';
          setError(message);
          setActivity('idle');
        }
      }
    }

    void loadPersistedRun();
    return () => {
      controller.abort();
      if (pollTimer !== undefined) {
        window.clearTimeout(pollTimer);
      }
    };
  }, [runId]);

  useEffect(() => {
    const controller = new AbortController();

    async function loadComparison(): Promise<void> {
      setComparison(null);
      setComparisonError(null);
      if (!leftRunId || !rightRunId) {
        return;
      }

      const leftRun = recentRuns.find((item) => item.id === leftRunId);
      const rightRun = recentRuns.find((item) => item.id === rightRunId);
      if (!leftRun || !rightRun) {
        setComparisonError('Selecione duas execuções disponíveis no histórico recente.');
        return;
      }
      if (leftRun.id === rightRun.id) {
        setComparisonError('Selecione dois runs diferentes.');
        return;
      }
      if (leftRun.document_id !== rightRun.document_id) {
        setComparisonError('A comparação exige dois runs do mesmo documento.');
        return;
      }
      if (leftRun.status !== 'succeeded' || rightRun.status !== 'succeeded') {
        setComparisonError('A comparação exige dois runs concluídos com sucesso.');
        return;
      }

      setComparisonLoading(true);
      try {
        const [leftResult, rightResult] = await Promise.all([
          getRunResult(leftRun.id, controller.signal),
          getRunResult(rightRun.id, controller.signal),
        ]);
        setComparison({ leftRun, leftResult, rightRun, rightResult });
      } catch (requestError: unknown) {
        if (!isAbortError(requestError)) {
          const message =
            requestError instanceof Error ? requestError.message : 'Falha desconhecida.';
          setComparisonError(message);
        }
      } finally {
        if (!controller.signal.aborted) {
          setComparisonLoading(false);
        }
      }
    }

    void loadComparison();
    return () => controller.abort();
  }, [leftRunId, recentRuns, rightRunId]);

  const selectedCapability = configuration?.capabilities.find(
    (capability) => capability.mode === mode,
  );
  const exceedsLimit = Boolean(
    selectedFile && configuration && selectedFile.size > configuration.max_upload_bytes,
  );
  const isBusy = activity !== 'idle';
  const canSubmit = Boolean(
    selectedFile &&
      selectedCapability?.available &&
      !exceedsLimit &&
      !isBusy &&
      (mode === 'demo' || confirmExternal),
  );
  const canRetry = Boolean(
    run &&
      documentRecord &&
      (run.status === 'failed' || run.status === 'interrupted') &&
      !isBusy &&
      (run.mode === 'demo' || (selectedCapability?.available && confirmExternal)),
  );
  const documentsById = new Map(
    recentDocuments.map((recentDocument) => [recentDocument.id, recentDocument]),
  );
  const ocrCandidatePages = documentPages
    .filter((page) => page.status === 'ocr_candidate')
    .map((page) => page.page);
  const noTextPages = documentPages
    .filter((page) => page.status === 'no_text')
    .map((page) => page.page);
  const extractedPageCount = documentPages.filter((page) => page.status === 'extracted').length;

  function clearPersistedSelection(): void {
    setSearchParams({});
    setDocumentRecord(null);
    setDocumentPages([]);
    setRun(null);
    setResult(null);
    setError(null);
    setActivity('idle');
  }

  function handleFileSelection(event: ChangeEvent<HTMLInputElement>): void {
    const file = event.target.files?.[0] ?? null;
    clearPersistedSelection();
    submissionKey.current = newIdempotencyKey();
    setSelectedFile(file);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!selectedFile || !canSubmit) {
      return;
    }

    setActivity('uploading');
    setError(null);
    setResult(null);
    try {
      const admittedDocument = await createDocument(selectedFile);
      const admittedPages = await getDocumentPages(admittedDocument.id);
      const createdRun = await createRun(
        admittedDocument.id,
        mode,
        confirmExternal,
        submissionKey.current,
      );
      setDocumentRecord(admittedDocument);
      setDocumentPages(admittedPages);
      setRun(createdRun);
      setSelectedFile(null);
      setActivity('waiting');
      setSearchParams({ run: createdRun.id });
    } catch (requestError: unknown) {
      const message = requestError instanceof Error ? requestError.message : 'Falha desconhecida.';
      setError(message);
      setActivity('idle');
    }
  }

  async function retryRun(): Promise<void> {
    if (!run || !documentRecord || !canRetry) {
      return;
    }

    setActivity('uploading');
    setError(null);
    try {
      if (retryIntent.current.sourceRunId !== run.id) {
        retryIntent.current = { sourceRunId: run.id, key: newIdempotencyKey() };
      }
      const createdRun = await createRun(
        documentRecord.id,
        run.mode,
        confirmExternal,
        retryIntent.current.key,
      );
      retryIntent.current = { sourceRunId: '', key: '' };
      setRun(createdRun);
      setResult(null);
      setConfirmExternal(false);
      setActivity('waiting');
      setSearchParams({ run: createdRun.id });
    } catch (requestError: unknown) {
      const message = requestError instanceof Error ? requestError.message : 'Falha desconhecida.';
      setError(message);
      setActivity('idle');
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-stone-100 text-stone-950">
      <div className="print:hidden">
        <Navbar />
      </div>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 print:max-w-none print:p-0 sm:px-6 lg:py-12">
        <header className="mb-8 max-w-3xl print:hidden">
          <p className="mb-2 text-sm font-semibold uppercase tracking-widest text-red-800">
            Avaliação documental
          </p>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Execute e reabra avaliações persistentes
          </h1>
          <p className="mt-3 text-stone-600">
            O documento e o run ficam no PostgreSQL local. A página acompanha o worker sem inventar
            porcentagens e pode reabrir o resultado pelo endereço desta execução.
          </p>
        </header>

        <div className="grid gap-6 print:block lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.4fr)]">
          <form
            className="h-fit rounded-2xl border border-stone-200 bg-white p-6 shadow-sm print:hidden"
            onSubmit={handleSubmit}
          >
            <fieldset disabled={!configuration || isBusy}>
              <legend className="text-lg font-semibold">1. Escolha o modo</legend>
              <div className="mt-4 space-y-3">
                {configuration?.capabilities.map((capability: Capability) => (
                  <label
                    className="flex cursor-pointer gap-3 rounded-xl border border-stone-200 p-4 has-[:checked]:border-red-700 has-[:checked]:bg-red-50 has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-60"
                    key={capability.mode}
                  >
                    <input
                      checked={mode === capability.mode}
                      className="mt-1 accent-red-800"
                      disabled={!capability.available}
                      name="evaluation-mode"
                      onChange={() => {
                        clearPersistedSelection();
                        submissionKey.current = newIdempotencyKey();
                        setMode(capability.mode);
                        setConfirmExternal(false);
                      }}
                      type="radio"
                      value={capability.mode}
                    />
                    <span>
                      <span className="block font-medium">{capability.label}</span>
                      <span className="mt-1 block text-sm text-stone-600">
                        {capability.provider} · {capability.model}
                      </span>
                      {capability.reason ? (
                        <span className="mt-1 block text-sm text-amber-800">
                          Indisponível: {capability.reason}
                        </span>
                      ) : null}
                    </span>
                  </label>
                ))}
                {!configuration && !error ? (
                  <p className="text-sm text-stone-600" role="status">
                    Consultando a API local…
                  </p>
                ) : null}
              </div>
            </fieldset>

            <div className="mt-7">
              <p className="text-lg font-semibold">2. Selecione um PDF digital</p>
              <label className="mt-4 flex cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-stone-400 px-4 py-6 font-medium hover:border-red-700 hover:bg-red-50 focus-within:ring-2 focus-within:ring-red-700 focus-within:ring-offset-2">
                <FaPaperclip aria-hidden="true" />
                <span>{selectedFile ? 'Trocar arquivo' : 'Selecionar arquivo'}</span>
                <input
                  accept="application/pdf,.pdf"
                  className="sr-only"
                  disabled={isBusy}
                  onChange={handleFileSelection}
                  type="file"
                />
              </label>
              {selectedFile ? (
                <p className="mt-3 break-all text-sm text-stone-700">
                  {selectedFile.name} · {formatBytes(selectedFile.size)}
                </p>
              ) : null}
              {configuration ? (
                <p className="mt-2 text-xs text-stone-500">
                  Limites: {formatBytes(configuration.max_upload_bytes)} e{' '}
                  {configuration.max_pages} páginas.
                </p>
              ) : null}
              {exceedsLimit ? (
                <p className="mt-2 text-sm text-red-800" role="alert">
                  O arquivo excede o limite informado pela API.
                </p>
              ) : null}
            </div>

            {mode === 'real' ? (
              <label className="mt-6 flex gap-3 rounded-xl bg-amber-50 p-4 text-sm text-amber-950">
                <input
                  checked={confirmExternal}
                  className="mt-1 accent-red-800"
                  disabled={isBusy}
                  onChange={(event) => setConfirmExternal(event.target.checked)}
                  type="checkbox"
                />
                <span>
                  Autorizo o envio do texto extraído ao Google Gemini. Cada reexecução real exige
                  nova confirmação e cria outro run.
                </span>
              </label>
            ) : null}

            <button
              className="mt-7 w-full rounded-xl bg-red-800 px-5 py-3 font-semibold text-white transition hover:bg-red-900 focus:outline-none focus:ring-2 focus:ring-red-700 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-stone-400"
              disabled={!canSubmit}
              type="submit"
            >
              {activity === 'uploading' ? 'Persistindo solicitação…' : 'Executar avaliação'}
            </button>
          </form>

          <section
            aria-busy={activity === 'waiting'}
            aria-labelledby="result-title"
            className="min-h-96 rounded-2xl border border-stone-200 bg-white p-6 shadow-sm print:min-h-0 print:border-0 print:p-0 print:shadow-none"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold uppercase tracking-widest text-red-800">
                  Resultado persistente
                </p>
                <h2 className="mt-1 text-2xl font-bold" id="result-title">
                  Parecer da execução
                </h2>
              </div>
              {documentRecord && run && result ? (
                <div className="flex flex-wrap gap-2 print:hidden">
                  <button
                    className="inline-flex items-center gap-2 rounded-lg border border-stone-300 px-3 py-2 text-sm font-semibold hover:border-red-700 focus:outline-none focus:ring-2 focus:ring-red-700"
                    onClick={() => downloadRunJson(documentRecord, run, result)}
                    type="button"
                  >
                    <FaFileArrowDown aria-hidden="true" />
                    Exportar JSON
                  </button>
                  <button
                    className="inline-flex items-center gap-2 rounded-lg border border-stone-300 px-3 py-2 text-sm font-semibold hover:border-red-700 focus:outline-none focus:ring-2 focus:ring-red-700"
                    onClick={() => downloadRunMarkdown(documentRecord, run, result)}
                    type="button"
                  >
                    <FaFileArrowDown aria-hidden="true" />
                    Exportar Markdown
                  </button>
                  <button
                    className="rounded-lg border border-stone-300 px-3 py-2 text-sm font-semibold hover:border-red-700 focus:outline-none focus:ring-2 focus:ring-red-700"
                    onClick={() => window.print()}
                    type="button"
                  >
                    Imprimir
                  </button>
                </div>
              ) : null}
            </div>

            {error ? (
              <div
                className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-red-900"
                role="alert"
              >
                <p className="font-semibold">A operação não foi concluída.</p>
                <p className="mt-1 text-sm">{error}</p>
              </div>
            ) : null}

            {run && documentRecord ? (
              <div className="mt-6 space-y-5">
                <div
                  className={`rounded-xl border p-4 ${
                    run.status === 'succeeded'
                      ? 'border-emerald-300 bg-emerald-50 text-emerald-950'
                      : run.status === 'failed' || run.status === 'interrupted'
                        ? 'border-red-300 bg-red-50 text-red-950'
                        : 'border-amber-300 bg-amber-50 text-amber-950'
                  }`}
                  role="status"
                >
                  <p className="font-bold">{statusLabels[run.status]}</p>
                  <p className="mt-1 text-sm">
                    {documentRecord.file_name} · {run.provider} · {run.model}
                  </p>
                  {run.status === 'queued' || run.status === 'running' ? (
                    <p className="mt-2 text-sm">Aguardando o worker local concluir esta etapa.</p>
                  ) : null}
                  {run.error_message ? (
                    <p className="mt-2 text-sm">
                      {run.error_code}: {run.error_message}
                    </p>
                  ) : null}
                </div>

                <dl className="grid gap-3 rounded-xl bg-stone-100 p-4 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="font-semibold text-stone-600">Run</dt>
                    <dd className="mt-1 break-all font-mono text-xs">{run.id}</dd>
                  </div>
                  <div>
                    <dt className="font-semibold text-stone-600">Modo e prompt</dt>
                    <dd className="mt-1">{run.mode} · {run.prompt_version}</dd>
                  </div>
                  <div>
                    <dt className="font-semibold text-stone-600">Criado</dt>
                    <dd className="mt-1">{formatDate(run.created_at)}</dd>
                  </div>
                  <div>
                    <dt className="font-semibold text-stone-600">Finalizado</dt>
                    <dd className="mt-1">{formatDate(run.finished_at)}</dd>
                  </div>
                  <div>
                    <dt className="font-semibold text-stone-600">Consumo</dt>
                    <dd className="mt-1">
                      {run.usage_kind ?? 'não registrado'} · entrada {run.input_tokens ?? '—'} ·
                      saída {run.output_tokens ?? '—'}
                    </dd>
                  </div>
                  <div>
                    <dt className="font-semibold text-stone-600">Documento</dt>
                    <dd className="mt-1">
                      {documentRecord.page_count} página(s) · {documentRecord.character_count}{' '}
                      caracteres
                    </dd>
                  </div>
                </dl>

                {documentPages.length > 0 ? (
                  <div
                    className={`rounded-xl border p-4 text-sm ${
                      ocrCandidatePages.length || noTextPages.length
                        ? 'border-amber-300 bg-amber-50 text-amber-950'
                        : 'border-emerald-300 bg-emerald-50 text-emerald-950'
                    }`}
                  >
                    <p className="font-bold">
                      {ocrCandidatePages.length || noTextPages.length
                        ? 'Extração parcial — revise as páginas sinalizadas'
                        : 'Texto extraído em todas as páginas'}
                    </p>
                    <p className="mt-1">
                      Texto extraído em {extractedPageCount} de {documentPages.length} página(s).
                    </p>
                    {ocrCandidatePages.length ? (
                      <p className="mt-1">
                        Candidatas a OCR por conter imagem sem texto: páginas{' '}
                        {ocrCandidatePages.join(', ')}. OCR não foi executado.
                      </p>
                    ) : null}
                    {noTextPages.length ? (
                      <p className="mt-1">
                        Sem texto ou imagem raster detectável: páginas {noTextPages.join(', ')}.
                        Isso não comprova que estejam semanticamente vazias.
                      </p>
                    ) : null}
                  </div>
                ) : null}

                {result ? (
                  <>
                    <div
                      className={`rounded-xl border p-4 ${
                        result.report.simulated
                          ? 'border-amber-300 bg-amber-50 text-amber-950'
                          : 'border-emerald-300 bg-emerald-50 text-emerald-950'
                      }`}
                    >
                      <p className="font-bold">
                        {result.report.simulated
                          ? 'Simulado — sem inferência LLM'
                          : 'Real — inferência externa autorizada'}
                      </p>
                      <p className="mt-1 text-sm">Parecer validado e reaberto do PostgreSQL local.</p>
                    </div>
                    <div className="result-markdown">
                      <ReactMarkdown>{result.result_markdown}</ReactMarkdown>
                    </div>
                  </>
                ) : null}

                {run.status === 'failed' || run.status === 'interrupted' ? (
                  <button
                    className="inline-flex items-center gap-2 rounded-lg bg-red-800 px-4 py-2 font-semibold text-white hover:bg-red-900 focus:outline-none focus:ring-2 focus:ring-red-700 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-stone-400"
                    disabled={!canRetry}
                    onClick={() => void retryRun()}
                    type="button"
                  >
                    <FaArrowRotateRight aria-hidden="true" />
                    Reexecutar como novo run
                  </button>
                ) : null}
              </div>
            ) : null}

            {!run && !error && activity === 'idle' ? (
              <div className="mt-8 rounded-xl bg-stone-100 p-6 text-stone-600">
                Selecione o modo e o arquivo. A execução só começa ao acionar “Executar avaliação”.
              </div>
            ) : null}
            {!run && activity !== 'idle' ? (
              <p className="mt-8 text-stone-600" role="status">
                Persistindo o documento e criando o run…
              </p>
            ) : null}
          </section>
        </div>

        <section className="mt-6 rounded-2xl border border-stone-200 bg-white p-6 shadow-sm print:hidden">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-sm font-semibold uppercase tracking-widest text-red-800">
                Histórico local
              </p>
              <h2 className="mt-1 text-2xl font-bold">Execuções recentes</h2>
            </div>
            {runId ? (
              <button
                className="rounded-lg border border-stone-300 px-3 py-2 text-sm font-semibold hover:border-red-700 focus:outline-none focus:ring-2 focus:ring-red-700"
                onClick={() => {
                  clearPersistedSelection();
                  setSelectedFile(null);
                }}
                type="button"
              >
                Nova avaliação
              </button>
            ) : null}
          </div>

          {historyError ? <p className="mt-4 text-sm text-red-800">{historyError}</p> : null}
          {!historyError && recentRuns.length === 0 ? (
            <p className="mt-4 text-stone-600">Nenhuma execução persistida ainda.</p>
          ) : null}
          {recentRuns.length > 0 ? (
            <ul className="mt-4 divide-y divide-stone-200">
              {recentRuns.slice(0, 10).map((recentRun) => (
                <li className="py-3" key={recentRun.id}>
                  <button
                    className="flex w-full flex-col gap-1 rounded-lg p-2 text-left hover:bg-stone-100 focus:outline-none focus:ring-2 focus:ring-red-700 sm:flex-row sm:items-center sm:justify-between"
                    onClick={() => {
                      setSelectedFile(null);
                      setConfirmExternal(false);
                      setSearchParams({ run: recentRun.id });
                    }}
                    type="button"
                  >
                    <span>
                      <span className="block font-semibold">
                        {documentsById.get(recentRun.document_id)?.file_name ?? 'Documento local'}
                      </span>
                      <span className="block text-xs text-stone-500">
                        {recentRun.mode === 'demo'
                          ? 'Simulado — sem inferência LLM'
                          : 'Real — inferência externa autorizada'}
                        {' · '}
                        {recentRun.provider} · {recentRun.model} · {formatDate(recentRun.created_at)}
                      </span>
                    </span>
                    <span className="text-sm font-semibold text-stone-700">
                      {statusLabels[recentRun.status]}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </section>

        <section className="mt-6 rounded-2xl border border-stone-200 bg-white p-6 shadow-sm print:hidden">
          <p className="text-sm font-semibold uppercase tracking-widest text-red-800">
            Comparação descritiva
          </p>
          <h2 className="mt-1 text-2xl font-bold">Compare dois runs concluídos</h2>
          <p className="mt-2 max-w-3xl text-sm text-stone-600">
            A comparação exige o mesmo documento e apresenta configurações e resultados congelados.
            Ela não escolhe vencedor nem substitui revisão humana.
          </p>

          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-semibold text-stone-700">
              Run esquerdo
              <select
                className="mt-2 block w-full rounded-lg border border-stone-300 bg-white px-3 py-2 font-normal focus:outline-none focus:ring-2 focus:ring-red-700"
                onChange={(event) => setLeftRunId(event.target.value)}
                value={leftRunId}
              >
                <option value="">Selecione</option>
                {recentRuns
                  .filter((recentRun) => recentRun.status === 'succeeded')
                  .map((recentRun) => (
                    <option key={recentRun.id} value={recentRun.id}>
                      {documentsById.get(recentRun.document_id)?.file_name ?? 'Documento local'} ·{' '}
                      {recentRun.id.slice(0, 8)} · {recentRun.model}
                    </option>
                  ))}
              </select>
            </label>
            <label className="text-sm font-semibold text-stone-700">
              Run direito
              <select
                className="mt-2 block w-full rounded-lg border border-stone-300 bg-white px-3 py-2 font-normal focus:outline-none focus:ring-2 focus:ring-red-700"
                onChange={(event) => setRightRunId(event.target.value)}
                value={rightRunId}
              >
                <option value="">Selecione</option>
                {recentRuns
                  .filter((recentRun) => recentRun.status === 'succeeded')
                  .map((recentRun) => (
                    <option key={recentRun.id} value={recentRun.id}>
                      {documentsById.get(recentRun.document_id)?.file_name ?? 'Documento local'} ·{' '}
                      {recentRun.id.slice(0, 8)} · {recentRun.model}
                    </option>
                  ))}
              </select>
            </label>
          </div>

          {comparisonLoading ? (
            <p className="mt-4 text-stone-600" role="status">
              Carregando os pareceres congelados…
            </p>
          ) : null}
          {comparisonError ? (
            <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-900" role="alert">
              {comparisonError}
            </p>
          ) : null}

          {comparison ? (
            <div className="mt-6 overflow-x-auto">
              <table className="w-full min-w-[42rem] border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-stone-300">
                    <th className="p-3">Campo</th>
                    <th className="p-3">Run {comparison.leftRun.id.slice(0, 8)}</th>
                    <th className="p-3">Run {comparison.rightRun.id.slice(0, 8)}</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ['Modo', comparison.leftRun.mode, comparison.rightRun.mode],
                    [
                      'Provedor/modelo',
                      `${comparison.leftRun.provider} / ${comparison.leftRun.model}`,
                      `${comparison.rightRun.provider} / ${comparison.rightRun.model}`,
                    ],
                    [
                      'Prompt',
                      comparison.leftRun.prompt_version,
                      comparison.rightRun.prompt_version,
                    ],
                    [
                      'Duração',
                      formatDuration(comparison.leftRun),
                      formatDuration(comparison.rightRun),
                    ],
                    [
                      'Criado',
                      formatDate(comparison.leftRun.created_at),
                      formatDate(comparison.rightRun.created_at),
                    ],
                    [
                      'Finalizado',
                      formatDate(comparison.leftRun.finished_at),
                      formatDate(comparison.rightRun.finished_at),
                    ],
                    [
                      'Consumo',
                      `${comparison.leftRun.usage_kind ?? '—'} · ${comparison.leftRun.input_tokens ?? '—'}/${comparison.leftRun.output_tokens ?? '—'} tokens`,
                      `${comparison.rightRun.usage_kind ?? '—'} · ${comparison.rightRun.input_tokens ?? '—'}/${comparison.rightRun.output_tokens ?? '—'} tokens`,
                    ],
                    [
                      'Título do parecer',
                      comparison.leftResult.report.title,
                      comparison.rightResult.report.title,
                    ],
                    ...comparison.leftResult.report.dimensions.map((leftDimension) => {
                      const rightDimension = comparison.rightResult.report.dimensions.find(
                        (item) => item.dimension === leftDimension.dimension,
                      );
                      const describe = (score: number | null, insufficient: boolean) =>
                        insufficient ? 'Evidência insuficiente' : `Nota ${score ?? '—'}`;
                      return [
                        dimensionLabels[leftDimension.dimension],
                        `${describe(leftDimension.score, leftDimension.insufficient)} — ${leftDimension.justification}`,
                        rightDimension
                          ? `${describe(rightDimension.score, rightDimension.insufficient)} — ${rightDimension.justification}`
                          : 'Dimensão ausente',
                      ];
                    }),
                  ].map(([label, leftValue, rightValue]) => (
                    <tr className="border-b border-stone-200 align-top" key={label}>
                      <th className="p-3 font-semibold text-stone-700">{label}</th>
                      <td className="p-3 text-stone-700">{leftValue}</td>
                      <td className="p-3 text-stone-700">{rightValue}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>
      </main>
      <div className="print:hidden">
        <Footer />
      </div>
    </div>
  );
}
