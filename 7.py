from flask import Flask, jsonify
import sqlite3
import pandas as pd
import random
import time
from threading import Thread
from datetime import datetime

app = Flask(__name__)

# SQLite setup and table creation
conn = sqlite3.connect("conveyor_belt.db", check_same_thread=False)
cursor = conn.cursor()

# Create the Conveyor_Belt table if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS Conveyor_Belt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    Timestamp TEXT NOT NULL,
    Vibration INTEGER NOT NULL,
    RPM INTEGER NOT NULL,
    Temp INTEGER NOT NULL,
    Status TEXT NOT NULL,
    Failure_Type TEXT
);
""")
conn.commit()

# Migration logic to add Failure_Type column if it doesn't exist
cursor.execute("PRAGMA table_info(Conveyor_Belt)")
columns = [column[1] for column in cursor.fetchall()]
if "Failure_Type" not in columns:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Conveyor_Belt_New (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Timestamp TEXT NOT NULL,
        Vibration INTEGER NOT NULL,
        RPM INTEGER NOT NULL,
        Temp INTEGER NOT NULL,
        Status TEXT NOT NULL,
        Failure_Type TEXT
    );
    """)
    cursor.execute("""
    INSERT INTO Conveyor_Belt_New (id, Timestamp, Vibration, RPM, Temp, Status)
    SELECT id, Timestamp, Vibration, RPM, Temp, Status FROM Conveyor_Belt
    """)
    cursor.execute("DROP TABLE Conveyor_Belt")
    cursor.execute("ALTER TABLE Conveyor_Belt_New RENAME TO Conveyor_Belt")
    conn.commit()

# Limits for Conveyor Belt
limits = {
    "Vibration": {"lower": 5, "maintenance": 20, "upper": 40, "critical": 50},
    "RPM": {"lower": 500, "maintenance": 1500, "upper": 2000, "critical": 2500},
    "Temp": {"lower": 20, "maintenance": 60, "upper": 80, "critical": 100}
}

dataset = pd.DataFrame(columns=["Timestamp", "Vibration", "RPM", "Temp", "Status", "Failure_Type"])
stop_flag = {"status": False}

def generate_value(sensor):
    return random.randint(limits[sensor]["upper"] - 20, limits[sensor]["critical"] - 1)

def insert_to_db(timestamp, vibration, rpm, temp, status, failure_type):
    cursor.execute("""
        INSERT INTO Conveyor_Belt (Timestamp, Vibration, RPM, Temp, Status, Failure_Type)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (timestamp, vibration, rpm, temp, status, failure_type))
    conn.commit()

def monitor_data():
    while not stop_flag["status"]:
        vibration = generate_value("Vibration")
        rpm = generate_value("RPM")
        temp = generate_value("Temp")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "Normal"
        failure_type = None

        # Determine the status and failure type
        if (
            vibration >= limits["Vibration"]["critical"] or
            rpm >= limits["RPM"]["critical"] or
            temp >= limits["Temp"]["critical"]
        ):
            status = "Belt Misalignment or Motor Overload"
            failure_type = "Critical Threshold Exceeded"
            stop_flag["status"] = True
        elif (
            vibration >= limits["Vibration"]["maintenance"] or
            rpm >= limits["RPM"]["maintenance"] or
            temp >= limits["Temp"]["maintenance"]
        ):
            status = "Maintenance Required"
            failure_type = "Approaching Critical Threshold"

        # Add data to the dataset and database
        dataset.loc[len(dataset)] = [timestamp, vibration, rpm, temp, status, failure_type]
        insert_to_db(timestamp, vibration, rpm, temp, status, failure_type)

        # Optimized output format
        print(f"""
        === Monitoring Report ===
        Timestamp: {timestamp}
        Vibration: {vibration} (Limit: Critical >= {limits['Vibration']['critical']})
        RPM: {rpm} (Limit: Critical >= {limits['RPM']['critical']})
        Temperature: {temp} (Limit: Critical >= {limits['Temp']['critical']})
        Status: {status}
        Failure Type: {failure_type if failure_type else "None"}
        ==========================
        """)

        if stop_flag["status"]:
            break
        time.sleep(2)

@app.route('/start', methods=['GET'])
def start_monitoring():
    if stop_flag["status"]:
        return jsonify({"message": "Stopped due to critical value. Use /reset to restart."}), 400

    thread = Thread(target=monitor_data)
    thread.start()
    return jsonify({"message": "Monitoring started."})

@app.route('/data', methods=['GET'])
def get_data():
    cursor.execute("SELECT * FROM Conveyor_Belt")
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]
    return jsonify(data)

@app.route('/reset', methods=['POST'])
def reset_monitoring():
    global dataset
    dataset = pd.DataFrame(columns=["Timestamp", "Vibration", "RPM", "Temp", "Status", "Failure_Type"])
    stop_flag["status"] = False

    cursor.execute("DELETE FROM Conveyor_Belt")
    conn.commit()

    return jsonify({"message": "Monitoring reset. Data cleared."})

if __name__ == '__main__':
    app.run(debug=True)