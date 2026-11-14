import { useFarmer } from './FarmerLayout';
import { Accent } from '../../design-system/Accent';
import { Brocade } from '../../design-system/Brocade';
import { ButtonLink } from '../../design-system/Button';
import { Icon, type IconName } from '../../design-system/Icon';
import { Media } from '../../design-system/Media';
import { useT } from '../../app/settings';
import { ART } from '../../data/art';
import { useSignInAvailable } from '../account/AccountProvider';
import s from './farmer.module.css';

const HELP_ICONS: IconName[] = ['sun', 'sprout', 'user'];
const STEP_ART = [
  'media/field/field-at-end-of-canal.webp',
  'media/field/field-often-short-of-water.webp',
  'media/field/water-under-control.webp',
  'media/field/ask-extension-officer.webp',
];

/** What the farmer part does and does not do, in plain words, before the first tap. */
export function StartStep() {
  const t = useT();
  const { search } = useFarmer();
  const signIn = useSignInAvailable();
  return (
    <div className={`${s.shell} ${s.wide}`}>
      <article className={`${s.startCard} surface-forest`}>
        <div className={s.startPhoto}>
          <Media slug={ART.farmerStart.slug} priority sizes="(max-width: 700px) 320px, 600px" decorative />
        </div>
        <div className={s.startBody}>
          <h1 className={`display ${s.startTitle}`}>
            <Accent text={t.farmer.startTitle} />
          </h1>
          <p className={s.startLead}>{t.farmer.startLead}</p>
          <ButtonLink to={{ pathname: '/nong-dan/ruong', search }} size="lg" block icon="arrowRight">
            {t.farmer.startCta}
          </ButtonLink>
        </div>
      </article>
      {signIn && (
        <ButtonLink to="/da-luu" variant="secondary" leadingIcon="book">
          {t.account.savedTitle}
        </ButtonLink>
      )}
      <Brocade />

      <section className={s.explain} aria-labelledby="farmer-helps">
        <div className={s.explainCol}>
          <h2 id="farmer-helps" className="h3">
            {t.farmer.helpsTitle}
          </h2>
          <ul className={s.helps}>
            {t.farmer.helps.map((h, i) => (
              <li key={h}>
                <span className={s.helpIcon}>
                  <Icon name={HELP_ICONS[i] ?? 'check'} size={22} />
                </span>
                {h}
              </li>
            ))}
          </ul>
        </div>
        <div className={s.explainCol}>
          <h2 className="h3">{t.farmer.notTitle}</h2>
          <ul className={s.nots}>
            {t.farmer.nots.map((h) => (
              <li key={h}>
                <span className={s.notIcon}>
                  <Icon name="close" size={18} strokeWidth={2.4} />
                </span>
                {h}
              </li>
            ))}
          </ul>
        </div>
      </section>

      <ol className={s.startSteps} aria-label={t.farmer.stepsLabel}>
        {t.home.steps.map((st, i) => (
          <li key={st.title}>
            <img src={STEP_ART[i]} alt="" width={474} height={356} loading="lazy" decoding="async" />
            <span className={s.startStepNum}>{t.home.stepLabel(i + 1)}</span>
            <span className={s.startStepTitle}>{st.title}</span>
          </li>
        ))}
      </ol>
      <p className={s.support}>
        <Icon name="user" size={20} />
        {t.common.support}
      </p>
    </div>
  );
}
