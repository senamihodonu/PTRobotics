import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import time

# --- Machine Vision Placeholder ---
def get_current_layer_width():
    return np.random.uniform(27, 40)

def send_print_speed_to_printer(speed):
    print(f"[🖨️ CONTROL] Sending print speed to printer: {speed:.2f} mm/s")

# --- Load Data and Train Model ---
csv_path = Path("all_prints_export.csv")
df = pd.read_csv(csv_path)

print(f"[📁 DATA] Columns in dataset: {df.columns.tolist()}")

features = ['print_speed', 'nozzle_height', 'temperature', 'humidity']
target = 'layer_width'

X = df[features]
y = df[target]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

rf_model = RandomForestRegressor(n_estimators=100, criterion= 'squared_error', random_state=42)
rf_model.fit(X_train, y_train)
print("[✅ MODEL] Random Forest model trained successfully.")

# --- Model Evaluation ---
y_pred = rf_model.predict(X_test)

mae = mean_absolute_error(y_test, y_pred)
mse = mean_squared_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)


print("\n[📊 METRICS] Model Evaluation:")
print(f"  - MAE (Mean Absolute Error): {mae:.3f} mm")
print(f"  - MSE (Mean Square Error): {mse:.3f} mm")
print(f"  - RMSE (Root Mean Squared Error): {rmse:.3f} mm")
print(f"  - R² Score: {r2:.3f}")

# --- Feature Importance Plot ---
# importances = rf_model.feature_importances_
# print("\n[🔍 IMPORTANCE] Feature importances:")
# for feature, importance in zip(features, importances):
#     print(f"  - {feature}: {importance:.3f}")

# plt.barh(features, importances)
# plt.xlabel("Feature Importance")
# plt.title("Random Forest Feature Importance")
# plt.tight_layout()
# plt.show()

# --- Visualize Predictions vs Actual Values ---
# plt.figure(figsize=(8, 6))
# plt.scatter(y_test, y_pred, alpha=0.6, edgecolor='k', label='Predicted vs Actual')
# plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', label='Ideal (y = x)')
# plt.xlabel("Actual Layer Width (mm)")
# plt.ylabel("Predicted Layer Width (mm)")
# plt.title("Random Forest: Predicted vs Actual Layer Width")
# plt.legend()
# plt.grid(True)
# plt.tight_layout()
# plt.show()

# # --- Adaptive Control Loop ---
# def refined_adaptive_print_speed_control(
#     initial_speed,
#     nozzle_height,
#     temperature,
#     humidity,
#     target_min=29,
#     target_max=32.0,
#     speed_range=(0.5, 5.0),
#     speed_resolution=0.05,
#     max_iterations=1
# ):
#     print_speed = initial_speed
#     print(f"\n[⚙️ INIT] Starting adaptive control with initial speed {print_speed:.2f} mm/s")
#     send_print_speed_to_printer(print_speed)

#     for iteration in range(1, max_iterations + 1):
#         print(f"\n[🔁 ITERATION {iteration}]")

#         # Simulated actual layer width from vision system
#         actual_layer_width = get_current_layer_width()
#         print(f"[📷 SENSOR] Measured layer width: {actual_layer_width:.2f} mm")

#         # Generate candidate speeds and predictions
#         candidate_speeds = np.arange(speed_range[0], speed_range[1] + speed_resolution, speed_resolution)
#         predictions = []

#         for speed in candidate_speeds:
#             X_candidate = pd.DataFrame([{
#                 'print_speed': speed,
#                 'nozzle_height': nozzle_height,
#                 'temperature': temperature,
#                 'humidity': humidity
#             }])
#             predicted_width = rf_model.predict(X_candidate)[0]
#             predictions.append((speed, predicted_width))

#         # Try to select a speed whose predicted width falls inside the target range
#         in_range = [
#             (s, w) for s, w in predictions
#             if target_min <= w <= target_max
#         ]

#         if in_range:
#             # Pick the one closest to the center of the range
#             target_center = (target_min + target_max) / 2.0
#             best_speed, best_predicted_width = min(in_range, key=lambda x: abs(x[1] - target_center))
#             print(f"[🎯 IN-RANGE] Speed {best_speed:.2f} mm/s gives predicted width {best_predicted_width:.2f} mm")
#         else:
#             # No prediction within target range; pick closest overall
#             best_speed, best_predicted_width = min(predictions, key=lambda x: abs((target_min + target_max) / 2.0 - x[1]))
#             print(f"[⚠️ OUT-OF-RANGE] Closest prediction: Speed {best_speed:.2f} mm/s → {best_predicted_width:.2f} mm")

#         # Update print speed
#         print_speed = best_speed
#         send_print_speed_to_printer(print_speed)
#         time.sleep(1)

# # Example usage
# for x in range(6):
#     y = 6
#     refined_adaptive_print_speed_control(
#         initial_speed=6.0,
#         nozzle_height=15.0,
#         temperature=18.0,
#         humidity=40.0,
#         target_min=28,
#         target_max=32.0
#     )

#     y -= 1

