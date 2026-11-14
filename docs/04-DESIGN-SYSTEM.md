# MIAUDOW — Lam Giang Golden Heritage / Design system 2.0

## Brand architecture

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

### Typography

- Display: `Noto Serif` with Vietnamese support verified before production. Scale desktop: 52–119 px depending context, mobile: 35–70 px.
- Primary UI: `Be Vietnam Pro`, weights 400–700. Body default 15 px site-wide, **farmer UI 15–18 px**, 1.65–1.85 line height.
- Data: `DM Mono`, limited to numeric and provenance notes.
- No font binaries included. Hosted type may fall back to Georgia/system fonts without network.

### Spacing and shape

- Grid: 8 px scale (4, 8, 12, 16, 24, 32, 48, 64, 96, 128).
- Max text width: 55–70 characters; big narrative column 370–550 px.
- Responsive gutters: 50 px at wide desktop; 19 px narrow mobile.
- Default rectangular editorial frames 4 px radius; friendly interactive farmer cards 10–15 px; pill buttons 999 px.
- Atypical image silhouette such as top-right 140 px leaf corner reserved for hero editorial imagery, not scattered across ordinary controls.
- Shadows low contrast on paper, more emphasis from typography, color and photography.

### Motion

- 400–1000 ms editorial motion, cubic-bezier `.2,.75,.25,1`.
- Atmospheric hero Ken Burns 22 s max only when motion permitted; no constant aggressive animation.
- Hover: 3–5% image scale, subtle translateY ≤ 7 px.
- Science stage: pointer drag rotates CSS 3D illustration. For **real georeferenced** rendering use MapLibre/deck.gl or Cesium after geometry exists and licences are approved.
- `prefers-reduced-motion` and manual Lite disable motion; Lite deliberately avoids loading heavyweight immersive layers in future.

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
