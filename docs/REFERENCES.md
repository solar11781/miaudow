# References (master citation list)

The team agreed on 2026-11-11 that every source we use is recorded here when it is first used, so that the
submission can cite it. The Hanoi rules require us to declare every third-party resource with its licence (SRS.md
CR-01..CR-13). Each source has one row, and this file is the list we cite from.

Columns: ID | full citation | URL | accessed | terms / licence | used for | read status
(READ means we read the full text or data ourselves; ABSTRACT means we read the abstract only; SUMMARY means we saw
only a search or secondary summary; NOT READ means the source is known but was not opened. We never rely on NOT READ
sources for numbers.)

## 1. NASA data

| ID | Citation | URL | Accessed | Terms | Used for | Status |
|---|---|---|---|---|---|---|
| R-N01 | NASA Langley Research Center POWER Project, Prediction Of Worldwide Energy Resources, POWER Daily API v2.10.3, community AG (sources in the API header of every cached file: MERRA2, SRB, SYN1DEG, POWER; T2M-only cache: MERRA2) | https://power.larc.nasa.gov/api/temporal/daily/point | 2026-11-10/11 (cache downloads 2026-11-11) | NASA open data; citation requested by POWER | province weather features, water balance inputs (incl. T2MDEW) | READ (data) |
| R-N02 | Friedl, M., Sulla-Menashe, D. (2022) MODIS/Terra+Aqua Land Cover Type Yearly L3 Global 0.05Deg CMG V061 (MCD12C1), NASA EOSDIS Land Processes DAAC, doi:10.5067/MODIS/MCD12C1.061 (release date 2022-08-05, CMR citation record) | https://cmr.earthdata.nasa.gov/search/granules.json?short_name=MCD12C1&version=061 | 2026-11-11 | CC0 (NASA Earthdata data use guidance, R-E24, READ); cite | farmland weights for province weather (one fixed pre-2016 map) | READ (data) |
| R-N03 | Huffman, G.J., Stocker, E.F., Bolvin, D.T., Nelkin, E.J., Tan, J. (2023) GPM IMERG Final Precipitation L3 1 day 0.1 degree x 0.1 degree V07 (GPM_3IMERGDF), GES DISC, doi:10.5067/GPM/IMERGDF/DAY/07 (release date 2023-07-12, CMR citation record) | https://disc.gsfc.nasa.gov/ (OPeNDAP gpm1.gesdisc.eosdis.nasa.gov) | 2026-11-10 | NASA open data | access verified; stretch cross-check only | READ (access) |
| R-N05 | Huffman, G.J., Stocker, E.F., Bolvin, D.T., Nelkin, E.J., Tan, J. (2023) GPM IMERG Final Precipitation L3 1 month 0.1 degree x 0.1 degree V07 (GPM_3IMERGM), GES DISC, doi:10.5067/GPM/IMERG/3B-MONTH/07 (release date 2023-07-12, CMR citation record; year corrected from 2024, checked 2026-11-13) | https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGM.07/ | 2026-11-13 | NASA open data (CC0); cite | satellite rain check on the method page; variable `precipitation` "Merged microwave-infrared-gauge precipitation estimate", units "mm/hr" (file attributes, READ); gauge input GPCC (UCAR dataset description, search summary only) | READ (file attributes) |
| R-N06 | Reichle, R. et al. (2017) Land surface precipitation and hydrology in MERRA-2, GMAO slides, 5th International Conference on Reanalysis, Rome (paper: Reichle et al. 2017, J. Climate 30(5):1643-1664, doi:10.1175/JCLI-D-16-0570.1, NOT READ) | https://ntrs.nasa.gov/api/citations/20170011571/downloads/20170011571.pdf | 2026-11-13 | NASA technical report server | what corrects POWER's rain: "Land surface precipitation corrected to observations-based products except at high latitudes. Separately for each day / 0.5 deg grid cell (CPCU) or pentad / 2.5 deg grid cell (CMAP)"; "a different observational product in Africa" | READ (slides) |
| R-N07 | NASA Common Metadata Repository (CMR), collection metadata (time_start, title) | https://cmr.earthdata.nasa.gov/search/collections.json | 2026-11-13 | NASA public metadata | dates and resolutions of the datasets we do not use (method page list of datasets considered and not used) | READ |
| R-N08 | Weier, J., Herring, D. (2000). Measuring Vegetation (NDVI & EVI). NASA Earth Observatory (updated 2025-11-14) | https://science.nasa.gov/earth/earth-observatory/measuring-vegetation-ndvi-evi (was https://earthobservatory.nasa.gov/features/MeasuringVegetation, 301 redirect) | 2026-11-14 | NASA public web page | NDVI definition on the method page (explain term ndvi): "NDVI is calculated from the visible and near-infrared light reflected by vegetation" | READ |
| R-N09 | Copernicus Climate Data Store, ERA5 hourly data on single levels from 1940 to present | https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels | 2026-11-14 | public dataset page | ERA5 facts in the datasets-not-used list: "ERA5 is the fifth generation ECMWF reanalysis", "Data is available from 1940 onwards", "regular lat-lon grid of 0.25 degrees" | READ |
| R-N10 | GEDI (Global Ecosystem Dynamics Investigation), Mission Overview, University of Maryland | https://gedi.umd.edu/mission/mission-overview/ | 2026-11-14 | public mission page | GEDI facts in the datasets-not-used list: "GEDI makes precise measurements of forest canopy height, canopy vertical structure, and surface elevation." | READ |
| R-N11 | Didan, K. (2021). MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V061 (MOD13Q1), NASA LP DAAC | https://doi.org/10.5067/MODIS/MOD13Q1.061 (resolves to https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13q1-061) | 2026-11-14 | NASA public dataset | NDVI chart on /khoa-hoc: values recomputed from the team's subset files in the number audit | READ (data) |

## 2. Other data

| ID | Citation | URL | Accessed | Terms | Used for | Status |
|---|---|---|---|---|---|---|
| R-D01 | Cục Thống kê (General Statistics Office / NSO Vietnam), PX-Web database E06 Agriculture, Forestry and Fishing, tables E06.13-E06.35 | https://pxweb.nso.gov.vn/pxweb/en/ | 2026-11-10 | copyright Cục Thống kê; cite "Nguồn: trang Thông tin điện tử Cục Thống kê (www.gso.gov.vn)"; raw files not redistributed | yield labels, areas | READ (data) |
| R-D02 | Poggio, L., de Sousa, L.M. et al. (2021). SoilGrids 2.0: producing soil information for the globe with quantified spatial uncertainty. SOIL 7: 217-240 (data: ISRIC SoilGrids 250 m v2.0) | https://rest.isric.org/soilgrids/v2.0/ | 2026-11-10 | CC BY 4.0 (ISRIC SoilGrids page, R-E26, READ); credit ISRIC | considered for the soil information block; block dropped (R-K13), never shown (UI-UX-SPEC test T27) | READ (access) |
| R-D03 | Turek, M.E. et al. (2023). Global mapping of volumetric water retention at 100, 330 and 15 000 cm suction using the WoSIS database. International Soil and Water Conservation Research 11(2): 225-239. doi:10.1016/j.iswcr.2022.08.001 (SoilGrids wv0010 / wv0033 / wv1500) | https://maps.isric.org/mapserv?map=/map/wv0033.map (WCS) | 2026-11-11 | CC BY 4.0 (Earth Engine catalog) | soil water held at 33 and 1500 kPa, considered for the soil information block; block dropped (R-K13), never shown (UI-UX-SPEC test T27) | READ (data, one test); full text READ as R-W04 |
| R-D04 | Runfola, D. et al. (2020). geoBoundaries: A global database of political administrative boundaries. PLoS ONE 15(4): e0231866. Dataset gbOpen VNM ADM1 | https://www.geoboundaries.org/api/current/gbOpen/VNM/ADM1/ | 2026-11-11 | record licence Public Domain (API field `boundaryLicense`, `licenseSource` commons.wikimedia.org); the geoBoundaries site states "provided under the CC BY 4.0 license ... requires an acknowledgement" (R-E28, re-read 2026-11-13); credit geoBoundaries | province shapes (record: boundary year 2008, source "geoBoundaries, Wikipedia") | READ (data, licence field) |
| R-D05 | Climate Hazards Center, UC Santa Barbara. CHIRPS v3.0 (Climate Hazards Center InfraRed Precipitation with Station data), monthly | https://www.chc.ucsb.edu/data/chirps3 | 2026-11-14 | public dataset page | second rain source on /khoa-hoc (number audit); the page says "CHIRPS is fundamentally a pentad and monthly product"; values recomputed from the team's monthly files | READ (data) |
| R-D06 | ESA Copernicus Sentinel-2 Level-2A (MSI), via Element 84 Earth Search v1 (collection sentinel-2-l2a, hosted by AWS Open Data); legal notice: Copernicus Sentinel Data Legal Notice | https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a ; https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice | 2026-11-15 | public dataset (free, full and open access, Regulation (EU) No 377/2014; notice "Contains modified Copernicus Sentinel data 2020-2024") | 6 greenness (NDVI) images of the former Đô Lương district on /dai-quan-sat; 20 m, dates 2020-06..2021-06 and 2023-01..2024-12 with cloud cover < 60% (the team's catalog sentinel2_l2a_do_luong_vi) | READ (collection page, legal notice) |

## 3. Methods and standards

| ID | Citation | URL | Accessed | Terms | Used for | Status |
|---|---|---|---|---|---|---|
| R-M01 | Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998). Crop evapotranspiration: Guidelines for computing crop water requirements. FAO Irrigation and Drainage Paper 56. Rome: FAO | https://www.fao.org/4/x0490e/x0490e00.htm | 2026-11-11 | FAO copyright, cite | ET0, Kc, stage lengths, soil water, bucket, Ks, RHmin from dew point (eq. 63) | READ (ch. 6-8) |
| R-M02 | Brouwer, C., Heibloem, M. (1986). Irrigation Water Management: Irrigation Water Needs. FAO Training Manual No. 3. Rome: FAO | https://www.fao.org/4/s2022e/s2022e00.htm | 2026-11-11 | FAO copyright, cite | paddy rice water items, monthly effective rain | READ (ch. 3-4) |
| R-M03 | Đào Anh Công, Nguyễn Văn Lượng, Lê Hữu Huấn, Phan Thị Như Xuyến, Ngô Sỹ Giai (2022). Tính toán và phân tích chỉ số bốc thoát hơi tiềm năng và chỉ số thỏa mãn nhu cầu nước của lúa và một số cây màu tại huyện Tĩnh Gia và Quan Hóa, tỉnh Thanh Hóa trong thời kỳ 1991-2020. Tạp chí Khí tượng Thủy văn 737: 26-39. doi:10.36335/VNJHM.2022(737).26-39 | https://vjol.info.vn/index.php/TCKHTV/article/download/67642/57186/ | 2026-11-11 | journal copyright, cite | WRSI precedent and Vietnamese WRSI drought classes | READ |
| R-M04 (SUPERSEDED by R-W15) | TCVN 8641:2011 Công trình thủy lợi - Kỹ thuật tưới tiêu nước cho cây lương thực và cây thực phẩm (Bộ KH&CN, QĐ 362/QĐ-BKHCN, 2011) | https://thuvienphapluat.vn/TCVN/Xay-dung/TCVN-8641-2011-Cong-trinh-thuy-loi-Ky-thuat-tuoi-tieu-nuoc-cho-cay-luong-thuc-906394.aspx | 2026-11-11 | national standard | irrigation amounts per crop; Appendix E Kc not used | this URL NOT READ (login); full text READ via the caselaw.vn transcription, R-W15 |
| R-M05 (SUPERSEDED by R-A04) | Satake, T., Yoshida, S. (1978). High temperature-induced sterility in indica rices at flowering. Japanese Journal of Crop Science 47: 6-17 | - | - | - | heat threshold 35 C | NOT READ (cited via a 2023 review) |

## 4. Agronomy papers (PDFs never committed)

