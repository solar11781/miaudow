"""AI core 01, climate ML: analog years and anomalous years of Nghệ An farmland (NASA POWER, farmland-weighted).

Two small, transparent methods on the 34 years 1991-2024, written with numpy only (no scikit-learn, no fitted model
beyond the baseline statistics named below). Both describe past years; neither is a forecast.

Analog-year search
    Features per year: the 12 monthly rain anomalies (% of the 1991-2020 normal of that month), hot days
    (T2M_MAX >= 35 °C) and the longest dry spell (days). Each feature is z-scored with the mean and standard deviation
    of the 1991-2020 baseline years only, so 2021-2024 never shift the scale. Distance = Euclidean over the 14
    z-scores. The k nearest other years are returned with the features that make up most of the squared distance.

Anomalous years
    Per calendar month, a robust z-score of log(1 + monthly rain mm) against the median and MAD (x 1.4826) of the 30
    baseline years; the year's score is the largest |robust z| of its 12 months; a year is flagged when its score is
    above the 95th percentile of the 30 baseline scores. Why this and not Mahalanobis with a shrunk covariance: 30
    years for 12 correlated, skewed monthly values give an unstable covariance even with shrinkage; the median and MAD
    are not pulled by the very extremes they should find; and the largest |z| names the month that drove the flag, so
    an officer can check it. log(1 + mm) because rain is bounded at zero and right-skewed: on the raw scale a very wet
    month always outweighs a very dry one.

Evaluation (api/eval/run_climate_ml_eval.py writes api/eval/results/climate_ml_2026-11-14.json)
    Analogs: leave-one-year-out on 1992-2024. For each held-out year the monthly normal, the z-score scale and the
    tercile thresholds are recomputed from the baseline years WITHOUT that year (no leakage). Proxy task: does the
    nearest analog's annual rain category (below / near / above normal, terciles; and the sign) match the held-out
    year's, compared with climatology (always "near normal"; for the sign, the majority sign) and persistence (the
    previous year)? The features contain the held-out year's own rain, so this checks that analogs share the year's
    character; it is not forecast skill. A second, out-of-sample check uses January-June only and asks about
    July-December. Exact McNemar tests say whether a difference is more than chance at this sample size.
    Anomalies: agreement with the simple rule "annual total outside the 10th-90th percentile of 1991-2020", and the
    same detector run on CHIRPS as a cross-source check.

Missing values are NaN inside the arrays and None outside; a year with a missing feature is excluded and listed, never
filled.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

import numpy as np

from . import canonical, climate_series
from .climate import FARMLAND, ClimateInputError
from .contracts import (
    AnalogResult,
    AnalogYear,
    AnomalyYear,
    AnomalyYearsResult,
    FeatureDriver,
    MethodEvaluation,
    MonthDriver,
    Provenance,
    Text,
    TimeWindow,
)
from .paths import ROOT

MODEL_ID = "climate_ml"
MODEL_VERSION = "1.0.0"
BASELINE = (1991, 2020)
MAD_SCALE = 1.4826  # MAD of a normal distribution x 1.4826 = its standard deviation
THRESHOLD_PERCENTILE = 95.0
DRIVER_Z = 2.0  # months listed as drivers: |robust z| >= 2, always including the largest
EVAL_FILE = ROOT / "api" / "eval" / "results" / "climate_ml_2026-11-14.json"
EVAL_COMMAND = r".venv\Scripts\python api/eval/run_climate_ml_eval.py"
EVAL_FILE_LABEL = "api/eval/results/climate_ml_2026-11-14.json"
MONTHS_VI = [f"tháng {m}" for m in range(1, 13)]
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
             "November", "December"]  # fmt: skip
FEATURES = [f"rain_anomaly_pct_m{m:02d}" for m in range(1, 13)] + ["hot_days", "longest_dry_spell_days"]
DISTANCE_UNIT = "standard deviations (Euclidean distance over 14 features z-scored on 1991-2020)"

PAST = Text(vi="So sánh các năm đã qua, không phải dự báo.", en="A comparison of past years, not a forecast.")
GRID = Text(
    vi="Số NASA POWER theo ô lưới mô hình, cân theo đất trồng; không phải số đo tại ruộng.",
    en="NASA POWER model grid values, farmland-weighted; not measured at a field.",
)
ANALOG_LIMITS = [
    PAST,
    GRID,
    Text(
        vi="Chỉ có 34 năm; năm giống nhất vẫn có thể khác nhiều ở những điều không đo ở đây (bão, lũ, sâu bệnh, giá).",
        en="Only 34 years; the closest year can still differ a lot in what is not measured here (storms, floods, "
        "pests, prices).",
    ),
    Text(
        vi="Mưa 12 tháng chiếm 12 trên 14 đặc trưng, nên mưa quyết định phần lớn khoảng cách.",
        en="Rain makes up 12 of the 14 features, so rain decides most of the distance.",
    ),
]
ANOMALY_LIMITS = [
    PAST,
    GRID,
    Text(
        vi="Không có danh sách 'năm bất thường' chính thức để kiểm tra; chỉ so được với một quy tắc đơn giản.",
        en="No official list of 'unusual years' exists to check against; only agreement with a simple rule is shown.",
    ),
    Text(
        vi="Ngưỡng là phân vị 95 của 30 năm chuẩn, nên khoảng 1-2 năm chuẩn luôn bị đánh dấu theo cách tính.",
        en="The threshold is the 95th percentile of 30 baseline years, so about 1-2 baseline years are flagged by "
        "construction.",
    ),
    Text(
        vi="Một năm khô đều mọi tháng có thể không bị đánh dấu, vì điểm chỉ nhìn tháng lệch nhiều nhất.",
        en="A year that is evenly dry in every month can stay unflagged, because the score looks at the most unusual "
        "month only.",
    ),
]


# ---------------------------------------------------------------------------------------------------- data


@dataclass(frozen=True)
class Table:
    years: np.ndarray  # (n,) int
    rain: np.ndarray  # (n, 12) monthly rain mm, NaN when missing
    anomaly_pct: np.ndarray  # (n, 12) canonical anomaly % vs the 1991-2020 normal, NaN when missing
    hot: np.ndarray  # (n,) hot days
    dry: np.ndarray  # (n,) longest dry spell days
    annual: np.ndarray  # (n,) annual rain mm


def _nan(v) -> float:
    return math.nan if v is None else float(v)


def load_table(clim: dict | None = None) -> Table:
    c = clim if clim is not None else canonical.load("climate.json")
    rows = c["series"]["farmland_weighted"]
    years = sorted(int(y) for y in rows)
    return Table(
        years=np.array(years, dtype=int),
        rain=np.array([[_nan(v) for v in rows[str(y)]["monthly_rain_mm"]] for y in years]),
        anomaly_pct=np.array([[_nan(v) for v in rows[str(y)]["anomaly_pct"]] for y in years]),
        hot=np.array([_nan(rows[str(y)]["hot_days"]) for y in years]),
        dry=np.array([_nan(rows[str(y)]["longest_dry_spell_days"]) for y in years]),
        annual=np.array([_nan(rows[str(y)]["annual_rain_mm"]) for y in years]),
    )


def annual_anomaly_pct(annual: float) -> float | None:
    """Annual total vs the sum of the stored 1991-2020 monthly normals (same number as /api/climate/history)."""
    if not np.isfinite(annual):
        return None
    normal = canonical.load("climate.json")["normal_mm"]["farmland_weighted"]
    return climate_series._annual_anomaly_pct(float(annual), normal)


def _opt(v: float, digits: int = 1) -> float | None:
    return None if v is None or not np.isfinite(v) else round(float(v), digits)


def baseline_mask(years: np.ndarray, exclude: int | None = None) -> np.ndarray:
    mask = (years >= BASELINE[0]) & (years <= BASELINE[1])
    if exclude is not None:
        mask &= years != exclude
    return mask


# ---------------------------------------------------------------------------------------------------- analogs


def monthly_normal(rain: np.ndarray, fit: np.ndarray) -> np.ndarray:
    """Mean of each month over the fit years; NaN for a month with any missing fit value (never re-averaged)."""
    sub = rain[fit]
    return np.where(np.isnan(sub).any(axis=0), np.nan, np.nanmean(np.where(np.isnan(sub), 0.0, sub), axis=0))


def features_from(rain_anom_pct: np.ndarray, hot: np.ndarray, dry: np.ndarray) -> np.ndarray:
    return np.column_stack([rain_anom_pct, hot, dry])


def zscale(x: np.ndarray, fit: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Mean and sample standard deviation of each feature over the fit rows only. A feature with zero spread (or a
    missing fit value) gets NaN and is left out of every distance."""
    sub = x[fit]
    bad = np.isnan(sub).any(axis=0)
    mean = np.where(bad, np.nan, np.nanmean(np.where(np.isnan(sub), 0.0, sub), axis=0))
    std = np.where(bad, np.nan, np.std(np.where(np.isnan(sub), 0.0, sub), axis=0, ddof=1))
    std = np.where(std > 0, std, np.nan)
    return mean, std


