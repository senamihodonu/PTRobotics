import pandas as pd
import numpy as np
import time
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import random
import csv
from datetime import datetime
import matplotlib.pyplot as plt

# -----------------------------
# 0. Model Selection Option
# -----------------------------
USE_MODEL = "both"  # Options: "rf", "gb", "both"

# -----------------------------
# 1. Load and Prepare Dataset
# -----------------------------
df = pd.read_csv('all_prints_export.csv')

# Forward model: Predict layer width
X_fwd = df[['print_speed', 'nozzle_height', 'temperature', 'humidity']]
y_fwd = df['layer_width']

# Inverse model: Predict print speed
df['target_layer_width'] = df['layer_width']
X_inv = df[['nozzle_height', 'temperature', 'humidity', 'target_layer_width']]
y_inv = df['print_speed']

# -----------------------------
# 2. Train Models
# -----------------------------
X_train_fwd, X_test_fwd, y_train_fwd, y_test_fwd = train_test_split(X_fwd, y_fwd, test_size=0.2, random_state=42)
X_train_inv, X_test_inv, y_train_inv, y_test_inv = train_test_split(X_inv, y_inv, test_size=0.2, random_state=42)

model_fwd_rf = RandomForestRegressor(n_estimators=100, random_state=42)
model_fwd_rf.fit(X_train_fwd, y_train_fwd)

model_inv_rf = RandomForestRegressor(n_estimators=100, random_state=42)
model_inv_rf.fit(X_train_inv, y_train_inv)

model_fwd_gb = GradientBoostingRegressor(n_estimators=100, random_state=42)
model_fwd_gb.fit(X_train_fwd, y_train_fwd)

model_inv_gb = GradientBoostingRegressor(n_estimators=100, random_state=42)
model_inv_gb.fit(X_train_inv, y_train_inv)

# -----------------------------
# 3. Evaluate Models (optional)
# -----------------------------
def print_metrics(name, y_true, y_pred):
    print(f"\n🔹 {name}")
    print("MAE:", mean_absolute_error(y_true, y_pred))
    print("RMSE:", np.sqrt(mean_squared_error(y_true, y_pred)))
    print("R²:", r2_score(y_true, y_pred))

# -----------------------------
# 4. Real-Time Monitoring
# -----------------------------
def get_live_sensor_data():
    """Simulated sensor readings (replace with actual sensors)."""
    return {
        'print_speed': random.uniform(1, 5),
        'nozzle_height': random.uniform(13, 20),
        'temperature': random.uniform(18, 26),
        'humidity': random.uniform(12, 30),
        'measured_width': random.uniform(30.0, 33.0)  # Simulated actual measurement
    }

def send_to_printer(corrected_speed):
    print(f"Sending {corrected_speed:.2f} to the robot")

# Set control target and tolerance
TARGET_WIDTH = 31.5  # mm
TOLERANCE = 0.5      # mm (+/-)

# Set up logging
log_filename = 'realtime_log.csv'
with open(log_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['timestamp', 'print_speed', 'nozzle_height', 'temperature', 'humidity',
                     'measured_width', 'predicted_width', 'width_diff', 'corrected_speed'])

print("\n🔄 Starting real-time loop (Press Ctrl+C to stop)")

timestamps, diffs = [], []

try:
    while True:
        sensors = get_live_sensor_data()
        print(f"\n📡 Sensor Data — Speed: {sensors['print_speed']:.2f}, Height: {sensors['nozzle_height']:.2f}, Temp: {sensors['temperature']:.2f}, Humidity: {sensors['humidity']:.2f}, MV Width: {sensors['measured_width']:.2f}")

        fwd_input = pd.DataFrame([{
            'print_speed': sensors['print_speed'],
            'nozzle_height': sensors['nozzle_height'],
            'temperature': sensors['temperature'],
            'humidity': sensors['humidity']
        }])

        if USE_MODEL in ["rf", "both"]:
            predicted_rf = model_fwd_rf.predict(fwd_input)[0]
            print(f"🌲 RF Predicted width: {predicted_rf:.2f} mm")

        if USE_MODEL in ["gb", "both"]:
            predicted_gb = model_fwd_gb.predict(fwd_input)[0]
            print(f"🔥 GB Predicted width: {predicted_gb:.2f} mm")

        if USE_MODEL == "rf":
            predicted_width = predicted_rf
        elif USE_MODEL == "gb":
            predicted_width = predicted_gb
        else:
            predicted_width = (predicted_rf + predicted_gb) / 2

        width_difference = abs(predicted_width - sensors['measured_width'])
        print(f"📏 Difference between predicted and actual width: {width_difference:.2f} mm")

        corrected_speed = None
        if abs(sensors['measured_width'] - TARGET_WIDTH) > TOLERANCE:
            inv_input = pd.DataFrame([{
                'nozzle_height': sensors['nozzle_height'],
                'temperature': sensors['temperature'],
                'humidity': sensors['humidity'],
                'target_layer_width': TARGET_WIDTH
            }])

            if USE_MODEL == "rf":
                corrected_speed = model_inv_rf.predict(inv_input)[0]
            elif USE_MODEL == "gb":
                corrected_speed = model_inv_gb.predict(inv_input)[0]
            else:
                corrected_speed = (model_inv_rf.predict(inv_input)[0] + model_inv_gb.predict(inv_input)[0]) / 2

            print(f"⚠️  Measured width out of spec")
            print(f"→ Adjusting speed from {sensors['print_speed']:.2f} to {corrected_speed:.2f} mm/s")
            send_to_printer(corrected_speed)
            sensors['print_speed'] = corrected_speed
        else:
            print(f"✅ Width OK — Measured: {sensors['measured_width']:.2f} mm, Predicted: {predicted_width:.2f} mm")

        # Log data
        with open(log_filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([datetime.now().isoformat(),
                             sensors['print_speed'], sensors['nozzle_height'], sensors['temperature'],
                             sensors['humidity'], sensors['measured_width'],
                             predicted_width, width_difference, corrected_speed])

        timestamps.append(datetime.now())
        diffs.append(width_difference)

        time.sleep(2)

except KeyboardInterrupt:
    print("\n🛑 Real-time monitoring stopped.")

    # Visualization
    plt.figure(figsize=(10, 4))
    plt.plot(timestamps, diffs, label='Predicted vs Measured Width Error')
    plt.xlabel('Time')
    plt.ylabel('Width Difference (mm)')
    plt.title('Model Drift and Prediction Error Over Time')
    plt.legend()
    plt.tight_layout()
    plt.savefig("model_drift_plot.png")
    plt.show()
