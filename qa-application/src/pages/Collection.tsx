import { FormEvent, useEffect, useRef, useState } from 'react';

import Footer from '../components/Footer';
import Navbar from '../components/Navbar';
import {
  AcademicDocumentType,
  AcademicMetadata,
  CatalogApiError,
  CatalogEntry,
  CatalogEvidence,
  CatalogFilters,
  CatalogListResponse,
  CatalogSearchHit,
  CatalogSearchResponse,
  DocumentRecord,
  createDocument,
  getCatalogEntry,
  getCatalogEvidence,
  listCatalog,
  listDocuments,
  saveCatalogEntry,
  searchCatalog,
} from '../lib/api';

const inputClass = 'mt-1 w-full rounded-lg border border-stone-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-700';
const buttonClass = 'rounded-lg bg-red-800 px-4 py-2 font-semibold text-white hover:bg-red-900 focus:outline-none focus:ring-2 focus:ring-red-700 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-stone-400';
const secondaryClass = 'rounded-lg border border-stone-400 px-3 py-2 font-semibold focus:outline-none focus:ring-2 focus:ring-red-700 disabled:opacity-50';
const textFields = [
  ['institution', 'Instituição'], ['program', 'Programa de pós-graduação'], ['area', 'Área'],
  ['author', 'Autor'], ['advisor', 'Orientador'], ['coadvisor', 'Coorientador'],
] as const;
type TextField = typeof textFields[number][0];
type MetadataForm = Record<keyof AcademicMetadata, string>;
type FilterForm = Record<TextField | 'document_type' | 'year_from' | 'year_to', string>;
const emptyMetadata: MetadataForm = {
  title: '', document_type: '', publication_year: '', institution: '', program: '', area: '',
  author: '', advisor: '', coadvisor: '', source_url: '',
};
const emptyFilters: FilterForm = {
  document_type: '', year_from: '', year_to: '', institution: '', program: '', area: '',
  author: '', advisor: '', coadvisor: '',
};

function message(error: unknown): string {
  return error instanceof Error ? error.message : 'Não foi possível concluir a operação.';
}

function aborted(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}

function metadataForm(metadata: AcademicMetadata): MetadataForm {
  return Object.fromEntries(
    Object.entries(metadata).map(([key, value]) => [key, value === null ? '' : String(value)]),
  ) as MetadataForm;
}

function metadataPayload(form: MetadataForm): AcademicMetadata {
  const optional = (value: string) => value.trim() || null;
  return {
    title: form.title.trim(),
    document_type: (form.document_type || null) as AcademicDocumentType | null,
    publication_year: form.publication_year ? Number(form.publication_year) : null,
    institution: optional(form.institution), program: optional(form.program), area: optional(form.area),
    author: optional(form.author), advisor: optional(form.advisor), coadvisor: optional(form.coadvisor),
    source_url: optional(form.source_url),
  };
}

function filterPayload(form: FilterForm): CatalogFilters {
  return Object.fromEntries(
    Object.entries(form)
      .filter(([, value]) => value.trim() !== '')
      .map(([key, value]) => [key, key.startsWith('year_') ? Number(value) : value.trim()]),
  ) as CatalogFilters;
}

function DocumentTypeOptions() {
  return <><option value="">Não informado</option><option value="thesis">Tese</option><option value="dissertation">Dissertação</option><option value="other">Outro</option></>;
}

function SourceIdentity({ entry }: { entry: CatalogEntry }) {
  return (
    <div className="mt-2 space-y-1 text-sm text-stone-600">
      <p>{[entry.metadata.author, entry.metadata.institution, entry.metadata.program, entry.metadata.publication_year].filter(Boolean).join(' · ') || 'Metadados acadêmicos ainda incompletos.'}</p>
      <p>Metadados informados manualmente · revisão {entry.metadata_revision}</p>
      <p className="break-all text-xs">Arquivo: {entry.document.file_name} · SHA256: {entry.document.sha256}</p>
    </div>
  );
}

