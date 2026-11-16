---
paths:
  - "frontend/**"
---

# Frontend conventions (D-125)

Updated 2026-11-17 to the app as built: the team's web app became the product frontend at integration (D-166).

## Where code goes

- `frontend/src/features/<area>/`: one folder per page or area (`farmer`, `officer`, `science`, `method`, `evidence`,
  `ai`, `earth`, `home`, `account`, `provenance`, `charts`, `cinema`). One component per file, file name = component
  name in `PascalCase`, with its styles beside it as `<Name>.module.css` or the area's `<area>.module.css`.
- `frontend/src/app/`: the shell (router, layout, header, footer, settings, paths). `frontend/src/design-system/`:
  shared pieces (button, icon, media). Do not write a second component for a job one of them already does.
- `frontend/src/domain/`: logic and data without React (plans, sources, hazards, formatting).
  `frontend/src/data/`: the bundled data files and their typed readers.
- `frontend/src/api.ts`: the only module that talks to the backend; it validates every response (spec section 11).
  The lint rule `no-restricted-globals` blocks `fetch` anywhere else.
- `frontend/src/types.ts`: the TypeScript types of the data contract, names and fields as in spec section 11.
- `frontend/src/i18n/`: `vi.ts`, `en.ts` (typed as `Messages`) and `GLOSSARY.md`. Every user-visible string comes
  from them through `useT()` or from API `Text` fields (hard rule H15). Bilingual data files (`domain/sources.ts`,
  `domain/plans.ts`, `features/ai/knowledge.ts`, `features/evidence/claims.ts`, `features/earth/missions.ts`) hold
  `{vi, en}` pairs.

## Code

- TypeScript strict; no `any`, no non-null assertions (`!`), no type casts to silence errors (a JSON import may be
  cast once, where it is read).
- Function components and hooks; a shared custom hook lives in `src/hooks/use<Name>.ts`.
- Styling with CSS modules built from the visual tokens of `src/styles/tokens.css` (spec section 5); shared rules in
  `src/styles/global.css`. A new inline `style` only sets a value computed at run time (a position, a size, a CSS
  variable); a few static ones remain from the integration. No new colours.
- The hard rules of spec section 4 apply to every component (44 x 44 px targets, contrast, 200% zoom, no
  horizontal scroll at 360 px, meaning never by colour alone).
- Test hooks: the `data-testid` values and data attributes of spec section 14a.
- Only packages on the allow-list (`.github/scripts/dependency-allowlist.json`), exact versions.

## Tests

- Unit tests with vitest next to the code: `<Name>.test.tsx` / `<name>.test.ts`.
- Browser tests with Playwright in `frontend/e2e/<topic>.spec.ts` at 360 x 740 and 1440 x 900. A test of a spec
  requirement starts its name with the spec's test ID (for example `T10 no-hscroll`); a test of an audit finding says
  the finding in a comment above it.
