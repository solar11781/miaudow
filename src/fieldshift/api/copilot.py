"""The copilot, POST /api/copilot: member B's grounded question answering (branch feat/lamgiang-2,
lamgiang/api/miaudow_api/copilot.py and evidence.py), ported by D-172 with the protections of the explain endpoint.

Two engines share three read-only tools over our own data: a search of the passages (rules/copilot.yaml, the plans,
the official conditions and the model gates), the year shares of the official conditions (GET /api/past-years) and
the plans in the study order (rules/rotations.yaml).
- deterministic (the default, no key): fixed sentences from rules/copilot.yaml filled from the tool results.
- claude (only with ANTHROPIC_API_KEY): Claude calls the same tools and returns only ids, in a structured output
  (D-177): passages, plans and years the tools returned. The server drops unknown ids and shows the rest word for
  word from our data, each with its source, under one fixed line; no model-written sentence reaches the farmer. The
  question goes to the model escaped inside <question> tags and capped at QUESTION_MAX_CHARS.
Plans are never ranked, a past year is never a forecast, and the year card is not sent (D-169: it has no source
button). Member B's climate ML, satellite, map and dataset tools are not ported: D-169 hid the climate ML and the
other data have no register row or are not served by our API.
"""

from __future__ import annotations

import html
import itertools
import json
import math
import re
import unicodedata
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Literal

import anthropic
from pydantic import BaseModel, ConfigDict, StringConstraints, ValidationError

from fieldshift.api.caps import ModelCallsFullError
from fieldshift.api.explain import (
    BASE_URL,
    MAX_RETRIES,
    MODEL,
    THINKING,
    TIMEOUT_SECONDS,
    UNITS,
    ExplainError,
    numbers,
)
from fieldshift.engine.past_years import past_years
from fieldshift.engine.rules import (
    CopilotAnswers,
    gate_rows,
    load_card_texts,
    load_copilot_texts,
    load_crops,
    load_plans,
    load_prompt,
    load_sources,
)
from fieldshift.engine.schemas import FIRST_YEAR, LAST_YEAR, Contract, PlanId, SourceFacts, SourceId, Text

COPILOT_LIMIT = 2  # the explain endpoint's own limit (review of PR #43), so a burst never fills the farmer threads
# routine choice: 300 letters of 3 UTF-8 bytes stay under the 1024-byte body limit (tests/test_copilot.py)
QUESTION_MAX_CHARS = 300
MAX_TOOL_ROUNDS = 2  # routine choice: 3 calls of at most TIMEOUT_SECONDS stay under the page's 90 s wait (api.ts)
MAX_TOKENS = 2048  # routine choice: member B's 220-word technical answer as JSON, in Vietnamese
EFFORT = "low"  # the explain endpoint's effort; the tools do the work
SEARCH_LIMIT = 3  # member B's deterministic answer quotes the top 3 passages
# member B's search (frontend/src/features/ai/retrieve.ts, kept by the D-169 audit): BM25 with k1 1.4 and b 0.72, and
# an answer only when the top hit reaches both floors (its MIN_SCORE and MIN_COVERAGE)
K1, B = 1.4, 0.72
MIN_SCORE, MIN_COVERAGE = 4.5, 0.5
MAX_TOOLS_PER_ROUND = 3  # security review of PR #55: a prompt injection asked for about 100 tool calls in one turn
MAX_TOOL_RESULT_BYTES = 20_000  # security review of PR #55: about 3 plan lists; more is refused, so a loop cannot grow
# CLAUDE.md scientific boundaries (regional estimates only, never the farmer's own field, past years never a forecast,
# no ranking): forecast questions never reach the model, so a model answer with a future marker, a ranking or advice
# is refused. Matched on the lower-case text with its accents, so "sẽ" never matches "sẻ" (second pass of PR #55).
FIELD_CLAIMS = re.compile(
    r"(?<!\w)(sẽ|sắp|sang năm|năm sau|năm tới|vụ sau|vụ tới|mùa sau|mùa tới|tương lai|ngày mai|tối ưu|khuyên|"
    r"lựa chọn tốt|nên trồng|nên chọn|bạn nên|bác nên|tốt nhất|hay nhất|lời nhất|lãi nhất|chắc chắn|đảm bảo|"
    r"will|won't|going to|gonna|future|next (year|season|crop)|tomorrow|optimal|most profitable|recommend\w*|"
    r"advise\w*|can produce|should|best|guarantee\w*|"
    # third pass of PR #55: phrases only, since our own passages hold "hơn" and "your field"
    r"if you|nếu bác|nếu bạn|expect\w*|switch\w*|chuyển sang|kế tiếp|coming (seasons?|years?)|mất mùa|"
    r"hợp lý nhất|an toàn nhất|safest|safe bet|more than|less than|lãi hơn|ít hơn)(?!\w)"
)
# third pass of PR #55: yield, area and money words the explain list lacks; a number with one of them must have that
# very unit in a tool result, never only a unit-less token
STRICT_UNITS = frozenset(
    ("tonnes", "tonne", "tons", "ton", "tạ", "yến", "sào", "hectare", "hectares", "dollars", "dollar", "usd")
)
COPILOT_UNITS = UNITS | STRICT_UNITS


