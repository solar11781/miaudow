/**
 * A heading with its second half in brush lettering: "Bốn lõi AI, *một nguồn dữ liệu*". The split is at the first
 * comma; a heading without one stays plain. The words never change, only how the second half is drawn.
 */
export function Accent({ text }: { text: string }) {
  const i = text.indexOf(', ');
  if (i < 0) return <>{text}</>;
  return <>{text.slice(0, i + 1)} <em>{text.slice(i + 2)}</em></>;
}
