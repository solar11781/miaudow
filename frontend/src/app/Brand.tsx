/** Miaudow mark: a rice ear under two leaf "ears" (meow + meadow), pressed like a seal. */
export function BrandMark({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true" focusable="false">
      <rect x="1" y="1" width="38" height="38" rx="12" fill="var(--c-forest-900)" />
      <rect
        x="1.5"
        y="1.5"
        width="37"
        height="37"
        rx="11.5"
        fill="none"
        stroke="var(--c-gold-500)"
        strokeOpacity=".35"
      />
      <path d="M10.5 15.5c0-4.8 1.6-7.8 3.6-8.8 1 2.7 1.5 5.6 1.2 8.8Z" fill="var(--c-paddy-300)" />
      <path d="M29.5 15.5c0-4.8-1.6-7.8-3.6-8.8-1 2.7-1.5 5.6-1.2 8.8Z" fill="var(--c-paddy-300)" />
      <path d="M20 33c0-6 .7-11 4-15" stroke="var(--c-gold-500)" strokeWidth="1.7" fill="none" strokeLinecap="round" />
      <ellipse cx="24.6" cy="16.4" rx="1.7" ry="3" transform="rotate(32 24.6 16.4)" fill="var(--c-gold-500)" />
      <ellipse cx="21.9" cy="21" rx="1.6" ry="2.8" transform="rotate(-28 21.9 21)" fill="var(--c-gold-500)" />
      <ellipse cx="23.6" cy="25.4" rx="1.5" ry="2.6" transform="rotate(30 23.6 25.4)" fill="var(--c-gold-500)" />
      <path d="M12 33h16" stroke="var(--c-paddy-500)" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}
