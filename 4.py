from flask import Flask, jsonify
import sqlite3
import pandas as pd
import random
import time
from threading import Thread
from datetime import datetime

app = Flask(__name__)  # Corrected here

# SQLite setup and table creation
conn = sqlite3.connect("cnc_data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS CNC_Machine (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    Timestamp TEXT NOT NULL,
    Temp INTEGER NOT NULL,
    Vibration INTEGER NOT NULL,
    RPM INTEGER NOT NULL,
    Status TEXT NOT NULL
);
""")
conn.commit()

# Limits
limits = {
    "Temp": {"lower": 40, "maintenance": 80, "upper": 100, "critical": 110},
    "Vibration": {"lower": 20, "maintenance": 50, "upper": 70, "critical": 85},
    "RPM": {"lower": 500, "maintenance": 1500, "upper": 2000, "critical": 2200}
}

dataset = pd.DataFrame(columns=["Timestamp", "Temp", "Vibration", "RPM", "Status"])
stop_flag = {"status": False}

def generate_value(sensor):
    return random.randint(limits[sensor]["upper"] - 20, limits[sensor]["critical"] - 1)

def insert_to_db(timestamp, temp, vib, rpm, status):
    cursor.execute("""
        INSERT INTO CNC_Machine (Timestamp, Temp, Vibration, RPM, Status)
        VALUES (?, ?, ?, ?, ?)
    """, (timestamp, temp, vib, rpm, status))
    conn.commit()

def monitor_data():
    while not stop_flag["status"]:
        temp = generate_value("Temp")
        vib = generate_value("Vibration")
        rpm = generate_value("RPM")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "Normal"

        if temp >= limits["Temp"]["critical"] or vib >= limits["Vibration"]["critical"] or rpm >= limits["RPM"]["critical"]:
            status = "Replacement Required"
            stop_flag["status"] = True
        elif (
            temp >= limits["Temp"]["maintenance"] or
            vib >= limits["Vibration"]["maintenance"] or
            rpm >= limits["RPM"]["maintenance"]
        ):
            status = "Maintenance Required"

        dataset.loc[len(dataset)] = [timestamp, temp, vib, rpm, status]
        insert_to_db(timestamp, temp, vib, rpm, status)

        print(f"[{timestamp}] Temp: {temp}, Vibration: {vib}, RPM: {rpm} --> {status}")

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
    cursor.execute("SELECT * FROM CNC_Machine")
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]
    return jsonify(data)

@app.route('/reset', methods=['POST'])
def reset_monitoring():
    global dataset
    dataset = pd.DataFrame(columns=["Timestamp", "Temp", "Vibration", "RPM", "Status"])
    stop_flag["status"] = False

    cursor.execute("DELETE FROM CNC_Machine")
    conn.commit()

    return jsonify({"message": "Monitoring reset. Data cleared."})

if __name__ == '__main__':
    app.run(debug=True)