# security review of PR #55: numbers written in words escape the digit check, so each must also be in a tool result;
# "năm" (five, also "year") counts only before another number word or a unit (number_words)
NUMBER_WORDS = frozenset(
    [
        "một",
        "mốt",
        "hai",
        "ba",
        "bốn",
        "tư",
        "sáu",
        "bảy",
        "bẩy",
        "tám",
        "chín",
        "mười",
        "mươi",
        "lăm",
        "linh",
        "lẻ",
        "chục",
        "tá",
        "trăm",
        "nghìn",
        "ngàn",
        "vạn",
        "triệu",
        "tỷ",
        "tỉ",
        "nửa",
        "rưỡi",
        "gấp",
        "phẩy",
        "zero",
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "eleven",
        "twelve",
        "thirteen",
        "fourteen",
        "fifteen",
        "sixteen",
        "seventeen",
        "eighteen",
        "nineteen",
        "twenty",
        "thirty",
        "forty",
        "fifty",
        "sixty",
        "seventy",
        "eighty",
        "ninety",
        "hundred",
        "hundreds",
        "thousand",
        "thousands",
        "million",
        "millions",
        "billion",
        "billions",
        "half",
        "halves",
        "halved",
        "double",
        "doubled",
        "doubles",
        "twice",
        "triple",
        "tripled",
        "thrice",
        "quadruple",
        "quarter",
        "quarters",
        "third",
        "thirds",
        "dozen",
        "dozens",
        "percent",
    ]
)
FIVE = "năm"
# the unit spellings of the data (rules/crops.yaml, rules/copilot.yaml, the plan money units) as explain.UNITS spells them
UNIT_SPELLINGS = (("m³", "m3"), ("m²", "m2"), ("tấn/ha", "t/ha"), ("°C", "°c"))

Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=QUESTION_MAX_CHARS)]
Water = Literal["canal_end", "high_field", "reliable", "water_short"]
Status = Literal["grounded", "reference_only", "insufficient_evidence"]


class CopilotRequest(Contract):
    question: Question
    mode: Literal["simple", "technical"]
    lang: Literal["vi", "en"]
    water: Water | None = None


class Citation(Contract):
    passage_id: str
    source_id: SourceId
    title: Text
    location: str | None
    url: str | None


class AnswerCard(Contract):
    kind: Literal["plan", "passage"]
    ref_id: str
    title: Text


class ToolCall(Contract):
    tool: str
    input: dict[str, int]  # only a year: the model's own text never reaches the page (security review of PR #55)
    ok: bool


class NumberCheck(Contract):
    checked: int
    unverified: list[str]


class CopilotResponse(Contract):
    status: Status
    engine: Literal["claude", "deterministic"]
    model: str | None
    answer: str
    citations: list[Citation]
    cards: list[AnswerCard]
    tool_trace: list[ToolCall]
    numbers: NumberCheck
    missing_information: list[Text]


class CopilotError(ExplainError):
    """No usable model answer; the route answers a generic 502 and logs str(self) only (no question, text or key)."""

    def __init__(self, cause: str, status: int | None, stop_reason: str | None, request_id: str | None) -> None:
        Exception.__init__(
            self, f"copilot failed: {cause} status={status} stop_reason={stop_reason} request_id={request_id}"
        )


@dataclass(frozen=True)
class Passage:
    id: str
    source_id: SourceId
    keys: str
    title: Text
    text: Text


@dataclass(frozen=True)
class Corpus:
    passages: list[Passage]
    accented: _Bm25
    plain: _Bm25
    sources: dict[SourceId, SourceFacts]
    answers: CopilotAnswers
    rule_labels: dict[str, Text]
    years: dict[int, dict[str, str | None]]  # year -> rule code -> whole percent as shown by /api/past-years
    year_sources: list[SourceId]
    plans: list[dict[str, object]]  # what the list_plans tool returns, per language below
    plan_names: dict[PlanId, Text]
    system: str  # rules/prompts/copilot.md


# ---------------------------------------------------------------- search (port of member B's normalize.ts, retrieve.ts)


def normalize(text: str) -> str:
    """Lower case without diacritics (đ -> d) or punctuation, so "hạn hán", "han han" and "HẠN" match."""
    s = "".join(ch for ch in unicodedata.normalize("NFD", text) if not unicodedata.category(ch).startswith("M"))
    s = re.sub(r"[^a-z0-9\s]", " ", s.replace("đ", "d").replace("Đ", "d").lower())
    return re.sub(r"\s+", " ", s).strip()