| ID | Citation | URL | Accessed | Terms | Used for | Status |
|---|---|---|---|---|---|---|
| R-P01 (P-01) | Phan Thị Thanh, Trịnh Đức Toàn, Trần Duy Việt, Nguyễn Việt Đức (2019). Kết quả xây dựng mô hình thâm canh lạc Xuân đạt năng suất cao trên đất chuyển đổi tại Nghệ An và Hà Tĩnh. Tạp chí Khoa học Công nghệ Nông nghiệp Việt Nam 7(104): 95-99 | https://tapchi.vaas.vn/sites/tapchi.vaas.vn/files/tapchi/2021-05/TC%20so%207-2019-19.pdf | 2026-11-10 | journal copyright, cite | Plan B peanut evidence | READ |
| R-P02 (P-02) | Trịnh Đức Toàn, Phạm Duy Trình, Đào Thị Minh Hiền, Cao Đỗ Mười, Lê Thị Thơm (2023). Kết quả thử nghiệm một số cây trồng trên đất lúa kém hiệu quả, thường xuyên khô hạn tại tỉnh Nghệ An. Tạp chí Khoa học và Công nghệ Nông nghiệp Việt Nam 04(146): 43-51 | https://tapchi.vaas.vn/vi/tap-chi/ket-qua-thu-nghiem-mot-so-cay-trong-tren-dat-lua-kem-hieu-qua-thuong-xuyen-kho-han-tai-tinh (abstract); full text (PDF): https://vjol.info.vn/vaas/vi/article/download/167049/143292/289735 (the landing page https://vjol.info.vn/vaas/vi/article/view/167049 shows another article's details, "Xác định tác nhân gây bệnh xơ đen trên giống mít changai tại Tiền Giang"; the PDF holds P-02 on pp. 43-51; checked 2026-11-13) | 2026-11-10; full text 2026-11-11 | journal copyright, cite; PDF never committed | core source: plans CC1-CC5, money per crop (Table 13 net profit; Tables 4, 8, 12 cost and price), crop dates and varieties (Tables 1, 5, 9), trial facts and limitations | READ (full text, VJOL copy 167049) |
| R-P03 (P-03) | Trịnh Đức Toàn, Phạm Duy Trình, Đào Thị Minh Hiền, Cao Đỗ Mười và cs (2023). Thử nghiệm một số công thức luân canh trên đất lúa kém hiệu quả, có nguy cơ thiếu nước tại tỉnh Nghệ An. Đặc san KH&CN Nghệ An 2/2023 | https://ngheandost.gov.vn/tap-chi-chuyen-san/tap-chi-kh-cn-nghe-an/dac-san-kh-cn-nghe-an-so-2-2023-112.html?download=1&id=0 | 2026-11-11 | journal copyright, cite | Plan D evidence, crop durations | READ (PDF from team) |

## 5. Vietnamese official documents and statistics publications

| ID | Citation | URL | Accessed | Used for | Status |
|---|---|---|---|---|---|
| R-V01 | Nghị quyết 202/2025/QH15 sắp xếp đơn vị hành chính cấp tỉnh | https://luatvietnam.vn/hanh-chinh/nghi-quyet-202-2025-qh15-cua-quoc-hoi-ve-viec-sap-xep-don-vi-hanh-chinh-cap-tinh-402728-d1.html ; Nghệ An portal https://hcc.nghean.gov.vn/tin-tong-hop/quoc-hoi-thong-qua-nghi-quyet-sap-xep-don-vi-hanh-chinh-cap-tinh-2291.html ; Hà Tĩnh portal https://hatinh.gov.vn/vi/bai-viet/quoc-hoi-chinh-thuc-chot-ca-nuoc-con-34-tinh-thanh-pho | 2026-11-11 | province reference table | READ |
| R-V02 | Nghị quyết 15/2008/QH12 (Hà Tây into Hà Nội) | https://luatvietnam.vn/dia-gioi-hanh-chinh/nghi-quyet-15-2008-qh12-dieu-chinh-dia-gioi-hanh-chinh-tp-ha-noi-268858-d1.html | 2026-11-11 | series cleaning | READ |
| R-V03 | Nghị quyết 175/2024/QH15 (thành phố Huế) | https://luatvietnam.vn/co-cau-to-chuc/nghi-quyet-175-2024-qh15-cua-quoc-hoi-ve-viec-thanh-lap-thanh-pho-hue-truc-thuoc-trung-uong-377830-d1.html | 2026-11-11 | province reference table | READ |
| R-V04 | Nghị định 09/2025/NĐ-CP (support for crops damaged by disasters), summary on Nghệ An portal | https://hcc.nghean.gov.vn/tin-tong-hop/quy-dinh-moi-ve-muc-ho-tro-voi-cay-trong-bi-thiet-hai-do-thien-tai-dich-hai-thuc-vat-1973.html | 2026-11-11 | bad-year context (no longer used) | SUPERSEDED by R-G09 (full text READ) |
| R-V05 | NSO, Phụ lục 1 crop calendar (survey annex) | https://datacollection.nso.gov.vn/Data/Sites/1/media/huyvq/files/6_%20Ph%E1%BB%A5%20l%E1%BB%A5c%201_IN.doc | 2026-11-11 | season windows | READ |
| R-V06 | NSO agriculture pages and 2026 spring rice article | https://www.nso.gov.vn/nong-lam-nghiep-va-thuy-san/ ; https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2026/07/thang-loi-vu-lua-dong-xuan-nam-2026-nhin-tu-giai-phap-nang-cao-nang-suat/ | 2026-11-11 | season definitions | READ |
| R-V07 | Nghệ An statistics office monthly reports | https://datafiles.nghean.gov.vn/nan-ubnd/1/quantritintuc/10Nghe-An_01TH-T10-20226380421638059170890475265.pdf ; https://datafiles.nghean.gov.vn/nan-ubnd/2917/quantritintuc20261/NgheAn_01_KTXH_2025.pdf ; https://datafiles.nghean.gov.vn/nan-ubnd/2917/quantritintuc20267/nghean_01th_thang%206%20va%206%20thang%202026.pdf | 2026-11-11 | local calendar, biomass maize | READ |
| R-V08 | Nghệ An production plans and notices | https://datafiles.nghean.gov.vn/nan-ubnd/2938/steeringdocument/03-de_an_to_chuc_san_xuat_vu_x638391835944716082.pdf ; https://datafiles.nghean.gov.vn/nan-ubnd/2938/quantritintuc202512/pkt_tb_cay_lua_vu_xuan_202512120251212051853558_Signed.pdf ; https://datafiles.nghean.gov.vn/nan-ubnd/2929/steeringdocument/thong_bao_to_chuc_san_xuat_vu_20251204082112951_Signed.pdf ; https://datafiles.nghean.gov.vn/nan-ubnd/2933/quantritintuc20266/80.pdf ; https://datafiles.nghean.gov.vn/nan-ubnd/6713/quantritintuc20258/tb_thuc_hien_khsx_vu_dong_nam_20250812045209859_Signed.pdf | 2026-11-11 | local calendar | READ |
| R-V09 | FAO GIEWS country brief Viet Nam | https://www.fao.org/giews/countrybrief/country.jsp?code=VNM&lang=en | 2026-11-11 | maize season split | READ |

## 6. News and context (never used for numbers)

| ID | Citation | URL | Accessed | Status |
|---|---|---|---|---|
| R-C01 | Báo Nghệ An (English print page) on crop conversion | https://baonghean.vn/en/print/10139483.html | 2026-11-11 | READ |
| R-C02 | Nông nghiệp và Môi trường: 5 giải pháp cho vụ hè thu đặc biệt khó khăn ở Nghệ An | https://nongnghiepmoitruong.vn/tri-thuc-nong-dan/5-giai-phap-cho-vu-he-thu-dac-biet-kho-khan-o-nghe-an-d384071.html | 2026-11-11 | READ |
| R-C03 | NASA Space Apps Challenge 2026, Field Shift challenge page (page text pasted by the team) | https://www.spaceappschallenge.org/ | 2026-11-10 | READ (pasted by team) |

## 7. Software and AI tools (licence table for CR-05 to be completed at submission)

