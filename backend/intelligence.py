from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score


FEATURE_COLUMNS = [
    'ret_1', 'ret_lag_1', 'ret_lag_2', 'rolling_vol_10', 'ewma_vol_10', 'sma_gap_10', 'drawdown', 'momentum_5'
]


def build_ml_features(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    x['ret_1'] = x['Close'].pct_change()
    x['ret_lag_1'] = x['ret_1'].shift(1)
    x['ret_lag_2'] = x['ret_1'].shift(2)
    x['rolling_vol_10'] = x['ret_1'].rolling(10).std()
    x['ewma_vol_10'] = x['ret_1'].ewm(span=10, adjust=False).std()
    sma10 = x['Close'].rolling(10).mean()
    x['sma_gap_10'] = x['Close'] / sma10 - 1
    x['drawdown'] = x['Close'] / x['Close'].cummax() - 1
    x['momentum_5'] = x['Close'].pct_change(5)
    x['target'] = (x['ret_1'].shift(-1) > 0).astype(int)
    x = x.dropna(subset=FEATURE_COLUMNS + ['target']).reset_index(drop=True)
    return x


class MLEngine:
    @staticmethod
    def validate(df: pd.DataFrame, test_size: float = 0.3, random_state: int = 42) -> dict:
        feat = build_ml_features(df)
        if len(feat) < 60:
            raise ValueError('Insufficient rows for ML validation; need at least 60 feature rows')
        split = int(len(feat) * (1 - test_size))
        if split <= 20 or len(feat) - split <= 20:
            raise ValueError('Insufficient train/test rows after split')
        train, test = feat.iloc[:split], feat.iloc[split:]
        X_train, y_train = train[FEATURE_COLUMNS], train['target']
        X_test, y_test = test[FEATURE_COLUMNS], test['target']

        clf = RandomForestClassifier(n_estimators=200, random_state=random_state, max_depth=6, min_samples_leaf=3)
        clf.fit(X_train, y_train)
        preds = clf.predict(X_test)
        warnings = []
        pmat = clf.predict_proba(X_test)
        if pmat.shape[1] == 1:
            cls = int(clf.classes_[0])
            probs = np.ones(len(X_test)) if cls == 1 else np.zeros(len(X_test))
            warnings.append("Probability degenerate: training saw one class.")
        else:
            probs = pmat[:, 1]

        auc = None
        if len(np.unique(y_test)) > 1:
            auc = float(roc_auc_score(y_test, probs))
        else:
            warnings.append('ROC-AUC unavailable: validation target has one class.')

        return {
            'accuracy': float(accuracy_score(y_test, preds)),
            'precision': float(precision_score(y_test, preds, zero_division=0)),
            'recall': float(recall_score(y_test, preds, zero_division=0)),
            'f1': float(f1_score(y_test, preds, zero_division=0)),
            'roc_auc': auc,
            'confusion_matrix': confusion_matrix(y_test, preds).tolist(),
            'feature_importance': {k: float(v) for k, v in zip(FEATURE_COLUMNS, clf.feature_importances_)},
            'latest_probability': float(probs[-1]),
            'latest_confidence': float(max(probs[-1], 1 - probs[-1])),
            'train_rows': int(len(train)),
            'validation_rows': int(len(test)),
            'warnings': warnings,
            'generated_at': datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def predict_latest(df: pd.DataFrame, random_state: int = 42) -> dict:
        feat = build_ml_features(df)
        if len(feat) < 60:
            raise ValueError('Insufficient rows for ML prediction; need at least 60 feature rows')
        X = feat[FEATURE_COLUMNS]
        y = feat['target']
        clf = RandomForestClassifier(n_estimators=200, random_state=random_state, max_depth=6, min_samples_leaf=3)
        clf.fit(X.iloc[:-1], y.iloc[:-1])
        pmat = clf.predict_proba(X.iloc[[-1]])
        if pmat.shape[1] == 1:
            p = float(1.0 if int(clf.classes_[0]) == 1 else 0.0)
            warnings=["Probability degenerate: training saw one class."]
        else:
            p = float(pmat[:, 1][0])
            warnings=[]
        return {
            'latest_probability': p,
            'latest_confidence': float(max(p, 1 - p)),
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'warnings': warnings,
        }
