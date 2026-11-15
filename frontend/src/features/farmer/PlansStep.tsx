import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { StepShell, useFarmer } from './FarmerLayout';
import { PlanCard } from './PlanCard';
import type { OwnState } from './OwnNumbers';
import { ButtonLink } from '../../design-system/Button';
import { Icon } from '../../design-system/Icon';
import { api, explainOn, SnapshotMissError, type SavedAnswers, type SnapshotEntry } from '../../api';
import type { CompareRequest, CompareResponse, Plan } from '../../types';
import {
  compareRequest,
  NO_OWN,
  ownOf,
  serializeFarmerState,
  setOwn,
  type Land,
  type OwnNumbers,
} from '../../domain/farmerState';
import { useApi } from '../../hooks/useApi';
import { DataLine } from '../provenance/DataLine';
import { LoadState } from '../provenance/LoadState';
import { SaveAnswers } from '../account/SaveAnswers';
import { usePick, useSettings, useT, type Lang } from '../../app/settings';
import { planLabel } from '../../domain/plans';
import { pathFor, useLocalTo } from '../../app/paths';
import s from './farmer.module.css';

/** Builds the absolute link that opens exactly this card with the current answers (the answers stay in the fragment),
 * under the path of the language it is shared in (D-174). */
export function cardUrl(search: URLSearchParams, lang: Lang) {
  const base = `${window.location.origin}${window.location.pathname}`;
  return `${base}#${pathFor('/nong-dan/phuong-an', lang)}?${search.toString()}`;
}

