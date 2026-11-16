import { StepShell, useFarmer } from './FarmerLayout';
import { ButtonLink } from '../../design-system/Button';
import { Icon } from '../../design-system/Icon';
import { api } from '../../api';
import type { PastYearsResponse, YearRow as Row } from '../../types';
import { RULES } from '../../domain/hazards';
import { MAX_YEARS, toggleYear } from '../../domain/farmerState';
import { hardestYears } from '../../domain/hardYears';
import { useApi } from '../../hooks/useApi';
import { DataLine } from '../provenance/DataLine';
import { LoadState } from '../provenance/LoadState';
import { SourceValue } from '../provenance/SourceValue';
import { useProvenance } from '../provenance/ProvenanceProvider';
import { useApiRefs } from '../provenance/useApiRefs';
import { useEffect, useState } from 'react';
import { useFormat, usePick, useSettings, useT } from '../../app/settings';
import s from './farmer.module.css';

// the bar only draws the API's whole-percent share; the number itself is the source button next to it
const barWidth = (value: string) => `${Math.max(2, Math.min(100, Number(value)))}%`;

function YearRow({ row, res }: { row: Row; res: PastYearsResponse }) {
  const t = useT();
  const pick = usePick();
  const refs = useApiRefs(res.sources, res.rules);
  return (
    <article id={`year-card-${row.year}`} className={s.yearCard} aria-labelledby={`y-${row.year}`}>
      <header className={s.yearHead}>
        <h2 id={`y-${row.year}`} className={s.yearNum}>
          {t.farmer.yearHeading(row.year)}
        </h2>
        <p className={s.yearSub}>{t.farmer.yearRowLabel}</p>
      </header>
      <ul className={s.hzList}>
        {res.rules.map((rule) => {
          const v = row.shares[rule.code];
          return (
            <li key={rule.code} className={s.hz} data-rule={rule.code}>
              <span className={s.hzName}>
                <i style={{ background: RULES[rule.code].color }} />
                {pick(rule.label)}
              </span>
              <span className={s.bar} aria-hidden="true">
                {v && <i style={{ width: barWidth(v.value), background: RULES[rule.code].color }} />}
              </span>
              {v ? (
                <SourceValue {...refs.share(rule.code, v, `${pick(rule.label)} · ${row.year}`)} />
              ) : (
                <span className="muted">{t.common.notAvailable}</span>
              )}
            </li>
          );
        })}
      </ul>
    </article>
  );
}

/** UI-UX-SPEC section 8 item 2: one row per rule with a "?" button that opens the sheet in rule mode (H19). */
function Legend({ res }: { res: PastYearsResponse }) {
  const t = useT();
  const pick = usePick();
  const open = useProvenance();
  const refs = useApiRefs(res.sources, res.rules);
  return (
    <section className={s.legend} aria-labelledby="legend-title">
      <h2 id="legend-title" className={s.legendTitle}>
        {t.farmer.legendTitle}
      </h2>
      <ul>
        {res.rules.map((rule) => (
          <li key={rule.code} className={s.legendRow}>
            <span>{pick(rule.label)}</span>
            <button
              type="button"
              className={s.legendHelp}
              data-testid={`legend-${rule.code}`}
              aria-label={t.common.sourceFor(pick(rule.label))}
              onClick={() => open(refs.rule(rule))}
            >
              <Icon name="question" size={22} />
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Years({ res }: { res: PastYearsResponse }) {
  const t = useT();
  const f = useFormat();
  const { state, update } = useFarmer();
  const { calm } = useSettings();
  const offered = res.years.map((y) => y.year);
  const picked = state.years.filter((y) => offered.includes(y));
  const shown = picked.join(',');
  // the year just picked: its detail is brought on screen, clear of the sticky header and Next bar (scroll-margin)
  const [added, setAdded] = useState<number | null>(null);
  useEffect(() => {
    // the URL update lands after the tap, so this waits until the picked list holds the new year
    if (added === null || !shown.split(',').includes(String(added))) return;
    document
      .getElementById(`year-card-${added}`)
      ?.scrollIntoView({ block: 'nearest', behavior: calm ? 'auto' : 'smooth' });
  }, [added, calm, shown]);
  return (
    <>
      <div className={s.hardYears}>
        <button
          type="button"
          className={s.hardYearsButton}
          onClick={() => {
            const years = hardestYears(res);
            update({ years });
            setAdded(years[0] ?? null); // the first picked year comes on screen, so the tap is seen to do something
          }}
        >
          {t.farmer.hardYears}
        </button>
        <p className="muted small">{t.farmer.hardYearsNote}</p>
      </div>
      <div className={s.yearGridHead}>
        <span>{t.farmer.yearsPicked(picked.length)}</span>
        <span className="muted small">
          {f.n(picked.length)}/{MAX_YEARS}
        </span>
      </div>
      <div className={s.yearGrid} role="group" aria-label={t.farmer.yearsTitle}>
        {res.years.map((row) => {
          const on = picked.includes(row.year);
          const dry = row.shares.drought_rain_any2;
          return (
            <button
              key={row.year}
              type="button"
              aria-pressed={on}
              className={[s.yearChip, on ? s.on : ''].join(' ')}
              data-testid={`year-${row.year}`}
              onClick={() => {
                update({ years: toggleYear(picked, row.year) });
                setAdded(on ? null : row.year);
              }}
              disabled={!on && picked.length >= MAX_YEARS}
            >
              <span className="num">{row.year}</span>
              {dry && <i aria-hidden="true" style={{ width: barWidth(dry.value) }} />}
            </button>
          );
        })}
      </div>
      <p className="muted small">{t.farmer.yearChipLegend}</p>
      {picked.length ? (
        <div className={s.yearCards}>
          {res.years
            .filter((row) => picked.includes(row.year))
            .map((row) => (
              <YearRow key={row.year} row={row} res={res} />
            ))}
        </div>
      ) : (
        <p className={s.note}>{t.farmer.noYears}</p>
      )}
      <details className={`fold-arrow ${s.limits}`}>
        <summary>
          {t.farmer.limitsTitle}
          <Icon name="chevronDown" size={18} />
        </summary>
        <ul>
          <li>{t.farmer.cellsNote(res.n_cells)}</li>
          {t.farmer.limits.map((l) => (
            <li key={l}>{l}</li>
          ))}
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
        <ButtonLink
          to={{ pathname: '/nong-dan/uu-tien', search }}
          size="lg"
          block
          icon="arrowRight"
          aria-disabled={!ready}
          onClick={(e) => {
            if (!ready) e.preventDefault();
          }}
          className={!ready ? s.disabledLink : undefined}
        >
          {t.common.next}
        </ButtonLink>
      }
    >
      <p className={s.notForecast}>
        <Icon name="alert" size={18} />
        {t.common.notForecast}
      </p>
      {res.status === 'ok' ? (
        <>
          <DataLine sources={res.data.sources} className="muted small" />
          {/* the years are the farmer's task; the rule names are reference and come after them */}
          <Years res={res.data} />
          <Legend res={res.data} />
        </>
      ) : (
        <LoadState state={res} retry={retry} />
      )}
    </StepShell>
  );
}
