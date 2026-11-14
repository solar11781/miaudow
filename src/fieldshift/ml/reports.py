"""Method-page reports (05-DATA-CONTRACTS section 5b ReportItem) for the register items that ask for one.

Plain words: each report is one short bilingual text with the numbers of one experiment, counted here from the
artifacts so that no number is typed by hand. Texts are drafts for the copy review (vi and en).
"""

from __future__ import annotations

import pandas as pd

from fieldshift.ml.primary_test import bilingual, decimal_text, find_row

NGHE_AN = "Nghe An"  # province_nso spelling of the training table
SEASONS = {  # NSO rice season -> (vi, en): the season labels of rules/method.yaml (R-D01, R-P02)
    "spring": ("vụ Đông Xuân", "spring"),
    "autumn": ("vụ Hè Thu", "summer-autumn"),
    "winter": ("vụ Mùa", "winter"),
}


def _count(n: int) -> tuple[str, str]:
    """(vi, en) of a whole number with the thousands separator of each language."""
    en = f"{n:,}"
    return en.replace(",", "."), en


def winter_claim_report(metrics: list[dict]) -> dict:
    """E-012 and E-018: winter M1 against the no-weather model in the primary run, and in how many sensitivity and
    robustness runs (E-018, E-008) the lower end of the 90% interval is below 0 or 0.000 at 3 decimals."""
    primary = find_row(metrics, "winter", "national")["skill_vs_bnw"]
    lows = [
        r["skill_vs_bnw"]["ci90_low"]
        for r in metrics
        if r["sensitivity"] is not None
        and (r["model_id"], r["season"], r["scheme"], r["subset"])
        == ("m1_ridge", "winter", "rolling_origin", "national")
    ]
    if not lows:
        raise ValueError("no sensitivity rows for winter M1 in metrics.json: run scripts/run_sensitivity.py first")
    below = sum(round(x, 3) < 0 for x in lows)
    zero = sum(round(x, 3) == 0 for x in lows)
    (v, e), (lv, le), (hv, he) = (decimal_text(primary[k]) for k in ("value", "ci90_low", "ci90_high"))
    zero_vi, zero_en = decimal_text(0.0)
    return {
        "id": "E-018",
        "title": bilingual(
            "Kết quả thời tiết của lúa vụ Mùa còn hẹp và chưa vững",
            "The winter rice weather result is narrow and fragile",
        ),
        "text": bilingual(
            f"Lúa vụ Mùa: trong lần kiểm tra chính, M1 hơn mô hình không dùng thời tiết {v} (khoảng tin cậy 90%: {lv} "
            f"đến {hv}); đầu dưới gần 0, nên kết quả còn hẹp. Trong {below} trong {len(lows)} lần chạy kiểm tra, đầu "
            f"dưới thấp hơn 0, và trong {zero} lần nữa bằng {zero_vi} khi làm tròn, nên kết quả chưa vững.",
            f"Winter rice: in the main test, M1's skill against the no-weather model was {e} (90% CI {le} to {he}); "
            f"the lower end is close to 0, so the result is narrow. In {below} of the {len(lows)} checking runs the "
            f"lower end is below 0, and in {zero} more it is {zero_en} after rounding, so the result is fragile.",
        ),
        "source_ids": ["E-012", "E-018", "E-008"],
    }


def setup_report() -> dict:
    """E-012, E-013, E-017: model settings chosen by the team, disclosed on the method page (EXPERIMENTS)."""
    return {
        "id": "E-012",
        "title": bilingual("Các lựa chọn khi dựng mô hình", "Choices made when setting up the models"),
        "text": bilingual(
            "Nhóm đặt sau khi đã chốt danh sách đặc trưng và trước mọi lần chạy mô hình: tương tác theo vụ lúa của M1 "
            "là chỉ báo vụ Đông Xuân nhân với từng đặc trưng thời tiết; trung bình khí hậu dài hạn của tỉnh là trung "
            "bình của từng đặc trưng thời tiết theo tỉnh và vụ, trên các năm trước năm kiểm tra (Lobell và Burke 2010; "
            "Ortiz-Bobea 2021). Thang tìm tham số của M2 (LightGBM: mặc định của LightGBM lùi và tiến một bước, và thang "
            "độ sâu của Meroni và cộng sự 2021) và của M3 (rừng ngẫu nhiên: Bảng 4 của Meroni và cộng sự 2021) do nhóm "
            "chọn.",
            "Set by the team after the features were frozen and before any model run: M1's rice-season interactions "
            "are the spring indicator times every weather feature; the province long-term climate means are, per "
            "province and season, the mean of every weather feature over the years before the test year (Lobell and "
            "Burke 2010; Ortiz-Bobea 2021). The search grids of M2 (LightGBM: the LightGBM defaults one step either "
            "side, and the depth grid of Meroni et al. 2021) and of M3 (random forest: Meroni et al. 2021 Table 4) "
            "were chosen by the team.",
        ),
        "source_ids": ["E-012", "E-013", "E-017", "R-M25", "R-M26", "R-M12", "R-M27"],
    }


