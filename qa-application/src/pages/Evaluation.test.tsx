import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import Evaluation from './Evaluation';

const documentRecord = {
  id: 'document-1',
  file_name: 'fixture.pdf',
  sha256: 'a'.repeat(64),
  page_count: 1,
  character_count: 42,
  created_at: '2026-09-14T12:00:00Z',
};

const extractedPages = {
  pages: [
    {
      document_id: documentRecord.id,
      page: 1,
      status: 'extracted',
      character_count: 42,
      has_images: false,
    },
  ],
};

const partialPages = {
  pages: [
    extractedPages.pages[0],
    {
      document_id: documentRecord.id,
      page: 2,
      status: 'ocr_candidate',
      character_count: 0,
      has_images: true,
    },
    {
      document_id: documentRecord.id,
      page: 3,
      status: 'no_text',
      character_count: 0,
      has_images: false,
    },
  ],
};

const capabilities = {
  default_mode: 'demo',
  max_upload_bytes: 20 * 1024 * 1024,
  max_pages: 300,
  capabilities: [
    {
      mode: 'demo',
      label: 'Simulado — sem inferência LLM',
      available: true,
      reason: null,
      provider: 'local',
      model: 'deterministic-demo-v1',
      requires_external_confirmation: false,
    },
    {
      mode: 'real',
      label: 'Real — inferência externa autorizada',
      available: false,
      reason: 'Configure a chave no backend.',
      provider: 'google-gemini',
      model: 'gemini-3.5-flash-lite',
      requires_external_confirmation: true,
    },
  ],
  judge_capabilities: [
    {
      mode: 'demo',
      label: 'Simulado — validação técnica sem inferência LLM',
      available: true,
      reason: null,
      provider: 'local',
      model: 'deterministic-judge-demo-v1',
      requires_external_confirmation: false,
    },
    {
      mode: 'real',
      label: 'LLM as judge — inferência externa autorizada',
      available: false,
      reason: 'Configure QA_JUDGE_GEMINI_MODEL no backend.',
      provider: 'google-gemini',
      model: 'não configurado',
      requires_external_confirmation: true,
    },
  ],
  retrieval_capabilities: [],
};

function runRecord(
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'interrupted',
  id = 'run-1',
) {
  const terminal = status === 'succeeded' || status === 'failed' || status === 'interrupted';
  return {
    id,
    document_id: documentRecord.id,
    mode: 'demo',
    provider: 'local',
    model: 'deterministic-demo-v1',
    prompt_version: 'qa-method-structured-v2',
    status,
    usage_kind: status === 'succeeded' ? 'simulated' : null,
    credential_slot: null,
    input_tokens: null,
    output_tokens: null,
    error_code: status === 'interrupted' ? 'worker_interrupted' : null,
    error_message: status === 'interrupted' ? 'O worker anterior foi interrompido.' : null,
    created_at: '2026-09-14T12:00:00Z',
    started_at: status === 'queued' ? null : '2026-09-14T12:00:01Z',
    finished_at: terminal ? '2026-09-14T12:00:02Z' : null,
  };
}

const runResult = {
  run_id: 'run-1',
  report: {
    revision_sha256: 'a'.repeat(64),
    simulated: true,
    title: 'Parecer técnico de demonstração',
    summary: 'Resumo simulado.',
    dimensions: [],
  },
  result_markdown: '# Parecer persistido\n\nResultado de teste.',
};

function judgeRunRecord(
  status: 'queued' | 'running' | 'succeeded',
  mode: 'demo' | 'real' = 'demo',
) {
  return {
    id: 'judge-1',
    source_run_id: 'run-1',
    document_id: documentRecord.id,
    mode,
    provider: mode === 'demo' ? 'local' : 'google-gemini',
    model: mode === 'demo' ? 'deterministic-judge-demo-v1' : 'judge-model',
    prompt_version: 'qa-method-judge-v2',
    status,
    source_report_sha256: 'b'.repeat(64),
    usage_kind: status === 'succeeded' ? (mode === 'demo' ? 'simulated' : 'actual') : null,
    credential_slot: status === 'succeeded' && mode === 'real' ? 'primary' : null,
    input_tokens: null,
    output_tokens: null,
    error_code: null,
    error_message: null,
    created_at: '2026-09-16T12:00:00Z',
    started_at: status === 'queued' ? null : '2026-09-16T12:00:01Z',
    finished_at: status === 'succeeded' ? '2026-09-16T12:00:02Z' : null,
  };
}