def has_diacritics(text: str) -> bool:
    return any(unicodedata.category(ch) == "Mn" for ch in unicodedata.normalize("NFD", text)) or "đ" in text.lower()


def _keep_accents(text: str) -> str:
    s = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in unicodedata.normalize("NFC", text).lower())
    return re.sub(r"\s+", " ", s).strip()


# member B's farmer words mapped to one key term (normalize.ts SYNONYMS)
SYNONYMS = [
    (re.compile(r"\b(loi|lai|tien|thu nhap|lo lai|kiem duoc|profit|income|earn|money)\b"), "k_lai"),
    (re.compile(r"\b(han|kho han|thieu nuoc|drought|dry|khong mua)\b"), "k_han"),
    (re.compile(r"\b(nang suat|san luong|yield)\b"), "k_nangsuat"),
    (re.compile(r"\b(nang nong|heat|hot)\b"), "k_nong"),
    (re.compile(r"\b(ret|lanh|ret hai|cold)\b"), "k_ret"),
    (re.compile(r"\b(mua lon|mua to|lu|ngap|heavy rain|flood)\b"), "k_mualon"),
    (re.compile(r"\b(nuoc|tuoi|irrigation|water)\b"), "k_nuoc"),
    (re.compile(r"\b(dat|do am|soil|nito|dam)\b"), "k_dat"),
    (re.compile(r"\b(du doan|mo hinh|model|predict|prediction|hoc may|machine learning)\b"), "k_mohinh"),
    (re.compile(r"\b(nasa|ve tinh|satellite|power|modis)\b"), "k_nasa"),
    (re.compile(r"\b(nguon|source)\b"), "k_nguon"),
    (re.compile(r"\b(lac|dau phong|peanut|groundnut)\b"), "k_lac"),
    (re.compile(r"\b(ngo|bap|maize|corn)\b"), "k_ngo"),
    (re.compile(r"\b(lua|thoc|rice|paddy)\b"), "k_lua"),
]
STOP = frozenset(
    [
        "da",
        "di",
        "nay",
        "roi",
        "se",
        "dang",
        "tu",
        "ra",
        "len",
        "thi",
        "ma",
        "vay",
        "sao",
        "la",
        "co",
        "khong",
        "cua",
        "va",
        "cho",
        "nha",
        "toi",
        "minh",
        "the",
        "nao",
        "bao",
        "nhieu",
        "gi",
        "o",
        "trong",
        "duoc",
        "nhu",
        "mot",
        "cac",
        "nhung",
        "voi",
        "a",
        "an",
        "is",
        "are",
        "what",
        "how",
        "of",
        "in",
        "to",
        "do",
        "does",
        "my",
        "i",
        "and",
        "for",
        "it",
        "be",
    ]
)
# member B's scope guard (evidence.py GUARDS): today's prices and a "best" plan are never answered from evidence
GUARD = re.compile(
    r"\b(gia .*(hom nay|bay gio|hien nay|hien tai)|(hom nay|bay gio|hien nay).* gia|price today|current price|"
    r"tot nhat|hay nhat|loi nhat|xep hang|nen chon|chon giup|best|rank|ranking|which plan should)\b"
)


def tokens(text: str, accented: bool) -> list[str]:
    plain = normalize(text)
    keys = [key for rx, key in SYNONYMS if rx.search(plain)]
    words = (_keep_accents(text) if accented else plain).split(" ")
    return [w for w in words if len(w) > 1 and normalize(w) not in STOP] + keys


class _Bm25:
    def __init__(self, passages: list[Passage], accented: bool) -> None:
        self.tf: list[Counter[str]] = []
        for p in passages:
            doc = f"{p.title['vi']} {p.title['en']} {p.title['vi']} {p.text['vi']} {p.text['en']} {p.keys} {p.keys}"
            self.tf.append(Counter(tokens(doc, accented)))
        self.df = Counter(t for tf in self.tf for t in tf)
        self.n = len(passages)
        self.avg = sum(sum(tf.values()) for tf in self.tf) / max(1, self.n)

    def ranked(self, query: list[str]) -> list[tuple[float, float, int]]:
        """(score, coverage, index) of every passage with a score, best first."""
        out = []
        for i, tf in enumerate(self.tf):
            score, matched, length = 0.0, 0, sum(tf.values())
            for t in query:
                f = tf.get(t)
                if f:
                    matched += 1
                    idf = math.log(1 + (self.n - self.df[t] + 0.5) / (self.df[t] + 0.5))
                    score += idf * (f * (K1 + 1)) / (f + K1 * (1 - B + B * length / self.avg))
            if score > 0:
                out.append((score, matched / len(query), i))
        return sorted(out, key=lambda r: (-r[0], r[2]))


