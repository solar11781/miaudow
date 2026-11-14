import { StepShell, useFarmer } from './FarmerLayout';
import { ButtonLink } from '../../design-system/Button';
import { Icon, type IconName } from '../../design-system/Icon';
import type { Priority } from '../../domain/farmerState';
import { useT } from '../../app/settings';
import s from './farmer.module.css';

const PRIOS: [Priority, IconName][] = [
  ['income', 'coin'],
  ['stability', 'shield'],
  ['water', 'drop'],
  ['land', 'sprout'],
];

export function PriorityStep() {
  const t = useT();
  const { state, update, search } = useFarmer();
  return (
    <StepShell
      step={3}
      title={t.farmer.prioTitle}
      help={t.farmer.prioHelp}
      actions={
        <ButtonLink
          to={{ pathname: '/nong-dan/phuong-an', search }}
          size="lg"
          block
          icon="arrowRight"
          aria-disabled={!state.priority}
          onClick={(e) => {
            if (!state.priority) e.preventDefault();
          }}
          className={!state.priority ? s.disabledLink : undefined}
        >
          {t.farmer.seePlans}
        </ButtonLink>
      }
    >
      <div className={s.prioGrid} role="radiogroup" aria-label={t.farmer.prioTitle}>
        {PRIOS.map(([p, icon]) => {
          const on = state.priority === p;
          return (
            <button
              key={p}
              type="button"
              role="radio"
              aria-checked={on}
              className={[s.prio, on ? s.on : ''].join(' ')}
              onClick={() => update({ priority: p })}
            >
              <span className={s.prioIcon}>
                <Icon name={icon} size={30} strokeWidth={1.6} />
              </span>
              <span className={s.choiceTitle}>{t.farmer.prios[p].title}</span>
              <span className={s.choiceBody}>{t.farmer.prios[p].body}</span>
              <span className={s.tick} aria-hidden="true">
                {on && <Icon name="check" size={16} strokeWidth={2.6} />}
              </span>
            </button>
          );
        })}
      </div>
    </StepShell>
  );
}
