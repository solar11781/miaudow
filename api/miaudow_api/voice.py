"""Voice benchmark harness (AI core 04 input side): word and character error rates.

No annotated Vietnamese farm audio exists yet, so `benchmark_status()` reports "no_data" and claims no accuracy. The
WER/CER code is real and tested, so a benchmark can run as soon as reference transcripts arrive.

WER = (substitutions + deletions + insertions) / reference words (Levenshtein distance on words); CER the same on
characters. Text is compared after Unicode NFC, lower case and whitespace folding; diacritics are kept, because in
Vietnamese they change the word ("lúa" rice vs "lửa" fire).
"""

from __future__ import annotations

import re
import unicodedata

BENCHMARK_DIR = "data/raw/voice_benchmark"


def _clean(text: str) -> str:
    s = unicodedata.normalize("NFC", text).lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def edit_distance(ref: list[str], hyp: list[str]) -> int:
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, start=1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, start=1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
        prev = cur
    return prev[-1]


def wer(reference: str, hypothesis: str) -> float:
    ref = _clean(reference).split()
    if not ref:
        raise ValueError("empty reference transcript")
    return edit_distance(ref, _clean(hypothesis).split()) / len(ref)


def cer(reference: str, hypothesis: str) -> float:
    ref = list(_clean(reference).replace(" ", ""))
    if not ref:
        raise ValueError("empty reference transcript")
    return edit_distance(ref, list(_clean(hypothesis).replace(" ", ""))) / len(ref)


def corpus_scores(pairs: list[tuple[str, str]]) -> dict:
    """Corpus WER and CER (errors summed over all utterances, divided by all reference words or characters)."""
    if not pairs:
        raise ValueError("no utterances")
    w_err = w_n = c_err = c_n = 0
    for ref, hyp in pairs:
        rw, hw = _clean(ref).split(), _clean(hyp).split()
        rc, hc = list("".join(rw)), list("".join(hw))
        w_err += edit_distance(rw, hw)
        w_n += len(rw)
        c_err += edit_distance(rc, hc)
        c_n += len(rc)
    return {"utterances": len(pairs), "wer": w_err / w_n, "cer": c_err / c_n}


def benchmark_status() -> dict:
    return {
        "status": "no_data",
        "metric": ["wer", "cer"],
        "annotated_utterances": 0,
        "message": {
            "vi": "Chưa có bản ghi âm tiếng Việt của nông dân có chép lời để kiểm tra, nên chưa có số đo độ chính xác "
            "nhận dạng giọng nói. Không nói giọng Nghệ An được nhận đúng.",
            "en": "No annotated Vietnamese farm audio exists yet, so there is no measured speech recognition accuracy. "
            "No claim is made that the Nghệ An dialect is recognised.",
        },
        "expected_input": f"{BENCHMARK_DIR}/<set>/transcripts.jsonl with one {{audio, reference, hypothesis, dialect, "
        "noise, device}} object per line",
    }
