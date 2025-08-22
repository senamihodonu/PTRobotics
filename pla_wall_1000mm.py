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
layer_height = 3.5
z_offset = 20 

# Configure robot/PLC
woody.set_speed(speed)
woody.set_robot_speed_percent(100)
plc.reset_coils()
time.sleep(2)

# Move robot to initial pose
pose = [-100, 0, 0, 0, 90, 0]  # X, Y, Z, W, P, R
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

# === Initial Travel to First Robot Position ===
distance = 95.23
plc.travel(Y_LEFT_MOTION, distance, "mm", "y")

# === Print Setup ===
woody.set_speed(print_speed)          # Set robot print speed
plc.md_extruder_switch("on")          # Turn extruder ON

# === Lead Sequence (First Pass) ===
pose[0] = -60                         # Move X to -60
woody.write_cartesian_position(pose)

pose[1] = 200                         # Move Y to 200
woody.write_cartesian_position(pose)

pose[0] = 100                         # Move X to 100
woody.write_cartesian_position(pose)

pose[1] = 0                           # Return Y to 0
woody.write_cartesian_position(pose)

# === End of First Pass ===
plc.md_extruder_switch("off")         # Turn extruder OFF

# Raise Z to safe height
pose[2] = z_offset
woody.write_cartesian_position(pose)

# Move robot to clearance position (X=100, Y=400)
pose[0] = 100
pose[1] = 400
woody.write_cartesian_position(pose)

# === Transition Travel ===
distance = 495.23
plc.travel(Y_LEFT_MOTION, distance, "mm", "y")

# Lower Z back to print height
pose[2] = 0
woody.write_cartesian_position(pose)

# === Second Pass ===
plc.md_extruder_switch("on")          # Turn extruder ON
pose[1] = -400                        # Move Y to -400 (extruding)
woody.write_cartesian_position(pose)

# End of Second Pass
plc.md_extruder_switch("off")         # Turn extruder OFF





