import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AcademicMetadata, CatalogEntry, DocumentRecord } from '../lib/api';
import Collection from './Collection';

const document: DocumentRecord = {
  id: '11111111-1111-4111-8111-111111111111', file_name: 'trabalho.pdf',
  sha256: 'a'.repeat(64), page_count: 3, character_count: 180,
  created_at: '2026-11-21T12:00:00Z',
};
const metadata: AcademicMetadata = {
  title: 'Gestão do conhecimento', document_type: 'dissertation', publication_year: 2024,
  institution: 'UFSC', program: 'PPGEGC', area: 'Gestão', author: 'Ana', advisor: 'Maria',
  coadvisor: null, source_url: null,
};
const entry: CatalogEntry = {
  document, metadata, metadata_revision: 1, metadata_source: 'manual',
  updated_at: '2026-11-21T12:00:00Z',
};
const secondEntry: CatalogEntry = {
  ...entry,
  document: { ...document, id: '22222222-2222-4222-8222-222222222222', sha256: 'b'.repeat(64), file_name: 'tese.pdf' },
  metadata: { ...metadata, title: 'Redes de pesquisa', document_type: 'thesis' },
};

function json(payload: object, status = 200): Response {
  return new Response(JSON.stringify(payload), { status, headers: { 'Content-Type': 'application/json' } });
}

function list(entries: CatalogEntry[], offset = 0, total = entries.length) {
  return { entries, total, limit: 20, offset };
}

function renderCollection() {
  return render(<MemoryRouter><Collection /></MemoryRouter>);
}

afterEach(() => vi.restoreAllMocks());

