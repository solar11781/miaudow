import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { usePageReveals } from '../../motion/cinema';
import { Link, useSearchParams } from 'react-router-dom';
import { api, type CopilotResponse, type WaterSituation } from '../../api';
import { answer as localAnswer, type Answer } from './answer';
import { climateYear } from '../../data/climate';
import { Button, ButtonLink } from '../../design-system/Button';
import { Icon } from '../../design-system/Icon';
import { KindBadge } from '../provenance/KindBadge';
import { SourceValue } from '../provenance/SourceValue';
import { useFormat, usePick, useSettings, useT } from '../../app/settings';
import { useSpeech } from './useSpeech';
import { VoiceButton } from './VoiceButton';
import { CoreTag } from '../../design-system/CoreTag';
import { Brocade } from '../../design-system/Brocade';
import { Media } from '../../design-system/Media';
import { ART } from '../../data/art';
import { BrandEmblem, BrandMark } from '../../app/Brand';
import s from './assistant.module.css';
import { useLocalTo } from '../../app/paths';
import { nextStep, type NextStep } from './nextStep';

type Engine = 'checking' | 'server' | 'browser';
type Turn =
  | { id: number; question: string; step: NextStep | null; kind: 'server'; res: CopilotResponse }
  | { id: number; question: string; step: NextStep | null; kind: 'local'; res: Answer }
  | { id: number; question: string; step: NextStep | null; kind: 'pending' };

const WATERS: WaterSituation[] = ['canal_end', 'high_field', 'water_short', 'reliable'];

function YearCard({ year }: { year: number }) {
  const t = useT();
  const local = useLocalTo();
  const f = useFormat();
  const row = climateYear(year);
  if (!row) return null;
  return (
    <Link to={local(`/khoa-hoc?nam=${year}`)} className={s.card}>
      <span className={s.cardKind}>
        <Icon name="rain" size={18} />
        {t.copilot.cardYear}
      </span>
      <strong className={s.cardTitle}>{year}</strong>
      <span className={s.cardStrip} aria-hidden="true">
        {row.anomaly_pct.map((p, m) => (
          <i
            key={m}
            style={{
              background:
                p === null
                  ? 'transparent'
                  : `color-mix(in oklab, ${p < 0 ? 'var(--data-drought-strong)' : 'var(--data-rain)'} ${Math.round(10 + Math.min(1, Math.abs(p) / (p < 0 ? 100 : 150)) * 85)}%, var(--bg-sunk))`,
            }}
          />
        ))}
      </span>
      <span className={s.cardLine}>
        {t.climate.annual}: {f.n(row.annual_rain_mm ?? 0)} mm · {t.climate.dryMonths}: {row.drought_rain_months.length}
      </span>
      <span className={s.cardGo}>
        {t.copilot.openObservatory}
        <Icon name="arrowRight" size={16} />
      </span>
    </Link>
  );
}

function Citations({ citations }: { citations: CopilotResponse['citations'] }) {
  const t = useT();
  const pick = usePick();
  if (citations.length === 0) return null;
  return (
    <ul className={s.cites}>
      {citations.map((c) => (
        <li key={c.passage_id}>
          <Icon name="book" size={18} />
          <span>
            <strong>{pick(c.title)}</strong>
            {c.location && <span className={s.loc}> · {c.location}</span>}
          </span>
          {c.url && (
            <a href={c.url} target="_blank" rel="noreferrer" className={s.citeLink}>
              {t.sheet.link}
            </a>
          )}
        </li>
      ))}
    </ul>
  );
}

function AnswerHead({ res }: { res: CopilotResponse }) {
  const t = useT();
  return (
    <div className={s.aHead}>
      <span className={`${s.who} ${s.bot}`}>
        <BrandMark size={32} />
        {t.assistant.bot}
      </span>
      <span className={s.status} data-status={res.status}>
        {t.copilot.status[res.status]}
      </span>
      <span className={s.engine}>
        {res.engine === 'claude' ? t.copilot.engineClaude : t.copilot.engineDeterministic}
      </span>
    </div>
  );
}

function Missing({ items }: { items: CopilotResponse['missing_information'] }) {
  const t = useT();
  const pick = usePick();
  if (items.length === 0) return null;
  return (
    <div className={s.missing}>
      <p>{t.copilot.missing}</p>
      <ul>
        {items.slice(0, 5).map((m) => (
          <li key={m.vi}>{pick(m)}</li>
        ))}
      </ul>
    </div>
  );
}

