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
print_speed = 5
woody.set_speed(speed)
woody.set_robot_speed_percent(100)

pose = [-80, -400, 0, 0, 90, 0]  # X, Y, Z, W, P, R
woody.write_cartesian_position(pose)

# Set Y axis speed
plc.calculate_pulse_per_second(speed, DIP_SWITCH_SETTING_Y, LEAD_Y_SCREW, 'y')
print(f"[INFO] PLC Y-axis speed configured to {speed} mm/min")
# Set Z axis speed
plc.calculate_pulse_per_second(speed, DIP_SWITCH_SETTING_Z, LEAD_Z_SCREW, 'z')

plc.md_extruder_switch("off")
# # Ensure initial positioning
while plc.read_modbus_coils(8) == True or plc.read_modbus_coils(9) == True or plc.read_modbus_coils(14) == True:
    plc.write_modbus_coils(Z_DOWN_MOTION, True)
    plc.write_modbus_coils(Y_RIGHT_MOTION,True)
plc.write_modbus_coils(Z_DOWN_MOTION, False)
plc.write_modbus_coils(Y_RIGHT_MOTION,False)
time.sleep(2)

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
woody.set_speed(200)
pose[2] = 10    # Z = 10 mm
woody.write_cartesian_position(pose)

# === ZigZag Pattern (First Pass) ===
pose[0] = 96
pose[1] = 396
woody.write_cartesian_position(pose)

pose[2] = 0     # Lower Z to 0 mm
woody.write_cartesian_position(pose)

# Turn MD on
plc.md_extruder_switch("on")
woody.set_speed(print_speed)

pose[0] = -56
pose[1] = 200
woody.write_cartesian_position(pose)

pose[0] = 96
pose[1] = 0
woody.write_cartesian_position(pose)

pose[0] = -56
pose[1] = -200
woody.write_cartesian_position(pose)

pose[0] = 96
pose[1] = -400
woody.write_cartesian_position(pose)

# === Travel along Y axis using PLC ===
distance = 400
plc.travel(Y_LEFT_MOTION, distance, "mm", 5)


# === Post-Travel Movements ===
pose[0] = -60
woody.write_cartesian_position(pose)

pose[1] = -4
woody.write_cartesian_position(pose)

pose[0] = -100
woody.write_cartesian_position(pose)

pose[1] = 0
woody.write_cartesian_position(pose)

pose[0] = -60
woody.write_cartesian_position(pose)

# Turn MD off
plc.md_extruder_switch("off")

# === ZigZag Pattern (Second Pass) ===
pose[0] = 96
pose[1] = 0
woody.write_cartesian_position(pose)

# Turn MD on
plc.md_extruder_switch("on")

pose[0] = -56
pose[1] = -200
woody.write_cartesian_position(pose)

pose[0] = 96
pose[1] = -396
woody.write_cartesian_position(pose)

plc.md_extruder_switch("off")
# raise Z
# pose[2] = 4
# woody.write_cartesian_position(pose)


