"""Method-page reports (05-DATA-CONTRACTS section 5b ReportItem) for the register items that ask for one.

Plain words: each report is one short bilingual text with the numbers of one experiment, counted here from the
artifacts so that no number is typed by hand. Labels come from rules/*.yaml. Texts are drafts for the copy review.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd
import yaml

from fieldshift.features.hazards import CLIM_YEARS, DROUGHT_DEFICIT
from fieldshift.ml.primary_test import app_season, bilingual, decimal_text
from fieldshift.paths import project_root

RULES = project_root() / "rules"
NGHE_AN = "Nghe An"  # province_nso spelling of the training table
WINTER_M1 = ("m1_ridge", "winter", "rolling_origin", "national")  # (model_id, season, scheme, subset)
DROUGHT_READINGS = ("drought_rain_consecutive", "drought_rain_any2")  # rule codes of rules/conditions.yaml (D-58)
# report kind -> (id, place among the reports of that id): run_primary_test.py writes E-010, then two E-012 reports
# (zero-weight cells, penalty), so this script's E-012 report is the third (ReportItem has no key field)
SLOTS = {
    "winter_claim": ("E-018", 0),
    "setup": ("E-012", 2),
    "drought_readings": ("E-014", 0),
    "heavy_rain_check": ("E-016", 0),
}


def _rules(name: str) -> object:
    return yaml.safe_load(Path(RULES, name).read_text(encoding="utf-8"))


def _mid(label: str) -> str:
    """A label inside a sentence: its first letter lower case ("Vụ Đông Xuân" -> "vụ Đông Xuân")."""
    return label[:1].lower() + label[1:]


def _count(n: int) -> tuple[str, str]:
    """(vi, en) of a whole number with the thousands separator of each language."""
    en = f"{n:,}"
    return en.replace(",", "."), en


def _winter_rows(metrics: list[dict]) -> tuple[dict, list[float]]:
    """The main-test skill of winter M1 against BNW and the lower ends of the checking runs."""
    rows = [r for r in metrics if (r["model_id"], r["season"], r["scheme"], r["subset"]) == WINTER_M1]
    main = [r["skill_vs_bnw"] for r in rows if r["sensitivity"] is None]
    if len(main) != 1:
        raise ValueError(f"{len(main)} main test rows for winter M1 in metrics.json, expected 1")
    lows = [r["skill_vs_bnw"]["ci90_low"] for r in rows if r["sensitivity"] is not None]
    if not lows:
        raise ValueError("no sensitivity rows for winter M1 in metrics.json: run scripts/run_sensitivity.py first")
    return main[0], lows


def winter_claim_report(metrics: list[dict]) -> dict:
    """E-012 and E-018: winter M1 against the no-weather model in the main test, and in how many sensitivity and
    robustness runs (E-018, E-008) the lower end of the 90% interval is below 0 or 0.000 at 3 decimals.

    "Fragile" needs a checking run at 0 or below; "narrow" needs a lower end above 0 that is smaller than the largest
    drop of the lower end in one checking run. Either failing raises, so the words always follow from the numbers."""
    primary, lows = _winter_rows(metrics)
    below = sum(round(x, 3) < 0 for x in lows)
    zero = sum(round(x, 3) == 0 for x in lows)
    if below + zero == 0:
        raise ValueError("no checking run has a lower end at 0 or below: the winter result is not fragile")
    low, drop = primary["ci90_low"], primary["ci90_low"] - min(lows)
    if not 0 < low < drop:
        raise ValueError(f"lower end {low} is not above 0 and below the largest drop {drop}: not narrow")
    (v, e), (lv, le), (hv, he) = (decimal_text(primary[k]) for k in ("value", "ci90_low", "ci90_high"))
    (dv, de), (zv, ze) = decimal_text(drop), decimal_text(0.0)
    return {
        "id": "E-018",
        "title": bilingual(
            "Kết quả thời tiết của lúa vụ Mùa còn hẹp và chưa vững",
            "The winter rice weather result is narrow and fragile",
        ),
        "text": bilingual(
            f"Lúa vụ Mùa: trong lần kiểm tra chính, M1 hơn mô hình không dùng thời tiết {v} (khoảng tin cậy 90%: {lv} "
            f"đến {hv}). Đầu dưới {lv} nhỏ hơn mức giảm lớn nhất của đầu dưới trong một lần chạy kiểm tra ({dv}), nên "
            f"kết quả còn hẹp. Ở {below} trong {len(lows)} lần chạy kiểm tra, đầu dưới thấp hơn 0, và ở {zero} lần nữa "
            f"bằng {zv} khi làm tròn, nên kết quả chưa vững.",
            f"Winter rice: in the main test, M1's skill against the no-weather model was {e} (90% CI {le} to {he}). "
            f"The lower end {le} is smaller than the largest drop of the lower end in one checking run ({de}), so the "
            f"result is narrow. In {below} of the {len(lows)} checking runs the lower end is below 0, and in {zero} "
            f"more it is {ze} after rounding, so the result is fragile.",
        ),
        "source_ids": ["E-012", "E-018", "E-008"],
    }


def setup_report() -> dict:
    """E-012, E-013, E-017: model settings chosen by the team, disclosed on the method page (EXPERIMENTS), each next
    to its source (R-M25, R-M26 with its warning, R-M12, R-M27)."""
    return {
        "id": "E-012",
        "title": bilingual("Các lựa chọn khi dựng mô hình", "Choices made when setting up the models"),
        "text": bilingual(
            "Nhóm đặt sau khi đã chốt danh sách đặc trưng và trước mọi lần chạy mô hình. M1 gộp mọi tỉnh vào một hồi "
            "quy ridge, với tương tác theo vụ lúa là chỉ báo vụ Đông Xuân nhân với từng đặc trưng thời tiết (Lobell và "
            "Burke 2010). Trung bình khí hậu dài hạn của tỉnh là trung bình của từng đặc trưng thời tiết theo tỉnh và "
            "vụ, trên các năm trước năm kiểm tra (Ortiz-Bobea 2021, tác giả cảnh báo rằng các trung bình như vậy có "
            "thể mang theo những khác biệt khác không đo được giữa các nơi). Thang tìm tham số của M2 (LightGBM: mặc "
            "định của LightGBM lùi và tiến một bước, theo tài liệu chỉnh tham số của LightGBM, và thang độ sâu của "
            "Meroni và cộng sự 2021) và của M3 (rừng ngẫu nhiên: Bảng 4 của Meroni và cộng sự 2021) do nhóm chọn.",
            "Set by the team after the features were frozen and before any model run. M1 pools all provinces in one "
            "ridge regression, with rice-season interactions: the spring indicator times every weather feature "
            "(Lobell and Burke 2010). The province long-term climate means are, per province and season, the mean of "
            "every weather feature over the years before the test year (Ortiz-Bobea 2021, who warns that such means "
            "can carry other, unmeasured differences between places). The search grids of M2 (LightGBM: the LightGBM "
            "defaults one step either side, from the LightGBM tuning documentation, and the depth grid of Meroni et "
            "al. 2021) and of M3 (random forest: Meroni et al. 2021 Table 4) were chosen by the team.",
        ),
        "source_ids": ["E-012", "E-013", "E-017", "R-M25", "R-M26", "R-M12", "R-M27"],
    }


def drought_readings_report(readings: pd.DataFrame) -> dict:
    """E-014 (D-58): in how many province seasons the farmland shares of the two readings differ (each reading per
    POWER cell, then weighted, D-72).

    readings: one row per province, NSO rice season and year (training-table rows) with the shares `consecutive`
    and `any2`.
    """
    differ = readings["consecutive"] != readings["any2"]
    first, last = int(readings["year"].min()), int(readings["year"].max())
    seasons = _rules("method.yaml")["season_labels"]
    rules = {r["code"]: r for r in _rules("conditions.yaml")}
    (cv, ce), (av, ae) = ((rules[c]["label"]["vi"], rules[c]["label"]["en"]) for c in DROUGHT_READINGS)
    pct, normal = f"{100 * DROUGHT_DEFICIT:.0f}%", f"{CLIM_YEARS[0]}-{CLIM_YEARS[1]}"

    def share(mask: pd.Series) -> tuple[str, str]:
        (kv, ke), (nv, ne) = _count(int(differ[mask].sum())), _count(int(mask.sum()))
        return f"{kv} trong {nv}", f"{ke} of {ne}"

    total, nghe_an = share(pd.Series(True, index=readings.index)), share(readings["province_nso"] == NGHE_AN)
    parts = [
        (seasons[app_season(s)]["label"], share(readings["season"] == s))
        for s in ("spring", "autumn", "winter")
        if (readings["season"] == s).any()
    ]
    by_vi = "; ".join(f"{_mid(label['vi'])}: {txt[0]}" for label, txt in parts)
    by_en = "; ".join(f"{_mid(label['en'])} {txt[1]}" for label, txt in parts)
    return {
        "id": "E-014",
        "title": bilingual("Hai cách đọc quy tắc hạn hán", "Two readings of the drought rule"),
        "text": bilingual(
            f'Quy tắc hạn hán được tính theo hai cách, "{cv}" và "{av}", với các tháng mưa thiếu hơn {pct} so với '
            f"trung bình {normal}. Mỗi cách được tính cho từng ô NASA POWER, rồi thành tỉ lệ đất trồng của tỉnh. Trên "
            f"các vụ lúa của các tỉnh có số liệu năng suất của Cục Thống kê {first}-{last} (các dòng của bảng huấn "
            f"luyện mô hình), trong khung thời gian của từng vụ, hai tỉ lệ khác nhau ở {total[0]} vụ ({by_vi}), và ở "
            f"{nghe_an[0]} vụ của Nghệ An.",
            f'The drought rule is computed in two readings, "{ce}" and "{ae}", with months of rain more than {pct} '
            f"below the {normal} normal. Each reading is computed per NASA POWER cell, then as a share of the "
            f"province's farmland. Over the province rice seasons with NSO rice yield data {first}-{last} (the rows "
            f"of the model's training table), within each season's window, the two shares differ in {total[1]} province seasons "
            f"({by_en}), and in {nghe_an[1]} Nghệ An seasons.",
        ),
        "source_ids": ["E-014", "R-A01"],
    }


def heavy_rain_check_report(heavy_rain_years: set[int], damage_years: set[int], years: range) -> dict:
    """E-016 (D-54): agreement counts between heavy-rain years (E-019) and years with DesInventar rice flood damage,
    with the agreement expected by chance from the same numbers of years of each kind.

    Only counts are written: no DesInventar year or value is shown (D-54: never republish its data).
    """
    outside = sorted((heavy_rain_years | damage_years) - set(years))
    if outside:
        raise ValueError(f"years {outside} are outside the checked period {years.start}-{years.stop - 1}")
    n, rain, dmg = len(years), len(heavy_rain_years), len(damage_years)
    both = len(heavy_rain_years & damage_years)
    rain_only, damage_only = rain - both, dmg - both
    neither = n - both - rain_only - damage_only
    chance_en = f"{(rain * dmg + (n - rain) * (n - dmg)) / n:.1f}"
    chance_vi = chance_en.replace(".", ",")
    first, last = years.start, years.stop - 1
    return {
        "id": "E-016",
        "title": bilingual(
            "Kiểm tra năm mưa lớn với thiệt hại lúa được ghi nhận",
            "Heavy-rain years checked against recorded rice damage",
        ),
        "text": bilingual(
            f"Nghệ An {first}-{last}. Năm mưa lớn: năm có tỉ lệ đất trồng đạt quy tắc mưa lớn chính thức, khi cây của "
            "thử nghiệm ở ngoài ruộng, lớn hơn 0 (cách hiểu của chúng tôi). Thiệt hại lúa do lũ được ghi nhận: chỉ tính "
            "các bản ghi lũ, lũ quét và lụt của DesInventar có diện tích lúa bị hư hại; các loại bản ghi khác, như "
            "lốc tố, lốc kèm mưa đá và bão, không được tính. "
            f"Cả hai: {both} năm; chỉ mưa lớn: {rain_only}; chỉ có thiệt hại được ghi nhận: {damage_only}; không có "
            f"cả hai: {neither}; trùng nhau ở {both + neither} trong {n} năm. Với cùng số năm mỗi loại, chỉ do ngẫu "
            f"nhiên đã có khoảng {chance_vi} trong {n} năm trùng nhau, nên phép kiểm tra này không xác nhận các năm "
            "mưa lớn. DesInventar chỉ dùng để kiểm tra; các bản ghi của nó không được hiển thị.",
            f"Nghệ An {first}-{last}. Heavy-rain year: a year whose share of farmland meeting the official heavy-rain "
            "rule, while a trial crop was in the field, is above 0 (our reading). Recorded rice flood damage: only the "
            "DesInventar flood, flash flood and inundation records with rice area damaged count; other record types, "
            f"such as cyclone, hailstorm and storm, are left out. Both in {both} years; heavy rain only in {rain_only}; recorded damage only in {damage_only}; "
            f"neither in {neither}; they agree in {both + neither} of {n} years. With the same numbers of years of "
            f"each kind, chance alone gives about {chance_en} of {n} years in agreement, so this check does not "
            "validate the heavy-rain years. DesInventar is used for this check only; its records are not shown.",
        ),
        "source_ids": ["E-016", "R-A19", "E-019"],
    }


def merge_reports(existing: list[dict], new: dict[str, dict]) -> list[dict]:
    """`existing` with each new report (by kind of SLOTS) in its slot: replaced where the slot is taken, else
    appended, so a changed title or text never adds a second copy."""
    out, seen, index = list(existing), Counter(), {}
    for i, r in enumerate(out):
        index[(r["id"], seen[r["id"]])] = i
        seen[r["id"]] += 1
    for kind, item in new.items():
        rid, place = SLOTS[kind]
        if item["id"] != rid:
            raise ValueError(f"report {kind} has id {item['id']}, its slot is {rid}")
        if (rid, place) in index:
            out[index[(rid, place)]] = item
            continue
        if seen[rid] != place:
            raise ValueError(
                f"slot {(rid, place)} of {kind}: {seen[rid]} {rid} reports present, so it would not land there"
            )
        index[(rid, place)] = len(out)
        out.append(item)
        seen[rid] += 1
    return out
