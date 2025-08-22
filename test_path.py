# Imports
import sys
import os
import time
import threading

# Get the absolute path to the directory of this script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Navigate to the fanuc_ethernet_ip_drivers/src directory
src_path = os.path.normpath(
    os.path.join(current_dir, "fanuc_ethernet_ip_drivers", "src")
)

# Add the src path to sys.path
sys.path.append(src_path)

from robot_controller import robot

from PyPLCConnection import (
    PyPLCConnection,
    LEAD_Y_SCREW, LEAD_Z_SCREW,
    DIP_SWITCH_SETTING_Y,
    GREEN,
    Y_LEFT_MOTION, Y_RIGHT_MOTION,
    Z_DOWN_MOTION, Z_UP_MOTION,
    DISTANCE_SENSOR_IN,
    DIP_SWITCH_SETTING_Z,
    PLC_IP,
    ROBOT_IP
)


print("Small program established")

plc = PyPLCConnection(PLC_IP)


woody = robot(ROBOT_IP)
speed = 200
print_speed = 20
offset = 4
z_offset = 20 
woody.set_speed(speed)
woody.set_robot_speed_percent(100)
plc.reset_coils()
time.sleep(2)

pose = [-100, -400, 0, 0, 90, 0]  # X, Y, Z, W, P, R
woody.write_cartesian_position(pose)


plc.md_extruder_switch("off")
# Ensure initial positioning: move Z down and Y right 
# until coils 8, 9, or 14 are no longer active
while any(plc.read_modbus_coils(c) for c in (8, 9, 14)):
    for coil in (Z_DOWN_MOTION, Y_RIGHT_MOTION):
        plc.write_modbus_coils(coil, True)

# Stop motion
for coil in (Z_DOWN_MOTION, Y_RIGHT_MOTION):
    plc.write_modbus_coils(coil, False)

time.sleep(1)


# === Setup ===
woody.set_speed(print_speed)

# Optional: Move robot to home (commented)
# print("[HOME] Moving robot to home position")
# pose = [0, -30, 30, 0, -30, 0]  # J1..J6
# woody.write_cartesian_position(pose)

# Start with MD on
plc.md_extruder_switch("on")

# === Lead Sequence ===
pose = [-100, -400, 0, 0, 90, 0]  # X, Y, Z, W, P, R
woody.write_cartesian_position(pose)

pose[0] = -60   # X = -60
woody.write_cartesian_position(pose)

pose[1] = 400   # Y = 400
woody.write_cartesian_position(pose)

pose[0] = 100   # X = 100
woody.write_cartesian_position(pose)

pose[1] = -400  # Y = -400
woody.write_cartesian_position(pose)

# Turn MD off before moving up
plc.md_extruder_switch("off")

# Move up slightly before zig-zag
woody.set_speed(speed)
pose[2] = z_offset    
woody.write_cartesian_position(pose)

# === ZigZag Pattern (First Pass) ===
pose[0] = 100-offset
pose[1] = 400-offset
woody.write_cartesian_position(pose)

pose[2] = 0     # Lower Z to 0 mm
woody.write_cartesian_position(pose)

# Turn MD on
plc.md_extruder_switch("on")
woody.set_speed(print_speed)

pose[0] = -60+offset
pose[1] = 200
woody.write_cartesian_position(pose)

pose[0] = 100-offset
pose[1] = 0
woody.write_cartesian_position(pose)

pose[0] = -60+offset
pose[1] = -200
woody.write_cartesian_position(pose)

pose[0] = 100-offset
pose[1] = -400
woody.write_cartesian_position(pose)
plc.md_extruder_switch("off")

woody.set_speed(speed)
pose[2] = z_offset    
woody.write_cartesian_position(pose)
pose[0] = 100
pose[1] = 20
woody.write_cartesian_position(pose)

# === Travel along Y axis using PLC ===
distance = 400
plc.travel(Y_LEFT_MOTION, distance, "mm", "y")

woody.set_speed(print_speed)
plc.md_extruder_switch("on")

pose[2] = 0
woody.write_cartesian_position(pose)

# === Post-Travel Movements ===
pose[1] = -400
woody.write_cartesian_position(pose)

pose[0] = -60
woody.write_cartesian_position(pose)

pose[1] = -offset
woody.write_cartesian_position(pose)

pose[0] = -100
woody.write_cartesian_position(pose)

pose[1] = 0
woody.write_cartesian_position(pose)

pose[0] = -60
woody.write_cartesian_position(pose)

# Turn MD off
plc.md_extruder_switch("off")
woody.set_speed(speed)

# === ZigZag Pattern (Second Pass) ===
pose[0] = 96
pose[1] = 0
woody.write_cartesian_position(pose)

# Turn MD on
woody.set_speed(print_speed)
plc.md_extruder_switch("on")

pose[0] = -60+offset
pose[1] = -200
woody.write_cartesian_position(pose)

pose[0] = 100-offset
pose[1] = -400+offset
woody.write_cartesian_position(pose)
plc.md_extruder_switch("off")

plc.travel(Z_UP_MOTION, 4,"mm","z")

woody.set_speed(speed)
pose[0] = -60
pose[1] = 400
woody.write_cartesian_position(pose)

woody.set_speed(print_speed)
plc.md_extruder_switch("on")

pose[1] = -400
woody.write_cartesian_position(pose)

pose[0] = 100
woody.write_cartesian_position(pose)

pose[1] = 400
woody.write_cartesian_position(pose)

pose[0] = 100-offset
woody.write_cartesian_position(pose)

pose[0] = -60+offset
pose[1] = 200
woody.write_cartesian_position(pose)

pose[0] = 100-offset
pose[1] = 0
woody.write_cartesian_position(pose)

pose[0] = -60+offset
pose[1] = -200
woody.write_cartesian_position(pose)

pose[0] = 100-offset
pose[1] = -400+offset
woody.write_cartesian_position(pose)

plc.md_extruder_switch("off")
woody.set_speed(speed)
pose[2] = z_offset    # Z = 10 mm
woody.write_cartesian_position(pose)

pose[0] = 100
pose[1] = 0
woody.write_cartesian_position(pose)



woody.set_speed(print_speed)
distance = 400
plc.travel(Y_RIGHT_MOTION, distance, "mm", "y")
plc.md_extruder_switch("on")

pose[1] = 400
pose[2] = 0 
woody.write_cartesian_position(pose)

pose[0] = -60
woody.write_cartesian_position(pose)

pose[1] = 4
woody.write_cartesian_position(pose)

plc.md_extruder_switch("off")
woody.set_speed(speed)

pose[0] = 96
pose[1] = 0
woody.write_cartesian_position(pose)

woody.set_speed(print_speed)
plc.md_extruder_switch("on")

pose[0] = -60+offset
pose[1] = 200
woody.write_cartesian_position(pose)

pose[0] = 100-offset
pose[1] = 400-offset
woody.write_cartesian_position(pose)
plc.md_extruder_switch("off")


# raise Z
# pose[2] = 4
# woody.write_cartesian_position(pose)


