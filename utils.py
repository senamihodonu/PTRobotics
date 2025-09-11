# === Imports ===
import sys
import os
import time
import threading

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

    z = woody.read_current_cartesian_pose()[2]  # start with the current z

    if current_distance > max_threshold:
        diff = current_distance - layer_height
        z -= diff
    elif current_distance < min_threshold:
        diff = layer_height - current_distance
        z += diff
    else:
        print(f"Z is within bounds. z_value = {z}, current_distance = {current_distance}")

    return z


