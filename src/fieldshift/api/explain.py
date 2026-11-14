"""The "explain simply" call to the Claude API (02-SRS FR-15; 01-PRD later idea 5; D-146, D-159, D-165).

It rewords text the app already shows in simpler words. It is the one stated exception to NFR-01 (no live external
call). Off by default: it runs only when FIELDSHIFT_EXPLAIN is "1" and ANTHROPIC_API_KEY is set in the server
environment. The browser sends only what identifies a shown text: the compare answers, a plan id and one of the card's
four "why" parts; the server takes that part's text from its own compare answer (D-165), so no browser can choose the
text the model reads. The request holds only the system prompt and that text, with < > & escaped, inside <text> tags
(H14: no personal data); neither the text nor the key is logged. The reply is plain text, marked AI-generated
(R-H15). A reply is refused when its numbers, read in order with their sign and the first unit word from UNITS
within the next few words, differ from the text's; the check sees only numbers and units, so it cannot show that
the words around them keep their meaning.
"""

from __future__ import annotations

import html
import logging
import re
from collections.abc import Mapping
from typing import Literal

import anthropic

from fieldshift.engine.schemas import CompareRequest, CompareResponse, Contract, PlanId

# decided by the team in D-165: the claude-api skill's current small, fast model for a short rewording
MODEL = "claude-haiku-5-5"
EFFORT = "low"  # claude-api skill: low effort for simple tasks
# claude-api skill: Haiku 5.5 accepts disabled thinking at effort high or below, so all of max_tokens is reply text
THINKING = {"type": "disabled"}
TIMEOUT_SECONDS = 20.0  # routine choice: a farmer waits on the page; with no retry the longest wait is about 20 s
MAX_RETRIES = 0  # review of PR #43: the SDK obeys retry-after without a cap; the farmer can press again
EXPLAIN_LIMIT = 2  # own thread limit (review of PR #43): stalled calls must never starve the threadpool compare runs in
BASE_URL = "https://api.anthropic.com"  # set here so no environment variable can send the text and key elsewhere
LANGUAGES = {"vi": "Vietnamese", "en": "English"}
MIN_MAX_TOKENS = 512  # routine choice: a 3-letter term may need a sentence or two to say simply
# The words that give a number its meaning: the units of the Value fields the API serves and the words that follow
# numbers in its texts (both read 2026-11-14), plus the second review's list (PR #43). Other words never count.
UNITS = frozenset(
    {
        "%",
        "mm",
        "m2",
        "m3",
        "m3/ha",
        "ha",
        "tấn",
        "t/ha",
        "kg",
        "°c",
        "ngày",
        "day",
        "days",
        "tháng",
        "month",
        "months",
        "năm",
        "year",
        "years",
        "giờ",
        "hours",
        "vụ",
        "lần",
        "times",
        "nghìn",
        "thousand",
        "triệu",
        "million",
        "đồng",
        "đ/ha",
        "vnd",
        "vnd/ha",
        "loại",
        "crops",
        "ô",
        "cells",
    }
)
UNIT_WINDOW = 3  # routine choice: the second review's faithful "1.5 dry months" puts one word before the unit
# a number (a minus is a sign only at the start or after a space or bracket, so 1995-2024 is a range; 16.200 and 1,5
# (vi), 16,200 and 1.5 (en) keep their separators), a %, a word (m2, m3 and m3/ha keep their digit), or a sentence end
TOKEN = re.compile(
    r"(?:(?<![^\s(\[])([-\N{MINUS SIGN}]))?(\d+(?:[.,]\d+)*)"
    r"|(%)"
    r"|((?i:m[23](?:/ha)?)(?!\w)|°?[^\W\d_]+(?:/[^\W\d_]+)*)"
    r"|([.;!?])"
)

for _name in ("anthropic", "httpx2"):  # their debug log holds the request body; ANTHROPIC_LOG must never turn it on
    logging.getLogger(_name).setLevel(logging.WARNING)


# FR-15 names no field; these are the card's long texts, the four labelled parts of its `why` row (UI-UX-SPEC §9).
# The risks are left out: they are quoted lines with their own sources in the row `check` (D-136).
WhyPart = Literal["why", "evidence", "benefits", "gaps"]


class ExplainRequest(Contract):
    answers: CompareRequest
    plan: PlanId
    field: WhyPart
    lang: Literal["vi", "en"]


class ExplainResponse(Contract):
    text: str
    ai_generated: Literal[True]
    model: str


