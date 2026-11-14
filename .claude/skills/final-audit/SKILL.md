---
name: final-audit
description: Whole-project audit when the planned features are finished - spec traceability, a fresh-clone run of every CI check, security, scientific boundaries, code quality, the farmer walkthrough and the submission check. Reports findings and proposes fix items; changes no code. Use when the user runs /final-audit.
disable-model-invocation: true
---

# Final audit

Report and propose; change no code, branch, deployment or setting. Every finding cites evidence (file and line,
command output, or a page checked). Independent parts may run as parallel subagents; give each one its scope and the
evidence rule. Write the full report to `.autopilot/audit.md`.

## 1. Fresh clone, every check

Clone `origin/main` into a temporary folder and run every check CI runs (see `.github/workflows/ci.yml`), plus the
README's run instructions. Record the real results. A step that only works on this machine is a finding.

## 2. Spec traceability

A table of every requirement ID, hard rule ID, acceptance test ID and ML gate from the specs (see "Specs" in
`CLAUDE.md`): where it is implemented (file and line), which test proves it, status `covered`, `partial` or
`missing`. Copy IDs from the documents; never invent them. Then run the `spec-review` skill with the first commit of
`main` as the fixed point.

## 3. Security

Run the `security-review` skill on the whole repository. Scan the full history for secrets (`gitleaks git` if
installed, otherwise `git log -p` searches for keys, tokens, passwords, private keys and `.env` content). Run the
dependency audits from CI. Check that the API validates its inputs and that no personal data is stored or logged.

## 4. Scientific boundaries

Every boundary in `CLAUDE.md`, checked in the code and on the running app with Playwright at 360 x 740: sources and
fact-only trust labels on every displayed number, no past year shown as a forecast, revenue never called profit, no
farm-specific prediction, model results shown only when the spec's gates pass.

## 5. Code quality

Run the `simplify` skill on the whole repository in report mode, and look for duplicated logic, dead code, unused
files and dependencies, commented-out code, TODOs, and hard-coded user-visible text (coding standards in `CLAUDE.md`).

## 6. People

Run the `cognitive-walkthrough` skill for the main farmer task on the running app at 360 x 740 (expert-method review,
not user testing).

## 7. Submission

Run the `submission-check` skill.

## Output
 In `.autopilot/audit.md`: the table of sections 1 to 7 with PASS / FAIL / UNKNOWN and evidence, then every FAIL as a
proposed queue item (format of the `plan-queue` skill) under the heading `proposed by final-audit (needs team
approval)`. Append the same items to `docs/AUTOPILOT-QUEUE.md` in the planning repository (see "Specs" in `CLAUDE.md`)
under that heading and push them there; the items run only after the team moves them into the approved list. Reply in at
most fifteen lines: counts per section, the worst five findings, and where the report is.
