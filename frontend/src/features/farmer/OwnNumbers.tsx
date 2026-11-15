import { useState } from 'react';
import type { MoneyItem, SourceId, Value } from '../../types';
import { Icon } from '../../design-system/Icon';
import { millionsOf, ownMoney, readMillions, readWhole } from '../../domain/ownMoney';
import type { OwnNumbers as Own } from '../../domain/farmerState';
import { SourceValue } from '../provenance/SourceValue';
import type { ApiRefs } from '../provenance/useApiRefs';
import { useT } from '../../app/settings';
import s from './PlanCard.module.css';

/** The farmer's own numbers (kept in the fragment by the cards page) and how to change one. */
export interface OwnState {
  values: Own;
  set: (field: keyof Own, crop: string, digits: string | null) => void;
}

/** How a field reads and shows its number: a price as whole đồng per kg, a cost typed in million đồng per ha and kept
 * in thousand (D-192, so a link or saved set keeps its meaning, D-180). */
const PRICE = { inputMode: 'numeric', step: 1, read: readWhole, show: (d: string) => d, invalid: 'invalid' } as const;
const COST = {
  inputMode: 'decimal',
  step: 'any',
  read: readMillions,
  show: millionsOf,
  invalid: 'invalidCost',
} as const;

function Field({
  id,
  crop,
  label,
  kind,
  digits,
  onDigits,
}: {
  id: string;
  /** Said to screen readers before the label; the fieldset's legend shows it on screen. */
  crop: string;
  label: string;
  kind: typeof PRICE | typeof COST;
  digits: string | undefined;
  onDigits: (digits: string | null) => void;
}) {
  const t = useT();
  const [invalid, setInvalid] = useState(false);
  return (
    <div className={s.ownField}>
      <label htmlFor={id}>
        <span className="visually-hidden">{crop}: </span>
        {label}
      </label>
      {/* numeric input, which H4 and T4 allow; uncontrolled, so a wrong entry stays visible while it is not used */}
      <input
        id={id}
        type="number"
        inputMode={kind.inputMode}
        min={0}
        step={kind.step}
        defaultValue={digits === undefined ? undefined : kind.show(digits)}
        aria-invalid={invalid || undefined}
        aria-describedby={invalid ? `${id}-invalid` : undefined}
        onChange={(e) => {
          const read = e.currentTarget.validity.badInput ? 'invalid' : kind.read(e.currentTarget.value);
          setInvalid(read === 'invalid');
          onDigits(read === 'invalid' ? null : read);
        }}
      />
      {invalid && (
        <p id={`${id}-invalid`} className={s.ownInvalid}>
          <Icon name="alert" size={16} />
          {t.farmer.own[kind.invalid]}
        </p>
      )}
    </div>
  );
}

/** "Your price and costs" (UI-UX-SPEC section 12d, D-163): per crop the farmer types a sale price and a cost per ha;
 * the study's yield with those numbers is worked out here in the browser and shown apart from the study's money. */
