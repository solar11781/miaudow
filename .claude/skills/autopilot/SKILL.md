---
name: autopilot
description: Work through the team's task queue alone, one task skill run per item, parking questions instead of asking, and keeping a short phone-readable status file. Use when the user says "start autopilot", "start evening autopilot", "continue autopilot" or runs /autopilot.
disable-model-invocation: true
---

# Autopilot

The team is away or on a phone. Work only on tasks that can be finished and checked without a person (tests,
metrics, automated checks). The team keeps control through three checkpoints: the queue they approve, the parked
questions they answer, and the merge gate (CI green, branch up to date, reviews clean; D-124), which the safety hook
enforces. Anything the gate refuses waits for the team.

## Files

- `.autopilot/queue.md`, shared, on `main`: the approved queue (drafted by `plan-queue`, approved and merged by a
  person). Always read the latest: `git fetch origin && git show origin/main:.autopilot/queue.md`. Never edit it
  on `main`; changes go through a pull request that a person merges.
- `.autopilot/status.md` (local to this laptop, ignored by git): you keep it. One line per item: `<n>. <running | merged | waiting-merge | parked | skipped>
  <short note> <PR link>`, newest change first line `updated <HH:MM> ICT`.
- `.autopilot/parked.md` (local, ignored by git): questions for the team, each with the item number, the question, the options seen, and
  what you did meanwhile.

## Start

1. If the queue on `origin/main` does not exist, is empty, or its first line is not `status: APPROVED`: stop and ask
   the team to approve one (the `plan-queue` skill drafts it). Never invent or approve the queue yourself.
2. Read `CLAUDE.md` and the queue. Items under a heading that says "needs team approval" do not run until the team
   moves them into the approved list.
3. Ask once, before going alone, whose items to run (the `owner:` value), unless the start message names it. Run only
   that owner's items, so two people's sessions never work on the same item. Reply with those items in one line each,
   then begin.
4. On "continue autopilot": read `status.md` and resume at the first item not marked merged, skipped or
   waiting-merge.

## For each item

0. Check the clock (`date`). If a checkpoint of the `checkpoints` skill's table passed since the last check, send its
   message with PushNotification and note it in `status.md` (reminders scheduled elsewhere do not fire while this
   session is busy).
1. Mark it `running` in `status.md`.
2. Run the `task` skill for it. Under the autopilot, the task skill parks questions instead of asking.
3. Check the item's "done when" yourself, with the real command output.
4. Mark it `merged` with the pull request link, `waiting-merge` with the gate's reason, or `parked` / `skipped`
   with one line why. A later item that needs a `waiting-merge` item: park it.

## When something is unclear or blocked

- Questions go to `parked.md`; then continue with the next item.
- Only for a genuine blocker (no further item can proceed without an answer): use the best-practice option, record it
  as a PROVISIONAL decision with the alternatives in the team's decision log, continue, and list it in `parked.md`.

## Rules

- No destructive actions, no paid services, no rule-sensitive actions, no changes to decided specs.
- Full test suite green before every commit. Merge only through the task skill's gate; never push to `main`.
- After the feature freeze (23:30 ICT Sat 14 Nov 2026): only fixes, checks, documentation and results.

## End

When no item is left: write a final block in `status.md` with what was merged, what waits for the team (with the
gate's reason), and the parked questions. Reply with the same in at most ten lines. Suggest `/final-audit` when the
queue covered all planned features.
