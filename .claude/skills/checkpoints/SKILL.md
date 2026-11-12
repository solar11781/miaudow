---
name: checkpoints
description: Schedule phone reminders for the hackathon checkpoints of the approved schedule (Sat 14 - Sun 15 Nov 2026, ICT). Run once at the start of the event in a separate session that stays open and idle with Remote Control connected. Use when the user runs /checkpoints.
disable-model-invocation: true
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
| Sat 14 Nov 00:00 | Work starts. Scope freeze. Pipeline on real data next (00:30). |
| Sat 14 Nov 03:45 | 15 min: primary model test window starts at 04:00. |
| Sat 14 Nov 07:45 | 15 min: deploy the backend with real data (08:00-09:00). |
| Sat 14 Nov 08:50 | Opening ceremony at 09:00. Hand-over to the frontend member. |
| Sat 14 Nov 15:30 | 30 min to the end-to-end version (Tier 0, 16:00). Run /submission-check after it. |
| Sat 14 Nov 17:15 | Finalise and approve the evening queue before 17:30, then start the autopilot. |
| Sat 14 Nov 23:00 | 30 min to the feature freeze (23:30). After it: fixes, checks, docs, results only. |
| Sun 15 Nov 02:45 | 15 min: first submission of the form (03:00). Then the honesty review. |
| Sun 15 Nov 05:30 | Demo: at most 7 slides including the cover, in English. |
| Sun 15 Nov 07:30 | Form fields in English; secret scan, then make the repository public; test links in a private window. |
| Sun 15 Nov 09:45 | 15 min to the final resubmit (10:00). Check the submitted status afterwards. |
| Sun 15 Nov 10:50 | 10 min to the 11:00 hard deadline. |

The times follow the approved schedule (team decision D-87); if the team changes the schedule, change this table.
