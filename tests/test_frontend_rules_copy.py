"""The hand-written frontend copies of rule values (plans.ts, sources.ts) equal rules/*.yaml (queue item 64).

The TS files are read as text with one small regex per field, since the frontend has no YAML parser and the rules
files have no generator into frontend/src. Known differences are strict xfails that name both values, for a team
decision; no value is changed here.
"""

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PLANS_TS = (ROOT / "frontend" / "src" / "domain" / "plans.ts").read_text(encoding="utf-8")
SOURCES_TS = (ROOT / "frontend" / "src" / "domain" / "sources.ts").read_text(encoding="utf-8")
RULES = ROOT / "rules"
CROPS_YAML = {c["crop_id"]: c for c in yaml.safe_load((RULES / "crops.yaml").read_text(encoding="utf-8"))}
PLANS_YAML = {p["id"]: p for p in yaml.safe_load((RULES / "rotations.yaml").read_text(encoding="utf-8"))}
SOURCES_YAML = {s["id"]: s for s in yaml.safe_load((RULES / "sources.yaml").read_text(encoding="utf-8"))}

# The frontend uses its own short ids; these pairs are read off the two files (same crop, same plan).
CROP_IDS = {
    "rice": "rice",
    "blackbean": "black_bean",
    "sweetpotato": "sweet_potato",
    "peanut": "peanut",
    "mung": "mung_bean",
    "maize": "maize_grain",
    "chili": "chili",
    "soy": "soybean",
    "biomaize": "maize_biomass",
    "sesame": "black_sesame",
    "pumpkin": "pumpkin",
}
PLAN_IDS = {"cc5": "usual", "p03": "usual_p03", "cc1": "cc1", "cc2": "cc2", "cc3": "cc3", "cc4": "cc4"}
SEASONS = {"spring": "spring", "summer": "summer_autumn", "autumn": "autumn_winter"}


def norm(text: str) -> str:
    """Compare digits, not typography: en dash to hyphen, "6.500"/"6,500" to "6500", "about"/"khoảng" dropped."""
    text = text.replace("\N{EN DASH}", "-")
    text = re.sub(r"(?<=\d)[.,](?=\d{3}\b)", "", text)
    return re.sub(r"^(about|khoảng) ", "", text).strip()


def ts_crops() -> dict[str, dict]:
    head = re.compile(
        r"^  (\w+): \{\s*name: \{ vi: '([^']*)', en: '([^']*)' \},\s*family: '\w+',\s*legume: (true|false)", re.M
    )
    block = PLANS_TS[PLANS_TS.index("export const CROPS") : PLANS_TS.index("} as const satisfies")]
    matches = list(head.finditer(block))
    crops = {}
    for i, m in enumerate(matches):
        body = block[m.end() : matches[i + 1].start() if i + 1 < len(matches) else len(block)]
        rows = re.findall(r"tcvn\('([^']*)', '([^']*)'\)", body)
        rows += re.findall(r"value: \{ vi: '([^']*)', en: '([^']*)' \}", body)
        scopes = re.findall(r"scope: \{ vi: '([^']*)', en: '([^']*)' \}", body)
        fao = re.search(r"fao: '([^']*)'", body)
        crops[m[1]] = {
            "name": (m[2], m[3]),
            "legume": m[4] == "true",
            "tcvn": rows,
            "scopes": scopes,
            "fao": fao[1] if fao else None,
        }
    return crops


def ts_plans() -> dict[str, list[dict]]:
    crop = re.compile(
        r"key: '\w+',\s*crop: '(\w+)',\s*variety: '([^']*)',\s*season: '(\w+)',\s*sow: '([\d-]+)',\s*"
        r"harvest: '([\d-]+)',(?:\s*harvestNote: '[^']*',)?\s*days: '[^']*',\s*profit: (\d+),\s*cost: (\d+),\s*"
        r"price: (\d+),"
    )
    block = PLANS_TS[PLANS_TS.index("export const PLANS") :]
    heads = list(re.finditer(r"id: '(\w+)',\s*current:", block))
    plans = {}
    for i, h in enumerate(heads):
        body = block[h.end() : heads[i + 1].start() if i + 1 < len(heads) else len(block)]
        plans[h[1]] = [
            dict(zip(("crop", "variety", "season", "sow", "harvest", "profit", "cost", "price"), c, strict=True))
            for c in crop.findall(body)
        ]
    return plans


def ts_sources() -> dict[str, str | None]:
    heads = list(re.finditer(r"registerId: '([^']+)'", SOURCES_TS))
    out = {}
    for i, h in enumerate(heads):
        body = SOURCES_TS[h.end() : heads[i + 1].start() if i + 1 < len(heads) else len(SOURCES_TS)]
        url = re.search(r"url: '([^']+)'", body)
        out[h[1]] = url[1] if url else None
    return out


