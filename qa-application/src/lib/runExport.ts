import { DocumentRecord, RunRecord, RunResult } from './api';

function downloadText(content: string, fileName: string, type: string): void {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function exportBaseName(documentRecord: DocumentRecord, run: RunRecord): string {
  const documentName = documentRecord.file_name
    .replace(/\.pdf$/i, '')
    .replace(/[^a-z0-9_-]+/gi, '-');
  return `${documentName || 'documento'}-run-${run.id.slice(0, 8)}`;
}

export function buildMarkdownExport(
  documentRecord: DocumentRecord,
  run: RunRecord,
  result: RunResult,
): string {
  const modeLabel = result.report.simulated
    ? 'Simulado — sem inferência LLM'
    : 'Real — inferência externa autorizada';
  return [
    `# ${modeLabel}`,
    '',
    `- Documento: ${documentRecord.file_name}`,
    `- SHA-256: ${documentRecord.sha256}`,
    `- Run: ${run.id}`,
    `- Status: ${run.status}`,
    `- Modo: ${run.mode}`,
    `- Provedor/modelo: ${run.provider} / ${run.model}`,
    `- Prompt: ${run.prompt_version}`,
    `- Criado: ${run.created_at}`,
    `- Iniciado: ${run.started_at ?? 'não registrado'}`,
    `- Finalizado: ${run.finished_at ?? 'não registrado'}`,
    `- Consumo: ${run.usage_kind ?? 'não registrado'}`,
    `- Tokens de entrada: ${run.input_tokens ?? 'não registrado'}`,
    `- Tokens de saída: ${run.output_tokens ?? 'não registrado'}`,
    `- Slot de credencial: ${run.credential_slot ?? 'não registrado'}`,
    '',
    result.result_markdown,
    '',
  ].join('\n');
}

export function downloadRunJson(
  documentRecord: DocumentRecord,
  run: RunRecord,
  result: RunResult,
): void {
  const payload = JSON.stringify(
    {
      document: documentRecord,
      run,
      report: result.report,
      result_markdown: result.result_markdown,
    },
    null,
    2,
  );
  downloadText(payload, `${exportBaseName(documentRecord, run)}.json`, 'application/json');
}

export function downloadRunMarkdown(
  documentRecord: DocumentRecord,
  run: RunRecord,
  result: RunResult,
): void {
  downloadText(
    buildMarkdownExport(documentRecord, run, result),
    `${exportBaseName(documentRecord, run)}.md`,
    'text/markdown;charset=utf-8',
  );
}