class ExplainError(Exception):
    """No usable reply; the route answers a generic 502 and logs str(self), which holds no text, key or address."""

    def __init__(self, cause: str, status: int | None, stop_reason: str | None, request_id: str | None) -> None:
        super().__init__(f"explain failed: {cause} status={status} stop_reason={stop_reason} request_id={request_id}")


PROMPT = "explain"  # rules/prompts/explain.md, read once at start (app.py)
PLACEHOLDER = "language"


def system_prompt(template: str, lang: str) -> str:
    """rules/prompts/explain.md with its {language} filled in."""
    return template.replace("{" + PLACEHOLDER + "}", LANGUAGES[lang])


def shown_text(request: ExplainRequest, answer: CompareResponse) -> str:
    """The asked part of the plan's `why`, in the asked language, from the server's own answer to request.answers."""
    plan = next(p for p in answer.plans if p.id == request.plan)  # every answer holds every plan (CompareResponse)
    return getattr(plan.why, request.field)[request.lang]


def claude_client(environ: Mapping[str, str]) -> anthropic.Anthropic | None:
    """The client when the feature is on and the key is set, else None (FR-15: off by default)."""
    key = environ.get("ANTHROPIC_API_KEY")
    if environ.get("FIELDSHIFT_EXPLAIN") != "1" or not key:
        return None
    return anthropic.Anthropic(api_key=key, base_url=BASE_URL, timeout=TIMEOUT_SECONDS, max_retries=MAX_RETRIES)


def numbers(text: str) -> list[tuple[str, str, str]]:
    """(sign, digits, unit) of each number, in order. The unit is the first word of UNITS (or a %, attached or not)
    within the next UNIT_WINDOW words, before the next number or sentence end; else "". The Unicode minus reads as
    "-"."""
    found: list[list[str]] = []
    open_words = 0
    for sign, digits, percent, word, _end in TOKEN.findall(text):
        if digits:
            found.append(["-" if sign else "", digits, ""])
            open_words = UNIT_WINDOW
        elif open_words and (percent or word):
            unit = percent or word.lower()
            if unit in UNITS:
                found[-1][2] = unit
                open_words = 0
            else:
                open_words -= 1
        else:  # a sentence end closes the window
            open_words = 0
    return [(sign, digits, unit) for sign, digits, unit in found]


def max_tokens(text: str) -> int:
    """Twice the UTF-8 bytes of the text, at least MIN_MAX_TOKENS. The claude-api skill gives no characters-per-token
    figure and count_tokens is a network call, so this assumes each token holds at least one byte: the bytes bound the
    text's tokens, and the reply gets twice that. The longest part a request can name is 414 bytes (usual_p03 why, en,
    2026-11-14), so at most 828."""
    return max(2 * len(text.encode("utf-8")), MIN_MAX_TOKENS)


def explain(text: str, lang: str, client: anthropic.Anthropic, template: str) -> ExplainResponse:
    """The text reworded by Claude in `lang`; raises ExplainError when the reply is not usable."""
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=max_tokens(text),
            system=system_prompt(template, lang),
            thinking=THINKING,
            output_config={"effort": EFFORT},
            # escaped, so no form of a tag in the text can close the app's tag (second review of PR #43)
            messages=[{"role": "user", "content": f"<text>{html.escape(text, quote=False)}</text>"}],
        )
    except anthropic.APIStatusError as err:
        raise ExplainError(type(err).__name__, err.status_code, None, err.request_id) from err
    except anthropic.APIError as err:
        raise ExplainError(type(err).__name__, None, None, None) from err
    # the SDK hands back a non-JSON body as a str and an unexpected JSON body as a Message with fields set to None
    if not isinstance(message, anthropic.types.Message):
        raise ExplainError("NotWhole", 200, None, None)
    request_id = getattr(message, "_request_id", None)
    if message.stop_reason != "end_turn":  # refusal, or cut off at max_tokens
        raise ExplainError("NotWhole", 200, message.stop_reason, request_id)
    blocks = message.content or []
    simple = "".join(block.text for block in blocks if isinstance(block, anthropic.types.TextBlock)).strip()
    if not simple:
        raise ExplainError("Empty", 200, message.stop_reason, request_id)
    if numbers(simple) != numbers(text):
        raise ExplainError("NumbersDiffer", 200, message.stop_reason, request_id)
    return ExplainResponse(text=simple, ai_generated=True, model=MODEL)