def search(corpus: Corpus, query: str) -> list[Passage]:
    """The top passages, or none when the best match is too weak or the guard applies (member B's abstention)."""
    if GUARD.search(normalize(query)):
        return []
    accented = has_diacritics(query)
    terms = list(dict.fromkeys(tokens(query, accented)))
    if not terms:
        return []
    ranked = (corpus.accented if accented else corpus.plain).ranked(terms)
    if not ranked or ranked[0][0] < MIN_SCORE or ranked[0][1] < MIN_COVERAGE:
        return []
    return [corpus.passages[i] for _, _, i in ranked[:SEARCH_LIMIT]]


# ---------------------------------------------------------------- the corpus, read once at start


def _both(text: str) -> Text:
    return {"vi": text, "en": text}


def _written(number: str, lang: str) -> str:
    """A rules-file number ("25,980", English style) as Vietnamese writes it ("25.980"); the same number."""
    return number.translate(str.maketrans(",.", ".,")) if lang == "vi" else number


def load_corpus(root: Path) -> Corpus:
    texts = load_copilot_texts(root)
    sources = load_sources(root)
    crops = load_crops(root)
    plans = load_plans(root)
    passages = [Passage(p.id, p.source_id, p.keys, p.title, p.text) for p in texts.passages]
    tool_plans: list[dict[str, object]] = []
    for plan in plans:
        money = plan.reported_economics
        parts = {
            lang: ", ".join(
                f"{crops[s.crop_id].name[lang]} {_written(money.profit_per_crop[s.crop_key], lang)}"
                for s in plan.seasons
                if s.crop_key in money.profit_per_crop
            )
            for lang in ("vi", "en")
        }
        if money.text_only is not None:
            text: Text = money.text_only
        else:
            unit = money.unit or _both("")
            text = {
                lang: texts.answers.plan_money[lang].format(unit=unit[lang], parts=parts[lang]) for lang in ("vi", "en")
            }
        keys = " ".join(f"{crops[s.crop_id].name['vi']} {crops[s.crop_id].name['en']}" for s in plan.seasons)
        passages.append(Passage(f"plan-{plan.id}", money.source_id, f"{plan.id} {keys} lai co cau", plan.name, text))
        tool_plans.append(
            {
                "plan_id": plan.id,
                "name": plan.name,
                "is_usual": plan.is_usual,
                "site": plan.site,
                "trial_period": plan.trial_period,
                "money": text,
                "money_definition": money.definition,
                "source_id": money.source_id,
                "limitations": plan.limitations,
            }
        )
    shown = past_years("nghe_an", root)
    for rule in shown.rules:
        rule_passage = Passage(
            f"rule-{rule.code.replace('_', '-')}",
            rule.threshold_source_id,
            f"{rule.label['vi']} {rule.label['en']} nguong",
            rule.label,
            rule.rule_text,
        )
        passages.append(rule_passage)
    seasons = load_card_texts(root).season_labels
    for gate in gate_rows(root):
        if gate.gate == "G2":
            label = seasons[gate.season].label
            title: Text = {lang: texts.answers.model_title[lang].format(season=label[lang]) for lang in ("vi", "en")}
            keys = f"{label['vi']} {label['en']} mo hinh du doan model skill"
            passages.append(Passage(f"model-{gate.season}", gate.source_ids[0], keys, title, gate.detail))
    years = {y.year: {code: (v.value if v else None) for code, v in y.shares.items()} for y in shown.years}
    year_sources = [shown.rules[0].threshold_source_id, *shown.rules[0].values_source_ids, shown.rules[0].computed_by]
    missing = {p.source_id for p in passages} - set(sources) | set(year_sources) - set(sources)
    if missing:
        raise ValueError(f"rules/copilot.yaml: source ids not in rules/sources.yaml: {sorted(missing)}")
    return Corpus(
        passages=passages,
        accented=_Bm25(passages, accented=True),
        plain=_Bm25(passages, accented=False),
        sources=sources,
        answers=texts.answers,
        rule_labels={r.code: r.label for r in shown.rules},
        years=years,
        year_sources=year_sources,
        plans=tool_plans,
        plan_names={p.id: p.name for p in plans},
        system=load_prompt(root, PROMPT),
    )


# ---------------------------------------------------------------- tools (read-only, over our own data)


def _lang(value: object, lang: str) -> object:
    """A tool result in one language: every {vi, en} pair becomes its `lang` text."""
    if isinstance(value, dict):
        if set(value) == {"vi", "en"}:
            return value[lang]
        return {k: _lang(v, lang) for k, v in value.items()}
    if isinstance(value, list):
        return [_lang(v, lang) for v in value]
    return value


