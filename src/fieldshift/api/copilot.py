"""The copilot, POST /api/copilot: member B's grounded question answering (branch feat/lamgiang-2,
lamgiang/api/miaudow_api/copilot.py and evidence.py), ported by D-172 with the protections of the explain endpoint.

The server finds what our own data holds for the question, with no model: a search of the passages
(rules/copilot.yaml, the plans, the official conditions and the model gates), the year shares of the official
conditions for each past year the question names (GET /api/past-years), and the plans in the study order
(rules/rotations.yaml) when a plan or crop word appears.
- deterministic (the default, no key): fixed sentences from rules/copilot.yaml filled from that data.
- claude (only with ANTHROPIC_API_KEY): one model call, with no tools, gets the question and the numbered candidates
  as data and returns only the ids of those that answer it, in a structured output whose schema lists the candidate
  ids (live test after PR #55: with tools and a structured output, the model called no tool). The server shows the
  picked candidates word for word from our data, each with its source, under one fixed line; no model-written
  sentence reaches the farmer. The question goes to the model escaped inside <question> tags and capped at
  QUESTION_MAX_CHARS.
Plans are never ranked, a past year is never a forecast, and the year card is not sent (D-169: it has no source
button). Member B's climate ML, satellite, map and dataset tools are not ported: D-169 hid the climate ML and the
other data have no register row or are not served by our API.
"""

from __future__ import annotations

import html
import math
import re
import unicodedata
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass
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
    metrics_file,
)
from fieldshift.engine.schemas import FIRST_YEAR, LAST_YEAR, Contract, PlanId, SourceFacts, SourceId, Text

COPILOT_LIMIT = 2  # the explain endpoint's own limit (review of PR #43), so a burst never fills the farmer threads
# routine choice: 300 letters of 3 UTF-8 bytes stay under the 1024-byte body limit (tests/test_copilot.py)
QUESTION_MAX_CHARS = 300
MAX_TOKENS = 1024  # routine choice: a list of at most a dozen candidate ids as JSON
EFFORT = "low"  # the explain endpoint's effort; the server has already found the candidates
SEARCH_LIMIT = 3  # member B's deterministic answer quotes the top 3 passages
# the method report that qualifies a season's model result (D-165: the winter result is "narrow" and "fragile"; E-018 is
# src/fieldshift/ml/reports.py winter_claim_report)
SEASON_REPORTS = {"winter": "E-018"}
# member B's search (frontend/src/features/ai/retrieve.ts, kept by the D-169 audit): BM25 with k1 1.4 and b 0.72, and
# an answer only when the top hit reaches both floors (its MIN_SCORE and MIN_COVERAGE)
K1, B = 1.4, 0.72
MIN_SCORE, MIN_COVERAGE = 4.5, 0.5
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
    plans: list[dict[str, object]]  # the plans in the study order, each text in both languages
    plan_names: dict[PlanId, Text]
    crop_words: frozenset[str]  # the crop names of rules/crops.yaml without accents, both languages
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
    reports = {r.id: r.title for r in metrics_file(root).reports}
    for gate in gate_rows(root):
        if gate.gate == "G2":
            label = seasons[gate.season].label
            title: Text = {lang: texts.answers.model_title[lang].format(season=label[lang]) for lang in ("vi", "en")}
            keys = f"{label['vi']} {label['en']} mo hinh du doan model skill"
            report = reports[SEASON_REPORTS[gate.season]] if gate.season in SEASON_REPORTS else None
            text = {
                lang: f"{gate.detail[lang]} {report[lang]}." if report else gate.detail[lang] for lang in ("vi", "en")
            }
            passages.append(Passage(f"model-{gate.season}", gate.source_ids[0], keys, title, text))
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
        crop_words=frozenset(normalize(c.name[lang]) for c in crops.values() for lang in ("vi", "en")),
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


PROMPT = "copilot"  # rules/prompts/copilot.md: pick the candidates that answer the question


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
            found |= set(numbers(_units_spelled(item)))
    return found


def check_numbers(text: str, known: set[Number]) -> NumberCheck:
    """The shown text's numbers that are not a token, with the same sign and unit, of the data it was built from."""
    found = numbers(_units_spelled(text))
    return NumberCheck(checked=len(found), unverified=[f"{s}{d}" for s, d, u in found if (s, d, u) not in known])


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
OWN_FIELD = re.compile(
    r"\b(ruong (nha |cua )?(toi|minh|em|tao)|nha (toi|minh|em)|(toi|em|minh) trong|"
    r"my (own )?(field|farm|plot|land|paddy)s?|if i|will i|i (plant|grow|earn))\b"
)


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


def _create(
    client: anthropic.Anthropic, system: str, messages: list[dict[str, object]], schema: dict[str, object]
) -> anthropic.types.Message:
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            thinking=THINKING,  # type: ignore[arg-type]
            output_config={"effort": EFFORT, "format": {"type": "json_schema", "schema": schema}},
            messages=messages,  # type: ignore[arg-type]
        )
    except anthropic.APIStatusError as err:
        raise CopilotError(type(err).__name__, err.status_code, None, err.request_id) from err
    except anthropic.APIError as err:
        raise CopilotError(type(err).__name__, None, None, None) from err
    if not isinstance(message, anthropic.types.Message):
        raise CopilotError("NotWhole", 200, None, None)
    return message


PICKED_BY = {"engine": "claude", "model": MODEL}  # the model picked what the server shows (D-177)


class PickedIds(BaseModel):
    """The model's whole answer: ids of the candidates, so no model-written sentence reaches the farmer."""

    model_config = ConfigDict(extra="forbid")

    ids: list[str]


