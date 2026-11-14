// Read-aloud must never use a voice of another language than the app language.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, render, renderHook, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { SettingsProvider } from '../../app/settings';
import type { CopilotResponse } from '../../api';
import { vi as viText } from '../../i18n/vi';
import { ServerAnswer } from './AssistantPage';
import { useSpeech } from './useSpeech';

const voice = (lang: string, name = lang) => ({ lang, name }) as SpeechSynthesisVoice;

let voices: SpeechSynthesisVoice[];
let changed: Array<() => void>;
const synth = {
  getVoices: () => voices,
  speak: vi.fn(),
  cancel: vi.fn(),
  addEventListener: (_: string, fn: () => void) => changed.push(fn),
  removeEventListener: (_: string, fn: () => void) => {
    changed = changed.filter((f) => f !== fn);
  },
};
const loadVoices = (v: SpeechSynthesisVoice[]) => {
  voices = v;
  act(() => changed.forEach((f) => f()));
};

beforeEach(() => {
  voices = [];
  changed = [];
  synth.speak.mockClear();
  vi.stubGlobal('speechSynthesis', synth);
  vi.stubGlobal(
    'SpeechSynthesisUtterance',
    class {
      lang = '';
      voice: SpeechSynthesisVoice | null = null;
      constructor(public text: string) {}
    },
  );
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const spoken = () => synth.speak.mock.calls[0]?.[0] as { lang: string; voice: SpeechSynthesisVoice | null };

describe('read-aloud voice', () => {
  it('uses the vi voice that arrives after the page loaded', () => {
    const { result } = renderHook(() => useSpeech('vi', () => undefined));
    expect(result.current.canSpeak).toBe(false);
    loadVoices([voice('en-US'), voice('vi_VN', 'An')]);
    expect(result.current.canSpeak).toBe(true);
    act(() => result.current.speak('xin chào'));
    expect(spoken().voice?.name).toBe('An');
    expect(spoken().lang).toBe('vi-VN');
  });

  it('never speaks with an en voice for vi text', () => {
    voices = [voice('en-US'), voice('en_GB')];
    const { result } = renderHook(() => useSpeech('vi', () => undefined));
    expect(result.current.canSpeak).toBe(false);
    act(() => result.current.speak('xin chào'));
    expect(synth.speak).not.toHaveBeenCalled();
  });

  it('matches vi-VN, vi_VN and plain vi', () => {
    for (const code of ['vi-VN', 'vi_VN', 'vi']) {
      voices = [voice(code)];
      const { result, unmount } = renderHook(() => useSpeech('vi', () => undefined));
      expect(result.current.canSpeak).toBe(true);
      unmount();
    }
  });

  it('picks the matching voice again when the language changes', () => {
    voices = [voice('en-US', 'Sam'), voice('vi-VN', 'An')];
    const { result, rerender } = renderHook(({ l }) => useSpeech(l, () => undefined), {
      initialProps: { l: 'vi' as 'vi' | 'en' },
    });
    act(() => result.current.speak('a'));
    expect(spoken().voice?.name).toBe('An');
    synth.speak.mockClear();
    rerender({ l: 'en' });
    act(() => result.current.speak('b'));
    expect(spoken().voice?.name).toBe('Sam');
    expect(spoken().lang).toBe('en-US');
  });

  it('removes its listener on unmount', () => {
    const { unmount } = renderHook(() => useSpeech('vi', () => undefined));
    expect(changed).toHaveLength(1);
    unmount();
    expect(changed).toHaveLength(0);
  });
});

const answer: CopilotResponse = {
  status: 'grounded',
  engine: 'claude',
  model: 'm',
  answer: 'Trả lời',
  citations: [],
  cards: [],
  tool_trace: [],
  numbers: { checked: 0, unverified: [] },
  missing_information: [],
};
const view = () =>
  render(
    <SettingsProvider>
      <MemoryRouter>
        <ServerAnswer res={answer} water={null} />
      </MemoryRouter>
    </SettingsProvider>,
  );

describe('read-aloud button', () => {
  it('shows the install note and no button when there is no vi voice', () => {
    voices = [voice('en-US')];
    view();
    expect(screen.getByText(viText.copilot.noVoice)).toBeTruthy();
    expect(screen.queryByRole('button', { name: viText.copilot.readAloud })).toBeNull();
  });

  it('shows the button when a vi voice exists', () => {
    voices = [voice('vi-VN')];
    view();
    expect(screen.getByRole('button', { name: viText.copilot.readAloud })).toBeTruthy();
    expect(screen.queryByText(viText.copilot.noVoice)).toBeNull();
  });
});
