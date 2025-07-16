from flask import Flask, jsonify
import sqlite3
import pandas as pd
import random
import time
from threading import Thread
from datetime import datetime

app = Flask(__name__)

# SQLite setup and table creation
conn = sqlite3.connect("air_compressor.db", check_same_thread=False)
cursor = conn.cursor()

# Create the Air_Compressor table if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS Air_Compressor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    Timestamp TEXT NOT NULL,
    Pressure INTEGER NOT NULL,
    RPM INTEGER NOT NULL,
    Temp INTEGER NOT NULL,
    Humidity INTEGER NOT NULL,
    Status TEXT NOT NULL,
    Failure_Type TEXT
);
""")
conn.commit()

# Migration logic to add Failure_Type column if it doesn't exist
cursor.execute("PRAGMA table_info(Air_Compressor)")
columns = [column[1] for column in cursor.fetchall()]
if "Failure_Type" not in columns:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Air_Compressor_New (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Timestamp TEXT NOT NULL,
        Pressure INTEGER NOT NULL,
        RPM INTEGER NOT NULL,
        Temp INTEGER NOT NULL,
        Humidity INTEGER NOT NULL,
        Status TEXT NOT NULL,
        Failure_Type TEXT
    );
    """)
    cursor.execute("""
    INSERT INTO Air_Compressor_New (id, Timestamp, Pressure, RPM, Temp, Humidity, Status)
    SELECT id, Timestamp, Pressure, RPM, Temp, Humidity, Status FROM Air_Compressor
    """)
    cursor.execute("DROP TABLE Air_Compressor")
    cursor.execute("ALTER TABLE Air_Compressor_New RENAME TO Air_Compressor")
    conn.commit()

# Limits for Air Compressor
limits = {
    "Pressure": {"lower": 50, "maintenance": 150, "upper": 200, "critical": 250},
    "RPM": {"lower": 500, "maintenance": 1500, "upper": 2000, "critical": 2500},
    "Temp": {"lower": 20, "maintenance": 60, "upper": 80, "critical": 100},
    "Humidity": {"lower": 30, "maintenance": 60, "upper": 80, "critical": 90}
}

dataset = pd.DataFrame(columns=["Timestamp", "Pressure", "RPM", "Temp", "Humidity", "Status", "Failure_Type"])
stop_flag = {"status": False}

def generate_value(sensor):
    return random.randint(limits[sensor]["upper"] - 20, limits[sensor]["critical"] - 1)

def insert_to_db(timestamp, pressure, rpm, temp, humidity, status, failure_type):
    cursor.execute("""
        INSERT INTO Air_Compressor (Timestamp, Pressure, RPM, Temp, Humidity, Status, Failure_Type)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, pressure, rpm, temp, humidity, status, failure_type))
    conn.commit()

def monitor_data():
    while not stop_flag["status"]:
        pressure = generate_value("Pressure")
        rpm = generate_value("RPM")
        temp = generate_value("Temp")
        humidity = generate_value("Humidity")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "Normal"
        failure_type = None

        # Determine the status and failure type
        if (
            pressure >= limits["Pressure"]["critical"] or
            rpm >= limits["RPM"]["critical"] or
            temp >= limits["Temp"]["critical"] or
            humidity >= limits["Humidity"]["critical"]
        ):
            status = "Overpressure or Motor Burnout"
            failure_type = "Critical Threshold Exceeded"
            stop_flag["status"] = True
        elif (
            pressure >= limits["Pressure"]["maintenance"] or
            rpm >= limits["RPM"]["maintenance"] or
            temp >= limits["Temp"]["maintenance"] or
            humidity >= limits["Humidity"]["maintenance"]
        ):
            status = "Maintenance Required"
            failure_type = "Approaching Critical Threshold"

        # Add data to the dataset and database
        dataset.loc[len(dataset)] = [timestamp, pressure, rpm, temp, humidity, status, failure_type]
        insert_to_db(timestamp, pressure, rpm, temp, humidity, status, failure_type)

        # Optimized output format
        print(f"""
        === Monitoring Report ===
        Timestamp: {timestamp}
        Pressure: {pressure} (Limit: Critical >= {limits['Pressure']['critical']})
        RPM: {rpm} (Limit: Critical >= {limits['RPM']['critical']})
        Temperature: {temp} (Limit: Critical >= {limits['Temp']['critical']})
        Humidity: {humidity} (Limit: Critical >= {limits['Humidity']['critical']})
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
    cursor.execute("SELECT * FROM Air_Compressor")
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]
    return jsonify(data)

@app.route('/reset', methods=['POST'])
def reset_monitoring():
    global dataset
    dataset = pd.DataFrame(columns=["Timestamp", "Pressure", "RPM", "Temp", "Humidity", "Status", "Failure_Type"])
    stop_flag["status"] = False

    cursor.execute("DELETE FROM Air_Compressor")
    conn.commit()

    return jsonify({"message": "Monitoring reset. Data cleared."})

if __name__ == '__main__':
    app.run(debug=True)