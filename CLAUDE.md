# Claude instructions for miaudow

## What this repo is

The main project and the repository submitted to the NASA Space Apps Challenge 2026, challenge "Field Shift:
Adapting Farms with NASA Data" (Hanoi team, Nov 14-15, 2026).

We build a visual, Vietnamese-language decision-support tool that helps farmers on drought-prone, low-productivity
rice land in Nghệ An compare a few evidence-backed one-year crop sequences (including keeping rice) under past
years labelled with Vietnam's official hazard conditions, across income, climate risk, water and land-care, shown as
one card per plan with the farmer's priorities highlighted. It compares; it does not dictate.

This file must work on its own: in a cloud session only this repository is available.

## Specs

The product, requirements, design, data contracts and ML specs live in the team's planning repository until
they are copied into `docs/` at the end of the event. Read them there; if it is not available in this session,
ask the team before any change that depends on them. If a spec does not say what should happen, ask the team.
Never let the code decide.

## Branches, commits and merging

- Every task gets its own branch from the latest `main`, named `<type>/<short-name>` in lowercase with hyphens,
  for example `feat/plan-cards`, `fix/month-bar-overflow`, `chore/pin-versions`. The type is one of the commit types
  below.
- Commit and push to the task branch freely. Pull before pushing. Never push directly to `main`.
- Merging into `main` (team decisions, 2026-11-13 and 2026-11-14): only by `gh pr merge <number> --merge` (or `-m`; a
  normal merge, so every branch commit stays on `main` with its real time; squash and rebase are refused) through the gate
  in the `task` skill: every CI check passed, the branch contains the latest `main`, and a gate record shows that the
  double-checked spec-review and security-review found no open issue. The safety hook enforces the gate. Without
  `gh`, the team merges. Each branch commit is one clean, logical step; no work-in-progress commits.
- Commit format: `<type>: <description>`. Types: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `perf`,
  `style`, `build`, `ci`.
- Subject and body all lowercase, including names and acronyms (`nasa`, `modis`). No emojis. No en dashes or em
  dashes. No attribution trailers (`Co-Authored-By`, `Claude-Session` or similar).

## Scientific boundaries (non-negotiable)

- Regional estimates only; never farm-specific yield predictions.
- ML never claims causal rotation benefits.
- Past years are never presented as forecasts.
- Revenue is not profit; no profit claim for the farmer's own field without user-entered costs.
- Every displayed number has a source and a trust label made of facts about that source only (study type, place,
  years, replicated or not, full text read; no grades). Non-comparable evidence is never ranked together.
- No random row splits; trend and scaling fitted on past years only.
- Non-rice crops: study values only, no ML.

## Competition rules

- The core product is built during the event. Before 00:00 ICT Sat 14 Nov only permitted preparation: specs,
  architecture, data caches, generic libraries, scaffolding with placeholder data. Never pre-build the decision
  engine, final plan values, trained models or results, real product screens or final copy. Real screens and
  final copy start at 09:00 ICT Sat 14 Nov (frontend skeleton with placeholder data only before then).
- At least one NASA dataset. Declare every third-party resource and AI tool (including Claude Code and the skills
  in `.claude/skills/`) with version and licence. Third-party material must be public or OSI-licensed. Our code is
  Apache-2.0. Reproducible pipeline with data provenance. No personal data.
- Hanoi submission deadline: 11:00 ICT Sun 15 Nov 2026.

## No assumptions

- Never guess facts, numbers, sources, requirements, rules or what the team meant. If unsure, ask.
- Every number, threshold and method must be backed by data or published evidence. A source is never an AI tool.
- Decide routine technical choices yourself (file layout, test design, refactors) and say so.

## Coding standards (the spec-review skill checks changes against this section and `.claude/rules/*.md`)

Area conventions load automatically: `.claude/rules/python.md` (layers, naming, errors, tests) for Python files,
`.claude/rules/frontend.md` (file layout, api.ts, types, i18n, tests) for `frontend/`. Formatting and lint rules live
in `ruff.toml`, `frontend/eslint.config.js` and `frontend/.prettierrc.json`; `.editorconfig` and `.gitattributes`
keep files identical on every laptop. `tests/test_architecture.py` enforces the layer rules.

1. Tests first: write the test, run it, see it fail, then implement. Expected values come from the spec, real data
   or an external fact, never from the code under test.
2. Reuse before writing: search this repo for an existing function, component or pattern and use it the way the
   surrounding code does. Never write a second version of something that exists.
3. Smallest complete change: no option, wrapper, abstraction, config or "for later" code that nobody asked for.
   Name anything skipped in one line.
