# MIAUDOW — UI/UX audit on 7 provided screenshots

**Audit scope:** seven user-supplied screenshots from 14 November 2026 and `Miaudow Đồng Lúa.html` (1,095 lines). This is an expert design review, **not a formal moderated usability study**.

## Main diagnosis

The current product has a reasonably consistent forest/rice-gold palette and strong source-transparency intention. The failure is compositional: dense text, miniature units, inconsistent image geography, thin information hierarchy and simulated numbers are being presented inside the same polished-looking UI. Scientific content is not progressively disclosed; farmers and extension officers must read like researchers.

| Screen | Current issue | Redesign decision | Acceptance test |
|---|---|---|---|
| Home / first screenshot | Hero occupies a compact panel; 100% metric dominates without measurement definition; sources in microtype | Full-bleed authentic-inspired landscape, one emotional message, one unambiguous farmer CTA; no unverified headline statistics | User identifies primary action in 5 seconds; metric always has definition + source |
| Home / long narrative | Landscape images compete with tiny paragraph blocks; geographic shots mixed (tea, mountain terrace, jars) | Dedicated editorial modules, deliberate big/small typography, only real Nghệ An photography once rights cleared | Hero and each section retain distinctive narrative at 390/1440 px |
| Farmer onboarding | Oversized dark card; a lot of text before interaction; farmer-related options not prominent | Light, warm, single-column choice screens with 48+ px touch targets, photo-assisted options, one task per step | First-time farmer can complete four steps without jargon |
| Officer | Dense 5-column evidence matrix, small type, many competing source seals | Evidence desk with clickable source list + generous detail panel; source/provenance shown on demand | Officer can find author/source/limitations within two taps |
| Science spatial | Tiny pseudo-3D map surrounded by microtype and many numeric badges | Observatory-first full-size spatial stage + documented layers + big legends + controlled 2D fallback | Users distinguish simulated visualization from actual measurements |
| Science model evaluation | Tight charts with insufficient context; users cannot distinguish baseline vs model or metric uncertainty | Research mode with explicit baseline, dataset split, intervals, sample size, no chart without actual results | No benchmark presented without experiment logs |
| Evidence / Copilot | Standard chat bubble, no link between citations and actual visualization; heavy microcopy | Editorial conversational research assistant; voice, citations, source images and progressive details | Claims trace to exact source and response says insufficient evidence when needed |

## Content errors found in original HTML

1. `cellUnits` and `provShare` are deterministic synthetic generation for weather hazard values (around lines 365–381); **not NASA POWER observations**.
2. `modelChart` renders demonstration metrics (around line 936); no verified model eval artifact is included.
3. The front page uses “100% con số có nguồn” but provenance links do not convert synthetically generated values into genuine measurements.
4. Profit figures in `PLANS` represent reported 2020–21 trial plots, not general future profits; full trial data is not present in the artifact.
5. The sentence “cả chuỗi chưa từng được trồng liền trên một ruộng” overstates the paper evidence; use **“Bài báo không nêu rõ cả chuỗi đã được thử trên cùng một thửa ruộng hay chưa.”**
6. The geographic context should explicitly differentiate *vùng đồng bằng và trung du Nghệ An*; not conflating western terraces with rice lowlands in Đô Lương.
7. Photo fallback set uses several landscape types from other regions; a real local documentary photo library must be geolocated and permissioned.
8. Original state is memory-based; if persisting fields via `localStorage` in future, record the exact decision and retention period in DECISION-LOG.
9. Scientific caveats and model-validity badges need to be surfaced before recommendation, not hidden as footnotes.
10. Many text elements appear too small in the supplied screenshots; replace “microcopy everywhere” with clear hierarchy and controlled disclosure.

## Revised product north star

- **Home:** cinematic Nghệ An heritage, editorial composition, purpose-driven scroll narrative.
- **Farmer:** exceptionally calm, familiar Vietnamese, no hidden assumptions and no hard cognitive load.
- **Officer:** evidence atlas, sources linked to each conclusion, no spreadsheet-density default.
- **Science:** interactive real-data observatory once geo layers are loaded; illustrative stages are separately labeled.
- **Evidence / Copilot:** avoid default chatbot look. Teach through comparison, evidence and visual components.

## Copy rules

| Avoid | Use |
|---|---|
| “Lúa xuân có khả năng giảm lợi nhuận 3,6%” without verified study | “Chưa đủ thông tin để kết luận mức chênh lệch lợi nhuận.” |
| “NASA POWER đã đo nhiệt độ ruộng” | “NASA POWER ước tính khí tượng theo ô lưới mô hình.” |
| “Cơ cấu chưa từng được trồng trên cùng một ruộng” | “Bài nghiên cứu chưa nêu rõ điều này.” |
| “Lãi 54 triệu/ha” as a universal claim | “Kết quả trong ô thử của nghiên cứu 2020–2021, không phải lợi nhuận dự kiến trên ruộng bạn.” |
| “Năm sau chắc chắn thiếu nước” | “Dữ liệu các năm trước không phải dự báo năm sau.” |

## Formal testing still required

Conduct 5–8 moderated farmer usability tests in the target communes with actual smartphones, include older low-literacy users, and observe tasks without explanations. Test a separate extension-officer cohort, a science reviewer and accessibility workflows. Do not claim usability acceptance before the studies occur.
