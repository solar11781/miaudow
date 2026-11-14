"""Tests for the Earthdata Login opener (MODIS land cover R-N02, GPM IMERG R-N05).

Source: NASA Earthdata Login user tokens are sent as an "Authorization: Bearer <token>" header; this header reached the
LP DAAC and GES DISC archives on this laptop on 2026-11-14 (team). Expectations: the token goes only to https requests
to NASA Earthdata hosts, never to other hosts (the archives redirect to storage hosts), never over http, and is not
carried to a redirect target; without a token the opener still keeps cookies for the login redirect.
"""

import urllib.request

import pytest

from fieldshift.data.earthdata import earthdata_opener, gets_token

SAMPLE = "sample-value-not-real"


@pytest.mark.parametrize(
    "url",
    [
        "https://urs.earthdata.nasa.gov/oauth/authorize",
        "https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/MCD12C1.061/x.hdf",
        "https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGM.07/2001/contents.html",
    ],
)
def test_nasa_earthdata_hosts_over_https_get_the_token(url: str) -> None:
    assert gets_token(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://urs.earthdata.nasa.gov/oauth/authorize",
        "https://lp-prod-protected.s3.us-west-2.amazonaws.com/x.hdf",
        "https://urs.earthdata.nasa.gov.example.com/",
        "https://cmr.example.org/search",
    ],
)
def test_other_hosts_and_http_never_get_the_token(url: str) -> None:
    assert not gets_token(url)


def _header(opener: urllib.request.OpenerDirector) -> str | None:
    req = urllib.request.Request("https://urs.earthdata.nasa.gov/oauth/authorize")
    for handler in opener.handlers:
        hook = getattr(handler, "https_request", None)
        if hook is not None:
            req = hook(req)
    return req.unredirected_hdrs.get("Authorization")  # unredirected: not carried to a redirect target


def test_the_opener_adds_the_header_from_the_environment_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EARTHDATA_TOKEN", SAMPLE)
    assert _header(earthdata_opener()) == f"Bearer {SAMPLE}"
    monkeypatch.delenv("EARTHDATA_TOKEN")
    opener = earthdata_opener()
    assert _header(opener) is None
    assert any(isinstance(h, urllib.request.HTTPCookieProcessor) for h in opener.handlers)
