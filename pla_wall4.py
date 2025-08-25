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

print("Program initialized.")

# === Initialize PLC and Robot ===
plc = PyPLCConnection(PLC_IP)
woody = robot(ROBOT_IP)

# === Parameters ===
speed = 200            # Robot travel speed (mm/s)
print_speed = 20       # Printing speed (mm/s)
inside_offset = 4
layer_height = 4       # Layer height (mm)
z_offset = 20          # Safe Z offset (mm)
x_offset = 13.5        # X-axis offset (mm)
n = 2
print_offset = 3       # Vertical offset between passes (mm)
x = 100                # Initial X reference position

# === Configure robot and PLC ===
woody.set_speed(speed)
woody.set_robot_speed_percent(100)
plc.reset_coils()
time.sleep(2)

# === Initial pose ===
pose = [-100, 0, 0, 0, 90, 0]  # Format: [X, Y, Z, W, P, R]
woody.write_cartesian_position(pose)

# === Safe start ===
# Move Z down + Y right until coils 8, 9, or 14 deactivate
plc.md_extruder_switch("off")
while any(plc.read_modbus_coils(c) for c in (8, 9, 14)):
    for coil in (Z_DOWN_MOTION, Y_RIGHT_MOTION):
        plc.write_modbus_coils(coil, True)

# Stop motion once safe
for coil in (Z_DOWN_MOTION, Y_RIGHT_MOTION):
    plc.write_modbus_coils(coil, False)
time.sleep(1)

# === Print setup ===
plc.md_extruder_switch("on")
time.sleep(2)

# === Printing sequence ===
z = 0
for layer in range(n):  
    # --- First extrusion path ---
    pose = [-100, 0, z, 0, 90, 0]  # Start point
    woody.write_cartesian_position(pose)

    woody.set_speed(print_speed)
    plc.md_extruder_switch("on")

    # Path 1: X move
    pose[0] = -60 + x_offset
    woody.write_cartesian_position(pose)

    # Path 2: Y move forward
    pose[1] = 400
    woody.write_cartesian_position(pose)

    # Path 3: Raise Z slightly
    pose[2] += print_offset
    woody.write_cartesian_position(pose)

    # Path 4: X move forward
    pose[0] = 100 + x_offset
    woody.write_cartesian_position(pose)

    # Path 5: Y move back
    pose[1] = 0
    woody.write_cartesian_position(pose)

    # End of first extrusion
    woody.set_speed(speed)
    plc.md_extruder_switch("off")

    #==infill==
    pose[0] = -60+x_offset+inside_offset
    pose[1] = 0
    woody.write_cartesian_position(pose)

    woody.set_speed(print_speed)
    plc.md_extruder_switch("on")
    time.sleep(1)

    pose[0] = 100+x_offset-inside_offset
    pose[1] = 200
    woody.write_cartesian_position(pose)

    pose[0] = -60+x_offset+inside_offset
    pose[1] = 400-inside_offset
    woody.write_cartesian_position(pose)

    woody.set_speed(speed)
    plc.md_extruder_switch("off")

    # Travel move: retract Z and shift Y
    pose[0] = 100
    pose[1] = 405
    pose[2] += z_offset
    woody.write_cartesian_position(pose)

    distance = 400
    plc.travel(Y_LEFT_MOTION, distance, "mm", "y")  # Travel left

    # Lower back to print height
    pose[2] -= z_offset
    woody.write_cartesian_position(pose)

    # --- Second extrusion path ---
    woody.set_speed(print_speed)
    plc.md_extruder_switch("on")
    time.sleep(1)

    # Path 1: Y move backward
    pose[1] = -400
    woody.write_cartesian_position(pose)

    # Path 2: Lower Z slightly
    pose[2] -= print_offset
    woody.write_cartesian_position(pose)

    # Path 3: X move backward
    pose[0] = -60
    woody.write_cartesian_position(pose)

    # Path 4: Y move forward
    pose[1] = 400
    woody.write_cartesian_position(pose)

    # End of second extrusion
    woody.set_speed(speed)
    plc.md_extruder_switch("off")

    pose[0] = -60+inside_offset
    woody.write_cartesian_position(pose)

    woody.set_speed(print_speed)
    plc.md_extruder_switch("on")

    pose[0] = 100-inside_offset
    pose[1] = 200
    woody.write_cartesian_position(pose)

    pose[0] = -60+inside_offset
    pose[1] = 0
    woody.write_cartesian_position(pose)

    pose[0] = 100-inside_offset
    pose[1] = -200
    woody.write_cartesian_position(pose)

    pose[0] = -60+inside_offset
    pose[1] = -400+inside_offset
    woody.write_cartesian_position(pose)

    woody.set_speed(speed)
    plc.md_extruder_switch("off")

    # Travel move back to the right
    plc.travel(Y_RIGHT_MOTION, distance, "mm", "y")

    # Raise Z slightly for next layer
    # pose[2] += print_offset
    z += layer_height
