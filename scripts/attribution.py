"""Print the Python part of the README attribution table from a lock file (compliance CR-04, CR-05).

Usage: python scripts/attribution.py [requirements.lock]   (run in the environment where the lock is installed)
"""

import re
import sys
from collections.abc import Callable
from importlib import metadata
from pathlib import Path

PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?==([^\s;\\]+)")


def parse_lock(text: str) -> list[tuple[str, str]]:
    """Return (name, version) for every pinned requirement, sorted by name."""
    found = [m.groups() for line in text.splitlines() if (m := PIN.match(line.strip()))]
    return sorted((name.lower(), version) for name, version in found)


def installed_licence(name: str) -> str | None:
    """Licence of an installed distribution from its metadata, or None when it does not say."""
    try:
        meta = metadata.metadata(name)
    except metadata.PackageNotFoundError:
        return None
    if meta.get("License-Expression"):
        return meta["License-Expression"]
    classifiers = [c.split(" :: ")[-1] for c in meta.get_all("Classifier") or [] if c.startswith("License ::")]
    if classifiers:
        return ", ".join(classifiers)
    text = (meta.get("License") or "").strip()
    return text.splitlines()[0][:60] if text else None


def table_rows(packages: list[tuple[str, str]], licence_of: Callable[[str], str | None]) -> list[str]:
    return [f"| {name} | {version} | {licence_of(name) or 'UNKNOWN (check by hand)'} |" for name, version in packages]


if __name__ == "__main__":
    lock = Path(sys.argv[1] if len(sys.argv) > 1 else "requirements.lock")
    print("| Package | Version | Licence |\n|---|---|---|")
    print("\n".join(table_rows(parse_lock(lock.read_text(encoding="utf-8")), installed_licence)))
