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

print("Small program established")

# === Initialize PLC and robot ===
plc = PyPLCConnection(PLC_IP)
woody = robot(ROBOT_IP)

# === Parameters ===
speed = 200
print_speed = 20
offset = 4
layer_height = 4
z_offset = 20
x_offset = 13.5
n=1 
print_offset=3

# === Configure robot/PLC ===
woody.set_speed(speed)
woody.set_robot_speed_percent(100)
plc.reset_coils()
time.sleep(2)

# === Initial pose ===
pose = [-100, 0, 0, 0, 90, 0]  # X, Y, Z, W, P, R
woody.write_cartesian_position(pose)

# === Safe start: move Z down + Y right until coils 8, 9, or 14 deactivate ===
plc.md_extruder_switch("off")
while any(plc.read_modbus_coils(c) for c in (8, 9, 14)):
    for coil in (Z_DOWN_MOTION, Y_RIGHT_MOTION):
        plc.write_modbus_coils(coil, True)

# Stop motion
for coil in (Z_DOWN_MOTION, Y_RIGHT_MOTION):
    plc.write_modbus_coils(coil, False)
time.sleep(1)

# === Print setup ===
woody.set_speed(print_speed)
plc.md_extruder_switch("on")
time.sleep(2)

# === Lead Sequence: Pass 1 ===
z = 0
for x in range(2):
    # --- First extrusion path ---
    
    woody.set_speed(print_speed)  
    
    pose = [-100, 0, z, 0, 90, 0]   # Start point
    woody.write_cartesian_position(pose)
    plc.md_extruder_switch("on")
    pose[0] = -60+x_offset                     # Move in X
    woody.write_cartesian_position(pose)

    pose[1] = 104.78                     # Move in Y
    woody.write_cartesian_position(pose)

    plc.md_extruder_switch("off")
    woody.set_speed(speed)
    pose[1] = 400                     # Move in Y
    woody.write_cartesian_position(pose)


    pose[0] = 100+x_offset                    # Move in X
    pose[2] += 4 
    woody.write_cartesian_position(pose)

    pose[2] -= 4 
    pose[1] = 104.78                     # Move in Y
    woody.write_cartesian_position(pose)
    woody.set_speed(print_speed)
    plc.md_extruder_switch("on")

    pose[1] = 0                     # Move in Y
    woody.write_cartesian_position(pose)
    woody.set_speed(speed)
    plc.md_extruder_switch("off")

    pose[0] =100
    pose[1] = 405
    pose[2] +=z_offset
    woody.write_cartesian_position(pose)


    distance = 400
    plc.travel(Y_LEFT_MOTION, distance, 'mm', 'y')  # Travel left
    pose[2] -=z_offset
    woody.write_cartesian_position(pose)
    woody.set_speed(print_speed)
    plc.md_extruder_switch("on")
    time.sleep(1)

    pose[2] +=print_offset
    woody.write_cartesian_position(pose)

    pose[1] = 200                     # Move in Y
    woody.write_cartesian_position(pose)
    woody.set_speed(speed)
    plc.md_extruder_switch("off")



    pose[1] = -400                     # Move in Y
    woody.write_cartesian_position(pose)

    pose[0] = -60                    # Move in X
    woody.write_cartesian_position(pose)

    pose[2] -=print_offset
    woody.write_cartesian_position(pose)

    pose[1] = 200                     # Move in Y
    woody.write_cartesian_position(pose)
    woody.set_speed(print_speed)
    plc.md_extruder_switch("on")

    pose[1] = 400                     # Move in Y
    woody.write_cartesian_position(pose)

    plc.md_extruder_switch("off")
    plc.travel(Y_RIGHT_MOTION, distance, 'mm', 'y')  # Travel left
    pose[2] +=print_offset
    z+=layer_height