const judgeResult = {
  judge_run_id: 'judge-1',
  source_report: runResult.report,
  source_evidence: {
    document_id: documentRecord.id,
    revision_sha256: 'a'.repeat(64),
    source_report_sha256: 'b'.repeat(64),
    items: [
      {
        unit_id: `${'a'.repeat(64)}:page:1`,
        page: 1,
        text: 'Evidência congelada.',
      },
    ],
  },
  report: {
    source_run_id: 'run-1',
    source_report_sha256: 'b'.repeat(64),
    revision_sha256: 'a'.repeat(64),
    simulated: true,
    verdict: 'needs_human_review',
    summary: 'A auditoria determinística exige revisão humana.',
    findings: [],
  },
  result_markdown: '# Auditoria de parecer\n\nFluxo técnico validado.',
};

function comparisonResult(runId: string, title: string, score: number) {
  return {
    ...runResult,
    run_id: runId,
    report: {
      ...runResult.report,
      title,
      dimensions: [
        {
          dimension: 'originality',
          insufficient: false,
          score,
          justification: `Justificativa ${score}.`,
          evidence_ids: [`${'a'.repeat(64)}:page:1`],
        },
      ],
    },
  };
}

function jsonResponse(payload: object, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('Evaluation', () => {
  it('admite o documento, cria o run idempotente e publica o resultado persistido', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      const method = init?.method ?? 'GET';
      if (url.endsWith('/capabilities')) {
        return jsonResponse(capabilities);
      }
      if (url.endsWith('/api/v1/documents') && method === 'GET') {
        return jsonResponse({ documents: [] });
      }
      if (url.endsWith('/api/v1/documents') && method === 'POST') {
        return jsonResponse(documentRecord, 201);
      }
      if (url.endsWith('/api/v1/documents/document-1/pages')) {
        return jsonResponse(extractedPages);
      }
      if (url.endsWith('/api/v1/runs') && method === 'GET') {
        return jsonResponse({ runs: [] });
      }
      if (url.endsWith('/api/v1/runs') && method === 'POST') {
        return jsonResponse(runRecord('queued'), 202);
      }
      if (url.endsWith('/api/v1/runs/run-1/result')) {
        return jsonResponse(runResult);
      }
      if (url.endsWith('/api/v1/runs/run-1')) {
        return jsonResponse(runRecord('succeeded'));
      }
      if (url.endsWith('/api/v1/documents/document-1')) {
        return jsonResponse(documentRecord);
      }
      throw new Error(`URL inesperada: ${method} ${url}`);
    });
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={['/evaluation']}>
        <Evaluation />
      </MemoryRouter>,
    );

    await screen.findByText('local · deterministic-demo-v1');
    await user.upload(
      screen.getByLabelText('Selecionar arquivo'),
      new File(['%PDF-1.4'], 'fixture.pdf', { type: 'application/pdf' }),
    );
    await user.click(screen.getByRole('button', { name: 'Executar avaliação' }));

    expect(await screen.findByText('Parecer persistido')).toBeInTheDocument();
    expect(screen.getAllByText('Simulado — sem inferência LLM')).toHaveLength(2);
    expect(screen.getByRole('button', { name: 'Exportar JSON' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Exportar Markdown' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Imprimir' })).toBeEnabled();
    expect(screen.getByText('Texto extraído em todas as páginas')).toBeInTheDocument();

    const runSubmission = fetchMock.mock.calls.find(
      ([input, init]) => String(input).endsWith('/api/v1/runs') && init?.method === 'POST',
    );
    expect(runSubmission).toBeDefined();
    const headers = new Headers(runSubmission?.[1]?.headers);
    expect(headers.get('Idempotency-Key')).not.toBeNull();
    expect(JSON.parse(String(runSubmission?.[1]?.body))).toMatchObject({
      document_id: documentRecord.id,
      mode: 'demo',
      confirm_external_processing: false,
    });
  });

  it('reabre um resultado diretamente pelo identificador na URL', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/capabilities')) {
        return jsonResponse(capabilities);
      }
      if (url.endsWith('/api/v1/documents')) {
        return jsonResponse({ documents: [documentRecord] });
      }
      if (url.endsWith('/api/v1/runs')) {
        return jsonResponse({ runs: [runRecord('succeeded')] });
      }
      if (url.endsWith('/api/v1/runs/run-1/result')) {
        return jsonResponse(runResult);
      }
      if (url.endsWith('/api/v1/runs/run-1')) {
        return jsonResponse(runRecord('succeeded'));
      }
      if (url.endsWith('/api/v1/documents/document-1/pages')) {
        return jsonResponse(partialPages);
      }
      if (url.endsWith('/api/v1/documents/document-1')) {
        return jsonResponse({ ...documentRecord, page_count: 3 });
      }
      throw new Error(`URL inesperada: ${url}`);
    });

    render(
      <MemoryRouter initialEntries={['/evaluation?run=run-1']}>
        <Evaluation />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Parecer persistido')).toBeInTheDocument();
    expect(screen.getByText('Parecer validado e reaberto do PostgreSQL local.')).toBeInTheDocument();
    expect(screen.getByText('run-1')).toBeInTheDocument();
    expect(screen.getAllByText(/Simulado — sem inferência LLM/).length).toBeGreaterThanOrEqual(2);
    expect(
      screen.getByText('Extração parcial — revise as páginas sinalizadas'),
    ).toBeInTheDocument();
    expect(screen.getByText(/Candidatas a OCR.*páginas 2/)).toBeInTheDocument();
    expect(screen.getByText(/semanticamente vazias/)).toBeInTheDocument();
  });

  it('reexecuta um run interrompido somente como uma nova solicitação', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      const method = init?.method ?? 'GET';
      if (url.endsWith('/capabilities')) {
        return jsonResponse(capabilities);
      }
      if (url.endsWith('/api/v1/documents')) {
        return jsonResponse({ documents: [documentRecord] });
      }
      if (url.endsWith('/api/v1/runs') && method === 'GET') {
        return jsonResponse({ runs: [runRecord('interrupted', 'run-old')] });
      }
      if (url.endsWith('/api/v1/runs') && method === 'POST') {
        return jsonResponse(runRecord('queued', 'run-new'), 202);
      }
      if (url.endsWith('/api/v1/runs/run-old')) {
        return jsonResponse(runRecord('interrupted', 'run-old'));
      }
      if (url.endsWith('/api/v1/runs/run-new/result')) {
        return jsonResponse({ ...runResult, run_id: 'run-new' });
      }
      if (url.endsWith('/api/v1/runs/run-new')) {
        return jsonResponse(runRecord('succeeded', 'run-new'));
      }
      if (url.endsWith('/api/v1/documents/document-1/pages')) {
        return jsonResponse(extractedPages);
      }
      if (url.endsWith('/api/v1/documents/document-1')) {
        return jsonResponse(documentRecord);
      }
      throw new Error(`URL inesperada: ${method} ${url}`);
    });
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={['/evaluation?run=run-old']}>
        <Evaluation />
      </MemoryRouter>,
    );

    const retryButton = await screen.findByRole('button', {
      name: 'Reexecutar como novo run',
    });
    await user.click(retryButton);

    expect(await screen.findByText('Parecer persistido')).toBeInTheDocument();
    expect(screen.getByText('run-new')).toBeInTheDocument();
    const submissions = fetchMock.mock.calls.filter(
      ([input, init]) => String(input).endsWith('/api/v1/runs') && init?.method === 'POST',
    );
    expect(submissions).toHaveLength(1);
  });

  it('compara dois pareceres congelados do mesmo documento sem escolher vencedor', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/capabilities')) {
        return jsonResponse(capabilities);
      }
      if (url.endsWith('/api/v1/documents')) {
        return jsonResponse({ documents: [documentRecord] });
      }
      if (url.endsWith('/api/v1/runs')) {
        return jsonResponse({
          runs: [runRecord('succeeded', 'run-left'), runRecord('succeeded', 'run-right')],
        });
      }
      if (url.endsWith('/api/v1/runs/run-left/result')) {
        return jsonResponse(comparisonResult('run-left', 'Parecer esquerdo', 4));
      }
      if (url.endsWith('/api/v1/runs/run-right/result')) {
        return jsonResponse(comparisonResult('run-right', 'Parecer direito', 7));
      }
      throw new Error(`URL inesperada: ${url}`);
    });
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={['/evaluation']}>
        <Evaluation />
      </MemoryRouter>,
    );

    expect(await screen.findAllByRole('option', { name: /run-left/ })).toHaveLength(2);
    await user.selectOptions(screen.getByLabelText('Run esquerdo'), 'run-left');
    await user.selectOptions(screen.getByLabelText('Run direito'), 'run-right');

    expect(await screen.findByText('Parecer esquerdo')).toBeInTheDocument();
    expect(screen.getByText('Parecer direito')).toBeInTheDocument();
    expect(screen.getByText('Nota 4 — Justificativa 4.')).toBeInTheDocument();
    expect(screen.getByText('Nota 7 — Justificativa 7.')).toBeInTheDocument();
    expect(screen.getByText(/não escolhe vencedor/)).toBeInTheDocument();
  });

  it('executa o judge demo sobre um snapshot sem alterar o parecer exibido', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      const method = init?.method ?? 'GET';
      if (url.endsWith('/capabilities')) {
        return jsonResponse(capabilities);
      }
      if (url.endsWith('/api/v1/documents')) {
        return jsonResponse({ documents: [documentRecord] });
      }
      if (url.endsWith('/api/v1/runs')) {
        return jsonResponse({ runs: [runRecord('succeeded')] });
      }
      if (url.endsWith('/api/v1/runs/run-1/result')) {
        return jsonResponse(runResult);
      }
      if (url.endsWith('/api/v1/runs/run-1')) {
        return jsonResponse(runRecord('succeeded'));
      }
      if (url.endsWith('/api/v1/documents/document-1/pages')) {
        return jsonResponse(extractedPages);
      }
      if (url.endsWith('/api/v1/documents/document-1')) {
        return jsonResponse(documentRecord);
      }
      if (url.endsWith('/api/v1/judge-runs') && method === 'POST') {
        return jsonResponse(judgeRunRecord('queued'), 202);
      }
      if (url.endsWith('/api/v1/judge-runs/judge-1/result')) {
        return jsonResponse(judgeResult);
      }
      if (url.endsWith('/api/v1/judge-runs/judge-1')) {
        return jsonResponse(judgeRunRecord('succeeded'));
      }
      throw new Error(`URL inesperada: ${method} ${url}`);
    });
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={['/evaluation?run=run-1']}>
        <Evaluation />
      </MemoryRouter>,
    );

    await user.click(await screen.findByRole('button', { name: 'Executar judge demo' }));

    expect(await screen.findByText('Fluxo técnico validado.')).toBeInTheDocument();
    expect(screen.getByText('Parecer persistido')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Exportar judge JSON' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Exportar judge Markdown' })).toBeEnabled();
    const submission = fetchMock.mock.calls.find(
      ([input, init]) =>
        String(input).endsWith('/api/v1/judge-runs') && init?.method === 'POST',
    );
    expect(JSON.parse(String(submission?.[1]?.body))).toEqual({
      source_run_id: 'run-1',
      mode: 'demo',
      confirm_external_processing: false,
    });
    expect(new Headers(submission?.[1]?.headers).get('Idempotency-Key')).not.toBeNull();
  });

  it('exige consentimento antes de executar LLM as judge com outro modelo', async () => {
    const realJudgeCapabilities = {
      ...capabilities,
      judge_capabilities: capabilities.judge_capabilities.map((capability) =>
        capability.mode === 'real'
          ? { ...capability, available: true, reason: null, model: 'judge-model' }
          : capability,
      ),
    };
    const realJudgeResult = {
      ...judgeResult,
      report: { ...judgeResult.report, simulated: false, summary: 'Auditoria real concluída.' },
    };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      const method = init?.method ?? 'GET';
      if (url.endsWith('/capabilities')) {
        return jsonResponse(realJudgeCapabilities);
      }
      if (url.endsWith('/api/v1/documents')) {
        return jsonResponse({ documents: [documentRecord] });
      }
      if (url.endsWith('/api/v1/runs')) {
        return jsonResponse({ runs: [runRecord('succeeded')] });
      }
      if (url.endsWith('/api/v1/runs/run-1/result')) {
        return jsonResponse(runResult);
      }
      if (url.endsWith('/api/v1/runs/run-1')) {
        return jsonResponse(runRecord('succeeded'));
      }
      if (url.endsWith('/api/v1/documents/document-1/pages')) {
        return jsonResponse(extractedPages);
      }
      if (url.endsWith('/api/v1/documents/document-1')) {
        return jsonResponse(documentRecord);
      }
      if (url.endsWith('/api/v1/judge-runs') && method === 'POST') {
        return jsonResponse(judgeRunRecord('queued', 'real'), 202);
      }
      if (url.endsWith('/api/v1/judge-runs/judge-1/result')) {
        return jsonResponse(realJudgeResult);
      }
      if (url.endsWith('/api/v1/judge-runs/judge-1')) {
        return jsonResponse(judgeRunRecord('succeeded', 'real'));
      }
      throw new Error(`URL inesperada: ${method} ${url}`);
    });
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={['/evaluation?run=run-1']}>
        <Evaluation />
      </MemoryRouter>,
    );

    await user.click(
      await screen.findByRole('radio', { name: /LLM as judge — inferência externa autorizada/ }),
    );
    const realButton = screen.getByRole('button', { name: 'Executar LLM as judge' });
    expect(realButton).toBeDisabled();
    await user.click(screen.getByLabelText(/Autorizo o envio do parecer congelado/));
    expect(realButton).toBeEnabled();
    await user.click(realButton);

    expect(await screen.findByText('Auditoria real concluída.')).toBeInTheDocument();
    expect(
      screen.getAllByText('LLM as judge — inferência externa autorizada'),
    ).toHaveLength(2);
    const submission = fetchMock.mock.calls.find(
      ([input, init]) =>
        String(input).endsWith('/api/v1/judge-runs') && init?.method === 'POST',
    );
    expect(JSON.parse(String(submission?.[1]?.body))).toEqual({
      source_run_id: 'run-1',
      mode: 'real',
      confirm_external_processing: true,
    });
  });
});
