"""데이터 전처리 유틸리티."""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler


def load_and_preprocess(filepath: str):
    """CSV 로드 및 전처리."""
    df = pd.read_csv(filepath)
    target_col = "price"
    X = df.drop(columns=[target_col]).values
    y = df[target_col].values
    scaler = StandardScaler()
    X = scaler.fit_transform(X)
    return X, y, scaler
