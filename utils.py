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
current_distance = plc.read_current_distance()



def check_height(layer_height):
    """Check current nozzle height relative to the print bed."""
    z = woody.read_current_cartesian_pose()[2]

    print(f"[Check] Current distance: {current_distance:.2f} mm | Target: {layer_height:.2f} mm | Z: {z:.2f} mm")

    return current_distance, z

def calibrate_height(pose, robot, plc, layer_height):
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

# === Distance Sensor Monitoring Thread ===
stop_monitoring = False  # flag to stop the thread cleanly

def monitor_distance_sensor(layer_height):
    """
    Continuously read distance sensor value from PLC.
    Takes action if value > threshold.
    """
    max_threshold = layer_height+2
    min_threshold = layer_height-2
    if current_distance > max_threshold:
        #Take the difference between the current distance and layer height
        difference= current_distance - max_threshold
        #Translate robot arm by distance
        plc.travel(Z_DOWN_MOTION, difference, "mm", "z")

    if current_distance < min_threshold:
        #Take the difference between the current distance and layer height
        difference= current_distance - min_threshold
        #Translate robot arm by distance
        plc.travel(Z_UP_MOTION, difference, "mm", "z")




