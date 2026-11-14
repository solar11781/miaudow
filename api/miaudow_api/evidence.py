"""AI core 02: evidence retrieval over the canonical passages (data/canonical/passages.json).

Hybrid lexical search, no neural model:
1. BM25 on word tokens with two indexes, ported from web/src/features/ai/retrieve.ts and normalize.ts: one keeps
   Vietnamese diacritics (used when the question has them, so "máy bay" never matches "máy móc"), one strips them (for
   questions typed without diacritics, and English). Farmer words are mapped to synonym keys; stop words are dropped.
2. Character 3-gram TF-IDF cosine on the diacritic-free text (catches partial words and typing variants).
3. Reciprocal rank fusion (RRF, k = 60) of the two rankings.
4. Abstention: the search answers only when the best fused hit reaches a BM25 score and a term coverage threshold,
   tuned on the DEV split of api/eval/retrieval_eval.jsonl (api/eval/run_retrieval_eval.py --tune). A small scope
   guard also abstains on requests the product must never answer from evidence: forecasts of coming weather, today's
   local prices, and ranking or choosing a "best" plan.

Neural embeddings are not used. `Embedder` is the plug-in point: pass an object with `embed(texts) -> vectors` to
`EvidenceIndex` and its cosine ranking joins the fusion as a third list. `NoEmbedder` (the default) adds nothing.

All functions return JSON-serialisable pydantic models, so the copilot can call `search` and `passage` as tools.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from collections.abc import Sequence
from functools import lru_cache
from typing import Protocol

from . import canonical
from .contracts import Passage, SearchHit, SearchResult

K1 = 1.4
B = 0.72
RRF_K = 60
# Weight of each ranking in the fusion: BM25, character 3-grams, dense (when an embedder is plugged in). The 3-gram
# weight is the best DEV MRR among the non-zero weights scanned by api/eval/run_retrieval_eval.py --tune (0.1); BM25
# alone (weight 0) scored higher still on DEV, see the results file. A non-zero weight keeps the hybrid design.
RRF_WEIGHTS = (1.0, 0.1, 1.0)
# Tuned on the DEV split only (api/eval/run_retrieval_eval.py --tune, 2026-11-14); TEST numbers are in
# api/eval/results/retrieval_2026-11-14.json.
MIN_BM25 = 0.0  # DEV tuning put no extra weight on the raw BM25 score; coverage decides
MIN_COVERAGE = 0.45
# Share of the query's information (IDF-weighted; a word the library never uses weighs most) that the top passage
# matches. Stops a question whose rare words are all unknown ("công thức nấu phở") from riding on common words.
MIN_IDF_COVERAGE = 0.3  # DEV: the largest floor below every answerable DEV question (lowest 0.31); no TEST data used


# ---------------------------------------------------------------- text normalisation (port of normalize.ts)


def normalize(text: str) -> str:
    """Lower-case, strip Vietnamese diacritics (đ -> d) and punctuation, so "hạn hán", "han han" and "HẠN" match."""
    s = unicodedata.normalize("NFD", text)
    s = "".join(ch for ch in s if not unicodedata.category(ch).startswith("M"))
    s = s.replace("đ", "d").replace("Đ", "d").lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def has_diacritics(text: str) -> bool:
    """True when the text carries Vietnamese diacritics; then words are matched with their accents kept."""
    nfd = unicodedata.normalize("NFD", text)
    return any("̀" <= ch <= "ͯ" for ch in nfd) or "đ" in text or "Đ" in text


def keep_accents(text: str) -> str:
    s = unicodedata.normalize("NFC", text).lower()
    s = "".join(ch if (ch.isalnum() or ch.isspace()) else " " for ch in s)
    return re.sub(r"\s+", " ", s).strip()


# Farmer words mapped to one key term, so questions in everyday language find the evidence. Matched on plain text.
SYNONYMS: list[tuple[re.Pattern, str]] = [
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

STOP = set(
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


def tokens(text: str, accented: bool = False) -> list[str]:
    """Search terms: the words (accents kept or stripped) plus the synonym key terms found in the text.

    Stop words are judged on the plain form, so "đã" and "da" are both dropped.
    """
    plain = normalize(text)
    keys = [k for rx, k in SYNONYMS if rx.search(plain)]
    words = (keep_accents(text) if accented else plain).split(" ")
    return [w for w in words if len(w) > 1 and normalize(w) not in STOP] + keys


def trigrams(text: str) -> Counter:
    s = f" {normalize(text)} "
    return Counter(s[i : i + 3] for i in range(len(s) - 2))


# ---------------------------------------------------------------- scope guard (product rules, not retrieval)

GUARDS: list[tuple[str, re.Pattern]] = [
    (
        "forecast_not_available",
        re.compile(
            r"\b(ngay mai|tuan toi|tuan sau|thang toi|thang sau|nam toi|nam sau|sap toi|du bao thoi tiet|"
            r"tomorrow|next week|next month|next year|weather forecast)\b"
        ),
    ),
    (
        "current_price_not_available",
        re.compile(
            r"\b(gia .*(hom nay|bay gio|hien nay|hien tai)|(hom nay|bay gio|hien nay).* gia|price today|current price)\b"
        ),
    ),
    (
        "ranking_not_supported",
        re.compile(
            r"\b(tot nhat|hay nhat|loi nhat|xep hang|nen trong cai nao|nen chon|chon giup|best|rank|ranking|"
            r"which plan should)\b"
        ),
    ),
]


def scope_guard(query: str) -> str | None:
    plain = normalize(query)
    for reason, rx in GUARDS:
        if rx.search(plain):
            return reason
    return None


# ---------------------------------------------------------------- index


class Embedder(Protocol):
    """Plug-in point for a sentence-embedding model (none is used today)."""

    name: str

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class NoEmbedder:
    """The default: no dense vectors, so retrieval stays fully lexical and reproducible offline."""

    name = "none"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:  # pragma: no cover - never called
        raise NotImplementedError("no embedding model is configured")


def passage_text(p: Passage) -> str:
    return f"{p.title.vi} {p.title.en} {p.title.vi} {p.text.vi} {p.text.en}"


class _Bm25:
    def __init__(self, docs: list[str], accented: bool):
        self.tf = []
        self.len = []
        for d in docs:
            toks = tokens(d, accented)
            self.tf.append(Counter(toks))
            self.len.append(len(toks))
        self.df = Counter(t for tf in self.tf for t in tf)
        self.n = len(docs)
        self.avg = sum(self.len) / max(1, self.n)
        self.accented = accented

    def score(self, q: list[str]) -> list[tuple[float, int]]:
        out = []
        for i, tf in enumerate(self.tf):
            score, matched = 0.0, 0
            for t in q:
                f = tf.get(t)
                if not f:
                    continue
                matched += 1
                df = self.df.get(t, 0)
                idf = math.log(1 + (self.n - df + 0.5) / (df + 0.5))
                score += idf * (f * (K1 + 1)) / (f + K1 * (1 - B + B * self.len[i] / self.avg))
            out.append((score, matched))
        return out


class EvidenceIndex:
    def __init__(
        self,
        passages: list[Passage],
        embedder: Embedder | None = None,
        weights: tuple[float, float, float] = RRF_WEIGHTS,
    ):
        self.weights = weights
        self.passages = passages
        self.by_id = {p.passage_id: p for p in passages}
        texts = [passage_text(p) for p in passages]
        self.accented = _Bm25(texts, accented=True)
        self.plain = _Bm25(texts, accented=False)
        grams = [trigrams(t) for t in texts]
        df = Counter(g for c in grams for g in c)
        n = len(texts)
        self.idf = {g: math.log((1 + n) / (1 + d)) + 1.0 for g, d in df.items()}
        self.doc_vecs = [self._vec(c) for c in grams]
        self.embedder = embedder if embedder is not None and not isinstance(embedder, NoEmbedder) else None
        self.dense = self.embedder.embed(texts) if self.embedder else None

    def _vec(self, grams: Counter) -> dict[str, float]:
        v = {g: (1 + math.log(c)) * self.idf.get(g, 0.0) for g, c in grams.items() if g in self.idf}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {g: x / norm for g, x in v.items()}

    def rank(self, query: str) -> list[dict]:
        """Every passage with any signal, best first, with its fused score and the raw signals behind it."""
        accented = has_diacritics(query)
        bm = self.accented if accented else self.plain
        q = list(dict.fromkeys(tokens(query, accented)))
        if not q:
            return []
        bm25 = bm.score(q)
        idf = {t: math.log(1 + (bm.n - bm.df.get(t, 0) + 0.5) / (bm.df.get(t, 0) + 0.5)) for t in q}
        idf_total = sum(idf.values()) or 1.0
        qv = self._vec(trigrams(query))
        cos = [sum(w * dv.get(g, 0.0) for g, w in qv.items()) for dv in self.doc_vecs]
        lists = [
            sorted((i for i in range(len(self.passages)) if bm25[i][0] > 0), key=lambda i: -bm25[i][0]),
            sorted((i for i in range(len(self.passages)) if cos[i] > 0), key=lambda i: -cos[i]),
        ]
        if self.dense is not None:
            qd = self.embedder.embed([query])[0]
            dense = [sum(a * b for a, b in zip(qd, d, strict=True)) for d in self.dense]
            lists.append(sorted(range(len(self.passages)), key=lambda i: -dense[i]))
        fused: dict[int, float] = {}
        for weight, ranking in zip(self.weights, lists, strict=False):
            for r, i in enumerate(ranking):
                fused[i] = fused.get(i, 0.0) + weight / (RRF_K + r + 1)
        order = sorted(fused, key=lambda i: (-fused[i], self.passages[i].passage_id))
        out = []
        for i in order:
            matched_terms = [t for t in q if bm.tf[i].get(t)]
            out.append(
                {
                    "index": i,
                    "fused": fused[i],
                    "bm25": bm25[i][0],
                    "coverage": bm25[i][1] / len(q),
                    "idf_coverage": sum(idf[t] for t in matched_terms) / idf_total,
                    "cosine": cos[i],
                    "matched_terms": matched_terms,
                }
            )
        return out

    def search(
        self,
        query: str,
        k: int = 5,
        min_bm25: float = MIN_BM25,
        min_coverage: float = MIN_COVERAGE,
        use_guard: bool = True,
    ) -> SearchResult:
        query = query.strip()
        k = max(1, min(int(k), 20))
        ranked = self.rank(query)
        hits = [
            SearchHit(
                passage=self.passages[r["index"]],
                score=round(r["fused"], 6),
                coverage=round(r["coverage"], 4),
                matched_terms=r["matched_terms"],
            )
            for r in ranked[:k]
        ]
        reason = decide(
            ranked[0] if ranked else None, scope_guard(query) if use_guard else None, min_bm25, min_coverage
        )
        return SearchResult(query=query, hits=[] if reason else hits, abstained=reason is not None, reason=reason)


def decide(
    top: dict | None,
    guard_reason: str | None,
    min_bm25: float = MIN_BM25,
    min_coverage: float = MIN_COVERAGE,
    min_idf_coverage: float | None = None,
) -> str | None:
    """The abstention reason for a ranked top hit, or None to answer."""
    if guard_reason is not None:
        return guard_reason
    if top is None:
        return "no_matching_evidence"
    floor = MIN_IDF_COVERAGE if min_idf_coverage is None else min_idf_coverage
    if top["bm25"] < min_bm25 or top["coverage"] < min_coverage or top.get("idf_coverage", 1.0) < floor:
        return "below_threshold"
    return None


@lru_cache(maxsize=1)
def load_passages() -> tuple[Passage, ...]:
    return tuple(Passage(**r) for r in canonical.load("passages.json")["passages"])


@lru_cache(maxsize=1)
def default_index() -> EvidenceIndex:
    return EvidenceIndex(list(load_passages()))


def search(query: str, k: int = 5) -> SearchResult:
    """Tool: search the evidence passages. Abstains (no hits, `reason` set) when the evidence is not strong enough."""
    return default_index().search(query, k)


def passage(passage_id: str) -> Passage | None:
    """Tool: one passage by id, or None."""
    return default_index().by_id.get(passage_id)
