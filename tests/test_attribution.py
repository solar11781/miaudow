"""Attribution table for the README (compliance CR-04/CR-05: every third-party resource with version and licence).

Written before scripts/attribution.py. Run: pytest tests/test_attribution.py
"""

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("attribution", REPO / "scripts" / "attribution.py")
attribution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(attribution)


def test_lock_lines_become_name_and_version() -> None:
    lock = "# comment\npandas==3.0.2 \\n    --hash=sha256:abc\nnumpy==2.3.1\n\n-e .\nrequests[socks]==2.32.4\n"
    assert attribution.parse_lock(lock) == [("numpy", "2.3.1"), ("pandas", "3.0.2"), ("requests", "2.32.4")]


def test_rows_show_licence_or_unknown() -> None:
    licences = {"numpy": "BSD-3-Clause", "pandas": None}
    rows = attribution.table_rows([("numpy", "2.3.1"), ("pandas", "3.0.2")], licences.get)
    assert rows == [
        "| numpy | 2.3.1 | BSD-3-Clause |",
        "| pandas | 3.0.2 | UNKNOWN (check by hand) |",
    ]