function Pagination({ offset, limit, total, loading, label, onChange }: {
  offset: number; limit: number; total: number; loading: boolean; label: string;
  onChange: (offset: number) => void;
}) {
  const first = offset < total ? offset + 1 : 0;
  const last = first ? Math.min(offset + limit, total) : 0;
  return (
    <nav aria-label={label} className="mt-4 flex flex-wrap items-center gap-3">
      <button className={secondaryClass} disabled={loading || offset === 0} onClick={() => onChange(Math.max(0, offset - limit))} type="button">Anterior</button>
      <span className="text-sm">{first}–{last} de {total}</span>
      <button className={secondaryClass} disabled={loading || offset + limit >= total} onClick={() => onChange(offset + limit)} type="button">Próxima</button>
    </nav>
  );
}

export default function Collection() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [documentId, setDocumentId] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [metadata, setMetadata] = useState<MetadataForm>(emptyMetadata);
  const [revision, setRevision] = useState(0);
  const [loadingEditor, setLoadingEditor] = useState(false);
  const [saving, setSaving] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [editorRefresh, setEditorRefresh] = useState(0);
  const [editorReady, setEditorReady] = useState(false);
  const [editorError, setEditorError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterForm>(emptyFilters);
  const [appliedFilters, setAppliedFilters] = useState<CatalogFilters>({});
  const [query, setQuery] = useState('');
  const [activeQuery, setActiveQuery] = useState<string | null>(null);
  const [listing, setListing] = useState<CatalogListResponse | null>(null);
  const [listOffset, setListOffset] = useState(0);
  const [listRefresh, setListRefresh] = useState(0);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [results, setResults] = useState<CatalogSearchResponse | null>(null);
  const [searchOffset, setSearchOffset] = useState(0);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<CatalogEvidence | null>(null);
  const [loadingEvidence, setLoadingEvidence] = useState(false);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);
  const evidenceRequest = useRef<AbortController | null>(null);
  const evidenceSection = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    listDocuments(controller.signal).then((items) => {
      if (controller.signal.aborted) return;
      setDocuments((current) => {
        const knownIds = new Set(current.map((item) => item.id));
        return [...current, ...items.filter((item) => !knownIds.has(item.id))];
      });
    }).catch((error: unknown) => {
      if (!controller.signal.aborted && !aborted(error)) setEditorError('Não foi possível carregar os PDFs já admitidos. Você ainda pode enviar um PDF.');
    });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    listCatalog(appliedFilters, listOffset, 20, controller.signal)
      .then((response) => { if (!controller.signal.aborted) setListing(response); })
      .catch((error: unknown) => { if (!controller.signal.aborted && !aborted(error)) { setListing(null); setListError(message(error)); } })
      .finally(() => { if (!controller.signal.aborted) setLoadingList(false); });
    return () => controller.abort();
  }, [appliedFilters, listOffset, listRefresh]);

  useEffect(() => {
    if (!documentId) return;
    const controller = new AbortController();
    getCatalogEntry(documentId, controller.signal)
      .then((entry) => {
        if (controller.signal.aborted) return;
        setMetadata(entry ? metadataForm(entry.metadata) : emptyMetadata);
        setRevision(entry?.metadata_revision ?? 0);
        setEditorReady(true);
      })
      .catch((error: unknown) => { if (!controller.signal.aborted && !aborted(error)) setEditorError(message(error)); })
      .finally(() => { if (!controller.signal.aborted) setLoadingEditor(false); });
    return () => controller.abort();
  }, [documentId, editorRefresh]);

  useEffect(() => {
    if (!activeQuery) return;
    const controller = new AbortController();
    searchCatalog(activeQuery, appliedFilters, searchOffset, 10, controller.signal)
      .then((response) => { if (!controller.signal.aborted) setResults(response); })
      .catch((error: unknown) => { if (!controller.signal.aborted && !aborted(error)) setSearchError(message(error)); })
      .finally(() => { if (!controller.signal.aborted) setSearching(false); });
    return () => controller.abort();
  }, [activeQuery, appliedFilters, searchOffset, listRefresh]);

  useEffect(() => () => evidenceRequest.current?.abort(), []);

  useEffect(() => {
    if (evidence || evidenceError) evidenceSection.current?.focus();
  }, [evidence, evidenceError]);

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    setUploading(true); setEditorError(null); setNotice(null);
    try {
      const document = await createDocument(file);
      setDocuments((current) => [document, ...current.filter((item) => item.id !== document.id)]);
      prepareEditor(document.id);
      setNotice('PDF admitido. Informe os metadados para incluí-lo no acervo.');
    } catch (error: unknown) { setEditorError(message(error)); }
    finally { setUploading(false); }
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!documentId || !editorReady || conflict) return;
    setSaving(true); setEditorError(null); setNotice(null);
    try {
      const entry = await saveCatalogEntry(documentId, metadataPayload(metadata), revision);
      setMetadata(metadataForm(entry.metadata)); setRevision(entry.metadata_revision);
      setLoadingList(true); setListError(null); setListOffset(0);
      if (activeQuery) { setSearching(true); setSearchError(null); setResults(null); }
      setListRefresh((current) => current + 1);
      setNotice('Metadados salvos no acervo.');
    } catch (error: unknown) {
      if (error instanceof CatalogApiError && error.status === 409) setConflict(true);
      setEditorError(message(error));
    } finally { setSaving(false); }
  }

  function consult(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (filters.year_from && filters.year_to && Number(filters.year_from) > Number(filters.year_to)) {
      setSearchError('O ano inicial não pode ser maior que o ano final.'); return;
    }
    evidenceRequest.current?.abort();
    setEvidence(null); setEvidenceError(null); setLoadingEvidence(false);
    setResults(null); setSearchError(null); setListOffset(0); setSearchOffset(0);
    setLoadingList(true); setListError(null); setSearching(Boolean(query.trim()));
    setAppliedFilters(filterPayload(filters)); setActiveQuery(query.trim() || null);
  }

  async function openEvidence(hit: CatalogSearchHit) {
    evidenceRequest.current?.abort();
    const controller = new AbortController(); evidenceRequest.current = controller;
    setLoadingEvidence(true); setEvidence(null); setEvidenceError(null);
    try {
      const response = await getCatalogEvidence(hit.entry.document.id, hit.unit_id, controller.signal);
      if (controller.signal.aborted) return;
      if (response.entry.document.id !== hit.entry.document.id || response.unit_id !== hit.unit_id || response.entry.document.sha256 !== hit.entry.document.sha256 || response.page !== hit.page) {
        throw new Error('A evidência recebida não corresponde ao documento e à revisão selecionados.');
      }
      setEvidence(response);
      if (response.entry.metadata_revision !== hit.entry.metadata_revision) {
        setEvidenceError('Os metadados mudaram desde a busca. Abaixo estão os metadados atuais; o conteúdo corresponde à mesma revisão documental.');
      }
    } catch (error: unknown) { if (!aborted(error)) setEvidenceError(message(error)); }
    finally { if (!controller.signal.aborted) setLoadingEvidence(false); }
  }

  function prepareEditor(id: string) {
    setDocumentId(id); setLoadingEditor(Boolean(id)); setEditorReady(false);
    setEditorError(null); setConflict(false); setNotice(null);
    setEditorRefresh((current) => current + 1);
  }

  function changeListOffset(offset: number) {
    setLoadingList(true); setListError(null); setListOffset(offset);
  }

  function changeSearchOffset(offset: number) {
    setSearching(true); setSearchError(null); setResults(null); setSearchOffset(offset);
  }

  function selectEntry(entry: CatalogEntry) {
    setDocuments((current) => current.some((item) => item.id === entry.document.id) ? current : [entry.document, ...current]);
    prepareEditor(entry.document.id);
  }

  return (
    <div className="flex min-h-screen flex-col bg-stone-50 text-stone-950">
      <Navbar />
      <main className="mx-auto w-full max-w-6xl flex-1 space-y-8 px-4 py-10 sm:px-6">
        <header className="max-w-3xl">
          <p className="text-sm font-semibold uppercase tracking-widest text-red-800">Question Answering · Acervo local</p>
          <h1 className="mt-3 text-3xl font-bold sm:text-4xl">Explore teses e dissertações</h1>
          <p className="mt-4 leading-relaxed text-stone-600">Cadastre trabalhos e encontre evidências entre documentos com filtros acadêmicos. A busca lexical consulta o texto extraído e não gera respostas por IA.</p>
        </header>

        <section aria-labelledby="catalog-editor-title" className="rounded-2xl border border-stone-200 bg-white p-5 sm:p-7">
          <h2 className="text-xl font-bold" id="catalog-editor-title">Adicionar ou editar trabalho</h2>
          <p className="mt-2 text-sm text-stone-600">Envie somente PDFs digitais autorizados. O envio extrai o texto localmente; o trabalho entra no acervo após salvar os metadados.</p>
          <form className="mt-4 flex flex-wrap items-end gap-3" onSubmit={upload}>
            <label className="min-w-0 flex-1 text-sm font-semibold" htmlFor="catalog-file">PDF digital
              <input accept="application/pdf" className={inputClass} disabled={uploading || saving} id="catalog-file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} type="file" />
            </label>
            <button className={buttonClass} disabled={!file || uploading || saving} type="submit">{uploading ? 'Enviando…' : 'Enviar PDF'}</button>
          </form>
          <label className="mt-5 block text-sm font-semibold" htmlFor="catalog-document">PDF já admitido (recentes)
            <select className={inputClass} disabled={uploading || saving} id="catalog-document" onChange={(event) => prepareEditor(event.target.value)} value={documentId}>
              <option value="">Selecione um PDF para catalogar</option>
              {documents.map((document) => <option key={document.id} value={document.id}>{document.file_name}</option>)}
            </select>
          </label>
          {loadingEditor ? <p className="mt-4" role="status">Carregando metadados…</p> : null}
          {documentId && editorReady ? (
            <form className="mt-5 space-y-4" onSubmit={save}>
              <p className="text-sm text-stone-600">Origem dos metadados: cadastro manual · revisão {revision}. Campos opcionais vazios permanecem desconhecidos.</p>
              <fieldset disabled={saving || uploading || loadingEditor || conflict}>
                <legend className="sr-only">Metadados acadêmicos</legend>
                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="text-sm font-semibold sm:col-span-2" htmlFor="catalog-title">Título do trabalho
                    <input className={inputClass} id="catalog-title" maxLength={500} onChange={(event) => setMetadata({ ...metadata, title: event.target.value })} required value={metadata.title} />
                  </label>
                  <label className="text-sm font-semibold" htmlFor="catalog-type">Tipo de trabalho
                    <select className={inputClass} id="catalog-type" onChange={(event) => setMetadata({ ...metadata, document_type: event.target.value })} value={metadata.document_type}><DocumentTypeOptions /></select>
                  </label>
                  <label className="text-sm font-semibold" htmlFor="catalog-year">Ano de publicação
                    <input className={inputClass} id="catalog-year" max={2100} min={1600} onChange={(event) => setMetadata({ ...metadata, publication_year: event.target.value })} step={1} type="number" value={metadata.publication_year} />
                  </label>
                  {textFields.map(([key, label]) => <label className="text-sm font-semibold" htmlFor={`catalog-${key}`} key={key}>{label}<input className={inputClass} id={`catalog-${key}`} maxLength={300} onChange={(event) => setMetadata({ ...metadata, [key]: event.target.value })} value={metadata[key]} /></label>)}
                  <label className="text-sm font-semibold sm:col-span-2" htmlFor="catalog-source">URL de origem (opcional)
                    <input className={inputClass} id="catalog-source" maxLength={2000} onChange={(event) => setMetadata({ ...metadata, source_url: event.target.value })} pattern="https?://.*" type="url" value={metadata.source_url} />
                  </label>
                </div>
              </fieldset>
              <button className={buttonClass} disabled={saving || uploading || loadingEditor || conflict} type="submit">{saving ? 'Salvando…' : 'Salvar metadados'}</button>
            </form>
          ) : null}
          {editorError ? <p className="mt-4 rounded-lg bg-red-50 p-3 text-red-900" role="alert">{editorError}</p> : null}
          {conflict || (documentId && !editorReady && !loadingEditor) ? <button className={`${secondaryClass} mt-3`} onClick={() => prepareEditor(documentId)} type="button">Recarregar metadados atuais</button> : null}
          {notice ? <p className="mt-4 rounded-lg bg-green-50 p-3 text-green-900" role="status">{notice}</p> : null}
        </section>

        <section aria-labelledby="catalog-query-title" className="rounded-2xl border border-stone-200 bg-white p-5 sm:p-7">
          <h2 className="text-xl font-bold" id="catalog-query-title">Consultar acervo</h2>
          <form className="mt-4 space-y-4" onSubmit={consult}>
            <label className="block text-sm font-semibold" htmlFor="catalog-query">Assunto ou expressão no texto (opcional)
              <input className={inputClass} id="catalog-query" maxLength={200} onChange={(event) => setQuery(event.target.value)} placeholder="Ex.: gestão do conhecimento" type="search" value={query} />
            </label>
            <p className="text-sm text-stone-600">Sem assunto, liste os trabalhos pelos filtros. Os filtros textuais correspondem ao valor completo, sem diferenciar maiúsculas de minúsculas.</p>
            <div className="grid gap-4 sm:grid-cols-3">
              <label className="text-sm font-semibold" htmlFor="filter-type">Filtrar por tipo
                <select className={inputClass} id="filter-type" onChange={(event) => setFilters({ ...filters, document_type: event.target.value })} value={filters.document_type}><option value="">Todos</option><option value="thesis">Tese</option><option value="dissertation">Dissertação</option><option value="other">Outro</option></select>
              </label>
              <label className="text-sm font-semibold" htmlFor="filter-from">Ano inicial
                <input className={inputClass} id="filter-from" max={2100} min={1600} onChange={(event) => setFilters({ ...filters, year_from: event.target.value })} step={1} type="number" value={filters.year_from} />
              </label>
              <label className="text-sm font-semibold" htmlFor="filter-to">Ano final
                <input className={inputClass} id="filter-to" max={2100} min={1600} onChange={(event) => setFilters({ ...filters, year_to: event.target.value })} step={1} type="number" value={filters.year_to} />
              </label>
              {textFields.map(([key, label]) => <label className="text-sm font-semibold" htmlFor={`filter-${key}`} key={key}>Filtrar por {label.toLowerCase()}<input className={inputClass} id={`filter-${key}`} maxLength={300} onChange={(event) => setFilters({ ...filters, [key]: event.target.value })} value={filters[key]} /></label>)}
            </div>
            <button className={buttonClass} disabled={searching || loadingList} type="submit">Consultar acervo</button>
          </form>
          {searchError ? <p className="mt-4 rounded-lg bg-red-50 p-3 text-red-900" role="alert">{searchError}</p> : null}
        </section>

        <section aria-labelledby="catalog-list-title">
          <h2 className="text-2xl font-bold" id="catalog-list-title">Trabalhos catalogados</h2>
          {loadingList ? <p className="mt-4" role="status">Carregando acervo…</p> : null}
          {listError ? <p className="mt-4 text-red-900" role="alert">{listError}</p> : null}
          {listing && !loadingList ? <>
            <p className="mt-2 text-sm text-stone-600">{listing.total} trabalho(s) nos filtros aplicados. Esta coleção não representa automaticamente toda a produção de uma instituição.</p>
            {listing.entries.length === 0 ? <p className="mt-4 rounded-xl border bg-white p-5">Nenhum trabalho catalogado nos filtros atuais. Envie um PDF ou cadastre os metadados de um documento já admitido.</p> : <ul className="mt-4 space-y-4">{listing.entries.map((entry) => <li className="rounded-xl border border-stone-200 bg-white p-5" key={entry.document.id}><h3 className="text-lg font-bold">{entry.metadata.title}</h3><SourceIdentity entry={entry} /><button className={`${secondaryClass} mt-3`} disabled={saving || uploading} onClick={() => selectEntry(entry)} type="button">Editar metadados de {entry.metadata.title}</button></li>)}</ul>}
            <Pagination label="Páginas de trabalhos" limit={listing.limit} loading={loadingList} offset={listing.offset} onChange={changeListOffset} total={listing.total} />
          </> : null}
        </section>

        {activeQuery ? <section aria-labelledby="catalog-results-title">
          <h2 className="text-2xl font-bold" id="catalog-results-title">Evidências para “{activeQuery}”</h2>
          <p className="mt-2 text-sm text-stone-600">Busca lexical entre trabalhos · sem geração de resposta</p>
          {searching ? <p className="mt-4" role="status">Buscando evidências…</p> : null}
          {results ? <>
            <p className="mt-3">{results.total_hits} evidência(s) em {results.total_documents} trabalho(s) correspondentes.</p>
            {results.hits.length === 0 ? <p className="mt-4 rounded-xl border bg-white p-5">Nenhuma evidência corresponde ao assunto e aos filtros aplicados.</p> : <ol className="mt-4 space-y-4">{results.hits.map((hit) => <li className="rounded-xl border border-stone-200 bg-white p-5" key={`${hit.entry.document.id}-${hit.unit_id}`}><h3 className="font-bold">{hit.entry.metadata.title} · página {hit.page}</h3><SourceIdentity entry={hit.entry} /><p className="mt-3 whitespace-pre-wrap leading-relaxed">{hit.snippet}</p><p className="mt-3 break-all text-xs text-stone-500">Unidade: {hit.unit_id} · Relevância lexical: {hit.score.toFixed(3)}</p><button className={`${secondaryClass} mt-3`} onClick={() => { void openEvidence(hit); }} type="button">Abrir evidência de {hit.entry.metadata.title}, página {hit.page}</button></li>)}</ol>}
            <Pagination label="Páginas de evidências" limit={results.limit} loading={searching} offset={results.offset} onChange={changeSearchOffset} total={results.total_hits} />
          </> : null}
        </section> : null}

        {loadingEvidence || evidenceError || evidence ? <section aria-labelledby="catalog-evidence-title" ref={evidenceSection} tabIndex={-1} className="rounded-2xl border border-stone-300 bg-white p-5 sm:p-7">
          <h2 className="text-2xl font-bold" id="catalog-evidence-title">Evidência original extraída</h2>
          {loadingEvidence ? <p className="mt-4" role="status">Abrindo evidência…</p> : null}
          {evidenceError ? <p className="mt-4 text-red-900" role="alert">{evidenceError}</p> : null}
          {evidence ? <><h3 className="mt-4 font-bold">{evidence.entry.metadata.title} · página {evidence.page}</h3><SourceIdentity entry={evidence.entry} /><p className="mt-3 break-all text-xs text-stone-600">Unidade: {evidence.unit_id}</p><p className="mt-5 whitespace-pre-wrap leading-relaxed">{evidence.text}</p><p className="mt-4 text-sm text-stone-500">Texto da unidade extraída. Figuras, tabelas e páginas sem texto podem não estar representadas.</p></> : null}
        </section> : null}
      </main>
      <Footer />
    </div>
  );
}
