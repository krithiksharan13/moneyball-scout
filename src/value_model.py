"""Predict log market value from on-pitch output; the gap to the actual value is the scouting signal."""
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

PARAMS = dict(n_estimators=600, learning_rate=0.03, num_leaves=31, min_child_samples=20,
              subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, verbose=-1)


def fit(train: pd.DataFrame, features: list[str]) -> lgb.LGBMRegressor:
    model = lgb.LGBMRegressor(**PARAMS)
    model.fit(train[features], np.log(train.value_eur))
    return model


def oof_predict(df: pd.DataFrame, features: list[str], n_splits: int = 5) -> np.ndarray:
    """Out-of-fold log-value predictions, grouped by player so nobody is valued by a model that saw them."""
    pred = np.full(len(df), np.nan)
    for tr, te in GroupKFold(n_splits=n_splits).split(df, groups=df.player_id):
        pred[te] = fit(df.iloc[tr], features).predict(df.iloc[te][features])
    return pred


def score(df: pd.DataFrame, pred_log: np.ndarray) -> pd.DataFrame:
    """Attach predicted value and value gap (log ratio: +0.69 means the model values him at 2x the market)."""
    return df.assign(pred_value_eur=np.exp(pred_log), value_gap=pred_log - np.log(df.value_eur))
