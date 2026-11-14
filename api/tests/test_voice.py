"""Voice harness: WER and CER are real; the benchmark says it has no data."""

import pytest

from miaudow_api import voice


def test_wer_counts_substitutions_deletions_insertions():
    assert voice.wer("lúa hè thu bị hạn", "lúa hè thu bị hạn") == 0.0
    assert voice.wer("lúa hè thu bị hạn", "lửa hè thu bị hạn") == pytest.approx(1 / 5)  # diacritics matter
    assert voice.wer("lúa hè thu", "lúa thu") == pytest.approx(1 / 3)
    assert voice.wer("lúa hè thu", "lúa hè thu rồi") == pytest.approx(1 / 3)


def test_cer_and_normalisation():
    assert voice.cer("Lúa, hè!", "lúa hè") == 0.0
    assert voice.cer("abc", "abd") == pytest.approx(1 / 3)


def test_corpus_scores_sum_errors_over_utterances():
    out = voice.corpus_scores([("a b c d", "a b c d"), ("e f", "e x")])
    assert out["wer"] == pytest.approx(1 / 6)
    with pytest.raises(ValueError):
        voice.corpus_scores([])
    with pytest.raises(ValueError):
        voice.wer("", "x")


def test_benchmark_reports_no_data():
    status = voice.benchmark_status()
    assert status["status"] == "no_data"
    assert status["annotated_utterances"] == 0
