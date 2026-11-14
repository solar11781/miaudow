"""Abuse caps shared by the two routes that call the Claude API with the same key, POST /api/copilot and
POST /api/explain (the two security passes of PR #55; D-173). In memory, so they restart with the server. Each model
call takes one call of its client's hour, which both routes share, and one of its route's own day, so one route cannot
drain the other; a refused call is not counted and answers 429 with a fixed detail. A fixed answer takes nothing.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Literal

from starlette.requests import Request

PER_CLIENT_PER_HOUR = 20  # D-173: a routine abuse limit per client against the team's 30 USD key limit
PER_DAY = 1500  # D-173: a routine abuse limit per route and day against the team's 30 USD key limit
HOUR, DAY = 3600.0, 86400.0
TOO_MANY = "Too Many Requests"
Pool = Literal["copilot", "explain"]


class ModelCallsFullError(Exception):
    """The client's hour or the route's day is full; the route answers 429 with TOO_MANY."""


def client_of(request: Request) -> str:
    """Railway's X-Real-IP ("for identifying client's remote IP", docs.railway.com/networking/public-networking/
    specs-and-limits, read 2026-11-15), else the socket peer; a client-sent X-Forwarded-For entry is never used."""
    real = request.headers.get("x-real-ip", "").strip()
    if real:
        return real
    return request.client.host if request.client else "unknown"


def _forget(calls: deque[float], now: float, span: float) -> None:
    while calls and now - calls[0] >= span:
        calls.popleft()


class ModelCallCaps:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self.clock = clock
        self.per_client, self.per_day = PER_CLIENT_PER_HOUR, PER_DAY  # read at start, so a test can lower them
        self.lock = threading.Lock()
        self.clients: defaultdict[str, deque[float]] = defaultdict(deque)
        self.days: defaultdict[str, deque[float]] = defaultdict(deque)

    def take(self, client: str, pool: Pool) -> bool:
        """True and one call counted, or False when the client's hour or the pool's day is full."""
        now = self.clock()
        with self.lock:
            day = self.days[pool]
            _forget(day, now, DAY)
            for key in list(self.clients):  # forget old calls, so memory holds only the last hour's clients
                _forget(self.clients[key], now, HOUR)
                if not self.clients[key]:
                    del self.clients[key]
            calls = self.clients[client]
            if len(calls) >= self.per_client or len(day) >= self.per_day:
                if not calls:
                    del self.clients[client]
                return False
            calls.append(now)
            day.append(now)
            return True