def tool_search(corpus: Corpus, query: str, lang: str) -> dict[str, object]:
    hits = search(corpus, query[:QUESTION_MAX_CHARS])
    return {
        "abstained": not hits,
        "passages": [
            {"passage_id": p.id, "source_id": p.source_id, "title": p.title[lang], "text": p.text[lang]} for p in hits
        ],
    }


def tool_year(corpus: Corpus, year: int, lang: str) -> dict[str, object]:
    if year not in corpus.years:
        raise ValueError(f"year {year} is not a past year of the app ({FIRST_YEAR}-{LAST_YEAR})")
    return {
        "year": year,
        "share_of_farmland": {
            corpus.rule_labels[code][lang]: None if share is None else f"{share}%"
            for code, share in corpus.years[year].items()
        },
        "source_ids": corpus.year_sources,
        "note": corpus.answers.year_note[lang],
    }


def tool_plans(corpus: Corpus, lang: str) -> dict[str, object]:
    return {
        "plans": _lang(corpus.plans, lang),
        "rule": "Plans are listed in the study order. Never rank, score or recommend one.",
    }


def run_tool(corpus: Corpus, name: str, args: object, lang: str) -> dict[str, object]:
    if not isinstance(args, dict):
        raise ValueError("tool input is not an object")
    if name == "search_evidence" and isinstance(args.get("query"), str):
        return tool_search(corpus, args["query"], lang)
    if name == "year_conditions" and type(args.get("year")) is int:
        return tool_year(corpus, args["year"], lang)
    if name == "list_plans":
        return tool_plans(corpus, lang)
    raise ValueError(f"unknown tool or bad input: {name}")


