# ML Specification

This document specifies the ML part of the project: the target, the features, the models, the validation and the pass
rules. It is version 0.3 of 2026-11-12, updated with the method answers of 2026-11-13 (§4 mask, §5a heat and cold, §6
penalty grid, §7.2 holdout B0) and with the choices made at the event on 2026-11-14 (§3 normal method, §4 freeze
commit, §6 model details, §7 sensitivity runs). The full history is in git.

We read the challenge Resources tab on 2026-11-13, and it did not change the core of this design. We interpret the rules
as follows: public data may be used before the event, official challenge datasets are not used for training outside the
event window, and the final reported models are trained during the event. Open items are listed in §11.

## 1. What question does the ML answer?

The ML does not predict what a given farm will yield. The question it answers, as worded on the method page, is:

> **"How much of the year-to-year swing in regional rice yield can NASA weather predict, tested on 2016-2024?"**

Past years are labelled with the official risk-level rules of QĐ 18/2021 (§5). We do not define a bad-year label and
do not train a bad-year classifier.

The cards always show the farmer the real past harvest numbers from the NSO. For picked years in 2016-2024 only, a card
may show the model's out-of-sample prediction next to the real value. The prediction never replaces the real value,
and it appears only for a season whose own test passed (§8). No model value is shown for 1995-2015, because it would be
an in-sample value. The model gives a regional climate-sensitivity estimate and is labeled as one. It is applied only
to past years and never to the coming season.

## 2. Labels: what the data actually supports (NSO PX-Web, English DB E06)

| Crop / season | NSO table | Years available | Units in rows | ML role |
|---|---|---|---|---|
| Rice, whole year | E06.13/14/15 | 1995 - 2024 (+ "Prel. 2025") | 64 historical provinces + regions | context |
| Spring (winter-spring) rice | E06.16/17/18 | 1995 - 2024 (+ Prel. 2025) | same | **ML target** |
| Autumn (summer-autumn) rice | E06.19/20/21 | 1995 - 2024 (+ Prel. 2025) | 32 provinces only; the 13 Mekong provinces excluded and Đà Nẵng dropped by the 2,000 ha rule (data 1995-2003 only), leaving 18 | **history only, no model**: gate G1 fails (18 provinces vs >= 25 required), pre-registered action "drop the failing season" |
| Winter (10th-month) rice | E06.22/23/24 | 1995 - 2024 (+ Prel. 2025) | same | **ML target** where present |
| Maize (grain) | E06.25/26/27 | 1995 - 2024 (+ Prel. 2025) | same | not an ML target |
| Peanut | E06.34/35 (area, production) | **2018 - 2024 only** (+ Prel. 2025) | ~60 provinces | not an ML target (descriptive only) |
| Other plan crops (pumpkin, biomass maize, mung bean, sesame, chili, soybean, sweet potato, black bean) | none used | none | none | study values only (P-02) |

The province list includes Hà Tây (merged into Hà Nội in 2008), because the rows use historical units; see
DATA-DICTIONARY.md. By the NSO definition, the E06 rice yields are yields per sown area.

We parsed the labels on 2026-11-10 and counted only non-preliminary rows that have a yield. Spring rice has 1,863 rows
from 64 provinces, autumn rice 908 rows from 32, and winter rice 1,758 rows from 63. After cleaning, the training table
has 3,961 rice rows (spring 1,827, summer-autumn 514, winter 1,620).

The data hold less independent information than the row count suggests, because neighbouring provinces share weather
in the same year. All uncertainty statements therefore resample whole years (year bootstrap), which keeps the spatial
correlation (Wilks 1997, secondary, R-S30).

This affects what the product can show. The plans shown are the P-02 structures, and CC1-CC4 contain no rice. Only the
rice of CC5 and of the P-03 control (rice - rice - fallow) has rice history numbers, and only spring and winter rice
can get an out-of-sample prediction (2016-2024). The UI makes this difference visible: non-rice crops show "no regional
data", and only summer-autumn rice shows "not modeled".

## 3. Target definition

For province p, rice season c, year t:

    anom[p,c,t] = yield[p,c,t] / normal[p,c](t) - 1        (percent anomaly against a past-only normal)

- The form comes from published work: a percent anomaly against a past-only normal (Iizumi and Ramankutty 2016:
  "three-year RM yield (year t-3 to t-1)", anomaly in percent; Lu et al. 2017: anomaly = ratio minus one, with a
  two-sided fit that we do not use because it would include later years).
