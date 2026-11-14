import { StepShell, useFarmer } from './FarmerLayout';
import { ButtonLink } from '../../design-system/Button';
import { Icon } from '../../design-system/Icon';
import { LANDS, type Land } from '../../domain/farmerState';
import { useT } from '../../app/settings';
import s from './farmer.module.css';

// AI-generated illustrations made for MIAUDOW (assets/field-conditions/manifest.json): they help a farmer recognise
// the situation; they are not photographs of Đô Lương and carry no data. The words on the card always say it.
const ART: Record<Land, string> = {
  high_field: 'media/field/high-field-hard-to-water.webp',
  canal_end: 'media/field/field-at-end-of-canal.webp',
  water_short: 'media/field/field-often-short-of-water.webp',
  reliable: 'media/field/water-under-control.webp',
  ask: 'media/field/ask-extension-officer.webp',
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
        <ButtonLink to={{ pathname: '/nong-dan/nam', search }} size="lg" block icon="arrowRight"
          aria-disabled={!state.land} onClick={(e) => { if (!state.land) e.preventDefault(); }}
          className={!state.land ? s.disabledLink : undefined}>
          {state.land ? t.common.next : t.farmer.pickFirst}
        </ButtonLink>
      }
    >
      <div className={s.landGrid} data-stagger role="radiogroup" aria-label={t.farmer.landTitle}>
        {LANDS.map((land) => {
          const on = state.land === land;
          return (
            <button key={land} type="button" role="radio" aria-checked={on} className={[s.landCard, on ? s.on : ''].join(' ')} onClick={() => update({ land })}>
              <span className={s.landArt}>
                <img src={ART[land]} alt="" width={474} height={356} loading="lazy" decoding="async" />
                <span className={s.landTick} aria-hidden="true">{on ? <Icon name="check" size={22} strokeWidth={2.8} /> : null}</span>
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
      {state.land === 'reliable' && <p className={s.note} role="status"><Icon name="alert" size={20} />{t.farmer.wetNote}</p>}
      {(state.land === 'high_field' || state.land === 'canal_end' || state.land === 'water_short') && <p className={s.note} role="status"><Icon name="canal" size={20} />{t.farmer.dryNote}</p>}
      {state.land === 'ask' && <p className={s.note} role="status"><Icon name="user" size={20} />{t.farmer.askNote}</p>}
    </StepShell>
  );
}
