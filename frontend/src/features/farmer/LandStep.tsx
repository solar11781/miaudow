import { StepShell, useFarmer } from './FarmerLayout';
import { LandArt } from './LandArt';
import { ButtonLink } from '../../design-system/Button';
import { Icon } from '../../design-system/Icon';
import { LANDS } from '../../domain/farmerState';
import { useT } from '../../app/settings';
import s from './farmer.module.css';

export function LandStep() {
  const t = useT();
  const { state, update, search } = useFarmer();
  return (
    <StepShell
      step={1}
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
          {t.common.next}
        </ButtonLink>
      }
    >
      <div className={s.choices} role="radiogroup" aria-label={t.farmer.landTitle}>
        {LANDS.map((land) => {
          const on = state.land === land;
          return (
            <button
              key={land}
              type="button"
              role="radio"
              aria-checked={on}
              className={[s.choice, on ? s.on : ''].join(' ')}
              onClick={() => update({ land })}
            >
              <span className={s.choiceArt}>
                <LandArt land={land} />
              </span>
              <span className={s.choiceText}>
                <span className={s.choiceTitle}>{t.farmer.lands[land].title}</span>
                <span className={s.choiceBody}>{t.farmer.lands[land].body}</span>
              </span>
              <span className={s.tick} aria-hidden="true">
                {on && <Icon name="check" size={16} strokeWidth={2.6} />}
              </span>
            </button>
          );
        })}
      </div>
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