- `normal` is fitted per province x rice season, only on years before the test year, and refit in each fold (Paudel et
  al. 2021: trend from later years "would cause information leakage").
- Normal-yield method: we choose it from published candidates by rolling-origin skill on years before the test period
  and report the sensitivity to that choice (Lobell and Field 2007). The comparison years are the inner test years of
  the first outer fold (§7), restricted to years where both candidates have a normal. The candidates are the 3-year
  past mean (Iizumi and Ramankutty 2016) and the 5-year linear trend (Paudel et al. 2021). A normal exists only when
  that many past years exist. We use only these two candidates, because their sources define their windows. At the
  event, before the freeze commit (§4), we chose the 3-year past mean (`normal.CHOSEN_METHOD` in
  ../src/fieldshift/ml/normal.py).
- Interpretation: anom = -0.10 means 10% below the normal yield.
- Years without a normal (the first years of a series, before the method has its required past years) have no
  anomaly. The value is null in every artifact, and the app shows "not available" for that year. These years are not
  used as training or test rows.
- We exclude "Prel. 2025" from training and from the main test, and report it separately if at all.
- Structural breaks: the 2004 province splits (Nghị quyết 22/2003/QH11: Cần Thơ, Đắk Lắk, Lai Châu; Than Uyên from
  Lào Cai; NSO footnote on 1995-2003 merged values) start new series in 2004 as named rules, in the same way as Hà Tây
  in 2008. The > 50% area-change rule still applies to every unit, including these four in other years. A row gets the
  low-yield flag when its yield is outside +-30% of the previous 3-year mean (FAO statistics system outlier rule).
  Flagged rows are not dropped silently. The code is in ../src/fieldshift/data/series.py.

## 4. Features

All features are computed from NASA POWER daily data over the season window from the NSO calendar. Province weather
is computed from the POWER cells, weighted by farmland. The farmland weights come from one fixed MODIS farmland mask,
built from years before the first test year 2016 and used for every year 1995-2024. A same-year map is in-season
information, and a map from a test year would use later information.

In the mask, each 0.05 deg pixel's farmland share is its minimum MODIS cropland percent over 2001-2015. IGBP class 12
(croplands, "At least 60% of area is cultivated cropland", MCD12 user guide, R-K10) is counted at 80%, the middle of
60-100%. Class 14 (cropland/natural vegetation mosaics, "small-scale cultivation 40-60%", R-K10) is counted at 50%, the
middle of that range, so both classes follow the same middle rule. We recomputed the weights on 2026-11-13 with class
12 at 80% (scripts/build_cell_weights.py). Compared with class 12 at 100%, Nghệ An weights change by at most 0.004 and
the weights of other provinces by up to 0.040 (Tiền Giang cell 10.5 N 106.875 E). Between 40% and 60% for class 14,
Nghệ An weights change by at most 0.0085 and the weights of other provinces by up to 0.069 (Tiền Giang, same cell).

Taking the minimum keeps the farmland that is present in every year. This adapts Dong et al. 2016 (R-K12) to percent
data; the binary per-pixel rule removes all farmland from 9 NSO provinces and the Côn Đảo shape. The MODIS guide
advises against using the product for year-to-year change (R-K10). Before the freeze commit, we list and report every
POWER cell whose farmland weight becomes zero, because small tropical fields can be under-mapped (R-K10). There is no
silent fallback. The check at the event listed 89 zero-weight cells and found no province without farmland.

The ETCCDI, temperature-mean, soil-water and radiation features use the weighted province series. The
official-condition counts, including the hot days above 35 C, are counted per POWER cell first and then weighted.

Freeze rule: the feature list below and the cleaning rules (§3, DATA-DICTIONARY.md) are frozen in a recorded commit
before the first model run on real data. The freeze commit is ea7a60c (2026-11-14). No feature or cleaning change
after that commit enters the primary test.