4. Dependencies: shipped (runtime) packages only from the spec's allow-list; development-only quality and security
   tools allowed (ruff, pytest, eslint, @eslint/js, typescript-eslint, prettier, gitleaks, pip-audit, npm audit).
   Exact pinned versions. Anything else needs team approval. CI checks `frontend/package.json` against
   `.github/scripts/dependency-allowlist.json`.
5. No hard-coded user-visible text in components; all of it comes from the Vietnamese and English text files.
6. Delete dead code and files you created that are no longer used. No commented-out code.
7. Comments explain why, in one line, only where the code cannot show it.
8. Never cut validation at trust boundaries, error handling, or accessibility.
9. Done means verified: run the tests (and the build) and report the real output before saying it works.

## Review loop

The `task` skill runs this loop for every task; follow it by hand only for work outside that skill.

1. After each chunk of work: `/simplify` (duplication, reuse, needless complexity in the changed code).
2. Before asking to merge a task branch: `/spec-review` from `main` (the standards above, plus the spec).
3. Before a screen counts as done: a Playwright check at 360 x 740 and `/cognitive-walkthrough` as a first-time
   farmer with an Android phone, little technical experience and nothing to type. The walkthrough is an
   expert-method review; never call it user testing.

## Model choice

Claude picks the model per job. Mechanical work (status, health, reminders, watching CI, reading logs) uses `haiku`;
the `progress`, `health` and `checkpoints` skills set it themselves, and helper agents for such work are started with
it. Writing code, reviews, planning, audits, submission checks and copy use the session's main model.

## Talking to the team

The team are AI engineers with no farming or agriculture background. Start from ML and software ideas they know,
then add the farming meaning. Explain each new term in plain words the first time. Short sentences, one idea at a
time. No internal labels without saying what they mean. Use the `ste` skill for explanations.

## Tools set up in this repo

- Layout: Python at the repository root (`pyproject.toml`, `requirements*.lock`, `src/`, `tests/`), frontend in
  `frontend/`. Deployed app: OPEN (set the URL here after the first deployment).
- CI (`.github/workflows/ci.yml`, pull requests only): hook tests, secret scan, Python lint, format, tests and
  dependency audit, frontend allow-list, lint, format, type check, tests, build, audit and browser tests. Run the same
  checks locally before pushing (listed in the `task` skill).
- Connectors in `.mcp.json` (approve each once on first start): Playwright (headless browser at 360 x 740),
  Chrome DevTools (slow-network emulation such as Slow 3G, Lighthouse and performance checks), Context7 (current docs
  for the exact pinned library versions; use it before writing code against a library API, for example Tailwind 3,
  not 4), Railway (deploy, environment, logs; each person signs in once).
- Playwright MCP: headless browser at 360 x 740 for phone-size checks.
  Save screenshots without a file name (they go to `.playwright-mcp/`, ignored by git), or delete them before a
  commit.
- Safety hook (`.claude/settings.json`, `.claude/hooks/guard.mjs`): blocks pushing to `main`, local merges into
  `main`, `gh pr merge` unless the gate passes, force pushes, branch deletion, `git reset --hard`, `git clean -f`,
  discarding all changes, and recursive deletes outside scratch folders. When it blocks a command, do not work
  around it; fix the reason or ask the team. Tests: `node --test .claude/hooks/guard.test.mjs`. A second layer, CC
  Safety Net, is installed per laptop (destructive commands, secret files).
- Workflow skills: `/plan-queue` (proposes the shared queue `.autopilot/queue.md` in a pull request; a person
  approves and merges it; items carry an owner and each person's autopilot runs only their own items), `/task` (one task
  end to end, merges through the gate), `/autopilot` (works through the approved queue, parks questions),
  `/progress` (phone-readable status), `/health` (deployed app and CI; `/loop 30m /health`), `/final-audit`
  (whole-project audit when features are done, proposes fixes), `/submission-check` (pre-submission audit).
  `/checkpoints` (phone reminders for the schedule; run in a separate idle session), `/vi-copy` (glossary-consistent
  Vietnamese and English text; glossary in `frontend/src/i18n/GLOSSARY.md`).
  `/plan-queue`, `/autopilot`, `/health`, `/final-audit`, `/submission-check` and `/checkpoints` run only when a
  person types them.
- Checks as tests: `tests/test_source_trace.py` (every displayed value has a source that is in the response and in
  the registers; hard rule H5), `tests/test_architecture.py` (layers). `scripts/attribution.py` prints the Python
  licence table for the README from the lock file.
- Other skills in `.claude/skills/`: `ste` (clear explanations), `cognitive-walkthrough` (task walkthrough as a
  first-time user), `spec-review` (two-axis review of a diff). Each third-party folder holds its licence;
  `spec-review/NOTICE.md` and `.claude/hooks/GUARD-NOTICE.md` list the changes made.
