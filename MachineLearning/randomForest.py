import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import time

# --- Machine Vision Placeholder ---
def get_current_layer_width():
    """
    Replace this with your actual machine vision interface.
    This mock randomly simulates a sensor value between 27 and 34 mm.
    """
    return np.random.uniform(27, 34)

def send_print_speed_to_printer(speed):
    """
    Replace this with actual code to send speed to your printer.
    """
    print(f"🖨️ Sending print speed: {speed:.1f} mm/s to printer...")

# --- Load Data and Train Model ---
csv_path = Path(r"generated_3d_print_data.csv")
df = pd.read_csv(csv_path)

print("Columns in dataset:", df.columns.tolist())

features = ['print_speed', 'nozzle_height', 'temperature', 'humidity']
target = 'layer_width'

X = df[features]
y = df[target]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
rf_model.fit(X_train, y_train)

# --- Adaptive Control Loop ---
def adaptive_print_speed_control(initial_speed, nozzle_height, temperature, humidity,
                                  target_min=29.0, target_max=32.0, tolerance=0.2, adjust_step=1.0):
    """
    Dynamically adjusts print speed based on current layer width from vision system.
    """
    print_speed = initial_speed
    send_print_speed_to_printer(print_speed)

    while True:
        layer_width = get_current_layer_width()
        print(f"📷 Current layer width: {layer_width:.2f} mm")

        if layer_width < target_min - tolerance:
            print("📉 Layer too thin. Increasing speed.")
            print_speed += adjust_step
        elif layer_width > target_max + tolerance:
            print("📈 Layer too thick. Decreasing speed.")
            print_speed -= adjust_step
        else:
            print("✅ Layer within target range. No speed change.")

        # Clamp speed within safe range
        print_speed = max(10.0, min(150.0, print_speed))

        # Use model to verify width stays valid
        X_sample = pd.DataFrame([{
            'print_speed': print_speed,
            'nozzle_height': nozzle_height,
            'temperature': temperature,
            'humidity': humidity
        }])
        predicted_width = rf_model.predict(X_sample)[0]

        print(f"🤖 Predicted width: {predicted_width:.2f} mm with speed {print_speed:.1f} mm/s")
        send_print_speed_to_printer(print_speed)

        time.sleep(1)  # adjust sampling rate as needed

# --- Example Run (replace with real values) ---
adaptive_print_speed_control(
    initial_speed=80.0,
    nozzle_height=15.0,
    temperature=210.0,
    humidity=40.0
)