function Cards({ res }: { res: CompareResponse }) {
  const t = useT();
  const pick = usePick();
  const { lang } = useSettings();
  const { state, update } = useFarmer();
  const [focused, setFocused] = useState(state.plan);
  const [explain] = useApi(explainOn, 'explain-on'); // asked once per screen; hidden unless the server says on
  // the numbers are held here and the fragment follows them: the router applies a URL change in a React transition, so
  // a second quick entry built from the URL could still miss the first (review of PR #66). Section 6b rule 2: keys of
  // crops this response does not have are dropped.
  const [values, setValues] = useState(() =>
    ownOf(
      state.own,
      res.plans.flatMap((p) => p.money.items.map((i) => i.crop_key)),
    ),
  );
  const own: OwnState = { values, set: (field, crop, digits) => setValues((v) => setOwn(v, field, crop, digits)) };
  useEffect(() => {
    if (JSON.stringify(values) !== JSON.stringify(state.own)) update({ own: values });
  }, [values, state.own, update]);

  useEffect(() => {
    if (!state.plan) return;
    const el = document.getElementById(`the-${state.plan}`);
    el?.scrollIntoView({ block: 'start' });
    const timer = window.setTimeout(() => setFocused(null), 2600);
    return () => window.clearTimeout(timer);
    // only when the cards first open with a card in the link
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const share = useCallback(
    async (plan: Plan) => {
      // the farmer's own price and costs never go into a shared link (D-163, D-180)
      const url = cardUrl(serializeFarmerState({ ...state, plan: plan.id, own: NO_OWN }), lang);
      try {
        if (navigator.share && window.matchMedia('(pointer: coarse)').matches) {
          await navigator.share({
            title: `Miaudow · ${planLabel({ id: plan.id, current: plan.is_usual }, t.farmer)}`,
            text: t.farmer.shareHelp,
            url,
          });
          return true;
        }
        await navigator.clipboard.writeText(url);
        return true;
      } catch {
        return false;
      }
    },
    [state, t, lang],
  );

  return (
    <>
      <DataLine sources={res.sources} className="muted small" />
      <nav className={s.jump} aria-label={t.farmer.jumpTo}>
        {res.plans.map((p) => (
          <a
            key={p.id}
            href={`#the-${p.id}`}
            onClick={(e) => {
              e.preventDefault();
              document.getElementById(`the-${p.id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
              update({ plan: p.id });
            }}
          >
            {planLabel({ id: p.id, current: p.is_usual }, t.farmer)}
            <span className="muted"> · {p.calendar.map((c) => pick(c.crop)).join(' → ')}</span>
          </a>
        ))}
      </nav>
      {/* the API's order is final: no sorting, filtering or ranking (H3) */}
      <div className={s.cards}>
        {res.plans.map((p) => (
          <PlanCard
            key={p.id}
            plan={p}
            res={res}
            priority={res.request.priority}
            focused={focused === p.id}
            explain={explain.status === 'ok' && explain.data}
            own={own}
            onShare={share}
          />
        ))}
      </div>
    </>
  );
}

/** Offline copy only: these answers were not saved, so no cards; the saved answer sets are listed instead. */
function SnapshotMiss({ saved }: { saved: SnapshotEntry[] }) {
  const t = useT();
  return (
    <div className={s.note} role="alert" data-testid="snapshot-miss">
      <Icon name="alert" size={20} />
      <div>
        <p>{t.snapshot.missing}</p>
        <ul className={s.noteList}>
          {saved.map((e) => (
            <li key={e.file}>
              {t.snapshot.saved(
                e.land === 'dry' ? t.snapshot.landDry : t.farmer.lands.ask.title,
                e.years.join(', '),
                t.farmer.prios[e.priority].title,
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function Compare({ body }: { body: CompareRequest }) {
  const [res, retry] = useApi((signal) => api.compare(body, signal), JSON.stringify(body));
  if (res.status === 'ok') return <Cards res={res.data} />;
  if (res.status === 'error' && res.error instanceof SnapshotMissError) return <SnapshotMiss saved={res.error.saved} />;
  return <LoadState state={res} retry={retry} />;
}

/** The answers a farmer can save, with the typed prices and costs (D-180): only with plans to see, so never an
 * irrigated field. */
const savable = (land: Land | null, body: CompareRequest | null, own: OwnNumbers): SavedAnswers | null =>
  body && land && land !== 'reliable' ? { land, years: body.years, priority: body.priority, ...own } : null;

export function PlansStep() {
  const t = useT();
  const { state, search } = useFarmer();
  const local = useLocalTo();
  const [years, retryYears] = useApi(api.pastYears, 'past-years');
  // picked years are checked against the past-years response before any compare request (UI-UX-SPEC section 6b)
  const offered = years.status === 'ok' ? years.data.years.map((y) => y.year) : [];
  const body =
    years.status === 'ok' ? compareRequest({ ...state, years: state.years.filter((y) => offered.includes(y)) }) : null;
  const saved = savable(state.land, body, state.own);
  return (
    <StepShell step={4} title={t.farmer.plansTitle} help={t.farmer.plansLead} wide>
      <div className={s.plansMeta}>
        <div className={s.pickedYears}>
          {state.years.map((y) => (
            <span key={y} className={s.yearTag}>
              {y}
            </span>
          ))}
          <Link to={local({ pathname: '/nong-dan/nam', search })} className={s.editLink}>
            {t.farmer.yearsTitle}
          </Link>
        </div>
        {state.priority && (
          <p className={s.prioNow}>
            <span className={s.prioSwatch} />
            {t.farmer.yourPriority}: <strong>{t.farmer.prios[state.priority].title}</strong>
          </p>
        )}
        {/* next to the answers, not after the six cards (walkthrough of PR #53) */}
        {saved && <SaveAnswers key={JSON.stringify(saved)} answers={saved} />}
      </div>
      {/* one notice box instead of four (walkthrough 2026-11-14); each card repeats its warnings (H17) */}
      <div className={s.note}>
        <Icon name="alert" size={20} />
        <ul className={s.noteList}>
          <li>{t.common.notForecast}</li>
          <li>{t.farmer.trialNote}</li>
          {state.land === 'ask' && <li>{t.farmer.askNote}</li>}
          <li>{t.common.support}</li>
        </ul>
      </div>

      {state.land === 'reliable' && (
        <p className={s.note}>
          <Icon name="alert" size={20} />
          {t.farmer.wetNote}
        </p>
      )}
      {state.land !== 'reliable' && years.status === 'ok' && !body && (
        <p className={s.note}>
          <Icon name="alert" size={20} />
          {t.farmer.needAnswers}{' '}
          <Link to={local({ pathname: '/nong-dan/ruong', search })} className={s.editLink}>
            {t.farmer.restart}
          </Link>
        </p>
      )}
      {state.land !== 'reliable' && years.status !== 'ok' && <LoadState state={years} retry={retryYears} />}
      {body && <Compare body={body} />}

      <section className={s.officerBox} aria-labelledby="ask-officer">
        <h2 id="ask-officer" className="h3">
          <Icon name="user" size={20} /> {t.farmer.askOfficer}
        </h2>
        <ol>
          {t.farmer.officerQuestions.map((q) => (
            <li key={q}>{q}</li>
          ))}
        </ol>
        <div className="cluster">
          <ButtonLink to="/can-bo" variant="secondary" icon="arrowRight">
            {t.farmer.officerView}
          </ButtonLink>
          <ButtonLink to="/nong-dan/ruong" variant="ghost" leadingIcon="rotateL">
            {t.farmer.restart}
          </ButtonLink>
        </div>
      </section>
    </StepShell>
  );
}