describe('Collection', () => {
  it('preserva o PDF recém-enviado quando a listagem inicial responde depois do upload', async () => {
    let resolveInitial!: (response: Response) => void;
    const initialDocuments = new Promise<Response>((resolve) => { resolveInitial = resolve; });
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = new URL(String(input));
      if (url.pathname === '/api/v1/documents' && init?.method === 'POST') return json(document, 201);
      if (url.pathname === '/api/v1/documents') return initialDocuments;
      if (url.pathname === '/api/v1/catalog/documents') return json(list([]));
      if (url.pathname === `/api/v1/catalog/documents/${document.id}`) {
        return json({ detail: { code: 'catalog_entry_not_found', message: 'Ainda não catalogado.' } }, 404);
      }
      throw new Error(`URL inesperada: ${url}`);
    });
    const user = userEvent.setup();
    renderCollection();
    await screen.findByText(/Nenhum trabalho catalogado nos filtros atuais/);
    await user.upload(screen.getByLabelText('PDF digital'), new File(['%PDF'], 'trabalho.pdf', { type: 'application/pdf' }));
    await user.click(screen.getByRole('button', { name: 'Enviar PDF' }));
    await user.type(await screen.findByLabelText('Título do trabalho'), 'Título em edição');

    await act(async () => {
      resolveInitial(json({ documents: [secondEntry.document, document] }));
    });

    const selector = screen.getByLabelText('PDF já admitido (recentes)');
    expect(within(selector).getByRole('option', { name: 'tese.pdf' })).toBeInTheDocument();
    expect(within(selector).getAllByRole('option', { name: 'trabalho.pdf' })).toHaveLength(1);
    expect(selector).toHaveValue(document.id);
    expect(screen.getByLabelText('Título do trabalho')).toHaveValue('Título em edição');
  });

  it('admite PDF e cadastra metadados sem criar avaliação nem chamar provedor', async () => {
    let saved: CatalogEntry | null = null;
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = new URL(String(input));
      if (url.pathname === '/api/v1/documents' && init?.method === 'POST') return json(document, 201);
      if (url.pathname === '/api/v1/documents') return json({ documents: [] });
      if (url.pathname === '/api/v1/catalog/documents') return json(list(saved ? [saved] : []));
      if (url.pathname === `/api/v1/catalog/documents/${document.id}` && init?.method === 'PUT') {
        const body = JSON.parse(String(init.body)) as { metadata: AcademicMetadata };
        saved = { ...entry, metadata: body.metadata };
        return json(saved);
      }
      if (url.pathname === `/api/v1/catalog/documents/${document.id}`) {
        return saved ? json(saved) : json({ detail: { code: 'catalog_entry_not_found', message: 'Ainda não catalogado.' } }, 404);
      }
      throw new Error(`URL inesperada: ${url}`);
    });
    const user = userEvent.setup();
    renderCollection();
    await screen.findByText(/Nenhum trabalho catalogado nos filtros atuais/);
    await user.upload(screen.getByLabelText('PDF digital'), new File(['%PDF'], 'trabalho.pdf', { type: 'application/pdf' }));
    await user.click(screen.getByRole('button', { name: 'Enviar PDF' }));
    const title = await screen.findByLabelText('Título do trabalho');
    expect(title).toHaveValue('');
    await user.type(title, metadata.title);
    await user.selectOptions(screen.getByLabelText('Tipo de trabalho'), 'dissertation');
    await user.type(screen.getByLabelText('Ano de publicação'), '2024');
    await user.type(screen.getByLabelText('Instituição', { exact: true }), 'UFSC');
    await user.click(screen.getByRole('button', { name: 'Salvar metadados' }));
    expect(await screen.findByText('Metadados salvos no acervo.')).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: metadata.title })).toBeInTheDocument();
    const request = fetchMock.mock.calls.find(([, init]) => init?.method === 'PUT');
    expect(JSON.parse(String(request?.[1]?.body))).toEqual({
      metadata: { ...metadata, program: null, area: null, author: null, advisor: null },
      expected_revision: 0,
    });
    expect(fetchMock.mock.calls.some(([input]) => /\/runs|\/evaluation|\/insights|gemini/.test(String(input)))).toBe(false);
  });

  it('reabre trabalho catalogado e atualiza com a revisão exibida', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = new URL(String(input));
      if (url.pathname === '/api/v1/documents') return json({ documents: [] });
      if (url.pathname === '/api/v1/catalog/documents') return json(list([entry]));
      if (init?.method === 'PUT') return json({ ...entry, metadata_revision: 2, metadata: { ...metadata, title: 'Título revisado' } });
      return json(entry);
    });
    const user = userEvent.setup();
    renderCollection();
    await user.click(await screen.findByRole('button', { name: `Editar metadados de ${metadata.title}` }));
    const title = await screen.findByLabelText('Título do trabalho');
    expect(title).toHaveValue(metadata.title);
    await user.clear(title); await user.type(title, 'Título revisado');
    await user.click(screen.getByRole('button', { name: 'Salvar metadados' }));
    await screen.findByText('Metadados salvos no acervo.');
    const update = fetchMock.mock.calls.find(([, init]) => init?.method === 'PUT');
    expect(JSON.parse(String(update?.[1]?.body))).toMatchObject({ expected_revision: 1, metadata: { title: 'Título revisado' } });
    expect(screen.getByText(/Origem dos metadados: cadastro manual · revisão 2/)).toBeInTheDocument();
  });

  it('consulta assunto com filtros entre trabalhos e abre somente a unidade selecionada', async () => {
    const hit = { entry: secondEntry, unit_id: `${secondEntry.document.sha256}:page:2`, page: 2, snippet: 'Trecho sobre conhecimento.', score: 0.7 };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = new URL(String(input));
      if (url.pathname === '/api/v1/documents') return json({ documents: [] });
      if (url.pathname === '/api/v1/catalog/documents') return json(list([entry, secondEntry]));
      if (url.pathname === '/api/v1/catalog/search') return json({ query: 'conhecimento', filters: {}, retrieval_mode: 'lexical', hits: [
        { ...hit, entry, unit_id: `${document.sha256}:page:1`, page: 1 }, hit,
      ], total_hits: 2, total_documents: 2, limit: 10, offset: 0 });
      if (url.pathname.includes('/evidence/')) return json({ entry: secondEntry, unit_id: hit.unit_id, page: 2, text: 'Texto integral verificável da segunda tese.' });
      throw new Error(`URL inesperada: ${url} ${init?.method}`);
    });
    const user = userEvent.setup();
    renderCollection();
    await screen.findByRole('heading', { name: metadata.title });
    await user.type(screen.getByLabelText('Assunto ou expressão no texto (opcional)'), ' conhecimento ');
    await user.type(screen.getByLabelText('Ano inicial'), '2020');
    await user.type(screen.getByLabelText('Ano final'), '2024');
    await user.type(screen.getByLabelText('Filtrar por área'), 'Gestão');
    await user.type(screen.getByLabelText('Filtrar por orientador'), 'Maria');
    await user.click(screen.getByRole('button', { name: 'Consultar acervo' }));
    expect(await screen.findByText('2 evidência(s) em 2 trabalho(s) correspondentes.')).toBeInTheDocument();
    const request = fetchMock.mock.calls.find(([input]) => String(input).endsWith('/catalog/search'));
    expect(JSON.parse(String(request?.[1]?.body))).toEqual({ query: 'conhecimento', filters: { year_from: 2020, year_to: 2024, area: 'Gestão', advisor: 'Maria' }, limit: 10, offset: 0 });
    await user.click(screen.getByRole('button', { name: 'Abrir evidência de Redes de pesquisa, página 2' }));
    expect(await screen.findByText('Texto integral verificável da segunda tese.')).toBeInTheDocument();
    const evidenceRequest = fetchMock.mock.calls.find(([input]) => String(input).includes('/evidence/'));
    expect(String(evidenceRequest?.[0])).toContain(`/catalog/documents/${secondEntry.document.id}/evidence/${encodeURIComponent(hit.unit_id)}`);
    expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith('/units'))).toBe(false);
    const filteredList = fetchMock.mock.calls.find(([input]) => String(input).includes('/catalog/documents?') && String(input).includes('year_from=2020'));
    expect(filteredList).toBeDefined();
  });

  it('pagina catálogo preservando filtros e totais', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = new URL(String(input));
      if (url.pathname === '/api/v1/documents') return json({ documents: [] });
      const offset = Number(url.searchParams.get('offset'));
      return json(list(offset ? [secondEntry] : [entry], offset, 21));
    });
    const user = userEvent.setup();
    renderCollection();
    await screen.findByRole('heading', { name: metadata.title });
    await user.type(screen.getByLabelText('Filtrar por instituição'), 'UFSC');
    await user.click(screen.getByRole('button', { name: 'Consultar acervo' }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Consultar acervo' })).toBeEnabled());
    await user.click(within(screen.getByRole('navigation', { name: 'Páginas de trabalhos' })).getByRole('button', { name: 'Próxima' }));
    expect(await screen.findByRole('heading', { name: 'Redes de pesquisa' })).toBeInTheDocument();
    expect(screen.getByText('21–21 de 21')).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes('offset=20') && String(input).includes('institution=UFSC'))).toBe(true);
  });

  it('bloqueia nova gravação após conflito até recarregar os metadados atuais', async () => {
    let getCount = 0;
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = new URL(String(input));
      if (url.pathname === '/api/v1/documents') return json({ documents: [document] });
      if (url.pathname === '/api/v1/catalog/documents') return json(list([entry]));
      if (init?.method === 'PUT') return json({ detail: { code: 'catalog_revision_conflict', message: 'Outra pessoa atualizou os metadados.' } }, 409);
      getCount += 1;
      return json(getCount === 1 ? entry : { ...entry, metadata_revision: 2, metadata: { ...metadata, title: 'Revisão de outra pessoa' } });
    });
    const user = userEvent.setup();
    renderCollection();
    await user.selectOptions(await screen.findByLabelText('PDF já admitido (recentes)'), document.id);
    await screen.findByLabelText('Título do trabalho');
    await user.click(screen.getByRole('button', { name: 'Salvar metadados' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Outra pessoa atualizou os metadados.');
    expect(screen.getByRole('button', { name: 'Salvar metadados' })).toBeDisabled();
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'PUT')).toHaveLength(1);
    await user.click(screen.getByRole('button', { name: 'Recarregar metadados atuais' }));
    await waitFor(() => expect(screen.getByLabelText('Título do trabalho')).toHaveValue('Revisão de outra pessoa'));
    expect(screen.getByRole('button', { name: 'Salvar metadados' })).toBeEnabled();
  });

  it('exibe consulta vazia e falha de busca sem resultado parcial', async () => {
    let fail = false;
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = new URL(String(input));
      if (url.pathname === '/api/v1/documents') return json({ documents: [] });
      if (url.pathname === '/api/v1/catalog/documents') return json(list([]));
      return fail
        ? json({ detail: { message: 'A busca no acervo falhou.' } }, 503)
        : json({ query: 'ausente', filters: {}, retrieval_mode: 'lexical', hits: [], total_hits: 0, total_documents: 0, limit: 10, offset: 0 });
    });
    const user = userEvent.setup();
    renderCollection();
    await screen.findByText(/Nenhum trabalho catalogado nos filtros atuais/);
    await user.type(screen.getByLabelText('Assunto ou expressão no texto (opcional)'), 'ausente');
    await user.click(screen.getByRole('button', { name: 'Consultar acervo' }));
    expect(await screen.findByText('Nenhuma evidência corresponde ao assunto e aos filtros aplicados.')).toBeInTheDocument();
    fail = true;
    await user.click(screen.getByRole('button', { name: 'Consultar acervo' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('A busca no acervo falhou.');
    expect(screen.queryByText('Nenhuma evidência corresponde ao assunto e aos filtros aplicados.')).not.toBeInTheDocument();
  });

  it('rejeita evidência de outro documento e valida intervalo de ano antes da consulta', async () => {
    const hit = { entry, unit_id: `${document.sha256}:page:1`, page: 1, snippet: 'Conhecimento.', score: 0.8 };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = new URL(String(input));
      if (url.pathname === '/api/v1/documents') return json({ documents: [] });
      if (url.pathname === '/api/v1/catalog/documents') return json(list([entry]));
      if (url.pathname.includes('/evidence/')) return json({ entry: secondEntry, unit_id: hit.unit_id, page: 1, text: 'Texto indevido.' });
      return json({ query: 'conhecimento', filters: {}, retrieval_mode: 'lexical', hits: [hit], total_hits: 1, total_documents: 1, limit: 10, offset: 0 });
    });
    const user = userEvent.setup();
    renderCollection();
    await screen.findByRole('heading', { name: metadata.title });
    await user.type(screen.getByLabelText('Ano inicial'), '2025');
    await user.type(screen.getByLabelText('Ano final'), '2024');
    await user.click(screen.getByRole('button', { name: 'Consultar acervo' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('O ano inicial não pode ser maior que o ano final.');
    expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith('/catalog/search'))).toBe(false);
    await user.clear(screen.getByLabelText('Ano inicial'));
    await user.type(screen.getByLabelText('Assunto ou expressão no texto (opcional)'), 'conhecimento');
    await user.click(screen.getByRole('button', { name: 'Consultar acervo' }));
    await user.click(await screen.findByRole('button', { name: `Abrir evidência de ${metadata.title}, página 1` }));
    expect(await screen.findByRole('alert')).toHaveTextContent('A evidência recebida não corresponde');
    expect(screen.queryByText('Texto indevido.')).not.toBeInTheDocument();
  });
});
