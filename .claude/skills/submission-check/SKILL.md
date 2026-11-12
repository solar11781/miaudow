---
name: submission-check
description: Pre-submission audit of the repository and app against the Space Apps Hanoi rules and the judging criteria; reports PASS, FAIL, MANUAL or UNKNOWN with evidence and changes nothing. Use when the user says "submission check", "are we ready to submit" or runs /submission-check.
disable-model-invocation: true
---

# Submission check

Report only. Change no file, branch, deployment or setting. Every PASS needs evidence (file and line, command output,
or a page checked). If something cannot be checked from here, mark it MANUAL and say who checks it and how. Never
guess; UNKNOWN is a valid answer.

Hanoi submission: by the Team Owner on spaceappschallenge.org before 11:00 ICT Sun 15 Nov 2026 (team plan: final
resubmit 10:00; resubmitting is unlimited until the deadline).

## Checklist

1. NASA data: at least one NASA (or partner agency) dataset is used in the code and named in the README and in the app.
2. Preparation: the README has a section "What was prepared before the event".
3. Attribution and AI disclosure: the README lists every third-party resource and AI tool with version, licence and
   role. Cross-check against the dependency files (package.json, Python lock files), datasets, papers, Claude Code,
   every folder in `.claude/skills/` (its licence file and notice), `.claude/hooks/` (its notice), `.mcp.json`
   servers, and any other tool named in `CLAUDE.md`.
4. Licences: every third-party item is public or OSI-licensed and its licence is declared. Restricted material is not
   in the repository or its history: journal PDFs, national-standard texts, FAO .CRO files, raw NSO statistics files.
5. Our licence: `LICENSE` at the root is Apache-2.0.
6. Reproducibility: dependencies pinned to exact versions; data provenance (source URL, access date, checksum) for
   every input; run instructions in the README that work from a fresh clone (try it in a temporary folder if
   feasible, otherwise MANUAL).
7. Secrets and personal data: search tracked files and the whole history (`git grep`, `git log -p`) for keys, tokens,
   passwords, private keys, `.env` content, e-mail addresses and phone numbers. No commercial promotion, no images of
   minors.
8. No link to the team's planning repository: ask the team for its name if you do not know it, then search files and
   history for it.
9. Contributions: both team members appear in the git history.
10. Challenge fit: the README or project page maps features to the Field Shift objectives.
11. Scientific boundaries of `CLAUDE.md`, checked in the code and on the running app (Playwright, 360 x 740): every
    displayed number has a source and a fact-only trust label; no past year is shown as a forecast; revenue is not
    called profit; no farm-specific yield prediction.
12. Form fields, in English: Project Name; High-Level Summary; Project Demo (at most 7 slides including the cover, or a
    video of at most 30 seconds that shows the product working and names the NASA data; spoken Vietnamese needs
    English subtitles); Final Project link; Project Details; Use of AI (each AI tool and what it was used for); NASA
    Data (at least one); References (every external source: libraries, images, music, articles, AI tools). Text not in
    the repository is MANUAL.
13. Links: every link opens for anyone with the link. Check each with Playwright (isolated, not signed in); a link
    that needs sign-in is FAIL.
14. Judging criteria (Impact; Creativity; Validity: scientific basis and real-world use; Relevance: answers the
    chosen challenge, NASA data is a core part; Presentation: clear, has a demo, tells a story): for each, the
    evidence present and the biggest gap. No numeric scores.

## Output

A table: number, item, PASS / FAIL / MANUAL / UNKNOWN, evidence or reason. Then the FAIL items in order of risk, one
line each with the fix. At most 25 lines in total.
