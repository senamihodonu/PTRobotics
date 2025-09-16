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



print("=== Program initialized ===")

# === Initialize PLC and Robot ===
# plc = PyPLCConnection(PLC_IP)
# woody = robot(ROBOT_IP)

print("PLC and Robot connections established.")
# plc.reset_coils()

# === Parameters ===
speed = 200            # Robot travel speed (mm/s)
print_speed = 10       # Printing speed (mm/s)
inside_offset = 6      # Offset for inner infill moves (mm)
layer_height = 4       # Vertical step per layer (mm)
z_offset = 20          # Safe Z offset for travel moves (mm)
x_offset = 13.5        # X-axis offset (mm)
print_offset = 5       # Vertical offset between passes (mm)
z_correction = 4       # Fine Z correction for alignment (mm)

# current_distance = plc.read_current_distance()
flg = True

def open_all_cameras(camera_indices=[0, 1], window_name="All Cameras"):
    """
    Open all cameras specified by camera_indices and show them in one frame.

    Args:
        camera_indices (list): List of integer camera IDs (0,1,2…).
        window_name (str): Name of the display window.
    """
    # Open each camera
    caps = []
    for idx in camera_indices:
        cap = cv2.VideoCapture(idx)
        if not cap.isOpened():
            print(f"[Camera] Could not open camera {idx}")
        else:
            print(f"[Camera] Opened camera {idx}")
            caps.append(cap)

    if not caps:
        print("[Camera] No cameras opened.")
        return

    while True:
        frames = []
        for cap in caps:
            ret, frame = cap.read()
            if not ret:
                frames.append(None)
                continue
            # Resize to same height for stacking
            frame = cv2.resize(frame, (320, 240))
            frames.append(frame)

        # Only stack non-None frames
        frames = [f for f in frames if f is not None]
        if not frames:
            break

        # Horizontally stack all feeds in one window
        combined = cv2.hconcat(frames)
        cv2.imshow(window_name, combined)

        key = cv2.waitKey(1) & 0xFF
        if key == 27 or key == ord("q"):  # ESC or q to quit
            break

    for cap in caps:
        cap.release()
    cv2.destroyAllWindows()

camera_thread = threading.Thread(
    target=open_all_cameras, 
    args=([0, 1],),   # change list to your available camera IDs
    daemon=True
)
camera_thread.start()


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

# Modern OpenCV (4.7+)
import cv2
import numpy as np
import sys

# === ArUco Setup ===
ARUCO_DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
ARUCO_PARAMS = cv2.aruco.DetectorParameters()
DETECTOR = cv2.aruco.ArucoDetector(ARUCO_DICT, ARUCO_PARAMS)


def detect_aruco(frame):
    """
    Returns:
      detected: list of dicts: [{'id': int, 'corners': np.array(4,2), 'center_px': (u,v)}...]
    """
    if len(frame.shape) == 3:  # Color image (H, W, 3)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:  # Already grayscale (H, W)
        gray = frame

    corners, ids, _ = DETECTOR.detectMarkers(gray)
    out = []
    if ids is None:
        return out
    for c, i in zip(corners, ids.flatten()):
        c = c.reshape((4, 2))  # 4 corners
        cx, cy = float(c[:, 0].mean()), float(c[:, 1].mean())
        out.append({'id': int(i), 'corners': c, 'center_px': (cx, cy)})
    return out


if __name__ == "__main__":
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # force DirectShow on Windows
    if not cap.isOpened():
        print("[Camera] Could not open camera 0")
        sys.exit(1)

    ret, frame = cap.read()
    if ret:
        detections = detect_aruco(frame)
        print(detections)
        # optional: draw detections
        if detections:
            for d in detections:
                cv2.aruco.drawDetectedMarkers(frame, [d['corners']], np.array([d['id']]))
            cv2.imshow("ArUco", frame)
            cv2.waitKey(0)

    cap.release()
    cv2.destroyAllWindows()


