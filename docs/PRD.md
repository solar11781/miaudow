# Product Requirements (PRD)

This document describes the current design only. It is the specification the submitted app was built from: the
provisional v0.4 of 2026-11-13, updated with the team's later decisions up to 2026-11-15. The app was submitted for
Hanoi judging on 15 Nov 2026 (tag `submitted-hanoi`). We read the official Resources tab on 2026-11-13, and it did
not change the core (R-H16).
The app is called Miaudow in both Vietnamese and English. The project name is Field Shift Nghệ An.
The evidence is listed in REFERENCES.md and DATA-SOURCES.md, and the screens and data contract are in UI-UX-SPEC.md.

## 1. Problem

On drought-prone, low-productivity rice land in Nghệ An, a farmer asks:

> "What should I plant this year, and in what order, so I balance income, climate risk and the long-term health of my land?"

The sources describe what farmers grow on this land today in different ways [RESEARCH]. The P-02 trial (Lưu Sơn,
Đô Lương) names the local structure "Lúa - Đậu - Khoai lang", and P-03 at the same site names "Lúa - lúa - bỏ hoang".
A 2013 news report says that in the 2000s, water-short crop fields ("đất màu") in Nam Cường (Nam Đàn) carried "chỉ
cơ cấu 1 vụ xuân trồng lạc, ngô, sau đó bỏ hoang vụ hè thu", and that farmers later added mung bean (Báo Nghệ An
2013, R-C07; re-read 2026-11-13). "Drought-prone, low-productivity rice land" is a description used in policy and
research, not a legal category (Nghị định 112/2024/NĐ-CP has no definition of "kém hiệu quả").

A published field trial in Nghệ An (P-02: Lưu Sơn, Đô Lương, June 2020 - June 2021) tested crops in each season on
this land type, grouped in four structures, next to the farmers' usual structure. Farmers have no simple way to
compare such options with what they do now, in past years with known official weather conditions.

## 2. Product statement

Miaudow is a visual decision-support tool in Vietnamese. It lets a farmer (or an extension officer helping a farmer)
compare a small set of evidence-backed one-year crop sequences for their land type, in past years that the farmer
picks. Each picked year is shown with the share of Nghệ An farmland where each official Vietnamese hazard rule was
met. The plans are compared on four transparent trade-off axes and shown as one card per plan with identical rows,
without a score or ranking:

1. Money: the card shows the net profit per crop, including labour, as reported in P-02 Table 13. All values come
   from one study with one profit definition. They are shown with their source facts: one unreplicated 1,000 m2 plot
   per crop, in one year (2020-2021). The whole-year sums are our own arithmetic. We make no profit claim for the
   farmer's own field unless the user enters costs.
2. Climate risk and stability: the card shows the regional rice-season history for the picked past years as the
   lowest, middle and highest value, with the worst years named. This summary is built from 2 picked years with a
   real value; otherwise the card shows each year's value. There is no "bad year" label. The real history is always
   shown. For picked years 2016-2024 only, the model's out-of-sample prediction for spring rice may be shown next to
   it, never in its place, and only if that season's own test passes. Its 80% range is shown only when G4 passes for
   that season. There is no model value for 1995-2015. Summer-autumn rice shows history numbers only, because gate G1
   fails for it. Official-condition shares per crop are shown for every plan with P-02 field dates (CC1-CC5). The
   P-03 card has none, because P-03 gives no sowing dates (ML-DESIGN.md §5a).
3. Water: the row shows sourced facts only and no crop water score. (a) It shows the drought rain-part shares per
   crop and picked year, in both readings, for every plan with P-02 field dates (CC1-CC5; the P-03 card has none).
   (b) It shows the TCVN 8641:2011 irrigation amounts where the standard lists the crop: maize 2,000-2,500 m3/ha for
   the whole season; peanut about 2,000 m3/ha; soybean about 2,000 m3/ha (§6); sweet potato 1,200-1,400 m3/ha. For
   rice, the standard gives amounts per region, season and method, for maintenance only (land preparation excluded).
   Both regions are shown, and each rice crop gets the rows of its own season: "khu vực Trung bộ" transplanted
   spring 6,500-7,500, summer-autumn 6,000-7,000, direct-seeded spring 6,500-7,500, summer-autumn 5,700-7,000; Bắc bộ
   spring 6,000-7,000, mùa 4,500-5,500 m3/ha (ML-DESIGN.md §4b). The standard does not state whether Nghệ An falls
   under Trung bộ or Bắc bộ, and the card says so next to the figures. (c) It shows the seasonal crop water need from
   FAO Training Manual 3 Table 14 where the crop is listed, labelled as FAO's "rough estimate": maize 500-800 mm,
   peanut 500-700 mm, rice (paddy) 450-700 mm, soybean 450-700 mm. Crops that a source does not list show "not listed
   in the source". Pumpkin is in neither table, and FAO's melon row (400-600 mm) is a different crop, so it is not
   used for pumpkin. No source applies the maize rows to biomass maize harvested green, so biomass maize says "not
   listed in these sources". (d) It shows NASA POWER root-zone soil wetness (GWETROOT) per plan crop and picked year,
   next to its 1991-2020 average. The value is labelled as a NASA model value (MERRA-2) and not a measurement, and it
   has no category word, colour or threshold (SRS.md FR-20).
