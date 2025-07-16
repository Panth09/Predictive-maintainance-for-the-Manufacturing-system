from flask import Flask, jsonify
import sqlite3
import pandas as pd
import random
import time
from threading import Thread
from datetime import datetime

app = Flask(__name__)

# SQLite setup and table creation
conn = sqlite3.connect("hydraulic_press.db", check_same_thread=False)
cursor = conn.cursor()

# Migration logic to add Failure_Type column if it doesn't exist
cursor.execute("PRAGMA table_info(Hydraulic_Press)")
columns = [column[1] for column in cursor.fetchall()]
if "Failure_Type" not in columns:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Hydraulic_Press_New (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Timestamp TEXT NOT NULL,
        Pressure INTEGER NOT NULL,
        Temp INTEGER NOT NULL,
        Vibration INTEGER NOT NULL,
        Status TEXT NOT NULL,
        Failure_Type TEXT
    );
    """)
    cursor.execute("""
    INSERT INTO Hydraulic_Press_New (id, Timestamp, Pressure, Temp, Vibration, Status)
    SELECT id, Timestamp, Pressure, Temp, Vibration, Status FROM Hydraulic_Press
    """)
    cursor.execute("DROP TABLE Hydraulic_Press")
    cursor.execute("ALTER TABLE Hydraulic_Press_New RENAME TO Hydraulic_Press")
    conn.commit()

# Limits for Hydraulic Press
limits = {
    "Pressure": {"lower": 50, "maintenance": 120, "upper": 180, "critical": 200},
    "Temp": {"lower": 20, "maintenance": 60, "upper": 80, "critical": 100},
    "Vibration": {"lower": 5, "maintenance": 20, "upper": 40, "critical": 50}
}

dataset = pd.DataFrame(columns=["Timestamp", "Pressure", "Temp", "Vibration", "Status", "Failure_Type"])
stop_flag = {"status": False}

def generate_value(sensor):
    return random.randint(limits[sensor]["upper"] - 20, limits[sensor]["critical"] - 1)

def insert_to_db(timestamp, pressure, temp, vib, status, failure_type):
    cursor.execute("""
        INSERT INTO Hydraulic_Press (Timestamp, Pressure, Temp, Vibration, Status, Failure_Type)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (timestamp, pressure, temp, vib, status, failure_type))
    conn.commit()

def monitor_data():
    while not stop_flag["status"]:
        pressure = generate_value("Pressure")
        temp = generate_value("Temp")
        vib = generate_value("Vibration")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "Normal"
        failure_type = None

        if pressure >= limits["Pressure"]["critical"] or temp >= limits["Temp"]["critical"] or vib >= limits["Vibration"]["critical"]:
            status = "Seal Leakage or Pump Failure"
            failure_type = "Critical Threshold Exceeded"
            stop_flag["status"] = True
        elif (
            pressure >= limits["Pressure"]["maintenance"] or
            temp >= limits["Temp"]["maintenance"] or
            vib >= limits["Vibration"]["maintenance"]
        ):
            status = "Maintenance Required"
            failure_type = "Approaching Critical Threshold"

        dataset.loc[len(dataset)] = [timestamp, pressure, temp, vib, status, failure_type]
        insert_to_db(timestamp, pressure, temp, vib, status, failure_type)

        # Optimized output format
        print(f"""
        === Monitoring Report ===
        Timestamp: {timestamp}
        Pressure: {pressure} (Limit: Critical >= {limits['Pressure']['critical']})
        Temperature: {temp} (Limit: Critical >= {limits['Temp']['critical']})
        Vibration: {vib} (Limit: Critical >= {limits['Vibration']['critical']})
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
    cursor.execute("SELECT * FROM Hydraulic_Press")
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]
    return jsonify(data)

@app.route('/reset', methods=['POST'])
def reset_monitoring():
    global dataset
    dataset = pd.DataFrame(columns=["Timestamp", "Pressure", "Temp", "Vibration", "Status", "Failure_Type"])
    stop_flag["status"] = False

    cursor.execute("DELETE FROM Hydraulic_Press")
    conn.commit()

    return jsonify({"message": "Monitoring reset. Data cleared."})

if __name__ == '__main__':
    app.run(debug=True)