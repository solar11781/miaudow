import { useMemo, useRef, useState, type FormEvent } from 'react';
import { answer, type Answer } from './answer';
import { notConnected } from './languageModel';
import { Button } from '../../design-system/Button';
import { Icon } from '../../design-system/Icon';
import { Photo } from '../../design-system/Photo';
import { KindBadge } from '../provenance/KindBadge';
import { SourceValue } from '../provenance/SourceValue';
import { useFormat, useSettings, useT } from '../../app/settings';
import s from './assistant.module.css';

interface Turn { id: number; question: string; result: Answer; example?: boolean }

export function AssistantPage() {
  const t = useT();
  const { lang } = useSettings();
  const f = useFormat();
  const fmt = useMemo(() => ({ pct: (v: number) => f.pct(v), signedPct: (v: number) => f.signedPct(v), n: f.n }), [f]);
  // Opens with one answered example, so the first screen shows what the assistant does (marked as an example).
  const [turns, setTurns] = useState<Turn[]>(() => {
    const q0 = t.assistant.examples[0] ?? '';
    return [{ id: 0, question: q0, example: true, result: answer(q0, lang, fmt, { noEvidence: t.assistant.noEvidence, noRanking: t.assistant.noRanking }) }];
  });
  const [q, setQ] = useState('');
  const input = useRef<HTMLInputElement>(null);
  const log = useRef<HTMLOListElement>(null);

  const ask = (question: string) => {
    const text = question.trim();
    if (!text) return;
    const result = answer(text, lang, fmt, { noEvidence: t.assistant.noEvidence, noRanking: t.assistant.noRanking });
    setTurns((prev) => [...prev, { id: Date.now(), question: text, result }]);
    setQ('');
    requestAnimationFrame(() => log.current?.lastElementChild?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }));
  };
  const onSubmit = (e: FormEvent) => { e.preventDefault(); ask(q); input.current?.focus(); };

  return (
    <main id="main" className="surface-paper">
      <section className={`band ${s.page}`} aria-labelledby="ai-title">
        <div className={`container ${s.grid}`}>
          <div className={s.intro}>
            <p className="eyebrow">{t.assistant.eyebrow}</p>
            <h1 id="ai-title" className="display" style={{ fontSize: 'var(--t-h1)' }}>{t.assistant.title}</h1>
            <p className="lead">{t.assistant.lead}</p>
            <ol className={s.pipeline} aria-label={t.assistant.eyebrow}>
              {t.assistant.pipeline.map((step, i) => <li key={step}><span>{i + 1}</span>{step}</li>)}
            </ol>
            <div className={s.status}>
              <span className={s.statusDot} data-on={notConnected.connected} aria-hidden="true" />
              <div><strong>{t.assistant.llmStatus}</strong><p>{t.assistant.llmHelp}</p></div>
            </div>
            <p className={s.honest}><Icon name="shield" size={18} />{t.assistant.honest}</p>
            <div className={s.photo}><Photo slug="dam-sen" sizes="(min-width: 960px) 420px, 92vw" /></div>
          </div>

          <div className={s.chat}>
            <div className={s.examples} aria-label={t.assistant.examplesLabel}>
              {t.assistant.examples.map((ex) => (
                <button key={ex} type="button" onClick={() => ask(ex)}>{ex}</button>
              ))}
            </div>

            <ol ref={log} className={s.log} aria-live="polite">
              {turns.map((turn) => (
                <li key={turn.id} className={s.turn}>
                  <p className={s.q}><span className={s.who}>{t.assistant.you}</span>{turn.question}</p>
                  <div className={s.a}>
                    <div className={s.aHead}>
                      <span className={s.who}>{t.assistant.bot}</span>
                      {turn.example && <span className={s.exampleTag}>{t.assistant.exampleTag}</span>}
                      <KindBadge kind="assistant" compact />
                      {turn.result.kinds.map((k) => <KindBadge key={k} kind={k} compact />)}
                    </div>
                    <ul className={s.lines}>
                      {turn.result.lines.map((line, i) => (
                        <li key={i} className={line.ref ? s.lineRef : undefined}>
                          <span>{line.text}</span>
                          {line.ref && <SourceValue {...line.ref} />}
                        </li>
                      ))}
                    </ul>
                    {turn.result.evidence.length > 0 && (
                      <div className={s.evidence}>
                        <p>{t.assistant.evidenceFrom}</p>
                        <ul>
                          {turn.result.evidence.map((h) => (
                            <li key={h.passage.id}>
                              <span className="mono">{h.passage.id}</span>
                              <span className={s.score}>{t.assistant.matchScore} {f.n(h.score, 1)}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </li>
              ))}
            </ol>

            <form className={s.form} onSubmit={onSubmit}>
              <label htmlFor="ask" className="visually-hidden">{t.assistant.inputLabel}</label>
              <input id="ask" ref={input} value={q} onChange={(e) => setQ(e.target.value)} placeholder={t.assistant.placeholder} autoComplete="off" enterKeyHint="send" maxLength={240} />
              <Button type="submit" icon="arrowUpRight" disabled={!q.trim()}>{t.assistant.ask}</Button>
            </form>
            {turns.length > 0 && (
              <button type="button" className={s.clear} onClick={() => setTurns([])}>{t.assistant.clear}</button>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