TOOLS = [
    {
        "name": "search_evidence",
        "description": "Search the app's evidence passages (study results with their limits, official rules, "
        "standards, model test results). Returns passages with ids; abstained=true means nothing relevant was found.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search words, Vietnamese or English."}},
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "year_conditions",
        "description": "For one past year, the share of Nghệ An farmland that met each official hazard condition. "
        "NASA POWER grid values, never field measurements, never a forecast.",
        "input_schema": {
            "type": "object",
            "properties": {"year": {"type": "integer"}},
            "required": ["year"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_plans",
        "description": "The crop plans of the studies in the study order, with the study's money values, their "
        "definition, source and limits. Never rank them.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]

TOOL_NAMES = frozenset(t["name"] for t in TOOLS)

PROMPT = "copilot"  # rules/prompts/copilot.md: member B's SYSTEM without its climate ML, map rules and numbers


# ---------------------------------------------------------------- number check

Number = tuple[str, str, str]  # (sign, digits as written, unit word), as explain.numbers reads them


def _leaves(value: object) -> list[int | str]:
    """The strings and integers of a tool result, dict keys included (the year tool keys its shares by rule label)."""
    if isinstance(value, bool) or value is None:
        return []
    if isinstance(value, int | str):
        return [value]
    if isinstance(value, dict):
        return [x for k, v in value.items() for x in (*_leaves(k), *_leaves(v))]
    if isinstance(value, list):
        return [x for v in value for x in _leaves(v)]
    return []


def _units_spelled(text: str) -> str:
    for spelling, unit in UNIT_SPELLINGS:
        text = text.replace(spelling, unit)
    return text


def known_numbers(value: object) -> set[Number]:
    """Every whole number token of a tool result with its unit, as written: its JSON integers and the numbers of its
    strings. A piece of a larger number or of a range is no token, so 6 is not in 6.500-7.500 (review of PR #55)."""
    found: set[Number] = set()
    for item in _leaves(value):
        if isinstance(item, int):
            found.add(("-" if item < 0 else "", str(abs(item)), ""))
        else:
            found |= set(numbers(_units_spelled(item), COPILOT_UNITS))
    return found


def check_numbers(text: str, known: set[Number]) -> NumberCheck:
    """The shown text's numbers that are not a token, with the same sign and unit, of the data it was built from."""
    found = numbers(_units_spelled(text), COPILOT_UNITS)
    return NumberCheck(checked=len(found), unverified=[f"{s}{d}" for s, d, u in found if (s, d, u) not in known])


def number_words(text: str) -> set[str]:
    words = _keep_accents(text).split()
    found = set(words) & NUMBER_WORDS
    if any(w == FIVE and (nxt in NUMBER_WORDS or nxt in UNITS) for w, nxt in itertools.pairwise([*words, ""])):
        found.add(FIVE)
    return found


# ---------------------------------------------------------------- deterministic engine (member B's)


FORECAST_WORDS = (
    "ngay mai", "tuan sau", "tuan toi", "thang sau", "nam sau", "nam toi", "mua toi", "vu toi", "du bao", "sap toi",
    "tomorrow", "next week", "next month", "next year", "next season", "forecast",
)  # fmt: skip
PLAN_WORDS = (
    "nen trong", "trong gi", "trong cay gi", "cach trong", "co cau", "phuong an", "luan canh", "nhung cach",
    "what to grow", "what should i grow", "which crop", "crop plan", "rotation", "plans",
)  # fmt: skip
YEAR = re.compile(r"\b(19\d\d|20\d\d)\b")  # member B's YEAR_RE
# CLAUDE.md: regional estimates only, never the asker's own field (last pass of PR #55), matched without accents
OWN_FIELD = re.compile(r"\b(ruong (nha |cua )?(toi|minh|em|tao)|my (own )?(field|farm|plot|land|paddy))s?\b")


def intent(question: str) -> str:
    q = f" {normalize(question)} "
    if OWN_FIELD.search(q):
        return "own_field"
    if any(f" {w} " in q for w in FORECAST_WORDS):
        return "forecast"
    if any(f" {w} " in q for w in PLAN_WORDS):
        return "plans"
    if YEAR.search(question):
        return "year"
    return "evidence"


def _citation(corpus: Corpus, passage_id: str, source_id: SourceId) -> Citation:
    facts = corpus.sources[source_id]
    return Citation(passage_id=passage_id, source_id=source_id, title=facts.citation, location=None, url=facts.url)


def _clip(text: str, limit: int = 320) -> str:
    """Member B's clip: a long passage is cut at a sentence or word end; the citation names the full source."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("; "))
    return (cut[: end + 1] if end > limit // 2 else cut[: cut.rfind(" ")]).rstrip() + " …"


def _response(
    status: Status,
    answer: str,
    known: set[float],
    citations: list[Citation] | None = None,
    cards: list[AnswerCard] | None = None,
    trace: list[ToolCall] | None = None,
) -> CopilotResponse:
    """An answer the server writes from our data (the extractive answer names the model that picked it, D-177)."""
    return CopilotResponse(
        status=status,
        engine="deterministic",
        model=None,
        answer=answer,
        citations=citations or [],
        cards=cards or [],
        tool_trace=trace or [],
        numbers=check_numbers(answer, known),
        missing_information=[],
    )


def _year_block(corpus: Corpus, year: int, lang: str) -> tuple[list[str], dict[str, object]]:
    """The fixed year lines (rules/copilot.yaml) filled from GET /api/past-years, and the tool data behind them."""
    said = corpus.answers
    lines = [said.year_head[lang].format(year=year)]
    for code, share in corpus.years[year].items():
        lines.append(f"• {corpus.rule_labels[code][lang]}: {f'{share}%' if share else said.no_value[lang]}")
    lines.append(said.year_note[lang])
    return lines, tool_year(corpus, year, lang)


def _year_citations(corpus: Corpus, year: int) -> list[Citation]:
    return [_citation(corpus, f"year-{year}-{sid}", sid) for sid in corpus.year_sources]


def fixed_only(req: CopilotRequest) -> bool:
    """A forecast, own-field, ranking or today's-price question gets a fixed answer and never reaches the model
    (security passes of PR #55)."""
    return intent(req.question) in ("forecast", "own_field") or GUARD.search(normalize(req.question)) is not None


def deterministic(req: CopilotRequest, corpus: Corpus) -> CopilotResponse:
    lang, said = req.lang, corpus.answers
    kind = intent(req.question)
    if kind in ("forecast", "own_field"):  # the fixed answers of rules/copilot.yaml with the same names
        return _response("insufficient_evidence", getattr(said, kind)[lang], set())
    if kind == "plans":
        data = tool_plans(corpus, lang)
        lines = [said.plans_head[lang], *(f"• {p['name'][lang]}" for p in corpus.plans), said.plans_tail[lang]]
        cards = [AnswerCard(kind="plan", ref_id=pid, title=name) for pid, name in corpus.plan_names.items()]
        trace = [ToolCall(tool="list_plans", input={}, ok=True)]
        return _response("grounded", "\n".join(lines), known_numbers(data), cards=cards, trace=trace)
    if kind == "year":
        year = int(YEAR.search(req.question).group(1))  # type: ignore[union-attr]
        if year not in corpus.years:
            return _response("insufficient_evidence", said.insufficient[lang], set())
        lines, data = _year_block(corpus, year, lang)
        trace = [ToolCall(tool="year_conditions", input={"year": year}, ok=True)]
        return _response("grounded", "\n".join(lines), known_numbers(data), _year_citations(corpus, year), trace=trace)
    hits = search(corpus, req.question)
    trace = [ToolCall(tool="search_evidence", input={}, ok=True)]
    if not hits:
        return _response("insufficient_evidence", said.insufficient[lang], set(), trace=trace)
    answer = "\n".join(f"• {_clip(p.text[lang])}" for p in hits)
    citations = [_citation(corpus, p.id, p.source_id) for p in hits]
    cards = [AnswerCard(kind="passage", ref_id=p.id, title=p.title) for p in hits]
    known = known_numbers([p.text[lang] for p in hits])
    return _response("reference_only", answer, known, citations, cards, trace)


# ---------------------------------------------------------------- claude engine


def copilot_on(environ: Mapping[str, str]) -> bool:
    return environ.get("FIELDSHIFT_COPILOT") == "1"


def copilot_client(environ: Mapping[str, str]) -> anthropic.Anthropic | None:
    """The client when the copilot is on and the key is set, else None (the deterministic mode)."""
    key = environ.get("ANTHROPIC_API_KEY")
    if not copilot_on(environ) or not key:
        return None
    return anthropic.Anthropic(api_key=key, base_url=BASE_URL, timeout=TIMEOUT_SECONDS, max_retries=MAX_RETRIES)


def _create(client: anthropic.Anthropic, system: str, messages: list[dict[str, object]]) -> anthropic.types.Message:
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            tools=TOOLS,  # type: ignore[arg-type]
            thinking=THINKING,  # type: ignore[arg-type]
            output_config={"effort": EFFORT, "format": {"type": "json_schema", "schema": ANSWER_SCHEMA}},
            messages=messages,  # type: ignore[arg-type]
        )
    except anthropic.APIStatusError as err:
        raise CopilotError(type(err).__name__, err.status_code, None, err.request_id) from err
    except anthropic.APIError as err:
        raise CopilotError(type(err).__name__, None, None, None) from err
    if not isinstance(message, anthropic.types.Message):
        raise CopilotError("NotWhole", 200, None, None)
    return message


@dataclass
class _ToolRuns:
    """What the tool calls of one answer returned, and the limits they keep (security review of PR #55)."""

    corpus: Corpus
    lang: str
    trace: list[ToolCall] = field(default_factory=list)
    results: list[dict[str, object]] = field(default_factory=list)
    returned: set[str] = field(default_factory=set)
    result_bytes: int = 0
    seen: dict[str, Passage] = field(default_factory=dict)
    listed: bool = False
    years: set[int] = field(default_factory=set)

    def reply(self, block: anthropic.types.ToolUseBlock, n: int, request_id: str | None) -> dict[str, object]:
        """The tool_result of one call: past MAX_TOOLS_PER_ROUND not run, a repeat answered by a short note."""
        call = f"{block.name} {json.dumps(block.input, sort_keys=True)}"
        if n >= MAX_TOOLS_PER_ROUND:
            content, ok = json.dumps({"error": f"not run: at most {MAX_TOOLS_PER_ROUND} tool calls per turn"}), False
        elif call in self.returned:
            content, ok = json.dumps({"note": "already returned above"}), True
        else:
            self.returned.add(call)
            content, ok = self.run(block, request_id)
        return {
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": content,
            **({} if ok else {"is_error": True}),
        }

    def run(self, block: anthropic.types.ToolUseBlock, request_id: str | None) -> tuple[str, bool]:
        try:
            out, ok = run_tool(self.corpus, block.name, block.input, self.lang), True
        except (ValueError, KeyError) as err:
            out, ok = {"error": str(err)}, False
        year = block.input.get("year") if isinstance(block.input, dict) else None
        shown = {"year": year} if ok and type(year) is int else {}  # a failed call shows no year
        self.trace.append(ToolCall(tool=block.name if block.name in TOOL_NAMES else "unknown", input=shown, ok=ok))
        content = json.dumps(out, ensure_ascii=False)
        self.result_bytes += len(content.encode())
        if self.result_bytes > MAX_TOOL_RESULT_BYTES:
            raise CopilotError("ToolResultsTooLarge", 200, "tool_use", request_id)
        if ok:
            self.results.append(out)
            by_id = {p.id: p for p in self.corpus.passages}
            self.seen |= {p["passage_id"]: by_id[p["passage_id"]] for p in out.get("passages", [])}
            self.listed = self.listed or block.name == "list_plans"
            if block.name == "year_conditions":
                self.years.add(block.input["year"])
        return content, ok


def id_refusal(raw: str) -> str | None:
    """A second layer on each id the model returns: a forecast, ranking or advice phrase, a number word or a number
    with a unit in it refuses the whole reply (CLAUDE.md scientific boundaries; the security passes of PR #55)."""
    if FIELD_CLAIMS.search(_keep_accents(raw)):
        return "FieldClaim"
    if number_words(raw):
        return "NumberWords"
    if any(unit for _, _, unit in numbers(raw, COPILOT_UNITS)):  # an id never carries a unit
        return "NumberWithUnit"
    return None


PICKED_BY = {"engine": "claude", "model": MODEL}  # the model picked what the server shows (D-177)


class PickedIds(BaseModel):
    """The model's whole answer (D-177): ids of what the tools returned, so no model-written sentence reaches the
    farmer."""

    model_config = ConfigDict(extra="forbid")

    passage_ids: list[str]
    plan_ids: list[str]
    years: list[int]


ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "passage_ids": {"type": "array", "items": {"type": "string"}},
        "plan_ids": {"type": "array", "items": {"type": "string"}},
        "years": {"type": "array", "items": {"type": "integer"}},
    },
    "required": ["passage_ids", "plan_ids", "years"],
    "additionalProperties": False,
}


