<!-- From member A's session, 2026-11-15 02:10 ICT. Member B's Claude: read this before more UI work. The same note is in the planning repository, docs/HANDOFF-MEMBER-B.md, with progress in docs/AUTOPILOT-STATUS.md. -->

# Hand-off for member B's Claude: getting the redesign into the live app

Written 2026-11-15 02:00 ICT by member A's session. Read this before more UI work. Decisions: D-166 to D-176 in
`docs/DECISION-LOG.md`. Report progress at the end of `docs/AUTOPILOT-STATUS.md` (one line per step, with the time).

## Where the app lives now

- The live app (https://miaudow.solareclipse.observer) is built from `frontend/` on miaudow `main`, not from
  `lamgiang/`. Your app was moved there in PR #51 (D-166) and wired to our API: the farmer cards, past years and the
  method page read `/api/past-years`, `/api/compare` and `/api/method` through `frontend/src/api.ts`.
- Changes made only in `lamgiang/` (branch `feat/lamgiang-2`) never reach the live app. Your redesign of 01:04-01:13
  (new type and colour system, gsap motion, cinematic home, plain farmer readings, solid header) is still only there.

## What to do

1. Branch from the latest miaudow `main` (for example `feat/redesign-2`) and port the redesign into `frontend/`. Keep
   everything `main` added since PR #51: the API wiring, source buttons, the number display (D-170), the card head
   summary and TCVN water range (D-172, D-175), the explain buttons, the sign-in and saved-answers screens (PR #53),
   the offline snapshot mode (PR #52), the folded per-year tables (D-170), the CSP and security headers.
2. Every displayed number must come from our API or from the audited, sourced data (D-169). Do not bring back the
   numbers the audit hid (list in D-169 and the PR #51 description). The audit table is attached to PR #51.
3. New package: gsap is not on `.github/scripts/dependency-allowlist.json`. Check its licence (gsap uses its own
   "Standard no-charge licence", which may not be OSI) and write the facts for member A, who decides (CLAUDE.md
   competition rules: third-party material public or OSI-licensed). Motion follows H1 and D-155: none under reduced
   motion, a pause button, nothing on the farmer routes beyond what H1 allows.
4. The 64 AI-generated home illustrations need a decision before the submission (R-H15, D-173): replace them with the
   open-licence photos, or watermark and declare them.
5. Page speed: our local test measured a median LCP of 5.5-7.3 s at 360 px (home 7.3 s) against your 2.5 s target.
   Check image sizes and what loads first.

## Checks before asking for a merge (all must pass, real output in the PR text)

- In `frontend/`: `npm run lint`, `npm run typecheck`, `npx prettier --check .`, `npx vitest run`, `npm run build`.
- At the repo root: `python -m pytest -q`, `ruff check .`, `ruff format --check .`.
- Browser tests against the real FastAPI server: `npx playwright test` (the config starts uvicorn on port 8000).
- A 360 x 740 check of every screen (no sideways scroll, text >= 17 px, taps >= 44 px, no console errors, no
  third-party request except the D-167 exceptions, no browser storage) and the cognitive walkthrough as a first-time
  farmer (`.claude/skills/cognitive-walkthrough`).
- Your own audit of the change: list what changed per screen, every number still traced, every text in the i18n files.

## Then

Open a pull request against `main` and write the results above in it. Member A's session reviews (spec, security,
phone check) and merges it through the gate; do not merge yourself. Note in `docs/AUTOPILOT-STATUS.md` when it is
ready, and anything you could not do.
