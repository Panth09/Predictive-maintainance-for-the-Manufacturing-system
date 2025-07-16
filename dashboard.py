from flask import Flask, render_template, jsonify
import pandas as pd
import random
import threading
import time

app = Flask(__name__)

# Simulated real-time data
real_time_data = {
    "time": [],
    "efficiency": []
}

# Function to simulate real-time data updates
def generate_real_time_data():
    while True:
        # Simulate new data
        current_time = pd.Timestamp.now().strftime("%H:%M:%S")
        efficiency = random.randint(50, 100)  # Random efficiency value between 50 and 100

        # Update the real-time data dictionary
        real_time_data["time"].append(current_time)
        real_time_data["efficiency"].append(efficiency)

        # Keep only the last 10 data points
        if len(real_time_data["time"]) > 10:
            real_time_data["time"].pop(0)
            real_time_data["efficiency"].pop(0)

        time.sleep(1)  # Update every second


@app.route("/")
def index():
    """Render the main dashboard page."""
    return render_template("real_time_dashboard.html")


@app.route("/api/real-time-data")
def real_time_data_api():
    """Provide real-time data as JSON for the graph."""
    return jsonify(real_time_data)


if __name__ == "__main__":
    # Start the real-time data generation in a separate thread
    threading.Thread(target=generate_real_time_data, daemon=True).start()

    # Run the Flask app
    app.run(debug=True, port=5001)