def _picked(message: anthropic.types.Message) -> PickedIds:
    request_id = getattr(message, "_request_id", None)
    if message.stop_reason != "end_turn":  # refusal, or cut off at max_tokens
        raise CopilotError("NotWhole", 200, message.stop_reason, request_id)
    raw = "".join(b.text for b in message.content if isinstance(b, anthropic.types.TextBlock))
    try:
        picked = PickedIds.model_validate_json(raw)
    except ValidationError as err:
        raise CopilotError("InvalidJson", 200, message.stop_reason, request_id) from err
    for cause in filter(None, map(id_refusal, [*picked.passage_ids, *picked.plan_ids])):
        raise CopilotError(cause, 200, message.stop_reason, request_id)
    return picked


def _extracted(picked: PickedIds, runs: _ToolRuns, req: CopilotRequest) -> CopilotResponse:
    """The picked passages, plans and years that a tool returned, word for word from our data under one fixed line,
    each with its source; an unknown id is dropped, and nothing left is the fixed "not enough evidence" answer."""
    corpus, lang = runs.corpus, req.lang
    by_id = {p.id: p for p in corpus.passages}
    plans = [i for i in dict.fromkeys(picked.plan_ids) if runs.listed and i in corpus.plan_names]
    shown = [runs.seen[i] for i in dict.fromkeys(picked.passage_ids) if i in runs.seen]
    shown += [by_id[f"plan-{i}"] for i in plans if by_id[f"plan-{i}"] not in shown]
    years = [y for y in dict.fromkeys(picked.years) if y in runs.years]
    if not shown and not years:
        out = _response("insufficient_evidence", corpus.answers.insufficient[lang], set(), trace=runs.trace)
        return out.model_copy(update=PICKED_BY)
    lines = [corpus.answers.extractive_head[lang], *(f"• {p.text[lang]}" for p in shown)]
    citations = [_citation(corpus, p.id, p.source_id) for p in shown]
    known = known_numbers([p.text[lang] for p in shown])
    for year in years:
        block, data = _year_block(corpus, year, lang)
        lines += block
        citations += _year_citations(corpus, year)
        known |= known_numbers(data)
    cards = [AnswerCard(kind="passage", ref_id=p.id, title=p.title) for p in shown if not p.id.startswith("plan-")]
    cards += [AnswerCard(kind="plan", ref_id=i, title=corpus.plan_names[i]) for i in plans]
    return _response("grounded", "\n".join(lines), known, citations, cards, runs.trace).model_copy(update=PICKED_BY)


