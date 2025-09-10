# === Imports ===
import sys
import os
import time
import threading

# === Path setup ===
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.normpath(os.path.join(current_dir, "fanuc_ethernet_ip_drivers", "src"))
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
layer_height = 4      # Vertical step per layer (mm)
z_offset = 20           # Safe Z offset for travel moves (mm)
x_offset = 13.5         # X-axis offset (mm)
print_offset = 5        # Vertical offset between passes (mm)
z_correction = 4          # Small correction in Z for alignment (mm)



print("Parameters set.")

# === Configure robot and PLC ===
woody.set_speed(speed)
woody.set_robot_speed_percent(100)
plc.reset_coils()
time.sleep(2)
print("Robot speed configured and PLC coils reset.")

# === Initial pose ===
z = 0
pose = [-100, 0, z, 0, 90, 0]
woody.write_cartesian_position(pose)
print(f"Robot moved to initial pose: {pose}")

def check_height(layer_height):
    """Check current nozzle height relative to the print bed."""
    current_distance = plc.read_current_distance()
    z = woody.read_current_cartesian_pose()[2]

    print(f"[Check] Current distance: {current_distance:.2f} mm | Target: {layer_height:.2f} mm | Z: {z:.2f} mm")

    return current_distance, z

def calibrate_height(layer_height):
    """Calibrate nozzle height relative to the print bed using PLC distance feedback."""

    while True:
        current_distance = plc.read_current_distance()

        # Overshoot by more than half the layer height → move down proportionally
        if current_distance / 2 > layer_height:
            pose[2] -= current_distance / 2
            woody.write_cartesian_position(pose)

        # Too high → move down incrementally
        elif current_distance > layer_height:
            print(f"Distance too high: {current_distance:.2f} mm")
            pose[2] -= 1
            woody.write_cartesian_position(pose)

        # Too low → move up incrementally
        elif current_distance < layer_height:
            print(f"Distance too low: {current_distance:.2f} mm")
            pose[2] += 1
            woody.write_cartesian_position(pose)

        # Correct height reached
        else:
            z = woody.read_current_cartesian_pose()[2]
            nozzle_height = current_distance
            print(f"Nozzle height above bed: {nozzle_height:.2f} mm")
            print(f"Starting Z value: {z:.2f} mm")
            break

    return pose, z


