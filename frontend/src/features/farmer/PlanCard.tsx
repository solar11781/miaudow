import { useState, type ReactNode } from 'react';
import type {
  CompareRequest,
  CompareResponse,
  Lang,
  Plan,
  PlanId,
  Priority,
  Rule,
  RuleCode,
  Stability,
  Value,
  WaterFact,
} from '../../types';
import { Icon, type IconName } from '../../design-system/Icon';
import { displayUnit } from '../../domain/format';
import { moneyStudy } from '../../domain/moneyStudy';
import { CROP_FAMILY, MonthBar } from './MonthBar';
import { SourceValue } from '../provenance/SourceValue';
import { useApiRefs, type ApiRefs } from '../provenance/useApiRefs';
import { ApiError, explainSimply, type WhyPart } from '../../api';
import { usePick, useSettings, useT } from '../../app/settings';
import s from './PlanCard.module.css';

const FAMILY_DOT: Record<string, string> = {
  rice: '#6e9e3c',
  legume: '#c9962e',
  maize: '#d8c03c',
  root: '#c06a44',
  other: '#9a73a0',
};
// UI-UX-SPEC section 9: heavy rain, heat and cold in the weather row; both drought readings in the water row (D-58)
const WEATHER_RULES: RuleCode[] = ['heavy_rain', 'heat', 'cold'];
const DROUGHT_RULES: RuleCode[] = ['drought_rain_consecutive', 'drought_rain_any2'];

/** One card row; `hook` is its test hook card-<plan id>-row-<row> (UI-UX-SPEC section 14a, B's row names, D-169). */
function Row({
  hook,
  icon,
  title,
  note,
  highlight,
  target,
  children,
}: {
  hook: string;
  icon: IconName;
  title: string;
  note?: string;
  highlight?: boolean;
  /** A link elsewhere on the card moves the focus here. */
  target?: boolean;
  children: ReactNode;
}) {
  const t = useT();
  return (
    <section
      id={hook}
      tabIndex={target ? -1 : undefined}
      className={[s.row, highlight ? s.hl : ''].join(' ')}
      data-testid={hook}
      data-highlighted={highlight ? 'true' : undefined}
    >
      <h3 className={s.rowHead}>
        <Icon name={icon} size={18} />
        {title}
        {highlight && (
          <span className={s.prioTag}>
            <Icon name="check" size={14} strokeWidth={2.6} />
            {t.farmer.yourPriority}
          </span>
        )}
      </h3>
      {children}
      {note && <p className={s.rowNote}>{note}</p>}
    </section>
  );
}

interface Ctx {
  plan: Plan;
  res: CompareResponse;
  refs: ApiRefs;
}

function NumberOr({ v, label, refs }: { v: Value | null; label: string; refs: ApiRefs }) {
  const t = useT();
  return v ? <SourceValue {...refs.value(v, label)} /> : <span className="muted">{t.common.notAvailable}</span>;
}

function MoneyRow({ plan, res, refs, highlight }: Ctx & { highlight: boolean }) {
  const t = useT();
  const pick = usePick();
  const m = plan.money;
  const seasonLabel = (code: string) => res.seasons.find((x) => x.code === code);
  const textIds = plan.calendar.flatMap((c) => c.source_ids);
  const study = moneyStudy(plan);
  return (
    <Row hook={`card-${plan.id}-row-money`} icon="coin" title={t.farmer.rows.money} highlight={highlight}>
      {m.total && (
        <div className={s.money}>
          <SourceValue size="xl" {...refs.value(m.total, t.farmer.ourSum)}>
            {refs.number(m.total)}
          </SourceValue>
          <span className={s.unit}>
            {refs.unit(m.total)} · {t.farmer.ourSum}
          </span>
        </div>
      )}
      {m.items.length > 0 && (
        <ul className={s.cropMoney}>
          {m.items.map((item) => {
            const season = seasonLabel(item.season);
            const name = `${pick(item.crop)}${season ? `, ${pick(season.label)}` : ''}`;
            return (
              <li key={item.crop_key}>
                <span>{name}</span>
                <span>{t.farmer.profit}</span>
                <SourceValue {...refs.value(item.profit, `${t.farmer.profit} · ${name}`)} />
                <span>{t.farmer.cost}</span>
                <NumberOr v={item.cost} label={`${t.farmer.cost} · ${name}`} refs={refs} />
                {item.flag && <span>{pick(item.flag)}</span>}
              </li>
            );
          })}
        </ul>
      )}
      {m.text_only && <SourceValue {...refs.sources(textIds, pick(m.text_only), t.farmer.rows.money)} />}
      {/* the source's definition as the API gives it, then the same in plain words for the study it cites (D-170) */}
      <p className={s.rowNote}>{pick(m.definition)}</p>
      {study && <p className={s.rowNote}>{t.farmer.definitionPlain[study]}</p>}
    </Row>
  );
}

