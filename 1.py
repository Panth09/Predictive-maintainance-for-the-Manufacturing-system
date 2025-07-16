import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import openai
import random
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple

class PredictiveMaintenance:
    def __init__(self):
        self.thresholds = {
            "temperature": {"normal": (20, 60), "warning": (60, 80), "critical": 80, "weight": 25},
            "vibration": {"normal": (0.1, 2.0), "warning": (2.0, 3.0), "critical": 3.0, "weight": 20},
            "pressure": {"normal": (2.0, 8.0), "warning": (1.5, 8.5), "critical": (1.0, 9.0), "weight": 15},
            "humidity": {"normal": (30, 60), "warning": (60, 70), "critical": 70, "weight": 10},
            "runtime": {"normal": (0, 5000), "warning": (5000, 8000), "critical": 8000, "weight": 20},
            "load": {"normal": (0, 0.7), "warning": (0.7, 0.9), "critical": 0.9, "weight": 10},
            "speed": {"normal": (500, 2000), "warning": (2000, 2500), "critical": 2500, "weight": 10}
        }
        self.maintenance_history = self._load_maintenance_history()
        self.model = self._load_or_train_model()
        self.scaler = self._load_or_create_scaler()

    def _load_or_train_model(self):
        model_file = "maintenance_model.joblib"
        if os.path.exists(model_file):
            return joblib.load(model_file)
        else:
            return self._train_new_model()

    def _load_or_create_scaler(self):
        scaler_file = "scaler.joblib"
        if os.path.exists(scaler_file):
            return joblib.load(scaler_file)
        else:
            return StandardScaler()

    def _train_new_model(self):
        # Generate synthetic training data
        n_samples = 1000
        training_data = []
        
        for _ in range(n_samples):
            params = self.generate_parameters()
            likelihood, issues = self.calculate_failure_likelihood(params)
            failure_status = 1 if likelihood > 50 else 0
            params['failure'] = failure_status
            training_data.append(params)

        # Convert to DataFrame
        df = pd.DataFrame(training_data)
        df = df.drop(['timestamp'], axis=1)
        
        # Split features and target
        X = df.drop('failure', axis=1)
        y = df['failure']

        # Scale the features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train test split
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

        # Train model
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)

        # Save model and scaler
        joblib.dump(model, 'maintenance_model.joblib')
        joblib.dump(self.scaler, 'scaler.joblib')

        print(f"Model Training Score: {model.score(X_test, y_test):.2f}")
        return model

    def predict_failure(self, parameters: Dict) -> Tuple[float, List[str]]:
        # Prepare the features
        features = pd.DataFrame([parameters])
        features = features.drop(['timestamp'], axis=1)
        
        # Scale the features
        features_scaled = self.scaler.transform(features)
        
        # Get prediction and probability
        failure_prob = self.model.predict_proba(features_scaled)[0][1]
        prediction = self.model.predict(features_scaled)[0]

        # Get feature importances
        feature_importance = dict(zip(features.columns, 
                                    self.model.feature_importances_))
        
        # Sort features by importance
        important_features = sorted(feature_importance.items(), 
                                  key=lambda x: x[1], 
                                  reverse=True)
        
        return failure_prob * 100, important_features

    def generate_parameters(self) -> Dict:
        return {
            "timestamp": datetime.now().isoformat(),
            "temperature": round(random.uniform(20.0, 100.0), 2),
            "vibration": round(random.uniform(0.1, 5.0), 2),
            "pressure": round(random.uniform(1.0, 10.0), 2),
            "humidity": round(random.uniform(30.0, 90.0), 2),
            "runtime": random.randint(0, 10000),
            "load": round(random.uniform(0.0, 1.0), 2),
            "speed": random.randint(500, 3000)
        }

    def assess_parameter_status(self, param_name: str, value: float) -> Tuple[str, float]:
        threshold = self.thresholds[param_name]
        if isinstance(threshold["critical"], tuple):
            if value < threshold["critical"][0] or value > threshold["critical"][1]:
                return "CRITICAL", 1.0
        elif value > threshold["critical"]:
            return "CRITICAL", 1.0
        
        if isinstance(threshold["warning"], tuple):
            if value < threshold["warning"][0] or value > threshold["warning"][1]:
                return "WARNING", 0.5
        elif value > threshold["warning"][1]:
            return "WARNING", 0.5
        
        return "NORMAL", 0.0

    def calculate_failure_likelihood(self, params: Dict) -> Tuple[float, List[Dict]]:
        likelihood = 0
        issues = []

        for param_name, value in params.items():
            if param_name != "timestamp":
                status, risk_factor = self.assess_parameter_status(param_name, value)
                weight = self.thresholds[param_name]["weight"]
                likelihood += risk_factor * weight
                
                if status != "NORMAL":
                    issues.append({
                        "parameter": param_name,
                        "value": value,
                        "status": status,
                        "risk_contribution": risk_factor * weight
                    })

        return min(likelihood, 100), sorted(issues, key=lambda x: x["risk_contribution"], reverse=True)

    def generate_recommendations(self, params: Dict, issues: List[Dict]) -> str:
        if not issues:
            return "All parameters are within normal operating ranges. Continue regular monitoring."

        recommendations = []
        total_runtime = params["runtime"]
        maintenance_due = total_runtime - self._get_last_maintenance_time()

        if maintenance_due > 5000:
            recommendations.append("⚠️ OVERDUE: Regular maintenance schedule exceeded by "
                                f"{maintenance_due-5000} hours")

        for issue in issues:
            param = issue["parameter"]
            status = issue["status"]
            value = issue["value"]
            
            if status == "CRITICAL":
                recommendations.append(f"🔴 URGENT: {param.capitalize()} is critically high "
                                    f"({value}). Immediate inspection required.")
            else:
                recommendations.append(f"🟡 WARNING: {param.capitalize()} is above normal "
                                    f"({value}). Schedule inspection within 48 hours.")

        return "\n".join(recommendations)

    def generate_ml_recommendations(self, params: Dict) -> str:
        failure_prob, important_features = self.predict_failure(params)
        
        recommendations = []
        
        # Add failure probability
        if failure_prob > 75:
            recommendations.append(f"🔴 CRITICAL: {failure_prob:.1f}% chance of failure")
        elif failure_prob > 50:
            recommendations.append(f"🟡 WARNING: {failure_prob:.1f}% chance of failure")
        else:
            recommendations.append(f"✅ NORMAL: {failure_prob:.1f}% chance of failure")

        # Add top contributing factors
        recommendations.append("\nTop contributing factors:")
        for feature, importance in important_features[:3]:
            recommendations.append(f"- {feature.capitalize()}: {importance:.3f} importance")

        return "\n".join(recommendations)

    def _load_maintenance_history(self) -> List[Dict]:
        history_file = "maintenance_history.json"
        if os.path.exists(history_file):
            with open(history_file, "r") as f:
                return json.load(f)
        return []

    def _get_last_maintenance_time(self) -> int:
        if not self.maintenance_history:
            return 0
        return self.maintenance_history[-1].get("runtime", 0)

    def save_parameters(self, parameters: Dict):
        with open("sensor_data.json", "a") as f:
            json.dump(parameters, f)
            f.write("\n")

def main():
    pm = PredictiveMaintenance()
    parameters = pm.generate_parameters()
    pm.save_parameters(parameters)
    
    # Get both traditional and ML-based predictions
    likelihood, issues = pm.calculate_failure_likelihood(parameters)
    traditional_recommendations = pm.generate_recommendations(parameters, issues)
    ml_recommendations = pm.generate_ml_recommendations(parameters)

    print("=== System Status Report ===")
    print(f"Timestamp: {parameters['timestamp']}")
    print("\n=== Parameters ===")
    for key, value in parameters.items():
        if key != "timestamp":
            print(f"{key.capitalize()}: {value}")

    print("\n=== ML-Based Predictions ===")
    print(ml_recommendations)

    print("\n=== Traditional Analysis ===")
    print(f"Failure Likelihood: {likelihood:.1f}%")
    print("\nRecommendations:")
    print(traditional_recommendations)

if __name__ == "__main__":
    main()