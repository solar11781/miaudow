import type { Land } from '../../domain/farmerState';

/** Small hand-made scenes for the land choice: pictures plus words, never pictures alone. */
export function LandArt({ land }: { land: Land }) {
  if (land === 'dry') {
    return (
      <svg viewBox="0 0 120 90" aria-hidden="true" focusable="false">
        <rect width="120" height="90" rx="14" fill="#f6e6bf" />
        <circle cx="92" cy="24" r="11" fill="#e9bc57" />
        <path d="M92 6v5M92 37v5M74 24h5M105 24h5M79 11l3.5 3.5M101.5 33.5 105 37M79 37l3.5-3.5M101.5 14.5 105 11" stroke="#c9962e" strokeWidth="2" strokeLinecap="round" />
        <path d="M0 58c20-6 44-8 66-6s38 3 54 0v38H0Z" fill="#c9a06a" />
        <path d="M0 66c22-4 50-5 74-3s32 2 46 0v27H0Z" fill="#b48650" />
        <path d="M14 72l7 5-3 6M21 77l9-2 4 5M48 70l-4 7 6 4M44 77l-9 1M80 72l6 4-2 6M86 76l8-3M102 78l-5 5" stroke="#7d5a2c" strokeWidth="1.6" fill="none" strokeLinecap="round" />
        <path d="M30 60c0-5 1-9 3-12M30 60c-1-4-4-7-7-8M64 58c0-5 2-9 4-11M64 58c-2-4-4-6-7-7" stroke="#8a9a3a" strokeWidth="2" fill="none" strokeLinecap="round" />
      </svg>
    );
  }
  if (land === 'wet') {
    return (
      <svg viewBox="0 0 120 90" aria-hidden="true" focusable="false">
        <rect width="120" height="90" rx="14" fill="#dceee4" />
        <path d="M0 40h120v26H0Z" fill="#7fb0c8" />
        <path d="M6 50c8-4 16-4 24 0s16 4 24 0 16-4 24 0 16 4 24 0 10-3 12-2M10 59c8-3 14-3 22 0s14 3 22 0" stroke="#e8f4f8" strokeWidth="2" fill="none" strokeLinecap="round" />
        <path d="M0 66h120v24H0Z" fill="#6e9e3c" />
        <path d="M0 28h120v12H0Z" fill="#8bb85a" />
        {[12, 28, 44, 60, 76, 92, 108].map((x) => (
          <g key={x} stroke="#2f5d22" strokeWidth="2" strokeLinecap="round" fill="none">
            <path d={`M${x} 82c0-6 1-10 3-13`} /><path d={`M${x} 82c-1-5-3-8-6-9`} /><path d={`M${x} 82c1-4 4-7 7-7`} />
          </g>
        ))}
        {[18, 46, 74, 102].map((x) => (
          <g key={x} stroke="#3d6b29" strokeWidth="1.8" strokeLinecap="round" fill="none">
            <path d={`M${x} 34c0-5 1-8 2-11`} /><path d={`M${x} 34c-1-4-3-6-5-7`} />
          </g>
        ))}
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 120 90" aria-hidden="true" focusable="false">
      <rect width="120" height="90" rx="14" fill="#ece6d6" />
      <path d="M0 70h120v20H0Z" fill="#a9c97a" />
      <path d="M22 44 40 24l18 20c-6 2.5-12 3.6-18 3.6S28 46.5 22 44Z" fill="#e8d7a0" stroke="#b39a5c" strokeWidth="1.2" />
      <path d="M30 41l10-11 10 11" stroke="#c9b27a" strokeWidth="1" fill="none" />
      <circle cx="40" cy="50" r="6" fill="#9a6b4a" />
      <path d="M28 86c0-12 5-22 12-22s12 10 12 22Z" fill="#3e6b8a" />
      <rect x="66" y="16" width="40" height="30" rx="10" fill="#fffdf7" stroke="#c9b27a" strokeWidth="1.4" />
      <path d="M74 46l-6 8 12-8" fill="#fffdf7" stroke="#c9b27a" strokeWidth="1.4" strokeLinejoin="round" />
      <path d="M81.5 26.5a4.5 4.5 0 1 1 6.3 4.1c-1.4.6-1.8 1.3-1.8 2.9M86 38h.01" stroke="#8a6210" strokeWidth="2.4" fill="none" strokeLinecap="round" />
    </svg>
  );
}
