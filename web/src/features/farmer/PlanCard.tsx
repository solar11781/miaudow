import { useState, type ReactNode } from 'react';
import { livingDays } from '../../domain/calendar';
import { cropShare, cropShareRange, soilReading } from '../../domain/hazards';
import { CROPS, planCropCount, planHasLegume, planProfitMillion, type Plan } from '../../domain/plans';
import { riceSummary } from '../../domain/rice';
import type { Priority } from '../../domain/farmerState';
import type { RiceSeason } from '../../data';
import { SOURCES } from '../../domain/sources';
import { Icon, type IconName } from '../../design-system/Icon';
import { MonthBar } from './MonthBar';
import { SourceValue } from '../provenance/SourceValue';
import { useRefs } from '../provenance/useRefs';
import { useFormat, usePick, useT } from '../../app/settings';
import s from './PlanCard.module.css';

const FAMILY_DOT: Record<string, string> = { rice: '#6e9e3c', legume: '#c9962e', maize: '#d8c03c', root: '#c06a44', other: '#9a73a0' };
const CARD_RULES = ['drought_rain_any2', 'heat', 'heavy_rain'] as const;

function Row({ icon, title, note, highlight, children }: { icon: IconName; title: string; note?: string; highlight?: boolean; children: ReactNode }) {
  const t = useT();
  return (
    <section className={[s.row, highlight ? s.hl : ''].join(' ')}>
      <h3 className={s.rowHead}>
        <Icon name={icon} size={18} />
        {title}
        {highlight && <span className={s.prioTag}><Icon name="check" size={14} strokeWidth={2.6} />{t.farmer.yourPriority}</span>}
      </h3>
      {children}
      {note && <p className={s.rowNote}>{note}</p>}
    </section>
  );
}

function RiceRows({ seasons, years }: { seasons: RiceSeason[]; years: number[] }) {
  const t = useT();
  const f = useFormat();
  const refs = useRefs();
  return (
    <div className={s.riceRows}>
      {seasons.map((season) => {
        const sum = riceSummary(season, years);
        const one = sum.years[0];
        return (
          <p key={season} className={s.riceLine}>
            <span className={s.riceSeason}>{t.science.seasons[season]}</span>
            {sum.min && sum.max ? (
              <span className={s.riceVals}>
                <SourceValue {...refs.rice(season, sum.min.year, sum.min.actual as number)} />
                <span className="muted">→</span>
                <SourceValue {...refs.rice(season, sum.max.year, sum.max.actual as number)} />
                <span className="muted small">{t.farmer.riceVs(f.signedPct(sum.min.actual as number), f.signedPct(sum.max.actual as number), sum.min.year)}</span>
              </span>
            ) : one ? <SourceValue {...refs.rice(season, one.year, one.actual as number)} /> : <span className="muted">{t.common.noData}</span>}
          </p>
        );
      })}
    </div>
  );
}

function MoneyRow({ plan, highlight }: { plan: Plan; highlight: boolean }) {
  const t = useT();
  const pick = usePick();
  const f = useFormat();
  const refs = useRefs();
  const total = planProfitMillion(plan);
  return (
    <Row icon="coin" title={t.farmer.rows.money} note={plan.crops.length ? t.farmer.rows.moneyNote : undefined} highlight={highlight}>
      {total !== null && (
        <>
          <div className={s.money}><SourceValue size="xl" {...refs.planProfit(plan, total)}>{f.n(total, 1)}</SourceValue><span className={s.unit}>{t.common.millionPerHa}</span></div>
          <ul className={s.cropMoney}>
            {plan.crops.map((c) => (
              <li key={c.key}><span>{pick(CROPS[c.crop].name)}</span><SourceValue {...refs.cropProfit(c)}>{f.million(c.profit)}</SourceValue></li>
            ))}
          </ul>
        </>
      )}
      {total === null && plan.textOnly && (
        <SourceValue sourceId="p03" kind="study" value={pick(plan.textOnly.profitNote)} label={t.farmer.rows.money} />
      )}
    </Row>
  );
}

