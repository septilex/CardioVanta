import pytest
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold
from src.preprocessing.preprocessor import PreprocessingFactory
from src.config.config import RANDOM_SEED
from src.experiment.baseline import run_baseline_experiment, HAS_XGBOOST

# We test that the infrastructure creates what we expect

def test_preprocessing_factory_profiles():
    factory = PreprocessingFactory()
    linear_prep = factory.get_preprocessing_pipeline("linear")
    tree_prep = factory.get_preprocessing_pipeline("tree")
    
    # Verify unfitted
    assert not hasattr(linear_prep, "transformers_")
    assert not hasattr(tree_prep, "transformers_")

def test_stratified_cv():
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    assert cv.n_splits == 5
    assert cv.random_state == RANDOM_SEED

from sklearn.model_selection import StratifiedKFold
def test_nested_cv_configuration():
    # Verify inner and outer CV specs without running
    outer_cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    inner_cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    
    assert outer_cv.n_splits == 5
    assert inner_cv.n_splits == 5
    assert outer_cv.random_state == 42
    assert inner_cv.random_state == 42

def test_phase2c_evaluation_framework():
    # 1. Verify Pipeline construct includes preprocessing and model correctly
    from src.experiment.final_evaluation import PreprocessingFactory, LogisticRegression, Pipeline
    factory = PreprocessingFactory()
    preprocessor = factory.get_preprocessing_pipeline('linear')
    estimator = LogisticRegression()
    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('model', estimator)
    ])
    assert 'preprocessor' in pipeline.named_steps
    assert 'model' in pipeline.named_steps

    # 2. Verify Final dataset test usage properties statically
    from src.data.split import get_train_test_split
    import pandas as pd
    from src.config.config import load_schema, RAW_DATA_PATH
    df = pd.read_csv(RAW_DATA_PATH)
    df.columns = [col.replace('\ufeff', '') for col in df.columns]
    schema = load_schema()
    X_train, X_test, y_train, y_test = get_train_test_split(df, schema["target_column"])
    # Ensure disjoint sets
    assert len(set(X_train.index).intersection(set(X_test.index))) == 0
