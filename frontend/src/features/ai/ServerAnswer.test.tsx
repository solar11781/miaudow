// D-177: the server copilot shows our passages and fixed year lines with their sources; a year answer has citations
// but no passage card, and its sources must still show (H5: every displayed number has a source).
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { SettingsProvider } from '../../app/settings';
import type { CopilotResponse } from '../../api';
import { ServerAnswer } from './AssistantPage';
import { vi } from '../../i18n/vi';

const yearAnswer: CopilotResponse = {
  status: 'grounded',
  engine: 'claude',
  model: 'claude-haiku-5-5',
  answer: 'Các nguồn này trả lời câu hỏi của bạn:\nNăm 2010 ở đất trồng Nghệ An:\n• Mưa lớn: 100%',
  citations: [
    {
      passage_id: 'year-2010-E-019',
      source_id: 'E-019',
      title: { vi: 'Thực nghiệm E-019 của nhóm', en: 'Our experiment E-019' },
      location: null,
      url: null,
    },
  ],
  cards: [],
  tool_trace: [{ tool: 'year_conditions', input: { year: 2010 }, ok: true }],
  numbers: { checked: 2, unverified: [] },
  missing_information: [],
};

describe('server copilot answer', () => {
  afterEach(cleanup);
  it('shows the sources of an answer without passage cards', () => {
    render(
      <SettingsProvider>
        <MemoryRouter>
          <ServerAnswer res={yearAnswer} water={null} />
        </MemoryRouter>
      </SettingsProvider>,
    );
    expect(screen.getByText('• Mưa lớn: 100%')).toBeTruthy();
    expect(screen.getByText('Thực nghiệm E-019 của nhóm')).toBeTruthy();
  });

  it('says what Claude did: it picked passages, it wrote none', () => {
    render(
      <SettingsProvider>
        <MemoryRouter>
          <ServerAnswer res={yearAnswer} water={null} />
        </MemoryRouter>
      </SettingsProvider>,
    );
    expect(screen.getByText(vi.copilot.engineClaude)).toBeTruthy();
  });

  it('explains a refusal to rank with the product rule, not with missing evidence', () => {
    const refused: CopilotResponse = {
      ...yearAnswer,
      status: 'insufficient_evidence',
      engine: 'deterministic',
      model: null,
      answer: 'Chưa đủ dữ liệu để kết luận.',
      citations: [],
      tool_trace: [],
    };
    render(
      <SettingsProvider>
        <MemoryRouter>
          <ServerAnswer res={refused} water={null} noRank />
        </MemoryRouter>
      </SettingsProvider>,
    );
    expect(screen.getByText(vi.copilot.noRankingReason)).toBeTruthy();
    expect(screen.queryByText('Chưa đủ dữ liệu để kết luận.')).toBeNull();
    expect(screen.queryByText(vi.copilot.status.insufficient_evidence)).toBeNull();
  });
});
