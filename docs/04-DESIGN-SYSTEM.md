# MIAUDOW — Lam Giang Golden Heritage / Design system 2.0

## Brand architecture

> Redesign of 15 Nov 2026 (D-043 to D-049): night surfaces for the story, rice-water light (`#F1F3EE`, not cream) for
> the tools, one accent (ripe-rice gold) for the action a person takes, photographs carry the colour. The sections
> below are updated where the redesign changed them.

**Core experience:** Vietnamese rural heritage × editorial luxury × scientific precision. No AI neon, no generic green-tech ornament. The soul is Nghệ An lowland agriculture and Lam River atmosphere; atmospheric images are artistic, sources are scientific.

### Visual principles

- **Hero/long-form:** cinematic image, strong deep-forest gradient, literary serif with impeccable Vietnamese diacritics, one CTA.
- **Farmer:** quiet paper and real-life crop symbols, 16–18 px readable text and large explicit choices; never require interpreting a chart first.
- **Officer:** evidence catalog, one fact per view, drill into document provenance, no full spreadsheet as the entry screen.
- **Science:** dark studio with a large manipulable data surface. When geographic data is absent, do not disguise illustrative 3D geometry as geospatial evidence.
- **Voice:** minimal, clear, human Vietnamese. Narratives can be evocative; recommendations must be plain and falsifiable.

### Primary colors

| Token | HEX | Primary usage |
|---|---|---|
| forest.950 | `#0C2015` | Research stage and premium UI bands |
| forest.800 | `#153526` | Science panel |
| forest.700 | `#244F36` | Elevation accents |
| harvest.500 | `#E7BB55` | Primary CTA, gentle golden light |
| harvest.600 | `#CFA04A` | Secondary contrast |
| paper.100 | `#F3EFE5` | Narrative and farmer surfaces |
| cream.050 | `#FAF8F2` | Reading surface |
| river.mist | `#DFE6DF` | De-emphasized evidence background |
| red.seal | `#AD402B` | Provenance markers only |
| soil.500 | `#B16B4B` | Ground and warning cues |

**Critical**: labels and charts must not rely on color alone. Text contrast for 10–12 px microcopy needs specific AA validation. The decorative research caption font may be <14 px, but never in the farmer primary path.

### Typography (redesign, 15 Nov 2026, D-044)

- Display: **Darker Grotesque** (variable, 700–750), tight (-0.02em), line height 0.94–1.04. Hero 56–132 px, page titles
  48–100 px. Headings rise out of a line mask once per page (GSAP SplitText); the mask is padded so Vietnamese marks
  above and below (ộ, ụ, ữ) are never clipped.
- Text and numbers: **Hanken Grotesk** (variable, 400–650), 18 px body, 17 px floor everywhere (H6), tabular figures for
  numbers. No monospace face, no italic.
- Both OFL-1.1, served by the app with their Vietnamese subsets (D-155).


### Spacing and shape

- Grid: 8 px scale (4, 8, 12, 16, 24, 32, 48, 64, 96, 128).
- Max text width: 55–70 characters; big narrative column 370–550 px.
- Responsive gutters: 50 px at wide desktop; 19 px narrow mobile.
- Default rectangular editorial frames 4 px radius; friendly interactive farmer cards 10–15 px; pill buttons 999 px.
- Atypical image silhouette such as top-right 140 px leaf corner reserved for hero editorial imagery, not scattered across ordinary controls.
- Shadows low contrast on paper, more emphasis from typography, color and photography.

### Motion (redesign, D-043)

- GSAP 3.15.0 in one module (`web/src/motion/cinema.ts`). Easing by character: heavy `expo.out` 1.1–2.6 s for the
  cinema, `power3.inOut` for transitions, under 250 ms for the tools. Nothing bounces.
- One authored moment per page; no fade-up on every block. The CSS holds the final state; GSAP animates from elsewhere.
- The opening photographs change every 7 s with a visible pause button; under reduced motion or "Máy yếu" nothing
  moves and every word is visible (H1, D-155). No video.


### Component semantic rules

- `SourceChip`: active link only for an actual source; never hyperlink fake generated metric to NASA homepage as though it's evidence of its value.
- `MonthChart`: daily NASA POWER aggregation. Month missing any day returns NULL; no visual infill.
- `FarmerChoice`: big text + short explanatory phrase + icon + visible selection.
- `CropPlan`: seasonal representation, explicit literature-verification status; no profitability or risk line without YAML source proof.
- `3D Stage`: illustration status visible at all times, including fullscreen and screenshots.
- `CopilotAnswer`: evidence chip, source name, status and read-aloud option; no fictitious confidence number.

### Visual QA gates

- Desktop 1440×900, mobile 390×844 screenshot review; additional required 320, 768, 1024, 1920.
- Check Vietnamese glyphs, wrapping, chart tabular numerals, dark overlays, focus states, reduced motion, keyboard-only actions and mobile tap area.
- Tested a **static art-direction HTML sample** rendered to screenshots. The full React/Vite app was not built in this workspace due unavailable npm dependency access; run `npm install && npm run build` in a connected environment.