def nearest(z: np.ndarray, i: int, candidates: np.ndarray, years: np.ndarray) -> list[tuple[int, float]]:
    """Other rows by Euclidean distance to row i over the usable features; ties broken by the earlier year."""
    usable = ~np.isnan(z).all(axis=0)  # a feature without a baseline scale is NaN for every year
    cols = [j for j in range(z.shape[1]) if usable[j] and not np.isnan(z[i, j])]
    out = []
    for r in np.flatnonzero(candidates):
        if r == i or np.isnan(z[r, cols]).any():
            continue
        d = float(np.sqrt(np.sum((z[r, cols] - z[i, cols]) ** 2)))
        out.append((r, d))
    out.sort(key=lambda t: (round(t[1], 12), int(years[t[0]])))
    return out


def _feature_label(name: str) -> tuple[Text, str]:
    if name.startswith("rain_anomaly_pct_m"):
        m = int(name[-2:])
        return Text(vi=f"Mưa {MONTHS_VI[m - 1]} so với trung bình", en=f"{MONTHS_EN[m - 1]} rain vs the mean"), "%"
    if name == "hot_days":
        return Text(vi="Số ngày từ 35 °C", en="Days at 35 °C or more"), "days"
    return Text(vi="Đợt khô dài nhất", en="Longest dry spell"), "days"


