---
name: health
description: Check that the deployed app and the latest CI runs are healthy, and record any failure as a parked question and a proposed fix item. Read-only apart from the local status files and a proposal pull request. Use when the user runs /health, or on a timer with "/loop 30m /health".
disable-model-invocation: true
---

# Health

1. Deployed app: read the URL from "Deployed app" in `CLAUDE.md`. If it is not set, say so and skip to step 3.
2. Request `<url>/api/health` (expect HTTP 200) and open the home page with Playwright at 360 x 740 (expect it to
   load without console errors). Record the real status codes and errors.
3. CI: `gh run list --limit 10`; note any failed run on an open pull request or on `main`.
4. If everything is healthy: add one line `health ok <HH:MM> ICT` to `.autopilot/status.md` and reply in one line.
5. If something failed: add a line to `.autopilot/status.md`, a question to `.autopilot/parked.md` with the evidence,
   and a proposed `fix/...` item in a pull request that adds it to `.autopilot/queue.md` under `proposed by health
   (needs team approval)`. It runs only after a person merges that and moves it into the approved list, or if the
   approved queue holds a standing item allowing health fixes.

Reply in at most five lines.