| Group | Features | Notes |
|---|---|---|
| Rain | season total (mm); season total vs the same window's mean **over the training years only** (%); longest dry spell (CDD, days < 1 mm); days >= 20 mm (R20mm); wettest 5 days (Rx5day) | ETCCDI definitions; the official 1991-2020 normal is used only for the displayed official conditions (§5), not in ML features (past-only rule) |
| Heat | mean Tmax, mean Tmin, hottest day (TXx), days Tmax > 35 C | basic definition of QĐ 18/2021/QĐ-TTg Art. 5.21 (R-A01): "vượt quá 35°c", so strictly above 35 C (35.0 C is not counted); counted over the whole season window, because flowering dates are not sourced |
| Official-condition counts | heavy-rain days (> 50 mm in 24 h, Art. 5.17), drought rain months (both readings), cold days (daily mean strictly below 13 C, Art. 5.18 "dưới 13oc"; below 15 C, TT 25/2022 Art. 3.6) | basic definitions of QĐ 18/2021 Art. 5 (R-A01) over the NSO season window, counted per cell then weighted; the ML features stay the ETCCDI and official-condition counts; the monthly comparison for ML uses the training-years normal. These are not the displayed labels (§5a uses the risk-level rules over the P-02 field days and months); the two counts are never mixed. The risk-level counts enter the ML only as sensitivity run (c) of §7 |
| Soil water (model) | mean and min GWETROOT (MERRA-2 root-zone wetness) | modeled, not observed; label as such |
| Radiation | mean ALLSKY_SFC_SW_DWN (MJ/m2/day) | from 1984, so training from 1995 is covered |
| Context | rice season, province long-term climate means over the training years of each fold (past-only): per province and season, the mean of every stored weather feature over the years before the fold; no region label (a held-out region in the spatial test would be an unseen category) | no province ID one-hot in the main model |

No crop water index is used as a feature.

The ML features and the displayed labels use different thresholds. The ML features above use the basic definitions,
which are strict (R-A01): a heat day has a daily maximum above 35 C (Art. 5.21 "vượt quá 35°c"), and rét hại is a
daily mean below 13 C (Art. 5.18 "dưới 13oc"). The displayed risk-level labels (§5a) use Art. 47 and 53, where 35.0 C
and 13.0 C are included.

The following are forbidden as features: the year, any yield or area value from the test year, NDVI or other in-season
vegetation signals, anything derived from the test year's labels, sequence or rotation IDs, and a land-cover map from
the same or a later year.

Preprocessing inside folds: standardisation means and standard deviations, the training-years rain normal and any
other fitted transformation are fitted on the training years of each fold only and then applied to that fold's test
year.

Information timing: the features use observed weather over the growing season. The model is therefore a
retrospective climate-sensitivity model and is not meant as a pre-planting forecast. In the app it is applied to past
years that the farmer picks, and it is never presented as a prediction of the next season.

### 4b. Water facts shown in the app (not an ML part)

The water row shows only sourced facts, and each line names what it measures:
- the crop's official rain and drought labels (§5);
- TCVN 8641:2011, "nước phải tưới vào ruộng" (water to apply to the field, m3/ha), where the standard has a section
  for the crop: maize 2,000-2,500 m3/ha whole season; peanut about 2,000; soybean about 2,000; sweet potato
  1,200-1,400 m3/ha; rice per region, season and method, both regions shown because the standard does not place
  Nghệ An: Trung bộ transplanted spring 6,500-7,500, summer-autumn 6,000-7,000; Trung bộ direct-seeded spring
  6,500-7,500, summer-autumn 5,700-7,000; Bắc bộ spring 6,000-7,000, mùa 4,500-5,500 m3/ha (maintenance only, land
  preparation excluded); a rice crop shows only the rows of its own season, taken from the standard's own row label;
- FAO Training Manual 3 Table 14, "nước cây dùng" (water the crop uses over its season, mm, "rough estimate"), where
  the exact crop is a row: rice paddy 450-700, maize 500-800, peanut 500-700, soybean 450-700 mm.
For mung bean, black bean, black sesame, chili, pumpkin and biomass maize the row says "not listed in these sources".
The two sources measure different quantities, so they are never compared or combined. FAO-56 Penman-Monteith ET0 is
not used for any displayed number.

## 5. Past years (how history and the model are used in the app)

### 5a. Official risk-level labels per past year and crop

The basic definitions alone are uninformative. A day above 35 C occurs in 30 of 30 springs (February-June 1995-2024)
on the farmland-weighted Nghệ An series, and in 27 of 30 at the largest-weight cell 19.0 N 105.625 E. We recomputed
these counts on 2026-11-13 from the cached POWER T2M_MAX, and they are unchanged with class 12 counted at 80%. The
labels therefore use the risk-level rules of QĐ 18/2021/QĐ-TTg (R-A01). The table below summarises the rules and
quotes the article text:

