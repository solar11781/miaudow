---
paths:
  - "src/**/*.py"
  - "tests/**/*.py"
  - "scripts/**/*.py"
---

# Python conventions (D-125; architecture from the tech design)

## Where code goes

| Folder | Holds | May import |
|---|---|---|
| `src/fieldshift/data/` | downloads, parsers, caches of public data | nothing from other layers |
| `src/fieldshift/features/` | season windows, climate indices, official-condition counts, feature table | `data` |
| `src/fieldshift/ml/` | splits, normal yield, baselines, models, evaluation, export to `artifacts/` | `data`, `features` |
| `src/fieldshift/engine/` | schemas, rules loading, `compare()` | nothing from other layers: reads `rules/*.yaml` and `artifacts/*.json` only |
| `src/fieldshift/api/` | FastAPI app serving engine results | `engine` |
| `scripts/` | command-line entry points that run the pipeline | anything |

`tests/test_architecture.py` fails the build when a layer imports a layer it may not.

## Code

- Python 3.11 syntax or newer. Type hints on every function signature; no `Any` in `engine/` or `api/`.
- API and engine schemas are pydantic models whose names and fields mirror the UI/UX spec's data contract exactly.
- Names: `snake_case` modules, functions and variables; `PascalCase` classes; `UPPER_CASE` module constants.
- `pathlib.Path` for files; no absolute paths; paths relative to the repository root are built in one place per layer.
- No number, threshold or label in code without a source: it lives in `rules/*.yaml` with its source id, and code
  reads it from there.
- Errors: raise a specific exception with a message that names the input; never swallow an exception; unknown data
  symbols fail loudly. Invalid API input returns HTTP 422.
- No `print` in `src/` (use return values; the API returns errors as responses). No personal data in logs.
- Randomness only with a fixed seed passed in; no random row splits.

## Tests

- pytest. One test file per module: `tests/test_<module>.py`. Shared JSON fixtures in `tests/fixtures/`.
- Expected values come from the spec, real data or an external fact, written in the test as literals with a comment
  naming the source.
- Tests that call real external services are marked `@pytest.mark.live` and skipped by default.
