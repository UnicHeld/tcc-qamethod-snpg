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
  judge_capabilities: Capability[];
  retrieval_capabilities: RetrievalCapability[];
}

export type RetrievalMode = 'lexical' | 'vector';

export interface RetrievalCapability {
  mode: RetrievalMode;
  label: string;
  available: boolean;
  reason: string | null;
  model: string | null;
  dimension: number | null;
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
  retrieval_mode: RetrievalMode;
  embedding_model: string | null;
  embedding_dimension: number | null;
  chunk_version: string | null;
  hits: SearchHitRecord[];
}

export interface EvidenceItemRecord {
  id: string;
  unit_id: string;
  page: number;
  text: string;
  score: number;
}

export interface EvidencePackageRecord {
  document_id: string;
  revision_sha256: string;
  question: string;
  retrieval_mode: RetrievalMode;
  embedding_model: string | null;
  embedding_dimension: number | null;
  chunk_version: string | null;
  items: EvidenceItemRecord[];
}

export interface InsightReport {
  revision_sha256: string;
  simulated: boolean;
  question: string;
  answer: string;
  citation_ids: string[];
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

export interface InsightRunRecord {
  id: string;
  document_id: string;
  question: string;
  retrieval_mode: RetrievalMode;
  retrieval_limit: number;
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

export interface InsightResult {
  insight_id: string;
  evidence_package: EvidencePackageRecord;
  report: InsightReport;
  result_markdown: string;
}

export interface JudgeRunRecord {
  id: string;
  source_run_id: string;
  document_id: string;
  mode: EvaluationMode;
  provider: string;
  model: string;
  prompt_version: string;
  status: RunStatus;
  source_report_sha256: string;
  usage_kind: 'simulated' | 'actual' | 'unknown' | null;
  credential_slot: 'primary' | 'fallback' | null;
  input_tokens: number | null;
  output_tokens: number | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface JudgeFindingRecord {
  id: string;
  criterion: 'evidence_alignment' | 'internal_consistency' | 'rubric_conformance';
  severity: 'info' | 'warning' | 'error';
  dimension: EvaluationReport['dimensions'][number]['dimension'] | null;
  explanation: string;
  evidence_ids: string[];
}

export interface JudgeEvidencePackageRecord {
  document_id: string;
  revision_sha256: string;
  source_report_sha256: string;
  items: Array<{
    unit_id: string;
    page: number;
    text: string;
  }>;
}

export interface JudgeResult {
  judge_run_id: string;
  source_report: EvaluationReport;
  source_evidence: JudgeEvidencePackageRecord;
  report: {
    source_run_id: string;
    source_report_sha256: string;
    revision_sha256: string;
    simulated: boolean;
    verdict: 'pass' | 'needs_human_review';
    summary: string;
    findings: JudgeFindingRecord[];
  };
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
  retrievalMode: RetrievalMode = 'lexical',
  limit = 10,
  signal?: AbortSignal,
): Promise<SearchResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      document_id: documentId,
      query,
      limit,
      retrieval_mode: retrievalMode,
    }),
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

export async function createInsight(
  documentId: string,
  question: string,
  retrievalMode: RetrievalMode,
  retrievalLimit: number,
  mode: EvaluationMode,
  confirmExternalProcessing: boolean,
  idempotencyKey: string,
): Promise<InsightRunRecord> {
  const response = await fetch(`${API_BASE_URL}/api/v1/insights`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify({
      document_id: documentId,
      question,
      retrieval_mode: retrievalMode,
      retrieval_limit: retrievalLimit,
      mode,
      confirm_external_processing: confirmExternalProcessing,
    }),
  });
  if (!response.ok) {
    throw await responseError(response);
  }
  return (await response.json()) as InsightRunRecord;
}

export async function listInsights(signal?: AbortSignal): Promise<InsightRunRecord[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/insights`, { signal });
  if (!response.ok) {
    throw await responseError(response);
  }
  const payload = (await response.json()) as { insights: InsightRunRecord[] };
  return payload.insights;
}

export async function getInsight(
  insightId: string,
  signal?: AbortSignal,
): Promise<InsightRunRecord> {
  const response = await fetch(`${API_BASE_URL}/api/v1/insights/${insightId}`, { signal });
  if (!response.ok) {
    throw await responseError(response);
  }
  return (await response.json()) as InsightRunRecord;
}

export async function getInsightResult(
  insightId: string,
  signal?: AbortSignal,
): Promise<InsightResult> {
  const response = await fetch(`${API_BASE_URL}/api/v1/insights/${insightId}/result`, { signal });
  if (!response.ok) {
    throw await responseError(response);
  }
  return (await response.json()) as InsightResult;
}

export async function createJudgeRun(
  sourceRunId: string,
  mode: EvaluationMode,
  confirmExternalProcessing: boolean,
  idempotencyKey: string,
): Promise<JudgeRunRecord> {
  const response = await fetch(`${API_BASE_URL}/api/v1/judge-runs`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify({
      source_run_id: sourceRunId,
      mode,
      confirm_external_processing: confirmExternalProcessing,
    }),
  });
  if (!response.ok) {
    throw await responseError(response);
  }
  return (await response.json()) as JudgeRunRecord;
}

export async function getJudgeRun(
  judgeRunId: string,
  signal?: AbortSignal,
): Promise<JudgeRunRecord> {
  const response = await fetch(`${API_BASE_URL}/api/v1/judge-runs/${judgeRunId}`, { signal });
  if (!response.ok) {
    throw await responseError(response);
  }
  return (await response.json()) as JudgeRunRecord;
}

export async function getJudgeResult(
  judgeRunId: string,
  signal?: AbortSignal,
): Promise<JudgeResult> {
  const response = await fetch(`${API_BASE_URL}/api/v1/judge-runs/${judgeRunId}/result`, {
    signal,
  });
  if (!response.ok) {
    throw await responseError(response);
  }
  return (await response.json()) as JudgeResult;
}