def _canonical_features(t: Table) -> np.ndarray:
    return features_from(t.anomaly_pct, t.hot, t.dry)


def provenance(method_id: str, transformation: str) -> Provenance:
    c = canonical.load("climate.json")
    return Provenance(
        dataset_id=c["dataset_id"],
        source_id=c["source_id"],
        source_url=c["source_url"],
        source_revision=c.get("source_revision"),
        method_id=method_id,
        transformation_id=transformation,
        spatial_resolution="0.5° x 0.625° NASA POWER (MERRA-2) grid; 5 cells weighted by MODIS farmland share",
        validation_status="DERIVED",
        missing_policy="A year with a missing feature is left out and listed; nothing is filled.",
        limitations=[GRID],
    )


def _window(first: int, last: int, vi: str, en: str) -> TimeWindow:
    return TimeWindow(start=date(first, 1, 1), end=date(last, 12, 31), label=Text(vi=vi, en=en))


BASELINE_WINDOW = _window(BASELINE[0], BASELINE[1], "Năm chuẩn 1991-2020", "Baseline years 1991-2020")


def analog_search(year: int, k: int = 3) -> AnalogResult:
    """Tool: the k past years whose rain pattern, hot days and dry spell were closest to `year`'s."""
    t = load_table()
    if year not in t.years:
        raise ClimateInputError(f"year {year} outside {t.years.min()}-{t.years.max()}")
    if not 1 <= k <= 10:
        raise ClimateInputError("k must be between 1 and 10")
    x = _canonical_features(t)
    mean, std = zscale(x, baseline_mask(t.years))
    z = (x - mean) / std
    i = int(np.flatnonzero(t.years == year)[0])
    excluded = [int(y) for r, y in enumerate(t.years) if np.isnan(x[r]).any()]
    if year in excluded:
        raise ClimateInputError(f"year {year} has a missing feature; no analog search")
    ranked = nearest(z, i, np.ones(len(t.years), dtype=bool), t.years)[:k]
    ok = [r for r in range(len(t.years)) if not np.isnan(z[r]).any()]
    pair = [float(np.sqrt(np.nansum((z[a] - z[b]) ** 2))) for n, a in enumerate(ok) for b in ok[n + 1 :]]
    analogs = []
    for order, (r, d) in enumerate(ranked, start=1):
        contrib = (z[r] - z[i]) ** 2
        total = float(np.nansum(contrib)) or 1.0
        top = [j for j in np.argsort(-np.nan_to_num(contrib, nan=-1.0), kind="stable")[:3] if np.isfinite(contrib[j])]
        drivers = []
        for j in top:
            label, unit = _feature_label(FEATURES[j])
            drivers.append(
                FeatureDriver(
                    feature=FEATURES[j],
                    label=label,
                    unit=unit,
                    target_value=_opt(x[i, j]),
                    other_value=_opt(x[r, j]),
                    z_difference=round(float(z[r, j] - z[i, j]), 2),
                    share_of_distance=round(float(contrib[j]) / total, 3),
                )
            )
        annual = t.annual[r]
        analogs.append(
            AnalogYear(
                year=int(t.years[r]),
                order=order,
                distance=round(d, 2),
                distance_unit=DISTANCE_UNIT,
                annual_rain_anomaly_pct=annual_anomaly_pct(annual),
                drivers=drivers,
            )
        )
    return AnalogResult(
        target_year=year,
        k=k,
        analogs=analogs,
        excluded_years=excluded,
        median_pairwise_distance=round(float(np.median(pair)), 2),
        features=FEATURES,
        place=climate_series.farmland_place(),
        time_window=_window(year, year, f"Năm {year}", f"Year {year}"),
        baseline=BASELINE_WINDOW,
        provenance=provenance(
            "analog_years_zscore_euclidean",
            "climate.json:series.farmland_weighted.*.{anomaly_pct,hot_days,longest_dry_spell_days}",
        ),
        evaluation=analog_evaluation_summary(),
        limitations=ANALOG_LIMITS,
    )


# ---------------------------------------------------------------------------------------------------- analog evaluation


def tercile_class(v: float, q33: float, q67: float) -> str:
    return "below" if v < q33 else ("above" if v > q67 else "near")


def sign_class(v: float) -> str:
    return "drier" if v < 0 else "wetter"


