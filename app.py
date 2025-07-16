from flask import Flask, jsonify, render_template, request
import sqlite3
import pandas as pd
import random
import time
from threading import Thread
from datetime import datetime

app = Flask(__name__)

# Global variables for stop flags
stop_flags = {
    "cnc": {"status": False},
    "hydraulic_press": {"status": False},
    "conveyor_belt": {"status": False},
    "industrial_fan": {"status": False},
    "air_compressor": {"status": False}
}

# Limits for each machine
limits = {
    "cnc": {
        "Temp": {"lower": 40, "maintenance": 80, "upper": 100, "critical": 110},
        "Vibration": {"lower": 20, "maintenance": 50, "upper": 70, "critical": 85},
        "RPM": {"lower": 500, "maintenance": 1500, "upper": 2000, "critical": 2200}
    },
    "hydraulic_press": {
        "Pressure": {"lower": 50, "maintenance": 120, "upper": 180, "critical": 200},
        "Temp": {"lower": 20, "maintenance": 60, "upper": 80, "critical": 100},
        "Vibration": {"lower": 5, "maintenance": 20, "upper": 40, "critical": 50}
    },
    "conveyor_belt": {
        "Vibration": {"lower": 5, "maintenance": 20, "upper": 40, "critical": 50},
        "RPM": {"lower": 500, "maintenance": 1500, "upper": 2000, "critical": 2500},
        "Temp": {"lower": 20, "maintenance": 60, "upper": 80, "critical": 100}
    },
    "industrial_fan": {
        "Vibration": {"lower": 5, "maintenance": 20, "upper": 40, "critical": 50},
        "RPM": {"lower": 500, "maintenance": 1500, "upper": 2000, "critical": 2500},
        "Temp": {"lower": 20, "maintenance": 60, "upper": 80, "critical": 100}
    },
    "air_compressor": {
        "Pressure": {"lower": 50, "maintenance": 150, "upper": 200, "critical": 250},
        "RPM": {"lower": 500, "maintenance": 1500, "upper": 2000, "critical": 2500},
        "Temp": {"lower": 20, "maintenance": 60, "upper": 80, "critical": 100},
        "Humidity": {"lower": 30, "maintenance": 60, "upper": 80, "critical": 90}
    }
}

# Generate random values for sensors
def generate_value(sensor, machine):
    return random.randint(limits[machine][sensor]["upper"] - 20, limits[machine][sensor]["critical"] - 1)

# Monitor data for a specific machine
def monitor_data(machine, db_name, table_name, columns):
    conn = sqlite3.connect(db_name, check_same_thread=False)
    cursor = conn.cursor()

    # Create the table if it doesn't exist
    column_definitions = ", ".join([f"{col} INTEGER NOT NULL" if col != "Timestamp" and col != "Status" else f"{col} TEXT NOT NULL" for col in columns])
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        {column_definitions}
    );
    """)
    conn.commit()

    dataset = pd.DataFrame(columns=columns)

    while not stop_flags[machine]["status"]:
        data = {col: generate_value(col, machine) for col in columns if col != "Timestamp" and col != "Status"}
        data["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["Status"] = "Normal"

        # Check for critical or maintenance thresholds
        for col in data:
            if col in limits[machine]:
                if data[col] >= limits[machine][col]["critical"]:
                    data["Status"] = "Critical Failure"
                    stop_flags[machine]["status"] = True
                elif data[col] >= limits[machine][col]["maintenance"]:
                    data["Status"] = "Maintenance Required"

        # Insert data into the database
        cursor.execute(f"""
            INSERT INTO {table_name} ({', '.join(columns)})
            VALUES ({', '.join(['?' for _ in columns])})
        """, [data[col] for col in columns])
        conn.commit()

        # Print the data to the console
        print(f"[{machine.upper()}] {data}")

        if stop_flags[machine]["status"]:
            break
        time.sleep(2)

# Start monitoring for a specific machine
@app.route('/start/<machine>', methods=['GET'])
def start_monitoring(machine):
    if stop_flags[machine]["status"]:
        return jsonify({"message": f"{machine.capitalize()} monitoring already stopped due to critical value. Use /reset/{machine} to restart."}), 400

    db_name = f"{machine}.db"
    table_name = machine.replace("_", " ").title().replace(" ", "")
    columns = list(limits[machine].keys()) + ["Timestamp", "Status"]

    thread = Thread(target=monitor_data, args=(machine, db_name, table_name, columns))
    thread.start()
    return jsonify({"message": f"{machine.capitalize()} monitoring started."})

# Get data for a specific machine
@app.route('/data/<machine>', methods=['GET'])
def get_data(machine):
    db_name = f"{machine}.db"
    table_name = machine.capitalize().replace("_", "")
    conn = sqlite3.connect(db_name, check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]
    return jsonify(data)

# Fetch the latest data for a specific machine
@app.route('/latest/<machine>', methods=['GET'])
def get_latest_data(machine):
    db_name = f"{machine}.db"
    table_name = machine.replace("_", " ").title().replace(" ", "")
    conn = sqlite3.connect(db_name, check_same_thread=False)
    cursor = conn.cursor()

    # Fetch the latest row from the database
    cursor.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    if not row:
        return jsonify({"error": "No data available"}), 404

    columns = [desc[0] for desc in cursor.description]
    data = dict(zip(columns, row))
    return jsonify(data)

# Reset monitoring for a specific machine
@app.route('/reset/<machine>', methods=['POST'])
def reset_monitoring(machine):
    db_name = f"{machine}.db"
    table_name = machine.capitalize().replace("_", "")
    conn = sqlite3.connect(db_name, check_same_thread=False)
    cursor = conn.cursor()

    stop_flags[machine]["status"] = False
    cursor.execute(f"DELETE FROM {table_name}")
    conn.commit()

    return jsonify({"message": f"{machine.capitalize()} monitoring reset. Data cleared."})

# Render the GUI
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)