def drought_readings_report(readings: pd.DataFrame) -> dict:
    """E-014 (D-58): in how many province seasons the readings "2 months in a row" and "any 2 months" differ.

    readings: one row per province, NSO rice season and year with the booleans `consecutive` and `any2`.
    """
    differ = readings["consecutive"] != readings["any2"]
    first, last = int(readings["year"].min()), int(readings["year"].max())

    def share(mask: pd.Series) -> tuple[str, str]:
        (kv, ke), (nv, ne) = _count(int(differ[mask].sum())), _count(int(mask.sum()))
        return f"{kv} trong {nv}", f"{ke} of {ne}"

    total = share(pd.Series(True, index=readings.index))
    seasons = [(SEASONS[s], share(readings["season"] == s)) for s in SEASONS if (readings["season"] == s).any()]
    by_vi = "; ".join(f"{vi}: {txt[0]}" for (vi, _), txt in seasons)
    by_en = "; ".join(f"{en} {txt[1]}" for (_, en), txt in seasons)
    nghe_an = share(readings["province_nso"] == NGHE_AN)
    return {
        "id": "E-014",
        "title": bilingual("Hai cách đọc quy tắc hạn hán", "Two readings of the drought rule"),
        "text": bilingual(
            'Quy tắc hạn hán tính các tháng mưa thiếu hơn 50% so với trung bình 1991-2020, "kéo dài từ 2 tháng đến 3 '
            'tháng"; chúng tôi tính theo hai cách: 2 tháng liền nhau, hoặc 2 tháng bất kỳ trong vụ. Trên lượng mưa '
            "trung bình theo đất trồng của từng tỉnh, trong khung thời gian các vụ lúa của Cục Thống kê, hai cách cho "
            f"kết quả khác nhau ở {total[0]} vụ của các tỉnh {first}-{last} ({by_vi}), và ở {nghe_an[0]} vụ của "
            "Nghệ An.",
            'The drought rule counts months with rain more than 50% below the 1991-2020 normal, "kéo dài từ 2 tháng '
            'đến 3 tháng" (lasting 2 to 3 months); we compute two readings: 2 months in a row, or any 2 months of the '
            "season. On each province's farmland-weighted rain, over the NSO rice season windows, the two readings "
            f"differ in {total[1]} province seasons {first}-{last} ({by_en}), and in {nghe_an[1]} Nghệ An seasons.",
        ),
        "source_ids": ["E-014"],
    }


def heavy_rain_check_report(heavy_rain_years: set[int], damage_years: set[int], years: range) -> dict:
    """E-016 (D-54): agreement counts between heavy-rain years (E-019) and years with DesInventar rice flood damage.

    Only counts are written: no DesInventar year or value is shown (D-54: never republish its data).
    """
    outside = sorted((heavy_rain_years | damage_years) - set(years))
    if outside:
        raise ValueError(f"years {outside} are outside the checked period {years.start}-{years.stop - 1}")
    both = len(heavy_rain_years & damage_years)
    rain_only, damage_only = len(heavy_rain_years - damage_years), len(damage_years - heavy_rain_years)
    neither = len(years) - both - rain_only - damage_only
    first, last = years.start, years.stop - 1
    return {
        "id": "E-016",
        "title": bilingual(
            "Kiểm tra năm mưa lớn với thiệt hại lúa được ghi nhận",
            "Heavy-rain years checked against recorded rice damage",
        ),
        "text": bilingual(
            f"Nghệ An {first}-{last}: năm có mưa lớn theo quy tắc chính thức (trên một phần đất trồng, khi cây của thử "
            "nghiệm ở ngoài ruộng) so với năm có diện tích lúa bị hư hại do lũ, lũ quét hoặc lụt trong các bản ghi "
            f"của DesInventar. Cả hai: {both} năm; chỉ mưa lớn: {rain_only}; chỉ có thiệt hại được ghi nhận: "
            f"{damage_only}; không có cả hai: {neither}; trùng nhau ở {both + neither} trong {len(years)} năm. "
            "DesInventar chỉ dùng để kiểm tra; các bản ghi của nó không được hiển thị.",
            f"Nghệ An {first}-{last}: years with heavy rain by the official rule (on part of the farmland, while a "
            "trial crop was in the field) against years with rice area damaged by a flood, flash flood or inundation "
            f"in the DesInventar records: both in {both} years; heavy rain only in {rain_only}; recorded "
            f"damage only in {damage_only}; neither in {neither}; they agree in {both + neither} of {len(years)} "
            "years. DesInventar is used for this check only; its records are not shown.",
        ),
        "source_ids": ["E-016", "R-A19", "E-019"],
    }
