import { StepShell, useFarmer } from './FarmerLayout';
import { ButtonLink } from '../../design-system/Button';
import { Icon } from '../../design-system/Icon';
import { YEARS } from '../../data';
import { FARMER_RULES, RULES, yearShare } from '../../domain/hazards';
import { riceYear } from '../../domain/rice';
import { MAX_YEARS, toggleYear } from '../../domain/farmerState';
import { SourceValue } from '../provenance/SourceValue';
import { useRefs } from '../provenance/useRefs';
import { useFormat, usePick, useT } from '../../app/settings';
import s from './farmer.module.css';

function YearRow({ year }: { year: number }) {
  const t = useT();
  const pick = usePick();
  const f = useFormat();
  const refs = useRefs();
  const rice = riceYear('spring', year);
  return (
    <article className={s.yearCard} aria-labelledby={`y-${year}`}>
      <header className={s.yearHead}>
        <h2 id={`y-${year}`} className={s.yearNum}>{year}</h2>
        <p className={s.yearSub}>{t.farmer.yearRowLabel}</p>
      </header>
      <ul className={s.hzList}>
        {FARMER_RULES.map((rule) => {
          const v = yearShare(rule, year);
          return (
            <li key={rule} className={s.hz}>
              <span className={s.hzName}><i style={{ background: RULES[rule].color }} />{pick(RULES[rule].name)}</span>
              <span className={s.bar} aria-hidden="true"><i style={{ width: `${Math.max(2, v * 100)}%`, background: RULES[rule].color }} /></span>
              <SourceValue {...refs.share(rule, year, v)} />
            </li>
          );
        })}
      </ul>
      <p className={s.riceLine}>
        <span>{t.farmer.riceLine}</span>
        {rice.actual === null ? <span className="muted">{t.farmer.riceNone}</span> : <SourceValue {...refs.rice('spring', year, rice.actual)}>{f.signedPct(rice.actual)}</SourceValue>}
      </p>
    </article>
  );
}

export function YearsStep() {
  const t = useT();
  const f = useFormat();
  const { state, update, search } = useFarmer();
  const picked = state.years;
  return (
    <StepShell
      step={2}
      title={t.farmer.yearsTitle}
      help={t.farmer.yearsHelp}
      actions={
        <ButtonLink to={{ pathname: '/nong-dan/uu-tien', search }} size="lg" block icon="arrowRight"
          aria-disabled={!picked.length} onClick={(e) => { if (!picked.length) e.preventDefault(); }}
          className={!picked.length ? s.disabledLink : undefined}>
          {t.common.next}
        </ButtonLink>
      }
    >
      <p className={s.notForecast}><Icon name="alert" size={18} />{t.common.notForecast}</p>
      <div className={s.yearGridHead}>
        <span>{t.farmer.yearsPicked(picked.length)}</span>
        <span className="muted small">{f.n(picked.length)}/{MAX_YEARS}</span>
      </div>
      <div className={s.yearGrid} role="group" aria-label={t.farmer.yearsTitle}>
        {YEARS.map((y) => {
          const on = picked.includes(y);
          const dry = yearShare('drought_rain_any2', y);
          return (
            <button key={y} type="button" aria-pressed={on} className={[s.yearChip, on ? s.on : ''].join(' ')}
              onClick={() => update({ years: toggleYear(picked, y) })}
              disabled={!on && picked.length >= MAX_YEARS}>
              <span className="num">{y}</span>
              <i aria-hidden="true" style={{ width: `${Math.max(8, dry * 100)}%` }} />
            </button>
          );
        })}
      </div>
      <p className="muted small">{t.farmer.yearChipLegend}</p>
      {picked.length ? (
        <div className={s.yearCards}>{picked.map((y) => <YearRow key={y} year={y} />)}</div>
      ) : (
        <p className={s.note}>{t.farmer.noYears}</p>
      )}
      <details className={s.limits}>
        <summary>{t.farmer.limitsTitle}</summary>
        <ul>{t.farmer.limits.map((l) => <li key={l}>{l}</li>)}</ul>
      </details>
    </StepShell>
  );
}
