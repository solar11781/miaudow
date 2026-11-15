import { StepShell, useFarmer } from './FarmerLayout';
import { ButtonLink } from '../../design-system/Button';
import { Icon } from '../../design-system/Icon';
import { Media } from '../../design-system/Media';
import { LANDS, type Land } from '../../domain/farmerState';
import { useT } from '../../app/settings';
import s from './farmer.module.css';

// AI-generated illustrations made for MIAUDOW (media.json, kind illustration): they help a farmer recognise the
// situation; they are not photographs of Đô Lương and carry no data. The words on the card always say it.
export const LAND_ART: Record<Land, string> = {
  high_field: 'high-field-hard-to-water',
  canal_end: 'field-at-end-of-canal',
  water_short: 'field-often-short-of-water',
  reliable: 'water-under-control',
  ask: 'ask-extension-officer',
};

export function LandStep() {
  const t = useT();
  const { state, update, search } = useFarmer();
  return (
    <StepShell
      step={1}
      wide
      title={t.farmer.landTitle}
      help={t.farmer.landHelp}
      actions={
        <ButtonLink
          to={{ pathname: '/nong-dan/nam', search }}
          size="lg"
          block
          icon="arrowRight"
          aria-disabled={!state.land}
          onClick={(e) => {
            if (!state.land) e.preventDefault();
          }}
          className={!state.land ? s.disabledLink : undefined}
        >
          {state.land ? t.common.next : t.farmer.pickFirst}
        </ButtonLink>
      }
    >
      {/* read before choosing (walkthrough 2026-11-14): high_field, canal_end and water_short all map to land "dry" */}
      <p className="muted">{t.farmer.landSameDry}</p>
      <div className={s.landGrid} role="radiogroup" aria-label={t.farmer.landTitle}>
        {LANDS.map((land) => {
          const on = state.land === land;
          return (
            <button
              key={land}
              type="button"
              role="radio"
              aria-checked={on}
              className={[s.landCard, on ? s.on : ''].join(' ')}
              onClick={() => update({ land })}
            >
              <span className={s.landArt}>
                <Media slug={LAND_ART[land]} sizes="474px" decorative />
                <span className={s.landTick} aria-hidden="true">
                  {on ? <Icon name="check" size={22} strokeWidth={2.8} /> : null}
                </span>
              </span>
              <span className={s.landText}>
                <span className={s.landTitle}>{t.farmer.lands[land].title}</span>
                <span className={s.landBody}>{t.farmer.lands[land].body}</span>
              </span>
            </button>
          );
        })}
      </div>
      <p className={s.artNote}>{t.farmer.artNote}</p>
      {state.land === 'reliable' && (
        <p className={s.note} role="status">
          <Icon name="alert" size={20} />
          {t.farmer.wetNote}
        </p>
      )}
      {(state.land === 'high_field' || state.land === 'canal_end' || state.land === 'water_short') && (
        <p className={s.note} role="status">
          <Icon name="canal" size={20} />
          {t.farmer.dryNote}
        </p>
      )}
      {state.land === 'ask' && (
        <p className={s.note} role="status">
          <Icon name="user" size={20} />
          {t.farmer.askNote}
        </p>
      )}
    </StepShell>
  );
}
