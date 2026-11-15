// CLAUDE.md scientific boundaries and D-52: the two studies' profit values are never shown as comparable; the trial
// chapter shows one study's value with its own definition and trial label, under the study's own land words (D-160).
import { afterEach, describe, expect, it, vi as vitest } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { SettingsProvider } from '../../app/settings';
import { ProvenanceProvider } from '../provenance/ProvenanceProvider';
import { HomePage, Problem } from './HomePage';
import { vi } from '../../i18n/vi';

function renderProblem() {
  render(
    <SettingsProvider>
      <ProvenanceProvider>
        <Problem />
      </ProvenanceProvider>
    </SettingsProvider>,
  );
  const section = document.querySelector('#ch-2');
  if (!section) throw new Error('no trial chapter');
  return section;
}

describe('home trial chapter', () => {
  afterEach(cleanup);
  it('shows one money value only, from the first paper, with its definition in the tile', () => {
    const section = renderProblem();
    expect([...section.querySelectorAll('[data-value]')]).toHaveLength(1);
    const tile = section.querySelector('[data-value]')?.parentElement;
    expect(tile?.textContent).toContain(vi.farmer.definitionPlain.p02);
    expect(tile?.textContent).toContain(vi.home.riceSpring);
    expect(section.textContent).not.toContain(vi.farmer.definitionPlain.p03);
    expect(section.textContent).not.toContain('1,16'); // the second paper's value (rules/rotations.yaml usual_p03)
  });
  it('heads the chapter with the land words of the first paper, not a profit claim', () => {
    const section = renderProblem();
    // rules/rotations.yaml `usual` land_archetypes: P-02 "đất lúa kém hiệu quả, thường xuyên khô hạn" (D-160)
    expect(section.querySelector('h2')?.textContent).toBe('Đất lúa kém hiệu quả, thường xuyên khô hạn');
  });
});

// D-187 (roleplay audit F6): the farmer meets what the app is and the four steps first; the AI cores, the model
// numbers and the other proof material sit lower, under a plain heading for extension officers.
describe('home page order', () => {
  afterEach(() => {
    cleanup();
    vitest.unstubAllGlobals();
  });

  function renderHome() {
    vitest.stubGlobal(
      'fetch',
      vitest.fn(async () => new Response('{}', { status: 503 })),
    );
    render(
      <SettingsProvider>
        <ProvenanceProvider>
          <MemoryRouter>
            <HomePage />
          </MemoryRouter>
        </ProvenanceProvider>
      </SettingsProvider>,
    );
    return [...document.querySelectorAll('main h2')].map((h) => h.id);
  }

  it('puts the "what this is" box and the four steps right after the hero, the proof material after them', () => {
    const order = renderHome();
    expect(order.slice(0, 3)).toEqual(['about-title', 'steps-title', 'more-title']);
    for (const id of ['problem-title', 'climate-title', 'cores-title', 'honesty-title', 'obs-title'])
      expect(order.indexOf(id)).toBeGreaterThan(order.indexOf('more-title'));
  });

  it('says in plain words what the app does, that past years are not a forecast and that it does not choose', () => {
    renderHome();
    const box = document.querySelector('section[aria-labelledby="about-title"]');
    expect(box?.querySelector('h2')?.textContent).toBe('Ứng dụng này làm gì?');
    expect(box?.textContent).toContain('Nghệ An');
    expect(box?.textContent).toContain('Không dự báo mùa tới');
    expect(box?.textContent).toContain('Không chọn thay gia đình bạn');
  });

  it('keeps AI words off the first screen and gives the steps their own start button', () => {
    renderHome();
    const hero = document.querySelector('section[aria-labelledby="hero-title"]');
    expect(hero?.textContent).not.toMatch(/lõi AI/i);
    const steps = document.querySelector('section[aria-labelledby="steps-title"]');
    const start = [...(steps?.querySelectorAll('a') ?? [])].find((a) => a.textContent === 'Tìm hiểu ruộng nhà mình');
    expect(start?.getAttribute('href')).toBe('/nong-dan/ruong');
  });

  it('folds what each AI core uses, gives and cannot do yet, one tap away, so the proof part is shorter', () => {
    renderHome();
    const folds = [...document.querySelectorAll('#cores article details')];
    expect(folds).toHaveLength(4);
    for (const d of folds) {
      expect(d.hasAttribute('open')).toBe(false);
      expect(d.querySelector('summary')?.textContent).toBe('Dùng gì, cho ra gì, chưa làm được gì');
      expect(d.querySelectorAll('dt')).toHaveLength(3);
    }
  });
});
