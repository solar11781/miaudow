// D-170: the plain sentence under a money definition follows the definition's study, named by its source id
import { describe, expect, it } from 'vitest';
import { validateCompare } from '../api';
import { body, compare, moneyItem } from '../tests/fixtures';
import { moneyStudy } from './moneyStudy';

const plans = () => validateCompare(compare(), body).plans;

describe('money study', () => {
  it('is P-02 when the money cites R-P02', () => {
    const plan = plans()[2];
    if (!plan) throw new Error('no plan');
    plan.money.items = [moneyItem('k', '1', '1', '1', null)];
    expect(moneyStudy(plan)).toBe('p02');
  });
  it('is P-03 when the plan cites R-P03, with or without text', () => {
    const plan = plans()[1];
    if (!plan) throw new Error('no plan');
    plan.calendar = plan.calendar.map((c) => ({ ...c, source_ids: ['R-P03'] }));
    plan.money.text_only = null;
    expect(moneyStudy(plan)).toBe('p03');
  });
  it('is unknown when neither study is cited', () => {
    const plan = plans()[3];
    if (!plan) throw new Error('no plan');
    plan.calendar = plan.calendar.map((c) => ({ ...c, source_ids: ['R-X'] }));
    expect(moneyStudy(plan)).toBeNull();
  });
});
