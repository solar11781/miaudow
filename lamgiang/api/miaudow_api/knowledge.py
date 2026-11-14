"""Build the evidence passages of AI core 02 from the governed data layer (docs/07-ARCHITECTURE-AND-CONTRACTS.md).

Every passage restates something the rulebook, a cited source or a canonical file already says; none adds a finding.
Passages about years are generated from climate.json and hazards.json, so their numbers cannot drift from the data.
pipeline/build_canonical.py calls `build_passages` and writes data/canonical/passages.json; `evidence` reads it.

Validation status of a passage (contracts.ValidationStatus):
- VERIFIED: the team read the source and recorded where (page, table, article); `location` says where.
- DERIVED: our own arithmetic or our own method notes (location None for computations).
- PENDING_VERIFICATION: a catalog entry or a team note without a cited source.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .contracts import Passage, PassageKind, Text, ValidationStatus

MONTHS_VI = [
    "tháng 1",
    "tháng 2",
    "tháng 3",
    "tháng 4",
    "tháng 5",
    "tháng 6",
    "tháng 7",
    "tháng 8",
    "tháng 9",
    "tháng 10",
    "tháng 11",
    "tháng 12",
]
MONTHS_EN = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]
SEASON_VI = {"spring": "vụ Đông Xuân", "summer_autumn": "vụ Hè Thu", "autumn_winter": "vụ Thu Đông", "winter": "vụ Mùa"}
SEASON_EN = {
    "spring": "spring season",
    "summer_autumn": "summer-autumn season",
    "autumn_winter": "autumn-winter season",
    "winter": "winter season",
}
RULE_LABEL = {
    "heavy_rain": ("mưa lớn", "heavy rain"),
    "heat": ("nắng nóng", "heat"),
    "drought_rain_consecutive": (
        "hạn hán (phần lượng mưa), 2 tháng liền nhau",
        "drought (rain part), 2 months in a row",
    ),
    "drought_rain_any2": ("hạn hán (phần lượng mưa), 2 tháng bất kỳ", "drought (rain part), any 2 months"),
    "cold": ("rét hại", "damaging cold"),
}
NOT_FIELD = Text(
    vi="Đây là giá trị mô hình theo ô lưới NASA POWER, không phải số đo tại ruộng. Năm đã qua không phải dự báo.",
    en="These are NASA POWER grid model values, not field measurements. A past year is not a forecast.",
)
KIND_OF_SOURCE: dict[str, PassageKind] = {
    "R-A01": "regulation", "R-G06": "regulation", "R-G27": "regulation",
    "R-P02": "study", "R-P03": "study", "R-A10": "study", "R-E06": "study", "R-M03": "study", "R-B02": "study",
    "R-W15": "standard", "R-M01": "standard", "R-M02": "standard", "R-A15": "standard", "R-E12": "standard",
    "R-E13": "standard",
    "R-A18": "team_note", "R-C13": "team_note",
    "E-012": "model", "E-010": "computation", "E-019": "computation", "E-020": "computation", "E-022": "computation",
}  # fmt: skip
TEAM_METHOD = "team-method"  # data/rules/method.yaml statements that cite no source


# ---------------------------------------------------------------- number formatting


def fmt(value: float, decimals: int, lang: str) -> str:
    """Vietnamese: 2.030,5 (dot groups, decimal comma); English: 2,030.5."""
    s = f"{value:,.{decimals}f}"
    if lang == "vi":
        s = s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return s


def parse_number(text: str, lang: str) -> float:
    """Inverse of `fmt` (used by tests to read numbers back from passages)."""
    text = text.replace(".", "").replace(",", ".") if lang == "vi" else text.replace(",", "")
    return float(text)


def fv(value: float | None, decimals: int, lang: str) -> str:
    """A number, or plain words saying it is missing (a missing value is never shown as 0)."""
    if value is None:
        return "không có số liệu" if lang == "vi" else "no value"
    return fmt(value, decimals, lang)


def pct(share: float, lang: str) -> str:
    return fmt(round(share * 100.0, 1), 1, lang) + " %"


def months_text(months: list[int], lang: str) -> str:
    names = MONTHS_VI if lang == "vi" else MONTHS_EN
    return ", ".join(names[m - 1] for m in months)


def _p(pid, doc_id, source_id, kind, title, text, location, status, url=None) -> Passage:
    return Passage(
        passage_id=pid,
        doc_id=doc_id,
        source_id=source_id,
        kind=kind,
        title=title,
        text=text,
        location=location,
        validation_status=status,
        url=url,
    )


def _slug(text: str) -> str:
    import unicodedata

    plain = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    plain = plain.encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", plain).strip("-")


# ---------------------------------------------------------------- sources and datasets


def source_passages(catalog: dict) -> list[Passage]:
    out = []
    for s in catalog["sources"]:
        sid = s["id"]
        own = sid.startswith("E-")
        external = sid.startswith("X-")
        lim_vi = " ".join(x["vi"] for x in s["limitations"])
        lim_en = " ".join(x["en"] for x in s["limitations"])
        st = s.get("study_type") or {"vi": "chưa ghi", "en": "not recorded"}
        py = s.get("place_years") or {"vi": "chưa ghi", "en": "not recorded"}
        read_vi = s.get("read_status") or "tính toán của nhóm"
        read_en = s.get("read_status") or "the team's computation"
        text = Text(
            vi=f"{s['citation']['vi']}. Loại nguồn: {st['vi']}. Nơi và năm: {py['vi']}. Mức đã đọc: {read_vi}. "
            f"Giới hạn: {lim_vi}",
            en=f"{s['citation']['en']}. Kind of source: {st['en']}. Place and years: {py['en']}. Read: {read_en}. "
            f"Limits: {lim_en}",
        )
        status: ValidationStatus = "DERIVED" if own else ("PENDING_VERIFICATION" if external else "VERIFIED")
        out.append(
            _p(
                f"src-{sid.lower()}",
                sid,
                sid,
                KIND_OF_SOURCE.get(sid, "dataset"),
                Text(vi=f"Nguồn {sid}: {st['vi']}", en=f"Source {sid}: {st['en']}"),
                text,
                None if own else "Toàn bộ tài liệu (mô tả nguồn của nhóm)",
                status,
                s.get("url"),
            )
        )
    return out


STATUS_VI = {
    "INGESTED": "đã nạp vào ứng dụng",
    "PARTIAL": "mới nạp một phần",
    "CONTRACT_ONLY": "chưa nạp, mới có khung mô tả",
    "BLOCKED": "bị chặn",
}
STATUS_EN = {
    "INGESTED": "loaded into the app",
    "PARTIAL": "partly loaded",
    "CONTRACT_ONLY": "not loaded, only described",
    "BLOCKED": "blocked",
}


def dataset_passages(catalog: dict) -> list[Passage]:
    out = []
    for d in catalog["datasets"]:
        measured_vi = "là số đo tại ruộng" if d["is_field_measurement"] else "không phải số đo tại ruộng"
        measured_en = "is a field measurement" if d["is_field_measurement"] else "is not a field measurement"
        notes_vi = " ".join(n["vi"] for n in d["notes"])
        notes_en = " ".join(n["en"] for n in d["notes"])
        out.append(
            _p(
                f"dataset-{d['dataset_id'].replace('_', '-')}",
                d["dataset_id"],
                d["source_id"],
                "dataset",
                Text(vi=f"Bộ số liệu: {d['title']['vi']}", en=f"Dataset: {d['title']['en']}"),
                Text(
                    vi=f"{d['title']['vi']} ({d['provider']}). Trạng thái: {STATUS_VI[d['ingestion_status']]}. "
                    f"Thời gian: {d['temporal_coverage']}. Độ phân giải: {d['spatial_resolution']}. "
                    f"Cách dùng: {d['allowed_use']['vi']} Số liệu này {measured_vi}. {notes_vi}".strip(),
                    en=f"{d['title']['en']} ({d['provider']}). Status: {STATUS_EN[d['ingestion_status']]}. "
                    f"Time: {d['temporal_coverage']}. Resolution: {d['spatial_resolution']}. "
                    f"Use: {d['allowed_use']['en']} This data {measured_en}. {notes_en}".strip(),
                ),
                None,
                "DERIVED" if d["ingestion_status"] in ("INGESTED", "PARTIAL") else "UNAVAILABLE",
                d.get("source_url"),
            )
        )
    return out


# ---------------------------------------------------------------- plans (rotations.generated.json)


def _crop_label(season: dict, lang: str) -> str:
    variety = f" {season['variety']}" if season.get("variety") else ""
    return f"{season['crop_name'][lang]}{variety}"


def plan_passages(rotations: dict) -> list[Passage]:
    out: list[Passage] = []
    seen_risks: dict[str, list[str]] = {}
    risk_lines: dict[str, dict] = {}
    for p in rotations["plans"]:
        pid, code, src = p["id"], p["study_code"], p["source_ids"][0]
        name = p["name"]
        if p["seasons"] and p["seasons"][0]["sow_from"]:
            seq_vi = "; ".join(
                f"{SEASON_VI[s['season']]}: {_crop_label(s, 'vi')}, gieo {s['sow_from'][3:]}/{s['sow_from'][:2]}, "
                f"thu hoạch {s['harvest_from'][3:]}/{s['harvest_from'][:2]}"
                + (f" đến {s['harvest_to'][3:]}/{s['harvest_to'][:2]}" if s["harvest_to"] != s["harvest_from"] else "")
                for s in p["seasons"]
            )
            seq_en = "; ".join(
                f"{SEASON_EN[s['season']]}: {_crop_label(s, 'en')}, sown {s['sow_from']}, harvested {s['harvest_from']}"
                + (f" to {s['harvest_to']}" if s["harvest_to"] != s["harvest_from"] else "")
                for s in p["seasons"]
            )
            loc = "Bảng 9, 1 và 5"
        else:
            seq_vi = "; ".join(f"{SEASON_VI[s['season']]}: {_crop_label(s, 'vi')}" for s in p["seasons"])
            seq_vi += "; vụ Thu Đông: bỏ hoang. Bài báo không ghi ngày gieo và ngày thu hoạch"
            seq_en = "; ".join(f"{SEASON_EN[s['season']]}: {_crop_label(s, 'en')}" for s in p["seasons"])
            seq_en += "; autumn-winter: fallow. The paper gives no sowing or harvest dates"
            loc = "tr. 2-3"
        kind_vi = "cách làm quen của người dân (đối chứng)" if p["is_usual"] else "cơ cấu thử nghiệm"
        kind_en = "the farmers' usual practice (control)" if p["is_usual"] else "a tested structure"
        out.append(
            _p(
                f"plan-{pid}-overview",
                src,
                src,
                "study",
                Text(vi=f"Cơ cấu {code}: {name['vi']}", en=f"Plan {code}: {name['en']}"),
                Text(
                    vi=f"{code} là {kind_vi} ở {p['site']}, {p['trial_period']}. Các vụ: {seq_vi}.",
                    en=f"{code} is {kind_en} in {p['site']}, {p['trial_period']}. Seasons: {seq_en}.",
                ),
                loc,
                "VERIFIED",
            )
        )
        why = p["why"]
        out.append(
            _p(
                f"plan-{pid}-why",
                src,
                src,
                "study",
                Text(vi=f"Vì sao có cơ cấu {code} trong ứng dụng", en=f"Why plan {code} is in the app"),
                Text(
                    vi=" ".join(why[k]["vi"] for k in ("why", "evidence", "benefits", "gaps") if k in why),
                    en=" ".join(why[k]["en"] for k in ("why", "evidence", "benefits", "gaps") if k in why),
                ),
                "tr. 45, tr. 50" if src == "R-P02" else "tr. 2-3",
                "VERIFIED",
            )
        )
        out.extend(_money_passages(p))
        for line in p["risk_lines"]:
            slug = _slug(line["source_id"] + " " + line["location"].split("(")[0].split(", lời")[0])
            key = f"risk-{slug}"
            seen_risks.setdefault(key, []).append(code)
            risk_lines[key] = line
    for key, line in risk_lines.items():
        codes = ", ".join(seen_risks[key])
        out.append(
            _p(
                key,
                line["source_id"],
                line["source_id"],
                KIND_OF_SOURCE.get(line["source_id"], "study"),
                Text(vi=f"Điều cần lưu ý cho cơ cấu {codes}", en=f"Point to check for plans {codes}"),
                Text(
                    vi=f"{line['text']['vi']} (Áp dụng cho: {codes}.)",
                    en=f"{line['text']['en']} (Applies to: {codes}.)",
                ),
                line["location"],
                "VERIFIED",
            )
        )
    for src, ids in (("R-P02", ["usual", "cc1", "cc2", "cc3", "cc4"]), ("R-P03", ["usual_p03"])):
        plan = next(p for p in rotations["plans"] if p["id"] == ids[0])
        codes = ", ".join(next(p["study_code"] for p in rotations["plans"] if p["id"] == i) for i in ids)
        out.append(
            _p(
                f"limits-{src.lower()}",
                src,
                src,
                "study",
                Text(vi=f"Giới hạn của nghiên cứu {src} ({codes})", en=f"Limits of study {src} ({codes})"),
                Text(
                    vi="; ".join(x["vi"] for x in plan["limitations"]) + ".",
                    en="; ".join(x["en"] for x in plan["limitations"]) + ".",
                ),
                "tr. 44-45" if src == "R-P02" else "tr. 2-3",
                "VERIFIED",
            )
        )
    return out


def _money_passages(p: dict) -> list[Passage]:
    econ, code, pid = p["reported_economics"], p["study_code"], p["id"]
    if econ.get("text_only"):
        t = econ["text_only"]
        return [
            _p(
                f"plan-{pid}-money",
                econ["source_id"],
                econ["source_id"],
                "study",
                Text(vi=f"Tiền lãi đã báo cáo của {code}", en=f"Reported money result of {code}"),
                Text(
                    vi=f"{t['vi']} Cách tính: {econ['definition']['vi']}. Giá bán năm {econ['price_year']}; "
                    "một ô thử không lặp lại, không phải thu nhập dự kiến.",
                    en=f"{t['en']} Definition: {econ['definition']['en']}. Prices of {econ['price_year']}; one "
                    "unreplicated plot, not expected income.",
                ),
                t["location"],
                "VERIFIED",
            )
        ]
    seasons = {s["crop_key"]: s for s in p["seasons"]}
    parts_vi, parts_en = [], []
    for row in econ["per_crop"]:
        s = seasons[row["crop_key"]]
        parts_vi.append(
            f"{_crop_label(s, 'vi')} ({SEASON_VI[s['season']]}): lãi thuần {fmt(row['profit_value'], 0, 'vi')} "
            f"nghìn đồng/ha, tổng chi {fmt(row['cost_value'], 0, 'vi')} nghìn đồng/ha"
        )
        parts_en.append(
            f"{_crop_label(s, 'en')} ({SEASON_EN[s['season']]}): net profit {fmt(row['profit_value'], 0, 'en')} "
            f"thousand VND/ha, total cost {fmt(row['cost_value'], 0, 'en')} thousand VND/ha"
        )
    total = sum(r["profit_value"] for r in econ["per_crop"])
    money = _p(
        f"plan-{pid}-money",
        econ["source_id"],
        econ["source_id"],
        "study",
        Text(vi=f"Tiền lãi và chi phí đã báo cáo của {code}", en=f"Reported profit and cost of {code}"),
        Text(
            vi=f"Trong thử nghiệm P-02 (giá bán năm {econ['price_year']}): "
            + "; ".join(parts_vi)
            + f". Lãi thuần: Bảng 13 (tr. 50); tổng chi: Bảng 12 (vụ Đông Xuân), Bảng 4 (vụ Hè Thu), Bảng 8 (vụ Thu "
            f"Đông). Cách tính: {econ['definition']['vi']}. Một ô thử không lặp lại; không phải thu nhập dự kiến.",
            en=f"In the P-02 trial ({econ['price_year']} prices): "
            + "; ".join(parts_en)
            + f". Net profit: Table 13 (p. 50); total cost: Table 12 (spring), Table 4 (summer-autumn), Table 8 "
            f"(autumn-winter). Definition: {econ['definition']['en']}. One unreplicated plot; not expected income.",
        ),
        "Bảng 4, 8, 12 và 13 (tr. 50)",
        "VERIFIED",
    )
    year_total = _p(
        f"plan-{pid}-year-total",
        "E-022",
        "E-022",
        "computation",
        Text(
            vi=f"Cộng lãi cả năm của {code} (phép cộng của ứng dụng)", en=f"Whole-year profit sum of {code} (app's sum)"
        ),
        Text(
            vi=f"Cộng lãi thuần của {len(econ['per_crop'])} vụ của {code} trong P-02: {fmt(total, 0, 'vi')} nghìn "
            "đồng/ha. Đây là phép cộng của ứng dụng; bài báo không nói cả cơ cấu được trồng liền trên một ruộng. "
            "Giá năm 2020-21, không phải thu nhập dự kiến.",
            en=f"Sum of the net profits of the {len(econ['per_crop'])} seasons of {code} in P-02: "
            f"{fmt(total, 0, 'en')} thousand VND/ha. This is the app's sum; the paper does not say one field carried "
            "the whole plan. 2020-21 prices, not expected income.",
        ),
        None,
        "DERIVED",
    )
    return [money, year_total]


# ---------------------------------------------------------------- crops, rules, method


def crop_passages(rotations: dict) -> list[Passage]:
    out = []
    measure = {
        "R-W15": (
            "lượng nước phải tưới vào ruộng theo TCVN 8641:2011",
            "water to apply to the field under TCVN 8641:2011",
        ),
        "R-M02": (
            "lượng nước cây dùng theo FAO (Bảng 14, ước tính thô)",
            "crop water need per FAO (Table 14, rough estimate)",
        ),
    }
    for c in rotations["crops"]:
        by_source: dict[str, list] = {}
        for f in c["water_facts"]:
            by_source.setdefault(f["source_id"], []).append(f)
        for sid in ("R-W15", "R-M02"):
            facts = by_source.get(sid)
            name = c["name"]
            if facts:
                notes = list(dict.fromkeys(tuple(f["note"].values()) for f in facts if f.get("note")))
                vi = "; ".join(f"{f['scope']['vi']}: {f['value_text'].replace(',', '.')} {f['unit']}" for f in facts)
                en = "; ".join(f"{f['scope']['en']}: {f['value_text']} {f['unit']}" for f in facts)
                if notes:
                    vi += ". Ghi chú: " + " ".join(n[0] for n in notes)
                    en += ". Note: " + " ".join(n[1] for n in notes)
                text = Text(
                    vi=f"{name['vi']}, {measure[sid][0]}: {vi}. Hai nguồn TCVN và FAO đo hai thứ khác nhau nên không "
                    "so với nhau.",
                    en=f"{name['en']}, {measure[sid][1]}: {en}. TCVN and FAO measure different things and are never "
                    "compared.",
                )
                status: ValidationStatus = "VERIFIED"
            else:
                text = Text(
                    vi=f"{name['vi']}: nguồn này không ghi {measure[sid][0].split(' theo ')[0]}. Ứng dụng không tự "
                    "lấy số của cây khác thay vào.",
                    en=f"{name['en']}: this source lists no {measure[sid][1].split(' under ')[0].split(' per ')[0]}. "
                    "The app does not borrow another crop's value.",
                )
                status = "VERIFIED"
            out.append(
                _p(
                    f"water-{c['crop_id'].replace('_', '-')}-{'tcvn' if sid == 'R-W15' else 'fao'}",
                    sid,
                    sid,
                    "standard",
                    Text(
                        vi=f"Nước cho {name['vi'].lower()} ({'TCVN 8641' if sid == 'R-W15' else 'FAO'})",
                        en=f"Water for {name['en'].lower()} ({'TCVN 8641' if sid == 'R-W15' else 'FAO'})",
                    ),
                    text,
                    "Bảng mức tưới theo cây trồng" if sid == "R-W15" else "Bảng 14",
                    status,
                )
            )
    legumes = [c for c in rotations["crops"] if c["is_legume"]]
    others = [c for c in rotations["crops"] if not c["is_legume"]]
    out.append(
        _p(
            "legumes",
            "R-B01",
            "R-B01",
            "dataset",
            Text(vi="Cây nào là cây họ đậu?", en="Which crops are legumes?"),
            Text(
                vi="Theo trang loài của GRIN-Global (USDA), các cây họ Đậu (Fabaceae) trong các cơ cấu là: "
                + ", ".join(c["name"]["vi"].lower() for c in legumes)
                + ". Không thuộc họ Đậu: "
                + ", ".join(c["name"]["vi"].lower() for c in others)
                + ". Nguồn chỉ cho biết họ thực vật, không nói cây cố định bao nhiêu đạm trên ruộng.",
                en="Per the GRIN-Global (USDA) taxon pages, the legume crops (family Fabaceae) in the plans are: "
                + ", ".join(c["name"]["en"].lower() for c in legumes)
                + ". Not legumes: "
                + ", ".join(c["name"]["en"].lower() for c in others)
                + ". The source gives the plant family only, not how much nitrogen a crop fixes in a field.",
            ),
            "Trang loài của từng cây",
            "VERIFIED",
        )
    )
    return out


def _article_vi(article: str) -> str:
    return article.replace("Art.", "Điều")


def rule_passages(conditions: list[dict]) -> list[Passage]:
    out = []
    for r in conditions:
        out.append(
            _p(
                f"rule-{r['code'].replace('_', '-')}",
                "R-A01",
                "R-A01",
                "regulation",
                Text(
                    vi=f"Quy tắc {r['label']['vi'].lower()} ({_article_vi(r['article'])}, Quyết định 18/2021)",
                    en=f"Rule {r['label']['en'].lower()} ({r['article']}, Decision 18/2021)",
                ),
                Text(
                    vi=" ".join(r["rule_text"]["vi"].split())
                    + " Ứng dụng áp ngưỡng cấp độ 1 này cho giá trị NASA POWER của các năm đã qua (E-019); đó là "
                    "cách đọc máy móc, không phải cảnh báo chính thức.",
                    en=" ".join(r["rule_text"]["en"].split())
                    + " The app applies this level-1 threshold to NASA POWER values of past years (E-019); it is a "
                    "mechanical reading, not an official warning.",
                ),
                _article_vi(r["article"]),
                "VERIFIED",
            )
        )
    return out


def method_passages(method: dict) -> list[Passage]:
    out = []
    for term in method["explain_terms"]:
        sid = term["source_ids"][0] if term["source_ids"] else TEAM_METHOD
        out.append(
            _p(
                f"term-{term['key'].replace('_', '-')}",
                sid,
                sid,
                KIND_OF_SOURCE.get(sid, "dataset") if term["source_ids"] else "team_note",
                Text(vi=term["title"]["vi"], en=term["title"]["en"]),
                Text(vi=" ".join(term["text"]["vi"].split()), en=" ".join(term["text"]["en"].split())),
                "Trang phương pháp (data/rules/method.yaml)",
                "VERIFIED" if term["source_ids"] else "PENDING_VERIFICATION",
            )
        )
    out.append(
        _p(
            "method-limitations",
            TEAM_METHOD,
            TEAM_METHOD,
            "team_note",
            Text(
                vi="Giới hạn của cách tính thời tiết và mô hình", en="Limits of the weather computation and the model"
            ),
            Text(
                vi=" ".join(x["vi"] for x in method["limitations"]),
                en=" ".join(x["en"] for x in method["limitations"]),
            ),
            None,
            "DERIVED",
        )
    )
    rows: dict[str, dict] = {}
    for cell in method["coverage"]:
        rows.setdefault(cell["row_key"], {"crop": cell["crop"], "cells": []})["cells"].append(cell)
    axis = {
        "money": ("tiền lãi", "money"),
        "conditions": ("điều kiện thời tiết theo quy tắc", "weather rule conditions"),
        "rice_history": ("năng suất lúa của tỉnh", "province rice history"),
        "model": ("mô hình", "model"),
        "water_tcvn": ("nước tưới TCVN", "TCVN irrigation water"),
        "water_fao": ("nước cây dùng FAO", "FAO crop water"),
    }
    for key, row in rows.items():
        out.append(
            _p(
                f"coverage-{key.replace('_', '-')}",
                TEAM_METHOD,
                TEAM_METHOD,
                "team_note",
                Text(
                    vi=f"Ứng dụng có số liệu gì cho: {row['crop']['vi']}",
                    en=f"What the app covers for: {row['crop']['en']}",
                ),
                Text(
                    vi="; ".join(f"{axis[c['axis']][0]}: {c['text']['vi']}" for c in row["cells"]) + ".",
                    en="; ".join(f"{axis[c['axis']][1]}: {c['text']['en']}" for c in row["cells"]) + ".",
                ),
                None,
                "DERIVED",
            )
        )
    return out


# ---------------------------------------------------------------- model (E-012)


def model_passages(model: dict) -> list[Passage]:
    out = []
    status_vi = {
        "shown": "dự đoán được hiện cạnh số liệu thật",
        "not_shown": "dự đoán không được hiện vì chưa qua đủ các bước kiểm tra",
        "not_modeled": "không có mô hình cho vụ này",
    }
    status_en = {
        "shown": "predictions are shown next to the real values",
        "not_shown": "predictions are not shown because the model did not pass every gate",
        "not_modeled": "this season has no model",
    }
    for s in model["seasons"]:
        season = s["season"]
        gates = [g for g in model["gates"] if g["season"] == season]
        gv = " ".join(f"{g['gate']} {'đạt' if g['passed'] else 'không đạt'}: {g['detail']['vi']}" for g in gates)
        ge = " ".join(f"{g['gate']} {'passed' if g['passed'] else 'failed'}: {g['detail']['en']}" for g in gates)
        out.append(
            _p(
                f"model-{season.replace('_', '-')}",
                "E-012",
                "E-012",
                "model",
                Text(vi=f"Mô hình năng suất lúa {SEASON_VI[season]}", en=f"Rice yield model, {SEASON_EN[season]}"),
                Text(
                    vi=f"Lúa {SEASON_VI[season]} của Nghệ An: {status_vi[s['model_status']]}. "
                    f"Năm kiểm tra {model['test_years']['first']}-{model['test_years']['last']}. {gv} "
                    "Mô hình cho trung bình của cả tỉnh, không cho một ruộng; năm đã qua không phải dự báo.".replace(
                        "  ", " "
                    ),
                    en=f"Nghệ An {SEASON_EN[season]} rice: {status_en[s['model_status']]}. Test years "
                    f"{model['test_years']['first']}-{model['test_years']['last']}. {ge} The model is for the province "
                    "average, not one field; a past year is not a forecast.".replace("  ", " "),
                ),
                None,
                "DERIVED",
            )
        )
    rows = [r for r in model["metrics"] if r["subset"] == "unit:Nghe An" and r["model_id"] == "m1_ridge"]
    for r in rows:
        season = r["season"]
        out.append(
            _p(
                f"model-error-{season.replace('_', '-')}",
                "E-012",
                "E-012",
                "model",
                Text(
                    vi=f"Sai số của mô hình cho Nghệ An, {SEASON_VI[season]}",
                    en=f"Model error for Nghệ An, {SEASON_EN[season]}",
                ),
                Text(
                    vi=f"Trên {r['n_test_years']} năm kiểm tra, sai số trung bình tuyệt đối (MAE) của mô hình ridge cho "
                    f"độ lệch năng suất lúa {SEASON_VI[season]} của Nghệ An là {fmt(r['mae'], 3, 'vi')}, căn sai số bình "
                    f"phương trung bình (RMSE) là {fmt(r['rmse'], 3, 'vi')} (độ lệch tương đối của năng suất).",
                    en=f"Over {r['n_test_years']} test years, the ridge model's mean absolute error (MAE) for Nghệ An "
                    f"{SEASON_EN[season]} rice yield anomalies is {fmt(r['mae'], 3, 'en')}, root mean squared error "
                    f"(RMSE) {fmt(r['rmse'], 3, 'en')} (relative yield anomaly).",
                ),
                None,
                "DERIVED",
            )
        )
    return out


# ---------------------------------------------------------------- years (climate.json, hazards.json)


def climate_year_text(year: int, row: dict, lang: str) -> str:
    """One year of farmland-weighted NASA POWER values in plain words (numbers rounded as in climate.json)."""
    totals = row["monthly_rain_mm"]
    wettest = max(range(12), key=lambda m: -1 if totals[m] is None else totals[m])
    drought = row["drought_rain_months"]
    if lang == "vi":
        parts = [
            f"Năm {year}, vùng đất trồng Nghệ An (trung bình có trọng số đất trồng của 5 ô lưới NASA POWER):",
            f"tổng mưa năm {fmt(row['annual_rain_mm'], 1, 'vi')} mm;"
            if row["annual_rain_mm"] is not None
            else "tổng mưa năm: thiếu ngày, không tính;",
            f"tháng mưa nhiều nhất là {MONTHS_VI[wettest]} ({fv(totals[wettest], 1, 'vi')} mm);",
            "tháng thiếu mưa trên 50 % so với mức thường 1991-2020: "
            + (months_text(drought, "vi") if drought else "không có")
            + ";",
            f"số ngày nóng từ 35 °C: {fv(row['hot_days'], 1, 'vi')} ngày;",
            f"số ngày lạnh đến 13 °C: {fv(row['cold_days'], 1, 'vi')} ngày;",
            f"đợt khô dài nhất (mưa dưới 1 mm): {fv(row['longest_dry_spell_days'], 1, 'vi')} ngày.",
            NOT_FIELD.vi,
        ]
    else:
        parts = [
            f"Year {year}, Nghệ An farmland (farmland-weighted mean of 5 NASA POWER grid cells):",
            f"annual rain {fmt(row['annual_rain_mm'], 1, 'en')} mm;"
            if row["annual_rain_mm"] is not None
            else "annual rain: days missing, not computed;",
            f"wettest month {MONTHS_EN[wettest]} ({fv(totals[wettest], 1, 'en')} mm);",
            "months more than 50 % below the 1991-2020 normal: "
            + (months_text(drought, "en") if drought else "none")
            + ";",
            f"hot days at or above 35 °C: {fv(row['hot_days'], 1, 'en')};",
            f"cold days at or below 13 °C: {fv(row['cold_days'], 1, 'en')};",
            f"longest dry spell (rain below 1 mm): {fv(row['longest_dry_spell_days'], 1, 'en')} days.",
            NOT_FIELD.en,
        ]
    return " ".join(parts)


def hazard_year_text(year: int, shares: dict[str, float], lang: str) -> str:
    """Farmland share meeting each official rule in one year (E-019), in plain words."""
    i = 0 if lang == "vi" else 1
    body = "; ".join(f"{RULE_LABEL[r][i]} {pct(v, lang)}" for r, v in shares.items())
    if lang == "vi":
        return (
            f"Năm {year}, phần đất trồng Nghệ An đạt từng quy tắc cấp độ 1 của Quyết định 18/2021 trong thời gian có "
            f"cây của thử nghiệm P-02 trên ruộng (E-019): {body}. Đây là cách đọc máy móc trên giá trị ô lưới NASA "
            "POWER, không phải ghi nhận thiên tai chính thức; năm đã qua không phải dự báo."
        )
    return (
        f"Year {year}, share of Nghệ An farmland meeting each level-1 rule of Decision 18/2021 while a P-02 crop was in "
        f"the field (E-019): {body}. A mechanical reading of NASA POWER grid values, not an official disaster record; "
        "a past year is not a forecast."
    )


def year_passages(climate: dict, hazards: dict) -> list[Passage]:
    out = []
    for y in climate["years"]:
        row = climate["series"]["farmland_weighted"][str(y)]
        out.append(
            _p(
                f"climate-{y}",
                "nasa_power_daily",
                "R-N01",
                "computation",
                Text(vi=f"Thời tiết năm {y} ở Nghệ An (NASA POWER)", en=f"Weather of {y} in Nghệ An (NASA POWER)"),
                Text(vi=climate_year_text(y, row, "vi"), en=climate_year_text(y, row, "en")),
                None,
                "DERIVED",
                climate.get("source_url"),
            )
        )
    for i, y in enumerate(hazards["years"]):
        shares = {r: hazards["year_level"][r][i] for r in hazards["rules"]}
        out.append(
            _p(
                f"hazards-{y}",
                "e019_hazard_labels",
                "E-019",
                "computation",
                Text(vi=f"Rủi ro thiên tai theo quy tắc năm {y}", en=f"Rule-based disaster risk in {y}"),
                Text(vi=hazard_year_text(y, shares, "vi"), en=hazard_year_text(y, shares, "en")),
                None,
                "DERIVED",
            )
        )
    return out


# ---------------------------------------------------------------- documents (data/raw/documents/*/chunks.jsonl)


CHUNK_KEYS = {"doc_id", "source_id", "location", "text", "url", "license", "retrieved_at", "sha256_of_source"}


def document_passages(root: Path, known_sources: set[str]) -> list[Passage]:
    """Chunks of fetched documents, one passage per line. A line missing a contract key stops the build."""
    out = []
    for path in sorted((root / "data" / "raw" / "documents").glob("*/chunks.jsonl")):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            missing = CHUNK_KEYS - set(row)
            if missing:
                raise ValueError(f"{path}:{n}: chunk misses {sorted(missing)}")
            text = " ".join(str(row["text"]).split())
            sid = row["source_id"]
            out.append(
                _p(
                    f"doc-{_slug(row['doc_id'])}-{n}",
                    row["doc_id"],
                    sid,
                    KIND_OF_SOURCE.get(sid, "study"),
                    Text(vi=f"{row['doc_id']}, {row['location']}", en=f"{row['doc_id']}, {row['location']}"),
                    Text(vi=text, en=text),
                    row["location"],
                    "VERIFIED" if sid in known_sources else "PENDING_VERIFICATION",
                    row.get("url"),
                )
            )
    return out


# ---------------------------------------------------------------- all passages


def build_passages(
    *, climate: dict, hazards: dict, model: dict, rotations: dict, catalog: dict, root: Path
) -> list[Passage]:
    import yaml

    rules_dir = root / "data" / "rules"
    conditions = yaml.safe_load((rules_dir / "conditions.yaml").read_text(encoding="utf-8"))
    method = yaml.safe_load((rules_dir / "method.yaml").read_text(encoding="utf-8"))
    passages = (
        source_passages(catalog)
        + dataset_passages(catalog)
        + plan_passages(rotations)
        + crop_passages(rotations)
        + rule_passages(conditions)
        + method_passages(method)
        + model_passages(model)
        + year_passages(climate, hazards)
        + document_passages(root, {s["id"] for s in catalog["sources"]})
    )
    ids = [p.passage_id for p in passages]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise ValueError(f"duplicate passage ids: {dupes}")
    return passages