def mcnemar_exact(a: list[bool], b: list[bool]) -> float:
    """Two-sided exact McNemar p-value for paired hits of two methods on the same cases."""
    n01 = sum(1 for x, y in zip(a, b, strict=True) if x and not y)
    n10 = sum(1 for x, y in zip(a, b, strict=True) if y and not x)
    n = n01 + n10
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(n01, n10) + 1)) / 2**n
    return round(min(1.0, 2 * tail), 4)


def _loo_case(t: Table, i: int, months: slice, label_months: slice, extra: bool) -> dict:
    """One held-out year: everything fitted on the baseline without it."""
    target = int(t.years[i])
    fit = baseline_mask(t.years, exclude=target)
    normal = monthly_normal(t.rain, fit)
    anom = (t.rain - normal) / normal * 100.0
    feats = [anom[:, months]] + ([t.hot[:, None], t.dry[:, None]] if extra else [])
    x = np.column_stack(feats)
    mean, std = zscale(x, fit)
    z = (x - mean) / std
    lab_ref = float(np.sum(normal[label_months]))
    label = (np.sum(t.rain[:, label_months], axis=1) - lab_ref) / lab_ref * 100.0
    q33, q67 = np.percentile(label[fit], [100.0 / 3.0, 200.0 / 3.0])
    ranked = nearest(z, i, np.ones(len(t.years), dtype=bool), t.years)
    a1 = ranked[0][0]
    top3 = [r for r, _ in ranked[:3]]
    votes = [tercile_class(label[r], q33, q67) for r in top3]
    best = max(votes, key=lambda c: (votes.count(c), -votes.index(c)))
    prev = i - 1
    fit_signs = [sign_class(v) for v in label[fit]]
    majority = "drier" if fit_signs.count("drier") >= fit_signs.count("wetter") else "wetter"
    truth_t = tercile_class(label[i], q33, q67)
    truth_s = sign_class(label[i])
    return {
        "year": target,
        "target_anomaly_pct": round(float(label[i]), 1),
        "target_tercile": truth_t,
        "target_sign": truth_s,
        "analog": int(t.years[a1]),
        "analog_distance": round(ranked[0][1], 3),
        "analog_anomaly_pct": round(float(label[a1]), 1),
        "analog_tercile": tercile_class(label[a1], q33, q67),
        "analog_sign": sign_class(label[a1]),
        "analog3_years": [int(t.years[r]) for r in top3],
        "analog3_tercile": best,
        "persistence_tercile": tercile_class(label[prev], q33, q67),
        "persistence_sign": sign_class(label[prev]),
        "majority_sign": majority,
        "tercile_thresholds_pct": [round(float(q33), 2), round(float(q67), 2)],
    }


def _score(cases: list[dict]) -> dict:
    def hits(pred: str, truth: str) -> list[bool]:
        return [c[pred] == c[truth] for c in cases]

    h = {
        "analog_k1_tercile": hits("analog_tercile", "target_tercile"),
        "analog_k3_tercile": hits("analog3_tercile", "target_tercile"),
        "persistence_tercile": hits("persistence_tercile", "target_tercile"),
        "climatology_tercile": [c["target_tercile"] == "near" for c in cases],
        "analog_k1_sign": hits("analog_sign", "target_sign"),
        "persistence_sign": hits("persistence_sign", "target_sign"),
        "climatology_sign": hits("majority_sign", "target_sign"),
    }
    n = len(cases)
    rates = {k: round(sum(v) / n, 3) for k, v in h.items()}
    p = {
        "tercile_analog_vs_persistence": mcnemar_exact(h["analog_k1_tercile"], h["persistence_tercile"]),
        "tercile_analog_vs_climatology": mcnemar_exact(h["analog_k1_tercile"], h["climatology_tercile"]),
        "sign_analog_vs_persistence": mcnemar_exact(h["analog_k1_sign"], h["persistence_sign"]),
        "sign_analog_vs_climatology": mcnemar_exact(h["analog_k1_sign"], h["climatology_sign"]),
    }
    beats_t = rates["analog_k1_tercile"] > max(rates["persistence_tercile"], rates["climatology_tercile"])
    beats_s = rates["analog_k1_sign"] > max(rates["persistence_sign"], rates["climatology_sign"])
    significant = beats_t and max(p["tercile_analog_vs_persistence"], p["tercile_analog_vs_climatology"]) < 0.05
    return {
        "n_cases": n,
        "hits": {k: int(sum(v)) for k, v in h.items()},
        "hit_rates": rates,
        "mcnemar_p": p,
        "beats_both_baselines_tercile": bool(beats_t),
        "beats_both_baselines_sign": bool(beats_s),
        "difference_significant_p05": bool(significant),
    }


