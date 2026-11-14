import { StepShell, useFarmer } from './FarmerLayout';
import { ButtonLink } from '../../design-system/Button';
import { Icon } from '../../design-system/Icon';
import { api } from '../../api';
import type { PastYearsResponse, YearRow as Row } from '../../types';
import { RULES } from '../../domain/hazards';
import { MAX_YEARS, toggleYear } from '../../domain/farmerState';
import { useApi } from '../../hooks/useApi';
import { DataLine } from '../provenance/DataLine';
import { LoadState } from '../provenance/LoadState';
import { SourceValue } from '../provenance/SourceValue';
import { useApiRefs } from '../provenance/useApiRefs';
import { useFormat, usePick, useT } from '../../app/settings';
import s from './farmer.module.css';

// the bar only draws the API's whole-percent share; the number itself is the source button next to it
const barWidth = (value: string) => `${Math.max(2, Math.min(100, Number(value)))}%`;

function YearRow({ row, res }: { row: Row; res: PastYearsResponse }) {
  const t = useT();
  const pick = usePick();
  const refs = useApiRefs(res.sources, res.rules);
  return (
    <article className={s.yearCard} aria-labelledby={`y-${row.year}`}>
      <header className={s.yearHead}>
        <h2 id={`y-${row.year}`} className={s.yearNum}>{row.year}</h2>
        <p className={s.yearSub}>{t.farmer.yearRowLabel}</p>
      </header>
      <ul className={s.hzList}>
        {res.rules.map((rule) => {
          const v = row.shares[rule.code];
          return (
            <li key={rule.code} className={s.hz} data-rule={rule.code}>
              <span className={s.hzName}><i style={{ background: RULES[rule.code].color }} />{pick(rule.label)}</span>
              <span className={s.bar} aria-hidden="true">{v && <i style={{ width: barWidth(v.value), background: RULES[rule.code].color }} />}</span>
              {v ? <SourceValue {...refs.share(rule.code, v, `${pick(rule.label)} · ${row.year}`)} /> : <span className="muted">{t.common.notAvailable}</span>}
            </li>
          );
        })}
      </ul>
    </article>
  );
}

function Years({ res }: { res: PastYearsResponse }) {
  const t = useT();
  const f = useFormat();
  const { state, update } = useFarmer();
  const offered = res.years.map((y) => y.year);
  const picked = state.years.filter((y) => offered.includes(y));
  return (
    <>
      <div className={s.yearGridHead}>
        <span>{t.farmer.yearsPicked(picked.length)}</span>
        <span className="muted small">{f.n(picked.length)}/{MAX_YEARS}</span>
      </div>
      <div className={s.yearGrid} role="group" aria-label={t.farmer.yearsTitle}>
        {res.years.map((row) => {
          const on = picked.includes(row.year);
          const dry = row.shares.drought_rain_any2;
          return (
            <button key={row.year} type="button" aria-pressed={on} className={[s.yearChip, on ? s.on : ''].join(' ')}
              data-testid={`year-${row.year}`}
              onClick={() => update({ years: toggleYear(picked, row.year) })}
              disabled={!on && picked.length >= MAX_YEARS}>
              <span className="num">{row.year}</span>
              {dry && <i aria-hidden="true" style={{ width: barWidth(dry.value) }} />}
            </button>
          );
        })}
      </div>
      <p className="muted small">{t.farmer.yearChipLegend}</p>
      {picked.length ? (
        <div className={s.yearCards}>
          {res.years.filter((row) => picked.includes(row.year)).map((row) => <YearRow key={row.year} row={row} res={res} />)}
        </div>
      ) : (
        <p className={s.note}>{t.farmer.noYears}</p>
      )}
      <details className={s.limits}>
        <summary>{t.farmer.limitsTitle}</summary>
        <ul>
          <li>{t.farmer.cellsNote(res.n_cells)}</li>
          {t.farmer.limits.map((l) => <li key={l}>{l}</li>)}
        </ul>
      </details>
    </>
  );
}

export function YearsStep() {
  const t = useT();
  const { state, search } = useFarmer();
  const [res, retry] = useApi(api.pastYears, 'past-years');
  const ready = state.years.length > 0 && res.status === 'ok';
  return (
    <StepShell
      step={2}
      title={t.farmer.yearsTitle}
      help={t.farmer.yearsHelp}
      actions={
        <ButtonLink to={{ pathname: '/nong-dan/uu-tien', search }} size="lg" block icon="arrowRight"
          aria-disabled={!ready} onClick={(e) => { if (!ready) e.preventDefault(); }}
          className={!ready ? s.disabledLink : undefined}>
          {t.common.next}
        </ButtonLink>
      }
    >
      <p className={s.notForecast}><Icon name="alert" size={18} />{t.common.notForecast}</p>
      {res.status === 'ok' ? <><DataLine sources={res.data.sources} className="muted small" /><Years res={res.data} /></> : <LoadState state={res} retry={retry} />}
    </StepShell>
  );
}
