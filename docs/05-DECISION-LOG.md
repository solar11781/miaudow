# MIAUDOW — decisions and dependency ledger

All visual and scientific compromises must be explicit before merge. Record new changes as a new D-number rather than editing away the reasons.

| ID | Decision | Implementation / follow-up |
|---|---|---|
| D-001 | Cinematic concept art is not a documentary photo | All bundled concept images declared AI-generated and non-geolocated in `ASSET_MANIFEST.json` and on UI caption. Replace with cleared Nghệ An photos before publish. |
| D-002 | No redistributed editorial photos | Real-image Sourcebook has author, license and source URLs; newspaper photos excluded from archive. |
| D-003 | No fabricated climate values | Existing `Math.sin` weather synth data not migrated; climate panel fetches real NASA POWER on demand and shows no numbers when unavailable. |
| D-004 | NASA POWER distinction | `source_type=model_assimilation_gridded`, label never “measured at farm”. |
| D-005 | P02 and P03 not verified | No trial profit displayed as expected farm profit. Data and calendar remain illustrative pending full-text review. |
| D-006 | Rulebook is source of crop text | `api/rules/rotations.yaml` → `scripts/sync_rotations.py` → `web/src/rotations.generated.json`. Risk lines are blocked unless supported by verified page-level source. |
| D-007 | Avoid claim “never grown together on one plot” | Use “paper does not say” if complete article remains ambiguous. |
| D-008 | Privacy | No `localStorage` in this prototype. If added, record retained fields, explicit consent, expiry and data governance before merge. |
| D-009 | 3D current scope | CSS 3D field is manipulable **conceptual geometry**, not a real Nghệ An geo-layer. Needs authorized AOI and data products before map claims. |
| D-010 | Claude connection | Only server-side environment keys; `ANTHROPIC_MODEL` must be explicitly set to an enabled model. No API key shipped. |
| D-011 | Browser voice | Web Speech prototype; device compatibility and Nghệ An dialect accuracy unverified. |
| D-012 | Static checks vs complete build | API tests ran locally. React syntax transpilation tested; full production build/browser E2E blocked by missing npm registry access. No claim of CI green. |
| D-013 | Location | Main geographic study focus: Đô Lương rice land. Other districts including Con Cuông/Thanh Chương are broader culture and geography only. |
| D-014 | Research-first narration | “Lowland and midland Nghệ An” where appropriate; do not replace the study geography with mountain terraces. |
| D-015 | Missing data | No climatological interpolations or silent zero-filling; monthly metrics withheld if incomplete. |
| D-016 | Evidence status | Verified source metadata != retrieved and evaluated source dataset or validated crop recommendation. |

## New runtime packages and licences

Versions in package manifests are **declared / intended**. They have not been installed or build-tested against a live registry in this environment.

| Package | Declared version | License | Purpose |
|---|---|---|---|
| react | ^19.2.0 | MIT | Component/state runtime |
| react-dom | ^19.2.0 | MIT | DOM rendering |
| lucide-react | ^0.468.0 | ISC | Consistent icons |
| vite | ^7.2.0 | MIT | Dev/build system |
| @vitejs/plugin-react | ^5.1.0 | MIT | Vite React transform |
| typescript | ^5.9.0 | Apache-2.0 | Type checking |
| @types/react | ^19.2.0 | MIT | Type declarations |
| @types/react-dom | ^19.2.0 | MIT | Type declarations |
| fastapi | 0.115.12 | MIT | Python API server |
| uvicorn | 0.34.2 | BSD-3-Clause | ASGI server |
| httpx | 0.28.1 | BSD-3-Clause | Async HTTPS calls |
| pydantic | 2.11.4 | MIT | Request/response validation |
| pytest | 8.3.5 | MIT | Tests |

## Offline asset and validation tooling (local only, not web dependencies)

| Package | Used local version | License | Purpose |
|---|---|---|---|
| Pillow | 12.3.0 | HPND | Image crop, grade and export |
| numpy | 2.3.5 | BSD-3-Clause | Efficient color grading |
| PyYAML | 6.0.3 | MIT | Compile audited crop YAML into frontend JSON |
| Playwright | 1.57.0 | Apache-2.0 | Offline static screenshot inspection |

**Release checklist:** confirm current package versions against official registry, review licenses and CVEs, run lockfile install + CI allowlist + dependency scan + build + E2E in connected CI. Deployment remains owned by the team with production credentials and infrastructure.
