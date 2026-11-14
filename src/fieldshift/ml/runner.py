"""Rolling-origin experiment runner (docs/03-ML-SPEC.md §6-§8; D-68, D-83, D-93, D-107).

Plain words: for each test year 2016-2024 we (1) take only earlier years as training data, (2) pick the ridge
penalty using the last 30% of those training years as inner test years (fold-time features refit inside each inner
split), (3) fit the weather model M1 and its no-weather twin BNW, (4) predict the test year, and (5) compare with the
references B0 (training mean) and B2 (last year's value) on exactly the same rows. The 80% error range comes from
the inner-year errors (split conformal).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence

import numpy as np
import pandas as pd

from fieldshift.ml import evaluation as ev

FoldTransform = Callable[[pd.DataFrame, pd.Index], pd.DataFrame]
ALPHA_GRID = np.logspace(-5, 0, 13)  # D-110: Meroni et al. 2021 grid (lasso scale; ev.fit_ridge converts, D-146)


def add_precip_anom(df: pd.DataFrame, train_idx: pd.Index) -> pd.DataFrame:
    """precip_anom_pct = season rain vs the same unit and season's mean over the training rows only (D-66).

    The unit key is province_nso until the unit_id crosswalk exists (05-DATA-CONTRACTS §2, §4c).
    """
    out = df.copy()
    mean = df.loc[train_idx].groupby(["province_nso", "season"])["precip_sum_mm"].mean()
    key = pd.MultiIndex.from_frame(df[["province_nso", "season"]])
    out["precip_anom_pct"] = (df["precip_sum_mm"].to_numpy() / mean.reindex(key).to_numpy() - 1) * 100
    return out


def _tune(
    df: pd.DataFrame,
    train_idx: pd.Index,
    cols: list[str],
    alphas: Sequence[float] | np.ndarray,
    fold_transform: FoldTransform | None = None,
) -> tuple[float, np.ndarray]:
    """Penalty with the lowest inner-fold MSE (first in grid order on ties), and that penalty's inner residuals.

    Fold-time features are refit on each inner split's training rows (03-ML-SPEC §4), so an inner test year never
    enters its own rain normal.
    """
    years = df.loc[train_idx, "year"].to_numpy()
    folds = []
    for itr, ite in ev.inner_splits(years):
        tr, te = train_idx[itr], train_idx[ite]
        d = fold_transform(df, tr) if fold_transform else df
        # a test row without fold-time features (no past normal in this split) is not scored, as in the outer loop
        te = te[d.loc[te, cols].notna().all(axis=1).to_numpy()]
        folds.append((tr, te, d))
    best = None
    for a in alphas:
        res = []
        for tr, te, d in folds:
            model = ev.fit_ridge(d.loc[tr, cols].to_numpy(), d.loc[tr, "anom"].to_numpy(), alpha=a)
            res.append(d.loc[te, "anom"].to_numpy() - model.predict(d.loc[te, cols].to_numpy()))
        res = np.concatenate(res)
        mse = float(np.mean(res**2))
        if best is None or mse < best[1]:
            best = (a, mse, res)
    return best[0], best[2]


def run_rolling_origin(
    df: pd.DataFrame,
    weather_cols: Sequence[str],
    context_cols: Sequence[str],
    alphas: Sequence[float] | np.ndarray,
    test_years: Iterable[int] = ev.TEST_YEARS,
    fold_transform: FoldTransform | None = None,
) -> dict:
    """Run the outer rolling origin. df: one row per series and year with `anom` (non-null), features, series_id.

    fold_transform(df, train_idx) -> df adds fold-time features (e.g. add_precip_anom) from training rows only.
    Returns {"predictions": DataFrame (same rows only), "metrics": dict}.
    """
    if len(alphas) == 0:
        raise ValueError("a penalty grid is required (no default without a decision)")
    dup = df.duplicated(["series_id", "year"], keep=False)
    if dup.any():
        bad = df.loc[dup, ["series_id", "year"]].drop_duplicates().to_dict("records")
        raise ValueError(f"more than one row per series and year: {bad}")
    if df["anom"].isna().any():
        raise ValueError("rows without an anomaly (no normal) must be dropped before the run (03-ML-SPEC §3)")
    data = df.reset_index(drop=True)
    m1_cols = list(context_cols) + list(weather_cols)
    parts = []
    for t in test_years:
        train_idx = data.index[data["year"] < t]
        test_idx = data.index[data["year"] == t]
        if len(test_idx) == 0:
            continue
        d = fold_transform(data, train_idx) if fold_transform else data
        # a test row without fold-time features (no past normal) is not scored (03-ML-SPEC section 3)
        test_idx = test_idx[d.loc[test_idx, m1_cols].notna().all(axis=1).to_numpy()]
        if len(test_idx) == 0:
            continue
        a_m1, res_m1 = _tune(data, train_idx, m1_cols, alphas, fold_transform)
        a_bnw, _ = _tune(data, train_idx, list(context_cols), alphas, fold_transform)
        m1 = ev.fit_ridge(d.loc[train_idx, m1_cols].to_numpy(), d.loc[train_idx, "anom"].to_numpy(), alpha=a_m1)
        bnw = ev.fit_ridge(
            d.loc[train_idx, list(context_cols)].to_numpy(), d.loc[train_idx, "anom"].to_numpy(), alpha=a_bnw
        )
        q = ev.conformal_halfwidth(np.abs(res_m1), alpha=ev.INTERVAL_ALPHA)
        p_m1 = m1.predict(d.loc[test_idx, m1_cols].to_numpy())
        part = pd.DataFrame(
            {
                "series_id": d.loc[test_idx, "series_id"],
                "year": t,
                "y": d.loc[test_idx, "anom"],
                "m1": p_m1,
                "lo80": p_m1 - q,
                "hi80": p_m1 + q,
                "bnw": bnw.predict(d.loc[test_idx, list(context_cols)].to_numpy()),
                "b0": ev.predict_b0(d, train_idx, test_idx),
                "b2": ev.predict_b2(d, test_idx),
                "alpha_m1": a_m1,
                "alpha_bnw": a_bnw,
            },
            index=test_idx,
        )
        parts.append(part)
    pred = pd.concat(parts)
    lo_a, hi_a = min(alphas), max(alphas)
    per_year = pred.drop_duplicates("year")
    edge = {k: float(per_year[f"alpha_{k}"].isin([lo_a, hi_a]).mean()) for k in ("m1", "bnw")}
    keep = ev.same_rows({k: pred[k] for k in ("m1", "bnw", "b0", "b2")})
    pred = pred[keep]
    y, p = pred["y"], pred["m1"]
    metrics = {
        "rmse": ev.rmse(y, p),
        "mae": ev.mae(y, p),
        "r2_oos": ev.r2_oos(y, p),
        "skill_vs_b0": ev.skill_score(y, p, pred["b0"]),
        "skill_vs_b2": ev.skill_score(y, p, pred["b2"]),
        "skill_vs_bnw": ev.skill_score(y, p, pred["bnw"]),
        "coverage_80": ev.coverage(y, pred["lo80"], pred["hi80"]),
        "n_rows": len(pred),
        "n_test_years": int(pred["year"].nunique()),
        "alpha_at_edge": edge,  # share of test years whose chosen penalty is an end of the grid (D-110)
    }
    return {"predictions": pred, "metrics": metrics}