def evaluate_analogs(t: Table | None = None) -> dict:
    """Leave-one-year-out evaluation of the analog method (1992-2024; 1991 has no previous year for persistence)."""
    t = t if t is not None else load_table()
    idx = [i for i, y in enumerate(t.years) if y - 1 in set(t.years.tolist())]
    full = [_loo_case(t, i, slice(0, 12), slice(0, 12), extra=True) for i in idx]
    half = [_loo_case(t, i, slice(0, 6), slice(6, 12), extra=False) for i in idx]
    main, oos = _score(full), _score(half)
    failures = [
        {
            k: c[k]
            for k in ("year", "target_anomaly_pct", "target_tercile", "analog", "analog_anomaly_pct", "analog_tercile")
        }
        for c in full
        if c["analog_tercile"] != c["target_tercile"]
    ]
    return {
        "proxy_task": {
            "years_evaluated": [c["year"] for c in full],
            "description": "Leave one year out. Features: 12 monthly rain anomalies (%), hot days, longest dry spell. "
            "Normal, z-score scale and tercile thresholds refitted on 1991-2020 without the held-out year. Label: the "
            "annual rain anomaly category (terciles of 1991-2020: below / near / above) and its sign. Baselines: "
            "climatology (always 'near normal'; for the sign, the majority sign of the fit years) and persistence "
            "(the previous year's category).",
            **main,
            "cases": full,
        },
        "out_of_sample_check": {
            "description": "Same leave-one-year-out setup, but the analog is chosen from January-June rain anomalies "
            "only and the label is the July-December rain anomaly category: information the features do not contain.",
            **oos,
            "cases": half,
        },
        "failure_cases": failures,
    }


def _verdict(main: dict, oos: dict) -> Text:
    r, q = main["hit_rates"], oos["hit_rates"]

    def pct(v: float) -> int:
        return round(v * 100)

    if main["beats_both_baselines_tercile"] and main["difference_significant_p05"]:
        vi_head = (
            f"Năm giống nhất trùng nhóm mưa cả năm của năm cần so trong {pct(r['analog_k1_tercile'])}% số năm, hơn cách "
            f"đoán 'bình thường' ({pct(r['climatology_tercile'])}%) và cách lấy năm trước ({pct(r['persistence_tercile'])}%)."
        )
        en_head = (
            f"The closest year matched the annual rain category in {pct(r['analog_k1_tercile'])}% of years, more than "
            f"'always normal' ({pct(r['climatology_tercile'])}%) and 'same as last year' ({pct(r['persistence_tercile'])}%)."
        )
    elif main["beats_both_baselines_tercile"]:
        vi_head = (
            f"Năm giống nhất trùng nhóm mưa cả năm trong {pct(r['analog_k1_tercile'])}% số năm, cao hơn cách đoán "
            f"'bình thường' ({pct(r['climatology_tercile'])}%) và năm trước ({pct(r['persistence_tercile'])}%), nhưng "
            "với 33 năm thì chênh lệch này chưa chắc không do ngẫu nhiên."
        )
        en_head = (
            f"The closest year matched the annual rain category in {pct(r['analog_k1_tercile'])}% of years, above "
            f"'always normal' ({pct(r['climatology_tercile'])}%) and last year ({pct(r['persistence_tercile'])}%), but "
            "with 33 years the difference may be chance."
        )
    else:
        vi_head = (
            f"Phương pháp KHÔNG hơn cách đơn giản: năm giống nhất trùng nhóm mưa cả năm trong "
            f"{pct(r['analog_k1_tercile'])}% số năm, so với {pct(r['climatology_tercile'])}% khi luôn đoán 'bình thường' "
            f"và {pct(r['persistence_tercile'])}% khi lấy năm trước."
        )
        en_head = (
            f"The method does NOT beat the simple baselines: the closest year matched the annual rain category in "
            f"{pct(r['analog_k1_tercile'])}% of years, against {pct(r['climatology_tercile'])}% for 'always normal' and "
            f"{pct(r['persistence_tercile'])}% for 'same as last year'."
        )
    vi_tail = (
        f" Phép thử này dùng chính mưa của năm đó nên chỉ cho thấy các năm giống nhau thật, không phải khả năng dự "
        f"báo: khi chọn năm giống theo tháng 1-6 để đoán tháng 7-12, mức trùng là {pct(q['analog_k1_tercile'])}% "
        f"(luôn đoán 'bình thường': {pct(q['climatology_tercile'])}%, năm trước: {pct(q['persistence_tercile'])}%)."
    )
    en_tail = (
        f" The test uses the year's own rain, so it shows that analogs are alike, not that they forecast: choosing "
        f"analogs from January-June to tell July-December matched in {pct(q['analog_k1_tercile'])}% of years "
        f"('always normal' {pct(q['climatology_tercile'])}%, last year {pct(q['persistence_tercile'])}%)."
    )
    return Text(vi=vi_head + vi_tail, en=en_head + en_tail)


@lru_cache(maxsize=1)
def _analog_eval_cached() -> dict:
    return evaluate_analogs()


