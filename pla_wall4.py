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

def caliberate_height():
    while True:
        if plc.read_current_distance()/2 > layer_height:
            pose[2]-= plc.read_current_distance()/2
            woody.write_cartesian_position(pose)

        if plc.read_current_distance() > layer_height:
            print(plc.read_current_distance())
            pose[2]-= 1
            woody.write_cartesian_position(pose)

        if plc.read_current_distance() < layer_height:
            print(plc.read_current_distance())
            pose[2]+= 1
            woody.write_cartesian_position(pose)

        if plc.read_current_distance() == layer_height:
            z = woody.read_current_cartesian_pose()[2]
            nozzle_height= plc.read_current_distance()
            print(f"nozzle_height_above_bed is {nozzle_height} mm")
            print(f"Starting z value is {z} mm")
            break
    return pose, z

# === Safe start ===
plc.md_extruder_switch("off")
print("Extruder OFF for safe start.")
while any(plc.read_modbus_coils(c) for c in (8, 9, 14)):
    print("Safety check: coils active, moving Z down and Y right...")
    for coil in (Z_DOWN_MOTION, Y_RIGHT_MOTION):
        plc.write_modbus_coils(coil, True)

for coil in (Z_DOWN_MOTION, Y_RIGHT_MOTION):
    plc.write_modbus_coils(coil, False)
print("Safety check complete.")
time.sleep(1)

pose, z = caliberate_height()

# # === Print setup ===
# plc.md_extruder_switch("on")
# print("Extruder ON, starting print sequence...")
# time.sleep(3)

# # === Printing loop ===
# z = 0
# z_translation_value = 4*layer_height
# flg = True
# end_height = 12*layer_height
# height_accumulation = 0

# while flg:
#     print(f"\n=== Starting new layer at z = {z} ===")

#     # --- First extrusion path ---
#     pose = [-100, 0, z, 0, 90, 0]
#     woody.write_cartesian_position(pose)
#     print(f"Moved to start pose: {pose}")

#     woody.set_speed(print_speed)
#     plc.md_extruder_switch("on")
#     print("Extruder ON for perimeter.")

#     # test_speed = 25
#     # woody.set_speed(test_speed)
#     # Path 1: X move
#     pose[0] = -60 + x_offset
#     woody.write_cartesian_position(pose)
#     print(f"Moving along X: {pose}")

#     # Path 2: Y forward
#     pose[1] = 400
#     woody.write_cartesian_position(pose)
#     print(f"Moving along Y forward: {pose}")

#     # Path 3: X forward
#     pose[2] += z_correction
#     woody.write_cartesian_position(pose)
#     print(f"Moving along X forward: {pose}")


#     # Path 3: X forward
#     pose[0] = 100 + x_offset
#     woody.write_cartesian_position(pose)
#     print(f"Moving along X forward: {pose}")

#     # Path 4: Y back
#     pose[1] = 152
#     woody.write_cartesian_position(pose)
#     print(f"Moving along Y back: {pose}")

#     # Path 3: X forward
#     pose[2] -= z_correction
#     woody.write_cartesian_position(pose)
#     print(f"Moving along X forward: {pose}")

#     # Path 4: Y back
#     pose[1] = -50
#     woody.write_cartesian_position(pose)
#     print(f"Moving along Y back: {pose}")

#     # Path 4: Y back
#     pose[0] = 140
#     woody.write_cartesian_position(pose)
#     print(f"Moving along Y back: {pose}")

#     woody.set_speed(speed)
#     plc.md_extruder_switch("off")
#     print("Extruder OFF - perimeter complete.")

#     # --- Infill path ---
#     pose[0] = -60 + x_offset + inside_offset
#     pose[1] = 0
#     woody.write_cartesian_position(pose)
#     print("Starting infill pass...")

#     woody.set_speed(print_speed)
#     plc.md_extruder_switch("on")

#     pose[0] = 100 + x_offset - inside_offset
#     pose[1] = 200
#     woody.write_cartesian_position(pose)
#     print(f"Infill diagonal 1: {pose}")

#     pose[0] = -60 + x_offset + inside_offset
#     pose[1] = 400 - inside_offset
#     woody.write_cartesian_position(pose)
#     print(f"Infill diagonal 2: {pose}")

#     woody.set_speed(speed)
#     plc.md_extruder_switch("off")
#     print("Extruder OFF - infill complete.")

