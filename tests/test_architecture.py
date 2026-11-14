"""Layer rules of the tech design (04-TECH-DESIGN sections 1-2; CLAUDE.md: the app reads precomputed artifacts only).

Written before arch_check.py. Run: pytest tests/test_architecture.py
"""

from pathlib import Path

import pytest

from arch_check import find_violations

REPO = Path(__file__).resolve().parents[1]


def make_tree(root: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        path = root / "src" / "fieldshift" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root / "src" / "fieldshift"


def test_engine_never_imports_the_pipeline(tmp_path: Path) -> None:
    pkg = make_tree(
        tmp_path,
        {
            "engine/a.py": "from fieldshift.ml import models\n",
            "engine/b.py": "import fieldshift.data.nso\n",
            "engine/c.py": "from ..features import climate\n",
        },
    )
    found = find_violations(pkg)
    assert len(found) == 3
    assert all("engine" in v for v in found)


def test_api_imports_only_the_engine(tmp_path: Path) -> None:
    pkg = make_tree(
        tmp_path,
        {"api/a.py": "from fieldshift.engine.compare import compare\nfrom fieldshift.ml.models import fit\n"},
    )
    found = find_violations(pkg)
    assert len(found) == 1
    assert "fieldshift.ml" in found[0]


def test_lower_layers_never_import_higher_ones(tmp_path: Path) -> None:
    pkg = make_tree(
        tmp_path,
        {
            "data/a.py": "from fieldshift.features import climate\n",
            "features/a.py": "from fieldshift.ml import splits\n",
            "ml/a.py": "from fieldshift.engine import rules\n",
        },
    )
    assert len(find_violations(pkg)) == 3


def test_allowed_imports_pass(tmp_path: Path) -> None:
    pkg = make_tree(
        tmp_path,
        {
            "features/a.py": "from fieldshift.data import power\n",
            "ml/a.py": "from fieldshift.features import feature_table\nfrom fieldshift.data import nso\n",
            "engine/a.py": "import json\nimport yaml\nfrom pydantic import BaseModel\nfrom fieldshift.engine import schemas\n",
            "engine/b.py": "from .schemas import Plan\n",
            "api/a.py": "from fieldshift.engine import compare\n",
            "config.py": "X = 1\n",
            "engine/c.py": "from fieldshift import config\n",
        },
    )
    assert find_violations(pkg) == []


def test_this_repository_follows_the_layer_rules() -> None:
    pkg = REPO / "src" / "fieldshift"
    if not pkg.is_dir():
        pytest.skip("src/fieldshift does not exist yet")
    assert find_violations(pkg) == []