def analog_evaluation_summary() -> MethodEvaluation:
    ev = _analog_eval_cached()
    main, oos = ev["proxy_task"], ev["out_of_sample_check"]
    return MethodEvaluation(
        task=Text(
            vi="Bỏ ra từng năm (1992-2024): nhóm mưa cả năm (thấp / gần / cao hơn bình thường) của năm giống nhất có "
            "trùng với năm bị bỏ ra không; so với luôn đoán 'bình thường' và lấy năm trước.",
            en="Leave one year out (1992-2024): does the closest year's annual rain category (below / near / above "
            "normal) match the held-out year's; against 'always normal' and 'same as last year'.",
        ),
        n_cases=main["n_cases"],
        scores={
            **{f"proxy_{k}": v for k, v in main["hit_rates"].items()},
            **{f"oos_{k}": v for k, v in oos["hit_rates"].items()},
            "proxy_mcnemar_p_vs_persistence": main["mcnemar_p"]["tercile_analog_vs_persistence"],
            "proxy_mcnemar_p_vs_climatology": main["mcnemar_p"]["tercile_analog_vs_climatology"],
        },
        beats_baselines=bool(main["beats_both_baselines_tercile"]),
        verdict=_verdict(main, oos),
        source_file=EVAL_FILE_LABEL,
    )


# ---------------------------------------------------------------------------------------------------- anomalies


def robust_z(rain: np.ndarray, fit: np.ndarray) -> np.ndarray:
    """Robust z of log(1 + mm) per calendar month against the fit years' median and MAD x 1.4826 (NaN stays NaN)."""
    v = np.log1p(rain)
    sub = v[fit]
    med = np.median(sub, axis=0)
    mad = np.median(np.abs(sub - med), axis=0) * MAD_SCALE
    bad = np.isnan(sub).any(axis=0) | ~(mad > 0)
    return np.where(bad, np.nan, (v - med) / np.where(bad, 1.0, mad))


def year_scores(z: np.ndarray) -> np.ndarray:
    """Largest |robust z| of the 12 months; NaN when a month is missing (the year is not scored, not filled)."""
    a = np.abs(z)
    return np.where(np.isnan(a).any(axis=1), np.nan, np.max(np.where(np.isnan(a), -1.0, a), axis=1))


def detect(rain: np.ndarray, years: np.ndarray) -> dict:
    fit = baseline_mask(years)
    z = robust_z(rain, fit)
    scores = year_scores(z)
    threshold = float(np.percentile(scores[fit & np.isfinite(scores)], THRESHOLD_PERCENTILE))
    flagged = np.isfinite(scores) & (scores > threshold)
    return {"z": z, "scores": scores, "threshold": threshold, "flagged": flagged}


def percentile_rule(annual: np.ndarray, years: np.ndarray) -> tuple[float, float, list[str | None]]:
    fit = baseline_mask(years) & np.isfinite(annual)
    p10, p90 = (float(v) for v in np.percentile(annual[fit], [10.0, 90.0]))
    flags = [
        None if not np.isfinite(v) else ("below_p10" if v < p10 else ("above_p90" if v > p90 else None)) for v in annual
    ]
    return p10, p90, flags


def agreement(a: list[bool], b: list[bool], years: list[int]) -> dict:
    n = len(a)
    both = sum(1 for x, y in zip(a, b, strict=True) if x and y)
    only_a = sum(1 for x, y in zip(a, b, strict=True) if x and not y)
    only_b = sum(1 for x, y in zip(a, b, strict=True) if y and not x)
    neither = n - both - only_a - only_b
    po = (both + neither) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    kappa = (po - pe) / (1 - pe) if pe < 1 else 1.0
    union = both + only_a + only_b
    return {
        "n_years": n,
        "both": both,
        "ml_only": only_a,
        "baseline_only": only_b,
        "neither": neither,
        "percent_agreement": round(po * 100.0, 1),
        "cohen_kappa": round(kappa, 3),
        "jaccard": round(both / union, 3) if union else 1.0,
        "ml_years": [y for y, x in zip(years, a, strict=True) if x],
        "baseline_years": [y for y, x in zip(years, b, strict=True) if x],
    }


def _drivers(z_row: np.ndarray, rain_row: np.ndarray, med_mm: np.ndarray) -> list[MonthDriver]:
    if np.isnan(z_row).any():
        return []
    order = np.argsort(-np.abs(z_row), kind="stable")
    picks = [int(order[0])] + [int(j) for j in order[1:] if abs(z_row[j]) >= DRIVER_Z]
    return [
        MonthDriver(
            month=j + 1,
            robust_z=round(float(z_row[j]), 2),
            rain_mm=round(float(rain_row[j]), 1),
            baseline_median_mm=round(float(med_mm[j]), 1),
            direction="wetter" if z_row[j] > 0 else "drier",
        )
        for j in picks[:4]
    ]