export function ServerAnswer({
  res,
  water,
  voiceNote = true,
}: {
  res: CopilotResponse;
  water: WaterSituation | null;
  /** The "no Vietnamese voice" note is printed once, under the newest answer. */
  voiceNote?: boolean;
}) {
  const t = useT();
  const local = useLocalTo();
  const pick = usePick();
  const { lang } = useSettings();
  const speech = useSpeech(lang, () => undefined);
  const plans = res.cards.filter((c) => c.kind === 'plan');
  const years = res.cards.filter((c) => c.kind === 'year');
  return (
    <div className={s.a}>
      <AnswerHead res={res} />
      <div className={s.answerText}>
        {res.answer.split('\n').map((line, i) => (
          <p key={i}>{line}</p>
        ))}
      </div>

      {plans.length > 0 && (
        <div className={s.cards}>
          {plans.map((c) => (
            <Link
              key={c.ref_id}
              className={s.card}
              to={local(
                `/nong-dan/phuong-an?${new URLSearchParams({ ...(water ? { ruong: water } : {}), the: c.ref_id }).toString()}`,
              )}
            >
              <span className={s.cardKind}>
                <Icon name="sprout" size={18} />
                {t.copilot.cardPlan}
              </span>
              <strong className={s.cardTitle}>{pick(c.title)}</strong>
              <span className={s.cardGo}>
                {t.copilot.openPlan}
                <Icon name="arrowRight" size={16} />
              </span>
            </Link>
          ))}
        </div>
      )}
      {years.length > 0 && (
        <div className={s.cards}>
          {years.map((c) => (
            <YearCard key={c.ref_id} year={Number(c.ref_id)} />
          ))}
        </div>
      )}
      <Citations citations={res.citations} />
      <Missing items={res.missing_information} />
      <div className={s.tools}>
        {speech.canSpeak && (
          <button
            type="button"
            className={s.toolBtn}
            onClick={() => (speech.speaking ? speech.stopSpeaking() : speech.speak(res.answer))}
            aria-pressed={speech.speaking}
          >
            <Icon name={speech.speaking ? 'stop' : 'volume'} size={18} />
            {speech.speaking ? t.copilot.stopReading : t.copilot.readAloud}
          </button>
        )}
        {voiceNote && speech.noVoice && <p className={s.small}>{t.copilot.noVoice}</p>}
        <details className={s.trace}>
          <summary>{t.copilot.howFound}</summary>
          <ol>
            {res.tool_trace.map((tc, i) => (
              <li key={i}>
                <span className="mono">{tc.tool}</span> {tc.ok ? '✓' : '✗'}{' '}
                <span className={s.traceIn}>{JSON.stringify(tc.input)}</span>
              </li>
            ))}
            {res.engine === 'claude' && res.model && <li>{t.copilot.modelUsed(res.model)}</li>}
            <li>{t.copilot.numbersChecked(res.numbers.checked, res.numbers.unverified.length)}</li>
          </ol>
        </details>
      </div>
    </div>
  );
}

function NextStepLink({ step }: { step: NextStep }) {
  const t = useT();
  const local = useLocalTo();
  const to = step.land ? `/nong-dan/nam?${new URLSearchParams({ ruong: step.land }).toString()}` : '/nong-dan/ruong';
  return (
    <div className={s.next}>
      <ButtonLink to={local(to)} icon="arrowRight" block>
        {step.land ? t.copilot.nextWithLand(t.farmer.lands[step.land].title) : t.copilot.nextNoLand}
      </ButtonLink>
      <p className={s.small}>{t.copilot.nextHelp}</p>
    </div>
  );
}

