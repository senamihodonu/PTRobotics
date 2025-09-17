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


# === Example usage ===
cameras = open_all_cameras(max_cameras=5)

# Read a frame from each camera
for idx, cap in cameras.items():
    ret, frame = cap.read()
    if ret:
        cv2.imshow(f"Camera {idx}", frame)
        cv2.waitKey(500)  # Show each camera for 0.5 seconds

# Release all cameras
for cap in cameras.values():
    cap.release()
cv2.destroyAllWindows()

# def open_all_cameras(camera_indices=[0, 1], window_name="All Cameras"):
#     """
#     Open all cameras specified by camera_indices and show them in one frame.

#     Args:
#         camera_indices (list): List of integer camera IDs (0,1,2…).
#         window_name (str): Name of the display window.
#     """
#     # Open each camera
#     caps = []
#     for idx in camera_indices:
#         cap = cv2.VideoCapture(idx)
#         if not cap.isOpened():
#             print(f"[Camera] Could not open camera {idx}")
#         else:
#             print(f"[Camera] Opened camera {idx}")
#             caps.append(cap)

#     if not caps:
#         print("[Camera] No cameras opened.")
#         return

#     while True:
#         frames = []
#         for cap in caps:
#             ret, frame = cap.read()
#             if not ret:
#                 frames.append(None)
#                 continue
#             # Resize to same height for stacking
#             frame = cv2.resize(frame, (320, 240))
#             frames.append(frame)

#         # Only stack non-None frames
#         frames = [f for f in frames if f is not None]
#         if not frames:
#             break

#         # Horizontally stack all feeds in one window
#         combined = cv2.hconcat(frames)
#         cv2.imshow(window_name, combined)

#         key = cv2.waitKey(1) & 0xFF
#         if key == 27 or key == ord("q"):  # ESC or q to quit
#             break

#     for cap in caps:
#         cap.release()
#     cv2.destroyAllWindows()

# camera_thread = threading.Thread(
#     target=open_all_cameras, 
#     args=([0, 1],),   # change list to your available camera IDs
#     daemon=True
# )
# camera_thread.start()


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


def detect_red_dot_and_distances_mm(image_path, px_per_mm=None, draw=True):
    """
    Detects the largest red dot in an image and computes distances to edges in pixels and mm.
    
    Args:
        image_path (str): Path to the input image.
        px_per_mm (float): Pixels per millimeter scale. If None, returns only pixels.
        draw (bool): Whether to draw circles, lines, and labels on the image.

    Returns:
        distances_px (dict): Distances from the red dot to edges in pixels.
        distances_mm (dict or None): Distances in mm if px_per_mm is provided.
        center (tuple): (x, y) pixel coordinates of the red dot.
        frame (np.array): Image with drawings (only if draw=True).
    """
    frame = cv2.imread(image_path)
    if frame is None:
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Red HSV ranges
    lower_red1 = np.array([0, 120, 70])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 120, 70])
    upper_red2 = np.array([180, 255, 255])

    mask = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)

    # Find contours
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None, None, None, frame  # No red dot found

    # Largest red contour
    c = max(cnts, key=cv2.contourArea)
    (x, y), radius = cv2.minEnclosingCircle(c)
    center = (int(x), int(y))

    h, w = frame.shape[:2]
    distances_px = {
        "Left": x,
        "Right": w - x,
        "Top": y,
        "Bottom": h - y
    }

    distances_mm = None
    if px_per_mm is not None:
        distances_mm = {edge: dist / px_per_mm for edge, dist in distances_px.items()}

    if draw:
        # Draw the detected dot
        cv2.circle(frame, center, int(radius), (0, 255, 0), 2)
        cv2.circle(frame, center, 5, (0, 0, 255), -1)

        # Draw lines and labels
        edge_points = {
            "Left": (0, int(y)),
            "Right": (w, int(y)),
            "Top": (int(x), 0),
            "Bottom": (int(x), h)
        }

        for edge, point in edge_points.items():
            cv2.line(frame, center, point, (255, 0, 255), 2)
            mid_x = (center[0] + point[0]) // 2
            mid_y = (center[1] + point[1]) // 2
            label = f"{distances_px[edge]:.0f}px"
            if distances_mm:
                label += f" / {distances_mm[edge]:.1f}mm"
            cv2.putText(frame, label, (mid_x + 5, mid_y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

    return distances_px, distances_mm, center, frame


# === Example usage ===
image_path = "c1_20250916-171447.jpg"

# Example: 5 pixels per mm (replace with your actual calibration)
px_per_mm = 5.0

distances_px, distances_mm, center, output_frame = detect_red_dot_and_distances_mm(image_path, px_per_mm)

if distances_px:
    print(f"Red dot at: {center} px")
    print("Distances (px / mm):")
    for edge in distances_px.keys():
        print(f"{edge}: {distances_px[edge]:.1f}px / {distances_mm[edge]:.1f}mm")

    # Show image
    cv2.imshow("Red Dot to Edges", output_frame)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
else:
    print("No red dot detected.")
