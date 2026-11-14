import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { StepShell, useFarmer } from './FarmerLayout';
import { PlanCard } from './PlanCard';
import { ButtonLink } from '../../design-system/Button';
import { Icon } from '../../design-system/Icon';
import { CROPS, PLANS, type Plan } from '../../domain/plans';
import { serializeFarmerState } from '../../domain/farmerState';
import { usePick, useT } from '../../app/settings';
import s from './farmer.module.css';

/** Builds the absolute link that opens exactly this card with the current answers. */
function cardUrl(search: URLSearchParams) {
  const base = `${window.location.origin}${window.location.pathname}`;
  return `${base}#/nong-dan/phuong-an?${search.toString()}`;
}

export function PlansStep() {
  const t = useT();
  const pick = usePick();
  const { state, update, search } = useFarmer();
  const [focused, setFocused] = useState(state.plan);

  useEffect(() => {
    if (!state.plan) return;
    const el = document.getElementById(`the-${state.plan}`);
    el?.scrollIntoView({ block: 'start' });
    const timer = window.setTimeout(() => setFocused(null), 2600);
    return () => window.clearTimeout(timer);
    // only when the page opens with a card in the link
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const share = useCallback(async (plan: Plan) => {
    const url = cardUrl(serializeFarmerState({ ...state, plan: plan.id }));
    const title = plan.textOnly ? pick(plan.textOnly.sequence) : plan.crops.map((c) => pick(CROPS[c.crop].name)).join(' → ');
    try {
      if (navigator.share && window.matchMedia('(pointer: coarse)').matches) {
        await navigator.share({ title: `Miaudow · ${title}`, text: t.farmer.shareHelp, url });
        return true;
      }
      await navigator.clipboard.writeText(url);
      return true;
    } catch {
      return false;
    }
  }, [state, pick, t]);

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
      {state.land === 'reliable' && <p className={s.note}><Icon name="alert" size={20} />{t.farmer.wetNote}</p>}

      <nav className={s.jump} aria-label={t.farmer.jumpTo}>
        {PLANS.map((p) => (
          <a key={p.id} href={`#the-${p.id}`} onClick={(e) => { e.preventDefault(); document.getElementById(`the-${p.id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' }); update({ plan: p.id }); }}>
            {p.current ? t.farmer.current : p.id.toUpperCase()}
            <span className="muted"> · {p.textOnly ? pick(p.textOnly.sequence).split(' – ')[1] : pick(CROPS[p.crops[0]?.crop ?? 'rice'].name)}</span>
          </a>
        ))}
      </nav>

      <div className={s.cards}>
        {PLANS.map((p) => (
          <PlanCard key={p.id} plan={p} years={state.years} priority={state.priority} focused={focused === p.id} onShare={share} />
        ))}
      </div>

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
      <p className={s.support}><Icon name="user" size={20} />{t.common.support}</p>
    </StepShell>
  );
}
