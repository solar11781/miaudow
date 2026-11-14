---
name: task
description: Run one task end to end on its own branch - failing test first, implement, review, push, pull request, CI, security review - and merge it only when every gate is green. Use when the user gives a feature or fix to build ("task ...", "build ...", "fix ..."), or when the autopilot skill hands over the next queue item.
argument-hint: "<type>: <what to build>"
---

# Task

One task, one branch, one pull request, merged only through the gate (team decision D-124): CI fully green, branch
up to date with `main`, and a gate record showing spec-review and security-review found no open issue. The safety
hook checks the gate itself; never try to get around it.
Structure based on Matt Pocock's `implement` skill (mattpocock/skills, MIT), changed to this project's rules.

## 0. Before starting

- Read `CLAUDE.md` (rules, timing, coding standards) if it is not already in context.
- Check the timing rules in `CLAUDE.md`: if the task is product work that is not allowed yet, stop and say so.
- `git status --short` must be clean. If it is not, stop and report what is uncommitted.
- Find the specs (see "Specs" in `CLAUDE.md`).

## 1. Understand

- Restate the task in one or two lines.
- Find the spec lines that define it and quote them (file and section).
- If the spec does not say what should happen, stop and ask (under the autopilot skill: park the question).

## 2. Branch

- Type: one of the commit types in `CLAUDE.md`. Name: `<type>/<short-name>`, lowercase with hyphens.
- `git fetch origin`, then `git checkout -b <branch> origin/main` (use local `main` if `origin/main` does not exist yet).
- If the task needs another task branch that is not merged yet, branch from that branch instead and say so in the
  pull request ("based on <branch>; merge that first").

## 3. Tests first (the same checks CI runs, locally, before every push)

Local checks: Python `ruff check .`, `ruff format --check .`, `pytest -q`; frontend (in `frontend/`) `npx eslint .`,
`npx prettier --check .`, `npx tsc --noEmit -p .`, `npx vitest run`, `npx vite build`, and `npx playwright test` for
screens. Run the ones for the code you touched.


- Write the test or tests from the quoted spec lines. Expected values come from the spec, real data or an external
  fact, never from the code.
- Run them and confirm they fail for the expected reason. Commit: `test: <what the tests pin down>`.

## 4. Implement

- Smallest complete change (coding standards in `CLAUDE.md`).
- Run the full test suite, plus the build or type check where one exists. Everything must pass.
- If the same step fails twice, stop and report the evidence instead of trying random fixes.

## 5. Review

Run every review skill (`simplify`, `spec-review`, `security-review`) inside its own Agent subagent, so its report
comes back to this task; a review never ends the task. Then continue with the next step.

1. Run the `simplify` skill on the changes; run the tests again.
2. Run the `spec-review` skill with `main` as the fixed point; fix the real findings; run the tests again.
3. For a user-facing screen: a Playwright check at 360 x 740 and the `cognitive-walkthrough` skill as described in
   `CLAUDE.md`.

Every review is thorough and double-checked (team decision D-152, 2026-11-14):

- Check each finding against the code before acting on it. Fix the real ones; for each one dismissed, write the reason
  (the code line or spec line that shows it is not a problem).
- After the fixes, run the full checks and every review of this step a second time on the final state. Only a clean
  second pass counts; if it finds something new, fix it and run that pass again.
- Report both passes in the pull request: findings, fixes and dismissals with their reasons.

## 6. Commit and push

- Commits as in `CLAUDE.md` ("Branches, commits and merging"): one logical step each, for example the failing test,
  the implementation, each review fix, the docs.
- `git push -u origin <branch>`. Never push to `main`, never force push. The safety hook blocks these; if it blocks
  something, do not work around it, report it.

## 7. Pull request

Write the body: what and why (one or two lines), the spec lines it implements, the tests run and their real result,
review findings fixed and left open, what was skipped, risks. A task from the queue names its item in the title, for
example `chore: switch the gate to normal merges (queue item 0)`.

- If `gh` is installed and signed in (`gh auth status`): `gh pr create --base main --head <branch> --title
  "<type>: <summary>" --body "<body>"`.
- Otherwise (no `gh`, or a cloud session where `gh pr` is blocked): give the link
  `https://github.com/<owner>/<repo>/compare/main...<branch>?expand=1` (from `git remote get-url origin`) and the
  body text, then stop at step 9: without `gh` the merge gate cannot run, so the team merges.

## 8. CI, security review, gate record, merge

1. `gh pr checks <number> --watch`. If a check fails: read the log (`gh run view --log-failed`), fix it on this
   branch, run the local checks, push, watch again. After three failed rounds, stop and report the evidence.
2. If `main` moved: `git fetch origin && git merge origin/main` on this branch (never rebase pushed work), run the
   local checks, push, and let CI run again.
3. Run the `security-review` skill on the branch (inside an Agent subagent, as in step 5), double-checked as in step
   5 (a fix goes back to 1). A finding that needs a decision
   about science, rules, numbers or scope: stop and ask (under the autopilot: park it, do not merge).
4. When CI is green, the second passes of spec-review and security-review have no open issue, and no commit came
   after them, post the gate record as a pull request comment, with this exact last line:
   `review-gates: spec-review=pass security-review=pass tests=pass`
   Above it, list the evidence: check names and results, findings of both passes and what was done with each.
5. Merge: `gh pr merge <number> --merge` (or `-m`; the merge rule in `CLAUDE.md`), run alone. If the hook refuses,
   read its reason, fix that, and retry; never change the command to get around it.
6. A task from the queue: add the line `- done: <date time ICT>, pull request #<n>` under the item in the planning
   repository's queue draft (not `.autopilot/queue.md`, which a person merges) and push it there at once, so a member
   who joins later sees it. If this session does not have the planning repository, give that line to the team in the
   report instead. Never name, link or give a path to the planning repository in this repository.

## 9. Report

At most eight short lines: branch, pull request link, CI result, merged or not (and why), open points.