4. Land care: the row shows three separate checks and no score. The first is the number of different crops in the
   year. It cites the FAO Conservation Agriculture principle "Species diversification ... at least three different
   crops" with its context: the principle describes crop sequences in conservation agriculture, not a count per
   year. The second is the number of days with a living crop out of 365 (NRCS "Maximize Continuous Living Roots").
   The third is whether a legume is grown, with the caveat from Witcombe and Tiemann 2022: groundnut "would be a heavy
   miner of soil N" if stover is removed, with the source's qualifier "<70% BNF efficiency", and field balances "were
   only positive when residues were spread and incorporated". Yao et al. 2025 (legume before rice) is not cited on any
   card, because no shown plan has a legume directly before rice (in CC5 the black bean is followed by sweet potato,
   not rice; P-02 Tables 1, 5, 9).

Every number shows its source and a trust label made of facts about that source. The tool shows the comparison and
leaves the decision to the farmer.

## 3. Users

| User | Need | Implication |
|---|---|---|
| Primary: smallholder farmer, Nghệ An, limited technical literacy | Understand options in plain Vietnamese, in a few taps | Icons, pictures, few words, no ML or satellite terms, mobile-friendly |
| Secondary: commune extension officer / cooperative leader | Explain options to farmers, see sources | Evidence panel, printable/shareable summary |
| Tertiary (competition): NASA judges | See NASA data use, scientific validity, honest limits | Method page with validation results and limitations |

Assumption: in most cases an extension officer will operate the app, because face-to-face extension is the most
common channel in Vietnam (IRRI/IFAD brief 2022). We found no data on use in Nghệ An itself (NOT FOUND). The design
therefore treats the farmer as the reader and the officer as the operator. We have no access to real farmers before
submission, so we cannot test with them; this is a stated limitation.

## 4. MVP scope (must ship)

1. **Farm setup**: a locked province line shows Nghệ An as the default and only value (other provinces come
   through the country adapter, ARCHITECTURE.md §1b). The farmer picks the land type from picture cards that use the
   official commune wording ("cao cưỡng", "cuối kênh", "thiếu nước"), or the option "không chắc, hỏi cán bộ khuyến
   nông". The answer selects regional content only and also carries the water situation, so there is no per-season
   water question. There is no soil card, because the SoilGrids producer advises against local, farm or subnational
   use (R-K13).
2. **Past-year picker**: the farmer picks past years (1995-2024) to compare, and the picker labels them "past year,
   not a forecast". Each year row shows the year and, for each official hazard, the share of Nghệ An farmland where
   the QĐ 18/2021/QĐ-TTg risk-level rule was met (heavy rain Art. 44, heat Art. 47, drought rain part Art. 48,
   damaging cold Art. 53; R-A01; ML-DESIGN.md §5a). The share is computed per NASA POWER cell over the days and
   months in which any P-02 crop was in the field in that calendar year. Level 1 or higher counts as "rule met", and
   the share is given in whole percent. There is no yes/no cut-off and no summary box. The drought rain part (monthly
   rain more than 50% below the 1991-2020 mean, "kéo dài từ 2 tháng đến 3 tháng") is shown with the rule's own
   wording and with both counts (consecutive months; any 2 months), because the rule does not say whether the months
   must be consecutive. The site shows these limitations: "we apply the official thresholds to NASA's 50 km grid
   values; gridded values smooth extremes (Zhang et al. 2011, abstract)"; issued levels weigh more factors than the
   tables, so ours is a mechanical reading (R-K03); the values come from {n} NASA weather squares of about 50 km;
   daily totals can miss heavy rain that crosses midnight; heat or cold spells whose days fall in different
   temperature bands are not counted.
   The basic definitions (QĐ 18/2021/QĐ-TTg Art. 5, R-A01; TT 25/2022/TT-BTNMT Art. 3.6) are used only as ML
   features, never as the displayed labels (ML-DESIGN.md §4). Their thresholds are strict, as the articles word
   them. A heat day has a daily maximum strictly above 35 C (Art. 5.21 "vượt quá 35°c"), counted over the whole
   season window because flowering dates are not sourced. Heavy rain is more than 50 mm in 24 h (Art. 5.17). The
   drought rain condition is computed in both readings against a rain normal from training years only. Rét hại is a
   daily mean strictly below 13 C (Art. 5.18 "dưới 13oc"), and rét đậm is a daily mean below 15 C
   (TT 25/2022 Art. 3.6). The displayed risk-level labels use Art. 47 and 53, where 35.0 C and 13.0 C are included.
   The two sets of counts are never mixed.
