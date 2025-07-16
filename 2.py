import pickle
import json
import numpy as np

# Load the trained predictive maintenance model
with open("predictive_model.pkl", "rb") as model_file:
    model = pickle.load(model_file)

# Example input parameters (replace with real sensor data)
parameters = {
    "temperature": 85.5,  # in Celsius
    "vibration": 2.3,     # in mm/s
    "pressure": 5.8,      # in bar
    "humidity": 45.0,     # in percentage
    "runtime": 6000,      # in hours
    "load": 0.75,         # as a fraction
    "speed": 1200         # in RPM
}

# Convert parameters to a feature array
features = np.array([parameters[key] for key in parameters.keys()]).reshape(1, -1)

# Predict maintenance needs
prediction = model.predict(features)
probability = model.predict_proba(features)  # If using a classification model

# Display the prediction
print("=== Predictive Maintenance Output ===")
if prediction[0] == 1:  # Assuming 1 means maintenance required
    print(f"Maintenance Required! (Confidence: {probability[0][1] * 100:.2f}%)")
else:
    print(f"No Immediate Maintenance Needed. (Confidence: {probability[0][0] * 100:.2f}%)")

# Provide actionable insights
print("\nRecommended Actions:")
if prediction[0] == 1:
    print("- Inspect cooling systems and bearings.")
    print("- Perform vibration analysis.")
    print("- Check for leaks or blockages.")
else:
    print("- Continue monitoring parameters.")