def claude_answer(
    req: CopilotRequest, corpus: Corpus, client: anthropic.Anthropic, charge: Callable[[], bool]
) -> CopilotResponse:
    """Member B's manual tool loop, so every tool result is ours; the model ends with ids only (D-177)."""
    mode = "Simple mode." if req.mode == "simple" else "Technical mode."
    water = f" The farmer's water situation: {req.water}." if req.water else ""
    question = f"<question>{html.escape(req.question, quote=False)}</question>"
    messages: list[dict[str, object]] = [{"role": "user", "content": f"{mode}{water}\n\n{question}"}]
    runs = _ToolRuns(corpus, req.lang)
    for _ in range(MAX_TOOL_ROUNDS + 1):
        if not charge():  # each model call takes one of the shared calls (caps.py), not each answer
            raise ModelCallsFullError
        message = _create(client, corpus.system, messages)
        request_id = getattr(message, "_request_id", None)
        if message.stop_reason != "tool_use":
            break
        blocks = [b for b in message.content if isinstance(b, anthropic.types.ToolUseBlock)]
        messages.append({"role": "assistant", "content": message.content})
        messages.append({"role": "user", "content": [runs.reply(b, n, request_id) for n, b in enumerate(blocks)]})
    else:
        raise CopilotError("TooManyToolRounds", 200, "tool_use", request_id)
    return _extracted(_picked(message), runs, req)


def answer(
    req: CopilotRequest, corpus: Corpus, client: anthropic.Anthropic | None, charge: Callable[[], bool]
) -> CopilotResponse:
    """`charge` takes one model call from the caps before each call, and False refuses it (ModelCallsFullError)."""
    if client is None or fixed_only(req):
        return deterministic(req, corpus)
    return claude_answer(req, corpus, client, charge)
