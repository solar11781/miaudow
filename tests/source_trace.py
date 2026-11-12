"""Source tracing for API responses (hard rule H5; UI-UX-SPEC section 11: every id used is a key of `sources`)."""

import re

ID_LISTS = ("source_ids", "values_source_ids", "principle_source_ids")
ID_SINGLES = ("threshold_source_id", "computed_by")
REGISTER_ROW = re.compile(r"^\|\s*((?:R-[A-Z]+\d+[a-z]?)|(?:E-\d{3}[a-z]?))\s*\|", re.MULTILINE)


def _walk(node: object, path: str, used: list[tuple[str, str]], problems: list[str]) -> None:
    if isinstance(node, list):
        for i, item in enumerate(node):
            _walk(item, f"{path}[{i}]", used, problems)
        return
    if not isinstance(node, dict):
        return
    if {"value", "unit", "source_ids"} <= node.keys() and not node["source_ids"]:
        problems.append(f"{path}: displayed value has no source")
    for key, child in node.items():
        if key == "sources" and path == "$":
            continue
        if key in ID_LISTS and isinstance(child, list):
            used.extend((f"{path}.{key}", sid) for sid in child)
        elif key in ID_SINGLES and isinstance(child, str):
            used.append((f"{path}.{key}", child))
        else:
            _walk(child, f"{path}.{key}", used, problems)


def check_response(response: dict, known_ids: set[str] | None) -> list[str]:
    """Return the tracing problems of one API response; known_ids None skips the register check."""
    problems: list[str] = []
    used: list[tuple[str, str]] = []
    _walk(response, "$", used, problems)
    sources = response.get("sources", {})
    problems += [f"{where}: {sid} is not in this response's sources" for where, sid in used if sid not in sources]
    for key, facts in sources.items():
        if facts.get("id") != key:
            problems.append(f"sources.{key}: facts carry id {facts.get('id')!r}")
        if known_ids is not None and key not in known_ids:
            problems.append(f"sources.{key}: not in REFERENCES or EXPERIMENTS")
    return problems


def known_ids_from(references_md: str, experiments_md: str) -> set[str]:
    """Ids from the first column of the REFERENCES and EXPERIMENTS tables."""
    return set(REGISTER_ROW.findall(references_md)) | set(REGISTER_ROW.findall(experiments_md))