/** The note every TCVN row of a crop carries (the region note, D-68), said once above those rows; null when the crop
 * has fewer than two TCVN rows or their notes differ. Other notes stay on their own row, so the TCVN and FAO caveats
 * never mix (D-64). */
function tcvnSharedNote(facts: WaterFact[]): WaterFact['note'] {
  const tcvn = facts.filter((w) => w.measure === 'to_apply');
  const first = tcvn[0]?.note;
  return tcvn.length > 1 && first && tcvn.every((w) => w.note?.en === first.en) ? first : null;
}

/** The per-year tables of a row behind one button (D-170). The content stays in the page and is hidden by screen-only
 * CSS, so print shows it (T35). */
function YearsFold({ id, children }: { id: string; children: ReactNode }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  return (
    <div className={s.fold}>
      <button
        type="button"
        className={s.foldButton}
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((o) => !o)}
      >
        <Icon name="chevronDown" size={18} />
        {t.farmer.eachYear}
      </button>
      <div id={id} className={open ? undefined : s.folded}>
        {children}
      </div>
    </div>
  );
}

/** Shares per crop and picked year for `codes`; the rule names are the response's own labels. */
function ShareTable({ plan, codes, rules, refs }: { plan: Plan; codes: RuleCode[]; rules: Rule[]; refs: ApiRefs }) {
  const t = useT();
  const pick = usePick();
  if (!plan.exposure.length) return null;
  const label = (r: RuleCode) => {
    const rule = rules.find((x) => x.code === r);
    return rule ? pick(rule.label) : r;
  };
  return (
    <div className={s.tableWrap} tabIndex={0} role="region" aria-label={t.farmer.rows.weather}>
      <table className={s.wTable}>
        <thead>
          <tr>
            <th scope="col">{t.farmer.crop}</th>
            {codes.map((r) => (
              <th key={r} scope="col">
                {label(r)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {plan.exposure.flatMap((c) =>
            c.per_year.map((y) => (
              <tr key={`${c.crop_key}-${y.year}`}>
                <th scope="row">
                  {pick(c.crop)} · {y.year}
                </th>
                {codes.map((r) => {
                  const v = y.shares[r];
                  return (
                    <td key={r} data-rule={r}>
                      {v ? (
                        <SourceValue {...refs.share(r, v, `${label(r)} · ${pick(c.crop)} · ${y.year}`)} />
                      ) : (
                        <span className="muted">{t.common.notAvailable}</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            )),
          )}
        </tbody>
      </table>
    </div>
  );
}

function RiceBlock({ st, refs }: { st: Stability; refs: ApiRefs }) {
  const t = useT();
  const pick = usePick();
  const label = pick(st.label);
  return (
    <div className={s.riceRows}>
      <p className={s.subHead}>{label}</p>
      {st.per_year.map((y) => (
        <p key={y.year} className={s.riceLine}>
          <span className={s.riceSeason}>{y.year}</span>
          <span className={s.riceVals}>
            <span className="muted small">{t.farmer.rice.real}</span>
            <NumberOr v={y.real} label={`${label} · ${y.year}`} refs={refs} />
            {y.oos_prediction && (
              <>
                <span className="muted small">{t.farmer.rice.prediction}</span>
                <SourceValue {...refs.value(y.oos_prediction, `${t.farmer.rice.prediction} · ${y.year}`)} />
              </>
            )}
            {y.range_80 && (
              <>
                <span className="muted small">{t.farmer.rice.range}</span>
                <SourceValue {...refs.value(y.range_80.low, `${t.farmer.rice.range} · ${y.year}`)} />
                <SourceValue {...refs.value(y.range_80.high, `${t.farmer.rice.range} · ${y.year}`)} />
              </>
            )}
          </span>
        </p>
      ))}
      {st.summary && (
        <p className={s.riceLine}>
          <span className={s.riceVals}>
            <span className="muted small">{t.farmer.rice.min}</span>
            <SourceValue {...refs.value(st.summary.min, `${t.farmer.rice.min} · ${label}`)} />
            <span className="muted small">{t.farmer.rice.median}</span>
            <SourceValue {...refs.value(st.summary.median, `${t.farmer.rice.median} · ${label}`)} />
            <span className="muted small">{t.farmer.rice.max}</span>
            <SourceValue {...refs.value(st.summary.max, `${t.farmer.rice.max} · ${label}`)} />
          </span>
          <span className="muted small">{t.farmer.rice.worstYears(st.worst_years.join(', '))}</span>
        </p>
      )}
      <p className={s.rowNote}>
        {t.farmer.rice.yearsCount(st.years_count)} · {pick(st.scope)}
      </p>
      {st.model_status === 'not_modeled' && <p className={s.rowNote}>{t.science.notModeled}</p>}
      {st.model_status === 'not_shown' && <p className={s.rowNote}>{t.science.modelHidden}</p>}
    </div>
  );
}

function WeatherRow({ plan, res, refs, highlight }: Ctx & { highlight: boolean }) {
  const t = useT();
  const pick = usePick();
  const rice = plan.stability ?? [];
  const nonRice = plan.calendar.filter((c) => !rice.some((st) => st.crop_key === c.crop_key));
  return (
    <Row
      hook={`card-${plan.id}-row-weather`}
      icon="sun"
      title={t.farmer.rows.weather}
      note={plan.exposure.length ? t.farmer.rows.weatherNote : undefined}
      highlight={highlight}
    >
      {plan.exposure.length > 0 && (
        <YearsFold id={`card-${plan.id}-weather-years`}>
          <ShareTable plan={plan} codes={WEATHER_RULES} rules={res.rules} refs={refs} />
        </YearsFold>
      )}
      {rice.length > 0 && (
        <div className={s.sub}>
          <p className={s.subHead}>{t.farmer.rows.rice}</p>
          {rice.map((st) => (
            <RiceBlock key={st.crop_key} st={st} refs={refs} />
          ))}
          <p className={s.rowNote}>{t.farmer.rice.nsoCredit}</p>
        </div>
      )}
      {nonRice.length > 0 && (
        <p className={s.rowNote}>
          {nonRice.map((c) => pick(c.crop)).join(', ')}: {t.farmer.rice.noData}
        </p>
      )}
    </Row>
  );
}

function WaterRow({ plan, res, refs, highlight }: Ctx & { highlight: boolean }) {
  const t = useT();
  const pick = usePick();
  return (
    <Row hook={`card-${plan.id}-row-water`} icon="drop" title={t.farmer.rows.water} highlight={highlight} target>
      {plan.exposure.length > 0 && (
        <YearsFold id={`card-${plan.id}-water-years`}>
          <ShareTable plan={plan} codes={DROUGHT_RULES} rules={res.rules} refs={refs} />
        </YearsFold>
      )}
      <ul className={s.kv}>
        {plan.calendar.map((c) => {
          const facts = plan.water.filter((w) => w.crop_key === c.crop_key);
          const lifted = tcvnSharedNote(facts);
          return [
            lifted && (
              <li key={`${c.crop_key}-note`} className={s.waterNote}>
                {pick(c.crop)}: {pick(lifted)}
              </li>
            ),
            ...facts.map((w, i) => (
              <li key={`${c.crop_key}-${i}`}>
                <span>
                  {pick(c.crop)} · {w.measure === 'not_listed' ? t.common.notListed : t.farmer.waterLead[w.measure]}
                </span>
                <span className={s.kvVals}>
                  {w.value && (
                    <SourceValue
                      {...refs.value(
                        w.value,
                        `${t.farmer.waterLead[w.measure === 'not_listed' ? 'to_apply' : w.measure]} · ${pick(c.crop)}`,
                      )}
                    />
                  )}
                  {w.scope && <span className="muted small">{pick(w.scope)}</span>}
                  {w.note && !(lifted && w.measure === 'to_apply') && (
                    <span className="muted small">{pick(w.note)}</span>
                  )}
                </span>
              </li>
            )),
          ];
        })}
      </ul>
      {plan.exposure.length > 0 && (
        <div className={s.sub}>
          <p className={s.subHead}>{t.farmer.rows.soil}</p>
          <ul className={s.kv}>
            {plan.exposure.flatMap((c) =>
              c.per_year.map((y) => (
                <li key={`${c.crop_key}-${y.year}`}>
                  <span>
                    {pick(c.crop)} · {y.year}
                  </span>
                  <span className={s.kvVals}>
                    <NumberOr
                      v={y.soil_wetness.value}
                      label={`${t.farmer.rows.soil} · ${pick(c.crop)} · ${y.year}`}
                      refs={refs}
                    />
                    <span className="muted small">{t.farmer.soilNormal}</span>
                    <NumberOr
                      v={y.soil_wetness.normal}
                      label={`${t.farmer.soilNormal} · ${pick(c.crop)}`}
                      refs={refs}
                    />
                  </span>
                </li>
              )),
            )}
          </ul>
          <p className={s.rowNote}>{t.farmer.rows.soilNote}</p>
        </div>
      )}
      <p className={s.rowNote}>{t.farmer.rows.waterNote}</p>
    </Row>
  );
}

function LandRow({ plan, refs, highlight }: Omit<Ctx, 'res'> & { highlight: boolean }) {
  const t = useT();
  const pick = usePick();
  const { crops_in_year: crops, living_days: days, legume } = plan.land;
  const why = (ids: string[], name: string) => <SourceValue {...refs.sources(ids, t.farmer.principle, name)} />;
  return (
    <Row
      hook={`card-${plan.id}-row-land`}
      icon="sprout"
      title={t.farmer.rows.land}
      note={legume.present ? t.farmer.legumeNote : undefined}
      highlight={highlight}
    >
      <ul className={s.checks}>
        <li>
          {t.farmer.cropsInYear}: <NumberOr v={crops.value} label={t.farmer.cropsInYear} refs={refs} />
          {why(crops.principle_source_ids, t.farmer.cropsInYear)}
        </li>
        <li>
          {t.farmer.livingDays}: <NumberOr v={days.value} label={t.farmer.livingDays} refs={refs} />
          {why(days.principle_source_ids, t.farmer.livingDays)}
        </li>
        <li className={s.legume}>
          {legume.present ? (
            <>
              <Icon name="check" size={16} strokeWidth={2.4} />
              {t.farmer.legumeYes}: {legume.crops.map(pick).join(', ')}
            </>
          ) : (
            t.farmer.legumeNo
          )}
          {why(legume.principle_source_ids, t.farmer.legumeYes)}
        </li>
      </ul>
    </Row>
  );
}

/** The card's money total, or the P-03 text, and a pointer to the water row (D-172); no new value: the money is the
 * money row's own value with its source, and the water line names no number, since one TCVN row would hide the other
 * region (D-68) and TCVN and FAO are never combined (D-64). */
function Summary({ plan, refs }: { plan: Plan; refs: ApiRefs }) {
  const t = useT();
  const pick = usePick();
  const m = plan.money;
  const textIds = plan.calendar.flatMap((c) => c.source_ids);
  const water = `card-${plan.id}-row-water`;
  return (
    <div className={s.summary}>
      {m.total ? (
        <p>
          {t.farmer.rows.money}:{' '}
          <SourceValue {...refs.value(m.total, t.farmer.ourSum)}>{refs.number(m.total)}</SourceValue>{' '}
          {refs.unit(m.total)} · {t.farmer.ourSum}
        </p>
      ) : (
        m.text_only && (
          <p>
            {t.farmer.rows.money}: <SourceValue {...refs.sources(textIds, pick(m.text_only), t.farmer.rows.money)} />
          </p>
        )
      )}
      <a
        href={`#${water}`}
        className={s.summaryLink}
        onClick={(e) => {
          e.preventDefault();
          const row = document.getElementById(water);
          row?.scrollIntoView({ block: 'start' });
          row?.focus({ preventScroll: true });
        }}
      >
        {t.farmer.summaryWater(t.farmer.rows.water)}
      </a>
    </div>
  );
}

function CardHead({ plan, refs }: { plan: Plan; refs: ApiRefs }) {
  const t = useT();
  const pick = usePick();
  return (
    <header className={`${s.head} surface-forest`} data-testid={`card-${plan.id}-row-header`}>
      <p className={s.kicker}>
        {plan.is_usual && <span className={s.currentTag}>{t.farmer.current}</span>}
        <span>{pick(plan.name)}</span>
      </p>
      <h2 id={`title-${plan.id}`} className={s.chain}>
        {plan.calendar.map((c, i) => (
          <span key={c.crop_key} className={s.link}>
            {i > 0 && (
              <span className={s.arrow} aria-hidden="true">
                →
              </span>
            )}
            <i
              className={s.dot}
              style={{ background: FAMILY_DOT[CROP_FAMILY[c.crop_id] ?? 'other'] }}
              aria-hidden="true"
            />
            {pick(c.crop)}
          </span>
        ))}
      </h2>
      <Summary plan={plan} refs={refs} />
    </header>
  );
}

type Explained =
  { status: 'loading' } | { status: 'ok'; text: string } | { status: 'error'; why: 'refused' | 'busy' | 'failed' };

/** The "explain simply" button of one why part (FR-15): the server rewords the text it shows itself (D-165); the
 * reply is marked as AI-generated (R-H15) and is dropped when the language changes. */
function ExplainPart({ answers, plan, field }: { answers: CompareRequest; plan: PlanId; field: WhyPart }) {
  const t = useT();
  const { lang } = useSettings();
  const [got, setGot] = useState<{ lang: Lang; reply: Explained } | null>(null);
  const reply = got?.lang === lang ? got.reply : null;
  const loading = reply?.status === 'loading';
  const ask = async () => {
    setGot({ lang, reply: { status: 'loading' } });
    try {
      const res = await explainSimply({ answers, plan, field, lang });
      setGot({ lang, reply: { status: 'ok', text: res.text } });
    } catch (e) {
      const status = e instanceof ApiError ? e.status : null;
      setGot({
        lang,
        reply: { status: 'error', why: status === 502 ? 'refused' : status === 503 ? 'busy' : 'failed' },
      });
    }
  };
  return (
    <div className={s.explain}>
      {reply?.status !== 'ok' && (
        <button
          type="button"
          className={s.foldButton}
          aria-disabled={loading || undefined}
          onClick={loading ? undefined : ask}
        >
          <Icon name="spark" size={18} />
          {loading ? t.farmer.explain.loading : t.farmer.explain.button}
          <span className="visually-hidden">: {t.farmer.whyParts[field]}</span>
        </button>
      )}
      <div role="status" aria-live="polite">
        {reply?.status === 'ok' && (
          <div className={s.explainReply}>
            <p className={s.rowNote}>{t.farmer.explain.aiLabel}</p>
            <p>{displayUnit(reply.text)}</p>
          </div>
        )}
        {reply?.status === 'error' && <p className={s.rowNote}>{t.farmer.explain[reply.why]}</p>}
      </div>
    </div>
  );
}

/** The risks, always open, then the four reasons of the API's Why behind a disclosure (UI-UX-SPEC section 9). */
function WhyRows({ plan, refs, answers, explain }: Omit<Ctx, 'res'> & { answers: CompareRequest; explain: boolean }) {
  const t = useT();
  const pick = usePick();
  const { why } = plan;
  return (
    <>
      <Row hook={`card-${plan.id}-row-checks`} icon="alert" title={t.farmer.rows.checks}>
        {why.risks.length ? (
          <ul className={s.risks}>
            {why.risks.map((r) => (
              <li key={r.text.en}>
                <span>{pick(r.text)}</span>
                {r.source_ids.length > 0 && (
                  <SourceValue {...refs.sources(r.source_ids, t.common.source, t.farmer.rows.checks)} />
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className={s.why}>{t.farmer.noneListed}</p>
        )}
        <p className={s.why}>{t.farmer.localReview}</p>
      </Row>
      <details className={s.more}>
        <summary>
          <Icon name="question" size={18} />
          {t.farmer.rows.why}
          <Icon name="chevronDown" size={18} />
        </summary>
        <Row hook={`card-${plan.id}-row-why`} icon="question" title={t.farmer.rows.why}>
          {(['why', 'evidence', 'benefits', 'gaps'] as const).map((k) => (
            <div key={k}>
              <p className={s.why}>
                <strong>{t.farmer.whyParts[k]}: </strong>
                {displayUnit(pick(why[k]))}
              </p>
              {explain && <ExplainPart answers={answers} plan={plan.id} field={k} />}
            </div>
          ))}
        </Row>
      </details>
    </>
  );
}

export function PlanCard({
  plan,
  res,
  priority,
  focused,
  explain = false,
  onShare,
}: {
  plan: Plan;
  res: CompareResponse;
  priority: Priority;
  focused?: boolean;
  /** The server has "explain simply" on (FR-15: off by default). */
  explain?: boolean;
  onShare: (plan: Plan) => Promise<boolean>;
}) {
  const t = useT();
  const refs = useApiRefs(res.sources, res.rules);
  const [shareMsg, setShareMsg] = useState('');
  const hasDates = plan.calendar.some((c) => c.sow_from !== null);
  return (
    <article
      id={`the-${plan.id}`}
      data-testid={`card-${plan.id}`}
      className={[s.card, focused ? s.focused : ''].join(' ')}
      aria-labelledby={`title-${plan.id}`}
    >
      <CardHead plan={plan} refs={refs} />
      <div className={s.body}>
        <div data-testid={`card-${plan.id}-row-calendar`}>
          {hasDates ? (
            <MonthBar plan={plan} refs={refs} />
          ) : (
            <p className={s.noCal}>
              <Icon name="calendar" size={18} />
              {t.farmer.p03NoCalendar}
            </p>
          )}
        </div>
        <MoneyRow plan={plan} res={res} refs={refs} highlight={priority === 'income'} />
        <WeatherRow plan={plan} res={res} refs={refs} highlight={priority === 'stability'} />
        <WaterRow plan={plan} res={res} refs={refs} highlight={priority === 'water'} />
        <LandRow plan={plan} refs={refs} highlight={priority === 'land'} />
        <WhyRows plan={plan} refs={refs} answers={res.request} explain={explain} />
      </div>
      <footer className={s.foot}>
        {/* the four warnings stay inside the card, so a screenshot of one card keeps them (H17, T16) */}
        <p>{t.farmer.trialNote}</p>
        <p>{plan.money.price_year ? t.farmer.priceYear(plan.money.price_year) : t.farmer.priceYearNotStated}</p>
        <p>{t.common.notForecast}</p>
        <p>{t.common.support}</p>
        <div className={s.shareRow} data-testid={`card-${plan.id}-row-share`}>
          <button
            type="button"
            className={s.share}
            onClick={async () => setShareMsg((await onShare(plan)) ? t.farmer.shareCopied : t.farmer.shareFailed)}
          >
            <Icon name="share" size={18} />
            {t.farmer.share}
          </button>
          <span className={s.shareMsg} role="status" aria-live="polite">
            {shareMsg}
          </span>
        </div>
      </footer>
    </article>
  );
}
