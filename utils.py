# === Imports ===
import sys
import os
import time
import threading
import cv2
import numpy as np
import csv
import pandas as pd

# === Path Setup ===
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.normpath(
    os.path.join(current_dir, "fanuc_ethernet_ip_drivers", "src")
)
sys.path.append(src_path)

# === Custom Libraries ===
from ArucoMarkers.detect_aruco import detect_from_image
from robot_controller import robot
from PyPLCConnection import (
    PyPLCConnection,
    LEAD_Y_SCREW, LEAD_Z_SCREW,
    DIP_SWITCH_SETTING_Y, DIP_SWITCH_SETTING_Z,
    GREEN,
    Y_LEFT_MOTION, Y_RIGHT_MOTION,
    Z_DOWN_MOTION, Z_UP_MOTION,
    DISTANCE_SENSOR_IN,
    PLC_IP, ROBOT_IP,
)

# Override IP if needed
PLC_IP = "192.168.1.25"
ROBOT_IP = "192.168.1.101"  # Woody

print("=== Program initialized ===")

# === Initialize PLC and Robot ===
plc = PyPLCConnection(PLC_IP)
woody = robot(ROBOT_IP)

print("PLC and Robot connections established.")
plc.reset_coils()

# === Parameters ===
speed = 200            # Robot travel speed (mm/s)
print_speed = 10       # Printing speed (mm/s)
inside_offset = 6      # Offset for inner infill moves (mm)
layer_height = 4       # Vertical step per layer (mm)
z_offset = 20          # Safe Z offset for travel moves (mm)
x_offset = 13.5        # X-axis offset (mm)
print_offset = 5       # Vertical offset between passes (mm)
z_correction = 4       # Fine Z correction for alignment (mm)

current_distance = plc.read_current_distance()
flg = True

# === Safety Check ===
def safety_check():
    """
    Ensure no safety coils are active before starting.
    Moves Z down and Y right if any safety coil is active.
    """
    while any(plc.read_modbus_coils(c) for c in (8, 9, 14)):
        print("Safety check: coils active, moving Z down and Y right...")
        for coil in (Z_DOWN_MOTION, Y_RIGHT_MOTION):
            plc.write_modbus_coils(coil, True)

    # Turn off safety coils
    for coil in (Z_DOWN_MOTION, Y_RIGHT_MOTION):
        plc.write_modbus_coils(coil, False)

    print("Safety check complete.")
    time.sleep(1)

# === Camera Utilities ===
def open_all_cameras(max_cameras=5):
    """
    Detects and opens all available cameras up to max_cameras.
    """
    cameras = {}
    for index in range(max_cameras):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)  # DirectShow for stability
        if cap is not None and cap.isOpened():
            print(f"[Camera] Opened camera {index}")
            cameras[index] = cap
        else:
            print(f"[Camera] No camera detected at index {index}")
            cap.release()
    if not cameras:
        print("[Camera] No cameras found!")
    return cameras

# === Functions ===
def check_height(layer_height: float):
    z = woody.read_current_cartesian_pose()[2]
    print(
        f"[Check] Current distance: {current_distance:.2f} mm | "
        f"Target: {layer_height:.2f} mm | Z: {z:.2f} mm"
    )
    return current_distance, z

def read_current_z_distance():
    return plc.read_current_distance()

def calibrate_height(pose, layer_height: float):
    """
    Calibrate nozzle height using PLC distance sensor feedback.
    """
    while flg:
        current_distance = plc.read_current_distance()

        if current_distance / 2 > layer_height:
            pose[2] -= current_distance / 2
            woody.write_cartesian_position(pose)

        elif current_distance > layer_height:
            print(f"[Calibration] Distance too high: {current_distance:.2f} mm")
            pose[2] -= 1
            woody.write_cartesian_position(pose)

        elif current_distance < layer_height:
            print(f"[Calibration] Distance too low: {current_distance:.2f} mm")
            pose[2] += 1
            woody.write_cartesian_position(pose)

        else:
            z = woody.read_current_cartesian_pose()[2]
            print(
                f"[Calibration] Nozzle height set: {current_distance:.2f} mm | "
                f"Starting Z: {z:.2f} mm"
            )
            break

    return pose, z

def apply_z_correction_gantry(layer_height, tolerance=0.1):
    current_dist = plc.read_current_distance()
    z_pose = woody.read_current_cartesian_pose()[2]
    diff = current_dist - layer_height

    if abs(diff) > tolerance:
        direction = Z_DOWN_MOTION if diff > 0 else Z_UP_MOTION
        plc.travel(direction, abs(diff), 'mm', 'z')
        print(f"[Calibration] Adjusted Z by {diff:.2f} mm | New Z: {z_pose:.2f} mm")
    else:
        print(
            f"[Calibration] No correction needed | "
            f"Nozzle height: {current_dist:.2f} mm | "
            f"Target: {layer_height:.2f} mm"
        )

