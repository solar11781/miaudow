---
name: plan-queue
description: Turn the team's planning documents into a draft task queue for the autopilot - small ordered items with owners, each tied to spec lines and acceptance tests with an objective "done when". Proposes .autopilot/queue.md in a pull request; only a person approves and merges it. Use when the user runs /plan-queue.
disable-model-invocation: true
---

# Plan queue

Draft only. The queue is shared by the whole team: it lives in `.autopilot/queue.md` on `main`. Write it on a branch
`docs/queue-<YYYYMMDD-HHMM>` from the latest `main`, with first line `status: DRAFT`, push, and open a pull request.
Never write `APPROVED` and never merge it: a person reviews it, changes the first line to `status: APPROVED` and
merges it on GitHub (the merge gate refuses queue changes from Claude).

## Read

The planning documents (see "Specs" in `CLAUDE.md`): the implementation plan (milestones, demo tiers, schedule, cut
list), the requirements, the UI/UX spec with its hard rules and acceptance tests, the data contracts, the ML spec, the
tech design and the decision log. Also the current code, `git log`, and any existing `.autopilot/status.md`, so done
work is not queued again. If `main` already has an approved queue, the draft replaces it in the pull request; keep
the numbers and status of items already merged.

## Items

Each item is one pull request (aim for a diff under about 400 lines). In plan order: the earliest demo tier first,
dependencies before the items that need them, cut-list items last. Each item has:

- `<n>. <type>/<short-name>`: one line saying what is built.
- `owner:` the team member whose column of the plan's schedule holds this work (pipeline, ML and backend in one
  column, frontend in the other), written as in the plan. A change to the shared data contract (types, schemas,
  fixtures on both sides) is one item with one owner that updates both sides in the same pull request.
- `spec:` the exact sections and decision IDs it implements.
- `tests:` the acceptance test IDs or requirement IDs it must satisfy, and the test files to write first.
- `done when:` objective checks only (commands and their expected result, test IDs green, CI green).
- `not before:` the earliest time the competition rules allow it (see `CLAUDE.md`); `now` for tooling and scaffolding
  with placeholder data only.
- `team input:` `none`, or the exact open question (science, numbers, rules, scope, wording). Items with team input
  park until answered; never fill the gap with a guess.
- `if blocked:` park, skip or continue (from the plan's cut list where it says so).

## Coverage table (end of the file)

List every acceptance test ID, hard rule ID and requirement ID from the specs with the item number that covers it.
Mark each uncovered one `NOT COVERED` with a reason. Do not invent IDs; copy them from the documents.

## Reply

At most ten lines: the pull request link, number of items per owner, what the first five are, uncovered IDs, open
team questions, and the reminder that a person approves by changing the first line to `status: APPROVED` and
merging.
