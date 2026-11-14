"""Tests for the system prompts in rules/prompts/*.md (team, 2026-11-15: the prompts move out of the code).

The text sent to the model stays byte-identical to the text the code sent before the move (tests/fixtures/
prompts_sent.json, taken from commit 3d70518, which already holds the review's two copilot rules), and a missing or
empty file, or a missing placeholder, stops the start.
"""

import json
from pathlib import Path

import pytest

from fieldshift.api import copilot, explain
from fieldshift.engine.rules import load_prompt

REPO = Path(__file__).resolve().parents[1]
SENT = json.loads((REPO / "tests" / "fixtures" / "prompts_sent.json").read_text(encoding="utf-8"))


def test_the_copilot_prompt_is_the_text_sent_before() -> None:
    assert copilot.load_corpus(REPO).system == SENT["copilot"]


@pytest.mark.parametrize("lang", ["vi", "en"])
def test_the_explain_prompt_is_the_text_sent_before(lang: str) -> None:
    template = load_prompt(REPO, explain.PROMPT, (explain.PLACEHOLDER,))
    assert explain.system_prompt(template, lang) == SENT[f"explain_{lang}"]


def write(tmp_path: Path, text: str | None) -> Path:
    (tmp_path / "rules" / "prompts").mkdir(parents=True)
    if text is not None:
        (tmp_path / "rules" / "prompts" / "x.md").write_bytes(text.encode())  # line ends as given
    return tmp_path


@pytest.mark.parametrize(
    ("text", "placeholders", "error"),
    [
        (None, (), "missing"),
        ("", (), "empty"),
        (" \n\n", (), "empty"),
        ("The text is in English.\n", ("language",), "no placeholder"),
    ],
)
def test_a_bad_prompt_file_stops_the_start(
    tmp_path: Path, text: str | None, placeholders: tuple[str, ...], error: str
) -> None:
    with pytest.raises(ValueError, match=f"rules/prompts/x.md: {error}"):
        load_prompt(write(tmp_path, text), "x", placeholders)


def test_the_file_is_read_without_its_final_line_end(tmp_path: Path) -> None:
    assert load_prompt(write(tmp_path, "a {language}\r\nb\n"), "x", ("language",)) == "a {language}\nb"