def monitor_distance_sensor(layer_height: float, tolerance: float = 1):
    while flg:
        current_distance = plc.read_current_distance()
        max_threshold = layer_height + tolerance
        min_threshold = layer_height - tolerance

        if current_distance > max_threshold:
            diff = current_distance - layer_height
            plc.travel(Z_DOWN_MOTION, diff, "mm", "z")
            print(f"[Monitor] Adjusting down by {diff:.2f} mm (distance {current_distance:.2f})")

        elif current_distance < min_threshold:
            diff = layer_height - current_distance
            plc.travel(Z_UP_MOTION, diff, "mm", "z")
            print(f"[Monitor] Adjusting up by {diff:.2f} mm (distance {current_distance:.2f})")

        else:
            z = woody.read_current_cartesian_pose()[2]
            print(
                f"[Monitor] Nozzle height stable: {current_distance:.2f} mm "
                f"(layer_height: {layer_height:.2f} mm)"
            )

        time.sleep(1)

def z_difference(layer_height, current_z, tol):
    current_distance = plc.read_current_distance()
    max_threshold = layer_height + tol
    min_threshold = layer_height - tol

    if current_distance > max_threshold:
        diff = current_distance - layer_height
        current_z -= diff
    elif current_distance < min_threshold:
        diff = layer_height - current_distance
        current_z += diff
    else:
        print(f"Z is within bounds. z_value = {current_z}, current_distance = {current_distance}")

    return current_z
# === ArUco Detection ===
aruco_path = os.path.normpath(os.path.join(current_dir, "ArucoMarkers"))
sys.path.append(aruco_path)
from detect_aruco import *

# === Calibration Function ===
def calibrate(calibration_distance, base_pose, move_axis='y', camera_index=0, save_dir="samples"):
    """
    Perform camera-to-motion calibration using ArUco marker distances.
    - Moves the robot to two positions (A and B)
    - Captures images from the camera
    - Measures marker displacement
    - Logs results to CSV
    """
    print("\n🔹 Starting calibration procedure...")
    print(f"  Move axis: {move_axis.upper()} | Distance: {calibration_distance} mm")

    os.makedirs(save_dir, exist_ok=True)
    base_pose = [200, 0, 0, 0, 90, 0]

    # --- Open camera ---
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError("❌ Could not open camera.")

    # === POSITION A ===
    print("➡️ Moving to position A...")
    woody.write_cartesian_position(base_pose)
    time.sleep(2)

    ret, image_A = cap.read()
    if not ret:
        raise RuntimeError("❌ Failed to capture image at position A.")

    img_A_path = os.path.join(save_dir, "sample_A.jpg")
    cv2.imwrite(img_A_path, image_A)
    print(f"📸 Image A saved to {img_A_path}")

    distances_A, marked_A = detect_from_image(img_A_path, return_marked=True, measure=True)

    # === POSITION B ===
    print("➡️ Moving to position B...")
    plc.travel(Y_LEFT_MOTION, calibration_distance, "mm", move_axis)
    time.sleep(2)

    ret, image_B = cap.read()
    if not ret:
        raise RuntimeError("❌ Failed to capture image at position B.")

    img_B_path = os.path.join(save_dir, "sample_B.jpg")
    cv2.imwrite(img_B_path, image_B)
    print(f"📸 Image B saved to {img_B_path}")

    distances_B, marked_B = detect_from_image(img_B_path, return_marked=True, measure=True)


    # === DIFFERENCE CALCULATION ===
    x_offset = distances_A - distances_B

    print(f"📏 Measured offset = {x_offset:.3f} mm")
    # === LOG RESULTS TO CSV ===
    csv_file = "MarkerData.csv"
    file_exists = os.path.isfile(csv_file)

    data = {
        'Distance A': [distances_A],
        'Distance B': [distances_B],
        'Offset': [x_offset]
    }

    pd.DataFrame(data).to_csv(csv_file, mode='a', header=not file_exists, index=False)

    # === CLEANUP ===
    cap.release()
    cv2.destroyAllWindows()

    print("✅ Calibration complete.\n")

    # print({
    #     "image_A": img_A_path,
    #     "image_B": img_B_path,
    #     "distances_A": distances_A,
    #     "distances_B": distances_B,
    #     "measured offset": x_offset,
    # })
    return x_offset



# === Main Run ===
if __name__ == "__main__":
    for x in range(1):
        safety_check()
        calibration_distance = 50
        woody.set_speed(200)
        base_pose = [200, 0, 0, 0, 90, 0]
        offset = calibrate(calibration_distance, base_pose, move_axis='y', camera_index=0, save_dir="samples")
        print(offset)
