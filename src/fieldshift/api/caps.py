"""Abuse caps shared by the two routes that call the Claude API with the same key, POST /api/copilot and
POST /api/explain (security review of PR #55; D-173). In memory, so they restart with the server; a refused call
answers 429 with a fixed detail and is not counted. Only a request that will call the model takes a call; a fixed
answer does not.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from starlette.requests import Request

PER_CLIENT_PER_HOUR = 20  # D-173: a routine abuse limit per client against the team's 30 USD key limit
PER_DAY = 1500  # D-173: a routine abuse limit for the whole app against the team's 30 USD key limit
HOUR, DAY = 3600.0, 86400.0
TOO_MANY = "Too Many Requests"


def client_of(request: Request) -> str:
    """The last X-Forwarded-For entry, the one Railway's proxy appends (a client can forge only the entries before
    it); without the header, the socket peer."""
    forwarded = request.headers.get("x-forwarded-for", "")
    last = forwarded.rsplit(",", 1)[-1].strip()
    if last:
        return last
    return request.client.host if request.client else "unknown"


class ModelCallCaps:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self.clock = clock
        self.per_client, self.per_day = PER_CLIENT_PER_HOUR, PER_DAY  # read at start, so a test can lower them
        self.lock = threading.Lock()
        self.clients: defaultdict[str, deque[float]] = defaultdict(deque)
        self.day: deque[float] = deque()

    def take(self, client: str) -> bool:
        """True and one call counted, or False when the client's hour or the app's day is full."""
        now = self.clock()
        with self.lock:
            while self.day and now - self.day[0] >= DAY:
                self.day.popleft()
            for key in list(self.clients):  # forget old calls, so memory holds only the last hour's clients
                calls = self.clients[key]
                while calls and now - calls[0] >= HOUR:
                    calls.popleft()
                if not calls:
                    del self.clients[key]
            calls = self.clients[client]
            if len(calls) >= self.per_client or len(self.day) >= self.per_day:
                if not calls:
                    del self.clients[client]
                return False
            calls.append(now)
            self.day.append(now)
            return True
