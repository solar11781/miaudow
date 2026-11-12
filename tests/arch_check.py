"""Import-direction check for the layers of src/fieldshift (04-TECH-DESIGN sections 1-2).

Layers may import only the layers listed for them; modules at the package root (shared helpers) are open to all.
"""

import ast
from pathlib import Path

PACKAGE = "fieldshift"
ALLOWED: dict[str, set[str]] = {
    "data": set(),
    "features": {"data"},
    "ml": {"data", "features"},
    "engine": set(),  # the app reads precomputed artifacts and rules files only
    "api": {"engine"},
}


def _imported_layers(tree: ast.Module, module_parts: list[str]) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import: resolve against the importing module's package
                base = module_parts[: len(module_parts) - node.level]
                names = [".".join([*base, node.module] if node.module else base)]
            else:
                names = [node.module or ""]
        else:
            continue
        for name in names:
            parts = name.split(".")
            if len(parts) >= 2 and parts[0] == PACKAGE and parts[1] in ALLOWED:
                found.append((node.lineno, f"{PACKAGE}.{parts[1]}"))
    return found


def find_violations(package_dir: Path) -> list[str]:
    """Return one line per import that crosses the layer rules; an empty list means the rules hold."""
    violations: list[str] = []
    for path in sorted(package_dir.rglob("*.py")):
        rel = path.relative_to(package_dir)
        layer = rel.parts[0] if len(rel.parts) > 1 else None
        if layer not in ALLOWED:
            continue
        module_parts = [PACKAGE, *rel.with_suffix("").parts]
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for lineno, target in _imported_layers(tree, module_parts):
            target_layer = target.split(".")[1]
            if target_layer != layer and target_layer not in ALLOWED[layer]:
                violations.append(f"{rel.as_posix()}:{lineno}: layer '{layer}' must not import {target}")
    return violations