def chirps_cross_check(t: Table, power_flags: list[bool]) -> dict:
    """The same detector on CHIRPS farmland-weighted monthly rain: do the same years stand out in a second source?"""
    ch = climate_series.chirps_monthly(FARMLAND)
    if ch is None:
        return {"status": "unavailable", "reason": "CHIRPS not loaded in climate.json"}
    years = [int(y) for y in t.years if int(y) in ch]
    rain = np.array([[_nan(v) for v in ch[y]] for y in years])
    det = detect(rain, np.array(years))
    flags = [bool(f) for f in det["flagged"]]
    power = [power_flags[int(np.flatnonzero(t.years == y)[0])] for y in years]
    return {
        "status": "available",
        "threshold": round(det["threshold"], 3),
        "chirps_flagged_years": [y for y, f in zip(years, flags, strict=True) if f],
        "agreement_with_power": agreement(power, flags, years),
    }


@lru_cache(maxsize=1)
def _anomaly_cached() -> dict:
    t = load_table()
    det = detect(t.rain, t.years)
    p10, p90, pflags = percentile_rule(t.annual, t.years)
    ml = [bool(f) for f in det["flagged"]]
    base = [f is not None for f in pflags]
    years = [int(y) for y in t.years]
    return {
        "table": t,
        "det": det,
        "p10": p10,
        "p90": p90,
        "pflags": pflags,
        "agreement": agreement(ml, base, years),
        "agreement_baseline_years": agreement(
            [f for f, y in zip(ml, years, strict=True) if BASELINE[0] <= y <= BASELINE[1]],
            [f for f, y in zip(base, years, strict=True) if BASELINE[0] <= y <= BASELINE[1]],
            [y for y in years if BASELINE[0] <= y <= BASELINE[1]],
        ),
        "chirps": chirps_cross_check(t, ml),
    }


def anomaly_evaluation_summary() -> MethodEvaluation:
    a = _anomaly_cached()
    g = a["agreement"]
    ch = a["chirps"]
    kappa_vi = f"{g['cohen_kappa']}".replace(".", ",")
    ch_j = ch["agreement_with_power"]["jaccard"] if ch.get("status") == "available" else None
    return MethodEvaluation(
        task=Text(
            vi="So với quy tắc đơn giản 'tổng mưa năm ngoài khoảng phân vị 10-90 của 1991-2020', trên 34 năm.",
            en="Agreement with the simple rule 'annual total outside the 10th-90th percentile of 1991-2020', 34 years.",
        ),
        n_cases=g["n_years"],
        scores={
            "percent_agreement": g["percent_agreement"],
            "cohen_kappa": g["cohen_kappa"],
            "jaccard_flagged_sets": g["jaccard"],
            "n_flagged_ml": float(g["both"] + g["ml_only"]),
            "n_flagged_percentile_rule": float(g["both"] + g["baseline_only"]),
            "jaccard_power_vs_chirps": ch_j,
        },
        beats_baselines=False,
        verdict=Text(
            vi=f"Không có đáp án đúng cho 'năm bất thường', nên đây là mức trùng khớp, không phải độ chính xác: hai cách "
            f"cùng đánh dấu {g['both']} năm; chỉ cách theo tháng đánh dấu {g['ml_only']} năm; chỉ quy tắc tổng năm đánh "
            f"dấu {g['baseline_only']} năm (kappa {kappa_vi}). Cách theo tháng bắt được tháng mưa dữ dội hay khô "
            "hạn mà tổng năm làm mờ đi; quy tắc tổng năm bắt được năm khô hoặc ướt đều.",
            en=f"There is no ground truth for 'unusual year', so this is agreement, not accuracy: years flagged by "
            f"both methods: {g['both']}; by the monthly method only: {g['ml_only']}; by the annual-total rule only: "
            f"{g['baseline_only']} (kappa {g['cohen_kappa']}). The monthly method catches single extreme months that "
            "an annual total smooths out; the annual rule catches evenly dry or wet years.",
        ),
        source_file=EVAL_FILE_LABEL,
    )


def anomaly_years() -> AnomalyYearsResult:
    """Tool: every year's anomaly score, the flagged years and the months that drove them, beside the simple rule."""
    a = _anomaly_cached()
    t, det = a["table"], a["det"]
    fit = baseline_mask(t.years)
    med_mm = np.expm1(np.median(np.log1p(t.rain[fit]), axis=0))
    years = []
    for r, y in enumerate(t.years):
        score = det["scores"][r]
        years.append(
            AnomalyYear(
                year=int(y),
                in_baseline=bool(fit[r]),
                score=_opt(score, 3),
                flagged=bool(det["flagged"][r]),
                driving_months=_drivers(det["z"][r], t.rain[r], med_mm),
                annual_rain_mm=_opt(t.annual[r]),
                annual_rain_anomaly_pct=annual_anomaly_pct(t.annual[r]),
                percentile_flag=a["pflags"][r],
            )
        )
    g = a["agreement"]
    return AnomalyYearsResult(
        place=climate_series.farmland_place(),
        time_window=_window(int(t.years[0]), int(t.years[-1]), "1991-2024", "1991-2024"),
        baseline=BASELINE_WINDOW,
        score_unit="robust z (largest |z| of the 12 months; log(1 + mm), median and MAD x 1.4826 of 1991-2020)",
        threshold=round(det["threshold"], 3),
        threshold_rule=Text(
            vi="Năm bị đánh dấu khi điểm lớn hơn phân vị 95 của điểm 30 năm chuẩn 1991-2020.",
            en="A year is flagged when its score is above the 95th percentile of the 30 baseline-year scores "
            "(1991-2020).",
        ),
        percentile_bounds_mm=[round(a["p10"], 1), round(a["p90"], 1)],
        years=years,
        agreement={k: v for k, v in g.items()},
        provenance=provenance("robust_mad_max_month_score", "climate.json:series.farmland_weighted.*.monthly_rain_mm"),
        evaluation=anomaly_evaluation_summary(),
        limitations=ANOMALY_LIMITS,
    )


