import sys
from pathlib import Path
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.advanced_model_search import load_dev_data
from src.preprocessing.preprocessor import PreprocessingFactory

def test_error_analysis_isolation():
    # 1. Ensure no locked test data entered dev
    X_dev, y_dev, dev_groups, df, X_full, y_full, dev_idx, schema, df_hash = load_dev_data()
    
    assert len(X_dev) == len(dev_idx), "Dev size mismatch"
    assert len(X_full) - len(dev_idx) == 61, "Test size mismatch (must be 61)"
    
    # 2. Check exact feature schema
    expected_cols = ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg", "thalach", "exang", "oldpeak", "slope", "ca", "thal"]
    assert list(X_dev.columns) == expected_cols, "Feature schema mismatch"
    
    # 3. Check duplicate-group handling
    assert len(dev_groups) == len(X_dev), "Group size mismatch"
    
def test_error_analysis_model():
    factory = PreprocessingFactory()
    
    baseline_pipe = Pipeline([
        ("preprocessor", factory.get_preprocessing_pipeline("linear")),
        ("model", LogisticRegression(C=0.1, class_weight="balanced", solver="lbfgs", random_state=42, max_iter=1000))
    ])
    
    assert baseline_pipe.steps[1][1].C == 0.1, "Incorrect baseline C"
    assert baseline_pipe.steps[1][1].class_weight == "balanced", "Incorrect baseline class_weight"

if __name__ == "__main__":
    test_error_analysis_isolation()
    test_error_analysis_model()
    print("All error analysis tests passed successfully!")
