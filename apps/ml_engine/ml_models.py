import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
import xgboost as xgb
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import joblib
import os

class PlacementPredictor:
    def __init__(self):
        self.models = {
            'decision_tree': DecisionTreeClassifier(random_state=42),
            'random_forest': RandomForestClassifier(n_estimators=100, random_state=42),
            'svm': SVC(kernel='rbf', probability=True, random_state=42),
            'knn': KNeighborsClassifier(n_neighbors=5),
            'xgboost': xgb.XGBClassifier(random_state=42)
        }
        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.current_model = None
        self.selected_model_name = None
        self.feature_names = None
        
    def preprocess_data(self, df, fit=False):
        """Preprocess the data for training or prediction"""
        data = df.copy()

        # Drop columns that should not be used as model features
        if 'student_id' in data.columns:
            data = data.drop(columns=['student_id'])
        
        # Handle categorical variables
        categorical_cols = data.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            if col != 'placement_status':  # Target variable
                if fit:
                    self.label_encoders[col] = LabelEncoder()
                    data[col] = self.label_encoders[col].fit_transform(data[col].astype(str))
                else:
                    if col in self.label_encoders:
                        data[col] = self.safe_transform(data[col].astype(str), self.label_encoders[col])

        # Convert remaining object columns to numeric where possible
        remaining_object_cols = [col for col in data.select_dtypes(include=['object']).columns if col != 'placement_status']
        for col in remaining_object_cols:
            data[col] = pd.to_numeric(data[col], errors='coerce')
        
        # Handle missing values
        data = data.fillna(data.mean())
        
        # Separate features and target if target exists
        if 'placement_status' in data.columns:
            y = data['placement_status']
            X = data.drop('placement_status', axis=1)
            if fit:
                self.feature_names = X.columns.tolist()
        else:
            X = data
            y = None

        # Align prediction data with training features
        if not fit and self.feature_names is not None:
            for feature in self.feature_names:
                if feature not in X.columns:
                    X[feature] = np.nan
            X = X[self.feature_names]
        
        # Scale numerical features
        if fit:
            X_scaled = self.scaler.fit_transform(X)
        else:
            X_scaled = self.scaler.transform(X)
            
        return X_scaled, y

    def safe_transform(self, series, encoder):
        transformed = []
        known_labels = set(encoder.classes_)
        for value in series:
            if value in known_labels:
                transformed.append(int(encoder.transform([value])[0]))
            else:
                transformed.append(-1)
        return pd.Series(transformed, index=series.index)
    
    def train_model(self, df, model_name='random_forest'):
        """Train the selected model"""
        X, y = self.preprocess_data(df, fit=True)
        
        # Split the data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Select and train model
        self.selected_model_name = model_name
        self.current_model = self.models[model_name]
        self.current_model.fit(X_train, y_train)
        
        # Make predictions
        y_pred = self.current_model.predict(X_test)
        y_prob = self.current_model.predict_proba(X_test) if hasattr(self.current_model, 'predict_proba') else None
        
        # Calculate metrics
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, average='weighted'),
            'recall': recall_score(y_test, y_pred, average='weighted'),
            'f1_score': f1_score(y_test, y_pred, average='weighted'),
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist()
        }
        
        return metrics, y_prob
    
    def predict(self, student_data):
        """Predict placement for new students"""
        if self.current_model is None:
            raise Exception("Model not trained yet!")
            
        X, _ = self.preprocess_data(student_data, fit=False)
        predictions = self.current_model.predict(X)
        probabilities = self.current_model.predict_proba(X) if hasattr(self.current_model, 'predict_proba') else None
        
        results = []
        for i, pred in enumerate(predictions):
            result = {
                'prediction': 'Placed' if pred == 1 else 'Not Placed',
                'probability': probabilities[i].tolist() if probabilities is not None else None,
                'confidence': max(probabilities[i]) if probabilities is not None else None
            }
            results.append(result)
            
        return results
    
    def save_model(self, filepath):
        """Save trained model and preprocessors"""
        model_data = {
            'model': self.current_model,
            'label_encoders': self.label_encoders,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'model_name': self.selected_model_name
        }
        joblib.dump(model_data, filepath)
        
    def load_model(self, filepath):
        """Load trained model and preprocessors"""
        model_data = joblib.load(filepath)
        self.current_model = model_data['model']
        self.label_encoders = model_data['label_encoders']
        self.scaler = model_data['scaler']
        self.feature_names = model_data['feature_names']
        self.selected_model_name = model_data['model_name']