def pairs() -> list[tuple[str, object, object]]:
    """(field, frontend value, rules value) for every value both files hold."""
    out: list[tuple[str, object, object]] = []
    for key, c in ts_crops().items():
        y = CROPS_YAML[CROP_IDS[key]]
        out.append((f"crop.{key}.name", c["name"], (y["name"]["vi"], y["name"]["en"])))
        out.append((f"crop.{key}.legume", c["legume"], y["is_legume"]))
        # The frontend shows the spring rows of rice only (the trial's season); other crops' rows carry no season.
        tcvn = [f for f in y["water_facts"] if f["source_id"] == "R-W15" and f.get("season") in (None, "spring")]
        out.append(
            (
                f"crop.{key}.tcvn",
                [(norm(vi), norm(en)) for vi, en in c["tcvn"]],
                [(norm(f["value_text"]), norm(f["value_text"])) for f in tcvn],
            )
        )
        if c["scopes"]:
            out.append((f"crop.{key}.tcvn_scope", c["scopes"], [(f["scope"]["vi"], f["scope"]["en"]) for f in tcvn]))
        fao = [norm(f["value_text"]) for f in y["water_facts"] if f["source_id"] == "R-M02"]
        out.append((f"crop.{key}.fao", [norm(c["fao"])] if c["fao"] else [], fao))
    for pid, crops in ts_plans().items():
        y = PLANS_YAML[PLAN_IDS[pid]]
        econ = y["reported_economics"]
        if not crops:
            continue
        out.append((f"plan.{pid}.crops", [CROP_IDS[c["crop"]] for c in crops], [s["crop_id"] for s in y["seasons"]]))
        for c, s in zip(crops, y["seasons"], strict=True):
            k = s["crop_key"]
            variety = s["variety"]["vi"] if s["variety"] else None
            # the frontend writes "no variety" as an empty string
            out.append((f"plan.{pid}.{k}.variety", c["variety"] or None, variety))
            out.append((f"plan.{pid}.{k}.season", SEASONS[c["season"]], s["season"]))
            out.append((f"plan.{pid}.{k}.sow", c["sow"], s["sow_from"]))
            out.append((f"plan.{pid}.{k}.harvest", c["harvest"], s["harvest_from"]))
            for field in ("profit", "cost", "price"):
                out.append((f"plan.{pid}.{k}.{field}", c[field], norm(econ[f"{field}_per_crop"][k])))
    for rid, url in ts_sources().items():
        out.append((f"source.{rid}.registered", True, rid in SOURCES_YAML))
        if url and rid in SOURCES_YAML:
            out.append((f"source.{rid}.url", url, SOURCES_YAML[rid]["url"]))
    return out


# Differences found on 2026-11-15, left for a team decision (field: frontend value vs rules value).
KNOWN = {
    "source.R-P02.url": "intended (D-191: a page people can read vs the data address): sources.ts tapchi.vaas.vn article page vs sources.yaml vjol.info.vn download link",
    "source.R-N01.url": "intended (D-191: a page people can read vs the data address): sources.ts https://power.larc.nasa.gov/ vs sources.yaml .../api/temporal/daily/point",
    "source.R-N02.url": "intended (D-191: a page people can read vs the data address): sources.ts doi.org/10.5067/MODIS/MCD12C1.061 vs sources.yaml cmr.earthdata.nasa.gov granules",
    "source.R-D05.registered": "intended (spec section 8): rules/sources.yaml lists only the sources of API values; R-D05 credits data bundled in the frontend and is in docs/REFERENCES.md",
    "source.R-N11.registered": "intended (spec section 8): rules/sources.yaml lists only the sources of API values; R-N11 credits data bundled in the frontend and is in docs/REFERENCES.md",
    "source.R-N12.registered": "intended (spec section 8): rules/sources.yaml lists only the sources of API values; R-N12 credits the relief picture bundled in the frontend and is in docs/REFERENCES.md",
    "source.R-D04.registered": "intended (spec section 8): rules/sources.yaml lists only the sources of API values; R-D04 credits data bundled in the frontend and is in docs/REFERENCES.md",
}

PAIRS = pairs()


@pytest.mark.parametrize(
    ("ts_value", "rules_value"),
    [
        pytest.param(t, r, id=f, marks=pytest.mark.xfail(reason=KNOWN[f], strict=True) if f in KNOWN else ())
        for f, t, r in PAIRS
    ],
)
def test_frontend_value_equals_rules(ts_value: object, rules_value: object) -> None:
    assert ts_value == rules_value


def test_every_crop_plan_and_source_was_read() -> None:
    # Counts read off the two TS files by hand, so a regex that silently stops matching fails here.
    assert len(ts_crops()) == 11
    assert {k: len(v) for k, v in ts_plans().items()} == {"cc5": 3, "p03": 0, "cc1": 3, "cc2": 3, "cc3": 3, "cc4": 3}
    assert len(ts_sources()) == 16
