# Miaudow

*Say it like "meadow", with a cat's "miau" in it.*

Miaudow is a visual, Vietnamese-language decision-support tool for farmers on drought-prone, low-productivity rice
land in Nghệ An, Vietnam. It lets a farmer compare a few evidence-backed one-year crop sequences, including keeping
rice, under past years labelled with Vietnam's official hazard conditions. Each plan is one card that shows income,
climate risk, water and land care, with the farmer's own priorities highlighted. Miaudow compares; it does not
dictate.

Built for the **NASA Space Apps Challenge 2026**, challenge **"Field Shift: Adapting Farms with NASA Data"**, by a
team of two in Hanoi (14-15 November 2026).

> **Status:** preparation only. The product itself is built during the event (14-15 November 2026), as the
> competition rules require. Sections marked *completed during the event* are filled in then.

## What Miaudow shows, and what it does not

- Regional estimates only, never a yield prediction for one farm.
- Past years are past years, never presented as a forecast.
- Revenue is not profit; profit is shown only as a study reported it, with its source.
- Every number on screen has a source, and a label made only of facts about that source.

## How it works

*Completed during the event:* the data pipeline, the model and its validation, the comparison engine and the screens.

## NASA data used

*Completed during the event.*

## Run it yourself

*Completed during the event:* install, rebuild the data and results from the original public downloads, run the tests,
start the app.

## What was prepared before the event

The competition allows preparation before the event (architecture, specifications, data caches, generic libraries,
scaffolding with placeholder data). This repository was prepared with development tooling only:

- Development workflow rules for the AI coding assistant (`CLAUDE.md`, `.claude/`): coding standards, a safety hook
  that blocks destructive git and file commands, and workflow skills (one task per branch, tests first, review,
  merge only when every check passes).
- Continuous integration (`.github/workflows/ci.yml`): tests, lint, format, type checks, secret scan and dependency
  audits on every pull request.
- Shared code style and architecture checks (`ruff.toml`, `frontend/eslint.config.js`, `frontend/.prettierrc.json`,
  `tests/test_architecture.py`, `tests/test_source_trace.py`).

*Completed during the event:* the generic libraries and data caches brought in from preparation.

## Attribution and AI disclosure

*Completed during the event:* every dataset, paper, library and tool with its version, licence and role.

AI tools used: **Claude Code** (Anthropic), as a coding, research and documentation assistant. Development tools and
Claude Code skills used in this repository, all used for development only and not shipped in the app:

| Tool | Licence | Role |
|---|---|---|
| CC Safety Net (kenryu42) | MIT | blocks destructive commands and secret-file reads |
| Safety hook, based on Matt Pocock's git-guardrails (mattpocock/skills) | MIT | blocks pushes to main, force pushes, branch deletion; merge gate |
| Skills `ste` (Johnathan Mo), `cognitive-walkthrough` (mastepanoski), `spec-review` (Matt Pocock, renamed from `code-review`) | MIT | clear explanations, usability walkthrough, code review against standards and spec |
| Playwright MCP (Microsoft) | Apache-2.0 | browser checks at phone size |
| Chrome DevTools MCP (Google) | Apache-2.0 | slow-network and performance checks |
| Context7 MCP (Upstash) | MIT (server); hosted service under Upstash terms | version-specific library documentation |
| Railway MCP (Railway) | Railway terms | deployment and logs |
| GitHub CLI | MIT | pull requests |
| ruff, gitleaks, eslint, typescript-eslint, prettier | MIT | lint, format, secret scan |
| pip-audit | Apache-2.0 | Python dependency audit |

## Licence

Our code is licensed under the Apache License 2.0 (see `LICENSE`). Data and published sources are not covered by this
licence; each keeps its own terms, listed in the attribution above.