3. **Priority question** (provisional): one question with tap buttons asks for the single most important priority
   (income, stability, water, land care). There are no sliders, no weights and no "least important" question. The
   chosen priority only highlights its row on every card; it adds no score and does not reorder the cards. This
   design rule is informed by abstract-only studies that did not involve farmers (web surveys, medical risk
   communication), and it stays provisional until it is tested with users.
4. **Seasonal timeline**: each plan has month-by-month bars (Jan-Dec), drawn from the sowing and harvest dates
   reported in P-02 Tables 1, 5 and 9. Overlaps are drawn as reported (see 6).
5. **Side-by-side comparison**: the app shows the four structures of P-02 (CC1 peanut L20 - mung bean D22 - grain
   maize VN5885; CC2 chili - soybean ĐT51 - biomass maize NK7328; CC3 grain maize VN5885 - black sesame - pumpkin;
   CC4 biomass maize - biomass maize - sweet potato) and the farmers' usual structure from the same trial (CC5 rice -
   black bean - sweet potato), unranked. It also shows the P-03 local control (rice - rice - fallow) as the second
   description of local practice. P-02 and P-03 disagree at the same site, and both are labelled. Each plan is
   described as "each crop tested in its season on this land type (P-02, 2020-21)", never as a tested or proven
   whole-year sequence.
6. **Trade-off view**: each plan gets one card with identical rows in real units. There is no combined ordering,
   score, tie rule or dominance flag. Non-comparable cells are marked and never silently imputed. The plans are shown
   with these limitations: single unreplicated 1,000 m2 plots in one year cannot separate small differences; it is
   unknown whether one field carried each whole structure; reported dates overlap in two places (CC1 mung bean
   harvest 30/8-3/9 vs maize sown 1/9; CC5 black bean harvest 25/8 vs sweet potato sown 15/8); the methods list of
   P-02 disagrees with its results tables on the CC2-CC4 crops (the seven results tables agree with each other and
   are used), and Table 4 has two identical rows (CC1 mung bean and CC5 black bean).
   Each plan also gets a short block, as the official objectives ask: why it is shown, the supporting evidence,
   possible benefits, information gaps, and risks needing local review by farmers or extension officers.
   The timeline shades the months when the field is bare, which is also an official ask. We make no erosion claim:
   bare months are not presented as erosion, because flat paddies trap sediment (Slaets et al. 2016).
   For income, a field-trial yield is never ranked against a provincial-average rice yield. All plan money comes
   from P-02, so it shares one site, one year and one profit definition.
7. **Evidence and limitations panel**: for every displayed value, the panel shows the source, a trust label of
   source facts and the source's limitations.
8. **Method page** for judges: the page shows the data, the ML target, the validation, the reference forecasts
   against the model, and the gate results (the numbers in gates G2-G4 are team choices, stated as such). It makes
   the claim "NASA weather improves the prediction" only if the model beats the same model without weather columns
   (BNW) on the test years; otherwise the model's predictions are not shown on the cards (G2). It also shows the
   PICSA sentence (the comparison follows steps B to G of the PICSA field manual and is not a full PICSA process;
   R-U19), the limitations and the failure cases.
9. Vietnamese and English UI: the starting language follows the browser's language setting, and a toggle switches it.
10. **Check before you change** (SRS.md FR-22): every card has an open row that lists the plan's risks needing local
    review, without any ranking.

## 5. Stretch (only after MVP works end to end)

