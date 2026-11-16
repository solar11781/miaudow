import { describe, expect, it } from 'vitest';
import { nextStep } from './nextStep';

describe('nextStep: questions Miaudow can only answer with the four-step comparison', () => {
  it('the first example question names a canal-end field and is a question about the asker’s own field', () => {
    const q = 'Ruộng nhà tôi cuối kênh, mùa hè thường thiếu nước, nên xem những cách trồng nào?';
    expect(nextStep(q, null)).toEqual({ kind: 'field', land: 'canal_end' });
  });

  it.each([
    ['Which plan is best for me? Just tell me what to plant.', 'ranking'],
    ['Nên trồng gì cho ruộng nhà tôi?', 'ranking'],
    ['Cách nào tốt nhất?', 'ranking'],
  ])('“%s” is a request to choose, so it is a %s question', (q, kind) => {
    expect(nextStep(q, null)?.kind).toBe(kind);
  });

  it('takes the field type from the water pick when the question names none', () => {
    expect(nextStep('Which plan is best for me?', 'high_field')).toEqual({ kind: 'ranking', land: 'high_field' });
    expect(nextStep('Which plan is best for me?', null)).toEqual({ kind: 'ranking', land: null });
  });

  it('the words of the question win over the pick', () => {
    expect(nextStep('My field is at the end of the canal, what should I look at?', 'reliable')?.land).toBe('canal_end');
  });

  it('leaves ordinary evidence questions alone', () => {
    expect(nextStep('Năm 2010 có hạn không?', null)).toBeNull();
    expect(nextStep('Dữ liệu NASA là gì?', null)).toBeNull();
    expect(nextStep('Năm sau có hạn không?', null)).toBeNull();
  });
});
