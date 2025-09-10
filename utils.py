# === Imports ===
import sys
import os
import time
import threading

# === Path setup ===
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.normpath(
    os.path.join(current_dir, "fanuc_ethernet_ip_drivers", "src")
)
sys.path.append(src_path)

# === Custom libraries ===
from robot_controller import robot
from PyPLCConnection import (
    PyPLCConnection,
    LEAD_Y_SCREW, LEAD_Z_SCREW,
    DIP_SWITCH_SETTING_Y, DIP_SWITCH_SETTING_Z,
    GREEN,
    Y_LEFT_MOTION, Y_RIGHT_MOTION,
    Z_DOWN_MOTION, Z_UP_MOTION,
    DISTANCE_SENSOR_IN,
    PLC_IP, ROBOT_IP
)

print("=== Program initialized ===")

# === Initialize PLC and Robot ===
plc = PyPLCConnection(PLC_IP)
woody = robot(ROBOT_IP)
print("PLC and Robot connections established.")

# === Parameters ===
speed = 200             # Robot travel speed (mm/s)
print_speed = 10        # Printing speed (mm/s)
inside_offset = 6       # Offset for inner infill moves (mm)
layer_height = 4        # Vertical step per layer (mm)
z_offset = 20           # Safe Z offset for travel moves (mm)
x_offset = 13.5         # X-axis offset (mm)
print_offset = 5        # Vertical offset between passes (mm)
z_correction = 4        # Small correction in Z for alignment (mm)

current_distance = plc.read_current_distance()


# === Functions ===
def check_height(layer_height: float):
    """
    Check the current nozzle height relative to the print bed.
    Returns (current_distance, z).
    """
    z = woody.read_current_cartesian_pose()[2]
    print(f"[Check] Current distance: {current_distance:.2f} mm | "
          f"Target: {layer_height:.2f} mm | Z: {z:.2f} mm")
    return current_distance, z


def calibrate_height(pose, robot, plc, layer_height: float):
    """
    Calibrate nozzle height relative to the print bed using PLC distance feedback.
    Adjusts robot Z until the target layer height is reached.
    """
    while True:
        current_distance = plc.read_current_distance()

        if current_distance / 2 > layer_height:
            # Overshoot → move down proportionally
            pose[2] -= current_distance / 2
            robot.write_cartesian_position(pose)

        elif current_distance > layer_height:
            # Too high → move down incrementally
            print(f"[Calibration] Distance too high: {current_distance:.2f} mm")
            pose[2] -= 1
            robot.write_cartesian_position(pose)

        elif current_distance < layer_height:
            # Too low → move up incrementally
            print(f"[Calibration] Distance too low: {current_distance:.2f} mm")
            pose[2] += 1
            robot.write_cartesian_position(pose)

        else:
            # Correct height reached
            z = robot.read_current_cartesian_pose()[2]
            print(f"[Calibration] Nozzle height: {current_distance:.2f} mm | "
                  f"Starting Z: {z:.2f} mm")
            return pose, z


def monitor_distance_sensor(layer_height: float):
    """
    Monitor distance sensor and correct Z position if deviation exceeds ±2 mm.
    This function should be run in a separate thread if continuous monitoring is required.
    """
    current_distance = plc.read_current_distance()
    max_threshold = layer_height + 2
    min_threshold = layer_height - 2

    if current_distance > max_threshold:
        diff = current_distance - max_threshold
        plc.travel(Z_DOWN_MOTION, diff, "mm", "z")

    elif current_distance < min_threshold:
        diff = min_threshold - current_distance
        plc.travel(Z_UP_MOTION, diff, "mm", "z")
