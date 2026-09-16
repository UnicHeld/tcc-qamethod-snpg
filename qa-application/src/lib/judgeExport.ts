import { JudgeResult, JudgeRunRecord } from './api';

function download(name: string, content: string, type: string): void {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function downloadJudgeJson(judgeRun: JudgeRunRecord, result: JudgeResult): void {
  download(
    `judge-${judgeRun.id}.json`,
    `${JSON.stringify({ judge_run: judgeRun, result }, null, 2)}\n`,
    'application/json',
  );
}

export function downloadJudgeMarkdown(judgeRun: JudgeRunRecord, result: JudgeResult): void {
  download(`judge-${judgeRun.id}.md`, result.result_markdown, 'text/markdown;charset=utf-8');
}