#     # Raise Z for travel
#     pose[2] += z_offset
#     woody.write_cartesian_position(pose)
#     print(f"Raised to safe Z: {pose[2]}")

#     # Travel move left
#     pose[0] = 100
#     pose[1] = 355
#     woody.write_cartesian_position(pose)
#     print(f"Traveling to Y-left prep: {pose}")

#     distance = 400
#     plc.travel(Y_LEFT_MOTION, distance, "mm", "y")
#     print("Traveling Y-left 400mm.")

#     # Lower back
#     pose[2] -= z_offset
#     woody.write_cartesian_position(pose)
#     print(f"Lowered back to print Z: {pose[2]}")

#     # --- Second extrusion path ---
#     woody.set_speed(print_speed)
#     plc.md_extruder_switch("on")
#     print("Extruder ON for return pass.")
#     time.sleep(1)

#     pose[0] = 100
#     woody.write_cartesian_position(pose)
#     print(f"Traveling to Y-left prep: {pose}")

#     pose[1] = 0
#     woody.write_cartesian_position(pose)
#     print(f"Return path Y=0: {pose}")

#     pose[2] -= z_correction
#     woody.write_cartesian_position(pose)
#     print(f"Applied Z correction: {pose[2]}")

#     pose[1] = -400
#     woody.write_cartesian_position(pose)
#     print(f"Return path Y back: {pose}")

#     pose[0] = -60
#     woody.write_cartesian_position(pose)
#     print(f"Return path X back: {pose}")

#     # Correction loop
#     pose[1] = 44
#     woody.write_cartesian_position(pose)
#     pose[2] += z_correction
#     woody.write_cartesian_position(pose)
#     print("Correction loop complete.")

#     # Path 4
#     pose[1] = 405
#     woody.write_cartesian_position(pose)
#     print(f"Return path final Y forward: {pose}")

#     woody.set_speed(speed)
#     plc.md_extruder_switch("off")
#     print("Extruder OFF - return pass complete.")

#     # --- Infill reverse ---
#     pose[0] = -60 + inside_offset
#     woody.write_cartesian_position(pose)
#     woody.set_speed(print_speed)
#     plc.md_extruder_switch("on")
#     print("Extruder ON - reverse infill.")

#     pose[0] = 100 - inside_offset
#     pose[1] = 200
#     woody.write_cartesian_position(pose)
#     print(f"Reverse infill diagonal 1: {pose}")

#     pose[0] = -60 + inside_offset
#     pose[1] = 0
#     woody.write_cartesian_position(pose)
#     print(f"Reverse infill diagonal 2: {pose}")

#     pose[2] -= z_correction
#     woody.write_cartesian_position(pose)
#     print(f"Applied Z correction: {pose[2]}")

#     pose[0] = 100 - inside_offset
#     pose[1] = -200
#     woody.write_cartesian_position(pose)
#     print(f"Reverse infill diagonal 3: {pose}")

#     pose[0] = -60 + inside_offset
#     pose[1] = -400 + inside_offset
#     woody.write_cartesian_position(pose)
#     print(f"Reverse infill diagonal 4: {pose}")

#     pose[2] += z_correction
#     woody.write_cartesian_position(pose)
#     print("Correction applied end of reverse infill.")

#     woody.set_speed(speed)
#     plc.md_extruder_switch("off")
#     print("Extruder OFF - reverse infill complete.")

#     # Raise Z for travel
#     pose[2] += z_offset
#     woody.write_cartesian_position(pose)
#     print(f"Raised to safe Z: {pose[2]}")

#     plc.travel(Y_RIGHT_MOTION, distance, "mm", "y")
#     print("Traveling Y-right 400mm.")
#     height_accumulation += layer_height 
#     # --- Layer management ---
#     if z >= z_translation_value:
#         distance = z
#         print(f"Z threshold exceeded, traveling up {distance}mm...")
#         plc.travel(Z_UP_MOTION, distance, "mm", "z")
#         z = 0
#         print("Z reset to 0 after vertical translation.")

#     if height_accumulation >= end_height:
#         flg = False
#         print(f"Reached end height {end_height}. Stopping print loop.")

#     print(f"Current vertical height: {z}")
#     z += layer_height
#     print(f"Incremented Z by {layer_height}. New z = {z}")

# print("=== Print job complete ===")
