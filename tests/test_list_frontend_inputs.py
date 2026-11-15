"""List of the frontend's shipped data and media inputs with their sha256 (competition rule: data provenance).

Written before scripts/list_frontend_inputs.py. Run: pytest tests/test_list_frontend_inputs.py
"""

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("list_frontend_inputs", REPO / "scripts" / "list_frontend_inputs.py")
inputs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inputs)


def test_sha256_of_a_file(tmp_path: Path) -> None:
    f = tmp_path / "abc.txt"
    f.write_bytes(b"abc")
    # FIPS 180-2 appendix B.1: SHA-256("abc")
    assert inputs.sha256_of(f) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_render_lists_each_group_with_its_note_and_sorted_files(tmp_path: Path) -> None:
    (tmp_path / "media" / "b").mkdir(parents=True)
    (tmp_path / "media" / "b" / "2.webp").write_bytes(b"abc")
    (tmp_path / "media" / "1.webp").write_bytes(b"")
    text = inputs.render(tmp_path, [("media", "**/*.webp", "Pictures, made by hand.")])
    assert text.splitlines() == [
        inputs.HEADER,
        "",
        "## media",
        "",
        "Pictures, made by hand.",
        "",
        # SHA-256 of the empty input: FIPS 180-2 / NIST CSRC example values
        "- `media/1.webp` e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "- `media/b/2.webp` ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
    ]


def test_every_group_has_files() -> None:
    for folder, pattern, _ in inputs.GROUPS:
        assert list((REPO / folder).glob(pattern)), folder


def test_committed_list_matches_the_files() -> None:
    committed = (REPO / inputs.OUT).read_text(encoding="utf-8")
    assert committed == inputs.render(REPO, inputs.GROUPS), "run: python scripts/list_frontend_inputs.py"
