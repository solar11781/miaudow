"""Retrieval evaluation of AI core 02 on api/eval/retrieval_eval.jsonl.

Run from the project root:

    .venv\\Scripts\\python api/eval/run_retrieval_eval.py           # report TEST with the thresholds in evidence.py
    .venv\\Scripts\\python api/eval/run_retrieval_eval.py --tune    # also search thresholds on DEV only

Metrics (TEST split):
- recall@1/3/5 and MRR over answerable questions: is any gold passage among the top k of the fused ranking;
- abstention precision and recall over all questions: precision = share of abstentions that were unanswerable,
  recall = share of unanswerable questions that abstained; reported with and without the scope guard;
- answerable questions wrongly abstained (false abstentions).
Writes api/eval/results/retrieval_2026-11-14.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "api"))

from miaudow_api import evidence  # noqa: E402

EVAL = ROOT / "api" / "eval" / "retrieval_eval.jsonl"
OUT = ROOT / "api" / "eval" / "results" / "retrieval_2026-11-14.json"


def load(split: str | None = None) -> list[dict]:
    rows = [json.loads(x) for x in EVAL.read_text(encoding="utf-8").splitlines() if x.strip()]
    return [r for r in rows if split is None or r["split"] == split]


def ranking_metrics(rows: list[dict], index) -> dict:
    ans = [r for r in rows if r["answerable"]]
    hits = {1: 0, 3: 0, 5: 0}
    rr = 0.0
    misses = []
    for r in ans:
        ranked = [index.passages[x["index"]].passage_id for x in index.rank(r["question"])]
        first = next((i for i, pid in enumerate(ranked) if pid in r["gold"]), None)
        for k in hits:
            hits[k] += first is not None and first < k
        rr += 0.0 if first is None else 1.0 / (first + 1)
        if first is None or first >= 3:  # noqa: PLR2004
            misses.append({"id": r["id"], "question": r["question"], "gold": r["gold"], "top3": ranked[:3]})
    n = max(1, len(ans))
    return {
        "n_answerable": len(ans),
        "recall@1": round(hits[1] / n, 3),
        "recall@3": round(hits[3] / n, 3),
        "recall@5": round(hits[5] / n, 3),
        "mrr": round(rr / n, 3),
        "misses_at_3": misses,
    }


def precompute(rows: list[dict], index) -> list[dict]:
    """Rank each question once; thresholds are then applied to the cached top hit."""
    out = []
    for r in rows:
        ranked = index.rank(r["question"])
        top = ranked[0] if ranked else None
        out.append(
            {
                **r,
                "_guard": evidence.scope_guard(r["question"]),
                "_top": top,
                "_top_id": index.passages[top["index"]].passage_id if top else None,
            }
        )
    return out


def abstention_metrics(rows: list[dict], min_bm25: float, min_cov: float, guard: bool) -> dict:
    tp = fp = fn = tn = 0
    wrong = []
    for r in rows:
        reason = evidence.decide(r["_top"], r["_guard"] if guard else None, min_bm25, min_cov)
        abstained = reason is not None
        if abstained and not r["answerable"]:
            tp += 1
        elif abstained and r["answerable"]:
            fp += 1
            wrong.append({"id": r["id"], "question": r["question"], "abstained": True, "reason": reason})
        elif not abstained and not r["answerable"]:
            fn += 1
            wrong.append({"id": r["id"], "question": r["question"], "abstained": False, "top1": r["_top_id"]})
        else:
            tn += 1
    return {
        "abstained_unanswerable": tp,
        "abstained_answerable": fp,
        "answered_unanswerable": fn,
        "answered_answerable": tn,
        "abstention_precision": round(tp / (tp + fp), 3) if tp + fp else None,
        "abstention_recall": round(tp / (tp + fn), 3) if tp + fn else None,
        "errors": wrong,
    }


def tune(rows: list[dict]) -> tuple[float, float, float]:
    """Grid search on DEV: maximise balanced accuracy of the answer/abstain decision (guard on); ties keep the
    lowest thresholds (answer more)."""
    best = (-1.0, 0.0, 0.0)
    for s10 in range(0, 301, 5):
        s = s10 / 10
        for c20 in range(0, 21):
            c = c20 / 20
            m = abstention_metrics(rows, s, c, guard=True)
            ans = m["answered_answerable"] / max(1, m["answered_answerable"] + m["abstained_answerable"])
            una = m["abstained_unanswerable"] / max(1, m["abstained_unanswerable"] + m["answered_unanswerable"])
            score = (ans + una) / 2
            if score > best[0] + 1e-9:
                best = (score, s, c)
    return best


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tune", action="store_true", help="search thresholds on the DEV split")
    args = parser.parse_args()
    index = evidence.default_index()
    dev, test = precompute(load("dev"), index), precompute(load("test"), index)
    report: dict = {
        "date": "2026-11-14",
        "eval_file": "api/eval/retrieval_eval.jsonl",
        "n_passages": len(index.passages),
        "n_questions": {"dev": len(dev), "test": len(test)},
        "method": "BM25 (two indexes, diacritics kept or stripped) + character 3-gram TF-IDF cosine, reciprocal rank "
        "fusion k=60; abstain below MIN_BM25 or MIN_COVERAGE on the top fused hit; scope guard for forecasts, "
        "current prices and plan ranking. No neural embeddings.",
        "thresholds_in_use": {"min_bm25": evidence.MIN_BM25, "min_coverage": evidence.MIN_COVERAGE},
        "rrf_weights_in_use": list(evidence.RRF_WEIGHTS),
    }
    if args.tune:
        scan = []
        for w in (0.0, 0.1, 0.25, 0.5, 1.0):
            index.weights = (1.0, w, 1.0)
            m = ranking_metrics(load("dev"), index)
            scan.append({"trigram_weight": w, "dev_mrr": m["mrr"], "dev_recall@1": m["recall@1"]})
        index.weights = evidence.RRF_WEIGHTS
        report["dev_weight_scan"] = scan
        sys.stdout.write(f"DEV 3-gram weight scan: {scan}\n")
        score, s, c = tune(dev)
        report["dev_tuning"] = {"balanced_accuracy": round(score, 3), "min_bm25": s, "min_coverage": c}
        sys.stdout.write(f"DEV tuning: balanced accuracy {score:.3f} at MIN_BM25={s} MIN_COVERAGE={c}\n")
    s, c = evidence.MIN_BM25, evidence.MIN_COVERAGE
    report["dev"] = {
        "ranking": ranking_metrics(dev, index),
        "abstention": abstention_metrics(dev, s, c, guard=True),
    }
    report["test"] = {
        "ranking": ranking_metrics(test, index),
        "abstention_with_guard": abstention_metrics(test, s, c, guard=True),
        "abstention_without_guard": abstention_metrics(test, s, c, guard=False),
    }
    t = report["test"]
    sys.stdout.write(
        f"TEST ranking ({t['ranking']['n_answerable']} answerable): recall@1 {t['ranking']['recall@1']}, "
        f"recall@3 {t['ranking']['recall@3']}, recall@5 {t['ranking']['recall@5']}, MRR {t['ranking']['mrr']}\n"
    )
    for name in ("abstention_with_guard", "abstention_without_guard"):
        a = t[name]
        sys.stdout.write(
            f"TEST {name}: precision {a['abstention_precision']}, recall {a['abstention_recall']} "
            f"(abstained on {a['abstained_answerable']} answerable, answered {a['answered_unanswerable']} unanswerable)\n"
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.stdout.write(f"written {OUT.relative_to(ROOT)}\n")


if __name__ == "__main__":
    main()
