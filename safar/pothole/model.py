"""
SAFAR Pothole Model Training, Evaluation, and Persistence Layer
"""

import os
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_recall_fscore_support

from .config import CLASS_ID_TO_LABEL
from .validation import PotholeDataValidator

DEFAULT_MODEL_PATH = os.path.join(os.path.dirname(__file__), "pothole_model.joblib")


class PotholeModelTrainer:
    """
    Trains, benchmarks, evaluates, and persists pothole classification models.
    """

    def __init__(self, random_state: int = 50):
        self.random_state = random_state
        self.feature_cols = ["PH_Width", "PH_Length", "PH_Depth"]
        self.target_col = "PH_Type"
        self.model = None

    def prepare_data(self, df: pd.DataFrame, test_size: float = 0.2) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        Validates dataset and creates stratified train/test split.
        """
        validation_report = PotholeDataValidator.validate_dataframe(df)
        clean_df = validation_report["clean_df"]

        X = clean_df[self.feature_cols]
        y = clean_df[self.target_col]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=self.random_state, stratify=y
        )
        return X_train, X_test, y_train, y_test

    def benchmark_models(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Compares DecisionTree, RandomForest, GradientBoosting, and ExtraTrees.
        """
        X_train, X_test, y_train, y_test = self.prepare_data(df)
        X = df[self.feature_cols]
        y = df[self.target_col]

        candidates = {
            "DecisionTree": DecisionTreeClassifier(random_state=self.random_state),
            "RandomForest": RandomForestClassifier(n_estimators=100, max_depth=6, random_state=self.random_state),
            "GradientBoosting": GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=self.random_state),
            "ExtraTrees": ExtraTreesClassifier(n_estimators=100, max_depth=6, random_state=self.random_state)
        }

        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=self.random_state)
        benchmark_results = {}

        for name, clf in candidates.items():
            clf.fit(X_train, y_train)
            y_pred = clf.predict(X_test)

            acc = accuracy_score(y_test, y_pred)
            prec, rec, f1, _ = precision_recall_fscore_support(y_test, y_pred, average="macro", zero_division=0)
            cv_scores = cross_val_score(clf, X, y, cv=cv, scoring="accuracy")

            cm = confusion_matrix(y_test, y_pred)
            report = classification_report(
                y_test, y_pred,
                target_names=[CLASS_ID_TO_LABEL[i] for i in sorted(CLASS_ID_TO_LABEL.keys())],
                digits=4,
                output_dict=True
            )

            benchmark_results[name] = {
                "model": clf,
                "test_accuracy": acc,
                "macro_precision": prec,
                "macro_recall": rec,
                "macro_f1": f1,
                "cv_mean": float(cv_scores.mean()),
                "cv_std": float(cv_scores.std()),
                "confusion_matrix": cm.tolist(),
                "classification_report": report
            }

        return benchmark_results

    def train_and_save(
        self,
        df: pd.DataFrame,
        model_type: str = "RandomForest",
        model_save_path: str = DEFAULT_MODEL_PATH
    ) -> Dict[str, Any]:
        """
        Trains the selected model on the dataset, evaluates metrics, and serializes to disk.
        """
        X_train, X_test, y_train, y_test = self.prepare_data(df)

        if model_type == "DecisionTree":
            clf = DecisionTreeClassifier(random_state=self.random_state)
        elif model_type == "GradientBoosting":
            clf = GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=self.random_state)
        elif model_type == "ExtraTrees":
            clf = ExtraTreesClassifier(n_estimators=100, max_depth=6, random_state=self.random_state)
        else: # Default: RandomForest for robust generalization and smooth probability estimates
            clf = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=self.random_state)

        clf.fit(X_train, y_train)
        self.model = clf

        # Evaluate on test split
        y_pred = clf.predict(X_test)
        y_prob = clf.predict_proba(X_test) if hasattr(clf, "predict_proba") else None

        acc = accuracy_score(y_test, y_pred)
        report_str = classification_report(
            y_test, y_pred,
            target_names=[CLASS_ID_TO_LABEL[i] for i in sorted(CLASS_ID_TO_LABEL.keys())],
            digits=4
        )
        cm = confusion_matrix(y_test, y_pred)

        payload = {
            "model": clf,
            "model_type": model_type,
            "feature_names": self.feature_cols,
            "class_id_to_label": CLASS_ID_TO_LABEL,
            "test_accuracy": acc,
            "random_state": self.random_state
        }

        os.makedirs(os.path.dirname(os.path.abspath(model_save_path)), exist_ok=True)
        joblib.dump(payload, model_save_path)

        return {
            "model_type": model_type,
            "save_path": model_save_path,
            "test_accuracy": acc,
            "classification_report": report_str,
            "confusion_matrix": cm
        }

    @staticmethod
    def load_model(model_path: str = DEFAULT_MODEL_PATH) -> Any:
        """
        Loads persisted model payload from disk.
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Trained pothole model not found at {model_path}. Run train_model.py first.")
        payload = joblib.load(model_path)
        return payload
