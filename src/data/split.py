import pandas as pd
from sklearn.model_selection import train_test_split
from src.config.config import RANDOM_SEED, TEST_SIZE

def get_train_test_split(df: pd.DataFrame, target_col: str):
    X = df.drop(columns=[target_col])
    y = df[target_col]
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, 
        test_size=TEST_SIZE, 
        random_state=RANDOM_SEED, 
        stratify=y
    )
    return X_train, X_test, y_train, y_test
