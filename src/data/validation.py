import pandas as pd
from src.config.config import load_schema

class DatasetValidator:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.schema = load_schema()
        self.errors = []
        self.warnings = []

    def validate(self):
        self._check_columns()
        self._check_target()
        self._check_missing()
        self._check_duplicates()
        self._check_features()
        
        return {
            "is_valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings
        }
        
    def _check_columns(self):
        expected_cols = self.schema["feature_order"] + [self.schema["target_column"]]
        actual_cols = list(self.df.columns)
        
        if len(actual_cols) - 1 != self.schema["feature_count"]:
            self.errors.append(f"Expected {self.schema['feature_count']} features, got {len(actual_cols)-1}")
            
        if actual_cols != expected_cols:
            self.errors.append("Column order or names do not exactly match the schema.")
            missing = set(expected_cols) - set(actual_cols)
            unexpected = set(actual_cols) - set(expected_cols)
            if missing: self.errors.append(f"Missing columns: {missing}")
            if unexpected: self.errors.append(f"Unexpected columns: {unexpected}")

    def _check_target(self):
        target = self.schema["target_column"]
        if target in self.df.columns:
            unique_vals = set(self.df[target].unique())
            if not unique_vals.issubset(set(self.schema["target_values"])):
                self.errors.append(f"Target contains invalid values. Expected {self.schema['target_values']}, got {unique_vals}")
        else:
            self.errors.append(f"Target column '{target}' is missing.")

    def _check_missing(self):
        missing_counts = self.df.isnull().sum()
        total_missing = missing_counts.sum()
        if total_missing > 0:
            self.warnings.append(f"Dataset contains {total_missing} missing values.")
            for col, count in missing_counts.items():
                if count > 0:
                    self.warnings.append(f"Column '{col}' has {count} missing values.")

    def _check_duplicates(self):
        dups = self.df.duplicated().sum()
        if dups > 0:
            self.warnings.append(f"Dataset contains {dups} duplicate rows.")

    def _check_features(self):
        for feature in self.schema["features"]:
            name = feature["name"]
            if name not in self.df.columns:
                continue
                
            if not pd.api.types.is_numeric_dtype(self.df[name]):
                self.errors.append(f"Feature '{name}' is not numeric.")
                
            if feature["type"] in ["categorical", "binary"]:
                unique_vals = set(self.df[name].dropna().unique())
                if not unique_vals.issubset(set(feature["allowed_values"])):
                    self.warnings.append(f"Feature '{name}' has unexpected values: {unique_vals - set(feature['allowed_values'])}")
            
            elif feature["type"] == "continuous":
                min_val = self.df[name].min()
                max_val = self.df[name].max()
                if min_val < feature["min"] or max_val > feature["max"]:
                    self.warnings.append(f"Feature '{name}' out of expected range ({feature['min']} - {feature['max']}). Got {min_val} - {max_val}.")
