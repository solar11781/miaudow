---
name: checkpoints
description: Schedule phone reminders for the hackathon checkpoints of the approved schedule (Sat 14 - Sun 15 Nov 2026, ICT). Run once at the start of the event in a separate session that stays open and idle with Remote Control connected. Use when the user runs /checkpoints.
disable-model-invocation: true
model: haiku
---

# Checkpoints

Reminders scheduled here live only in this session and fire only while it is idle. So: run this in its own session
(a second Claude window with Remote Control connected), not in the session that does the work, and leave it open.

1. Check the clock: `date`. The laptop must be on ICT (UTC+7). If not, stop and say so.
2. For every checkpoint below that is still in the future, create a one-shot reminder (CronCreate, `recurring:
   false`, minute and hour and day and month pinned) whose prompt is: send a PushNotification with exactly the
   message given, then do nothing else.
3. Reply with the list of scheduled reminders and their real next run times (from the CronCreate results).

| When (ICT) | Message |
|---|---|
| Sat 14 Nov 09:00 | Work starts. Opening ceremony in the organisers' Zoom; the code-move pull requests get prepared. |
| Sat 14 Nov 09:30 | Merge the code move and the approved queue; start the downloads in the background; create the Railway account and deploy the skeleton. |
| Sat 14 Nov 10:15 | 15 min to the 10:30 checkpoint: skeleton health check returns 200? Next: real-data pipeline, normal-yield method, freeze commit. |
| Sat 14 Nov 12:15 | 15 min to the 12:30 checkpoint: real-data pipeline done? If behind, re-plan the order; nothing is cut. |
| Sat 14 Nov 14:45 | 15 min to the 15:00 checkpoint: primary test done, gates.json written? If behind, re-plan; nothing is cut. |
| Sat 14 Nov 16:45 | 30 min to the end-to-end version (Tier 0, about 17:15). |
| Sat 14 Nov 17:15 | Finalise and check your evening queue before 17:30, then start the autopilot and go offline. |
| Sun 15 Nov 00:00 | Review the autopilot work; start the fresh-clone rebuild check in the background. |
| Sun 15 Nov 02:30 | 30 min to the feature freeze (03:00). After it: fixes, checks, docs, results only. |
| Sun 15 Nov 04:15 | 15 min to the first submission (about 04:30), with the cover slide as the demo link. |
| Sun 15 Nov 05:00 | Demo slides: at most 7, in English. |
| Sun 15 Nov 07:30 | Form fields in English; history and secret scan, then make the repository public; test every link in a private window; final deploy check; resubmit. |
| Sun 15 Nov 09:45 | 15 min to the final resubmit (10:00). Check the submitted status afterwards. |
| Sun 15 Nov 10:50 | 10 min to the 11:00 hard deadline. Then the frozen production branch and the tag `submitted-hanoi`. |
| Sun 15 Nov 16:30 | Closing ceremony. After it, switch the project page and the app link to the improved version. |
| Sun 15 Nov 23:29 | 30 min to the global deadline (23:59). |

The times follow the approved schedule for the 09:00 start (team decisions D-144 and D-154; the times are planning
estimates); if the team changes the schedule, change this table.