function WeatherRow({ plan, years, highlight }: { plan: Plan; years: number[]; highlight: boolean }) {
  const t = useT();
  const pick = usePick();
  const f = useFormat();
  const refs = useRefs();
  const riceSeasons: RiceSeason[] = plan.id === 'p03' ? ['spring', 'summer_autumn'] : plan.crops.some((c) => c.crop === 'rice') ? ['spring'] : [];
  return (
    <Row icon="sun" title={t.farmer.rows.weather} note={plan.crops.length ? t.farmer.rows.weatherNote : undefined} highlight={highlight}>
      {plan.crops.length > 0 && years.length > 0 && (
        <div className={s.tableWrap} tabIndex={0} role="region" aria-label={t.farmer.rows.weather}>
          <table className={s.wTable}>
            <thead><tr><th scope="col">{t.farmer.crop}</th><th scope="col">{t.farmer.drought}</th><th scope="col">{t.farmer.heat}</th><th scope="col">{t.farmer.rain}</th></tr></thead>
            <tbody>
              {plan.crops.map((c) => (
                <tr key={c.key}>
                  <th scope="row">{pick(CROPS[c.crop].name)}</th>
                  {CARD_RULES.map((rule) => {
                    const r = cropShareRange(c.key, rule, years);
                    if (!r) return <td key={rule}>—</td>;
                    const worst = years.find((y) => cropShare(c.key, rule, y) === r.max) ?? (years[0] as number);
                    const label = r.min === r.max ? f.pct(r.min) : `${f.n(r.min * 100)}–${f.pct(r.max)}`;
                    return <td key={rule}><SourceValue {...refs.share(rule, worst, r.max, c)}>{label}</SourceValue></td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {riceSeasons.length > 0 && (
        <div className={s.sub}>
          <p className={s.subHead}>{t.farmer.rows.rice}</p>
          <RiceRows seasons={riceSeasons} years={years} />
        </div>
      )}
    </Row>
  );
}

function WaterRow({ plan, years, highlight }: { plan: Plan; years: number[]; highlight: boolean }) {
  const t = useT();
  const pick = usePick();
  const f = useFormat();
  const refs = useRefs();
  const unique = [...new Map(plan.crops.map((c) => [c.crop, c])).values()];
  return (
    <Row icon="drop" title={t.farmer.rows.water} note={t.farmer.rows.waterNote} highlight={highlight}>
      <ul className={s.kv}>
        {unique.map((c) => {
          const info = CROPS[c.crop] as { tcvn?: { vi: string; en: string }; fao?: string };
          return (
            <li key={c.key}>
              <span>{pick(CROPS[c.crop].name)}</span>
              <span className={s.kvVals}>
                {info.tcvn ? <SourceValue {...refs.tcvn(c, pick(info.tcvn))} /> : <span className="muted small">{t.common.notListed}</span>}
                {info.fao && <SourceValue {...refs.fao(c, info.fao)} />}
              </span>
            </li>
          );
        })}
      </ul>
      <div className={s.sub}>
        <p className={s.subHead}>{t.farmer.rows.soil}</p>
        <ul className={s.kv}>
          {plan.crops.map((c) => {
            const sr = soilReading(c.key, years);
            if (!sr) return null;
            const mean = sr.values.reduce((a, b) => a + b, 0) / sr.values.length;
            return (
              <li key={c.key}>
                <span>{pick(CROPS[c.crop].name)}</span>
                <SourceValue {...refs.soil(c, f.n(mean, 2), f.n(sr.normal, 2))}>{t.farmer.soilVs(f.n(mean, 2), f.n(sr.normal, 2))}</SourceValue>
              </li>
            );
          })}
        </ul>
        <p className={s.rowNote}>{t.farmer.rows.soilNote}</p>
      </div>
    </Row>
  );
}

function LandRow({ plan, highlight }: { plan: Plan; highlight: boolean }) {
  const t = useT();
  return (
    <Row icon="sprout" title={t.farmer.rows.land} note={t.farmer.legumeNote} highlight={highlight}>
      <ul className={s.checks}>
        <li><SourceValue sourceId="p02" kind="derived" value={t.farmer.cropsInYear(planCropCount(plan))} label={t.farmer.rows.land} chain={['p02']} /></li>
        <li><SourceValue sourceId="p02" kind="derived" value={t.farmer.livingDays(livingDays(plan))} label={t.farmer.rows.land}
          detail={plan.crops.map((c) => `${c.sow} → ${c.harvest}`).join(' ∪ ')} chain={['p02']} /></li>
        <li className={s.legume}>{planHasLegume(plan) ? <><Icon name="check" size={16} strokeWidth={2.4} />{t.farmer.legumeYes}</> : t.farmer.legumeNo}</li>
      </ul>
    </Row>
  );
}

function CardHead({ plan }: { plan: Plan }) {
  const t = useT();
  const pick = usePick();
  const kicker = plan.current ? (plan.source === 'p03' ? t.farmer.describedByP03 : t.farmer.describedByP02) : t.farmer.trialPlan(plan.id.toUpperCase());
  return (
    <header className={`${s.head} surface-forest`}>
      <p className={s.kicker}>
        {plan.current && <span className={s.currentTag}>{t.farmer.current}</span>}
        <span>{kicker}</span>
      </p>
      <h2 id={`title-${plan.id}`} className={s.chain}>
        {plan.textOnly ? pick(plan.textOnly.sequence) : plan.crops.map((c, i) => (
          <span key={c.key} className={s.link}>
            {i > 0 && <span className={s.arrow} aria-hidden="true">→</span>}
            <i className={s.dot} style={{ background: FAMILY_DOT[CROPS[c.crop].family] }} aria-hidden="true" />
            {pick(CROPS[c.crop].name)}
          </span>
        ))}
      </h2>
      <p className={s.source}>{SOURCES[plan.source].short}</p>
    </header>
  );
}

export function PlanCard({ plan, years, priority, focused, onShare }: {
  plan: Plan; years: number[]; priority: Priority | null; focused?: boolean; onShare: (plan: Plan) => Promise<boolean>;
}) {
  const t = useT();
  const pick = usePick();
  const [shareMsg, setShareMsg] = useState('');
  const hasCrops = plan.crops.length > 0;
  return (
    <article id={`the-${plan.id}`} className={[s.card, focused ? s.focused : ''].join(' ')} aria-labelledby={`title-${plan.id}`}>
      <CardHead plan={plan} />
      <div className={s.body}>
        {hasCrops ? <MonthBar plan={plan} /> : <p className={s.noCal}><Icon name="calendar" size={18} />{t.farmer.p03NoCalendar}</p>}
        <MoneyRow plan={plan} highlight={priority === 'income'} />
        <WeatherRow plan={plan} years={years} highlight={priority === 'stability'} />
        {hasCrops && <WaterRow plan={plan} years={years} highlight={priority === 'water'} />}
        {hasCrops && <LandRow plan={plan} highlight={priority === 'land'} />}
        <Row icon="alert" title={t.farmer.rows.checks}>
          <ul className={s.bullets}>{plan.checks.map((c) => <li key={c.vi}>{pick(c)}</li>)}</ul>
        </Row>
        <Row icon="question" title={t.farmer.rows.why}>
          <p className={s.why}>{plan.current ? t.farmer.whyCurrent : t.farmer.whyTrial}</p>
        </Row>
      </div>
      <footer className={s.foot}>
        <p>{t.farmer.cardFoot}</p>
        <div className={s.shareRow}>
          <button type="button" className={s.share} onClick={async () => setShareMsg((await onShare(plan)) ? t.farmer.shareCopied : t.farmer.shareFailed)}>
            <Icon name="share" size={18} />{t.farmer.share}
          </button>
          <span className={s.shareMsg} role="status" aria-live="polite">{shareMsg}</span>
        </div>
      </footer>
    </article>
  );
}
