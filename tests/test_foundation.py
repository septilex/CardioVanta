import pytest
import pandas as pd
from src.config.config import RAW_DATA_PATH, load_schema
from src.data.validation import DatasetValidator
from src.data.split import get_train_test_split
from src.preprocessing.preprocessor import PreprocessingFactory

@pytest.fixture
def raw_data():
    df = pd.read_csv(RAW_DATA_PATH)
    # Fix BOM if present
    df.columns = [col.replace('\ufeff', '') for col in df.columns]
    return df

def test_dataset_loads_successfully(raw_data):
    assert not raw_data.empty

def test_exact_expected_columns_exist(raw_data):
    schema = load_schema()
    expected_cols = schema["feature_order"] + [schema["target_column"]]
    assert list(raw_data.columns) == expected_cols

def test_target_exists_and_binary(raw_data):
    schema = load_schema()
    assert schema["target_column"] in raw_data.columns
    unique_targets = set(raw_data[schema["target_column"]].unique())
    assert unique_targets.issubset({0, 1})

def test_feature_count(raw_data):
    schema = load_schema()
    assert len(raw_data.columns) - 1 == schema["feature_count"]
    assert schema["feature_count"] == 13

def test_schema_validation(raw_data):
    validator = DatasetValidator(raw_data)
    result = validator.validate()
    assert result["is_valid"]
    
def test_duplicate_count_detectable(raw_data):
    validator = DatasetValidator(raw_data)
    result = validator.validate()
    # There is 1 duplicate in the raw data
    assert any("duplicate" in w for w in result["warnings"])

def test_split_is_reproducible_and_stratified(raw_data):
    schema = load_schema()
    X_train1, X_test1, y_train1, y_test1 = get_train_test_split(raw_data, schema["target_column"])
    X_train2, X_test2, y_train2, y_test2 = get_train_test_split(raw_data, schema["target_column"])
    
    assert X_train1.equals(X_train2)
    assert y_train1.equals(y_train2)
    
    # Check stratification
    orig_ratio = raw_data[schema["target_column"]].mean()
    train_ratio = y_train1.mean()
    test_ratio = y_test1.mean()
    assert abs(orig_ratio - train_ratio) < 0.05
    assert abs(orig_ratio - test_ratio) < 0.05

def test_preprocessing_framework():
    factory = PreprocessingFactory()
    preprocessor = factory.get_preprocessing_pipeline('linear')
    assert preprocessor is not None
    # Verify it is an unfitted estimator
    assert not hasattr(preprocessor, 'transformers_')

def test_missing_value_check_works(raw_data):
    # Introduce a missing value
    df_missing = raw_data.copy()
    df_missing.loc[0, 'age'] = pd.NA
    validator = DatasetValidator(df_missing)
    result = validator.validate()
    # It logs a warning for missing values
    assert any("missing" in w.lower() for w in result["warnings"])
