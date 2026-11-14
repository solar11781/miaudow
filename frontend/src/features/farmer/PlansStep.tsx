import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { StepShell, useFarmer } from './FarmerLayout';
import { PlanCard } from './PlanCard';
import { ButtonLink } from '../../design-system/Button';
import { Icon } from '../../design-system/Icon';
import { api } from '../../api';
import type { CompareRequest, CompareResponse, Plan } from '../../types';
import { compareRequest, serializeFarmerState } from '../../domain/farmerState';
import { useApi } from '../../hooks/useApi';
import { DataLine } from '../provenance/DataLine';
import { LoadState } from '../provenance/LoadState';
import { usePick, useT } from '../../app/settings';
import s from './farmer.module.css';

/** Builds the absolute link that opens exactly this card with the current answers (the answers stay in the fragment). */
function cardUrl(search: URLSearchParams) {
  const base = `${window.location.origin}${window.location.pathname}`;
  return `${base}#/nong-dan/phuong-an?${search.toString()}`;
}

function Cards({ res }: { res: CompareResponse }) {
  const t = useT();
  const pick = usePick();
  const { state, update } = useFarmer();
  const [focused, setFocused] = useState(state.plan);

  useEffect(() => {
    if (!state.plan) return;
    const el = document.getElementById(`the-${state.plan}`);
    el?.scrollIntoView({ block: 'start' });
    const timer = window.setTimeout(() => setFocused(null), 2600);
    return () => window.clearTimeout(timer);
    // only when the cards first open with a card in the link
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const share = useCallback(async (plan: Plan) => {
    const url = cardUrl(serializeFarmerState({ ...state, plan: plan.id }));
    try {
      if (navigator.share && window.matchMedia('(pointer: coarse)').matches) {
        await navigator.share({ title: `Miaudow · ${pick(plan.name)}`, text: t.farmer.shareHelp, url });
        return true;
      }
      await navigator.clipboard.writeText(url);
      return true;
    } catch {
      return false;
    }
  }, [state, pick, t]);

  return (
    <>
      <DataLine sources={res.sources} className="muted small" />
      <nav className={s.jump} aria-label={t.farmer.jumpTo}>
        {res.plans.map((p) => (
          <a key={p.id} href={`#the-${p.id}`} onClick={(e) => { e.preventDefault(); document.getElementById(`the-${p.id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' }); update({ plan: p.id }); }}>
            {p.is_usual ? t.farmer.current : p.id.toUpperCase()}
            <span className="muted"> · {p.calendar.map((c) => pick(c.crop)).join(' → ')}</span>
          </a>
        ))}
      </nav>
      {/* the API's order is final: no sorting, filtering or ranking (H3) */}
      <div className={s.cards}>
        {res.plans.map((p) => (
          <PlanCard key={p.id} plan={p} res={res} priority={res.request.priority} focused={focused === p.id} onShare={share} />
        ))}
      </div>
    </>
  );
}

function Compare({ body }: { body: CompareRequest }) {
  const [res, retry] = useApi((signal) => api.compare(body, signal), JSON.stringify(body));
  return res.status === 'ok' ? <Cards res={res.data} /> : <LoadState state={res} retry={retry} />;
}

export function PlansStep() {
  const t = useT();
  const { state, search } = useFarmer();
  const [years, retryYears] = useApi(api.pastYears, 'past-years');
  // picked years are checked against the past-years response before any compare request (UI-UX-SPEC section 6b)
  const offered = years.status === 'ok' ? years.data.years.map((y) => y.year) : [];
  const body = years.status === 'ok' ? compareRequest({ ...state, years: state.years.filter((y) => offered.includes(y)) }) : null;
  return (
    <StepShell step={4} title={t.farmer.plansTitle} help={t.farmer.plansLead} wide>
      <div className={s.plansMeta}>
        <p className={s.notForecast}><Icon name="alert" size={18} />{t.common.notForecast}</p>
        <div className={s.pickedYears}>
          {state.years.map((y) => <span key={y} className={s.yearTag}>{y}</span>)}
          <Link to={{ pathname: '/nong-dan/nam', search }} className={s.editLink} viewTransition>{t.farmer.yearsTitle}</Link>
        </div>
        {state.priority && <p className={s.prioNow}><span className={s.prioSwatch} />{t.farmer.yourPriority}: <strong>{t.farmer.prios[state.priority].title}</strong></p>}
      </div>
      <p className={s.support}><Icon name="user" size={20} />{t.common.support}</p>
      {state.land === 'ask' && <p className={s.note}><Icon name="user" size={20} />{t.farmer.askNote}</p>}
      <p className={s.note}><Icon name="alert" size={20} />{t.farmer.trialNote}</p>

      {state.land === 'reliable' && <p className={s.note}><Icon name="alert" size={20} />{t.farmer.wetNote}</p>}
      {state.land !== 'reliable' && years.status === 'ok' && !body && (
        <p className={s.note}><Icon name="alert" size={20} />{t.farmer.needAnswers}{' '}
          <Link to={{ pathname: '/nong-dan/ruong', search }} className={s.editLink}>{t.farmer.restart}</Link>
        </p>
      )}
      {state.land !== 'reliable' && years.status !== 'ok' && <LoadState state={years} retry={retryYears} />}
      {body && <Compare body={body} />}

      <section className={s.officerBox} aria-labelledby="ask-officer">
        <h2 id="ask-officer" className="h3"><Icon name="user" size={20} /> {t.farmer.askOfficer}</h2>
        <ol>{t.farmer.officerQuestions.map((q) => <li key={q}>{q}</li>)}</ol>
        <div className="cluster">
          <ButtonLink to="/can-bo" variant="secondary" icon="arrowRight">{t.farmer.officerView}</ButtonLink>
          <ButtonLink to="/nong-dan/ruong" variant="ghost" leadingIcon="rotateL">
            {t.farmer.restart}
          </ButtonLink>
        </div>
      </section>
    </StepShell>
  );
}
