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
speed = 200             # Robot travel speed (mm/s)
print_speed = 10        # Printing speed (mm/s)
inside_offset = 6       # Offset for inner infill moves (mm)
layer_height = 3.5      # Vertical step per layer (mm)
z_offset = 20           # Safe Z offset for travel moves (mm)
x_offset = 13.5         # X-axis offset (mm)
n = 1                   # Placeholder variable (not used directly here)
print_offset = 5        # Vertical offset between passes (mm)
x = 100                 # Initial X reference position
correction = 4          # Small correction in Z for alignment (mm)

# === Configure robot and PLC ===
woody.set_speed(speed)
woody.set_robot_speed_percent(100)
plc.reset_coils()
time.sleep(2)

# === Initial pose ===
# Pose format: [X, Y, Z, W, P, R]
pose = [-100, 0, 0, 0, 90, 0]
woody.write_cartesian_position(pose)

# === Safe start ===
# Move Z down + Y right until coils 8, 9, or 14 deactivate (safety check)
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

# === Printing loop ===
z = 0
z_translation_value = 4  # Threshold to trigger vertical translation
flg = True               # Printing loop flag
end_height = 12           # Stop condition (max print height)

while flg:
    # --- First extrusion path (outer perimeter) ---
    pose = [-100, 0, z, 0, 90, 0]   # Starting point
    woody.write_cartesian_position(pose)

    woody.set_speed(print_speed)
    plc.md_extruder_switch("on")

    # Path 1: Move in X
    pose[0] = -60 + x_offset
    woody.write_cartesian_position(pose)

    # Path 2: Move Y forward
    pose[1] = 400
    woody.write_cartesian_position(pose)

    # Path 3: Move X forward
    pose[0] = 100 + x_offset
    woody.write_cartesian_position(pose)

    # Path 4: Move Y back
    pose[1] = 0
    woody.write_cartesian_position(pose)

    # End of outer perimeter
    woody.set_speed(speed)
    plc.md_extruder_switch("off")

    # --- Infill path ---
    pose[0] = -60 + x_offset + inside_offset
    pose[1] = 0
    woody.write_cartesian_position(pose)

    woody.set_speed(print_speed)
    plc.md_extruder_switch("on")

    # Infill diagonals
    pose[0] = 100 + x_offset - inside_offset
    pose[1] = 200
    woody.write_cartesian_position(pose)

    pose[0] = -60 + x_offset + inside_offset
    pose[1] = 400 - inside_offset
    woody.write_cartesian_position(pose)

    woody.set_speed(speed)
    plc.md_extruder_switch("off")

    # Raise Z for safe travel
    pose[2] += z_offset
    woody.write_cartesian_position(pose)

    # Travel move: retract and shift Y
    pose[0] = 100
    pose[1] = 405
    woody.write_cartesian_position(pose)

    distance = 400
    plc.travel(Y_LEFT_MOTION, distance, "mm", "y")  # Travel left

    # Lower back to print height
    pose[2] -= z_offset
    woody.write_cartesian_position(pose)

    # --- Second extrusion path (return pass) ---
    woody.set_speed(print_speed)
    plc.md_extruder_switch("on")
    time.sleep(2)

    # Path 1: Y back to start
    pose[1] = 0
    woody.write_cartesian_position(pose)

    # Apply small Z correction
    pose[2] -= correction
    woody.write_cartesian_position(pose)

    # Path 2: Move Y backward
    pose[1] = -400
    woody.write_cartesian_position(pose)

    # Path 3: Move X backward
    pose[0] = -60
    woody.write_cartesian_position(pose)

    # Correction loop
    pose[1] = 44
    woody.write_cartesian_position(pose)
    pose[2] += correction
    woody.write_cartesian_position(pose)

    # Path 4: Move Y forward
    pose[1] = 405
    woody.write_cartesian_position(pose)

    # End of second extrusion
    woody.set_speed(speed)
    plc.md_extruder_switch("off")

    # --- Infill path (reverse pass) ---
    pose[0] = -60 + inside_offset
    woody.write_cartesian_position(pose)

    woody.set_speed(print_speed)
    plc.md_extruder_switch("on")

    pose[0] = 100 - inside_offset
    pose[1] = 200
    woody.write_cartesian_position(pose)

    pose[0] = -60 + inside_offset
    pose[1] = 0
    woody.write_cartesian_position(pose)

    # Apply small Z correction
    pose[2] -= correction
    woody.write_cartesian_position(pose)

    pose[0] = 100 - inside_offset
    pose[1] = -200
    woody.write_cartesian_position(pose)

    pose[0] = -60 + inside_offset
    pose[1] = -400 + inside_offset
    woody.write_cartesian_position(pose)

    pose[2] += correction
    woody.write_cartesian_position(pose)

    woody.set_speed(speed)
    plc.md_extruder_switch("off")

    # Raise Z for travel
    pose[2] += z_offset
    woody.write_cartesian_position(pose)

    # Travel move: back to the right
    plc.travel(Y_RIGHT_MOTION, distance, "mm", "y")

    # --- Layer management ---
    if z > z_translation_value:
        distance = woody.read_current_cartesian_pose()[2]
        plc.travel(Z_UP_MOTION, distance, "mm", "z")
        z = 0

    if z == end_height:   # Stop condition
        flg = False
    print(f"The current vertical height is {z}")
    z += layer_height     # Increment layer height
    print(f"Incrementing vertical height by {layer_height}, z = {z}")
    

