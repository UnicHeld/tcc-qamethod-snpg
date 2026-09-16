import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import Search from './Search';

const documentRecord = {
  id: '11111111-1111-4111-8111-111111111111',
  file_name: 'dissertacao.pdf',
  sha256: 'a'.repeat(64),
  page_count: 3,
  character_count: 120,
  created_at: '2026-09-15T12:00:00Z',
};

const capabilitiesResponse = {
  default_mode: 'demo',
  max_upload_bytes: 20 * 1024 * 1024,
  max_pages: 300,
  capabilities: [],
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

function jsonResponse(payload: object, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('Search', () => {
  it('consulta um documento e exibe evidência lexical com página', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/api/v1/documents')) {
        return jsonResponse({ documents: [documentRecord] });
      }
      if (url.endsWith('/capabilities')) {
        return jsonResponse(capabilitiesResponse);
      }
      if (url.endsWith('/api/v1/search') && init?.method === 'POST') {
        return jsonResponse({
          document_id: documentRecord.id,
          query: 'metodologia',
          retrieval_mode: 'lexical',
          embedding_model: null,
          embedding_dimension: null,
          chunk_version: null,
          hits: [
            {
              unit_id: `${documentRecord.sha256}:page:2`,
              page: 2,
              snippet: 'A metodologia utiliza um protocolo verificável.',
              score: 0.5,
            },
          ],
        });
      }
      throw new Error(`URL inesperada: ${url}`);
    });
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={['/search']}>
        <Search />
      </MemoryRouter>,
    );

    expect(await screen.findByRole('option', { name: /dissertacao\.pdf/ })).toBeInTheDocument();
    await user.type(screen.getByLabelText('O que deseja encontrar?'), '  metodologia  ');
    await user.click(screen.getByRole('button', { name: 'Buscar no modo lexical' }));

    expect(await screen.findByRole('heading', { name: 'Página 2' })).toBeInTheDocument();
    expect(screen.getByText(/protocolo verificável/)).toBeInTheDocument();
    expect(screen.getByText('Modo lexical · sem geração')).toBeInTheDocument();
    const request = fetchMock.mock.calls.find(([input]) => String(input).endsWith('/api/v1/search'));
    expect(request).toBeDefined();
    expect(JSON.parse(String(request?.[1]?.body))).toEqual({
      document_id: documentRecord.id,
      query: 'metodologia',
      limit: 10,
      retrieval_mode: 'lexical',
    });
  });

  it('orienta o usuário quando ainda não há documento persistido', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) =>
      String(input).endsWith('/capabilities')
        ? jsonResponse(capabilitiesResponse)
        : jsonResponse({ documents: [] }),
    );

    render(
      <MemoryRouter initialEntries={['/search']}>
        <Search />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Nenhum documento disponível.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ir para avaliação' })).toHaveAttribute(
      'href',
      '/evaluation',
    );
  });

  it('apresenta estado vazio quando a consulta não encontra evidências', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/api/v1/documents')) {
        return jsonResponse({ documents: [documentRecord] });
      }
      if (url.endsWith('/capabilities')) {
        return jsonResponse(capabilitiesResponse);
      }
      return jsonResponse({
        document_id: documentRecord.id,
        query: 'expressão ausente',
        retrieval_mode: 'lexical',
        embedding_model: null,
        embedding_dimension: null,
        chunk_version: null,
        hits: [],
      });
    });
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={['/search']}>
        <Search />
      </MemoryRouter>,
    );

    await screen.findByRole('option', { name: /dissertacao\.pdf/ });
    await user.type(screen.getByLabelText('O que deseja encontrar?'), 'expressão ausente');
    await user.click(screen.getByRole('button', { name: 'Buscar no modo lexical' }));

    expect(await screen.findByText(/Nenhuma unidade deste documento/)).toBeInTheDocument();
    expect(screen.getByText('0 resultado(s)')).toBeInTheDocument();
  });

  it('apresenta falha da busca sem publicar resultado parcial', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/api/v1/documents')) {
        return jsonResponse({ documents: [documentRecord] });
      }
      if (url.endsWith('/capabilities')) {
        return jsonResponse(capabilitiesResponse);
      }
      return jsonResponse(
        { detail: { code: 'database_unavailable', message: 'A busca no banco falhou.' } },
        503,
      );
    });
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={['/search']}>
        <Search />
      </MemoryRouter>,
    );

    await screen.findByRole('option', { name: /dissertacao\.pdf/ });
    await user.type(screen.getByLabelText('O que deseja encontrar?'), 'metodologia');
    await user.click(screen.getByRole('button', { name: 'Buscar no modo lexical' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('A busca no banco falhou.');
    expect(screen.queryByRole('heading', { name: /Evidências para/ })).not.toBeInTheDocument();
  });

  it('mantém resultados lexical e vetorial para comparação', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/api/v1/documents')) {
        return jsonResponse({ documents: [documentRecord] });
      }
      if (url.endsWith('/capabilities')) {
        return jsonResponse(capabilitiesResponse);
      }
      const body = JSON.parse(String(init?.body)) as { retrieval_mode: 'lexical' | 'vector' };
      return jsonResponse({
        document_id: documentRecord.id,
        query: 'abordagem interpretativa',
        retrieval_mode: body.retrieval_mode,
        embedding_model:
          body.retrieval_mode === 'vector' ? 'intfloat/multilingual-e5-small' : null,
        embedding_dimension: body.retrieval_mode === 'vector' ? 384 : null,
        chunk_version: body.retrieval_mode === 'vector' ? 'document-unit-v1' : null,
        hits: [
          {
            unit_id: `${documentRecord.sha256}:page:${body.retrieval_mode === 'vector' ? 2 : 1}`,
            page: body.retrieval_mode === 'vector' ? 2 : 1,
            snippet: `Resultado ${body.retrieval_mode}.`,
            score: body.retrieval_mode === 'vector' ? 0.82 : 0.4,
          },
        ],
      });
    });
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={['/search']}>
        <Search />
      </MemoryRouter>,
    );

    await screen.findByRole('option', { name: /dissertacao\.pdf/ });
    await user.type(screen.getByLabelText('O que deseja encontrar?'), 'abordagem interpretativa');
    await user.click(screen.getByRole('button', { name: 'Buscar no modo lexical' }));
    await screen.findByText('Resultado lexical.');
    await user.click(screen.getByRole('radio', { name: /Vetorial local/ }));
    await user.click(screen.getByRole('button', { name: 'Buscar no modo vetorial' }));

    expect(await screen.findByText('Resultado vector.')).toBeInTheDocument();
    expect(screen.getByText('Resultado lexical.')).toBeInTheDocument();
    expect(screen.getAllByText(/intfloat\/multilingual-e5-small/)).toHaveLength(2);
  });

  it('não oferece o modo vetorial quando o perfil opt-in está desabilitado', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/api/v1/documents')) {
        return jsonResponse({ documents: [documentRecord] });
      }
      if (url.endsWith('/capabilities')) {
        return jsonResponse({
          ...capabilitiesResponse,
          retrieval_capabilities: capabilitiesResponse.retrieval_capabilities.map((capability) =>
            capability.mode === 'vector'
              ? {
                  ...capability,
                  available: false,
                  reason: 'Ative o perfil vetorial local e configure o PostgreSQL com pgvector.',
                }
              : capability,
          ),
        });
      }
      throw new Error(`URL inesperada: ${url}`);
    });

    render(
      <MemoryRouter initialEntries={['/search']}>
        <Search />
      </MemoryRouter>,
    );

    await screen.findByRole('option', { name: /dissertacao\.pdf/ });
    expect(await screen.findByRole('radio', { name: /Vetorial local/ })).toBeDisabled();
    expect(screen.getByText(/Ative o perfil vetorial local/)).toBeInTheDocument();
  });
});