export function OwnNumbers({
  planId,
  items,
  names,
  refs,
  own,
}: {
  planId: string;
  items: MoneyItem[];
  /** The crop and season name of each item, as the money row shows it. */
  names: string[];
  refs: ApiRefs;
  own: OwnState;
}) {
  const t = useT();
  const { prices, costs } = own.values;
  const [open, setOpen] = useState(() => items.some((i) => i.crop_key in prices || i.crop_key in costs));
  const first = items[0];
  if (!first) return null; // P-03 money is text only: no entry (D-163)
  const id = `card-${planId}-own-form`;
  const result = ownMoney(
    items.map((i) => i.yield.value),
    items.map((i) => ({ price: prices[i.crop_key] ?? null, cost: costs[i.crop_key] ?? null })),
  );
  // a computed number cites the study yield it multiplies and the engine's arithmetic E-022 (D-158); the sheet says
  // the price and costs are the farmer's own; shown in million dong per ha like the study's money (D-190)
  const computed = (value: string, ids: SourceId[], label: string) => {
    const v: Value = { value, unit: first.profit.unit, source_ids: [...ids, 'E-022'] };
    const m = refs.money(v);
    return (
      <SourceValue {...refs.value(v, label)} note={t.farmer.own.sheetNote}>
        {`${m.number} ${m.unit}`}
      </SourceValue>
    );
  };
  const yieldIds = items.flatMap((i) => i.yield.source_ids);
  const total = result.total;
  return (
    // a test hook of its own, so the money row's total stays the only unmarked div of the row (priority-line T37)
    <div className={s.fold} data-testid={`card-${planId}-your-numbers`}>
      <button
        type="button"
        className={s.foldButton}
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((o) => !o)}
      >
        <Icon name="chevronDown" size={18} />
        {t.farmer.yourNumbers}
      </button>
      <div id={id} hidden={!open} className={s.own}>
        <p className={s.rowNote}>{t.farmer.own.help}</p>
        {items.map((item, i) => {
          const name = names[i] ?? '';
          return (
            <fieldset key={item.crop_key} className={s.ownCrop}>
              <legend>{name}</legend>
              <p className={s.rowNote}>
                {t.farmer.own.study}: {t.farmer.own.yield}{' '}
                <SourceValue {...refs.value(item.yield, `${t.farmer.own.yield} · ${name}`)} /> {t.farmer.own.price}{' '}
                <SourceValue {...refs.value(item.price, `${t.farmer.own.price} · ${name}`)} />
              </p>
              <Field
                id={`own-${item.crop_key}-price`}
                crop={name}
                label={`${t.farmer.own.yourPrice} (${refs.unit(item.price)})`}
                kind={PRICE}
                digits={prices[item.crop_key]}
                onDigits={(d) => own.set('prices', item.crop_key, d)}
              />
              <Field
                id={`own-${item.crop_key}-cost`}
                crop={name}
                label={`${t.farmer.own.yourCost} (${t.common.millionPerHa})`}
                kind={COST}
                digits={costs[item.crop_key]}
                onDigits={(d) => own.set('costs', item.crop_key, d)}
              />
            </fieldset>
          );
        })}
        <section className={s.ownResult} data-testid={`card-${planId}-own`} aria-label={t.farmer.own.title}>
          <p className={s.subHead}>{t.farmer.own.title}</p>
          <p className={s.rowNote}>{t.farmer.yourNumbersLabel}</p>
          <ul className={s.kv}>
            {items.map((item, i) => {
              const name = names[i] ?? '';
              const r = result.crops[i];
              return (
                <li key={item.crop_key}>
                  <span>{name}</span>
                  <span className={s.kvVals}>
                    {r?.revenue ? (
                      <span>
                        {t.farmer.own.revenue}:{' '}
                        {computed(r.revenue, item.yield.source_ids, `${t.farmer.own.revenue} · ${name}`)}
                      </span>
                    ) : (
                      <span className="muted">{t.farmer.own.needPrice}</span>
                    )}
                    {r?.margin && (
                      <span>
                        {t.farmer.own.margin}:{' '}
                        {computed(r.margin, item.yield.source_ids, `${t.farmer.own.margin} · ${name}`)}
                      </span>
                    )}
                  </span>
                </li>
              );
            })}
            {total.revenue && (
              <li>
                <span>{t.farmer.own.yearSum}</span>
                <span className={s.kvVals}>
                  <span>
                    {t.farmer.own.revenue}:{' '}
                    {computed(total.revenue, yieldIds, `${t.farmer.own.revenue} · ${t.farmer.own.yearSum}`)}
                  </span>
                  {total.margin && (
                    <span>
                      {t.farmer.own.margin}:{' '}
                      {computed(total.margin, yieldIds, `${t.farmer.own.margin} · ${t.farmer.own.yearSum}`)}
                    </span>
                  )}
                </span>
              </li>
            )}
          </ul>
          <p className={s.rowNote}>{t.farmer.own.costNote}</p>
          <p className={s.rowNote}>{t.farmer.own.private(t.farmer.share)}</p>
        </section>
      </div>
    </div>
  );
}
