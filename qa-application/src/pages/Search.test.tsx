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
      if (url.endsWith('/api/v1/search') && init?.method === 'POST') {
        return jsonResponse({
          document_id: documentRecord.id,
          query: 'metodologia',
          retrieval_mode: 'lexical',
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
    await user.click(screen.getByRole('button', { name: 'Buscar evidências' }));

    expect(await screen.findByRole('heading', { name: 'Página 2' })).toBeInTheDocument();
    expect(screen.getByText(/protocolo verificável/)).toBeInTheDocument();
    expect(screen.getByText('Modo lexical · sem geração')).toBeInTheDocument();
    const request = fetchMock.mock.calls.find(([input]) => String(input).endsWith('/api/v1/search'));
    expect(request).toBeDefined();
    expect(JSON.parse(String(request?.[1]?.body))).toEqual({
      document_id: documentRecord.id,
      query: 'metodologia',
      limit: 10,
    });
  });

  it('orienta o usuário quando ainda não há documento persistido', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      jsonResponse({ documents: [] }),
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
      return jsonResponse({
        document_id: documentRecord.id,
        query: 'expressão ausente',
        retrieval_mode: 'lexical',
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
    await user.click(screen.getByRole('button', { name: 'Buscar evidências' }));

    expect(await screen.findByText(/Nenhuma unidade deste documento/)).toBeInTheDocument();
    expect(screen.getByText('0 resultado(s)')).toBeInTheDocument();
  });

  it('apresenta falha da busca sem publicar resultado parcial', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/api/v1/documents')) {
        return jsonResponse({ documents: [documentRecord] });
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
    await user.click(screen.getByRole('button', { name: 'Buscar evidências' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('A busca no banco falhou.');
    expect(screen.queryByRole('heading', { name: /Evidências para/ })).not.toBeInTheDocument();
  });
});
