# UI/UX specification: Miaudow (frontend; the app name is Miaudow in both languages, the project is Field Shift Nghệ An)

This is the frontend specification for the current design only. It is version 1.4 of 2026-11-13, with the team's
later event decisions applied up to 2026-11-15; earlier versions are in the git history.
Owner: team (Dev B builds). Status: APPROVED; nothing is built before 09:00 ICT Sat 14 Nov 2026. From 09:00 the
skeleton of section 13 is built first, then the screens (section 2). All file paths in this document are relative to
the frontend project folder `frontend/` (for example `src/i18n/vi.ts` = `frontend/src/i18n/vi.ts`).

During the event the team's redesigned web app became the product frontend in `frontend/`. Its farmer cards, past
years and method page read our API (`/api/past-years`, `/api/compare`, `/api/method`), so every number they show is a
number the engine traced to its source (H5). The app's extra pages (observatory, evidence library, copilot) were kept.
Where that app's own route names, URL keys or test hooks differ from the names below, the app's names apply (sections
3, 6, 6b and 14a).

We wrote this document so that a developer or a coding agent can implement it without having to interpret anything.
The words MUST, MUST NOT, SHOULD follow RFC 2119. If something is not specified here, do not invent it. Stop and ask
instead (open questions go to section 15). Every rule cites its reason (sources refer to REFERENCES.md; "team
decision" marks a choice the team made). "(routine)" marks a routine technical choice made by Claude under the
autonomy rule of CLAUDE.md.

There are no sketch images; this text is the only specification.

---

## 1. Who the users are (this decides everything)

| User | Device | What they need | Evidence |
|---|---|---|---|
| **Primary: farmer** on drought-prone rice land in Nghệ An | own Android phone, often a small screen, sometimes weak internet; limited technical experience | big text, few steps, pictures, Vietnamese, no technical words, nothing to type | Challenge page: "easily interpretable for farmers who may have limited technical or geospatial experience"; Medhi et al. 2011 (R-U06); IRRI/IFAD 2022 brief (R-U07): "simple interfaces, printable formats ... large font sizes" |
| **Secondary: extension officer (cán bộ khuyến nông) or cooperative leader** showing the phone to a farmer | phone or laptop | the same screens, plus sources and limitations one tap deeper | IRRI/IFAD 2022: face-to-face extension is the most common channel; Rose et al. 2016 (R-U11): advisers trust transparent evidence |
| **Tertiary: judges** | laptop | method, data, limitations, optional advanced map view | Space Apps judging |

Because of these users, the farmer path is a short, flat sequence of 2D screens (sections 6-10). Anything advanced,
such as maps or 3D, lives on a separate page that the farmer path never depends on (section 12).

---

## 2. Timing rule (competition rules)

- Before 09:00 ICT Sat 14 Nov 2026 (when team work starts) nothing is built in miaudow. From 09:00 the skeleton
  (section 13: project setup, routing, layout shell, reusable UI components, i18n mechanism, fixture loading and
  tests, with fake placeholder data) is built first, then the real screens, wording, plan data and copy.
- GO Team reply: "refrain from starting on their projects until the start of the official November 14-15
  hackathon (Saturday, 9am local time ...). Working ahead of the hackathon can lead to disqualification".
- Reason: Hanoi rules IV.2 ("phần lõi sản phẩm phải được phát triển trong thời gian thi"); SEPA page "Dự án làm trước
  sẽ bị loại"; organizers' reply allows preparing "kiến trúc ... và khung mã nguồn (codebase)".
- Later features (the map page of section 12, sign-in of section 12c, price entry of section 12d) start only after
  every section 14 test passes for the farmer routes and the team says go. The team gave that go during the event
  for all three.

---

## 3. Technology (fixed)

| Item | Choice | Reason |
|---|---|---|
| Framework | React + Vite; the first skeleton used Tailwind CSS 3 (latest 3.x at setup), the team's web app that became the product frontend does not use Tailwind | team decision; major version: routine |
| Language | TypeScript (strict mode) | routine choice (Claude): typed data contract below |
| Routing | react-router-dom with hash routing (`createHashRouter`), the team's web app's choice kept at integration: the route and the step answers both sit in the URL fragment, for example `#/nong-dan/...?ruong=&nam=&uutien=` (section 6b), so a shared link opens the same view and the server needs no route rewrites. Every page also has an English path (for example `/farmer`, `/assistant`, `/method`, `/sign-in`, `/saved`) that opens the same page in English; the Vietnamese paths stay the main ones | team decision |
| i18n | plain TypeScript dictionaries `src/i18n/vi.ts` and `src/i18n/en.ts`, read through `useT()` (section 6d); no i18n library | routine; keeps the bundle small for weak internet (R-U07) |
| Fonts | system font stack that supports Vietnamese: `system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans", Arial, sans-serif`; a web font only when served from the app itself (no third-party font request, T14), under a redistributable licence, with Vietnamese glyphs, `font-display: swap` and this stack as fallback. Web fonts in use: Be Vietnam Pro, Alegreya (variable) and Charm, all SIL OFL 1.1 | small download (R-U07); team decision |
| Backend | FastAPI over precomputed JSON. The frontend reads the API in section 11; until the backend exists it reads the same JSON from `public/fixtures/` (= `frontend/public/fixtures/`) | team decision |
| Versions | pin exact versions in package.json at setup time (no `^` or `~`) | reproducibility (CR-07) |

Dependency allow-list: package.json MUST contain only these packages (routine; it keeps pages small for weak
internet, R-U07). Any other package needs team approval first (name, exact version, licence, shipped size, purpose).
CI checks `frontend/package.json` against `.github/scripts/dependency-allowlist.json`.

| Kind | Packages |
|---|---|
| Runtime | `react`, `react-dom`, `react-router-dom` |
| Runtime, fonts (self-hosted, only the imported weights and subsets ship) | `@fontsource/be-vietnam-pro`, `@fontsource-variable/alegreya`, `@fontsource/charm` (all OFL-1.1) |
| Runtime, 3D on lazy routes outside the farmer routes (H1) | `cesium` (Apache-2.0; 3D globe on `/dai-quan-sat`; `@cesium/engine`, `@cesium/widgets`, `@cesium/core` pinned through overrides; no Cesium ion use, no access token), `three` (MIT; WebGL grid on `/khoa-hoc`) |
| Runtime, motion (under H1: off with reduced motion, pausable) | `gsap` 3.15.0, `@gsap/react` 2.1.2 (GSAP "Standard no-charge licence": free for all use, not OSI) |
| Build | `vite`, `@vitejs/plugin-react`, `typescript`, `@types/react`, `@types/react-dom`, `@types/node`, `tailwindcss` (3.x), `postcss`, `autoprefixer` (the tooling Tailwind 3 requires) |
| Test | `vitest`, `jsdom`, `@testing-library/react`, `@testing-library/dom` (peer dependency of `@testing-library/react`), `@playwright/test` |
| Licence notices | `rollup-plugin-license` (writes the third-party licence file shipped with the bundle and listed on `/nguon`) |
| Code quality and security (development only, never shipped) | `eslint`, `@eslint/js`, `typescript-eslint`, `prettier`, `eslint-plugin-react-hooks`, `globals`; in CI also `gitleaks` (secrets) and `npm audit` (built into npm) |
| Other development only (never shipped) | `@axe-core/playwright` (accessibility checks in the browser tests), `@testing-library/user-event` (user events in tests), `@types/three` |

The following are not on the list and so need team approval: UI kits, chart or map libraries, other 3D or animation
libraries, state-management libraries, i18n libraries, validation libraries, analytics, trackers, cookies and service
workers. The small-bundle reason (R-U07) applies to packages that ship to the phone, and development-only tools never
ship. The libraries of the optional map page are chosen in its own spec (section 12) and need team approval like any
other addition.

---

## 4. Hard rules (MUST / MUST NOT)

Each rule has a test in section 14. Route sets used below (routine):
- **Farmer routes**: `/`, `/ruong`, `/nam`, `/uu-tien`, `/phuong-an`, `/khong-co-phuong-an`. In the product frontend
  the farmer steps sit under the hash route `#/nong-dan/` with the app's own names (section 6).
- **All pages**: the farmer routes plus `/phuong-phap`, `/gioi-thieu`, `/nguon`, and the extra pages of the team's web
  app (`/can-bo`, `/khoa-hoc`, `/bang-chung`, `/dai-quan-sat`, `/tro-ly`) with the exceptions named in H1 and T14;
  `/ban-do`, `/dang-nhap` and `/da-luu` get their rules from their own sections (12, 12c) when they are built.

| # | Rule | Applies to | Reason |
|---|---|---|---|
| H1 | MUST NOT use video on any page, or 3D, WebGL or `<canvas>` on the farmer routes (those load only on other pages); every animation and CSS transition MUST be off under `prefers-reduced-motion: reduce`, pausable if it starts by itself and lasts over 5 s, never flash more than three times a second, and never be the only way to see content or act | all pages | team decision (relaxed during the event from a rule of no motion at all); WCAG 2.2 SC 2.3.3, 2.2.2, 2.3.1; earlier basis: challenge page, Medhi 2011 (routine) |
| H2 | MUST NOT use sliders (`<input type="range">` or any slider component) | all pages | Funke 2016; Couper 2006 (R-U01, R-U02) |
| H3 | MUST NOT show scores, ranks, stars, "best/recommended" badges, or sort plans by any value | all pages | UK MCA manual (R-E14); "It compares; it does not dictate" (CLAUDE.md) |
| H4 | MUST NOT have free-text input fields | farmer routes | Medhi 2011: "Avoid requiring nonnumeric text input" |
| H5 | Every sourced number shown (section 4a) MUST reach its source sheet (section 10) in one tap: either the number is itself a button that opens the sheet, or, where numbers sit inside another button (year rows, section 8) or a table row (method metrics, section 11b), the number is plain text and the one "?" button named in its section opens the sheet. Numbers without a source MUST NOT be shown | all pages | CLAUDE.md |
| H6 | No text smaller than 17 px | all pages | Apple HIG default 17 pt (R-E30) |
| H7 | Every interactive element (buttons, links, toggles, chips, number buttons, "?" buttons, footer links, the sheet's link) MUST have a bounding box at least 44 x 44 CSS px; no inline-text exception is used | all pages | WCAG 2.2 SC 2.5.5; Apple HIG 44 pt (R-E29, R-E30) |
| H8 | Text contrast MUST be at least 4.5:1 | all pages | WCAG 2.2 SC 1.4.3 |
| H9 | Pages MUST work at 200% browser zoom without losing content | all pages | WCAG 2.2 SC 1.4.4 |
| H10 | MUST NOT scroll horizontally at 360 px viewport width | all pages | phone-first design at 360 px (team decision); H6 |
| H11 | Meaning MUST NOT be carried by colour alone: every highlight or condition also has a text label | all pages | WCAG 2.2 SC 1.4.1 |
| H12 | Navigation MUST be flat: one screen per step, Back as in section 6a, no nested menus, no hamburger menu | farmer routes | Medhi 2011: "Minimize hierarchical structures", "Avoid menus that require scrolling" |
| H13 | Past years MUST always carry the label key `common.notForecast` ("năm đã qua, không phải dự báo" in meaning) | `/nam`, `/phuong-an` | CLAUDE.md boundary "Past years are never presented as forecasts" |
| H14 | MUST NOT collect personal data: no names, no phone numbers, no location permission, no cookies, no localStorage or sessionStorage. Only exception: the optional Google sign-in of section 12c on `/dang-nhap` and `/da-luu`, used only when the farmer chooses it | all pages | CR (no personal data); team decisions on sign-in and privacy |
| H15 | All user-visible text MUST come from the i18n files or from API `Text` fields (no hard-coded strings in components). Fixed sentences come from i18n keys only; data-dependent text comes from the API only; the API carries no copy of a fixed sentence (routine) | all pages | final copy is written in-event (section 2) |
| H16 | Starting language from the browser's language setting (Vietnamese if it lists Vietnamese, otherwise English; section 6c); a language toggle on every page switches between Vietnamese and English (section 6c) | all pages | FR (English toggle), judges |
| H17 | Every plan card MUST carry its own warnings inside the card box: `plans.trialNote`, `money.priceYear` (or `money.priceYearNotStated`, section 9), `common.notForecast` and `common.supportNote`, so a screenshot or print of one card keeps them | `/phuong-an` | team plan review (farmer persona); IRRI/IFAD 2022 (Zalo is the most used digital tool; that a card is shared as a screenshot is our design reading) |
| H18 | The reminder key `common.supportNote` ("the tool supports, and does not replace, the farmer's judgement and extension advice" in meaning) MUST be visible on `/`, on `/phuong-an` and inside every card | farmer routes named | challenge page: "Share reminders that the tool is intended to support ... not replace ... local expertise"; team plan review |
| H19 | Every official-condition value MUST name two sources: the threshold (QĐ 18/2021, article cited, R-A01) and the values (NASA POWER R-N01, weighted with MODIS farmland R-N02), with the words of key `conditions.computedNote` ("our computation, not an official record"); the line `common.dataLine` ("Dữ liệu: NASA POWER") MUST be visible on `/nam` and `/phuong-an` and in the footer of every page | all pages | team plan review (judge personas) |

### 4a. What counts as a sourced number (H5)

Sourced numbers (routine): every `Value` of section 11; the crop dates and bare-period dates of the month bar;
the metric numbers of the method page. Not sourced numbers, shown as plain text without a source button: year labels
(year rows, picked years, `worst_years`, the years chip), the progress text, the month tick labels, `years_count`
(picked years with a real value), `test_years`, numbers inside fixed i18n sentences, and the text inside a source
sheet.

Every element that shows a sourced number carries `data-value` (its displayed value string) and either is a button
that opens the source sheet or carries `data-source-ref` = the `data-testid` of the button that does (section 14a).

---

## 5. Visual tokens (fixed)

| Token | Value | Use |
|---|---|---|
| `--text` | `#1D2329` | body text |
| `--muted` | `#4A5560` | secondary text (still >= 17 px); text of a disabled button |
| `--bg` | `#FFFFFF` | page |
| `--surface` | `#F4F6F8` | cards; background of a disabled button; loading placeholder blocks |
| `--primary` | `#2F5F7E` | buttons, selected borders, link text |
| `--on-primary` | `#FFFFFF` | text on primary |
| `--highlight-bg` | `#FFF1B8` | priority row background (always with the text label, H11) |
| `--border` | `#5B6670` | card and button borders; outline of loading placeholder blocks |
| `--focus` | `#000000` | 3 px focus outline |

Pairs checked by T8 at >= 4.5:1 (the H8 value; applied to border and focus colours as well, so no second threshold
is needed, routine): `--text` on `--bg`, `--surface`, `--highlight-bg`; `--muted` on `--bg`, `--surface`;
`--on-primary` on `--primary`; `--primary` on `--bg`, `--surface`, `--highlight-bg`; `--border` on `--bg`,
`--surface`, `--highlight-bg`; `--focus` on `--bg`, `--surface`, `--highlight-bg`. If any pair fails, darken the
foreground colour; do not change sizes.

A disabled button (for example `common.next` before a choice) has the `disabled` attribute, `--muted` text on
`--surface` and a `--border` border. Loading placeholders are blocks filled with `--surface` with a 1 px `--border`
outline and no text (routine).

Spacing uses the Tailwind default scale. Cards and buttons have a 12 px corner radius. The layout is one column, with
a maximum content width of 480 px, centred on larger screens.

Pictures: each choice button on Screens 1 and 3 has a picture slot (64 x 64 px). Medhi 2011 found hand-drawn
pictures understood better than photos. Until drawings exist, use the placeholder component
`<PictureSlot label="..."/>` (a dashed box with the label). Final drawings are an in-event task (section 15 item 2).

Anti-"AI look" check: the `unslop` skill audits the finished screens once, in audit and polish mode. Where the skill
and this spec disagree, the spec applies. That means no font, colour, spacing scale or layout outside sections 3 and
5, no generated image, no icon package and no motion outside the H1 conditions. Only findings that fit this spec are
fixed.

---

## 6. Routes and flow

| Step | Route | Screen | Next | Progress text | Back goes to |
|---|---|---|---|---|---|
| 0 | `/` | Start | `/ruong` | none | no Back button |
| 1 | `/ruong` | Your field (Screen 1) | `/nam` or `/khong-co-phuong-an` | `common.step` n=1 | `/` |
| 2 | `/nam` | Past years (Screen 2) | `/uu-tien` | `common.step` n=2 | `/ruong` |
| 3 | `/uu-tien` | What matters most (Screen 3) | `/phuong-an` | `common.step` n=3 | `/nam` |
| 4 | `/phuong-an` | Plans (Screen 4) | - | `common.step` n=4 | `/uu-tien` |
| - | `/khong-co-phuong-an` | No tested plan for this land | - | none | `/ruong` |
| - | `/phuong-phap` | Method, data, limitations, explain the terms (for officers and judges; section 11b) | - | none | previous page (section 6a) |
| - | `/gioi-thieu` | About (section 12b) | - | none | previous page (section 6a) |
| - | `/nguon` | Sources and credits (section 12b) | - | none | previous page (section 6a) |
| - | `/ban-do` | Optional advanced map view (section 12, later feature) | - | - | - |
| - | `/dang-nhap`, `/da-luu` | Optional Google sign-in and saved answers (section 12c, later feature) | - | - | - |

`common.step` takes `{n}` and `{total}` (total = 4). The routes `/ban-do`, `/dang-nhap` and `/da-luu` do not exist in
the router until their feature is started under the rule of section 2. The source sheet (Screen 5, section 10) is a
bottom sheet over any page, not a route.

In the product frontend (the team's web app, hash routing, section 3) the farmer steps sit under `#/nong-dan/`, with
the answers in the app's URL keys after the route (`#/nong-dan/...?ruong=&nam=&uutien=`); the rules of sections 6a
and 6b apply to those names. Every page also has an English path (for example `/farmer`, `/assistant`, `/method`,
`/sign-in`, `/saved`) that opens the same page in English; the Vietnamese paths stay the main ones.

### 6a. Navigation (routine)

- Every internal link and button that changes the route keeps the current (cleaned, section 6b) fragment.
- Back on a step route goes to the route in the "Back goes to" column, keeping the fragment, so a cold deep link to
  `/phuong-an` goes back to `/uu-tien`. Back on `/khong-co-phuong-an` goes to `/ruong`. The browser's own back button
  works as usual through the browser history.
- Back on `/phuong-phap`, `/gioi-thieu` and `/nguon`: `history.back()` when the previous history entry belongs to
  this app (react-router `location.key` is not `"default"`), otherwise `/` with the fragment.
- Back uses key `common.back`; Next uses `common.next` unless a screen names another key.
- On every route change: focus moves to the page's `<h1>` (`tabIndex={-1}`) and `document.title` is set to the text of
  the page's title key: `/` `start.title`, `/ruong` `field.question`, `/nam` `years.title`, `/uu-tien`
  `priority.question`, `/phuong-an` `plans.title`, `/khong-co-phuong-an` `noplan.title`, `/phuong-phap`
  `method.title`, `/gioi-thieu` `about.title`, `/nguon` `sources.title`. The same key is the page's `<h1>`.

### 6b. State in the URL fragment

State between steps is kept in the URL fragment (the part after '#', which browsers never send to the server), so a
link can be shared on Zalo and reopens the same view without the answers reaching any server log. MUST NOT use
localStorage, sessionStorage or cookies for this state. MUST NOT put the answers in the query string (with hash
routing, a `?` after the hash route is still inside the fragment).

The fragment holds `key=value` pairs joined by `&`, read and written with `URLSearchParams` (routine). The keys are
listed below (routine; in the product frontend `land`, `years` and `priority` are named `ruong`, `nam` and `uutien`):

| Key | Valid values | Written by |
|---|---|---|
| `land` | `dry`, `irrigated`, `unsure` | `/ruong` |
| `years` | comma-separated years, strictly ascending (so unique), each one present in `PastYearsResponse.years[].year` | `/nam` |
| `priority` | `income`, `stability`, `water`, `land` | `/uu-tien` |
| `lang` | `vi`, `en` | the language toggle (section 6c) |

The price-entry keys of section 12d are added only when that feature is built. Example:
`/phuong-an#land=dry&years=2010,2020&priority=stability&lang=vi`.

Rules (routine):
1. Each step preselects its own choice from the fragment and writes only its own key; it never changes another key.
2. On every route load, unknown keys and keys with an invalid value are dropped from the fragment (`history.replace`).
   `years` is checked against the past-years response, so `/uu-tien` and `/phuong-an` also load
   `GET /api/past-years` (kept in memory for the life of the page, section 11) before they check `years`.
3. Required keys: `/nam` needs `land`; `/uu-tien` needs `land` and `years`; `/phuong-an` needs `land`, `years` and
   `priority`. Other routes need none.
4. If `land=irrigated` on `/nam`, `/uu-tien` or `/phuong-an`, the app replaces the route with `/khong-co-phuong-an`
   (keeping the fragment); no compare request is sent.
5. Otherwise, if a required key is missing or was dropped, the app replaces the route with the earliest of `/ruong`
   (`land`), `/nam` (`years`), `/uu-tien` (`priority`) whose key is missing or was dropped, keeping the cleaned
   fragment. Example: `/phuong-an` with an empty fragment goes to `/ruong`; `/phuong-an#land=dry&years=1990` goes
   to `/nam#land=dry`.
6. When `lang` is missing or dropped, the starting language follows section 6c. A missing `lang` never causes a
   redirect.

### 6c. Language (routine)

- The fragment key `lang` holds the language. Without a valid `lang`, the page is Vietnamese if any entry of
  `navigator.languages` (or `navigator.language` when the list is unavailable) has the primary language subtag `vi`
  (BCP 47, case-insensitive), and English otherwise. It is Vietnamese when the browser gives no language at all.
  The browser setting is read in the page only; nothing is sent or stored. A valid `lang` in the fragment and the
  toggle always win (W3C: the browser's language is "a good starting point" only if the user can override it,
  R-U22). The language is never kept in localStorage or cookies (H14).
- `<html lang>` is set to `vi` or `en` whenever the language changes, including on first load.
- The language toggle (`LangToggle`) is one button on every page, top right, at least 44 x 44 px. Its label is key
  `lang.toEn` while the page is Vietnamese and `lang.toVi` while it is English. Tapping it writes only `lang` with
  `history.replace` and re-renders the page in the other language.

### 6d. The text dictionaries and dates (routine)

```ts
function useT(): Messages   // src/app/settings.tsx: the message object of the current language
```
- The texts live in two typed objects, `src/i18n/vi.ts` and `src/i18n/en.ts`, with the same shape. A component reads
  them with `const t = useT()` and writes a key as a field, for example `t.copilot.claudeOn`.
- An entry that takes values is a function of those values, so a missing value is a type error. `src/i18n/i18n.test.ts`
  checks that both languages have the same keys, list lengths and function arities, and that no text is empty.
- No plural rules, no HTML inside values. This replaces the planned `t(key, params)` helper over JSON files.

The keys in this document are written as dotted names (`common.step`); in the code they are fields of the message
objects. Keys that take values (all other keys take none):

| Key | Params |
|---|---|
| `common.step` | `{n}`, `{total}` |
| `common.sourceFor` | `{name}` (accessible name of a "?" button: the rule or line it explains) |
| `calendar.bare` | `{from}`, `{to}` |
| `money.priceYear` | `{year}` |
| `years.cellsNote` | `{n}` |
| `stability.yearsCount` | `{count}` |
| `stability.worstYears` | `{years}` |
| `chip.years` | `{years}` |
| `method.question` | `{first}`, `{last}` |
| `method.skillCi` | `{value}`, `{low}`, `{high}` |

Formats: a list of years (`{years}`) is the years in ascending order joined by ", ". A date "MM-DD" is shown as
"D/M" without leading zeros, as P-02 writes its dates (e.g. "01-17" is shown as "17/1"), in both languages. A
`Value` is shown as `value`, one space, then `unit` in the current language. In Vietnamese mode the `value` is shown
with Vietnamese digit grouping (dot for thousands, comma for decimals) and units are written m³ and m², because a
Vietnamese reader takes "30,799" as about 30.8; English shows the value as given. This only affects the display; the
API values and their sources do not change.

---

## 7. Screen 0 and Screen 1: Start, Your field

**Start (`/`)**: the page shows the title key `start.title`, one sentence with key `start.lead`, the reminder
`common.supportNote` (H18), a primary button `start.go` that goes to `/ruong`, a secondary link `start.method` styled
as a button that goes to `/phuong-phap` (17 px text, 44 px tall, H6, H7), and the language toggle. It has no progress
text, no Back button and nothing else.

**Province line**: the top of Screen 1 shows a locked province selector, as the team asked. It is a `<select>` with
one option and `aria-disabled="true"`. We use `aria-disabled` rather than the `disabled` attribute so that
screen-reader and keyboard users can still reach and read it; any change is ignored. It shows the label key
`field.province`, the value key `province.nghe_an` ("Nghệ An", from i18n, not from the API) and the note key
`field.provinceNote` (other provinces are not available yet). The value is sent with every request as
`province: "nghe_an"`. The selector is there so the design can scale to other provinces through the country adapter
(ARCHITECTURE.md §1b); no other province is listed or selectable in the prototype.

**Screen 1 (`/ruong`)**: question key `field.question`. Exactly three single-choice buttons, full width, in this order:

| Order | Value | Label key | Required words in the Vietnamese label |
|---|---|---|---|
| 1 | `dry` | `field.dry` | "cao cưỡng", "cuối kênh", "thiếu nước" (official commune wording, R-G01, R-G13) |
| 2 | `irrigated` | `field.irrigated` | "chủ động nước" |
| 3 | `unsure` | `field.unsure` | "Không chắc", "hỏi cán bộ khuyến nông" |

Behaviour: a tap selects the option (border `--primary`, background `--surface`, a check mark and the text label
with key `common.selected`) and writes `land` to the fragment. Button `common.next` is disabled until one option is
selected. Next then goes to:
- `/nam` for `dry`;
- `/khong-co-phuong-an` for `irrigated`, because all shown plans were tested only on drought-prone land (P-02);
- `/nam` for `unsure`, and Screen 4 then shows the banner key `plans.unsureBanner` ("ask an extension officer whether
  your field is this type") above the cards.

There is no per-season water question, because the land-type question already covers the water situation.

**No tested plan (`/khong-co-phuong-an`)**: the page shows the title key `noplan.title`, the text key `noplan.text`
and the Back button (`common.back`, which goes to `/ruong`). It has no progress text.

---

## 8. Screen 2: Past years (`/nam`)

Data: `GET /api/past-years?province=nghe_an` (section 11). The layout, from the top:
1. Title `years.title`; the label `common.notForecast` (H13); the line `common.dataLine` (H19).
2. Legend (drawn after the year list and the picked years' cards since 2026-11-16: the years are the farmer's task,
   the rule names are reference): one row per rule in the order of `rules`: its `label` and a "?" button (`data-testid` `legend-<rule code>`,
   accessible name `common.sourceFor` with `{name}` = the label). The button opens the source sheet in rule mode
   (section 10): the quoted rule text (QĐ 18/2021 article, R-A01), the values sources (R-N01, R-N02), the computation
   entry and `conditions.computedNote` (H19). Rules (quoted from QĐ 18/2021, R-A01): heavy rain (Art. 44), heat
   (Art. 47), drought rain part, two readings (Art. 48), damaging cold (Art. 53). Rule names are written out in
   full; no letter codes stand for rules (a letter would need a yes/no per year, and no source sets a cut-off).
3. Year list: one full-width row per entry of `years` (1995-2024), in year order. Each row is
   exactly one toggle button (`<button aria-pressed>`, `data-testid` `year-<year>`) containing only text (no other
   interactive element inside it; routine). Inside the button: the year number, then one line per rule in the
   order of `rules`: the rule `label`, then the farmland share of that year as plain text with `data-value`,
   `data-rule` = the rule code and `data-source-ref` = `legend-<rule code>` (H5); a null share shows
   `common.notAvailable`. Lines wrap; nothing is truncated. The shares are counted over the P-02 field time of that
   calendar year: daily rules over the days, the drought rule over the months in which any P-02 crop was in the field,
   the same days and months the cards count, in whole percent. A selected row has a 3 px `--primary` border, a check
   mark and the text `common.selected`. Each row is at least 44 px high (H7), with text of at least 17 px (H6), in one
   column at any width and at 200% zoom (H9, H10). No year is picked when the screen opens. Tapping a row toggles it
   and writes `years` (strictly ascending) to the fragment.
4. Five limitation lines, in this order: `years.cellsNote` with param `{n}` = `n_cells` ("from {n} NASA weather
   squares of about 50 km"); `years.gridNote` (values come from NASA's 50 km grid; gridded values smooth
   extremes); `years.mechanicalNote` (official warning levels also weigh humidity, wind and duration; ours apply
   the decree's tables directly, R-K03); `years.dailyNote` (daily totals can miss heavy rain that crosses
   midnight); `years.coldNote` (the decree does not classify heat or cold spells whose days fall in
   different temperature bands; such spells are not counted).
5. Button `common.next`, enabled when at least 1 year is selected. At most 10 years can be picked (the web app's
   choice, kept by the team).

Screen 2 has no summary box.

---

## 9. Screens 3 and 4: Priority and Plans

**Screen 3 (`/uu-tien`)**: question key `priority.question`. Exactly four single-choice buttons in this order, each
with a picture slot: `income` (`priority.income`), `stability` (`priority.stability`), `water` (`priority.water`),
`land` (`priority.land`). One choice is required; a tap writes `priority` to the fragment. Button `priority.show`
goes to `/phuong-an`.

**Screen 4 (`/phuong-an`): one card per plan**

Data: `POST /api/compare` with the body of section 11 built from the fragment (`land` `dry` or `unsure`, `years`,
`priority`, `province: "nghe_an"`).

The top of the screen shows, in order:
1. Title `plans.title`, the label `common.notForecast`, the line `common.dataLine` (H19), the reminder
   `common.supportNote` (H18), and a summary chip row with three chips in step order (routine). The land chip
   (`chip.land.dry` or `chip.land.unsure`) goes to `/ruong`, the years chip (`chip.years` with `{years}`) goes to
   `/nam`, and the priority chip (`chip.priority.income`, `.stability`, `.water` or `.land`) goes to `/uu-tien`. Each
   chip is a button (`data-testid` `chip-land`, `chip-years`, `chip-priority`); there are no other menus.
2. Banner `plans.unsureBanner` only if land = `unsure`.
3. Banner `plans.trialNote` (always): plans come from one unreplicated trial, Lưu Sơn, Đô Lương, 2020-21; each crop
   was tested in its season on this land type; whether one field carried the whole year is not known. The same text
   is repeated inside every card (H17).

No SoilGrids soil-property values are shown anywhere (the SoilGrids producer advises against local, farm or
subnational use, R-K13). The only soil value shown is NASA POWER root-zone soil wetness in the water row.

Then come the cards, in exactly the order the API returns them: the farmers' usual plan from P-02 (`usual`, CC5), the
local practice described in P-03 (`usual_p03`: rice - rice - fallow), then the four tested plans in the source's order
(`cc1`..`cc4`). The frontend MUST NOT reorder, sort, filter or rank cards (H3). Each card has `data-testid`
`card-<plan id>`; each row has `data-testid` `card-<plan id>-row-<row key>` with the row keys of the table below.

Crop matching inside a card: `Plan.exposure`, `Plan.stability`, `Plan.money.items` and `Plan.water` are joined to
the crops of `Plan.calendar` by `crop_key`; season labels come from `CompareResponse.seasons` by season code.

Each card has these rows, top to bottom, in this fixed order, which is the same in every card:

| Row key | Heading key | Content | Notes |
|---|---|---|---|
| `header` | - | plan `name` and the badge key `plans.usual` on the two local-practice cards (`is_usual`) only, followed by the study it comes from (`farmer.currentOf`: `usual` "cùng thử nghiệm với 4 cách trồng thử", the control of the same P-02 trial as `cc1`..`cc4`; `usual_p03` "nghiên cứu khác", the control of P-03; rules/rotations.yaml, roleplay audit 2026-11-16 F-B2); under the name, the card's money total (`money.total`) with its source button and the water line: per crop of the plan, the TCVN 8641 "water to apply" as a range from the lowest to the highest of the standard's own rows for that crop and season, labelled "by region" (the standard does not place Nghệ An), in m³/ha, with the TCVN source button; a crop with no TCVN row says "no figure"; FAO figures stay out of the head. The label says "water to apply, by region"; the standard's name, the range note and the whole shared TCVN note are the closing note of the range's source sheet, and only the first sentence of the shared note stays after the range (rice: maintenance irrigation only). The local-practice P-03 card shows its text-only money as is | no other badges (H3); the target farmer (dry field) compares plans mainly on water; never compare P-03 money with P-02 money |
| `warnings` | `row.warnings` | four lines from i18n: `plans.trialNote`; `money.priceYear` with `{year}` = `money.price_year`, or `money.priceYearNotStated` when `price_year` is null; `common.notForecast`; `common.supportNote` | inside the card box (H17); no warning text comes from the API |
| `calendar` | `row.calendar` | the month bar of section 9a | caption key `calendar.trialDates` ("trial dates 2020-21") |
| `money` | `row.money` | one line per item of `money.items`: crop, season label, `money.profit` with `profit` and `money.cost` with `cost` (P-02 Tables 4, 8, 12, 13; a null `cost` shows `common.notAvailable`); a `flag` (CC1 mung bean and CC5 black bean: P-02 Table 4 rows identical in every column, both 16,200 thousand đ/ha; the paper does not explain it) closes the source sheet of that crop's profit and cost; then `total` with the short label "whole year, our addition", its sheet closing with the `money.ourSum` wording ("our addition of the profit values, not reported as a sequence"); `definition` from the API (P-02: "lợi nhuận thuần (RVAC) = GR - TVC", labour included), the plain sentence of the study and the table number close the sheet of each money value (D-187: one short label per number on the card, the source notes one tap away). For `usual_p03` (D-191): no item lines and no total; one line per item of `season_values`: the season label and its `value` in the paper's own million đồng/ha unit, unchanged (the D-190 million display applies to thousand values only), or, where the paper gives no number (autumn-winter fallow), the paper's `words` instead of a number; each sheet closes with the paper's `words`, its page (`money.paperPage`) and its `definition` (P-03: "Lợi nhuận = GR - Tổng chi phí vật chất", material costs only); the values are never summed, and the card keeps the one plain line that P-03 money takes off material costs only | never compare P-03 money with P-02 money |
| `stability` | `row.stability` | per crop of the calendar, in calendar order: (a) for every crop with an `exposure` entry: per picked year, the shares for `heavy_rain`, `heat` and `cold` from `exposure[].per_year[].shares`, each a number button, with the caption key `stability.trialDates` ("if sown on the trial's 2020-21 dates") above those tables; (b) for rice crops (a `stability` entry with the same `crop_key`): per picked year `stability.real` with `real` (a null `real` shows `common.notAvailable`); next to it `stability.prediction` with `oos_prediction` only where non-null (2016-2024 only); next to that `stability.range` with `range_80.low` and `range_80.high` only where non-null (G4 passed for that season); then, only when `summary` is non-null, `stability.min`, `stability.median`, `stability.max` with their values and `stability.worstYears` with `worst_years`; then `stability.yearsCount` with `years_count` and the `scope` text (province average, mostly irrigation-served rice); then one model line by `model_status`: `not_modeled` -> `stability.notModeled`, `not_shown` -> `stability.modelNotShown` (the reason is on the method page), `shown` -> none; then `common.nsoCredit` (section 12b). For non-rice crops part (b) shows `stability.noData`, never "no risk" | values from API only; the per-year tables show when the row opens (see below the table) |
| `water` | `row.water` | per crop: the shares for `drought_rain_consecutive` and `drought_rain_any2` per picked year from `exposure` (both readings), each a number button (H19); then each `WaterFact` of the crop on one line: lead key by `measure` (`to_apply` -> `water.toApply`, "nước phải tưới vào ruộng", m3/ha; `crop_uses` -> `water.cropUses`, "nước cây dùng", mm, "rough estimate"; `not_listed` -> `common.notListed`), then `value`, then `scope` (TCVN region, season, method); a non-null `note`, and for `to_apply` the line "seasonal irrigation in TCVN 8641 (m³/ha)", close the source sheet of that value (D-187), so the TCVN and FAO notes never share a sheet, and a note of a fact with no value stays on the row; then, for every crop with an `exposure` entry, per picked year: `water.soilWetness` with `per_year[].soil_wetness.value` and `water.soilNormal` ("1991-2020 average" in meaning) with `per_year[].soil_wetness.normal`, both whole percent of saturation and both number buttons (H5), followed once by the label `water.soilModelled` ("NASA model value, not a field measurement; 100% is soil full of water"), the longer note (MERRA-2, percent of saturation, over the field time) closing the sheet of each soil value; a null value shows `common.notAvailable`; no category word, colour or threshold | never combine or compare the two sources; rice shows every TCVN region row for its own season only (Trung bộ, Bắc bộ), the season taken from the standard's own row label, because the standard does not place Nghệ An; the per-year tables fold (see below the table) |
| `land` | `row.land` | three lines from `land`: `land.cropsInYear` with `crops_in_year.value`; `land.livingDays` with `living_days.value` (null shows `common.notAvailable`); `land.legume` with `common.yes` and the legume crop names, or `common.no`; after `common.yes` the residue note key `land.residueNote`. The values of `crops_in_year` and `living_days` are number buttons that open their own `source_ids` (H5); each line ends with a "?" button for its `principle_source_ids` | no score |
| `check` | `row.check` | behind its row button like every row (D-187 item 4): one line per `RiskItem` of `why.risks`, each followed by a source button `common.source` when its `source_ids` is non-empty; a quote that has a plain line in the i18n files (D-187: cost, market, biomass maize contracts, Decree 112/2024 Art. 6.1, 6.4 and 7.1) shows that line and its source in a few words, never claiming more than the quote, and the full quote opens first in the source sheet (`source.quote`); any other quote is shown in full; an empty list shows `check.noneListed`; then the line `check.localReview` ("check these with farmers or agricultural experts where you live before you change" in meaning; challenge page: "risks that would need local review by farmers or agricultural experts"). Risks include, where they apply, the market facts (P-03 p.4 on soybean, sesame and maize selling; R-C13 on biomass maize purchase contracts) and, for plans without rice (CC1-CC4), the legal context of converting rice land quoted from Nghị định 112/2024 (Art. 6.1 c-d, 6.4, 7.1; R-G06, R-G27) | guide, do not pick (team decision); procedure for a farmer's own field: [OPEN, section 15 item 7]; the row ends with `farmer.askOfficer` and the plan's questions for the extension officer, the same list as the officer page (decision text, D-187) |
| `why` | `row.why` | a disclosure button `why.toggle` (collapsed by default) that opens four labelled parts: `why.why`, `why.evidence`, `why.benefits`, `why.gaps` (Text from the API); the risks are in the row `check` | challenge page wording |
| `share` | `row.share` | button `plans.share` and button `plans.print`, both acting on the whole page (section 9b) | R-U07 |

D-187 item 4 (member A, 2026-11-15, built in part): the card face shows the header (plan name and crops, money total
and water line with their source buttons), the farmer's priority label and line, and the four warnings; every row
below the header folds behind a full-width heading button of at least 48 px (`aria-expanded`), closed at first, in this
order; the jump strip marks the card in view (`aria-current`). Each jump-strip chip is short, two lines from
`farmer.chip` ("Hiện nay / cùng thử nghiệm", "Hiện nay / nghiên cứu khác", "Cách trồng / thử 1"), so several chips show
at once on a 360 px phone; its accessible name is the full plan name with the study and the crops (roleplay audit
2026-11-16, F-A7). The line `farmer.comparedWith` says once, above the strip, that the four trial cards are compared
with the first card, the current practice of the same trial. Inside the `stability` row the per-year share tables
show as soon as the row opens (no second fold; roleplay audit 2026-11-16, F-B1), and the `stability.noData` line of
the non-rice crops comes after them as their limit. Inside the `water` row the per-year share tables fold once more
behind "Xem từng năm" / "Show each year". A card was 7-10 phone screens long; the closed card face
is now about 1.7 to 2 phone screens at 360 x 740 in Vietnamese (2026-11-16: 1,241 to 1,468 px under a 128 px sticky
header and strip); one screen is not reachable with the required face content at 17 px (H6).

**Comparison strip** (roleplay audit 2026-11-16): after the page lead and before the jump strip, one block
`farmer.stripTitle` shows the six plans side by side before any card is opened: a list in exactly the cards' order
(H3: no sort, rank, score, best mark or colour grading), stacked on a phone and in columns on a wide screen, so the
page never scrolls sideways at 360 px (H10). It opens with the line `farmer.comparedWith` (the four trial cards are
compared with the first card, the current practice of the same trial). The long labels are said once, in a short
list above the six plans: the money label (`row.money`, "profit in the trial, not on your own field") with the
sentence `farmer.stripSum` ("a whole-year figure is our addition; the 'another study' card gives each season as its
paper does", so the addition is never said of the P-03 values), the water label ("water to apply, by region") and
`land.cropsInYear`; the label of the chosen priority (`income` money, `water` water, `land` land; `stability` has no
line in the strip) starts with `plans.yourPriority` in words (H11). Per plan: the plan's short name from
`farmer.chip` and its crops, together one link of at least 44 px that jumps to its card (accessible name: the full
plan name with the study and the crops); the card head's money line and water line under the short labels
`farmer.strip.money` and `farmer.strip.water`, the same components, values and source buttons as the card head
(H5, H7), so the strip shows no number, sum or source that the card does not show; for `usual_p03` the plain line
`farmer.definitionPlain.p03` right after its money, so P-03 money is never lined up as comparable with P-02 money;
and one land line, the `crops_in_year` number button and `land.legume` yes or no in words. A phone (up to 700 px)
has room for two lines per plan: it shows the money line and, when the chosen priority is water or land, that
priority's line; a wider screen shows all three. Measured at 360 x 740 in Vietnamese: about one and a half screens
for the income priority (the first form, with every label repeated in every plan, was about three and a half); the
water priority is longer because each crop has its own range. Each card also carries the "explain simply" button
of FR-15 (SRS.md); its text is marked as AI-generated.

**Priority highlight**: the row that matches the chosen priority (`money` for income, `stability` for stability,
`water` for water, `land` for land) has background `--highlight-bg`, a 4 px `--primary` left border, the attribute
`data-highlighted="true"` and the visible text label key `plans.yourPriority` ("Ưu tiên của bạn") at its start (H11).
As a bonus item, built only after the core, the cards `cc1`..`cc4` (and only those) get a priority line (`data-testid`
`card-<plan id>-priority-line`) after the label. For income it is `priority.line.income` with this card's
`money.total` and the `usual` card's `money.total`. For land it is `priority.line.land` with this card's and the
`usual` card's `land.crops_in_year.value` and `land.living_days.value`. For stability and water it is
`priority.line.stability` or `priority.line.water` ("these values are per crop and per past year; compare this row
with the same row on the farmers' usual plan card" in meaning, no numbers). Both plans are
from P-02, so the values are comparable; the line names the source (P-02). Every number in it is a number button with
its own `source_ids` (H5); a null value shows `common.notAvailable`. The frontend shows response values only and
computes nothing. The line MUST NOT say better, best, should or recommended (or the Vietnamese equivalents in the
glossary). The `usual` and `usual_p03` cards have no priority line. Nothing else changes; the card order and content
stay the same.

### 9a. Month bar (routine unless cited)

- Scale: the bar spans the days of a 365-day year, with Jan 1 at the left edge and Dec 31 at the right. A date
  "MM-DD" maps to its day of a non-leap year. There are 12 tick marks, one on the first day of each month, and tick
  labels only at months 1, 4, 7, 10 with keys
  `calendar.m1`, `calendar.m4`, `calendar.m7`, `calendar.m10` ("T1", "T4", "T7", "T10" in Vietnamese; fit at 17 px,
  H6, H10).
- One lane per crop, stacked top to bottom in `calendar` order, so overlapping spans stay visible; reported dates are
  drawn exactly as given, including overlaps. A lane is a segment from `sow_from` to `harvest_to`, with the
  sowing range (`sow_from`..`sow_to`) and the harvest range (`harvest_from`..`harvest_to`) drawn as lighter ends. Under
  the bar, one line per lane: crop name, variety (P-02) and its dates in the format of section 6d. A lane carries no
  crop name, since a name cut by a short lane ("Đậu …") cannot be read (roleplay audit 2026-11-16, F-A4): each lane
  shows its number (1, 2, 3 in `calendar` order) and its line in the list starts with the same number on a key of the
  lane's colour, so lane and name are tied by text, not by colour alone (H11). No crop span crosses 31 December
  (ML-DESIGN.md §5a: no P-02 window crosses it; `src/api.ts` rejects a span that does).
- Bare periods (FR-18) are the `bare_periods` from the API (derived by the engine, never hand-entered). They are
  drawn with a hatched pattern and also labelled with `calendar.bare` and their dates (H11). A period with `from`
  later than `to` wraps across 31 December and is drawn as two pieces (from `from` to Dec 31 and from Jan 1 to `to`)
  with one label.
- Sources: the caption `calendar.trialDates` is a button (`data-testid` `card-<plan id>-calendar-source`) that opens
  the source sheet for the union of the plan's `CropSpan.source_ids`; every date shown in the bar carries
  `data-source-ref` pointing to it (H5).
- On the P-03 card, where all four dates are null on every span, the lanes are empty and the bar shows
  `calendar.noDates` ("dates not reported in P-03"). There is no bare shading and the caption is not a button.

### 9b. Share and print (team decision; details routine)

- `plans.share` shares the page URL with its whole fragment (the whole comparison, not one card) through the Web
  Share API (`navigator.share({ url: location.href })`). Where the Web Share API is missing or fails with an error
  other than the user cancelling (`AbortError`), it copies the URL with `navigator.clipboard.writeText` and shows
  `plans.linkCopied`; if copying fails too, it shows `common.error`.
- `plans.print` calls `window.print()` for the whole page. Print CSS (`@media print`): every disclosure is expanded,
  the card warnings, `common.nsoCredit` lines and the footer are printed, and only the Back, Next, share, print and
  language buttons and the source sheet are hidden. A printed list key `print.sources` at the end gives the citation of
  every source id used on the page, from the `sources` map (FR-14). The `Disclosure` component therefore
  keeps its content in the DOM when collapsed and hides it with CSS on screen only.

---

## 10. Screen 5: Source sheet (bottom sheet)

The source sheet opens from any number button, "?" button or source button (H5); its `data-testid` is
`source-sheet`. It is not a route and adds no history entry, and a route change closes it. The close button
`common.close` is 44 px and Escape also closes the sheet. Focus is trapped in the sheet while it is open and returns
to the opener on close. The sheet has no animation (H1). Source facts come from the `sources` map of the response
that the current page loaded (section 11).

Modes (routine):
- **Value mode** (a number button): first the row `source.value` with the tapped value and unit, as the card shows
  it, then one source block per id of the value's `source_ids`, in order. A money value the card shows in million
  đồng/ha (D-190) gives the paper's own value and unit right under it, as `sheet.inPaper` ("Trong bài báo: …" /
  "In the paper: …"), so the two never read as two different numbers (roleplay audit 2026-11-16, F-A5).
  - Official-condition share: its `source_ids` are the rule's `threshold_source_id`, `values_source_ids` and
    `computed_by`, in that order; the R-A01 block also shows `source.ruleText` with the rule's `rule_text` (from the
    response's `rules`); after the blocks, `conditions.computedNote` (H19).
  - A value with a closing note (D-187): after the blocks, the note that the card leaves out (definition, table,
    flag, TCVN or FAO note, soil model note).
  - Model prediction or 80% range: the experiment block, then the gate verdicts of that stability block's season from
    the response's `gates`, one line each: `gate.G1` .. `gate.G4`, then `gate.passed`, `gate.failed` or `gate.notRun`
    (`passed` true, false or null), then `detail`.
- **Rule mode** (a legend "?" button on `/nam`): title = the rule `label`; `source.ruleText` with `rule_text`; the
  blocks of `threshold_source_id`, `values_source_ids` and `computed_by`; then `conditions.computedNote`. There is no
  `source.value` row.
- **Source mode** (calendar caption, land-care "?", risk source button, method table row): the blocks of the given
  ids only, no `source.value` row. A risk with a plain card line shows its full quote first, under `source.quote`.

Each source block has these rows, in this order, with the label from i18n and the value from `SourceFacts`:

| Label key | Field | Shown when |
|---|---|---|
| `source.name` | `citation` | always |
| `source.type` | `study_type` | always |
| `source.placeYears` | `place_years` | always |
| `source.readStatus` | `read_status`, as written in REFERENCES.md | `read_status` is non-null |
| `source.fullText` | `full_text_read` as `common.yes` or `common.no` | `full_text_read` is non-null |
| `source.limits` | `limitations`, one line each | `limitations` is non-empty |
| `source.link` | `url` as a link (opens in a new tab, `rel="noopener noreferrer"`, 44 px tall) | `url` is non-null |

The sheet shows no grade, stars or confidence words.

---

## 11. Data contract (frontend <-> backend)

All responses are JSON. Until the backend exists, the same JSON lives in `public/fixtures/past-years.json`,
`public/fixtures/compare.json` and `public/fixtures/method.json`, and a single module `src/api.ts` switches between
fixtures and the API by the env variable `VITE_USE_FIXTURES=true|false`. The backend now exists, so the built app
reads only the API: the fixture files and the switch were removed, and the unit tests build their responses in
`src/tests/fixtures.ts`. Fields that no screen in sections 7-12
names (for example `Season.window`, `GateRow.model_id`, `MethodResponse.freeze_commit`) are for traceability and
tests only; the frontend MUST NOT display them. This section is the one canonical contract. ARCHITECTURE.md §3
mirrors it, and DATA-DICTIONARY.md defines the artifacts and rules files that feed it.

Fixtures (section 2; routine): every number and text MUST be a placeholder (e.g. `"xx.x"`, `"[plan name]"`),
never a real study value, because fixtures are test data and real values come only from the API, built from 09:00
Sat 14 Nov. Fixture dates are placeholder dates on the first day of a month (e.g. `"02-01"`), never the P-02 dates.
At least one fixture plan has a gap between spans (T19), the `usual_p03` plan has all dates null (T21), and one
fixture variant for T23 has an `oos_prediction` outside `test_years`. Years in fixtures use the real range 1995-2024
(a design fact, not a study value).

Canonical identifiers:
- Province: `nghe_an` (displayed with key `province.nghe_an`; DATA-DICTIONARY.md §1 maps it to `unit_id`
  `VN-NA`).
- Plan ids: `usual` (P-02 CC5, farmers' usual structure), `usual_p03` (P-03 control "Lúa - lúa - bỏ hoang"), `cc1`,
  `cc2`, `cc3`, `cc4` (P-02 tested structures), in this order.
- Season codes, each with its source window:
  - `spring`: vụ Đông Xuân / vụ Xuân. NSO spring rice (E06.16-18, R-D01), ML window from the NSO calendar
    (rules/calendar.yaml); P-02 Table 9 (2021): sown 17/1-18/1, harvested 05/4-25/6.
  - `summer_autumn`: vụ Hè Thu. NSO autumn rice (E06.19-21; NSO name "autumn"), NSO calendar window; P-02 Table 1
    (2020): sown 06/6-10/6, harvested 20/8-12/9.
  - `winter`: vụ Mùa (10th-month rice). NSO winter rice (E06.22-24), NSO calendar window; no P-02 crop.
  - `autumn_winter`: vụ Thu Đông. P-02 Table 5 (2020): sown 15/8-10/9, harvested 21/11-22/12; not an NSO rice season.
- Crop keys: `<plan id>_<season code>_<crop id>`, e.g. `cc1_spring_peanut`, `cc1_summer_autumn_mung_bean`,
  `cc1_autumn_winter_maize_grain`; crop ids are defined in DATA-DICTIONARY.md §6 (routine).
- Source ids: the REFERENCES ids (`R-` ids of REFERENCES.md, e.g. `R-P02`, `R-A01`) for every third-party source;
  our own computations (model results, condition shares, anomalies) use their own computation id, registered with
  its facts in `rules/sources.yaml` at the repository root: `E-` + three digits + an optional lowercase letter, e.g.
  `E-000l`; its SourceFacts name the input sources (routine choice, Claude). Numbers the engine computes from sourced
  inputs (money total, stability summary, land-care counts) cite their inputs plus the "engine computations" id
  (simple arithmetic, no model).
- Rule codes: `heavy_rain`, `heat`, `drought_rain_consecutive`, `drought_rain_any2`, `cold`.
- Rounding: sourced numbers keep the source's precision; our computed shares and anomalies are whole percent;
  money is shown as the study reports it. The backend rounds; the frontend shows `Value.value` as given, apart from
  the Vietnamese digit grouping of section 6d (display only) and the browser-computed numbers of section 12d.

Text ownership (H15; routine): fixed sentences are i18n keys only; the API carries only data-dependent text
(names, labels, quoted rule text, definitions, scope, notes, flags, why parts, risks, coverage, explain terms,
limitations, gate details). The API has no field for `common.supportNote`, `common.dataLine`,
`conditions.computedNote`, `plans.trialNote`, `money.ourSum`, `years.gridNote` or the card warnings.

```ts
type Lang = "vi" | "en";
type Text = Record<Lang, string>;                 // data-dependent text from the API, always both languages
type Province = "nghe_an";
type Land = "dry" | "unsure";                      // "irrigated" never reaches the API (section 6b rule 4)
type Priority = "income" | "stability" | "water" | "land";
type PlanId = "usual" | "usual_p03" | "cc1" | "cc2" | "cc3" | "cc4";
type SeasonCode = "spring" | "summer_autumn" | "winter" | "autumn_winter";
type RuleCode = "heavy_rain" | "heat" | "drought_rain_consecutive" | "drought_rain_any2" | "cold";
type SourceId = string;                            // "R-P02" (REFERENCES) or an own computation id like "E-000l"

interface SourceFacts {
  id: SourceId;
  citation: Text;
  study_type: Text;
  place_years: Text;
  read_status: string | null;                      // REFERENCES status cell as written; null for own computation ids
  full_text_read: boolean | null;                  // set per source in rules/sources.yaml; false whenever read_status names an abstract, title, summary, metadata or secondary reading; null for own computation ids
  limitations: Text[];
  url: string | null;
  nso_credit: boolean;                             // true for NSO statistics sources (R-J10)
}

interface Value { value: string; unit: Text; source_ids: SourceId[]; }   // display string, already rounded; >= 1 id
interface Season { code: SeasonCode; label: Text; window: Text; source_ids: SourceId[]; }
interface Rule {
  code: RuleCode; label: Text;
  rule_text: Text;                                 // quoted article text (QĐ 18/2021)
  threshold_source_id: SourceId;                   // "R-A01"
  values_source_ids: SourceId[];                   // ["R-N01", "R-N02"]
  computed_by: SourceId;                           // experiment id of the share computation
}
interface YearRow {
  year: number;
  shares: Record<RuleCode, Value | null>;          // share of Nghệ An farmland per official hazard, whole percent,
                                                   // unit "%"; daily rules over the P-02 field days, the drought
                                                   // rule over the P-02 field months of that year;
                                                   // null = no value computed
}

// GET /api/past-years?province=nghe_an   (province is not personal data; the farmer's answers never go in a URL)
interface PastYearsResponse {
  province: Province;
  rules: Rule[];                                   // the five rules, in RuleCode order
  years: YearRow[];                                // 1995..2024, strictly ascending, non-empty
  sources: Record<SourceId, SourceFacts>;          // every id used in this response
  n_cells: number;                                 // POWER cells with farmland weight in the province
}

interface CropSpan {                               // dates "MM-DD"; from = to when the source gives one date
  crop_key: string; crop_id: string; crop: Text; variety: Text | null; season: SeasonCode;
  sow_from: string | null; sow_to: string | null;
  harvest_from: string | null; harvest_to: string | null;   // all four set, or all four null (P-03: no dates reported);
                                                   // sow_from <= sow_to <= harvest_from <= harvest_to within one year
  source_ids: SourceId[];
}
interface Period { from: string; to: string; }    // "MM-DD"; from later than to = the period wraps across 31 December
interface MoneyItem {
  crop_key: string; crop: Text; season: SeasonCode;
  profit: Value;                                   // P-02 Table 13 "Lãi thuần"
  cost: Value | null;                              // P-02 Tables 4, 8, 12 "Tổng chi"; null when the source reports none
  flag: Text | null;                               // e.g. the identical Table 4 rows (CC1 mung bean, CC5 black bean)
}
interface Money {
  items: MoneyItem[];                              // empty for usual_p03
  total: Value | null;                             // our arithmetic: sum of the items' profit values (null for usual_p03)
  price_year: string | null;                       // e.g. "2020-21"; null when the source states no price year
  definition: Text;                                // profit definition of the source
  season_values: SeasonValue[];                    // usual_p03 (D-191): P-03 money per season, never summed; [] otherwise
}
interface SeasonValue {                            // one season's money as the study writes it
  season: SeasonCode;
  value: Value | null;                             // null where the study gives no number (P-03 fallow)
  page: string;                                    // the paper's page, e.g. "4" or "4-5"
  words: Text;                                     // the paper's words for the season (quoted where verbatim)
}
interface CropExposure {                           // per crop with field dates; [] for usual_p03
  crop_key: string; crop: Text;
  per_year: {
    year: number;
    shares: Record<RuleCode, Value | null>;
    soil_wetness: { value: Value | null; normal: Value | null };   // whole percent of saturation
  }[];                                             // picked years, ascending
}
interface StabilityYear {
  year: number;
  real: Value | null;                              // NSO anomaly; null = "not available" (no normal)
  oos_prediction: Value | null;                    // only years inside test_years, only if model_status is "shown"
  range_80: { low: Value; high: Value } | null;    // model's 80% range; only with oos_prediction and only if G4
                                                   // passes for that season
}
type ModelStatus = "shown" | "not_shown" | "not_modeled";   // not_modeled = no model for this season (G1);
                                                   // not_shown = the season's test did not pass
interface Stability {                              // one entry per rice crop
  crop_key: string; season: SeasonCode; label: Text;
  model_status: ModelStatus;
  years_count: number;                             // picked years with a non-null real value
  scope: Text;                                     // "province average; mostly irrigation-served rice"
  per_year: StabilityYear[];                       // picked years, ascending
  summary: { min: Value; median: Value; max: Value } | null;   // over the non-null real values; null when fewer
                                                   // than 2
  worst_years: number[];                           // years whose real value equals summary.min (ties give more than
                                                   // one), ascending; [] when summary is null
}
interface WaterFact {
  crop_key: string;
  measure: "to_apply" | "crop_uses" | "not_listed";   // TCVN 8641 / FAO TM3 / neither source lists the crop
  value: Value | null;                             // null only for not_listed
  scope: Text | null;                              // e.g. TCVN region, season and method of the row
  note: Text | null;                               // e.g. "rough estimate" context of the source
}
interface LandCheck { value: Value | null; principle_source_ids: SourceId[]; }
interface LandCare {                               // the three checks
  crops_in_year: LandCheck;                        // number of different crops in the plan's year
  living_days: LandCheck;                          // 365 minus bare-period days; null for usual_p03 (no dates)
  legume: { present: boolean; crops: Text[]; principle_source_ids: SourceId[] };
}
interface RiskItem { text: Text; source_ids: SourceId[]; }   // [] when the line has no source
interface Why { why: Text; evidence: Text; benefits: Text; gaps: Text; risks: RiskItem[]; }

interface Plan {
  id: PlanId;
  name: Text;
  is_usual: boolean;
  calendar: CropSpan[];
  bare_periods: Period[];                          // derived from calendar by the engine; [] when dates missing
  money: Money;
  exposure: CropExposure[];
  stability: Stability[] | null;                   // null = no rice in plan
  water: WaterFact[];
  land: LandCare;
  why: Why;
}

interface CompareRequest { province: Province; land: Land; years: number[]; priority: Priority; }
interface Interval { value: number; ci90_low: number; ci90_high: number; }
interface GateRow {
  gate: "G1" | "G2" | "G3" | "G4"; season: SeasonCode;
  model_id: string | null;                         // the model the gate judges; null for G1 (data gate)
  passed: boolean | null;                          // null = not run
  detail: Text;
  source_ids: SourceId[];
}

// POST /api/compare  body: CompareRequest (JSON body, not query parameters, so the answers are not in the address the
// host logs). land and priority are checked and echoed; they change no number, order or content.
interface CompareResponse {
  request: CompareRequest;                         // echo of the body
  test_years: { first: number; last: number };     // out-of-sample test years
  n_cells: number;                                 // POWER cells with farmland weight; shown with years.cellsNote
  seasons: Season[];                               // labels for every season code used in plans
  rules: Rule[];                                   // the five rules, for the source sheets
  gates: GateRow[];                                // gate verdicts of every season that has a Stability block
  plans: Plan[];                                   // order is final; frontend never reorders (H3)
  sources: Record<SourceId, SourceFacts>;          // every id used in this response
}

// GET /api/method  (method page, section 11b)
type ModelId = "b0" | "b2" | "bnw" | "m1_ridge" | "m2_lgbm" | "m3_rf";
type Sensitivity = "no_fao_flagged" | "mae_skill" | "risk_level_features" | "window" | "centroid_points";
interface MetricRow {
  model_id: ModelId;
  season: SeasonCode;
  role: "primary" | "secondary" | "reference";     // b0, b2, bnw = reference; primary = m1_ridge spring only
  scheme: "rolling_origin" | "spatial_holdout";    // ML-DESIGN.md §7 items 1-2
  sensitivity: Sensitivity | null;                 // null = main run; others pre-registered or robustness runs
  detail: Text | null;                             // what the run changed, e.g. the window change of a robustness run
  subset: string;                                  // "national"; "na_ht_th" (G3 subset: Nghệ An, Hà Tĩnh, Thanh Hóa);
                                                   // "unit:<unit_id>" (pilot report per province); "region:<region_id>"
  rmse: number | null; mae: number | null; r2_oos: number | null;   // Paudel 2021 eq. A.4
  skill_vs_b0: Interval | null; skill_vs_b2: Interval | null; skill_vs_bnw: Interval | null;
                                                   // with sensitivity "mae_skill": 1 - MAE_model / MAE_reference
  coverage_80: number | null;                      // G4
  n_rows: number; n_test_years: number;
  source_ids: SourceId[];                          // the computation id of the run (rules/sources.yaml)
}
interface WeatherClaim { season: SeasonCode; model_id: ModelId; made: boolean; source_ids: SourceId[]; }
                                                   // made: decided by the pipeline by the rule of ML-DESIGN.md §8
interface ReportItem { id: SourceId; title: Text; text: Text; source_ids: SourceId[]; }
                                                   // one-off reports (e.g. normal-yield method, drought-month
                                                   // readings, heavy-rain day split, heavy-rain check against
                                                   // DesInventar, zero-weight cells)
type CoverageAxis = "money" | "conditions" | "rice_history" | "model" | "water_tcvn" | "water_fao";
interface CoverageCell { row_key: string; crop: Text; axis: CoverageAxis; text: Text; source_ids: SourceId[]; }
type ExplainKey = "evapotranspiration" | "soil_moisture" | "ndvi" | "frost" | "water_balance" | "data_types";
interface ExplainTerm { key: ExplainKey; title: Text; text: Text; source_ids: SourceId[]; }
interface MethodResponse {
  test_years: { first: number; last: number };
  freeze_commit: string;                           // feature list and cleaning rules frozen before the first run
  metrics: MetricRow[];
  gates: GateRow[];
  weather_claims: WeatherClaim[];
  reports: ReportItem[];
  coverage: CoverageCell[];                        // each (row_key, axis) exactly once
  explain_terms: ExplainTerm[];                    // the six keys, in ExplainKey order
  limitations: Text[];                             // one line per limitation
  datasets_not_used: NotUsedDataset[];             // section 11b item 4b
  picsa: { source_ids: SourceId[] };               // sources of the PICSA sentence (key method.picsa; item 5)
  rain_check: RainCheck | null;                    // null = not run
  sources: Record<SourceId, SourceFacts>;
}
interface NotUsedDataset {                         // content in rules/method.yaml
  dataset: string;                                 // its official name
  reason: Text;                                    // official fact and why not used
  source_ids: SourceId[];                          // at least one
}
interface RainCheck {                              // DATA-DICTIONARY.md §5c
  months: { month: string; imerg: Value; power: Value }[];   // "YYYY-MM", 2001-01 .. 2024-12, mm per month
  cc: Value; mean_imerg: Value; mean_power: Value;
  source_ids: SourceId[];
}

// GET /api/health  (deployment check, routine)
interface HealthResponse { status: "ok"; artifacts: Record<string, { schema_version: string; generated_at: string }>; }
                                                   // keyed by artifact file name, e.g. "risk_table.json"
```

Privacy settings: the step answers live only in the URL fragment (section 6b) and reach the server only in the
POST body; our server's request log is off (`--no-access-log`); the deployment is in the Railway Singapore region;
saved answers of signed-in farmers, with any typed prices and costs (section 12d), are stored in the database
(section 12c). Limitation: Railway edge logs still hold IP and path for 7 days on the Hobby plan (R-J20).

**Validation in `src/api.ts`** (routine). Every response is checked before any screen uses it:
- shape: every field of the types above is present with the right type; enums hold only listed values; every `Text`
  has `vi` and `en`;
- sources: every id in any `source_ids`, `threshold_source_id`, `values_source_ids` or `computed_by` is a key of the
  same response's `sources`;
- past years: `rules` has the five codes in order; `years` is non-empty and strictly ascending; every `shares` has the
  five codes;
- compare: `request` equals the body sent; `plans` holds exactly the six plan ids in canonical order; every
  `CropSpan` has all four dates or none, in order inside one year; every `oos_prediction` and `range_80` is null for
  years outside `test_years`; `range_80` is null wherever `oos_prediction` is null; `summary` is null exactly when
  fewer than 2 `real` values are non-null; every `per_year` lists exactly the requested years;
- method: each (`row_key`, `axis`) of `coverage` occurs once; `explain_terms` has the six keys in order.

**Loading and errors** (routine): while a request is loading, the page shows grey placeholder blocks (section 5) in
the same layout instead of a full-screen spinner. On a network failure, a non-2xx HTTP status, or a response that fails
validation, the page's content area shows text `common.error` and a button `common.retry` that repeats the request.
There is no app-level timeout: the browser's default network behaviour applies, because no source or decision gives a
timeout length [OPEN, section 15 item 9]. The past-years response is kept in memory for the life of the page (for
the checks of section 6b); nothing is stored across page loads.

---

## 11b. Method page `/phuong-phap` (officers and judges)

Data: `GET /api/method`. Title key `method.title`. Content in this order (final copy written in-event, section 15
item 5):
1. What the model answers: key `method.question` with `{first}` and `{last}` from `test_years` ("how much of
   the year-to-year swing in regional rice yield can NASA weather predict, tested on 2016-2024" in meaning). Then one
   metrics table per season in `SeasonCode` order, rows in API order, grouped under headings: main runs
   (`sensitivity` null, key `method.mainRuns`), then each sensitivity code (keys `sensitivity.no_fao_flagged`,
   `sensitivity.mae_skill`, `sensitivity.risk_level_features`, `sensitivity.window`, `sensitivity.centroid_points`),
   then spatial-holdout runs (`scheme` `spatial_holdout`, key `method.spatialHoldout`). Columns and header keys:
   model (`model.<model id>`), role (`role.<role>`), subset (`subset.national`, `subset.na_ht_th`, or the unit or
   region id after `unit:` / `region:` in `subset`, shown with its name from i18n), `method.col.rmse`,
   `method.col.mae`, `method.col.r2`, `method.col.skillB0`, `method.col.skillB2`, `method.col.skillBnw` (each
   `Interval` shown with `method.skillCi`), `method.col.coverage80`,
   `method.col.nRows`, `method.col.nTestYears`. The primary row (M1 ridge, spring rice) is marked with `role.primary`;
   secondary results with `role.secondary`. Each table row ends with a source button (`data-testid`
   `metric-row-<index>`) for its `source_ids`; the numbers in the row carry `data-source-ref` to it (H5). Skill, R2,
   RMSE and MAE are shown to 2 decimals, and coverage as a whole percent; a value that rounds to zero is written
   without a minus sign. Within a group, the rows of one province or one region (subset `unit:` / `region:`) fold
   behind one disclosure (`<details>`, closed at first), so the page opens on the national and Nghe An rows
   (roleplay audit 2026-11-16: the page was about 40,000 px tall). A table wider than its column scrolls inside its
   own focusable region, with the line `method.scrollHint` wherever the frame is narrower than the table.
   Then the gate verdicts per season from `gates` (`gate.G1` .. `gate.G4`, `gate.passed` / `gate.failed` /
   `gate.notRun`, `detail`). The claim key `method.weatherClaim` ("NASA weather improves the prediction" in meaning)
   is shown for a season only where `weather_claims` has `made: true` for it; otherwise no claim is shown and the
   result stands as it is. The frontend never decides the claim. For a season whose G4 failed, key
   `method.rangeHidden` states why its 80% range is hidden on the cards. A season whose G2 fails is reported
   with its skill and CI, never as "climate explains little". The sensitivity analyses are the three
   pre-registered runs (without FAO-flagged rows; MAE-based skill; risk-level count features) and the robustness
   runs (season window one month earlier, later or wider; one point at the province centre instead of
   farmland-weighted cells). The secondary models M2 and M3 and these runs are core; any pre-registered run that
   did not run is named in one `limitations` line. Then the `reports` items, each with its title, text and a source
   button. The irrigated-provincial-rice limitation is one of the `limitations` lines.
   Results chart (core; from the `metrics` rows of `GET /api/method` only, no new claims): directly below the
   metrics tables, key `method.resultsChart` (heading) and `method.resultsChartAlt` (text alternative). For each season
   it plots the main runs (`sensitivity` null, `scheme` `rolling_origin`, subset `national`): one row per model (not
   the three references), and for each of `skill_vs_b0`, `skill_vs_b2` and `skill_vs_bnw` one mark at `value` with
   a horizontal line from `ci90_low` to `ci90_high` (the year-bootstrap interval), a vertical zero line
   (skill 0 = no better than that reference) and the numbers printed beside each mark. It is drawn without a chart
   library, as inline SVG (`<svg role="img">` with a `<title>`, no `<canvas>`, no animation; H1, section 3), or as the
   metrics table plus CSS bars. The chart repeats numbers of the tables above, so it carries the same
   `data-source-ref` as its table rows (H5). A null interval is left out, never drawn as zero. Colour is never the only
   carrier of meaning (labels on every mark; text contrast H8). Layout details are a routine choice. Display
   precision as in the tables above.
2. Coverage table: one row per distinct `row_key` in order of first appearance in `coverage`, one
   column per axis in `CoverageAxis` order; header keys `method.col.crop`, `coverage.money`, `coverage.conditions`,
   `coverage.rice_history`, `coverage.model`, `coverage.water_tcvn`, `coverage.water_fao`; each cell its `text` and a
   source button for its `source_ids`. The coverage the team decided, which the rules files produce:

   | Crop | Money (P-02) | Conditions per crop | Rice history (NSO) | Model | Water TCVN 8641 | Water FAO TM3 |
   |---|---|---|---|---|---|---|
   | spring rice (CC5; also in the P-03 control) | yes for CC5; as text for P-03 | yes for CC5; no for P-03 (no dates) | yes | no: the spring test (G2) of the ridge model did not pass (planned as "2016-2024 only, if the spring test passes" before the results) | yes (the spring rows of Trung bộ and Bắc bộ) | yes |
   | summer-autumn rice (P-03 control) | as text (P-03 definition) | no (P-03 gives no dates) | yes | never (G1 fails) | yes (Trung bộ rows; the Bắc bộ rows are spring and mùa) | yes |
   | peanut, grain maize, soybean | yes | yes | no | no | yes | yes |
   | sweet potato | yes | yes | no | no | yes | not listed |
   | mung bean, black bean, black sesame, chili, pumpkin, biomass maize | yes | yes | no | no | not listed | not listed |

   The method page names the studies by first author and year, not by the labels P-02 and P-03: P-03 appears there
   as "Trịnh Đức Toàn et al. 2023, 'rotation formulas'"; CC1-CC5 are the study's own plan names and stay. The labels
   in this table are our shorthand.

3. Explain the terms: one section per `explain_terms` entry in `ExplainKey` order, its `title`,
   `text` and a source button. Content of the six entries:
   - `evapotranspiration`: water leaving soil and plants as vapour (FAO-56, R-M01); not used for any displayed
     number;
   - `soil_moisture`: GWETROOT root-zone wetness from MERRA-2, a modelled value, not a measurement (R-W12, R-N01);
     used as a model feature and shown on the cards next to its 1991-2020 average;
   - `ndvi`: not used, and why: an in-season vegetation signal would leak the outcome into the features (ML-DESIGN.md
     §4 forbidden features);
   - `frost`: not covered, and why: QĐ 18/2021 Art. 5.19 defines sương muối only in words (R-A01); news reports it in
     high mountain communes, not on the target lowland rice land (PRD.md §8);
   - `water_balance`: not computed, and why: the published water index could not be reproduced from its paper without
     our own gap-filling choices;
   - `data_types`: reanalysis vs satellite vs station: NASA POWER daily values come from the MERRA-2 reanalysis
     (R-N01; the plain-language definition is taken from the GMAO MERRA-2 FAQ, R-W12, when the copy is written); GPM
     IMERG Final combines satellite estimates with the GPCC rain-gauge analysis (R-N05) and is used only for the
     method-page rain check; no station data is used; gridded values smooth extremes (Zhang et al. 2011, R-A10).
4. Data and NASA use: the line `common.dataLine`; the farmland weighting, key `method.farmland` (POWER cells weighted
   by the farmland mask: minimum MODIS cropland percent over 2001-2015, class 12 counted at 80% and class 14 at 50%,
   adapted from Dong et al. 2016, R-K12; ML-DESIGN.md §4). Bonus, built only after the core: the grid figure: the
   image `artifacts/figures/nghe_an_grid.svg` (the Vietnamese page uses `nghe_an_grid.vi.svg`, same drawing, served at
   `GET /api/figures/nghe_an_grid.vi.svg`) served by the backend (Nghệ An
   boundary and its POWER cells shaded by farmland weight, from data/processed/cell_weights.csv and geoBoundaries) with
   alt text key `method.gridAlt` and caption key `method.gridCaption`. Then the satellite rain check from `rain_check`
   (DATA-DICTIONARY.md §5c): heading `method.rainCheck`; a table of the monthly values (columns month,
   `method.col.imerg`, `method.col.power`) collapsed under a disclosure; the correlation `rain_check.cc` with key
   `method.rainCc`; the mean monthly rain of each series (`rain_check.mean_imerg`, `rain_check.mean_power`); the
   lines `method.rainNotTruth` (neither is ground truth) and `method.rainGauges` (both use rain-gauge information, so
   the check is partly independent; R-N05, R-N06); no pass or fail wording. When `rain_check` is null, key
   `method.rainNotRun`. The table is the display, because chart libraries are not on the allow-list of section 3.
4b. Datasets considered and not used: one line each, dataset name, official fact and reason (key `method.notUsed`;
   content in `rules/method.yaml`).
5. Limitations, one line each (`limitations`); the PICSA sentence (key `method.picsa`: "The comparison follows steps B
   to G of the PICSA field manual (Dorward, Clarkson and Stern 2015): past-year climate, counting years, an options
   table, and the farmer decides. It is not a full PICSA process: PICSA is run by trained staff with farmer groups,
   and this tool has not been tested with farmers.", R-U19; never claimed as a PICSA implementation); the AI-tool
   disclosure (key `method.aiTools`, REFERENCES.md §7); key `method.noUserTest` ("Usability has not been tested with
   farmers").
6. Link `method.advancedMap` to `/ban-do` only if that page exists (section 12).

---

## 12. Optional advanced page `/ban-do` (2D map over time) for officers and judges

- This is a later feature. It is started only after every test in section 14 passes for the farmer routes and the
  team says go. It is a bonus item, after the secondary models and before relief, sign-in and price entry, because
  the team puts quality before coverage. It is not promised in the pitch. It is built last, after checking the
  product frontend for a map; where a map already exists, only the missing enhancement is built.
- A separate short spec for this page is written and approved before it is built (section 15 item 4). Until then the
  route, its code and its code-split chunk do not exist.
- Reached only from `/phuong-phap` (link `method.advancedMap`), never from the farmer steps.
- MUST be code-split (`React.lazy`) so its libraries are never downloaded on farmer routes.
- Content: a 2D map of the Nghệ An boundary and its POWER cells drawn as inline SVG (no map, chart or 3D
  library; no canvas, H1). The user picks a year (1995-2024) and one official rule; each cell shows whether that rule
  was met in that year over the field days of the P-02 crops (the `year` level of DATA-DICTIONARY.md §4b, per cell),
  as met / not met / no data with a text label (never colour alone, H11), and its farmland weight; the province share
  of DATA-DICTIONARY.md §4b is shown next to the map. There is no 3D (team decision). A second, lower-priority layer
  is NASA SRTM shaded relief. It is added only after the map works and passes its tests, with its own download, a
  cited shading method, and the label key `map.reliefNote` ("height only; says nothing about where water reaches" in
  meaning). The page shows only data the project already has with sources: NASA POWER grid cells and their farmland
  weights (DATA-DICTIONARY.md §3), the official-condition shares per cell (the per-cell artifact is defined in the
  page's spec), the province boundary (geoBoundaries), and NASA SRTM elevation if downloaded and cited (the challenge
  page lists SRTM). It MUST show the same source facts (section 10) and MUST NOT show any farm-level prediction
  (CLAUDE.md boundary).

  Status (2026-11-16): the map lives in the data room (`#/khoa-hoc`, Grid3D flat 2D mode), so there is no `/ban-do` route and T15 stays skipped.
  The SRTM relief layer is built there: toggle `science.reliefToggle`, note `science.reliefNote` (the spec's `map.reliefNote`; the map texts live under `science`), source R-N12 and Horn 1981 (R-M29).

---

## 12b. Footer, About page, Sources and credits page

- Every page has a short footer (member A, 2026-11-15): the Miaudow emblem and wordmark, the reminder
  `common.support`, two links (`footer.privacy` to the privacy page, `footer.code` to the code repository, each at
  least 44 x 44 px, H7) and the team and licence line `footer.team`. Nothing else: no copy of the menu, no data line,
  no build time. Data credits stay next to the values they credit; the photo credits are a section of the evidence
  page (`evidence.photosTitle`). MUST NOT show any NASA, FAO or Space Apps logo. MUST NOT mention Space Apps anywhere
  in the app. MUST NOT imply endorsement by NASA, FAO, NSO or any ministry.
- `/gioi-thieu` (title `about.title`) sections, in this order:
  1. What it is and who it is for: compares a few tested one-year crop plans for drought-prone, low-productivity rice
     land in Nghệ An; it compares, it does not decide.
  2. What it does not do: not a forecast, not advice for one specific field (regional numbers only), revenue is not
     profit. Same warnings as the cards (H17).
  3. Data and how the numbers are made: one paragraph, links to `/phuong-phap` and `/nguon`.
  4. Team name, project email (no home address, no personal phone), how to ask for a correction or removal (by the project
     email; no response time is promised to users; the team removes unlawful content within 24 hours of a request from
     the Ministry of Information and Communications, Nghị định 147/2024 Art. 24.4, R-J01), licence (Apache-2.0),
     AI tools used (CR-04).
- `/nguon` (title `sources.title`): the POWER credit sentence (R-J16); the NSO credit `common.nsoCredit`; every study
  and standard by author and source (values only, never their text); geoBoundaries with URL; software licences (the
  file written by `rollup-plugin-license`, section 3); photo credits (the Wikimedia Commons credit lines and
  "Contains modified Copernicus Sentinel data 2020-2024" for the Sentinel-2 images); AI tools.
- NSO credit (R-J10; routine for the placement): key `common.nsoCredit` (Vietnamese text "Nguồn: trang Thông tin
  điện tử Cục Thống kê (www.gso.gov.vn)", the wording the NSO footer asks for: "Ghi rõ nguồn trang Thông tin điện tử
  Cục Thống kê (www.gso.gov.vn) khi trích lại thông tin", R-J13) is shown once inside every block that shows a
  `Value` whose `source_ids` include a source with `nso_credit: true`. These blocks are the rice part (b) of each
  Stability row and each method-page table or report with such a value. Because the credit sits inside the card, it
  is printed with the card (section 9b).
- Copy is written during the event (section 2); before then only the shells and keys exist.

## 12c. Optional Google sign-in and saved answers (later feature)

- Started only after every section 14 test passes for the farmer routes and the team says go. Every
  farmer route MUST keep working without signing in.
- The feature saves the answers of steps 1-3 (land, years, priority), with any prices and costs typed in section
  12d, so a farmer can reopen them on another phone. Reopening a saved set brings the typed prices and costs back.
  Saving does not change any number (regional estimates only, CLAUDE.md).
- Google sign-in requests the smallest scope. The app stores only Google's account id and the saved answers, with no
  name, email or picture, if Google allows that scope [UNVERIFIED: check during the build].
- Before the first sign-in the farmer sees a short privacy notice (what is stored, where, for how long, who hosts
  it). `/da-luu` has
  a "delete my account and all saved answers" button that deletes everything at once. The privacy notice is the
  page `/quyen-rieng-tu` (the path registered with Google; `/privacy` redirects to it with HTTP 308); it says that
  saved answers include any typed prices and costs.
- The Google sign-in script makes third-party requests and may set cookies; this is allowed only on `/dang-nhap` and
  `/da-luu` (H14), and T14 excludes those two routes. Their own privacy test is written with this feature.
- The database is Railway PostgreSQL (team decision: it survives redeploys and allows more than one instance). No
  backup schedule is set, so "kept until you delete it" stays true.
- A farmer may keep several saved sets of answers, at most 20 per account: a 21st save is refused (HTTP 409) and the
  page shows a "full, delete one first" message. How `/da-luu` lists, names and deletes single sets is [OPEN,
  section 15].

---

## 12d. Optional "your price and costs" (FR-13; later feature)

- Started only after every section 14 test passes for the farmer routes and the team says go. Cards work
  without it.
- On a plan card, a button key `plans.yourNumbers` opens a form: for each crop of the plan, the farmer's sale price
  in đồng per kg (the unit P-02's sums use) and cost in million đồng per ha, the unit every money number on the cards
  shows (D-190, D-192); the link and a saved set keep the cost in thousand đồng per ha, as before. Entry is per hectare only: no official Nghệ An sào size was found (Nghị định 86/2012 gives only the Trung Bộ
  sào). The `usual_p03` card has no entry (its money is text only and never compared with P-02 money).
- Inputs are `<input type="number">` (numeric input, allowed by H4 and T4, which forbid only free-text fields): the
  price a whole number (`inputmode="numeric"`, `step="1"`); the cost in million đồng per ha with one decimal mark
  (`inputmode="decimal"`), converted once to whole thousand đồng per ha, half up (D-192). Stored values stay whole
  numbers of at most 9 digits (up to 999,999,999 đ/kg or thousand đ/ha, far above any real value; a crafted link with
  a very long number froze the cards); empty fields are allowed. A value that is
  not such a number is not used, and the field says so ("tối đa 9 chữ số" / "up to 9 digits" for a longer one). Each
  input has a visible label (crop name, season label, unit) and the font and tap-target rules (H6, H7); the study's
  own yield, price and cost are shown beside it.
- The output is labelled with key `plans.yourNumbersLabel` ("the study's yield with your prices and costs, not your
  field's harvest"): revenue = study yield x your price; net margin = revenue - your costs, shown only when costs
  are entered (FR-13, CLAUDE.md revenue-not-profit rule). The study yield per crop is P-02's "Năng suất" (Tables 4,
  8, 12). A whole-year sum is shown only when every crop of the plan has the numbers it needs, labelled like
  `money.ourSum`.
  Revenue and margin are rounded once, at the end, to whole thousand đồng per ha, half up. The study's own numbers
  stay visible next to it.
- The sums are computed in the phone's browser, a stated exception to "the backend rounds" (section 11). Each
  computed number cites the study yield (R-P02) and the "engine computations" id (section 11); its source sheet adds
  that the price and costs are the farmer's own numbers, as entered and not checked.
- Fragment keys: `yp.<crop_key>=<whole number>` (your price) and `yc.<crop_key>=<whole number>` (your cost), written
  only by the form; a key whose crop key is not a money item of the compare response, or whose value is not a whole
  number of at most 9 digits, is dropped (section 6b rule 2). Entered numbers stay in the URL fragment and never go in
  a request URL. When a signed-in farmer saves the answers, the typed prices and costs are saved with them (section
  12c), with the same checks (whole numbers, at most 9 digits, known crop keys only); without a save they stay in the
  page address only.

---

## 13. Skeleton: the first event work (from 09:00 Sat 14 Nov)

Build exactly this, with placeholder text only; no product screen is built before the skeleton is done:
1. Vite + React + TypeScript + Tailwind project in `frontend/`, only the packages of section 3, pinned versions,
   `npm run dev`, `npm run build`, `npm test`, `npm run e2e`.
2. Route shells for exactly these routes: `/`, `/ruong`, `/nam`, `/uu-tien`, `/phuong-an`, `/khong-co-phuong-an`,
   `/phuong-phap`, `/gioi-thieu`, `/nguon`. Each shell renders `Page` with its `<h1>` title key, the progress text and
   Back button of section 6, the language toggle and the footer, and nothing else. The fragment rules of section 6b,
   the navigation of section 6a and the language rules of section 6c work on the shells. No shells for `/ban-do`,
   `/dang-nhap` or `/da-luu`.
3. Components (no real content): `Page`, `StepHeader`, `Footer`, `LangToggle`, `ProvinceLine`, `ChoiceButton` (with
   `PictureSlot`), `PrimaryButton`, `Chip`, `YearRowToggle`, `RuleLegend`, `PlanCard` with the fixed row slots,
   `MonthBar` (quarter labels, lanes, bare-period hatching), `NumberButton`, `Disclosure`, `SourceSheet`, `Banner`,
   `ShareButtons`, `LoadingBlock`, `ErrorBlock`.
4. `src/i18n/vi.ts` and `en.ts` with every key named in this document, values = the key name in brackets (e.g.
   "[field.question]"). (The plan said JSON files; the built app uses these TypeScript files.)
5. `useT()` (section 6d); `src/api.ts` with the validation of section 11; `public/fixtures/past-years.json`,
   `compare.json`, `method.json` matching section 11 with placeholder values (section 11 fixture rules).
6. Every test of section 14 exists. Tests marked "now" run and pass on the skeleton. Tests marked "event" need real
   screen logic or real copy: they are written with their checks as skipped tests (`test.skip` in vitest and
   Playwright) until the screen work starts, and enabled while the screens are built. T15 stays skipped while
   `/ban-do` does not exist.

The screens of sections 7-11b, real copy, real plan data, real numbers and drawings are built only after the
skeleton.

---

## 14. Acceptance tests (automated; all MUST pass)

Playwright at viewport 360 x 740 on every page named in the test, plus vitest unit tests. "Pages" means the set of
section 4.

| Test | Checks | Before the event |
|---|---|---|
| T1 no-3d | no `<video>` on any page; no `<canvas>` or WebGL context on the farmer routes; with reduced motion emulated, no running CSS animation or transition on any page (H1) | now |
| T2 no-slider | no `input[type=range]`, no `[role=slider]` on any page (H2) | now |
| T3 order | (pytest) `compare()` output is identical for every `priority` and every `land` except the `request` echo; (Playwright) card order equals API order, and changing `priority` in the fragment with the same response changes only which row has `data-highlighted` and the priority line of cards `cc1`..`cc4` (H3) | event |
| T4 no-text-input | no `input[type=text|search|email|tel]`, no `input` without a type, no `textarea` on farmer routes (H4) | now |
| T5 numbers-have-sources | every element with `data-value` is a button that opens the source sheet, or has `data-source-ref` naming a button that does; the opened sheet has a non-empty `source.name` (H5) | event |
| T6 font-size | computed font-size of every visible text node >= 17 px on every page (H6) | now |
| T7 tap-targets | every interactive element bounding box >= 44 x 44 px on every page, the open source sheet included (H7) | now |
| T8 contrast | each token pair listed in section 5 >= 4.5:1 (H8) | now |
| T9 zoom | at 200% zoom (viewport 180 x 370 CSS px equivalent) no content is clipped and all buttons are reachable on every page (H9), including the year list and the month bar | now (shells); event (screens) |
| T10 no-hscroll | `document.documentElement.scrollWidth <= 360` on every page (H10) | now (shells); event (screens) |
| T11 highlight-label | exactly one row per card has `data-highlighted="true"`, it is the row of the chosen priority, and it contains the text of `plans.yourPriority` (H11) | event |
| T12 i18n | every key used in code exists in vi.ts and en.ts; vi.ts and en.ts have the same keys; no hard-coded user-visible strings (H15); every key of section 6d with params is called with all its params | now |
| T13 not-forecast | `common.notForecast` visible on `/nam` and `/phuong-an` (H13) | event |
| T14 no-personal-data | on every page except `/dang-nhap` and `/da-luu`: no cookies set; no localStorage or sessionStorage writes; no requests to third-party hosts (only exceptions: the NASA GIBS map tiles and the NASA Eyes frame on `/dai-quan-sat`; voice input on `/tro-ly` starts only after a tap, with a note that the browser may send the audio to its provider); the farmer routes and the home page make no third-party request; answers and typed prices never appear in any request URL (H14) | now |
| T15 lazy-map | loading `/phuong-an` does not download the `/ban-do` chunk (section 12) | skipped until `/ban-do` exists |
| T16 card-warnings | each card element contains, inside its own bounding box, the texts of `plans.trialNote`, `money.priceYear` (or `money.priceYearNotStated`), `common.notForecast` and `common.supportNote` (H17) | event |
| T17 support-note | `common.supportNote` visible on `/` and `/phuong-an` (H18) | event |
| T18 two-sources | every condition share (card number buttons and legend "?" buttons) opens a sheet with the R-A01 block (with `source.ruleText`), the R-N01 and R-N02 blocks and `conditions.computedNote`; `common.dataLine` visible on `/nam`, `/phuong-an` and in every footer (H19) | event |
| T19 bare-periods | for a fixture plan with a gap between spans, the bar shows the hatched period and the `calendar.bare` text with its dates; a wrapping period is drawn in two pieces with one label; no bare shading on the P-03 card (H11, FR-18) | event |
| T20 month-labels | the `MonthBar` component shows exactly the texts of `calendar.m1`, `calendar.m4`, `calendar.m7`, `calendar.m10` and fits 360 px at 17 px (H6, H10) | now (component) |
| T21 p03-card | the `usual_p03` card shows `calendar.noDates` and the money of each season in `season_values` (a number with its source, or the paper's words for the fallow), and no per-crop money list or total | event |
| T22 money-total | the total carries the `money.ourSum` label; a `flag` renders next to its value | event |
| T23 oos-only | `src/api.ts` rejects a compare fixture with a non-null `oos_prediction` or `range_80` for a year outside `test_years` and shows `common.error` with `common.retry` (now); predictions render only where non-null (event) | now (validation); event (render) |
| T24 not-available | a null `real` renders `common.notAvailable` | event |
| T25 small-pick | a `summary: null` stability renders each year's value and no min / median / max and no `stability.worstYears` | event |
| T26 stability-scope | every stability block shows `years_count` with `stability.yearsCount` and the `scope` text | event |
| T27 no-soil | no response fixture or API response contains the SoilGrids source ids `R-D02` or `R-D03`, and no i18n key starts with `soil.` | now |
| T28 year-list | `/nam` renders one row per year in one column; each row is one button >= 44 px high with no interactive element inside it; no grid with fixed columns | event |
| T29 method-page | `/phuong-phap` shows the coverage table rows from the API and the six explain-term sections, each with at least one source button; `method.weatherClaim` appears only for seasons with `made: true` | event |
| T30 range-only-with-prediction | a `range_80` value is shown only next to an `oos_prediction`, and nothing is shown when `range_80` is null | event |
| T31 fragment | on the shells: invalid and unknown keys are dropped; the redirects of section 6b rules 3-5 go to the right route with the cleaned fragment; `land=irrigated` goes to `/khong-co-phuong-an`; each step writes only its own key | now |
| T32 navigation | Back goes to the route of section 6 with the fragment kept (a cold `/phuong-an` link goes back to `/uu-tien`); `/` has no Back and no progress text; `/khong-co-phuong-an` has no progress text; focus moves to `<h1>` and `document.title` equals the page title key's text after each route change | now |
| T33 language | `lang=en` renders English and sets `<html lang="en">`; missing or invalid `lang` renders Vietnamese when the emulated browser languages include a `vi` entry (for example `en-US, vi`) and English otherwise (for example `en-US`, `fr-FR`), and Vietnamese when no language is given; the toggle shows `lang.toEn` or `lang.toVi` and writes only `lang` | now |
| T34 api-validation | each validation rule of section 11 rejects a broken fixture variant and the page shows `common.error` with `common.retry` | now |
| T35 print | with print media emulated, every `Disclosure` content is visible and the share, print, Back, Next and language buttons are hidden | now (components) |
| T36 soil-wetness | every crop with an `exposure` entry shows, per picked year, the soil wetness value and its 1991-2020 average as number buttons and the `water.soilModelled` label; a null shows `common.notAvailable` | event |
| T37 priority-line | (bonus item; skipped until the priority line is built) the priority line exists on `cc1`..`cc4` only, inside the highlighted row; for income and land it shows the `usual` card's values from the same response; its text contains none of the words listed in the glossary as banned for it (better, best, should, recommended and their Vietnamese equivalents) | event |
| T38 check-row | every card has the `check` row open (no disclosure) between `land` and `why`, with one line per risk and the `check.localReview` line; `why` has no risk lines | event |

### 14a. Test hooks (routine)

In the product frontend the hooks follow the team's web app names where they differ.

`data-testid` values: `back`, `next`, `lang-toggle`, `source-sheet`, `legend-<rule code>`, `year-<year>`,
`chip-land`, `chip-years`, `chip-priority`, `card-<plan id>`, `card-<plan id>-row-<row key>`,
`card-<plan id>-calendar-source`, `metric-row-<index>`. Data attributes: `data-value` (displayed value string of a
sourced number), `data-source-ref` (the `data-testid` of the button that opens its source), `data-rule` (rule code of a
share), `data-highlighted="true"` (the priority row).

---

## 15. Open items (do not guess; ask the team)

1. Final Vietnamese and English copy for every key: written during the event.
2. Hand-drawn pictures for the choice buttons (Medhi 2011): who draws them and when (during the event). The app's
   current home and field-step illustrations are AI-generated: [OPEN] they need a watermark and a declaration, or
   they are dropped (R-H15).
3. Land-type labels beyond the required official words (section 7): settled as the studies' own Vietnamese phrases
   ("đất lúa kém hiệu quả, thường xuyên khô hạn" from P-02; "đất lúa kém hiệu quả, có nguy cơ thiếu nước" from P-03),
   with a plain English translation.
4. Short spec for `/ban-do` before building it (section 12), including its libraries and per-cell artifact.
5. Content of `/phuong-phap` beyond section 11b (method, data sources, limitations, the PICSA sentence,
   AI-tool disclosure): written during the event from ML-DESIGN.md and REFERENCES.md.
6. Usability has not been tested with farmers (no tester): stated on `/phuong-phap`.
7. [OPEN] Procedure for a farmer who converts their own rice field (Nghị định 112/2024 Art. 8 names a form only for
   perennial crops and rice-fish): shown as an information gap, not answered.
8. Sign-in data is stored in Railway PostgreSQL (team decision); its cost follows Railway's pricing, accepted by the
   team.
9. [OPEN] Request timeout: none is set (browser default) because no source or decision gives a length.
10. Display precision of the method-page metric numbers: settled (skill, R2, RMSE and MAE to 2 decimals; coverage
    as a whole percent; section 11b).
11. Details of section 12d (study-yield field, fragment keys, computed-number source sheet): settled and written in
    section 12d.
12. [OPEN] How `/da-luu` lists, names and deletes single saved sets when a farmer keeps several (at most 20, section
    12c).

## 16. Requirements referenced

Requirements (SRS.md): FR-01 is the locked province line (section 7), FR-11 the method page (section 11b),
FR-13 the optional price and cost entry (section 12d), FR-14 print and share link (section 9b), FR-15 the "explain
simply" button on the cards (section 9), FR-17 the "Why this plan" row, FR-18 the bare periods.
