# One-shot execution prompt — copy entire block into Claude Code

```text
You are leading a world-class Vietnamese agritech experience rebuild of MIAUDOW. Act simultaneously as principal creative director, staff frontend engineer, geospatial data engineer, ML scientist, Vietnamese UX researcher, accessibility engineer, scientific integrity reviewer and QA lead. USE DEEP REASONING. IMPLEMENT WORKING CODE. NO DESIGN SLOP. NO FAKE DATA. NO FALSE COMPLETION CLAIMS.

PROJECT INPUTS:
- Existing React + Vite + TypeScript source in web/.
- FastAPI starter in api/, rules in api/rules/rotations.yaml and facts in api/knowledge/facts.json.
- Original HTML baseline at reference/original-prototype.html.
- UI quality audit docs/01-UI-AUDIT.md and decision ledger docs/05-DECISION-LOG.md.
- Art direction docs/04-DESIGN-SYSTEM.md and curated concept imagery assets/concept-graded/.
- Provenance and real local photo sourcebook assets/references/REAL_NGHE_AN_SOURCEBOOK.csv.
- Four-pillar AI data architecture docs/02-DATA-AND-AI-BLUEPRINT.md.

DESIGN NORTH STAR:
Lam Giang Golden Heritage: the soul of Nghệ An, warm rice harvest light, mist over the Lam River, poetic editorial typography, authentic countryside geometry, exquisitely art-directed scientific views, and utterly simple farmer UX. The visual experience should compete with international flagship editorial/web-product experiences, never with generic SaaS or purple AI aesthetics. Use subtle film grain, natural warm highlights, deeply layered shadows, image-led chapter transitions, cinematic crossfades, scroll-linked storytelling where accessible, tactile micro-interactions and exceptional typography.

MOST CRITICAL CONSTRAINTS:
1. Every screen must be designed, not just Home. Distinct premium experiences for HOME, FARMER, OFFICER, SCIENCE, EVIDENCE and VOICE COPILOT, unified by one visual grammar.
2. FARMER must remain brilliantly simple on cheap Android devices, including real testing on narrow viewports, with minimum input and no jargon. One question, one action, one image-supported decision per step. Keep explicit agricultural limitations.
3. SCIENCE should become a truly immersive interactive 3D geospatial observatory (MapLibre/deck.gl/Cesium only after verifying required geometry and packages) with georeferenced fields, temporal animation, smart 2D fallback, validated legends and accessible source details. Never pass off current CSS-3D as actual mapped observations.
4. OFFICER should be an expert evidence explorer, not an administrative data table. Each point of evidence uses a beautiful visual, source, date, unit, applicability and research caveat.
5. EVIDENCE should offer research retrieval and page-level provenance; a link to a general NASA homepage is not proof of a fabricated number.
6. COPILOT must support Vietnamese-first questions and optional voice. Claude API keys remain server-side. Do not claim Nghệ An dialect accuracy without WER evaluation. No empty AI theater.
7. Four data/AI capabilities must use one canonical data fabric: Climate Intelligence; Evidence-grounded RAG; Crop Decision Support; Vietnamese Voice Copilot. Data quality > number of functions. All metric cards must share the same record contract and source methodology.
8. DO NOT create synthetic time series and label NASA observations. Do not render 2020–21 trial plot profit as future expected earnings; cite trial and location precisely. Do not say a full rotation was 'never grown on one field' when the paper only fails to specify it. Use 'Bài báo không nêu rõ'.
9. Crop risk lines are defined ONLY in api/rules/rotations.yaml and need verified source ID, page, quotation and review state. Generate web/src/rotations.generated.json from YAML with scripts/sync_rotations.py. Never hard-code unverified warning copy.
10. Treat all concept images as generated visual illustrations, NOT documentary photos of Nghệ An. For any real photo: creator + license + direct source or DROP IT. Bring in real Nghệ An CC0/CC BY material only with accurate credits/ShareAlike obligations and proper geographically truthful captions. Newspaper/Pinterest photography without granted license is NOT approved for packaging.
11. Do not introduce localStorage without a new documented D-number, explicit fields, expiration and privacy purpose. For each new runtime dependency update docs/05-DECISION-LOG.md with version, license, reason; coordinate build/CI allow-list with deployment owner.
12. Highest effort but evidence-based: visual artistry must never conceal research limitations.

IMPLEMENTATION ORDER:
A. Audit source and all original screenshots; run npm install/build/typecheck, pytest and baseline visual screenshots. Report any unavailable tools honestly.
B. Refine design system tokens and fully implement the cinematic HOME chapter sequence, responsive typography, identity, image transitions, immersive gallery and refined nav.
C. Refactor FARMER into plain-language, photo-supported mobile journey: land/water situation; historical climate with explicit no-forecast label; priority; trustworthy rotation cards. Add structured metric explanations with source cards, not prose walls.
D. Elevate OFFICER and EVIDENCE with a visual study explorer: result -> definition -> provenance -> caveat -> comparison, including exportable share state if permitted.
E. Build SCIENCE geospatial rendering only with verified source data. With data absent, show a truthful polished empty state; no pseudo-observational heatmaps. Validate NASA POWER in backend, geospatial AOI, CHIRPS v3 rain, Sentinel-2 L2A vegetation and NASA HLS harmonized series, plus NSO rice statistics. Provenance for every number.
F. Build robust data adapters, QC, source snapshots, deterministic aggregation, proper resolution handling, missingness and validation tests. Add per-source ingestion status, metrics, quality flags, timestamps and geographic scale annotations.
G. Expand RAG from metadata fact cards into page-scoped, evaluated full-text retrieval ONLY when document bytes have been obtained legally; citations must point to exact study pages. Keep Claude grounded in retrieved evidence with numeric verifier and abstention.
H. Implement Crop Decision deterministic gate checks and scenario comparisons; hide ranking until agronomist-reviewed ground evidence, cost assumptions and out-of-region validation exist.
I. Integrate Vietnamese voice with graceful browser fallback, explicit transcript confirmation and optional TTS; define ASR benchmarking for dialect/noise before claims.
J. Implement cinematic transitions and immersive 3D where warranted, with graceful Lite Mode, reduced-motion, offline/no-source states and strong Core Web Vitals.
K. Iteratively browse and screenshot at 320/390/768/1024/1440/1920; personally critique each screen and refine. Fix clipping, alignment, visual sameness, text density, color balance, poor legends, tiny font, and unused negative space. Compare before/after screenshots.
L. Verify no unsourced numbers, no broken interactions, no source miscaptioning, no invented statuses. Run full test suite, build, accessibility checks, performance sample, edge cases. Deliver actual screenshot artifacts and tested working source, with unfinished integrations clearly stated.

ACCEPTANCE GATES:
- Homepage feels like a cinematic Nghệ An cultural documentary, not a component library landing page.
- 6 interfaces have a coherent flagship visual system and meaningful interactions.
- Farmer can complete primary tasks with ordinary words, large touch controls and no need to interpret charts.
- Every metric has a defined numerator/denominator, spatial/temporal unit, data source and validity status.
- No synthetic hazard bars, fake confidence or invented model benchmark is mistaken for reality.
- AI never gives a crop recommendation when required field/market/soil/trial evidence is missing.
- Any source photo has an author and license record or is excluded. Generated concepts are explicitly labeled.
- React production build and Python tests succeed in connected environment; if unavailable, report rather than claim.
- Final UI screenshots from multiple breakpoints demonstrate real iteration, not promises.

Your job is to improve the WHOLE repository now. Do not stop at planning. Avoid superficial edits. Ship the strongest truthful result the available data, tooling and permissions allow.
```

Example for a supported Claude Code CLI environment (run from the project root after extracting the ZIP):

```bash
claude -p "$(cat docs/06-CLAUDE-CODE-ONE-SHOT-PROMPT.md)"
```

If your Claude Code environment is interactive rather than one-shot CLI, paste the prompt body without surrounding shell fences.