| Label | Rule (quoted) | What we compute from NASA POWER |
|---|---|---|
| heavy rain | Art. 44.1, level 1: "lượng mưa từ 100 mm đến 200 mm trong 24 giờ hoặc từ 50 mm đến 100 mm trong 12 giờ, kéo dài từ 1 ngày đến 2 ngày" (Bảng 4: higher amounts give higher levels) | a day with PRECTOTCORR >= 100 mm (daily totals; the 12-hour branch "từ 50 mm đến 100 mm trong 12 giờ" of Art. 44 (R-A01) is not computable, because POWER gives daily values (R-N01)); the "dưới 1/2 số huyện, xã" extent is not computed (we show a share of farmland instead) |
| heat | Art. 47.1: "đợt nắng nóng với nhiệt độ cao nhất trong ngày từ 35°c đến 37°c, kéo dài từ 3 ngày trở lên" and the higher bands b-d (regions "Bắc Bộ, Trung Bộ") | word for word, as for cold: a spell of >= 3 consecutive days with T2M_MAX inside one band of Art. 47.1: 35.0-37.0 C (both included), above 37 to 39, above 39 to 41, above 41 (consecutive: NCHMF practice and two papers, R-K01, R-K04, R-K05; 35.0 included: QCVN 84:2024, R-K07); a run that crosses bands is not one "đợt" of either band and is not counted, while a run of 3 or more days inside one band counts also inside a longer hot spell (limitation on the method page) (every band of Art. 47.1 a-d covers Bắc Bộ and Trung Bộ for spells of 3 days or more, and longer spells reach levels 2-4 of Art. 47.2-47.4, so every such spell is level 1 or higher; R-A01) |
| drought (rain part) | Art. 48.1: "thiếu hụt tổng lượng mưa tháng trên 50% so với trung bình nhiều năm, kéo dài từ 2 tháng đến 3 tháng" (same rain wording for Trung Bộ and Bắc Bộ; the surface-water part is not computable) | >= 2 months with rain more than 50% below the same month's 1991-2020 mean (the rainfall TBNN period stated by the national forecasting centre, R-K15), both readings (consecutive; any 2 months) |
| damaging cold | Art. 53.1 a: "nhiệt độ không khí trung bình ngày từ trên 8°c đến 13°c, kéo dài từ trên 5 ngày đến 10 ngày ở vùng đồng bằng Bắc Bộ, Bắc Trung Bộ, Trung Trung Bộ hoặc kéo dài trên 10 ngày ở vùng núi, trung du Bắc Bộ"; 53.1 d: "từ 8°c trở xuống, kéo dài từ 3 ngày đến 5 ngày ở vùng đồng bằng Bắc Bộ, Bắc Trung Bộ, Trung Trung Bộ" | word for word: at least 6 consecutive days with T2M daily mean above 8.0 C and at most 13.0 C (Art. 53.1 a "từ trên 8°c đến 13°c ... trên 5 ngày") or at least 3 consecutive days <= 8.0 C (Art. 53.1 d); a spell counts only as a run of consecutive days inside one band; a run that crosses bands is not one "đợt" of either band and is not counted, while a qualifying run inside one band counts also inside a longer cold spell (e.g. 6 days at 10 C followed by 3 days at 7 C: each part meets its own band's rule, so the label is met; 4 days at 10 C followed by 2 days at 7 C is not counted; limitation on the method page); 13.0 C included (Art. 53 "đến 13°c", R-K04), with the Bắc Trung Bộ wording for every Nghệ An cell (NCHMF bulletins and the VASS climate zone place all of Nghệ An, mountains included, in Bắc Trung Bộ, R-K01, R-K02) |

Region mapping: every Nghệ An cell, mountain cells included, uses the Bắc Trung Bộ wording, which falls inside
"Trung Bộ" for Art. 47 and 48. The basis is official forecasting practice (NCHMF bulletins and the VASS climate-zone
entry, R-K01, R-K02). It is not a legal assignment, since the four articles never name Nghệ An, and we state this.
QĐ 18/2021 Phụ lục II (flood-forecast river list) lists Nghệ An under "Khu vực Bắc Trung Bộ". Officially issued levels
also take humidity, foehn wind and duration into account (R-K03), so our labels are a mechanical reading of the
tables, and we state this. The region does not change the label for the drought rain part or, by the reading above,
for heat. It does change the label for cold.

Computation: each rule is evaluated per POWER cell, per crop, in each past year 1995-2024, over the time the P-02
trial shows the crop in the field (P-02 Tables 1, 5, 9):
- daily rules (heavy rain, heat, cold): the exact days from the P-02 sowing date to the first reported harvest date,
  both included; a spell is counted only inside one block of consecutive field days (it does not join across the gap
  between two crops' field times);
  for a harvest range ("30/8 - 3/9") the first reported date is used;
- the monthly drought rule: the calendar months in which the crop was in the field according to its P-02 dates, that
  is, every month from its sowing month to its harvest month; the rule itself uses whole-month rain totals.

No reported crop window crosses 31 December, so each window lies inside the picked calendar year. The year-level
shares on Screen 2 use the same field time as the cards, joined over all P-02 crops in that calendar year: the union of
their field days for daily rules and of their field months for the drought rule. P-02 reports one sowing date per
crop, so no sowing range arises. The harvest month is the month of the first reported harvest date. The label value is
the share of Nghệ An farmland where the rule was met, which is the sum of the farmland weights (fixed farmland mask,
§4) of the cells where it was met. The app shows the share itself and does not turn it into a yes or no, because no
source gives a cut-off for a weighted share.

A rule counts as met at level 1 or higher.

Every count is shown with two sources, the threshold (QĐ 18/2021, article cited) and the values (NASA POWER, weighted
with MODIS farmland), and with the words "our computation, not an official record". The app also shows this
limitation: "we apply the official thresholds to NASA's 50 km grid values; gridded values smooth extremes (Zhang et
al. 2011, abstract)". We check heavy-rain years against the rice flood damage that DesInventar records for Nghệ An in
1995-2008; this comparison is a check only. The P-03 card has no field months, because P-03 gives no sowing dates, and
therefore it has no labels.

### 5b. Stability row for rice crops

Per rice season, for the picked years:

- each year's **real** anomaly from NSO history (always shown; "not available" for a year without a normal, §3);
- for picked years 2016-2024 only: the out-of-sample prediction next to the real value, only if that season's test
  passed (§8); 1995-2015: no model value; summer-autumn rice: never;
- a summary of the real values as min / median / max, with the worst years named. With 8 years there is 50%
  confidence that the min-max range covers 80% of outcomes, and with 10 years 62% (arithmetic with the NIST e-Handbook
  7.2.6.4 formula). The picked years therefore cannot support p10 / p90 bands, and none are shown. Small picks follow
  one rule: when fewer than N picked years have a real value, each year's value is shown instead of min / median /
  max, with N = 2 (the smallest count at which worst and best can differ);
- the number of years the summary is based on, and the scope text on the card without a number (province average;
  mostly irrigation-served rice). The share itself appears only on the method page, as a sourced number: about 92-98%
  of Nghệ An rice area. This is our arithmetic from a reported estimate, the 165,765 ha "tưới cho lúa" of the Sở
  NN&PTNT reports (R-G11, an estimate equal to the plan figure, summed over seasons), against the NSO rice area (R-D01);
- the years themselves, each with its labels, so the user sees what was compared.

## 6. Models

| ID | Model | Purpose |
|---|---|---|
| B0 | Each series' own mean anomaly over its training years, refit in each fold (WMO/WWRP: the historical mean; per series because pooling "Non-homegeneous samples can lead to overestimates of forecast skill"); in the spatial holdout the held-out series' own mean over its years before the test year (§7.2) | reference forecast "climatology" |
| B2 | Previous-year anomaly | reference forecast "persistence" (WMO/WWRP) |
| BNW | "No-weather" model: context features only (§4 Context group), no year-to-year weather; the same algorithm and settings as M1 minus the weather columns | skill is credited to NASA weather only beyond this model |
| M1 | Ridge regression on features standardised inside each fold, pooled nationally, rice-season interactions (the spring indicator times every weather feature; Lobell and Burke 2010, R-M25; Ortiz-Bobea 2021, R-M26); penalty grid of Meroni et al. 2021 (13 log-spaced values 1e-5..1, published for lasso), rescaled to ridge's loss scale: each ridge fit uses alpha_ridge = 2 n a, a = grid value, n = rows of that fit, because scikit-learn's Lasso loss divides the squared error by 2n and its Ridge loss does not (scikit-learn 1.9.1 docstrings); our scale conversion, not a published ridge grid (one search 2026-11-13 found none for this setting); the chosen penalty is reported in grid units, with the share of test years at an end of the grid | **primary test**: spring rice, rolling origin 2016-2024 |
| M2 | LightGBM; num_leaves, min_data_in_leaf, max_depth tuned on earlier years only (LightGBM tuning docs, R-M27); grid (team choice): num_leaves 15/31/63, min_data_in_leaf 10/20/40 (LightGBM defaults one step either side), max_depth 10/20/40 (Meroni et al. 2021 boosting grid); no monotonic constraints (docs require strong prior knowledge; Li et al. 2019) | nonlinear candidate (secondary) |
| M3 (opt.) | Random Forest; grid (team choice, Meroni et al. 2021 Table 4): max_depth 10 to 40 step 5, max_features all or sqrt, min_samples_split 6 values in [0.2, 0.8]; 100 trees | robustness check (secondary) |

The references are B0, B2 and BNW.

Same rows for all models: every model and reference is scored on exactly the same test rows. A province-year enters
the comparison only if every model and reference (including B2, which needs the previous year) can predict it.

Uncertainty: the model reports a split conformal interval built from earlier out-of-sample residuals, with no window
(Lei et al. 2018; Angelopoulos and Bates 2023). For each outer test year, these are the residuals of that fold's inner
test years (§7). The guarantee assumes exchangeable years, so coverage on later years is the check. The guarantee of
Lei et al. 2018 (Algorithm 2) holds for residuals of one fitted model on a held-out set. Here the residuals come from
several inner-fold models and the interval is placed around the refit outer model, so the guarantee does not apply
exactly and the G4 coverage on the test years is the check. Coverage of the interval must be reported (G4).

## 7. Validation

1. **Rolling-origin temporal** (Hyndman and Athanasopoulos FPP3 s5.10; Paudel et al. 2021): for each test year t,
   train on years < t (normal and feature normals also refit on years < t) and predict year t for all provinces.
   The first test year is 2016, which leaves 70% of 1995-2024 for training and 30% for testing (Paudel et al. 2021,
   2022; team choice). Hyperparameters are tuned inside each outer fold with expanding inner folds on earlier years
   (Paudel 2022; Varma and Simon 2006). Inner folds: inside each outer training window, the last 30% of its anomaly
   years (rounded to the nearest whole year, a half rounded up, at least 1) are inner test years. Each is predicted
   from all years before it, with training always starting at the first available year ("the training folds always
   started with the minimum training year", Paudel et al. 2022). This is the same 70/30 rule as in the outer split. The
   inner residuals are used for tuning, for the conformal interval (§6) and for the normal-method choice (§3).
2. **Spatial holdout**: block cross-validation where dependence exists (Roberts et al. 2017), trained only on years < t
   as well. The blocks are the six NSO regions listed in E06.14 (Roberts et al. 2017), and a residual correlogram
   checks that the blocks are larger than the residual correlation range. B0 in the holdout: a held-out region's series
   have no training rows, so B0 is each held-out series' own mean anomaly over its years before t. This works like
   B2's own previous year and uses no future data (`evaluation.predict_b0_holdout`).
3. **Pilot report**: errors for Nghệ An, Hà Tĩnh, Thanh Hóa separately (three-province set: team choice).
4. **No random K-fold** on rows (Morales and Villalobos 2023: "Random partitioning of data ... should be avoided").

Metrics: RMSE and MAE of the anomaly; skill score against B0, B2 and BNW (1 - MSE_model / MSE_reference; WMO/WWRP);
interval coverage; and out-of-sample R2 = 1 - sum (y - p)^2 / sum (y - mean(y))^2 on the test rows (Paudel et al.
2021, thesis eq. A.4). Schauberger et al. 2020 recommend reporting "at least one common evaluation measure, namely R2
or RMSE". Results are reported by rice season and region. Confidence intervals on skill come from a bootstrap over
whole years, not rows, with 10,000 resamples and the expanded percentile interval (Hesterberg 2015). For window
sensitivity, we shift and widen the season window by one month (Lobell and Di Tommaso 2025): the whole window one
month earlier, one month later, and one month wider on both ends (team choice). A row whose shifted window the daily
data do not cover is skipped.

Primary and secondary results: one primary test, M1 ridge on spring rice, rolling origin 2016-2024. Every other
model x season result (M1 winter rice, M2, M3) is secondary and reported as such. Verdicts are per season: a season's
model may be shown only if its own test passes (§8).

Pre-registered sensitivity analyses, reported next to the primary result, never replacing it: (a) the same test
without the FAO-flagged rows: they are never trained on or scored, but stay in the normals and in B2's previous-year
lookup (team choice); (b) skill computed from MAE instead of MSE (1 - MAE_model / MAE_reference); (c) the
official-condition count features replaced by the risk-level counts of §5a: per province and season, the farmland
share meeting the heavy-rain, heat and cold rules over the NSO season window, with the cold rule in the wording of
each province's Art. 53 region (team choice): mountain wording for the NSO "Northern midlands and mountain areas"
(our reading of "vùng núi, trung du Bắc Bộ", which the decree never lists), plains wording for the Red River Delta and
the QĐ 18/2021 Phụ lục II "Khu vực Bắc Trung Bộ" and "Khu vực Trung Trung Bộ" provinces, and no cold rule (share 0)
for Nam Trung Bộ, Tây Nguyên and Nam Bộ, which Art. 53 does not name.
Disclosure: a reviewer saw reference-forecast numbers on 2016-2024 (but no model result), and these numbers informed
the repair of the pass rules (§8). The repair was made before any model result existed.

Run order: the normal-yield method is chosen first, by rolling-origin skill on years before 2016 (§3); then
references B0, B2, BNW and the primary M1 with its rolling-origin test and spatial holdout
(scripts/run_primary_test.py); then the secondary models M2 LightGBM and M3 random forest
(scripts/run_secondary_models.py) on the same rows, columns, folds and inner tuning as M1, and the sensitivity runs
(scripts/run_sensitivity.py), right after the primary test. The MAE skill of (b) is `evaluation.mae_skill` in
../src/fieldshift/ml/evaluation.py.

## 8. Go / no-go criteria (decided before seeing test results)

The form of the gates (skill against reference forecasts, calibration before sharpness) is standard (WMO/WWRP; Gneiting
et al. 2007). The numbers in G2-G4 (90% CI, the three-province set, 70-90% coverage) are team choices and are stated
as such on the method page.

| Gate | Criterion | If it fails |
|---|---|---|
| G1 data | >= 20 usable years and >= 40 provinces for spring rice and for winter (mùa) rice, >= 25 provinces for summer-autumn rice, after cleaning | drop the failing season. **Result: summer-autumn rice fails (18 provinces after the Mekong exclusion and the 2,000 ha area rule); dropped, history only** |
| G2 skill (per season) | for that season, the model beats B0 **and** the no-weather model BNW, each with skill > 0 whose year-bootstrap 90% CI excludes 0, on rolling origin 2016-2024. Primary: M1, spring rice | the season's model is not shown on cards; the method page reports the skill with its 90% CI, in the form "skill {s} (90% CI {lo} to {hi}) against the climatology reference" with the computed values |
| G3 vs local (per season) | model does at least as well as persistence (B2) on the Nghệ An / Hà Tĩnh / Thanh Hóa subset: it passes when it beats B2 (year-bootstrap 90% CI of the skill difference above 0) or matches it (CI includes 0); it fails only when the CI lies entirely below 0 | the season's model is not shown on cards; history stays |
| G4 calibration (per season) | the model's 80% interval covers 70-90% of held-out outcomes | widen intervals; the interval is shown on the card next to the out-of-sample prediction only when G4 passes for that season (after widening if needed); otherwise hidden, with the reason on the method page |

G3 and G4 are judged per season, like G2. Skill against BNW (with its 90% CI) is always reported; any statement that
"NASA weather predicts" part of the variation uses this skill. The claim that NASA weather improves the prediction is
made only if the model beats BNW on the test years; otherwise the result is shown and the claim is not made.

The gates are G1-G4.

Expectation (to keep us honest): skill will be modest. Published reference points: Ray et al. 2015 found climate
significant in 30% of Vietnam's rice area, with mean in-sample R2 0.21 there (in-sample, upward-biased); Lobell and
Field 2007 report a global rice first-difference R2 of 0.29. These are in-sample or global figures, not a forecast of
our result; a negative G2 result is acceptable and must be reported with its skill and CI (wording in §8).
Factors our features do not see (for example irrigation, varieties, pests, policy) are not modelled; their share of
the variation is not studied here.

## 9. Known threats to validity

- Spatial autocorrelation inflates apparent sample size (handled by the year bootstrap).
- Province weather comes from about 50 km reanalysis cells (farmland-weighted); gridded values smooth extremes
  (Zhang et al. 2011).
- Farmland weights from one fixed farmland mask (minimum MODIS cropland percent over 2001-2015, §4) ignore later
  land-cover change; a year-matched map would leak in-season information.
- Choices made after looking at 1995-2024 data (cleaning rules, the 2,000 ha filter) are stated on the method page;
  the freeze commit (§4) fixes them before the first model run.
- Normal-yield fitting near structural breaks (2004 splits, Hà Tây 2008) creates false anomalies.
- Season windows come from one national calendar (2019 appendix) and vary by province; calendar errors blur the
  climate signal.
- Ecological fallacy: regional sensitivity is not a farm's sensitivity.
- Historical administrative changes (Hà Tây 2008; 2025 restructuring) can corrupt joins.
- Provincial rice is mostly irrigation-served (about 92-98% of Nghệ An rice area: our arithmetic from a reported
  estimate, R-G11 against the NSO rice area R-D01), so regional sensitivity can understate drought-prone land
  sensitivity.

## 10. Outputs consumed by the app

`artifacts/risk_table.json` (schema in DATA-DICTIONARY.md §5) holds, per province x rice season x past year, the real
anomaly (null without a normal), the out-of-sample prediction and its 80% interval (only 2016-2024, only spring and
winter rice, only where that season's gates pass; the interval only where G4 passes; else null), the model ID per
season and the source ids.
No shown plan has a winter (mùa) rice crop (P-02 and P-03 report spring, summer-autumn and autumn-winter crops), so
winter-rice model results appear only on the method page. The cards use M1 for every season; M2 and M3 appear only on
the method page as secondary results (choosing a model after seeing test results would use the test years).
`artifacts/hazard_labels.json` (DATA-DICTIONARY.md §4b) holds the share of farmland per crop x past year x rule.
`artifacts/metrics.json` and `artifacts/gates.json` (DATA-DICTIONARY.md §5b) hold the metrics with CIs per model x
season, the gate verdicts per season and the sensitivity results. `GET /api/method` serves them to the method page
(UI-UX-SPEC §11). The app never calls the model live.

## 10b. Model card (structure; every [RESULT] field is filled from metrics.json and gates.json)

The model card uses the nine sections of Mitchell et al. 2019 §4 (R-M24): model details, intended use with its
out-of-scope uses, factors, metrics, evaluation data, training data, quantitative analyses, ethical considerations,
and caveats and recommendations. Judges then find the usual items in one place. We added the "Gate verdicts" section.

| Section | Content |
|---|---|
| Model details | M1 ridge regression on standardised weather and context columns (§4, §6), penalty grid as in §6; secondary M2 LightGBM and M3 random forest (§6); references B0, B2, BNW. Version: the freeze commit ea7a60c (§4) |
| Intended use | Regional (province x rice season) percent yield anomaly: spring rice (cards and method page) and winter rice (method page only, §10), shown next to the real history for 2016-2024 only if the season's test passes (§8) |
| Intended use: out of scope | Farm-level prediction; forecasts of future seasons; causal claims about crop rotations; summer-autumn rice (no model, §8 G1) |
| Factors | Rice season and NSO region (results reported by season and region; region blocks of the spatial holdout); the Nghệ An, Hà Tĩnh, Thanh Hóa pilot subset (§7) |
| Metrics | RMSE, MAE, out-of-sample R2, skill against B0, B2 and BNW with 90% year-bootstrap intervals, 80% interval coverage (§7; interval §6) |
| Evaluation data | Rolling-origin test years 2016-2024 for all provinces, and the region holdout (§7) |
| Training data | NSO provincial rice statistics 1995-2024 and NASA POWER weather weighted by MODIS farmland (§2, §4), years before each test year only (§7) |
| Quantitative analyses | [RESULT: metrics table and the results chart, per season] |
| Gate verdicts | [RESULT: G1-G4 per season; "NASA weather improves the prediction" only if the model beats BNW, §8] |
| Ethical considerations | Shown to farmers only as context next to real history, with sources; the tool compares and does not decide |
| Caveats and recommendations | Provincial rice is mostly irrigated; neighbouring provinces share weather, which inflates the apparent sample size; 50 km gridded weather smooths extremes (§9); the test has 9 years, 2016-2024 (§7) |

## 11. OPEN items in this spec

- Drought month counting: both readings are computed and shown.
- P-02 plot layout: not known; we state it as a limitation.
