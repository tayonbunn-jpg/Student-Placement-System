import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
import xgboost as xgb

from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

import joblib


class PlacementPredictor:
    def __init__(self):
        self.models = {
            "decision_tree": DecisionTreeClassifier(random_state=42),
            "random_forest": RandomForestClassifier(n_estimators=100, random_state=42),
            "svm": SVC(kernel="rbf", probability=True, random_state=42),
            "knn": KNeighborsClassifier(n_neighbors=5),
            "xgboost": xgb.XGBClassifier(eval_metric="logloss", random_state=42)
        }

        self.label_encoders = {}
        self.scaler = StandardScaler()

        self.best_model = None
        self.best_model_name = None
        self.feature_names = None

        self.model_results = {}

    # -------------------------
    # CLEAN DATA
    # -------------------------
    def preprocess_data(self, df, fit=False):
        df = df.copy()

        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

        if "student_id" in df.columns:
            df.drop(columns=["student_id"], inplace=True)

        # encode categoricals
        for col in df.select_dtypes(include=["object"]).columns:
            if col == "placement_status":
                continue

            if fit:
                le = LabelEncoder()
                df[col] = le.fit_transform(df[col].astype(str))
                self.label_encoders[col] = le
            else:
                if col in self.label_encoders:
                    le = self.label_encoders[col]
                    df[col] = df[col].astype(str).apply(
                        lambda x: le.transform([x])[0] if x in le.classes_ else -1
                    )

        # numeric conversion
        for col in df.columns:
            if col != "placement_status":
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df.fillna(0, inplace=True)

        # target encoding
        if "placement_status" in df.columns:
            y = df["placement_status"].astype(str).str.lower().map({
                "placed": 1,
                "not placed": 0,
                "yes": 1,
                "no": 0,
                "1": 1,
                "0": 0
            }).fillna(0)

            X = df.drop("placement_status", axis=1)

            if fit:
                self.feature_names = X.columns.tolist()
        else:
            X = df
            y = None

        # align features
        if not fit and self.feature_names:
            for col in self.feature_names:
                if col not in X.columns:
                    X[col] = 0
            X = X[self.feature_names]

        # scale
        if fit:
            X = self.scaler.fit_transform(X)
        else:
            X = self.scaler.transform(X)

        return X, y

    # -------------------------
    # TRAIN ALL MODELS + AUTO SELECT BEST
    # -------------------------
    def train_model(self, df, test_size=0.2):

        X, y = self.preprocess_data(df, fit=True)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=test_size,
            random_state=42,
            stratify=y if len(np.unique(y)) > 1 else None
        )

        results = {}

        best_score = 0
        best_name = None
        best_model = None

        for name, model in self.models.items():

            model.fit(X_train, y_train)
            preds = model.predict(X_test)

            acc = accuracy_score(y_test, preds)
            prec = precision_score(y_test, preds, average="weighted", zero_division=0)
            rec = recall_score(y_test, preds, average="weighted", zero_division=0)
            f1 = f1_score(y_test, preds, average="weighted", zero_division=0)

            results[name] = {
                "accuracy": acc,
                "precision": prec,
                "recall": rec,
                "f1_score": f1
            }

            # pick best model by accuracy
            if acc > best_score:
                best_score = acc
                best_name = name
                best_model = model

        # store best model
        self.best_model = best_model
        self.best_model_name = best_name
        self.model_results = results

        return {
            "best_model": best_name,
            "best_accuracy": best_score,
            "all_results": results
        }

    # -------------------------
    # PREDICT
    # -------------------------
    def predict(self, df):
        X, _ = self.preprocess_data(df, fit=False)

        preds = self.best_model.predict(X)

        probs = (
            self.best_model.predict_proba(X)
            if hasattr(self.best_model, "predict_proba")
            else None
        )

        results = []

        for i, p in enumerate(preds):
            confidence = float(max(probs[i]) * 100) if probs is not None else None

            results.append({
                "prediction": "Placed" if int(p) == 1 else "Not Placed",
                "confidence": round(confidence, 2) if confidence else None
            })

        return results

    # -------------------------
    # SAVE MODEL
    # -------------------------
    def save_model(self, path):
        joblib.dump({
            "model": self.best_model,
            "model_name": self.best_model_name,
            "scaler": self.scaler,
            "label_encoders": self.label_encoders,
            "feature_names": self.feature_names,
            "model_results": self.model_results
        }, path)

    # -------------------------
    # LOAD MODEL
    # -------------------------
    def load_model(self, path):
        data = joblib.load(path)

        self.best_model = data["model"]
        self.best_model_name = data["model_name"]
        self.scaler = data["scaler"]
        self.label_encoders = data["label_encoders"]
        self.feature_names = data["feature_names"]
        self.model_results = data.get("model_results", {})