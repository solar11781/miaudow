"""Earthdata Login for the NASA downloads that need it (MODIS land cover R-N02, GPM IMERG R-N05).

Plain words: two NASA archives need a free Earthdata login. The user token in EARTHDATA_TOKEN is sent as a bearer
header only on https requests to NASA Earthdata hosts, never to the storage hosts the archives redirect to (a redirect
gets it again only when its target is a NASA Earthdata host too), and never printed. Without a token the opener still
keeps the cookies of the login redirect.
"""

from __future__ import annotations

import http.cookiejar
import os
import time
import urllib.error
import urllib.parse
import urllib.request

EARTHDATA_HOSTS = (".earthdata.nasa.gov", ".earthdatacloud.nasa.gov", ".gesdisc.eosdis.nasa.gov")


def gets_token(url: str) -> bool:
    """True when a request to url may carry the token: https and a NASA Earthdata host."""
    parts = urllib.parse.urlparse(url)
    return parts.scheme == "https" and (parts.hostname or "").endswith(EARTHDATA_HOSTS)


class _Bearer(urllib.request.BaseHandler):
    handler_order = 100  # before the default handlers, so the header is set on the first request

    def __init__(self, token: str) -> None:
        self._token = token

    def https_request(self, req: urllib.request.Request) -> urllib.request.Request:
        if gets_token(req.full_url):
            req.add_unredirected_header("Authorization", f"Bearer {self._token}")
        return req


def earthdata_opener() -> urllib.request.OpenerDirector:
    """An opener with the login cookies, and the bearer token from EARTHDATA_TOKEN when it is set."""
    token = os.environ.get("EARTHDATA_TOKEN", "").strip()
    handlers: list[urllib.request.BaseHandler] = [urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())]
    if token:
        handlers.insert(0, _Bearer(token))
    return urllib.request.build_opener(*handlers)


def fetch(opener: urllib.request.OpenerDirector, url: str, timeout: float, retries: int = 4) -> bytes:
    """The body of url; a failed try is repeated after a growing wait (5, 10, 20, 40 s), then the error is raised."""
    delay = 5.0
    for attempt in range(retries + 1):
        try:
            with opener.open(url, timeout=timeout) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == retries:
                raise
        time.sleep(delay)
        delay *= 2
    raise RuntimeError("unreachable")
