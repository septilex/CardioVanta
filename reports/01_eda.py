import pandas as pd
from src.config.config import RAW_DATA_PATH

def run_eda():
    df = pd.read_csv(RAW_DATA_PATH)
    df.columns = [col.replace('\ufeff', '') for col in df.columns]
    
    print("=== CARDIOVANTA DATASET EDA ===")
    print(f"Row count: {len(df)}")
    print(f"Column count: {len(df.columns)}")
    print(f"Feature count: {len(df.columns) - 1}")
    print("\nColumns:", list(df.columns))
    
    print("\nData Types:")
    print(df.dtypes)
    
    print("\nMissing Values:")
    print(df.isnull().sum())
    
    print(f"\nDuplicate count: {df.duplicated().sum()}")
    
    print("\nTarget Distribution:")
    print(df['target'].value_counts())
    
    print("\nFeature Summaries (Min/Max/Unique for low cardinality):")
    for col in df.columns:
        if col == 'target': continue
        if df[col].nunique() < 10:
            print(f"- {col} (Categorical/Binary): {sorted(df[col].unique().tolist())}")
        else:
            print(f"- {col} (Continuous): Min={df[col].min()}, Max={df[col].max()}")


    print("\nCorrelation Matrix (Numeric):")
    print(df.corr().round(2))
    
    print("\nFeature-Target Comparisons (Mean grouped by target):")
    print(df.groupby('target').mean().round(2))
    
    print("\nOutlier Inspection (IQR method for Continuous):")
    continuous = ['age', 'trestbps', 'chol', 'thalach', 'oldpeak']
    for col in continuous:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR
        outliers = df[(df[col] < lower) | (df[col] > upper)]
        print(f"  - {col}: {len(outliers)} potential outliers")

if __name__ == '__main__':
    run_eda()
