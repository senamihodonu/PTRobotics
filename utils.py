# === Imports ===
import sys
import os
import time
import threading
import cv2
import numpy as np




# === Path Setup ===
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.normpath(
    os.path.join(current_dir, "fanuc_ethernet_ip_drivers", "src")
)
sys.path.append(src_path)

# === Custom Libraries ===
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


PLC_IP = "192.168.1.25"
ROBOT_IP = '192.168.1.101' #Woody

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

import cv2

def open_all_cameras(max_cameras=5):
    """
    Detects and opens all available cameras up to max_cameras.
    
    Args:
        max_cameras (int): Maximum number of camera indices to check.
        
    Returns:
        cameras (dict): Dictionary of {camera_index: cv2.VideoCapture object}.
    """
    cameras = {}
    for index in range(max_cameras):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)  # Use DirectShow on Windows for stability
        if cap is not None and cap.isOpened():
            print(f"[Camera] Opened camera {index}")
            cameras[index] = cap
        else:
            print(f"[Camera] No camera detected at index {index}")
            cap.release()  # Ensure proper release if not opened

    if not cameras:
        print("[Camera] No cameras found!")
    return cameras


# === Functions ===
def check_height(layer_height: float):
    """
    Check the nozzle height relative to the print bed.

    Args:
        layer_height (float): Target layer height (mm).

    Returns:
        tuple: (current_distance, z_position).
    """
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
    Adjusts the robot Z position until the target layer height is reached.

    Args:
        pose (list): Current Cartesian pose of the robot [x, y, z, ...].
        layer_height (float): Target layer height (mm).

    Returns:
        tuple: (adjusted_pose, z_position).
    """
    while flg:
        current_distance = plc.read_current_distance()

        if current_distance / 2 > layer_height:
            # Overshoot → move down proportionally
            pose[2] -= current_distance / 2
            woody.write_cartesian_position(pose)

        elif current_distance > layer_height:
            # Too high → move down incrementally
            print(f"[Calibration] Distance too high: {current_distance:.2f} mm")
            pose[2] -= 1
            woody.write_cartesian_position(pose)

        elif current_distance < layer_height:
            # Too low → move up incrementally
            print(f"[Calibration] Distance too low: {current_distance:.2f} mm")
            pose[2] += 1
            woody.write_cartesian_position(pose)

        else:
            # Correct height reached
            z = woody.read_current_cartesian_pose()[2]
            print(
                f"[Calibration] Nozzle height set: {current_distance:.2f} mm | "
                f"Starting Z: {z:.2f} mm"
            )
            break

    return pose, z

def apply_z_correction_gantry(layer_height, tolerance=0.1):
    """
    Apply Z correction using gantry PLC travel.
    
    Compares the current measured distance with the desired layer height
    and adjusts Z accordingly.
    """
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
    """
    Continuously monitor the distance sensor and adjust Z position if needed.

    Args:
        layer_height (float): Target layer height (mm).
        tolerance (float): Allowable deviation (± mm) before correction.
    """
    while flg:
        current_distance = plc.read_current_distance()
        max_threshold = layer_height + tolerance
        min_threshold = layer_height - tolerance

        if current_distance > max_threshold:
            # Too high → move down
            diff = current_distance - layer_height
            plc.travel(Z_DOWN_MOTION, diff, "mm", "z")
            print(f"[Monitor] Adjusting down by {diff:.2f} mm (distance {current_distance:.2f})")

        elif current_distance < min_threshold:
            # Too low → move up
            diff = layer_height - current_distance
            plc.travel(Z_UP_MOTION, diff, "mm", "z")
            print(f"[Monitor] Adjusting up by {diff:.2f} mm (distance {current_distance:.2f})")

        else:
            # Within tolerance band
            z = woody.read_current_cartesian_pose()[2]
            print(
                f"[Monitor] Nozzle height stable: {current_distance:.2f} mm "
                f"(layer_height: {layer_height:.2f} mm)"
            )

        time.sleep(1)

def z_difference(layer_height, current_z, tol):
    """
    Adjusts the Z value based on distance sensor reading.
    Returns the corrected z_value.
    """
    current_distance = plc.read_current_distance()
    max_threshold = layer_height + tol
    min_threshold = layer_height - tol

    # z = woody.read_current_cartesian_pose()[2]  # start with the current z

    if current_distance > max_threshold:
        diff = current_distance - layer_height
        current_z -= diff
    elif current_distance < min_threshold:
        diff = layer_height - current_distance
        current_z += diff
    else:
        print(f"Z is within bounds. z_value = {current_z}, current_distance = {current_distance}")

    return current_z


import cv2
import time
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.normpath(
    os.path.join(current_dir, "ArucoMarkers")
)
sys.path.append(src_path)

from detect_aruco import *

def calibrate(calibration_distance, base_pose, move_axis='y', camera_index=0, save_dir="samples"):
    """
    Perform camera-to-motion calibration using marker distances and OpenCV capture.

    Args:
        calibration_distance (float): Distance to move between positions A and B (in mm).
        base_pose (dict): The starting robot pose (e.g., {"x":0, "y":100, "z":50}).
        move_axis (str): Axis to move for calibration ('x', 'y', or 'z').
        camera_index (int): Index of the camera for cv2.VideoCapture (default 0).
        save_dir (str): Directory to save captured sample images.

    Returns:
        dict: Comparison results showing measured and expected distance differences.
    """

    print("🔹 Starting calibration procedure...")
    print(f"  Move axis: {move_axis.upper()} | Distance: {calibration_distance} mm")

    # Ensure save directory exists
    os.makedirs(save_dir, exist_ok=True)

    # --- Initialize camera
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError("❌ Could not open camera.")

    # --- Step 1: Move to position A and capture image
    print("➡️ Moving to position A...")
    woody.write_cartesian_position(base_pose)
    time.sleep(2)  # Wait for robot to stabilize

    ret, image_A = cap.read()
    if not ret:
        raise RuntimeError("❌ Failed to capture image at position A.")

    img_A_path = os.path.join(save_dir, "sample_A.jpg")
    cv2.imwrite(img_A_path, image_A)
    print(f"📸 Image A saved to {img_A_path}")

    # Detect marker and measure distances
    distances_A = detect_aruco.detect_from_image(image_A)
    print(f"🧭 Distances at A: {distances_A}")

    # # --- Step 2: Move to position B and capture image
    # pose_B = base_pose.copy()
    # pose_B[move_axis] += calibration_distance

    # print("➡️ Moving to position B...")
    # woody.write_cartesian_position(pose_B)
    # time.sleep(2)

    # ret, image_B = cap.read()
    # if not ret:
    #     raise RuntimeError("❌ Failed to capture image at position B.")

    # img_B_path = os.path.join(save_dir, "sample_B.jpg")
    # cv2.imwrite(img_B_path, image_B)
    # print(f"📸 Image B saved to {img_B_path}")

    # distances_B = detect_aruco.detect_from_image(image_B)
    # print(f"🧭 Distances at B: {distances_B}")

    # # --- Step 3: Compare results
    # diffs = {side: distances_B[side] - distances_A[side] for side in distances_A}
    # measured_motion = sum(abs(v) for v in diffs.values()) / len(diffs)
    # offset_error = calibration_distance - measured_motion

    # results = {
    #     "image_A": img_A_path,
    #     "image_B": img_B_path,
    #     "distances_A": distances_A,
    #     "distances_B": distances_B,
    #     "differences": diffs,
    #     "expected_move": calibration_distance,
    #     "measured_move": measured_motion,
    #     "offset_error": offset_error
    # }

    # # --- Clean up
    # cap.release()
    # cv2.destroyAllWindows()

    # print("✅ Calibration complete.")
    # print(f"  Expected move: {calibration_distance:.3f} mm")
    # print(f"  Measured move: {measured_motion:.3f} mm")
    # print(f"  Offset error: {offset_error:+.3f} mm")

    # return results

if __name__ == "__main__":
    calibration_distance = 100
    base_pose = [200, 0, 0, 0, 90, 0]
    calibrate(calibration_distance, base_pose, move_axis='y', camera_index=0, save_dir="samples")