The bonus items come in this order: satellite rain check; NASA grid figure; priority line; map page, then SRTM
relief; sign-in; price entry. The secondary models M2 and M3 and the pre-registered sensitivity runs belong to the
core and are not bonus items. SMAP comes only after the 11:00 Sunday submission. The scope is Nghệ An only, with no
other province. During the event the team decided to cut nothing and to build these items and item 5 below.

0. An optional 2D map page, then SRTM shaded relief, for officers and judges only. Farmer screens stay 2D. 3D
   appears only on pages outside the farmer routes, and only those pages load it.
2. Farmer-entered prices and costs (per hectare) give a net-margin estimate, labeled as user-entered. It is built
   only after the core works (FR-13, UI-UX-SPEC §12d).
3. A SMAP soil-moisture check of POWER GWETROOT, only after the 11:00 Sunday submission.
4. GPM IMERG monthly rain compared with POWER rain for Nghệ An, on the method page (this needs a free Earthdata
   login).
5. An LLM "explain this in simple words" button that uses member A's Claude API key. It started as a later idea; the
   team built it during the event and switched it on for the hosted Hanoi version. The server builds the text from
   its own compare answer, and the browser sends only a plan code and a field. The key lives only in the server
   environment, never in the frontend or the repository. The button is an exception to "no live external calls"
   (NFR-01), and this must be stated. Generated text is marked as SI-generated (R-H15).
6. Later idea: integrate a seasonal forecast, only with a verified source and a validated method. Any forecast shown
   is labelled as a forecast with its source, and past years are never presented as forecasts.
