# Imports
import sys
import os
import time
import threading

# Set up paths
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.normpath(os.path.join(current_dir, "fanuc_ethernet_ip_drivers", "src"))
sys.path.append(src_path)

# Custom libraries
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

print("Small program established")

# Initialize PLC and robot
plc = PyPLCConnection(PLC_IP)
woody = robot(ROBOT_IP)

# Motion parameters
speed = 200
print_speed = 15
offset = 4
layer_height = 4
z_offset = 20 

# Configure robot/PLC
woody.set_speed(speed)
woody.set_robot_speed_percent(100)
plc.reset_coils()
time.sleep(2)

# Move robot to initial pose
pose = [-100, -400, 0, 0, 90, 0]  # X, Y, Z, W, P, R
woody.write_cartesian_position(pose)

# Ensure safe start: move Z down + Y right until coils 8, 9, or 14 are off
plc.md_extruder_switch("off")
while any(plc.read_modbus_coils(c) for c in (8, 9, 14)):
    for coil in (Z_DOWN_MOTION, Y_RIGHT_MOTION):
        plc.write_modbus_coils(coil, True)

# Stop motion
for coil in (Z_DOWN_MOTION, Y_RIGHT_MOTION):
    plc.write_modbus_coils(coil, False)

time.sleep(1)

# === Print Setup ===
woody.set_speed(print_speed)
plc.md_extruder_switch("on")

# === Lead Sequence ===
pose = [-100, -400, 0, 0, 90, 0]
woody.write_cartesian_position(pose)

for layer in range(3):
    # First pass
    pose[0] = -60
    woody.write_cartesian_position(pose)
    plc.md_extruder_switch("on")

    pose[1] = 400
    woody.write_cartesian_position(pose)

    pose[0] = 100
    woody.write_cartesian_position(pose)

    pose[1] = -400
    woody.write_cartesian_position(pose)

    pose[0] = -60
    woody.write_cartesian_position(pose)

    # Offset passes
    pose[0] = -60 + offset
    pose[1] = -400 + offset
    woody.write_cartesian_position(pose)

    pose[0] = 100 - offset
    pose[1] = -198
    woody.write_cartesian_position(pose)

    pose[0] = -60 + offset
    pose[1] = 0
    woody.write_cartesian_position(pose)

    pose[0] = 100 - offset
    pose[1] = 198
    woody.write_cartesian_position(pose)

    pose[0] = -60 + offset
    pose[1] = 400 - offset
    woody.write_cartesian_position(pose)

    # End layer
    plc.md_extruder_switch("off")
    pose[2] += layer_height