| ID | Tool | Licence | Used for |
|---|---|---|---|
| R-T01 | Claude Code (Anthropic), AI coding and research assistant; version 2.1.323 in the cloud session of 2026-11-13 (`claude --version`), model claude-opus-5-5 in that session; versions on the team laptops and in earlier sessions not recorded [OPEN: Claude Code versions on the event laptops are added at the README step] | Anthropic commercial terms | coding, research, documentation (declared per Hanoi rules) |
| R-T03 | ChatGPT in deep research mode (OpenAI); the product shows no version number (team); dates of use: not recorded, the reports existed by 2026-11-11 [OPEN: exact dates of use to be added by the team] | provider terms | wrote the two input research reports (R1 challenge selection, R2 Vietnam region datasets), input reports only |
| R-T02 | Python, numpy, pandas, pytest, scikit-learn, LightGBM, FastAPI, React, Vite, Tailwind | OSI licences (versions recorded at submission) | pipeline and app |
| R-T04 | `ste` Claude Code skill (Johnathan Mo, jmo-skills, commit 6082bf2), https://github.com/23jmo/jmo-skills, accessed 2026-11-12, copied unchanged to .claude/skills/ste | MIT | development tool: makes Claude's explanations plain and precise; not part of the product |
| R-T05 | Playwright MCP 0.0.85 (Microsoft), https://github.com/microsoft/playwright-mcp, accessed 2026-11-12, configured in .mcp.json (headless, isolated, 360x740 viewport per UI-UX-SPEC) | Apache-2.0 (npm registry metadata) | development tool: lets Claude open and check the website at phone size; not part of the product |
| R-T06 | `cognitive-walkthrough` Claude Code skill (mastepanoski/claude-skills, commit ac30238), https://github.com/mastepanoski/claude-skills, accessed 2026-11-12, copied unchanged to .claude/skills | MIT | development tool: expert-method usability review of farmer tasks (not user testing); not part of the product |
| R-T07 | `code-review` Claude Code skill (Matt Pocock, mattpocock/skills, commit 5863806), https://github.com/mattpocock/skills, accessed 2026-11-12, copied to .claude/skills/spec-review, renamed and one line changed (listed in its NOTICE.md) | MIT | development tool: reviews code changes against the coding standards and the spec; not part of the product |
| R-T08 | `unslop` Claude Code skill (Damir Sokolovsky, heydamir/unslop, commit 97daa3e of 2026-11-08), https://github.com/heydamir/unslop, accessed 2026-11-14, copied unchanged to .claude/skills/unslop with its LICENSE and a SOURCE.md | CC BY 4.0 (credit kept in the skill and here) | development tool: audit of signs of an AI-generated look on the finished screens; not part of the product |
| R-T14 | Matt Pocock, mattpocock/skills (commit 5863806): `git-guardrails-claude-code` script, rewritten in Node and changed to the team's branch rules as .claude/hooks/guard.mjs (notice in GUARD-NOTICE.md); `implement` skill, used as the structure of the `task` skill. https://github.com/mattpocock/skills, accessed 2026-11-13 | MIT | development tools: safety hook and task workflow; not part of the product |
| R-T09 | CC Safety Net 2.7.12 (J Liew / kenryu42), Claude Code plugin from marketplace kenryu42/cc-marketplace, https://github.com/kenryu42/cc-safety-net, accessed 2026-11-13, installed at user scope on each laptop | MIT | development tool: blocks destructive commands and secret-file access; not part of the product |
| R-T10 | GitHub CLI `gh` 2.103.3 (GitHub), https://github.com/cli/cli, accessed 2026-11-13, installed with Scoop | MIT | development tool: opens pull requests and lists them; not part of the product |
| R-T11 | Code-quality and security tools for CI, exact versions: ruff 0.17.4 (Astral, https://github.com/astral-sh/ruff), pip-audit 2.10.1 (PyPA, https://github.com/pypa/pip-audit), gitleaks 8.30.1 (https://github.com/gitleaks/gitleaks), eslint 10.14.0, @eslint/js 10.0.1, typescript-eslint 8.72.2, prettier 3.10.1 (npm registry), npm audit (part of npm); GitHub Actions with actions/checkout@v4, setup-python@v5, setup-node@v4, cache@v4. Accessed 2026-11-13 | ruff, gitleaks, eslint, @eslint/js, typescript-eslint, prettier: MIT; pip-audit: Apache-2.0; GitHub Actions: GitHub terms | development and CI only (lint, format, secret scan, dependency audit); never shipped |
| R-T12 | MCP connectors, accessed 2026-11-13: Chrome DevTools MCP 1.13.0 (Google, https://github.com/ChromeDevTools/chrome-devtools-mcp, Apache-2.0); Context7 hosted MCP (Upstash, https://mcp.context7.com/mcp; server package @upstash/context7-mcp 4.7.0 MIT; hosted service under Upstash terms); Railway remote MCP (https://mcp.railway.com, Railway terms) | see each | development tools: slow-network and Lighthouse checks, version-specific library docs, deployment and logs; not part of the product |
| R-T13 | LightGBM 4.7.0 (Microsoft), https://github.com/microsoft/LightGBM, accessed 2026-11-14 (pip, requirements-dev.lock) | MIT | secondary model M2; pipeline only, not shipped |


## 8. Evidence audit sources (2026-11-11)

The sources in this section were accessed on 2026-11-11 unless a row gives another date. The status values are
defined at the top of this file.

| ID | Citation | URL / DOI | Used for | Status |
|---|---|---|---|---|
| R-A01 | Quyết định 18/2021/QĐ-TTg quy định về dự báo, cảnh báo, truyền tin thiên tai và cấp độ rủi ro thiên tai | https://vupc.mae.gov.vn/Data/files/18_2021_QD-TTg.doc | official heat, heavy rain, drought, rét hại definitions | READ |
| R-A02 | Thông tư 25/2022/TT-BTNMT (rét đậm definition, Art. 3.6) | https://caselaw.vn (copy) | cold definition | READ |
| R-A03 | UBND tỉnh Nghệ An, Chỉ thị 53/CT-UBND (2025-12-15) sản xuất vụ Xuân 2026 | https://datafiles.nghean.gov.vn/nan-ubnd/1/steeringdocument/ct_san_xuat_vu_xuan_2026_2025120251215051852397_Signed.pdf | 15 C sowing rule | READ |
| R-A04 | Satake, T., Yoshida, S. (1978) Jpn J Crop Sci 47(1):6-17 (replaces R-M05) | https://www.jstage.jst.go.jp/article/jcs1927/47/1/47_1_6/_article/-char/en | heat sterility at anthesis | ABSTRACT |
| R-A05 | Jagadish, S.V.K., Craufurd, P.Q., Wheeler, T.R. (2007) High temperature stress and spikelet fertility in rice. J Exp Bot 58(7):1627-1635 | doi:10.1093/jxb/erm003 | heat threshold | ABSTRACT |
| R-A06 | Lyu, X., Zhou, G., Zhou, M., Zhou, L., Ji, Y. (2019) J Meteor Res 33(2):363-374 | doi:10.1007/s13351-019-8105-2 ; https://html.rhhz.net/qxxb_en/html/20190214.htm | gridded Tmax >= 35 C at heading-flowering | READ |
| R-A07 | Shi, P. et al. (2015) Post-heading heat stress in rice of South China during 1981-2010. PLoS ONE 10:e0130642 | PMC4482448 | 35 C threshold selection | READ |
| R-A08 | Zhang, S., Tao, F., Zhang, Z. (2016) Field Crops Res 189:43-50 | doi:10.1016/j.fcr.2016.02.008 | heat degree days > 35 C | ABSTRACT |
| R-A25 | Bheemanahalli et al. (2016), as named in an earlier team decision on weather features for a heat threshold of about 33 C (full citation not recorded) | - | heat threshold context | NOT READ |
| R-A09 | ETCCDI, definitions of the 27 core indices | https://etccdi.pacificclimate.org/list_27_indices.shtml | R20mm, Rx5day, CDD | READ |
| R-A10 | Zhang, X. et al. (2011) Indices for monitoring changes in extremes based on daily temperature and precipitation data. WIREs Clim Change 2(6):851-870 | doi:10.1002/wcc.147 | relative thresholds; gridding dampens extremes | ABSTRACT |
| R-A11 | Zhao, W. et al. (2022) IJERPH 19:4437 (extreme precipitation and rice) | - | heavy rain vs rice | ABSTRACT |
| R-A12 | Huang, J. et al. (2017) Int J Biometeorol 61:1863 | - | heavy rain vs rice (Jiangsu) | ABSTRACT |
| R-A13 | WMO (2012) Standardized Precipitation Index User Guide, WMO-No. 1090 (Svoboda, Hayes, Wood) | https://www.droughtmanagement.info/literature/WMO_standardized_precipitation_index_user_guide_en_2012.pdf | drought categories | READ |
| R-A14 | WMO (2011) Guide to Climatological Practices, WMO-No. 100, 2011 edition (OLDER EDITION: a 2018 edition exists, French edition seen 2026-11-13: "Édition 2018", ISBN 978-92-63-20100-3, https://dgm-meteo.github.io/wmo-clino/Docs/WMO2018_100_fr_Guide%20des%20pratiques%20climatologiques.pdf; 2018 edition NOT READ) | https://www.uncclearn.org/wp-content/uploads/library/wmo40.pdf | categories, quintiles | READ |
| R-A15 | WMO, climatological standard normals (community page) and news "Updated 30-year reference period" | https://community.wmo.int/node/36682 ; https://wmo.int/media/news/updated-30-year-reference-period-reflects-changing-climate | 1991-2020 normal | SUMMARY / READ |
| R-A16 | MONRE (2016) Climate Change and Sea Level Rise Scenarios for Viet Nam (Tran Thuc et al.), 2016 edition (OLDER EDITION: updated scenarios approved by QĐ 1430/QĐ-BTNMT of 21/7/2021, https://imh.ac.vn/files/doc/1430-qd-btnmt-DA-CapNhatKichBanBDKH.pdf, and a National Climate Assessment by QĐ 1436/QĐ-BTNMT of 22/7/2021, https://imh.ac.vn/files/doc/1436-qd-btnmt-DA-DanhGiaKhiHauQuocGia.pdf; decision first pages seen 2026-11-13, reports NOT READ) | https://data.opendevelopmentmekong.net/dataset/ff33a524-a90c-4d1b-94b6-193ad878cf1d/resource/a354c3e0-3cfe-4d07-ad03-d24713792d37/download/climate-change-and-sea-level-rise-scenarios-for-vietnam-2016.pdf | observed trends | READ |
| R-A17 | IPCC AR6 WGI Regional Fact Sheet Asia | https://www.ipcc.ch/report/ar6/wg1/downloads/factsheets/IPCC_AR6_WGI_Regional_Fact_Sheet_Asia.pdf | trends | READ |
| R-A18 | Báo Văn Hóa (2025-01-16) on băng giá in Kỳ Sơn / Quế Phong | - | frost context (news) | READ (news) |
| R-W01 | Steduto, P., Hsiao, T.C., Fereres, E., Raes, D. (2012) Crop yield response to water. FAO Irrigation and Drainage Paper 66 (ch. 2, ch. 3, rice and maize sections) | https://www.fao.org/4/i2800e/i2800e02.pdf ; https://www.fao.org/4/i2800e/i2800e04.pdf ; https://www.fao.org/4/i2800e/i2800e07.pdf | Ky by stage; rice water inputs; AquaCrop bunds | READ |
| R-W02 | IRRI Rice Today (2009) How much water does rice use? | https://ricetoday.irri.org/?p=3063 ; https://ricetoday.irri.org/?p=3037 | rice water input vs ET | READ |
| R-W03 | USDA NRCS (2021) National Soil Survey Handbook, Title 430, Part 618 | https://sitesreservoirproject.riptideweb.com/references/REF21/_Ch12_GeologySoils/USDA_2021_NSSH_Part_618.pdf (copy) | 33 kPa field capacity, 1500 kPa wilting point | READ |
| R-W04 | Turek et al. (2023) full text (see R-D03) | https://edepot.wur.nl/577887 | soil water map accuracy | READ |
| R-W05 | USGS FEWS NET, CHIRPS croplands WRSI documentation | https://earlywarning.usgs.gov/fews/product/890 | WRSI method | READ |
| R-W06 | Senay, G.B., Verdin, J. (2002) ISPRS / Pecora 15 | https://www.isprs.org/proceedings/XXXIV/part1/paper/00026.pdf | WRSI method | READ |
| R-W07 | FEWS NET GeoWRSI help, chapter 11 | https://help.fews.net/en/tools/v3/chapter-11-geowrsi | WRSI definition | READ |
| R-W08 | ORYZA v3 paddy file format documentation | https://sites.google.com/view/oryzamodel/scientific-documentation/paddy-file-format | paddy bucket parameters | READ |
| R-W09 | FAO CROPWAT 8.0 example manual | https://www.waterwiki.net/ext_iframe/nr/water/docs/CROPWAT8.0Example.pdf | rice inputs, effective rain 80% | READ |
| R-W10 | Dastane, N.G. (1974) Effective rainfall in irrigated agriculture. FAO Irrigation and Drainage Paper 25 | https://www.fao.org/4/x5560e/x5560e04.htm | paddy effective rain | READ |
| R-W11 | Rienzner et al. (2025) EGU25-11331 | https://meetingorganizer.copernicus.org/EGU25/EGU25-11331.html | fixed percolation in models | ABSTRACT |
| R-W12 | NASA POWER parameter dictionary (GWETROOT) and GMAO MERRA-2 FAQ | https://power.larc.nasa.gov/api/system/manager/parameters/GWETROOT ; https://gmao.gsfc.nasa.gov/gmao-products/merra-2/faq_merra-2/ | variable definitions | READ |
| R-W13 | Nguyễn Quang Phi (2025) peanut water requirement, Ninh Bình, FAO-56 dual Kc. Tạp chí KH&CN Thủy lợi 92 | https://vawr.org.vn/Upload/BaibaoKH/nguyen-quang-phi_92_2025.pdf | Vietnamese peanut stages and Kcb | READ |
| R-W14 | pyCropWat documentation (USDA-SCS effective rain, citing FAO-46) | https://montimaj.github.io/pyCropWat | effective rain formula (secondary) | READ (secondary) |
| R-E01 | Tamburini, G. et al. (2020) Sci Adv | doi:10.1126/sciadv.aba1715 | diversification | READ |
| R-E02 | McDaniel, M.D., Tiemann, L.K., Grandy, A.S. (2014) Ecol Appl | doi:10.1890/13-0616.1 | rotation soil C/N | ABSTRACT |
| R-E03 | Bowles, T.M. et al. (2020) One Earth 2(3) | doi:10.1016/j.oneear.2020.02.007 | rotation resilience | ABSTRACT |
| R-E04 | Yao, et al. (2025) Legume-rice rotations increase rice yields and carbon sequestration potential globally. One Earth 8:101170 | doi:10.1016/j.oneear.2024.12.006 | legume before rice | READ |
| R-E05 | Peoples, M.B. et al. (2009) Symbiosis 48:1-17 | doi:10.1007/BF03179980 | legume N balance | ABSTRACT |
| R-E06 | Witcombe, A.A., Tiemann, L.K. (2022) Front Sustain Food Syst 5:691786 | doi:10.3389/fsufs.2021.691786 | groundnut residue N | READ |
| R-E07 | Toomsan, B. et al. (2000) Neth J Agric Sci 48(1) | https://library.wur.nl/ojs/index.php/njas/article/view/452 | pre-rice legumes N | ABSTRACT |
| R-E08 | Slaets, J.I.F. et al. (2016) Biogeosciences 13:3267 | doi:10.5194/bg-13-3267-2016 | paddy sediment sink, NW Vietnam | READ |
| R-E09 | Hou, et al. (2022) Agric Ecosyst Environ | doi:10.1016/j.agee.2021.107774 | green manure vs fallow | ABSTRACT |
| R-E10 | Ladha, J.K. et al. (2003) Field Crops Res 81:159-180 | doi:10.1016/S0378-4290(02)00219-8 | rice-wheat yield trends | ABSTRACT |
| R-E11 | FAO (2011) Save and Grow, ch. 3 | https://www.fao.org/4/i2215e/i2215e02.pdf | soil cover | READ |
| R-E12 | USDA NRCS Soil Health on Cropland | https://www.nrcs.usda.gov/conservation-basics/soil/soil-health/soil-health-on-cropland | four soil health principles | READ |
| R-E13 | FAO Conservation Agriculture | https://www.fao.org/conservation-agriculture/en/ | three principles | READ |
| R-E14 | Dodgson, J., Spackman, M., Pearman, A., Phillips, L. (2009) Multi-criteria analysis: a manual. UK DCLG | https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/7612/1132618.pdf | ordering method | READ |
| R-E15 | Krishnan, A.R. (2022) Front Big Data 5:990699 | doi:10.3389/fdata.2022.990699 | normalization sensitivity | ABSTRACT |
| R-E16 | Guyatt, G.H. et al. (2008) GRADE. BMJ 336:924; GRADE Handbook (2013) | PMC2335261 ; https://gdt.gradepro.org/app/handbook/handbook.html | evidence grades | READ |
| R-E17 | Mastrandrea, M.D. et al. (2010) IPCC AR5 Guidance Note on Consistent Treatment of Uncertainties | https://www.ipcc.ch/site/assets/uploads/2017/08/AR5_Uncertainty_Guidance_Note.pdf | confidence language | READ |
| R-E18 | OCEBM Levels of Evidence 2011, introduction v2.1 | https://ru.testingtreatments.org/wp-content/uploads/2017/11/CEBM-Levels-of-Evidence-Introduction-2.1.pdf | evidence levels | READ (intro) |
| R-E19 | Sutherland, W.J. et al. What Works in Conservation, farmland chapter (Open Book Publishers) | https://books.openbookpublishers.com/10.11647/obp.0267/ch4.xhtml | evidence categories | READ |
| R-E20 | Lobell, D.B., Cassman, K.G., Field, C.B. (2009) Annu Rev Environ Resour 34:179-204 | doi:10.1146/annurev.environ.041008.093740 | yield gaps | ABSTRACT |
| R-E21 | van Ittersum, M.K. et al. (2013) Field Crops Res 143:4-17 | doi:10.1016/j.fcr.2012.09.009 | yield gap methods | ABSTRACT |
| R-E22 | Laborte, A.G. et al. (2012) Eur J Agron | doi:10.1016/j.eja.2011.08.005 | SE Asia rice yield gaps | ABSTRACT |
| R-E23 | Stuart, A.M. et al. (2016) Field Crops Res | doi:10.1016/j.fcr.2016.04.039 | rice yield gaps | ABSTRACT |
| R-E24 | NASA Earthdata Data Use Guidance (CC0) | https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance | NASA licence | READ |
| R-E25 | NASA POWER referencing guide | https://power.larc.nasa.gov/docs/referencing/ | POWER citation text | READ |
| R-E26 | ISRIC SoilGrids page (CC BY 4.0) | https://isric.org/explore/soilgrids | SoilGrids licence | READ |
| R-E27 | FAO Statistical Database Terms of Use (CC BY 4.0) | https://www.fao.org/contact-us/terms/db-terms-of-use/en/ | FAOSTAT licence | READ |
| R-E28 | geoBoundaries site licence and VNM ADM1 record | https://www.geoboundaries.org/ | boundaries licence | READ |
| R-E29 | W3C WCAG 2.2 Understanding SC 2.5.8, 2.5.5, 1.4.4, 1.4.3 | https://www.w3.org/WAI/WCAG22/Understanding/ | accessibility | READ |
| R-E30 | Apple Human Interface Guidelines, Accessibility | https://developer.apple.com/design/human-interface-guidelines/accessibility | target and text size | READ |
| R-G01 | UBND xã Nghĩa Đàn, Đề án sản xuất vụ Xuân 2026 (11/12/2025) | https://datafiles.nghean.gov.vn/nan-ubnd/2938/steeringdocument/de_an_sx_vu_xuan_2026_nghia_da20251211025451800_Signed.pdf | spring calendar, peanut sowing | READ |
| R-G02 | UBND xã Hưng Nguyên, Kế hoạch 98/KH-UBND sản xuất vụ Hè 2026 (23/4/2026) | https://datafiles.nghean.gov.vn/nan-ubnd/2936/steeringdocument/ke_hoach_san_xuat_he_20260423020260423030002116_Signed.pdf | summer-autumn practice | READ |
| R-G03 | UBND Nam Đàn, Thông báo 1267/TB-UBND (2/6/2026) (= one file of R-V08) | https://datafiles.nghean.gov.vn/nan-ubnd/2933/quantritintuc20266/80.pdf | transplant deadline | READ |
| R-G04 | UBND xã Hậu Thành, QĐ 298 kế hoạch vụ Đông 2024 (27/8/2024) | https://datafiles.nghean.gov.vn/nan-ubnd/4321/steeringdocument/ke_hoach_san_xuat_vu_dong%202024.pdf | winter crop windows | READ |
| R-G05 | Nghệ An statistics, socio-economic report July 2024 | https://datafiles.nghean.gov.vn/nan-ubnd/2815/quantritintuc20249/BX%20KTXH%20thang%207.2024.pdf | summer maize area | READ |
| R-G06 | Nghị định 112/2024/NĐ-CP hướng dẫn về đất trồng lúa | https://caselaw.vn/van-ban-phap-luat/411897-nghi-dinh-so-112-2024-nd-cp-ngay-11-09-2024-cua-chinh-phu-huong-dan-ve-dat-trong-lua | rice land definitions | READ |
| R-G07 | Nghị định 94/2019/NĐ-CP | https://caselaw.vn/van-ban-phap-luat/327678-nghi-dinh-so-94-2019-nd-cp-ngay-13-12-2019-cua-chinh-phu-huong-dan-luat-trong-trot-ve-giong-cay-trong-va-canh-tac | rice land conversion | READ |
| R-G08 | Nghệ An QĐ 505/QĐ-UBND (2024) conversion plan, news summary | https://hcc.nghean.gov.vn/tin-tong-hop/ban-hanh-ke-hoach-chuyen-doi-co-cau-cay-trong-tren-gan-449-ha-dat-trong-lua-tren-dia-ban-tinh-nam-2024-1083.html | conversion area | READ |
| R-G09 | Nghị định 09/2025/NĐ-CP full text (replaces R-V04 summary) | https://hcc.nghean.gov.vn/tin-noi-bat/toan-van-nghi-dinh-ve-ho-tro-san-xuat-nong-nghiep-de-khoi-phuc-san-xuat-do-thien-tai-dich-hai-thuc-vat-1974.html | disaster support | READ |
| R-G10 | Thông tư liên tịch 43/2015/TTLT-BNNPTNT-BKHĐT (damage statistics) | https://caselaw.vn/van-ban-phap-luat/276855-thong-tu-lien-tich-43-2015-ttlt-bnnptnt-bkhdt-huong-dan-thong-ke-danh-gia-thiet-hai-do-thien-tai-gay-ra-do-bo-truong-bo-nong-nghiep-va-phat-trien-nong-thon-bo-ke-hoach-va-dau-tu-ban-hanh | damage levels | READ |
| R-G11 | Sở NN&PTNT Nghệ An, Báo cáo 714/BC-SNN.KHTC (25/12/2023) and 147/BC-SNN.KHTC (2024) | https://datafiles.nghean.gov.vn/nan-ubnd/2908/quantritintuc202312/3.-BAO-CAO-TONG-KET-KH-NAM-202638394385907361514.doc ; https://datafiles.nghean.gov.vn/nan-ubnd/2908/quantritintuc20244/BC%20147_Ban%20ky638482791074048034.pdf | irrigated rice area | READ |
| R-G12 | QĐ 2783/QĐ-BNNMT (17/7/2026) quy hoạch thủy lợi lưu vực sông Cả | https://datafiles.nghean.gov.vn/nan-ubnd/2920/quantritintuc20267/quyet_dinhphe_duyetqhtl_s_ca__260717112542__17072026141203_signed_20260717154246188.pdf | irrigation target | READ |
| R-G13 | UBND xã Quan Thành, Chỉ thị sản xuất vụ Hè Thu (28/4/2026) | https://datafiles.nghean.gov.vn/nan-ubnd/6645/steeringdocument/chi_thi_san_xuat_vu__20260428020260428043352310_Signed.pdf | water-assured planting rule | READ |
| R-G14 | Mai Trọng Thông, Vùng khí hậu Bắc Trung Bộ (encyclopedia entry, citing Nguyễn Đức Ngữ and Nguyễn Trọng Hiệu 2013) | https://storage-vnportal.vnpt.vn/vass/6475/FileQuanTriTinTuc/235.%20V%C3%99NG%20KH%C3%8D%20H%E1%BA%ACU%20B%E1%BA%AEC%20TRUNG%20B%E1%BB%98.docx | season climate | READ (secondary) |
| R-G15 | Bách Khoa Toàn Thư Việt Nam, Gió phơn | https://bktt.vn/Gi%C3%B3_ph%C6%A1n | gió Lào months | READ (secondary) |
| R-G16 | NSO PX-Web E06.17 metadata; NSO indicator definitions (yield, sown area) | https://pxweb.nso.gov.vn/pxweb/en/ ; https://www.nso.gov.vn/?p=17150 ; https://www.nso.gov.vn/du-lieu-dac-ta/2019/12/htcttkqg-dien-tich-gieo-trong-cay-hang-nam/ | units, definitions | READ |
| R-G17 | Nghị quyết 22/2003/QH11 (English translation) | https://english.luatvietnam.vn/resolution-no-22-2003-qh11-of-november-26-2003-on-division-and-adjustment-of-the-administrative-boundaries-of-a-number-of-provinces-15802-doc1.html | 2004 province splits | READ |
| R-G18 | Nghị định 86/2012/NĐ-CP Annex VI (English translation) | https://english.luatvietnam.vn/decree-no-86-2012-nd-cp-dated-october-19-2012-of-the-government-detailing-and-guiding-the-implementation-of-a-number-of-articles-of-the-law-on-metro-74257-Doc1.html | sào = 499.95 m2 | READ |
| R-G19 | Khuyến nông VN, Nghệ An triển khai đề án sản xuất vụ Hè Thu - Mùa 2026 | https://khuyennongvn.gov.vn/hoat-dong-khuyen-nong/thong-tin-huan-luyen/nghe-an-trien-khai-de-an-san-xuat-trong-trot-vu-he-thu-mua-nam-2026-32024.html | conversion guidance | READ |
| R-S01 | Lu, J., Carbone, G.J., Gao, P. (2017) Detrending crop yield data for spatial visualization of drought impacts. Agric For Meteorol 237-238:196-208 | doi:10.1016/j.agrformet.2017.02.001 | detrending | ABSTRACT |
| R-S02 | Lobell, D.B., Field, C.B. (2007) Global scale climate-crop yield relationships and the impacts of recent warming. Environ Res Lett 2:014002 | doi:10.1088/1748-9326/2/1/014002 | first differences; rice R2 | READ |
| R-S03 | Ray, D.K. et al. (2015) Climate variation explains a third of global crop yield variability. Nat Commun 6:5989 | doi:10.1038/ncomms6989 | expected skill (Vietnam rice) | READ |
| R-S04 | Iizumi, T., Ramankutty, N. (2016) Environ Res Lett 11:034003 | doi:10.1088/1748-9326/11/3/034003 | past-only normal | READ |
| R-S05 | Finger, R. (2010) Revisiting the evaluation of robust regression techniques for crop yield data detrending. Am J Agric Econ 92:205-211 | doi:10.1093/ajae/aap021 | robust trend | ABSTRACT |
| R-S06 | Paudel, D. et al. (2021) Machine learning for large-scale crop yield forecasting. Agric Syst 187:103016 (read as ch. 2 of Paudel's 2023 PhD thesis; ch. 3 = Paudel et al. 2022 Field Crops Res 276:108377, doi:10.1016/j.fcr.2021.108377) | doi:10.1016/j.agsy.2020.103016 ; thesis https://edepot.wur.nl/588095 | leakage, past-only trend | READ |
| R-S07 | Anderson, W.B. et al. (2019) Sci Adv 5:eaaw1976 | doi:10.1126/sciadv.aaw1976 | detrending | READ |
| R-S08 | Li, et al. (2023) npj Clim Atmos Sci | doi:10.1038/s41612-023-00375-6 | percent anomaly; 25th percentile failure | READ |
| R-S09 | Brás, T.A. et al. (2021) Environ Res Lett 16:065012 | doi:10.1088/1748-9326/abf004 | detrending | READ |
| R-S10 | Cottrell, R.S. et al. (2019) Food production shocks across land and sea. Nat Sustain 2:130-137; method via Zhang et al. (2023) arXiv:2303.00919 | doi:10.1038/s41893-018-0210-1 | shock definition | ABSTRACT / SECONDARY |
| R-S11 | Lesk, C., Rowhani, P., Ramankutty, N. (2016) Nature 529:84-87 | doi:10.1038/nature16467 | disaster losses | ABSTRACT |
| R-S12 | Sweet, et al. (2025) EGUsphere egusphere-2025-3006 (preprint), doi:10.5194/egusphere-2025-3006; published as Sweet, L., Müller, C., Jägermeyr, J., Zscheischler, J. (2026) A data-driven method for identifying climate drivers of agricultural yield failure from daily weather data. Geosci Model Dev 19:6687-6735, doi:10.5194/gmd-19-6687-2026 (Crossref, 2026-11-13; published version NOT READ, our notes rest on the preprint discussion) | https://egusphere.copernicus.org/ | 10th percentile failure, past-only | READ (author response) |
| R-S13 | Government of Manipur, PMFBY Kharif 2023 notification | https://agrimanipur.mn.gov.in/wp-content/uploads/2023/07/agrimanipur.gov.in_notification-kharif-2023_compressed.pdf | insurance threshold yield | READ |
| R-S14 | Morales, A., Villalobos, F.J. (2023) Front Plant Sci | doi:10.3389/fpls.2023.1128388 | temporal validation | ABSTRACT |
| R-S15 | Pham, H.T. et al. (2022) Sensors 22:719 | doi:10.3390/s22030719 | Vietnam rice yield model | READ |
| R-S16 | Roberts, D.R. et al. (2017) Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. Ecography 40:913-929 | doi:10.1111/ecog.02881 | block CV | READ |
| R-S17 | Bergmeir, C., Benítez, J.M. (2012) Inf Sci 191:192-213 | doi:10.1016/j.ins.2011.12.028 | time-series CV | ABSTRACT |
| R-S18 | Hyndman, R.J., Athanasopoulos, G. Forecasting: Principles and Practice, 3rd ed., s5.9-5.10 | https://otexts.com/fpp3/tscv.html | rolling origin; skill scores | READ |
| R-S19 | Kallenberg, M., Paudel, D. et al. (2026) CY-Bench. Earth Syst Sci Data 18:3997-4018 (preprint essd-2025-83) | doi:10.5194/essd-18-3997-2026 | benchmark practice | READ |
| R-S20 | WMO/WWRP JWGFVR, Forecast verification: issues, methods and FAQ | https://cawcr.gov.au/projects/verification/verif.html | skill scores, small samples | READ |
| R-S21 | Gneiting, T., Balabdaoui, F., Raftery, A.E. (2007) JRSS-B 69:243-268 | doi:10.1111/j.1467-9868.2007.00587.x | calibration and sharpness | ABSTRACT |
| R-S22 | Künsch, H.R. (1989) The jackknife and the bootstrap for general stationary observations. Ann Stat 17:1217-1241 | doi:10.1214/aos/1176347265 | block bootstrap | ABSTRACT |
| R-S23 | Field, C.A., Welsh, A.H. (2007) Bootstrapping clustered data. JRSS-B 69:369-390 | doi:10.1111/j.1467-9868.2007.00593.x | cluster bootstrap | ABSTRACT |
| R-S24 | Hyndman, R.J., Fan, Y. (1996) Sample quantiles in statistical packages. Am Stat 50:361-365 | https://robjhyndman.com/publications/quantiles/ | quantile type 8 | ABSTRACT |
| R-S25 | NIST/SEMATECH e-Handbook of Statistical Methods, s7.2.6.4 tolerance intervals | https://www.itl.nist.gov/div898/handbook/prc/section2/prc264.htm | min-max coverage | READ |
| R-S26 | Zeileis, A. et al. Testing and dating of structural changes in practice (working paper) | https://eldorado.tu-dortmund.de/bitstream/2003/5229/1/39_02.pdf | break detection | READ |
| R-S27 | Bai, J., Perron, P. (1998) Econometrica 66:47-78; (2003) J Appl Econom 18:1-22 | doi:10.2307/2998540 ; doi:10.1002/jae.659 | break tests | ABSTRACT |
| R-S28 | Grassini, P., Eskridge, K.M., Cassman, K.G. (2013) Distinguishing between yield advances and yield plateaus. Nat Commun 4:2918 | doi:10.1038/ncomms3918 | plateau detection; Vietnam rice | READ |
| R-S29 | FAO SWS faoswsProduction outlier module (code) | https://rdrr.io/github/SWS-Methodology/faoswsProduction/src/modules/production_outlier_official/production_outlier_official.R | +-30% yield flag | READ |
| R-S30 | Wilks, D. S. (1997). Resampling hypothesis tests for autocorrelated fields. Journal of Climate 10(1): 65-82 | doi:10.1175/1520-0442(1997)010<0065:RHTFAF>2.0.CO;2 | year bootstrap keeps spatial correlation (ML-DESIGN.md §2) | ABSTRACT (record via Crossref and OpenAlex 2026-11-12; publisher page 403) |
| R-S31 | Hamill and Juras (2005), as cited by the WMO/WWRP JWGFVR FAQ (R-S20) on pooled, non-homogeneous samples (full citation not recorded) | - | why B0 is per series | NOT READ |
| R-W15 | TCVN 8641:2011 full text (third-party transcription) | https://caselaw.vn/van-ban-phap-luat/252217-tieu-chuan-quoc-gia-tcvn-8641-2011-ve-cong-trinh-thuy-loi-ky-thuat-tuoi-tieu-nuoc-cho-cay-luong-thuc-va-cay-thuc-pham-nam-2011 | Kc tables, rice regime, stress thresholds, sensitive stages | READ |
| R-W16 | TCVN 9168:2012 Hệ thống tưới tiêu - Phương pháp xác định hệ số tưới lúa (third-party transcription) | https://caselaw.vn/van-ban-phap-luat/251545-tieu-chuan-quoc-gia-tcvn-9168-2012-ve-cong-trinh-thuy-loi-he-thong-tuoi-tieu-phuong-phap-xac-dinh-he-so-tuoi-lua-nam-2012 | paddy water balance, 2 mm/day percolation | READ |
| R-W17 | Trần Văn Đạt (VAWR), percolation in flooded rice fields, Red River Delta | https://vawr.org.vn/phuong-phap-xay-dung-cong-thuc-thuc-nghiem-tinh-tham-tren-ruong-lua-trong-giai-doan-ngap-nuoc-o-dong-bang-bac-bo | measured percolation | READ |
| R-W18 | Đoàn Doãn Tuấn, Trần Văn Đạt, Trần Việt Dũng (VAWR), rice water need and irrigation regime, Red River Delta | https://vawr.org.vn/nhu-cau-nuoc-che-do-tuoi-thich-hop-cho-lua-duoc-canh-tac-theo-phuong-phap-truyen-thong-va-cai-tien-o-vung-dong-bang-bac-bo | deep percolation per season | READ |
| R-W19 | Viện KH KTTV&BĐKH (IMH) (2016) Sổ tay hướng dẫn sử dụng (Bắc Trung Bộ agro-climate handbook) | https://imh.ac.vn/files/doc/Sotay_Huong%20dan%20su%20dung.pdf | Ky by stage incl. rice | READ |
| R-W20 | IMH (2023) water needs of crops in 14 northern midland and mountain provinces | https://imh.ac.vn/xac-dinh-cac-chi-so-ve-nhu-cau-nuoc-cho-cay-luong-thuc-cay-an-qua-cay-cong-nghiep-lau-nam-cay-duoc-lieu-va-rau-tren-tren-dia-ban-14-tinh-trung-du-va-mien-nui-phia-bac/ | CROPWAT soil parameters | READ |
| R-W21 | FAO CROPWAT 8.0 software, default crop and soil files and help | https://www.fao.org/fileadmin/user_upload/faowater/Applications/CRW8.ZIP | FAO default parameters | READ |
| R-W22 | Hoàng Thị Thu Hương, Nguyễn Văn Lượng, Lê Hữu Huấn, Ngô Sỹ Giai (2022) Phân tích, đánh giá chỉ số mưa nông nghiệp (ARI), chuẩn hóa lượng mưa (SPI) và lồng ghép thông tin cho 4 cây trồng chính (lúa, ngô, lạc, đậu tương) trong thời kỳ 1991-2020 tại tỉnh Nghệ An. Tạp chí Khí tượng Thủy văn Tập 736 Số 4 (published 2022-04-04) (authors corrected, checked 2026-11-13) | https://vjol.info.vn/TCKHTV/article/view/66588 | Nghệ An precedent | ABSTRACT (landing page 2026-11-13) |
| R-C04 | Báo Nghệ An (2023-05-04) Lạc được mùa tăng giá | https://baonghean.vn/lac-duoc-mua-tang-gia-nong-dan-nghe-an-phan-khoi-10253807.html | practice after peanut | READ |
| R-C05 | Báo Nghệ An (2024-04-17) Lạc tươi được mùa được giá | https://baonghean.vn/lac-tuoi-o-nghe-an-duoc-mua-duoc-gia-10271165.html | peanut then sesame | READ |
| R-C06 | Báo Nghệ An (2014-09-04) Trồng lạc thu đông ở Diễn Châu | https://baonghean.vn/trong-lac-thu-dong-o-dien-chau-loi-ca-doi-duong-10018026.html | upland sequence | READ |
| R-C07 | Báo Nghệ An (2013-10-16) Thu nhập cao nhờ luân canh gối vụ | https://baonghean.vn/thu-nhap-cao-nho-luan-canh-goi-vu-10011053.html | water-short fields practice | READ |
| R-C08 | Báo Nghệ An (2025-05-11) Lạc vụ xuân mất mùa | https://baonghean.vn/lac-vu-xuan-mat-mua-nong-dan-nghe-an-that-thu-10297035.html | peanut risk | READ |
| R-C09 | Báo Nghệ An (2024-06-10) Nghệ An có khoảng 3.500 ha lúa chét | https://baonghean.vn/nghe-an-co-khoang-3-500-ha-lua-chet-10273837.html | ratoon rice practice | READ |
| R-C10 | Báo Nghệ An (2026-05-24) Nông dân Nghệ An chuyển đổi cây trồng thích ứng biến đổi khí hậu | https://baonghean.vn/nong-dan-nghe-an-chuyen-doi-cay-trong-thich-ung-bien-doi-khi-hau-10338095.html | 4,000 ha water-short | READ |
| R-C11 | Báo Nghệ An (2013-08-23) Chọn cây trồng ăn chắc và né lụt | https://baonghean.vn/chon-cay-trong-an-chac-va-ne-lut-10009493.html | winter maize on two-rice land | READ |
| R-C12 | Báo Nghệ An (2021-08-01) sesame income; (2016-09-03) black sesame Thọ Sơn; (2017-12-15) pumpkin on two-rice land | https://baonghean.vn/nong-dan-nghe-an-thu-hang-chuc-trieu-dong-ha-tu-cay-vung-10229056.html ; https://baonghean.vn/vung-den-cay-trong-chong-han-thu-nhap-cao-10111147.html ; https://baonghean.vn/bi-do-dong-tien-vang-cho-thu-nhap-100-trieu-ha-10158621.html | crop practice and prices | READ |
| R-A19 | DesInventar Sendai, Viet Nam national disaster loss database (data from CCFSC) | https://www.desinventar.net/DesInventar/download/DI_export_vnm.zip | flood/storm rice damage 1989-2010 | READ (data); licence unclear |
| R-A20 | VDDMA VN-DANA damage and needs system | https://thiethai.dmptc.gov.vn/ | recorded events (current year only) | READ (public page) |
| R-A21 | EM-DAT terms of use (CRED) | https://doc.emdat.be/docs/legal/terms-of-use/ | licence check | READ |
| R-A22 | NSO PX-Web V14.91 Thiệt hại do thiên tai; indicator definition | https://pxweb.nso.gov.vn/pxweb/ ; https://www.nso.gov.vn/du-lieu-dac-ta/2024/04/htcttk-huyen-so-vu-thien-tai-va-muc-do-thiet-hai/ | national damage totals | READ |
| R-A23 | Yuen, K.W. et al. (2022) NHESS discussion paper | doi:10.5194/nhess-2022-4 | damage data quality in Vietnam | READ |
| R-A24 | Laborte, A.G. et al. (2017) RiceAtlas, a spatial database of global rice calendars and production. Sci Data; dataset | https://doi.org/10.7910/DVN/JE6R2R | rice calendars (no flowering) | READ (metadata); data not downloaded |
| R-C13 | VietNamNet, Trồng ngô sinh khối liên kết, hướng đi mới giúp nông dân làm giàu (quotes Phó Chủ tịch UBND tỉnh Nghệ An) | https://vietnamnet.vn/trong-ngo-sinh-khoi-lien-ket-huong-di-moi-giup-nong-dan-lam-giau-670666.html | biomass maize as cattle fodder, purchase contracts | READ |
| R-N04 | NASA POWER Hourly API (data start 2001-01-01, checked by request) and Daily API header "time_standard": "LST" | https://power.larc.nasa.gov/api/temporal/hourly/point | rain-day window check | READ (API) |
| R-H01 | NASA Space Apps 2026, Hanoi local event page | https://www.spaceappschallenge.org/2026/local-events/hanoi/ | start time, schedule | READ |
| R-H02 | eventstem, Space Apps Vietnam team information page | https://eventstem.com/spaceapps.html | Hanoi schedule | READ |
| R-H03 | SEPA press release 11/11/2026 and programme page | https://sepa.org.vn/nasa-space-apps-ha-noi-2026-khoi-tranh.htm ; https://sepa.org.vn/nasaspaceapp26 | venue, pre-event wording | READ |
| R-H04 | BTC Hà Nội, Thể lệ cuộc thi 01/NASAHN26 (31/10/2026) | linked from R-H01 | local rules | READ |
| R-H05 | Space Apps 2026 home page and participant FAQs | https://www.spaceappschallenge.org/2026/ ; https://www.spaceappschallenge.org/resources/participant-faqs/ | deadlines, AI use, resources date | READ |
| R-H06 | Space Apps legal terms | https://www.spaceappschallenge.org/legal/ | licences | READ (re-read 2026-11-13: original content "freely available without restriction or ... licensed as open source as defined by the Open Source Initiative"; "If you do not specify a specific OSI compliant license, NASA will distribute your original content under an Apache 2.0 license"; third-party materials free and public or OSI-licensed, with licence documentation) |
| R-H07 | Space Apps awards page | https://www.spaceappschallenge.org/awards/ | award descriptions | READ |
| R-H08 | Space Apps 2022 Judging and Awards Guide; 2022 Project Submission Guide | https://spaceapps-prod.s3.amazonaws.com/media/documents/Space_Apps_2022_Judging_and_Awards_Guide.pdf ; https://spaceapps-prod.s3.amazonaws.com/media/documents/Space_Apps_2022_Project_Submission_Guide.pdf | earlier criteria and demo limits | READ; SUPERSEDED by R-H12, R-H15 (2026 guides) |
| R-H09 | SEPA, "Hướng dẫn nộp bài NASA Space Apps Challenge Hà Nội 2026" (official Hanoi organiser page) | https://sepa.org.vn/huong-dan-nop-bai-nasa-space-apps-ha-noi-2026.htm | submission timeline, form fields, demo limits, judging criteria, rules | READ (2026-11-12) |
| R-H10 | NASA, "NASA Announces 2025 International Space Apps Challenge Global Winners" (2025-12-19) | https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-announces-2025-international-space-apps-challenge-global-winners/ | past winners, award-target choice | READ (2026-11-13) |
| R-H11 | NASA, "NASA International Space Apps Challenge Announces 2024 Global Winners" (2025-01-16) | https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-international-space-apps-challenge-announces-2024-global-winners/ | past winners, award-target choice | READ (2026-11-13) |
| R-H12 | NASA Space Apps 2026 Judging & Awards Guide (page dated 2026-11-12) | https://www.spaceappschallenge.org/resources/judging-awards-guide/ | criteria (1-5), eligibility, demo limits, English rule, award descriptions, dates | READ (2026-11-13) |
| R-H13 | NASA Space Apps 2026 Participant FAQs | https://www.spaceappschallenge.org/resources/participant-faqs/ | dates, no work before the hackathon, SI definition and disclosure | READ (2026-11-13) |
| R-H14 | NASA Space Apps 2026 Team Formation Guide | https://www.spaceappschallenge.org/resources/team-formation-guide/ | start "9:00 a.m. local time", "not expected to submit a fully developed project" | READ (2026-11-13) |
| R-H15 | NASA Space Apps 2026 Project Submission Guide | https://www.spaceappschallenge.org/resources/project-submission-guide/ | form fields, demo rules, English, SI rules, web filter classification | READ (2026-11-13) |
| R-H16 | Field Shift challenge page, Resources tab (published 2026-11-13) | https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/?tab=resources | listed datasets; fit with the plan | READ (2026-11-13) |
| R-U01 | Funke, F. (2016) Soc Sci Comput Rev 34(2):244-254 | doi:10.1177/0894439315575477 | avoid sliders | ABSTRACT |
| R-U02 | Couper, M.P. et al. (2006) Soc Sci Comput Rev 24(2):227-245 | doi:10.1177/0894439305281503 | visual analog scales | ABSTRACT |
| R-U03 | Krosnick, J.A., Alwin, D.F. (1988) Public Opinion Quarterly 52(4):526-538 | doi:10.1086/269128 | rating vs ranking | ABSTRACT |
| R-U04 | Jourdain, D., Lairez, J., Affholder, F. (2022) J Multi-Crit Decis Anal 29:402-415 | doi:10.1002/mcda.1785 | Lao rice farmers' goals | ABSTRACT |
| R-U05 | Mitchell, J., Sipaseuth, Fukai, S. (2014) Crop Pasture Sci 65(7):655-666 | doi:10.1071/CP14082 | farmer preference, field position | ABSTRACT |
| R-U06 | Medhi, I. et al. (2011) Designing mobile interfaces for novice and low-literacy users. ACM TOCHI 18(1):2 | doi:10.1145/1959022.1959024 | low-literacy UI rules | READ |
| R-U07 | Nelson, K., Barnard, Vu (2022) Best practice guidance for inclusive digital tool development for sustainable rice in Vietnam, IRRI/IFAD | https://cgspace.cgiar.org/server/api/core/bitstreams/8ed78886-03a7-43d7-a2bb-733b38e3e3c5/content | Vietnam farmer digital use | READ (licence not checked) |
| R-U08 | Barnard, et al. (2023) Use of digital tools in sustainable rice production in the Mekong Delta, IRRI | https://cgspace.cgiar.org/server/api/core/bitstreams/bb3e2929-7b7a-4e9a-87a5-c2b825e04f5d/content | app use rates | READ |
| R-U09 | NSO/UNICEF MICS 2020-2021 ICT brief | https://www.nso.gov.vn/wp-content/uploads/2021/12/SDGCW-Mass-media-ICT_VIE.pdf | phone and internet by region | READ |
| R-U10 | NSO, KSMS 2025 press release (3 July 2026) | https://www.nso.gov.vn/wp-content/uploads/2026/07/Thong-cao-bao-chi-ksms2025.pdf | IT skills rural/age | READ |
| R-U11 | Rose, D.C. et al. (2016) Decision support tools for agriculture. Agric Syst 149:165-174 | doi:10.1016/j.agsy.2016.09.009 | adviser trust, visuals | READ |
| R-U12 | Oda, M. et al. (2013) Trop Agric Dev 57(3):86 | doi:10.11248/jsta.57.86 | farmer field zoning | ABSTRACT |
| R-U13 | Gigerenzer, G., Hoffrage, U. (1995) Psychol Rev 102(4):684 | doi:10.1037/0033-295X.102.4.684 | frequency formats | ABSTRACT |
| R-U14 | Galesic, M., Garcia-Retamero, R., Gigerenzer, G. (2009) Health Psychol | doi:10.1037/a0014474 | icon arrays | ABSTRACT |
| R-U15 | Pighin, S. et al. (2011) Med Decis Making | doi:10.1177/0272989X11403490 | 1-in-X format | ABSTRACT |
| R-U16 | van der Bles, A.M. et al. (2020) PNAS; (2019) R Soc Open Sci | doi:10.1073/pnas.1913678117 ; doi:10.1098/rsos.181870 | communicating uncertainty | ABSTRACT |
| R-U17 | Hansen, J.W. et al. (2019) Front Sustain Food Syst; Hansen et al. (2011) Exp Agric | doi:10.3389/fsufs.2019.00021 ; doi:10.1017/S0014479710000876 | climate services for farmers | ABSTRACT |
| R-U18 | Spiegelhalter, D., Pearson, M., Short, I. (2011) Science; Spiegelhalter (2017) Annu Rev Stat Appl | doi:10.1126/science.1191181 ; doi:10.1146/annurev-statistics-010814-020148 | visualising uncertainty | ABSTRACT |
| R-U19 | Dorward, P., Clarkson, G., Stern, R. (2015) PICSA Field Manual, Walker Institute, University of Reading, ISBN 9780704915633 | https://cgspace.cgiar.org/items/4788fe81-7ae4-48f4-b4eb-731616823808 | method structure | READ (licence not checked) |
| R-U20 | Clarkson, G. et al. (2019) Climate Services 14:1-14 | doi:10.1016/j.cliser.2019.02.002 | PICSA outcomes | ABSTRACT |
| R-U21 | WWF Agrifood Systems Toolkit, Local Technical Agroclimatic Committees in Vietnam | https://agrifood-systems-toolkit.panda.org/case-studies/local-technical-agroclimatic-committees-enhance-resilience-of-farmers-in-vietnam | Vietnam climate services | READ |
| R-U22 | W3C Internationalization, "Accept-Language used for locale setting" (accessed 2026-11-13) | https://www.w3.org/International/questions/qa-accept-lang-locales | starting language: "a good starting point for determining the language of the user ... give the user some way to override the assumptions you make" | READ |
| R-U23 | Decree 73/CP land-grading and irrigation classes (vàn, vàn cao, vàn thấp), table seen in a HCMUAF lecture (secondary; full citation and URL not recorded; legal status UNVERIFIED) | not recorded | land-type wording | REMOVED 2026-11-13 (not used; team) |
| R-U24 | PICSA training for CIAT Hanoi project staff, 2020 (slides; author and URL not recorded) | not recorded | PICSA use in Vietnam | REMOVED 2026-11-13 (not used; team) |
| R-G20 | Báo Nghệ An (2024-09-15) Đến giữa tháng 9 Nghệ An đã gieo trồng gần 5.000 ha cây vụ đông | https://baonghean.vn/den-giua-thang-9-nghe-an-da-gieo-trong-gan-5-000-ha-cay-vu-dong-10280408.html | Lưu Sơn practice | READ |
| R-G21 | UBND huyện Đô Lương, land-use plan summary to 2030 | https://storage-vnportal.vnpt.vn/nan-ubnd/2930/quantritintuc/Bao-cao-Tom-tat637777753340438296.pdf | rice land types | READ |
| R-G22 | Báo Nghệ An 2020-05-14, 2020-08-14, 2015-07-16, 2016-10-20 (rice harvest timing, mùa calendar, conversion plan) | https://baonghean.vn/a-10213342.html ; https://baonghean.vn/a-10216650.html ; https://baonghean.vn/a-10022101.html ; https://baonghean.vn/a-10117234.html | calendars, practice | READ |
| R-G23 | Cục Thống kê Nghệ An, socio-economic report October 2025 | https://datafiles.nghean.gov.vn/nan-ubnd/2917/quantritintuc202511/NgheAn_01TH_T10_2025.pdf | mùa rice in mountain districts | READ |
| R-G24 | Dân tộc và Phát triển (2022-11-02) Hướng Hóa paddy rice yields | https://dantocphattrien.vietnamnet.vn/dong-bao-dtts-o-huong-hoa-lam-lua-nuoc-nang-suat-cao-1666060230040.htm | Quảng Trị check | READ |
| R-G25 | Nguyễn Văn Hoạt et al. (2016) Tạp chí KH&CN Thủy lợi 34 (thu đông rice statistics) | https://vawr.org.vn/images/file/Nguyen%20Van%20Hoat.pdf | season classification | READ |
| R-G26 | Tuổi Trẻ (2018-07-06) Nghệ An 23.000 ha lúa khô hạn | https://tuoitre.vn/25-ho-nghe-an-xuong-muc-nuoc-chet-23-000-ha-lua-kho-han-20180706164838405.htm | drought extent 2018 | READ |
| R-G27 | Nghị định 112/2024/NĐ-CP Art. 7-8 (annual conversion plans) | https://hethongphapluat.com/nghi-dinh-112-2024-nd-cp-huong-dan-ve-dat-trong-lua/dieu-7 | planning horizon | READ |
| R-L01 | Luật Sở hữu trí tuệ, consolidated 155/VBHN-VPQH (2025), Art. 15, 25 | https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/9/155-vbhn-vpqh.pdf | data not copyrighted; quotation | READ |
| R-L02 | Nghị định 17/2023/NĐ-CP, consolidated 6154/2026/VBHN-BVHTTDL, Art. 28 | https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/9/6154-vbhn-bvhttdl.signed.pdf | quotation conditions | READ |
| R-L03 | Luật Tiêu chuẩn và Quy chuẩn kỹ thuật 68/2006/QH11 Art. 21; TT 11/2021/TT-BKHCN Art. 9 | https://caselaw.vn | TCVN publishing right | READ |
| R-L04 | Luật Khí tượng thủy văn 90/2015/QH13 Art. 3 | https://sotuphap.daklak.gov.vn/images/DeCuongVanBan/201612515502590.Luat%20Khi%20tuong%20thuy%20van.doc | climate normal definition | READ |
| R-L05 | Quyết định 44/2014/QĐ-TTg (replaced by QĐ 18/2021) | https://caselaw.vn/van-ban-phap-luat/162623-quyet-dinh-so-44-2014-qd-ttg-ngay-15-08-2014-cua-thu-tuong-chinh-phu-huong-dan-ve-cap-do-rui-ro-thien-tai | drought wording history | READ |
| R-L06 | NCHMF national drought bulletin 2024-05-31 | https://kttv.gov.vn//upload/thuyvan2/2024/5/31/dbqg_hhan_20240531_1500.pdf | drought practice | READ |
| R-L07 | Doãn Đoàn Tuấn et al. (2014) Tạp chí Các Khoa học về Trái đất 36(2) | https://vjs.ac.vn/index.php/jse/article/download/4497/pdf/16056 | drought month criteria | READ |
| R-L08 | Statistics Sweden (2013) PX file format specification | https://www.scb.se/globalassets/vara-tjanster/px-programmen/PX-file_format_specification_2013.pdf | PX metadata meaning | READ |
| R-L09 | NSO indicator definitions: yield of main crops; production of main crops | https://www.nso.gov.vn/du-lieu-dac-ta/2019/12/htcttkqg-nang-suat-mot-so-loai-cay-trong-chu-yeu/ ; https://www.nso.gov.vn/du-lieu-dac-ta/2019/12/htcttkqg-san-luong-mot-so-loai-cay-trong-chu-yeu/ | sown-area yield | READ |
| R-L10 | Nghị quyết 22/2003/QH11 (caselaw) and news on provinces operating from 1/1/2004 | https://caselaw.vn/van-ban-phap-luat/136590-nghi-quyet-so-22-2003-qh11-ngay-26-11-2003 ; https://baolaichau.vn/chinh-tri/lai-chau-vung-buoc-vao-ky-nguyen-vuon-minh-cua-dan-toc-1109101 ; https://vov.vn/xa-hoi/dac-nong-5-nam-mot-guong-mat-moi-102036.vov | 2004 splits | READ |
| R-M10 | Varma, S., Simon, R. (2006) Bias in error estimation when using cross-validation for model selection. BMC Bioinformatics 7:91 | doi:10.1186/1471-2105-7-91 | nested tuning | READ |
| R-M11 | Cerqueira, V., Torgo, L., Mozetič, I. (2020) Evaluating time series forecasting models. Mach Learn 109:1997-2028 | doi:10.1007/s10994-020-05910-7 | temporal validation | READ (arXiv version) |
| R-M12 | Meroni, M. et al. (2021) Yield forecasting with machine learning and small data. Agric For Meteorol 308-309:108555 | doi:10.1016/j.agrformet.2021.108555 | nested tuning grids | READ (arXiv) |
| R-M13 | Probst, P., Wright, M.N., Boulesteix, A.-L. (2019) Hyperparameters and tuning strategies for random forest. WIREs DMKD 9:e1301 | doi:10.1002/widm.1301 | RF defaults | ABSTRACT |
| R-M14 | LightGBM documentation, Parameters and Parameters Tuning | https://lightgbm.readthedocs.io/en/latest/Parameters-Tuning.html | tuning parameters | READ |
| R-M15 | XGBoost monotonic constraints tutorial; scikit-learn user guide (monotonic constraints) | https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html | when to constrain | READ |
| R-M16 | Li, Y. et al. (2019) Excessive rainfall leads to maize yield loss. Glob Change Biol 25:2325-2337 | doi:10.1111/gcb.14628 | non-monotonic rain effect | ABSTRACT |
| R-M17 | Lei, J. et al. (2018) Distribution-free predictive inference for regression. JASA 113:1094-1111 | doi:10.1080/01621459.2017.1307116 | split conformal | READ (arXiv) |
| R-M18 | Angelopoulos, A.N., Bates, S. (2023) Conformal prediction: a gentle introduction. Found Trends ML 16(4) | arXiv:2107.07511 | conformal practice | READ |
| R-M19 | Barber, R.F. et al. (2023) Conformal prediction beyond exchangeability. Ann Stat 51(2):816-845; Gibbs and Candès (2021) NeurIPS; Romano et al. (2019) NeurIPS; Meinshausen (2006) JMLR 7:983 | arXiv:2202.13415 ; arXiv:2106.00170 ; arXiv:1905.03222 | interval alternatives | READ / READ / ABSTRACT / ABSTRACT |
| R-M20 | Schauberger, B., Jägermeyr, J., Gornott, C. (2020) A systematic review of local to regional yield forecasting approaches. Eur J Agron | doi:10.1016/j.eja.2020.126153 ; open copy https://publications.pik-potsdam.de/pubman/item/item_24342 | metrics (R2 has no formula there) | READ (open copy, 2026-11-12) |
| R-M21 | Hesterberg, T.C. (2015) What teachers should know about the bootstrap. Am Stat 69(4):371-386 | doi:10.1080/00031305.2015.1089789 | resamples, expanded percentile | READ (arXiv) |
| R-M22 | Lobell, D.B., Di Tommaso, S. (2025) PNAS; Jägermeyr, J., Frieler, K. (2018) Sci Adv 4:eaat4517; Chakravarty (2025) arXiv:2510.07350 | doi:10.1073/pnas.2502789122 | window sensitivity; regional blocks | READ / ABSTRACT / ABSTRACT |
| R-M23 | Roversi, G. et al. (2024) The extreme rainfall events of the 2020 typhoon season in Vietnam as seen by seven different precipitation products. Remote Sensing 16(5):805 (CC BY 4.0; accessed 2026-11-13) | https://www.mdpi.com/2072-4292/16/5/805 | rain-check statistic: Table 5 defines the Pearson correlation coefficient CC = cov(o,e)/(sd_o sd_e) among the continuous indices used against Vietnamese gauges | READ (section 3.3, Table 5) |
| R-M24 | Mitchell, M. et al. (2019) Model Cards for Model Reporting. Proceedings of the Conference on Fairness, Accountability, and Transparency, pp. 220-229, doi:10.1145/3287560.3287596 (Crossref checked 2026-11-13) | https://doi.org/10.1145/3287560.3287596 | section structure of the model card (ML-DESIGN.md §10b) | PARTLY READ: only the §4 section list (the nine section headings and the summary list of their contents) checked in the arXiv version 1810.03993v2 (https://arxiv.org/abs/1810.03993, HTML, 2026-11-13); the rest not read |
| R-W23 | Üzen, N., Çetin, O., Yolcu, R. (2018) Turk J Agric For 42(4) (silage maize ETc) | https://journals.tubitak.gov.tr/agriculture/vol42/iss4/5 | biomass maize check (not used) | ABSTRACT |
| R-L11 | QCVN 84:2024/BTNMT; QĐ 02/QĐ-TWPCTT 2020 (drought wording) | https://caselaw.vn | drought counting | READ |

## 9. Legal and disclosure sources (2026-11-11; research input, not legal advice)

The sources in this section were accessed on 2026-11-11. Unless a row gives another site, we read the Vietnamese law
texts on hethongphapluat.com, which is a private mirror and not the official gazette.

| id | citation | URL | purpose | status |
|---|---|---|---|---|
| R-J01 | Nghị định 147/2024/NĐ-CP, Art. 3, 24 (internet services and online information) | https://hethongphapluat.com/nghi-dinh-147-2024-nd-cp-quan-ly-cung-cap-su-dung-dich-vu-internet-va-thong-tin-tren-mang/dieu-24 | website licence exemption, owner/contact display, 24-hour takedown | READ |
| R-J02 | Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15 (effective 01/01/2026) | https://hethongphapluat.com/luat-bao-ve-du-lieu-ca-nhan-2025/dieu-38 | personal data duties | READ (selected articles) |
| R-J03 | Nghị định 356/2025/NĐ-CP (guides the PDP Law) | https://hethongphapluat.com/nghi-dinh-356-2025-nd-cp-huong-dan-luat-bao-ve-du-lieu-ca-nhan/dieu-3 | definitions incl. behaviour tracking | READ (selected articles) |
| R-J04 | Luật An ninh mạng 116/2025/QH15 (from 01/07/2026) | https://hethongphapluat.com/luat-an-ninh-mang-2025/dieu-44 | content rules; business-only duties | READ (selected articles) |
| R-J05 | Nghị định 333/2026/NĐ-CP, EY legal alert (secondary) | https://www.ey.com/en_vn/technical/tax/tax-and-law-updates/legal-alert-decree-no-333-2026-nd-cp-providing-detailed-guidance-on-a-number-of-articles-of-the-law-on-cybersecurity | cybersecurity guidance | SNIPPET (summary only) |
| R-J06 | Nghị định 83/2018/NĐ-CP on agricultural extension, Art. 4 | https://hethongphapluat.com/nghi-dinh-83-2018-nd-cp-ve-khuyen-nong/dieu-4 | who may give extension information | READ; SUPERSEDED by R-J07 (replaced from 20/08/2026, R-J07 Art. 24.1) |
| R-J07 | Nghị định 268/2026/NĐ-CP về khuyến nông (01/07/2026), Art. 1, 2.3, 3.6, 11, 24.1 | https://hethongphapluat.com/nghi-dinh-268-2026-nd-cp-ve-khuyen-nong.html (earlier listing: https://thuviennhadat.vn/van-ban-phap-luat-viet-nam/nghi-dinh-268-2026-nd-cp-khuyen-nong-712973.html) | replaces R-J06: Art. 24.1 "có hiệu lực thi hành từ ngày 20 tháng 8 năm 2026 và thay thế Nghị định số 83/2018/NĐ-CP"; who takes part in extension (Art. 2.3, 3.6, 11) | READ (2026-11-13, articles listed) |
| R-J08 | Bộ luật Dân sự 2015, Art. 584 | https://hethongphapluat.com/bo-luat-dan-su-2015/dieu-584 | damage liability (why disclaimers) | READ |
| R-J09 | Luật Bảo vệ quyền lợi người tiêu dùng 19/2023, Art. 3 | https://hethongphapluat.com/luat-bao-ve-quyen-loi-nguoi-tieu-dung-2023/dieu-3 | scope (profit-making businesses) | READ |
| R-J10 | Luật Thống kê 2015, Art. 58 | https://hethongphapluat.com/luat-thong-ke-2015/dieu-58 | NSO source credit | READ |
| R-J11 | Luật Sở hữu trí tuệ, consolidated text 155/VBHN-VPQH (2025), Art. 15, 25 | https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/9/155-vbhn-vpqh.pdf | data not protected; quotation with source | READ (selected articles) |
| R-J12 | Luật Tiêu chuẩn và Quy chuẩn kỹ thuật 2006, Art. 21 | https://hethongphapluat.com/luat-tieu-chuan-va-quy-chuan-ky-thuat-2006/dieu-21 | TCVN publishing right (values only) | READ |
| R-J13 | NSO website footer (source credit wording) | https://www.nso.gov.vn/ | "Ghi rõ nguồn trang Thông tin điện tử Cục Thống kê (www.gso.gov.vn) khi trích lại thông tin từ địa chỉ này" (re-read 2026-11-12) | READ |
| R-J14 | FAO terms of use; FAO database terms; FAO-56 copyright page | https://www.fao.org/contact-us/terms/en/ ; https://www.fao.org/contact-us/terms/db-terms-of-use/en/ ; https://www.fao.org/4/x0490e/x0490e00.htm | FAO acknowledgement, no logo, no reproduction | READ |
| R-J15 | NASA Earthdata data use guidance; NASA website disclaimer; NASA brand center; 14 CFR 1221.110 | https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance ; https://www.nasa.gov/organizations/disclaimer/ ; https://www.nasa.gov/nasa-brand-center/images-and-media/ | CC0 data, no endorsement, no insignia | READ |
| R-J16 | NASA POWER referencing page | https://power.larc.nasa.gov/docs/referencing/ | POWER credit sentence | READ |
| R-J17 | Space Apps brand page | https://www.spaceappschallenge.org/brand/ | logo use: the page describes logo forms, colours and fonts and offers downloads; it states no permission terms; the linked full brand guidelines NOT READ | READ (page, 2026-11-13, with the SSL.com intermediate certificate) |
| R-J18 | Creative Commons BY 4.0 legal code | https://creativecommons.org/licenses/by/4.0/legalcode.en | SoilGrids attribution terms | READ |
| R-J19 | Apache License 2.0 | https://www.apache.org/licenses/LICENSE-2.0.txt | our code licence, NOTICE rules | READ |
| R-J20 | Railway privacy policy, DPA, logging and regions docs | https://railway.com/legal/privacy ; https://railway.com/legal/dpa ; https://docs.railway.com/reference/logging ; https://docs.railway.com/deployments/regions | host data, IP logs, retention, region | READ |

## 10. Open-item evidence (2026-11-12)

The sources in this section were accessed on 2026-11-12.

| id | citation | URL | purpose | status |
|---|---|---|---|---|
| R-K01 | NCHMF (kttv.gov.vn) national bulletins: heat 08/04, 15/04, 04/06/2026; cold 05/01, 20/01/2026; monthly climate 01/02/2026; past-season report 15/06/2024 | https://kttv.gov.vn (bulletin paths not recorded here) | Nghệ An in Bắc Trung Bộ and Trung Bộ; spells as unbroken date ranges | READ |
| R-K02 | VASS encyclopedia entry "Vùng khí hậu Bắc Trung Bộ" | https://storage-vnportal.vnpt.vn/vass/6475/FileQuanTriTinTuc/235.%20V%C3%99NG%20KH%C3%8D%20H%E1%BA%ACU%20B%E1%BA%AEC%20TRUNG%20B%E1%BB%98.docx | all of Nghệ An in the Bắc Trung Bộ climate zone | READ |
| R-K03 | Báo Hà Tĩnh, interview with the NCHMF director on level-2 heat warnings | https://baohatinh.vn/vi-sao-co-quan-khi-tuong-canh-bao-rui-ro-thien-tai-muc-2-voi-nang-nong-dien-rong-post308930.html | issued levels weigh more than the tables (limitation) | READ |
| R-K04 | Tạp chí Khí tượng Thủy văn (2022), heat and cold spell study | https://vjol.info.vn/index.php/TCKHTV/article/download/74411/63203 | spell = consecutive days; Ttb <= 13 C as rét hại | READ |
| R-K05 | VNU Journal of Science: Earth and Environmental Sciences (2026), spell study | https://js.vnu.edu.vn/EES/article/download/5353/4302 | spell = consecutive days | READ |
| R-K06 | Thông tư 25/2022/TT-BTNMT (forecasting procedure for dangerous hydro-meteorological phenomena) | https://caselaw.vn/van-ban-phap-luat/412893-thong-tu-so-25-2022-tt-btnmt-ngay-30-12-2022-cua-bo-truong-bo-tai-nguyen-va-moi-truong-quy-dinh-ve-quy-trinh-ky-thuat-du-bao-canh-bao-hien-tuong-khi-tuong-thuy-van-nguy-hiem | no definition of "đợt" | READ |
| R-K07 | QCVN 84:2024/BTNMT via Thông tư 46/2024/TT-BTNMT (forecast verification) | https://caselaw.vn/van-ban-phap-luat/412857-thong-tu-so-46-2024-tt-btnmt-ngay-30-12-2024-cua-bo-truong-bo-tai-nguyen-va-moi-truong-quy-chuan-ky-thuat-quoc-gia-ve-danh-gia-chat-luong-du-bao-canh-bao-khi-tuong-thuy-van | heat "từ 35°C trở lên"; monthly-rain mean over about the latest 30 years | READ |
| R-K08 | TTLT 43/2015/TTLT-BNNPTNT-BKHĐT (disaster damage statistics) | https://caselaw.vn/van-ban-phap-luat/276855-thong-tu-lien-tich-43-2015-ttlt-bnnptnt-bkhdt-huong-dan-thong-ke-danh-gia-thiet-hai-do-thien-tai-gay-ra-do-bo-truong-bo-nong-nghiep-va-phat-trien-nong-thon-bo-ke-hoach-va-dau-tu-ban-hanh | events counted by type, no levels | READ |
| R-K09 | QĐ 18/2021/QĐ-TTg official copy (Art. 54 "liên tiếp") | https://vupc.mae.gov.vn/Data/files/18_2021_QD-TTg.doc | decree wording | READ |
| R-K10 | MODIS MCD12 user guide V6.1; LP DAAC MCD12Q1 v061 page | https://lpdaac.usgs.gov/documents/1409/MCD12_User_Guide_V61.pdf ; https://lpdaac.usgs.gov/products/mcd12q1v061/ | not for year-to-year change; tropical cropland under-mapped; 2021+ warning (the LP DAAC URL now redirects to https://www.earthdata.nasa.gov/data/catalog/lpcloud-mcd12q1-061, which carries the same "caution ... for 2021 and beyond" text, re-read 2026-11-13) | READ |
| R-K11 | NASA GLAM crop mask MCD12C1 IGBP 2018 | https://glam1.gsfc.nasa.gov/api/doc/cropmask/v1/MCD12C1-IGBP_2018_crops | one fixed mask year (no reason given) | READ |
| R-K12 | Dong, J. et al. (2016) Remote Sensing 8(4): 281 | https://mdpi-res.com/d_attachment/remotesensing/remotesensing-08-00281/article_deploy/remotesensing-08-00281.pdf | cropland only if cropland in all years 2001-2012 | READ |
| R-K13 | ISRIC SoilGrids FAQ (pages 03, 04); Poggio, L. et al. (2021) SOIL 7: 217-240 | https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_03.html ; https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_04.html | not for local or farm level, not subnational | READ |
| R-K14 | SAGE crop calendar dataset page | https://sage.nelson.wisc.edu/data-and-models/datasets/crop-calendar-dataset | partial-month practice (none found) | READ |
| R-K15 | NCHMF (Tổng cục KTTV, Trung tâm Dự báo KTTV Quốc gia), seasonal bulletin Số 191/KTHM-04/12h00/DBQG-DBKH, 15/4/2024, footnote 1 | https://kttv.gov.vn//upload/khihau/2024/4/16/dbqg_kthm_20240415_1200_signed-1.pdf | rain normal period: "Giá trị TBNN của nhiệt độ và lượng mưa trên toàn quốc được tính cho giai đoạn 1991-2020" | READ (2026-11-12) |
| R-K16 | Thông tư 25/2022/TT-BTNMT Art. 23.2 a (drought forecasting procedure) | https://caselaw.vn/van-ban-phap-luat/412893-thong-tu-so-25-2022-tt-btnmt-ngay-30-12-2022-cua-bo-truong-bo-tai-nguyen-va-moi-truong-quy-dinh-ve-quy-trinh-ky-thuat-du-bao-canh-bao-hien-tuong-khi-tuong-thuy-van-nguy-hiem | rain deficit "so với giá trị trung bình nhiều năm cùng thời kỳ"; no period given | READ (2026-11-12) |
| R-K17 | University of Arkansas Division of Agriculture, Arkansas Rice Production Handbook MP192, ch. 2 (rice growth and development) | https://www.uaex.uada.edu/publications/pdf/mp192/chapter-2.pdf | glossary: heading | READ (2026-11-12, research agent) |
| R-K18 | FAO Irrigation Water Management Training Manual 4, ch. 4 (rice) | https://www.fao.org/4/t7202e/t7202e07.htm | glossary: nursery, transplanting, direct (broadcast) sowing | READ (2026-11-12, research agent) |
| R-K19 | Nghị quyết 81/2023/QH15, consolidated text 151/VBHN-VPQH, Art. 3.1 a | https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/9/151-vbhn-vpqh.pdf | 14-province region "Bắc Trung Bộ và duyên hải miền Trung" | READ (2026-11-12, research agent) |
| R-K20 | QĐ 2161/QĐ-TTg (11/11/2013), tourism plan for Bắc Trung Bộ | https://caselaw.vn/van-ban-phap-luat/170115-quyet-dinh-so-2161-qd-ttg-ngay-11-11-2013-cua-thu-tuong-chinh-phu-phe-duyet-quy-hoach-tong-the-phat-trien-du-lich-vung-bac-trung-bo-den-nam-2020-tam-nhin-den-nam-2030 | Bắc Trung Bộ = Thanh Hóa, Nghệ An, Hà Tĩnh, Quảng Bình, Quảng Trị, Thừa Thiên - Huế | READ (2026-11-12, research agent) |
| R-K21 | QĐ 2350/QĐ-TTg (24/12/2014), tourism plan for Duyên hải Nam Trung Bộ | https://hethongphapluat.com/decision-no-2350-qd-ttg-dated-december-24-2014.html | Duyên hải Nam Trung Bộ = Đà Nẵng + 7 provinces | READ (2026-11-12, research agent) |

## 11. Audit notes (2026-11-13): duplicate ids and terms for sections 5-10

**Duplicate ids.** Each of the sets below names one source. We keep all the ids because other files cite them, and
new text cites the first id of each set: R-A01 = R-K09 (QĐ 18/2021); R-A02 = R-K06 = R-K16 (TT 25/2022);
R-G10 = R-K08 (TTLT 43/2015); R-G14 = R-K02 (VASS entry); R-G03 = one file of R-V08 (Nam Đàn notice 80.pdf); R-L01 = R-J11 (IP Law); R-L03 = R-J12
(Standards Law Art. 21); R-E25 = R-J16 (POWER referencing page); R-E24 = first page of R-J15 (Earthdata data use
guidance); R-H05 (FAQ part) = R-H13; R-G17 = R-L10 (NQ 22/2003); R-G06 = R-G27 (Decree 112/2024); R-D03 = R-W04
(Turek 2023); R-M05 = R-A04 (Satake and Yoshida 1978).

**Terms for sources whose values or text reach the app.** Sections 1-4 have a terms column. The table below covers
the sources in sections 5-10 that DATA-DICTIONARY.md names as `source_ids` of app values. Rows marked "not recorded"
are [OPEN: question for the team, 2026-11-13].

| id | terms (what the source text says) | evidence |
|---|---|---|
| R-A01, R-G06, R-G27, R-J10 | IP Law Art. 15.2 lists "Văn bản quy phạm pháp luật, văn bản hành chính, văn bản khác thuộc lĩnh vực tư pháp và bản dịch chính thức của văn bản đó" among the objects outside copyright protection. Whether each of these documents is of that kind, and the site terms of the caselaw.vn and hethongphapluat.com copies, are not checked | R-L01 Art. 15.2 (re-read 2026-11-13) |
| R-W15 | Bộ KH&CN holds the publishing right of TCVN (Standards Law Art. 21); IP Law Art. 15.3 lists "số liệu" outside copyright protection; values only, quoted with source | R-J12; R-L01 Art. 15.3 |
| R-M23, R-K12, R-E06 | CC BY 4.0 (Crossref licence records, 2026-11-13) | doi:10.3390/rs16050805; doi:10.3390/rs8040281; doi:10.3389/fsufs.2021.691786 |
| R-E13 | FAO terms of use: acknowledgement, no implied endorsement, no FAO logo | R-J14 |
| R-A15, R-W12, R-K03, R-K10, R-K15, R-C13, R-E12 | not recorded | - |

Two more groups remain: the sources in sections 5-10 that are research only, whose values or text do not reach the
app, and the sources cited only by UI-UX-SPEC (design evidence and About-page legal sources). Whether each of them
needs a terms entry is [OPEN: question for the team, 2026-11-13].

## 12. Event additions (2026-11-14; read during the event)

| ID | Citation | URL | Accessed | Terms | Used for | Status |
|---|---|---|---|---|---|---|
| R-M25 | Lobell, D.B., Burke, M.B. (2010). On the use of statistical models to predict crop yield responses to climate change. Agricultural and Forest Meteorology 150: 1443-1452 | https://web.stanford.edu/~mburke/papers/lobell_burke_2010_AFM.pdf | 2026-11-14 | author copy | M1 pooling with season interactions and ridge regression: "well worth the potential penalty of restricting all sites to obey the same functional relationship, whereas the same is not true for precipitation" | READ |
| R-M26 | Ortiz-Bobea, A. (2021). Climate, agriculture and food. Handbook of Agricultural Economics 5: 3981-4073 | https://arxiv.org/pdf/2105.12044 | 2026-11-14 | arXiv preprint | M1 design: "test whether coefficients are stable across major regional or temporal subsets of the data"; climate means as covariates (Moore and Lobell 2014 "hybrid" model), with the warning "the cross-sectional estimation is still vulnerable to omitted variables operating within countries" | READ |
| R-M27 | LightGBM documentation, Parameters Tuning ("Tune Parameters for the Leaf-wise (Best-first) Tree") | https://lightgbm.readthedocs.io/en/latest/Parameters-Tuning.html | 2026-11-14 | project docs (MIT) | M2 grid: num_leaves "smaller than 2^(max_depth)", min_data_in_leaf, max_depth | READ |
| R-M28 | NIST GLP 9, Good Laboratory Practice for Rounding Expanded Uncertainties and Calibration Values (NIST IR 6969-2019) | https://www.nist.gov/document/glp-9-rounding-20190506pdf | 2026-11-14 | US government work | engine rounding rule: round once, never intermediate values | READ (search result summary; not opened) |
| R-B01 | USDA ARS, GRIN-Global Taxonomy, taxon pages (family as written): Vigna radiata 41629, Glycine max 17711, Vigna unguiculata subsp. unguiculata Biflora Group 467840, Arachis hypogaea 3785 (all Fabaceae); Oryza sativa 26077, Zea mays 42207 (Poaceae); Ipomoea batatas 20142 (Convolvulaceae); Sesamum indicum 33749 (Pedaliaceae); Capsicum annuum 8904, Capsicum frutescens 8913 (Solanaceae); Cucurbita moschata 12601 (Cucurbitaceae) | https://npgsweb.ars-grin.gov/gringlobal/taxon/taxonomydetail?id=41629 (and the other ids) | 2026-11-14 | US government work | crop family, legume or not, in rules/crops.yaml | READ |
| R-B02 | Đỗ Tất Lợi, Những cây thuốc và vị thuốc Việt Nam, pp. 239-240 (đậu đen: "Vigna cylindrica Skeels ... Thuộc họ Cánh bướm Fabaceae"; "đậu đen xanh lòng có nhân màu xanh nhạt"; the book notes the name "hiện nay chưa được chính xác lắm"; GRIN lists Vigna cylindrica as a homotypic synonym under R-B01 467840) | https://vnras.com/?p=21639 (transcription) | 2026-11-14 | book, read in a transcription | scientific name and family of đậu đen xanh lòng | READ (transcription) |
