import json
import pandas as pd
from src.data.split import get_train_test_split
from src.config.config import RAW_DATA_PATH, load_schema, BASE_DIR

def save_indices():
    df = pd.read_csv(RAW_DATA_PATH)
    df.columns = [col.replace('\ufeff', '') for col in df.columns]
    schema = load_schema()
    X_train, _, _, _ = get_train_test_split(df, schema["target_column"])
    dev_idx = list(X_train.index)
    
    out_dir = BASE_DIR / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "dev_indices.json", "w") as f:
        json.dump(dev_idx, f)

if __name__ == "__main__":
    save_indices()
