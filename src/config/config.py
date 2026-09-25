import os
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_PATH = DATA_DIR / "raw" / "heart.csv"
SCHEMA_PATH = BASE_DIR / "configs" / "feature_schema.json"

TARGET_PYTHON_VERSION = "3.11"
RANDOM_SEED = 42
TEST_SIZE = 0.20

def load_schema():
    with open(SCHEMA_PATH, 'r') as f:
        return json.load(f)
