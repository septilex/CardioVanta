from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from src.config.config import load_schema

class PreprocessingFactory:
    def __init__(self):
        self.schema = load_schema()
        
    def get_preprocessing_pipeline(self, model_family: str):
        continuous_cols = [f["name"] for f in self.schema["features"] if f["type"] == "continuous"]
        binary_cols = [f["name"] for f in self.schema["features"] if f["type"] == "binary"]
        categorical_cols = [f["name"] for f in self.schema["features"] if f["type"] == "categorical"]
        
        if model_family in ["linear", "distance", "svm"]:
            # For scale-sensitive models: Standardize continuous, One-hot encode categorical.
            return ColumnTransformer(
                transformers=[
                    ("num", StandardScaler(), continuous_cols),
                    ("bin", "passthrough", binary_cols),
                    ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_cols)
                ],
                remainder="drop"
            )
        elif model_family in ["tree"]:
            # For tree models: Do not scale continuous. One-hot encode categorical to prevent 
            # integer codes from being treated as ordered continuous features.
            return ColumnTransformer(
                transformers=[
                    ("num", "passthrough", continuous_cols),
                    ("bin", "passthrough", binary_cols),
                    ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_cols)
                ],
                remainder="drop"
            )
        else:
            raise ValueError(f"Unknown model_family: {model_family}")