# ---------------------------------------------------------------------------------------------------- model card


def model_card() -> dict:
    """Version, inputs, training years, method, metrics, limitations and failure cases (served by the API)."""
    c = canonical.load("climate.json")
    ev = _analog_eval_cached()
    a = _anomaly_cached()
    flagged_monthly_only = [
        {
            "year": y,
            "why": "one or two extreme months; the annual total stays inside the 10th-90th percentile",
        }
        for y in a["agreement"]["ml_years"]
        if y not in a["agreement"]["baseline_years"]
    ]
    missed = [
        {
            "year": y,
            "why": "annual total outside the 10th-90th percentile, but no single month extreme enough to pass the "
            "threshold",
        }
        for y in a["agreement"]["baseline_years"]
        if y not in a["agreement"]["ml_years"]
    ]
    return {
        "model_id": MODEL_ID,
        "version": MODEL_VERSION,
        "implementation": "numpy only (no scikit-learn); api/miaudow_api/climate_ml.py",
        "inputs": {
            "file": "data/canonical/climate.json",
            "dataset_id": c["dataset_id"],
            "source_id": c["source_id"],
            "version_sha256": c.get("version_sha256"),
            "series": "series.farmland_weighted (monthly_rain_mm, anomaly_pct, hot_days, longest_dry_spell_days, "
            "annual_rain_mm)",
            "cross_check": "chirps.cells (CHIRPS v3, farmland-weighted with the same weights)",
            "years": [int(min(c["years"])), int(max(c["years"]))],
        },
        "training_years": {
            "baseline": list(BASELINE),
            "fitted_on_baseline_only": [
                "feature means and standard deviations (z-scores)",
                "monthly medians and MADs of log(1 + rain)",
                "the 95th-percentile score threshold",
                "the 10th and 90th percentiles of the annual total",
            ],
            "other_parameters": "none (no weights are learned)",
        },
        "components": [
            {
                "method_id": "analog_years_zscore_euclidean",
                "features": FEATURES,
                "distance": "Euclidean over z-scores; ties broken by the earlier year",
            },
            {
                "method_id": "robust_mad_max_month_score",
                "score": "max over months of |(log(1+mm) - median) / (1.4826 MAD)|",
                "threshold": f"{THRESHOLD_PERCENTILE:g}th percentile of the 1991-2020 scores",
                "why_not_mahalanobis": "30 years for 12 correlated, skewed months give an unstable covariance even "
                "with shrinkage; median/MAD resist the extremes being detected; the max names the driving month.",
            },
        ],
        "metrics": {
            "analogs_proxy": {k: ev["proxy_task"][k] for k in ("n_cases", "hit_rates", "hits", "mcnemar_p")},
            "analogs_out_of_sample": {
                k: ev["out_of_sample_check"][k] for k in ("n_cases", "hit_rates", "hits", "mcnemar_p")
            },
            "anomalies_agreement_all_years": a["agreement"],
            "anomalies_agreement_baseline_years": a["agreement_baseline_years"],
            "anomalies_chirps_cross_check": a["chirps"],
            "anomaly_threshold": round(a["det"]["threshold"], 3),
        },
        "limitations": [x.model_dump() for x in [*ANALOG_LIMITS, *ANOMALY_LIMITS[2:]]],
        "failure_cases": {
            "analog_category_mismatches": ev["failure_cases"],
            "anomaly_flagged_by_monthly_method_only": flagged_monthly_only,
            "anomaly_missed_compared_with_percentile_rule": missed,
        },
    }


def full_evaluation() -> dict:
    """Everything the eval script stores (deterministic: no randomness anywhere)."""
    ev = evaluate_analogs()
    return {
        "model": model_card(),
        "analogs": ev,
        "analog_summary": analog_evaluation_summary().model_dump(mode="json"),
        "anomalies": {
            "summary": anomaly_evaluation_summary().model_dump(mode="json"),
            "years": [y.model_dump(mode="json") for y in anomaly_years().years],
        },
    }


def stored_evaluation(path: Path | None = None) -> dict | None:
    """The stored evaluation file (EVAL_FILE, looked up at call time), or None when the script has not run."""
    path = EVAL_FILE if path is None else path
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def clear() -> None:
    _analog_eval_cached.cache_clear()
    _anomaly_cached.cache_clear()