7. Later idea (team, 2026-11-13): a "country data pack" that lets a national team add its country. The pack would
   use a documented format (regional statistics, crop calendar, crop plans from local field trials with sources,
   official hazard rules quoted from that country's own texts, licences). The pipeline would check structure,
   sources and licences, retrain, and run the same pass/fail tests (ML-DESIGN.md §8), and a reviewer would approve
   the result before farmers there see anything. It is not built for the event; the pitch presents it as the next
   step for scaling (ARCHITECTURE.md §1b country adapter).

Items 5-7 are not in the bonus order above. Item 5 was built during the event, and items 6 and 7 stay later ideas.

## 6. Non-goals (explicitly out of scope)

- Field- or farm-specific yield prediction.
- Claims that ML learned causal crop-rotation benefits.
- Multi-year soil-health simulation.
- Profit optimization or price forecasting.
- A generic chatbot as the main interface.
- Automatic "the best rotation" without user priorities.
- Any crop without at least one documented source for the target land type.

## 6b. User stories (derived from the workflows below and the requirements; no new scope)

| # | As a ... | I want to ... | so that ... | Requirements |
|---|---|---|---|---|
| US-1 | farmer on dry, low-productivity rice land in Nghệ An | pick my land type from pictures, without typing | the app tells me whether the tested plans fit land like mine (dry or unsure: every plan is shown; irrigated: the no-tested-plan page, UI-UX-SPEC §7) | FR-01, FR-02 |
| US-2 | farmer | pick past years I remember (for example a drought year) and see the official hazard shares for them | I can compare plans under conditions I know, never as a forecast | FR-04 |
| US-3 | farmer | say what matters most to me (income, stability, water or land care) | the matching row is highlighted on every plan card, without reordering the plans | FR-05, FR-09 |
| US-4 | farmer | see one card per plan with months, money, risk, water, soil wetness and land care, and what to check before I change | I can compare keeping rice with the alternatives and know what to ask locally | FR-06, FR-07, FR-08, FR-17, FR-18, FR-20, FR-22 |
| US-5 | farmer or extension officer | tap any number to see where it comes from | I can judge how far to trust it | FR-10 |
| US-6 | judge or officer | read how the model was tested, what NASA data does and where the limits are | I can check the science myself | FR-11, FR-21 |
| US-7 | farmer or officer | switch between Vietnamese and English, and share or print the result | I can read it in my language and show it to others | FR-12, FR-14 |

## 7. Key workflows

**W1 - Compare options (core):** the user opens the app, chooses the land type, picks past years and answers "what
matters most". The app then shows one card per plan with its timeline and highlights the matching row on every card,
without reordering the cards. The user can tap a value to see its source.

**W2 - "What happened in a past drought year?":** the user picks a past year whose row shows a farmland share under
the official drought rain rule (both readings). The cards show the official-condition shares per crop and what
regional rice did in that year. Non-rice crops show "no regional data" (study values only), and summer-autumn rice
shows "not modeled". We assume no direction of the result in advance, because an exploratory check before the event
found no simple rainfall-yield relation for Nghệ An summer-autumn rice.

**W3 - Judge / officer checks the science:** the judge or officer opens the method page, reads the validation table
(reference forecasts against the model) and then the limitations.

## 8. Competition alignment

The official text is the Field Shift challenge page (R-C03; the team pasted its text on 2026-11-10). We read the
Resources tab (R-H16) on 2026-11-13, and it did not change the core.

| Official ask | Our answer | Status (Hanoi version, 15 Nov 2026) |
|---|---|---|
| Decision-support tool: NASA EO + local soil info + crop characteristics + farmer priorities | NASA POWER (official-condition shares per past year; model features), P-02 crop values, one tap-button priority question; no local soil values (SoilGrids producer advises against local use, R-K13) | built |
| "Compare at least three rotation strategies, including the existing rotation" | four P-02 structures + farmers' usual structure CC5, plus the P-03 control | built (FR-06) |
| For each strategy: why suggested, evidence, benefits, information gaps, risks needing local review | per-strategy explanation block (FR-17) | built |
| Highlight times when fields are typically bare | bare periods shaded on the timeline (FR-18) | built |
| Seasons when current crops appear more vulnerable | regional rice-season history per past year; official-condition shares per crop in its trial months; out-of-sample model next to the history only for 2016-2024 and only for a season whose own test passes | built |
| Priorities: water use, forage value, nitrogen-fixing, erosion, organic matter, market suitability | water row of sourced facts; forage: biomass maize is grown as green fodder for cattle and the province requires purchase contracts for it (vietnamnet.vn, R-C13), shown for biomass maize only; land-care checks; erosion not scored (Slaets et al. 2016); market shown as an information gap, not scored | built |
| Explain terms (evapotranspiration, NDVI, water balance) and satellite vs ground data | explain-the-terms section on the method page (UI-UX-SPEC §11b item 3) | built |
| Explain how the model handles uncertainty and where local expertise is needed | the model's 80% range only where G4 passes, trust labels of source facts, "needs local review" list | built |
| Optional: maps, overlays, scenario sliders | bonus: optional 2D map page of the Nghệ An POWER cells by year and rule, then SRTM relief; 3D only on pages outside the farmer routes; no water-stress map or slider | partly built: 3D globe on the observatory page; 3D grid on the science page with a flat 2D map and an optional NASA SRTM terrain layer (built 16 Nov, after the Hanoi version); no separate `/ban-do` page |
| Supportive tool, does not replace farmer judgment | core principle | built |

The Hanoi rules summarize Field Shift as adjusting farming "based on satellite data and climate forecasts". The official
NASA text does not require forecasts; we use past years and explain why in the pitch.

Frost (sương muối) is defined only qualitatively (QĐ 18/2021 Art. 5.19); news reports it in high mountain communes
(Báo Văn Hóa 2025-01-16), not on the target lowland rice land. It is omitted, and this is stated on the method page.

| Judging criterion | How we answer it |
|---|---|
| Impact | Real, local adaptation problem (drought-prone rice land) with a published local evidence base |
| Creativity | A comparison in which every number carries facts about its source, in place of a black-box "optimal rotation" |
| Validity | Leakage-aware ML with honest reference forecasts; every rule sourced; non-comparable evidence not mixed |
| Relevance | NASA POWER climate history labels past years with official hazard conditions and feeds the rice model; the farmer's priority highlights a row |
| Presentation | Timeline + one card per plan; past-year comparison demo |

## 9. Success criteria (for submission)

- Every displayed number traces to a source file and a trust label of source facts.
- ML results for spring and winter rice are reported against the reference forecasts B0 (climatology) and B2
  (persistence) and the no-weather model BNW on rolling-origin test years 2016-2024. Summer-autumn rice is reported
  as history only (G1 fail).
- The hosted app reads only precomputed artifacts and makes no live external data calls during judging. The
  exceptions are the optional Google sign-in and the Claude API calls of the "explain simply" button and the copilot,
  and they are stated (NFR-01).
- The project is submitted by 10:00 ICT Sun 2026-11-15 (Hanoi deadline 11:00) and complies with SRS.md CR-01..CR-13.
- The README discloses all libraries, data sources, versions and AI-assistant use.
- Usability is not measured, because no farmer, officer or wording tester is available. This is stated as a
  limitation on the method page and in the pitch. We set no usability targets, because none would have a source or a
  way to be checked.