function LocalAnswer({ res }: { res: Answer }) {
  const t = useT();
  return (
    <div className={s.a}>
      <div className={s.aHead}>
        <span className={`${s.who} ${s.bot}`}>
          <BrandMark size={32} />
          {t.assistant.bot}
        </span>
        <span className={s.engine}>{t.copilot.engineBrowser}</span>
        {res.kinds.map((k) => (
          <KindBadge key={k} kind={k} compact />
        ))}
      </div>
      <ul className={s.lines}>
        {res.lines.map((line, i) => (
          <li key={i} className={line.ref ? s.lineRef : undefined}>
            <span>{line.text}</span>
            {line.ref && <SourceValue {...line.ref} />}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function AssistantPage() {
  const pageRef = useRef<HTMLElement>(null);
  usePageReveals(pageRef);
  const t = useT();
  const { lang } = useSettings();
  const f = useFormat();
  const [params] = useSearchParams();
  const fmt = useMemo(() => ({ pct: (v: number) => f.pct(v), signedPct: (v: number) => f.signedPct(v), n: f.n }), [f]);
  const [engine, setEngine] = useState<Engine>('checking');
  const [claude, setClaude] = useState(false);
  const [mode, setMode] = useState<'simple' | 'technical'>('simple');
  const [water, setWater] = useState<WaterSituation | null>(() => {
    const w = params.get('ruong');
    return (WATERS as string[]).includes(w ?? '') ? (w as WaterSituation) : null;
  });
  const [turns, setTurns] = useState<Turn[]>([]);
  const [q, setQ] = useState(() => params.get('q') ?? '');
  const [heard, setHeard] = useState(false);
  const input = useRef<HTMLTextAreaElement>(null);
  const log = useRef<HTMLOListElement>(null);
  const inflight = useRef<AbortController | null>(null);
  const speech = useSpeech(lang, (text) => {
    setQ(text);
    setHeard(true);
    input.current?.focus();
  });

  useEffect(() => {
    const ctrl = new AbortController();
    api
      .health(ctrl.signal)
      .then((h) => {
        const c = h.copilot;
        // the browser engine is the fallback: health has no copilot entry when the copilot is off or offline
        if (c === undefined) {
          setEngine('browser');
          return;
        }
        setEngine('server');
        setClaude(typeof c === 'object' && c !== null && (c.engine === 'claude' || c.configured === true));
      })
      .catch(() => {
        if (!ctrl.signal.aborted) setEngine('browser');
      });
    return () => {
      ctrl.abort();
      inflight.current?.abort();
    };
  }, []);

  const ask = async (question: string) => {
    const text = question.trim();
    if (!text) return;
    setQ('');
    setHeard(false);
    const id = Date.now();
    const step = nextStep(text, water);
    const local = (): Answer =>
      step?.kind === 'field'
        ? { type: 'abstain', lines: [{ text: t.copilot.ownField }], evidence: [], kinds: [] }
        : localAnswer(text, lang, fmt, { noEvidence: t.assistant.noEvidence, noRanking: t.assistant.noRanking });
    if (engine !== 'server') {
      setTurns((prev) => [...prev, { id, question: text, step, kind: 'local', res: local() }]);
      return;
    }
    setTurns((prev) => [...prev, { id, question: text, step, kind: 'pending' }]);
    inflight.current?.abort();
    const ctrl = new AbortController();
    inflight.current = ctrl;
    try {
      const res = await api.copilot({ question: text, mode, lang, water }, ctrl.signal);
      setTurns((prev) => prev.map((x) => (x.id === id ? { id, question: text, step, kind: 'server', res } : x)));
    } catch {
      if (ctrl.signal.aborted && inflight.current !== ctrl) return;
      setEngine('browser');
      setTurns((prev) =>
        prev.map((x) => (x.id === id ? { id, question: text, step, kind: 'local', res: local() } : x)),
      );
    }
    requestAnimationFrame(() =>
      log.current?.lastElementChild?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }),
    );
  };

  // A deep link with ?q=…&hoi=1 (from the observatory or the evidence library) asks right away, once.
  const asked = useRef(false);
  useEffect(() => {
    if (asked.current || engine === 'checking' || params.get('hoi') !== '1' || !params.get('q')) return;
    asked.current = true;
    void ask(params.get('q') ?? '');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [engine]);

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void ask(q);
  };

  return (
    <main ref={pageRef} id="main" className="surface-paper">
      <header className={`${s.hero} surface-forest`}>
        <span className={s.heroPhoto}>
          <Media slug={ART.pageHead.assistant.slug} sizes="100vw" priority decorative />
        </span>
        <div className={`container ${s.heroInner}`}>
          <BrandEmblem width={220} className={s.heroEmblem} />
          <div className={s.heroText}>
            <p className={`script ${s.greeting}`}>{t.copilot.greeting}</p>
            <h1 className={`display ${s.heroTitle}`}>{t.copilot.brandTitle}</h1>
            <p className={s.heroLead}>{t.copilot.brandLead}</p>
          </div>
        </div>
        <Brocade />
      </header>
      <section className={`band ${s.page}`} aria-labelledby="ai-title">
        <div className={`container ${s.grid}`}>
          <div className={s.chat}>
            <div className={s.controls}>
              <div className={s.seg} role="radiogroup" aria-label={t.copilot.modeLabel}>
                {(['simple', 'technical'] as const).map((m) => (
                  <button key={m} type="button" role="radio" aria-checked={mode === m} onClick={() => setMode(m)}>
                    {t.copilot.modes[m]}
                  </button>
                ))}
              </div>
              <label className={s.waterPick}>
                <span>{t.copilot.waterLabel}</span>
                <select
                  value={water ?? ''}
                  onChange={(e) => setWater((e.target.value || null) as WaterSituation | null)}
                >
                  <option value="">{t.copilot.waterUnknown}</option>
                  {WATERS.map((w) => (
                    <option key={w} value={w}>
                      {t.farmer.lands[w].title}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className={s.examples} aria-label={t.assistant.examplesLabel}>
              {t.copilot.examples.map((ex) => (
                <button key={ex} type="button" onClick={() => void ask(ex)}>
                  {ex}
                </button>
              ))}
            </div>

            <ol ref={log} className={s.log} aria-live="polite">
              {turns.length === 0 && <li className={s.empty}>{t.copilot.empty}</li>}
              {turns.map((turn) => (
                <li key={turn.id} className={s.turn}>
                  <p className={s.q}>
                    <span className={s.who}>{t.assistant.you}</span>
                    {turn.question}
                  </p>
                  {turn.kind === 'pending' && (
                    <div className={s.a}>
                      <p className={s.thinking}>{t.copilot.working}</p>
                    </div>
                  )}
                  {turn.kind === 'server' && (
                    <ServerAnswer res={turn.res} water={water} voiceNote={turn === turns[turns.length - 1]} />
                  )}
                  {turn.kind === 'local' && <LocalAnswer res={turn.res} />}
                  {turn.kind !== 'pending' && turn.step && <NextStepLink step={turn.step} />}
                </li>
              ))}
            </ol>

            {engine === 'server' && claude && <p className={s.privacy}>{t.copilot.privacy}</p>}
            <form className={s.form} onSubmit={onSubmit}>
              <label htmlFor="ask" className="visually-hidden">
                {t.assistant.inputLabel}
              </label>
              <textarea
                id="ask"
                ref={input}
                value={q}
                rows={2}
                maxLength={1200}
                placeholder={t.assistant.placeholder}
                onChange={(e) => {
                  setQ(e.target.value);
                  setHeard(false);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    void ask(q);
                  }
                }}
              />
              <div className={s.formRow}>
                {speech.canListen && (
                  <VoiceButton listening={speech.listening} listen={speech.listen} stop={speech.stopListening} />
                )}
                <Button type="submit" icon="send" disabled={!q.trim()}>
                  {t.assistant.ask}
                </Button>
              </div>
              {heard && (
                <p className={s.heard} role="status">
                  {t.copilot.checkTranscript}
                </p>
              )}
              {speech.error && (
                <p className={s.heard} role="status">
                  {t.copilot.micError}
                </p>
              )}
              {!speech.canListen && <p className={s.small}>{t.copilot.noMic}</p>}
            </form>
            {turns.length > 0 && (
              <button type="button" className={s.clear} onClick={() => setTurns([])}>
                {t.assistant.clear}
              </button>
            )}
          </div>

          <div className={s.intro}>
            <h2 id="ai-title" className={`h2 ${s.title}`}>
              {t.copilot.title}
            </h2>
            <p className="lead">{t.copilot.lead}</p>
            <CoreTag core="copilot" />
            <ol className={s.pipeline} aria-label={t.copilot.pipelineLabel}>
              {t.copilot.pipeline.map((step, i) => (
                <li key={step}>
                  <span>{i + 1}</span>
                  {step}
                </li>
              ))}
            </ol>
            <div className={s.statusBox} role="status">
              <span className={s.statusDot} data-on={engine === 'server'} aria-hidden="true" />
              <div>
                <strong>
                  {engine === 'checking'
                    ? t.common.loading
                    : engine === 'server'
                      ? t.copilot.serverOn
                      : t.copilot.serverOff}
                </strong>
                <p>
                  {engine === 'server' ? (claude ? t.copilot.claudeOn : t.copilot.claudeOff) : t.copilot.browserHelp}
                </p>
              </div>
            </div>
            <p className={s.honest}>
              <Icon name="shield" size={18} />
              {t.copilot.honest}
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
