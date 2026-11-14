"""Make the miaudow_api package importable for tests run from the project root."""

import sys
from pathlib import Path

API = Path(__file__).resolve().parent
if str(API) not in sys.path:
    sys.path.insert(0, str(API))