@dataclass(frozen=True)
class Candidate:
    """Something the server found for the question: a passage, a plan passage or a past year's fixed lines."""

    id: str
    text: str
    passage: Passage | None = None
    year: int | None = None


def candidates(req: CopilotRequest, corpus: Corpus) -> list[Candidate]:
    """The server's own retrieval, with no model and no tools (live test after PR #55): the passage search on the
    question with member B's floors, the fixed lines of each past year the question names, and the plans when a
    plan or crop word appears."""
    lang, q = req.lang, f" {normalize(req.question)} "
    found = [Candidate(p.id, p.text[lang], passage=p) for p in search(corpus, req.question)]
    for year in dict.fromkeys(int(y) for y in YEAR.findall(req.question)):
        if year in corpus.years:
            found.append(Candidate(f"year-{year}", "\n".join(_year_block(corpus, year, lang)[0]), year=year))
    if any(f" {w} " in q for w in (*PLAN_WORDS, *corpus.crop_words)):
        shown = {c.id for c in found}
        found += [
            Candidate(p.id, p.text[lang], passage=p)
            for p in corpus.passages
            if p.id.startswith("plan-") and p.id not in shown
        ]
    return found


def _trace(found: list[Candidate]) -> list[ToolCall]:
    """The server's retrieval steps; only a year, never model text, is shown (security review of PR #55)."""
    trace = [ToolCall(tool="search_evidence", input={}, ok=True)]
    trace += [ToolCall(tool="year_conditions", input={"year": c.year}, ok=True) for c in found if c.year]
    if any(c.id.startswith("plan-") for c in found):
        trace.append(ToolCall(tool="list_plans", input={}, ok=True))
    return trace


def _schema(found: list[Candidate]) -> dict[str, object]:
    """Structured output (claude-api skill: output_config.format json_schema, enum supported): only candidate ids."""
    ids = {"type": "array", "items": {"type": "string", "enum": [c.id for c in found]}}
    return {"type": "object", "properties": {"ids": ids}, "required": ["ids"], "additionalProperties": False}


def _content(req: CopilotRequest, found: list[Candidate]) -> str:
    mode = "Simple mode." if req.mode == "simple" else "Technical mode."
    water = f" The farmer's water situation: {req.water}." if req.water else ""
    question = f"<question>{html.escape(req.question, quote=False)}</question>"
    listed = "\n\n".join(f"[{n}] {c.id}\n{html.escape(c.text, quote=False)}" for n, c in enumerate(found, start=1))
    return f"{mode}{water}\n\n{question}\n\n<candidates>\n{listed}\n</candidates>"


def _picked(message: anthropic.types.Message) -> PickedIds:
    request_id = getattr(message, "_request_id", None)
    if message.stop_reason != "end_turn":  # refusal, or cut off at max_tokens
        raise CopilotError("NotWhole", 200, message.stop_reason, request_id)
    raw = "".join(b.text for b in message.content if isinstance(b, anthropic.types.TextBlock))
    try:
        picked = PickedIds.model_validate_json(raw)
    except ValidationError as err:
        raise CopilotError("InvalidJson", 200, message.stop_reason, request_id) from err
    return picked


def _shown(picked: PickedIds, found: list[Candidate], req: CopilotRequest, corpus: Corpus) -> CopilotResponse:
    """The picked candidates word for word from our data under one fixed line, each with its source; an id that is no
    candidate is dropped, and nothing left is the fixed "not enough evidence" answer."""
    lang, by_id, trace = req.lang, {c.id: c for c in found}, _trace(found)
    chosen = [by_id[i] for i in dict.fromkeys(picked.ids) if i in by_id]
    if not chosen:
        out = _response("insufficient_evidence", corpus.answers.insufficient[lang], set(), trace=trace)
        return out.model_copy(update=PICKED_BY)
    lines, citations, cards, known = [corpus.answers.extractive_head[lang]], [], [], set()
    for c in chosen:
        p = c.passage
        if p is None:  # a past year's fixed lines (candidates)
            year = int(c.id.removeprefix("year-"))
            block, data = _year_block(corpus, year, lang)
            lines += block
            citations += _year_citations(corpus, year)
            known |= known_numbers(data)
            continue
        lines.append(f"• {p.text[lang]}")
        citations.append(_citation(corpus, p.id, p.source_id))
        known |= known_numbers(p.text[lang])
        plan = p.id.removeprefix("plan-")
        if plan in corpus.plan_names:
            cards.append(AnswerCard(kind="plan", ref_id=plan, title=corpus.plan_names[plan]))
        else:
            cards.append(AnswerCard(kind="passage", ref_id=p.id, title=p.title))
    out = _response("grounded", "\n".join(lines), known, citations, cards, trace)
    return out.model_copy(update=PICKED_BY)


def answer(
    req: CopilotRequest, corpus: Corpus, client: anthropic.Anthropic | None, charge: Callable[[], bool]
) -> CopilotResponse:
    """The fixed answers without a key or for a fixed route; else the server's candidates and one model call that
    picks among them (`charge` takes that call from the caps first, and False refuses it: ModelCallsFullError)."""
    if client is None or fixed_only(req):
        return deterministic(req, corpus)
    found = candidates(req, corpus)
    if not found:  # nothing to pick from: no model call
        return _response("insufficient_evidence", corpus.answers.insufficient[req.lang], set(), trace=_trace(found))
    if not charge():
        raise ModelCallsFullError
    message = _create(client, corpus.system, [{"role": "user", "content": _content(req, found)}], _schema(found))
    return _shown(_picked(message), found, req, corpus)
