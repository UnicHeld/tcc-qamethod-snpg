import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import Insights from './Insights';

const documentRecord = {
  id: '11111111-1111-4111-8111-111111111111',
  file_name: 'dissertacao.pdf',
  sha256: 'a'.repeat(64),
  page_count: 3,
  character_count: 120,
  created_at: '2026-09-16T12:00:00Z',
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
  retrieval_capabilities: [
    {
      mode: 'lexical',
      label: 'Lexical',
      available: true,
      reason: null,
      model: 'postgresql-portuguese-fts',
      dimension: null,
    },
    {
      mode: 'vector',
      label: 'Vetorial local',
      available: true,
      reason: null,
      model: 'intfloat/multilingual-e5-small',
      dimension: 384,
    },
  ],
};

function insightRecord(status: 'queued' | 'succeeded' | 'failed') {
  return {
    id: '22222222-2222-4222-8222-222222222222',
    document_id: documentRecord.id,
    question: 'Qual metodologia foi utilizada?',
    retrieval_mode: 'lexical',
    retrieval_limit: 5,
    mode: 'demo',
    provider: 'local',
    model: 'deterministic-rag-demo-v1',
    prompt_version: 'rag-insight-v1',
    status,
    usage_kind: status === 'succeeded' ? 'simulated' : null,
    credential_slot: null,
    input_tokens: null,
    output_tokens: null,
    error_code: status === 'failed' ? 'insufficient_evidence' : null,
    error_message: status === 'failed' ? 'Nenhuma evidência foi recuperada.' : null,
    created_at: '2026-09-16T12:00:00Z',
    started_at: status === 'queued' ? null : '2026-09-16T12:00:01Z',
    finished_at: status === 'queued' ? null : '2026-09-16T12:00:02Z',
  };
}

const insightResult = {
  insight_id: '22222222-2222-4222-8222-222222222222',
  evidence_package: {
    document_id: documentRecord.id,
    revision_sha256: documentRecord.sha256,
    question: 'Qual metodologia foi utilizada?',
    retrieval_mode: 'lexical',
    embedding_model: null,
    embedding_dimension: null,
    chunk_version: null,
    items: [
      {
        id: 'E1',
        unit_id: `${documentRecord.sha256}:page:2`,
        page: 2,
        text: 'Foram realizadas entrevistas semiestruturadas.',
        score: 0.8,
      },
    ],
  },
  report: {
    revision_sha256: documentRecord.sha256,
    simulated: true,
    question: 'Qual metodologia foi utilizada?',
    answer: 'Resposta simulada baseada no pacote.',
    citation_ids: ['E1'],
  },
  result_markdown: '# Insight RAG\n',
};

function jsonResponse(payload: object, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

afterEach(() => {
  vi.restoreAllMocks();
  Reflect.deleteProperty(globalThis.navigator, 'clipboard');
});

describe('Insights', () => {
  it('cria, acompanha e apresenta resposta com evidência congelada', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      const method = init?.method ?? 'GET';
      if (url.endsWith('/api/v1/documents')) {
        return jsonResponse({ documents: [documentRecord] });
      }
      if (url.endsWith('/capabilities')) {
        return jsonResponse(capabilities);
      }
      if (url.endsWith('/api/v1/insights') && method === 'GET') {
        return jsonResponse({ insights: [] });
      }
      if (url.endsWith('/api/v1/insights') && method === 'POST') {
        return jsonResponse(insightRecord('queued'), 202);
      }
      if (url.endsWith('/api/v1/insights/22222222-2222-4222-8222-222222222222/result')) {
        return jsonResponse(insightResult);
      }
      if (url.endsWith('/api/v1/insights/22222222-2222-4222-8222-222222222222')) {
        return jsonResponse(insightRecord('succeeded'));
      }
      throw new Error(`URL inesperada: ${method} ${url}`);
    });
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(globalThis.navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    });

    render(
      <MemoryRouter initialEntries={['/insights']}>
        <Insights />
      </MemoryRouter>,
    );

    await screen.findByRole('option', { name: /dissertacao\.pdf/ });
    await user.type(screen.getByLabelText('Pergunta'), 'Qual metodologia foi utilizada?');
    await user.click(screen.getByRole('button', { name: 'Gerar insight' }));

    expect(await screen.findByText('Resposta simulada baseada no pacote.')).toBeInTheDocument();
    expect(screen.getByText('E1 · página 2')).toBeInTheDocument();
    expect(screen.getByText(/entrevistas semiestruturadas/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Markdown/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /JSON/ })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Copiar origem' }));
    expect(writeText).toHaveBeenCalledWith(`${documentRecord.sha256}:page:2`);
    expect(screen.getByRole('button', { name: 'Origem copiada' })).toBeInTheDocument();
    expect(screen.getByText('Origem E1 copiada.')).toHaveClass('sr-only');

    const request = fetchMock.mock.calls.find(
      ([input, init]) => String(input).endsWith('/api/v1/insights') && init?.method === 'POST',
    );
    expect(JSON.parse(String(request?.[1]?.body))).toEqual({
      document_id: documentRecord.id,
      question: 'Qual metodologia foi utilizada?',
      retrieval_mode: 'lexical',
      retrieval_limit: 5,
      mode: 'demo',
      confirm_external_processing: false,
    });
  });

  it('orienta quando ainda não há documento persistido', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/api/v1/documents')) {
        return jsonResponse({ documents: [] });
      }
      if (url.endsWith('/capabilities')) {
        return jsonResponse(capabilities);
      }
      return jsonResponse({ insights: [] });
    });

    render(
      <MemoryRouter initialEntries={['/insights']}>
        <Insights />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Nenhum documento disponível')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ir para avaliação' })).toHaveAttribute(
      'href',
      '/evaluation',
    );
  });

  it('mantém o perfil vetorial desabilitado quando a capability não está ativa', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/api/v1/documents')) {
        return jsonResponse({ documents: [documentRecord] });
      }
      if (url.endsWith('/capabilities')) {
        return jsonResponse({
          ...capabilities,
          retrieval_capabilities: capabilities.retrieval_capabilities.map((item) =>
            item.mode === 'vector'
              ? { ...item, available: false, reason: 'Ative o perfil vetorial local.' }
              : item,
          ),
        });
      }
      return jsonResponse({ insights: [] });
    });

    render(
      <MemoryRouter initialEntries={['/insights']}>
        <Insights />
      </MemoryRouter>,
    );

    await screen.findByRole('option', { name: /dissertacao\.pdf/ });
    expect(screen.getByRole('radio', { name: /Vetorial local/ })).toBeDisabled();
    expect(screen.getByText('Ative o perfil vetorial local.')).toBeInTheDocument();
  });

  it('reabre um insight falho sem publicar resposta parcial', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/api/v1/documents')) {
        return jsonResponse({ documents: [documentRecord] });
      }
      if (url.endsWith('/capabilities')) {
        return jsonResponse(capabilities);
      }
      if (url.endsWith('/api/v1/insights')) {
        return jsonResponse({ insights: [insightRecord('failed')] });
      }
      if (url.endsWith('/api/v1/insights/22222222-2222-4222-8222-222222222222')) {
        return jsonResponse(insightRecord('failed'));
      }
      throw new Error(`URL inesperada: ${url}`);
    });
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={['/insights']}>
        <Insights />
      </MemoryRouter>,
    );

    await user.click(await screen.findByRole('button', { name: /Qual metodologia/ }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Nenhuma evidência foi recuperada.');
    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: 'Evidências citadas' })).not.toBeInTheDocument();
    });
  });
});
