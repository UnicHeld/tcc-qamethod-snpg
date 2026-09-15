import { describe, expect, it } from 'vitest';

import { DocumentRecord, RunRecord, RunResult } from './api';
import { buildMarkdownExport } from './runExport';

describe('buildMarkdownExport', () => {
  it('identifica simulação e inclui configuração sem dados privados de infraestrutura', () => {
    const documentRecord: DocumentRecord = {
      id: 'document-1',
      file_name: 'fixture.pdf',
      sha256: 'a'.repeat(64),
      page_count: 1,
      character_count: 42,
      created_at: '2026-09-14T12:00:00Z',
    };
    const run: RunRecord = {
      id: 'run-1',
      document_id: documentRecord.id,
      mode: 'demo',
      provider: 'local',
      model: 'deterministic-demo-v1',
      prompt_version: 'qa-method-structured-v2',
      status: 'succeeded',
      usage_kind: 'simulated',
      credential_slot: null,
      input_tokens: null,
      output_tokens: null,
      error_code: null,
      error_message: null,
      created_at: '2026-09-14T12:00:00Z',
      started_at: '2026-09-14T12:00:01Z',
      finished_at: '2026-09-14T12:00:02Z',
    };
    const result: RunResult = {
      run_id: run.id,
      report: {
        revision_sha256: documentRecord.sha256,
        simulated: true,
        title: 'Parecer de teste',
        summary: 'Resumo.',
        dimensions: [],
      },
      result_markdown: '## Originalidade\n\nConteúdo simulado.',
    };

    const markdown = buildMarkdownExport(documentRecord, run, result);

    expect(markdown).toContain('# Simulado — sem inferência LLM');
    expect(markdown).toContain('- Modo: demo');
    expect(markdown).toContain('- Provedor/modelo: local / deterministic-demo-v1');
    expect(markdown).toContain('- Prompt: qa-method-structured-v2');
    expect(markdown).toContain('- Criado: 2026-09-14T12:00:00Z');
    expect(markdown).toContain('- Finalizado: 2026-09-14T12:00:02Z');
    expect(markdown).toContain('- Slot de credencial: não registrado');
    expect(markdown).toContain(result.result_markdown);
    expect(markdown).not.toContain('postgresql://');
  });
});
