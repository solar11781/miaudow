"""Choose the normal-yield method on real data before the freeze commit (03-ML-SPEC section 3, E-010).

Usage: PYTHONPATH=src python scripts/choose_normal.py
Reads data/processed/training_table.csv; uses the rice seasons the model is trained on (spring and winter, D-66) and
the years before the first test year (D-69). Prints the errors of both methods, per season, and the choice.
"""

import json

import pandas as pd

from fieldshift.ml.evaluation import ML_SEASONS, TEST_YEARS
from fieldshift.ml.normal import compare_normal_methods

table = pd.read_csv("data/processed/training_table.csv")
rows = table[(table["crop"] == "rice") & table["season"].isin(ML_SEASONS)].reset_index(drop=True)
print(json.dumps(compare_normal_methods(rows, before_year=min(TEST_YEARS)), indent=2))
