import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import Evaluation from './Evaluation';

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
      model: 'gemini-2.5-flash-lite',
      requires_external_confirmation: true,
    },
  ],
};

const evaluation = {
  mode: 'demo',
  simulated: true,
  mode_label: 'Simulado — sem inferência LLM',
  provider: 'local',
  model: 'deterministic-demo-v1',
  prompt_version: 'qa-method-v1',
  document: {
    file_name: 'fixture.pdf',
    sha256: 'a'.repeat(64),
    page_count: 1,
    character_count: 42,
  },
  result_markdown: '# Simulado — sem inferência LLM\n\nResultado de teste.',
  usage: { kind: 'simulated', input_tokens: null, output_tokens: null },
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe('Evaluation', () => {
  it('separa a seleção do arquivo da execução e marca o resultado simulado', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/capabilities')) {
        return new Response(JSON.stringify(capabilities), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      return new Response(JSON.stringify(evaluation), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    });
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <Evaluation />
      </BrowserRouter>,
    );

    await screen.findByText('local · deterministic-demo-v1');
    const fileInput = screen.getByLabelText('Selecionar arquivo');
    await user.upload(fileInput, new File(['%PDF-1.4'], 'fixture.pdf', { type: 'application/pdf' }));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const executeButton = screen.getByRole('button', { name: 'Executar avaliação' });
    expect(executeButton).toBeEnabled();
    await user.click(executeButton);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(await screen.findByRole('status', { name: '' })).toHaveTextContent(
      'Simulado — sem inferência LLM',
    );
    expect(screen.getByRole('button', { name: 'Exportar JSON' })).toBeEnabled();
  });
});
