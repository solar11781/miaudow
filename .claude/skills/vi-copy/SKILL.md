---
name: vi-copy
description: Write or review Vietnamese and English interface text so every screen uses the same terms from the shared glossary, in plain words a farmer with little technical experience understands. Use whenever user-visible text is written or changed (frontend/src/i18n/*.json, API Text fields), or when the user asks to check the copy.
---

# Vietnamese and English copy

Final copy is written during the event only (from 09:30 ICT Sat 14 Nov). Before then, keep placeholder values.

## Before writing

1. Read `frontend/src/i18n/GLOSSARY.md`. Every concept in it is written with exactly its glossary term, in both
   languages, everywhere: no synonyms, no shortened forms.
2. A concept that is not in the glossary yet: if it names something official (a hazard level, a season, a rule, a
   crop or a unit), take the wording from the cited source in the team's research notes, add a glossary row with the
   source, and use it. If no source gives the wording, do not invent one: ask the team (under the autopilot: park).

## Writing

- Readers: farmers on their own Android phone, little technical experience, nothing to type (UI/UX spec section 1).
  Short sentences, one idea each, everyday words, no technical or statistical terms on farmer screens.
- Every string goes in `vi.json` and `en.json` under the same key; the English says the same thing, not more.
- Fixed sentences come from the i18n files; data-dependent text comes from the API (hard rule H15).
- Text must fit 360 px at the spec's font size without horizontal scroll (hard rule H10). Check long strings with
  Playwright at 360 x 740.
- Never phrase a past year as a forecast, revenue as profit, or a regional number as the farmer's own field.

## Review (also when asked to check the copy)

Search both files for every glossary concept and for its likely synonyms; report each place that uses a different
term, each key missing in one language, and each farmer-screen string with a technical word. The text review is
done by a native speaker of the team; this skill prepares it, it does not replace it.
