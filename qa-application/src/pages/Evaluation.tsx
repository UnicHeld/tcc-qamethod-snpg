import { FormEvent, useEffect, useState } from 'react';
import { FaFileArrowDown, FaPaperclip } from 'react-icons/fa6';
import ReactMarkdown from 'react-markdown';

import Footer from '../components/Footer';
import Navbar from '../components/Navbar';
import {
  Capability,
  CapabilitiesResponse,
  EvaluationMode,
  EvaluationResponse,
  evaluateDocument,
  getCapabilities,
} from '../lib/api';

function formatBytes(bytes: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'unit',
    unit: 'megabyte',
    maximumFractionDigits: 0,
  }).format(bytes / (1024 * 1024));
}

function exportResult(result: EvaluationResponse): void {
  const payload = JSON.stringify(result, null, 2);
  const url = URL.createObjectURL(new Blob([payload], { type: 'application/json' }));
  const link = document.createElement('a');
  const baseName = result.document.file_name.replace(/\.pdf$/i, '').replace(/[^a-z0-9_-]+/gi, '-');
  link.href = url;
  link.download = `${baseName || 'documento'}-avaliacao.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export default function Evaluation() {
  const [configuration, setConfiguration] = useState<CapabilitiesResponse | null>(null);
  const [mode, setMode] = useState<EvaluationMode>('demo');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [confirmExternal, setConfirmExternal] = useState(false);
  const [result, setResult] = useState<EvaluationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    getCapabilities(controller.signal)
      .then((response) => {
        setConfiguration(response);
        setMode(response.default_mode);
      })
      .catch((requestError: unknown) => {
        if (requestError instanceof DOMException && requestError.name === 'AbortError') {
          return;
        }
        setError('Não foi possível consultar as capacidades da API local.');
      });
    return () => controller.abort();
  }, []);

  const selectedCapability = configuration?.capabilities.find(
    (capability) => capability.mode === mode,
  );
  const exceedsLimit = Boolean(
    selectedFile && configuration && selectedFile.size > configuration.max_upload_bytes,
  );
  const canSubmit = Boolean(
    selectedFile &&
      selectedCapability?.available &&
      !exceedsLimit &&
      !isLoading &&
      (mode === 'demo' || confirmExternal),
  );

  function handleFileSelection(event: React.ChangeEvent<HTMLInputElement>): void {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    setResult(null);
    setError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!selectedFile || !canSubmit) {
      return;
    }

    setIsLoading(true);
    setError(null);
    setResult(null);
    try {
      const evaluation = await evaluateDocument(selectedFile, mode, confirmExternal);
      setResult(evaluation);
    } catch (requestError: unknown) {
      const message = requestError instanceof Error ? requestError.message : 'Falha desconhecida.';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-stone-100 text-stone-950">
      <Navbar />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 lg:py-12">
        <header className="mb-8 max-w-3xl">
          <p className="mb-2 text-sm font-semibold uppercase tracking-widest text-red-800">
            Avaliação documental
          </p>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Execute uma avaliação com modo e destino explícitos
          </h1>
          <p className="mt-3 text-stone-600">
            O perfil padrão funciona sem credenciais. PDFs escaneados ainda exigem OCR e serão
            recusados com uma orientação clara.
          </p>
        </header>

        <div className="grid gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.4fr)]">
          <form
            className="h-fit rounded-2xl border border-stone-200 bg-white p-6 shadow-sm"
            onSubmit={handleSubmit}
          >
            <fieldset disabled={!configuration || isLoading}>
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
                        setMode(capability.mode);
                        setConfirmExternal(false);
                        setResult(null);
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
                  onChange={(event) => setConfirmExternal(event.target.checked)}
                  type="checkbox"
                />
                <span>
                  Autorizo o envio do texto extraído deste documento ao Google Gemini. Verifiquei
                  autorização dos dados, quota e política de faturamento da conta.
                </span>
              </label>
            ) : null}

            <button
              className="mt-7 w-full rounded-xl bg-red-800 px-5 py-3 font-semibold text-white transition hover:bg-red-900 focus:outline-none focus:ring-2 focus:ring-red-700 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-stone-400"
              disabled={!canSubmit}
              type="submit"
            >
              {isLoading ? 'Extraindo e avaliando…' : 'Executar avaliação'}
            </button>
          </form>

          <section
            aria-busy={isLoading}
            aria-labelledby="result-title"
            className="min-h-96 rounded-2xl border border-stone-200 bg-white p-6 shadow-sm"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold uppercase tracking-widest text-red-800">
                  Resultado
                </p>
                <h2 className="mt-1 text-2xl font-bold" id="result-title">
                  Parecer da execução
                </h2>
              </div>
              {result ? (
                <button
                  className="inline-flex items-center gap-2 rounded-lg border border-stone-300 px-3 py-2 text-sm font-semibold hover:border-red-700 focus:outline-none focus:ring-2 focus:ring-red-700"
                  onClick={() => exportResult(result)}
                  type="button"
                >
                  <FaFileArrowDown aria-hidden="true" />
                  Exportar JSON
                </button>
              ) : null}
            </div>

            {error ? (
              <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-red-900" role="alert">
                <p className="font-semibold">A execução não foi concluída.</p>
                <p className="mt-1 text-sm">{error}</p>
              </div>
            ) : null}
            {isLoading ? (
              <p className="mt-8 text-stone-600" role="status">
                Extraindo o PDF e aguardando o avaliador…
              </p>
            ) : null}
            {!result && !error && !isLoading ? (
              <div className="mt-8 rounded-xl bg-stone-100 p-6 text-stone-600">
                Selecione o modo e o arquivo. A execução só começa ao acionar “Executar avaliação”.
              </div>
            ) : null}
            {result ? (
              <div className="mt-6">
                <div
                  className={`rounded-xl border p-4 ${
                    result.simulated
                      ? 'border-amber-300 bg-amber-50 text-amber-950'
                      : 'border-emerald-300 bg-emerald-50 text-emerald-950'
                  }`}
                  role="status"
                >
                  <p className="font-bold">{result.mode_label}</p>
                  <p className="mt-1 text-sm">
                    {result.provider} · {result.model} · {result.document.page_count} página(s)
                  </p>
                </div>
                <div className="result-markdown mt-6">
                  <ReactMarkdown>{result.result_markdown}</ReactMarkdown>
                </div>
              </div>
            ) : null}
          </section>
        </div>
      </main>
      <Footer />
    </div>
  );
}
