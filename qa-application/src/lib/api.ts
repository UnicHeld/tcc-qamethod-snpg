export type EvaluationMode = 'demo' | 'real';

export interface Capability {
  mode: EvaluationMode;
  label: string;
  available: boolean;
  reason: string | null;
  provider: string;
  model: string;
  requires_external_confirmation: boolean;
}

export interface CapabilitiesResponse {
  default_mode: EvaluationMode;
  max_upload_bytes: number;
  max_pages: number;
  capabilities: Capability[];
}

export interface DocumentRecord {
  id: string;
  file_name: string;
  sha256: string;
  page_count: number;
  character_count: number;
  created_at: string;
}

export type PageExtractionStatus = 'extracted' | 'ocr_candidate' | 'no_text';

export interface DocumentPageRecord {
  document_id: string;
  page: number;
  status: PageExtractionStatus;
  character_count: number;
  has_images: boolean;
}

export interface SearchHitRecord {
  unit_id: string;
  page: number;
  snippet: string;
  score: number;
}

export interface SearchResponse {
  document_id: string;
  query: string;
  retrieval_mode: 'lexical';
  hits: SearchHitRecord[];
}

export type RunStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'interrupted';

export interface RunRecord {
  id: string;
  document_id: string;
  mode: EvaluationMode;
  provider: string;
  model: string;
  prompt_version: string;
  status: RunStatus;
  usage_kind: 'simulated' | 'actual' | 'estimated' | 'unknown' | null;
  credential_slot: 'primary' | 'fallback' | null;
  input_tokens: number | null;
  output_tokens: number | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface EvaluationReport {
  revision_sha256: string;
  simulated: boolean;
  title: string;
  summary: string;
  dimensions: Array<{
    dimension:
      | 'originality'
      | 'relevance'
      | 'methodology'
      | 'writing'
      | 'structure'
      | 'interdisciplinarity';
    insufficient: boolean;
    score: number | null;
    justification: string;
    evidence_ids: string[];
  }>;
}

export interface RunResult {
  run_id: string;
  report: EvaluationReport;
  result_markdown: string;
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000').replace(
  /\/$/,
  '',
);

async function responseError(response: Response): Promise<Error> {
  try {
    const payload = (await response.json()) as {
      detail?: { code?: string; message?: string } | string;
    };
    if (typeof payload.detail === 'object' && payload.detail?.message) {
      return new Error(payload.detail.message);
    }
    if (typeof payload.detail === 'string') {
      return new Error(payload.detail);
    }
  } catch {
    // A resposta sem JSON usa a mensagem HTTP abaixo.
  }
  return new Error(`A API respondeu com HTTP ${response.status}.`);
}

export async function getCapabilities(signal?: AbortSignal): Promise<CapabilitiesResponse> {
  const response = await fetch(`${API_BASE_URL}/capabilities`, { signal });
  if (!response.ok) {
    throw await responseError(response);
  }
  return (await response.json()) as CapabilitiesResponse;
}

export async function createDocument(file: File): Promise<DocumentRecord> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/api/v1/documents`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    throw await responseError(response);
  }
  return (await response.json()) as DocumentRecord;
}

export async function listDocuments(signal?: AbortSignal): Promise<DocumentRecord[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/documents`, { signal });
  if (!response.ok) {
    throw await responseError(response);
  }
  const payload = (await response.json()) as { documents: DocumentRecord[] };
  return payload.documents;
}

export async function getDocument(
  documentId: string,
  signal?: AbortSignal,
): Promise<DocumentRecord> {
  const response = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}`, { signal });
  if (!response.ok) {
    throw await responseError(response);
  }
  return (await response.json()) as DocumentRecord;
}

export async function getDocumentPages(
  documentId: string,
  signal?: AbortSignal,
): Promise<DocumentPageRecord[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}/pages`, { signal });
  if (!response.ok) {
    throw await responseError(response);
  }
  const payload = (await response.json()) as { pages: DocumentPageRecord[] };
  return payload.pages;
}

export async function searchDocument(
  documentId: string,
  query: string,
  limit = 10,
  signal?: AbortSignal,
): Promise<SearchResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_id: documentId, query, limit }),
    signal,
  });
  if (!response.ok) {
    throw await responseError(response);
  }
  return (await response.json()) as SearchResponse;
}

export async function createRun(
  documentId: string,
  mode: EvaluationMode,
  confirmExternalProcessing: boolean,
  idempotencyKey: string,
): Promise<RunRecord> {
  const response = await fetch(`${API_BASE_URL}/api/v1/runs`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify({
      document_id: documentId,
      mode,
      confirm_external_processing: confirmExternalProcessing,
    }),
  });
  if (!response.ok) {
    throw await responseError(response);
  }
  return (await response.json()) as RunRecord;
}

export async function listRuns(signal?: AbortSignal): Promise<RunRecord[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/runs`, { signal });
  if (!response.ok) {
    throw await responseError(response);
  }
  const payload = (await response.json()) as { runs: RunRecord[] };
  return payload.runs;
}

export async function getRun(runId: string, signal?: AbortSignal): Promise<RunRecord> {
  const response = await fetch(`${API_BASE_URL}/api/v1/runs/${runId}`, { signal });
  if (!response.ok) {
    throw await responseError(response);
  }
  return (await response.json()) as RunRecord;
}

export async function getRunResult(runId: string, signal?: AbortSignal): Promise<RunResult> {
  const response = await fetch(`${API_BASE_URL}/api/v1/runs/${runId}/result`, { signal });
  if (!response.ok) {
    throw await responseError(response);
  }
  return (await response.json()) as RunResult;
}
