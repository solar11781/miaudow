---
paths:
  - "frontend/**"
---

# Frontend conventions (D-125; structure from the UI/UX spec sections 3, 6d, 11, 13, 14a)

## Where code goes

- `frontend/src/components/<Name>.tsx`: one component per file, file name = component name in `PascalCase`. The
  component names are the ones the UI/UX spec lists (section 13); do not invent a second component for the same job.
- `frontend/src/pages/<Name>Page.tsx`: one file per route of the spec.
- `frontend/src/api.ts`: the only module that talks to the backend or loads fixtures; it validates every response
  (spec section 11). The lint rule `no-restricted-globals` blocks `fetch` anywhere else.
- `frontend/src/types.ts`: the TypeScript types of the data contract, names and fields exactly as in spec section 11.
- `frontend/src/i18n/`: `vi.json`, `en.json`, `t.ts` (spec section 6d). Every user-visible string comes from `t()` or
  from API `Text` fields (hard rule H15).
- `frontend/public/fixtures/`: placeholder responses matching spec section 11.

## Code

- TypeScript strict; no `any`, no non-null assertions (`!`), no type casts to silence errors.
- Function components and hooks; a custom hook lives in `src/hooks/use<Name>.ts`.
- Styling with Tailwind classes built from the spec's visual tokens (section 5); no inline `style`, no new colours.
- The hard rules of spec section 4 apply to every component (44 x 44 px targets, contrast, 200% zoom, no
  horizontal scroll at 360 px, meaning never by colour alone).
- Test hooks: exactly the `data-testid` values and data attributes of spec section 14a.
- Only packages on the allow-list (`.github/scripts/dependency-allowlist.json`), exact versions.

## Tests

- Unit tests with vitest next to the code: `<Name>.test.tsx` / `<name>.test.ts`.
- Browser tests with Playwright in `frontend/e2e/<topic>.spec.ts` at viewport 360 x 740; test names start with the
  spec's test ID (for example `T10 no-hscroll`).
