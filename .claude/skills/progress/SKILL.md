---
name: progress
description: Phone-readable project status in at most ten lines - what is done, running, parked, and waiting for the team to merge. Use when the user asks "status", "progress", "what's done", "what's waiting for me" or runs /progress. Read-only.
---

# Status

Read-only: change no file, branch or setting.

Collect:
1. `.autopilot/status.md` and `.autopilot/parked.md`, if they exist.
2. `git fetch origin --quiet`, then `git branch -r --no-merged origin/main` (task branches waiting to be merged; if
   `origin/main` does not exist yet, say so).
3. Open pull requests: `gh pr list --state open` if `gh` is installed and signed in; otherwise skip this line.
4. Current branch and whether there are uncommitted changes (`git status --short`).

Reply in at most ten short lines, in this order:
- `Waiting for your merge:` branches or pull requests, in merge order where one is based on another.
- `Questions for you:` parked questions, one line each (number and question).
- `Running:` / `Done:` from the status file.
- `Here:` current branch, clean or not.

No jargon; if a line has nothing, leave it out.
