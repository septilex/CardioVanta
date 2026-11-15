"""
Reproduce the contract 2.1.0 categorical-encoding verification (research tooling, not CI).

Matches every development row of data/raw/heart.csv (the 242 rows in data/processed/dev_indices.json;
the locked rows are never read past the parser's split) one-to-one to UCI processed.cleveland.data on
age, sex, trestbps, chol, thalach and oldpeak, then tabulates training code -> UCI code for each
categorical input and the outcome.

Usage:
    python scripts/research/verify_categorical_encoding.py PATH/TO/heart+disease.zip

The archive is https://archive.ics.uci.edu/static/public/45/heart+disease.zip; its SHA-256 must equal
the value pinned in src/cardiovanta/data/external_loader.py AUTHORITATIVE_SOURCES["zip_bundle"].
"""
from __future__ import annotations

import hashlib
import io
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from cardiovanta.data.external_loader import AUTHORITATIVE_SOURCES, parse_cleveland_dev_cohort  # noqa: E402

UCI_COLUMNS = ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg", "thalach", "exang",
               "oldpeak", "slope", "ca", "thal", "num"]
MATCH_KEY = ["age", "sex", "trestbps", "chol", "thalach", "oldpeak"]
CATEGORICAL = ["cp", "restecg", "slope", "thal", "ca", "fbs", "exang"]


def _key(frame: pd.DataFrame) -> pd.Series:
    return frame[MATCH_KEY].astype(float).round(1).astype(str).agg("|".join, axis=1)


def main(zip_path: str) -> int:
    data = Path(zip_path).read_bytes()
    expected = AUTHORITATIVE_SOURCES["zip_bundle"]["sha256"]
    if hashlib.sha256(data).hexdigest() != expected:
        print("archive SHA-256 does not match the pinned value; refusing to use it")
        return 2
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        uci = pd.read_csv(io.StringIO(z.read("processed.cleveland.data").decode()),
                          header=None, names=UCI_COLUMNS, na_values="?")
    dev = parse_cleveland_dev_cohort()
    rows = dev.X_13.copy()
    rows["disease"] = dev.y

    index = defaultdict(list)
    for i, k in enumerate(_key(uci)):
        index[k].append(i)

    pairs = {f: Counter() for f in CATEGORICAL + ["outcome"]}
    matched = 0
    for (_, row), k in zip(rows.iterrows(), _key(rows)):
        hits = index.get(k, [])
        if len(hits) != 1:
            continue
        matched += 1
        u = uci.iloc[hits[0]]
        for f in CATEGORICAL:
            pairs[f][(int(row[f]), None if pd.isna(u[f]) else int(u[f]))] += 1
        pairs["outcome"][(int(row["disease"]), int(u["num"] > 0))] += 1

    print(f"development rows: {len(rows)}; uniquely matched: {matched}")
    consistent = True
    for f, counter in pairs.items():
        by_code = defaultdict(set)
        for (code, uci_code), _ in counter.items():
            by_code[code].add(uci_code)
        ok = all(len(v) == 1 for v in by_code.values())
        consistent &= ok
        print(f"{f:8s} {'one-to-one' if ok else 'AMBIGUOUS'}  " +
              ", ".join(f"{c}->{u} (n={n})" for (c, u), n in sorted(counter.items(), key=lambda x: x[0][0])))
    return 0 if consistent and matched == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
