# === Imports ===
import sys
import os
import time
import threading
import utils

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

# === Height Calibration ===
pose, z = utils.calibrate_height(pose, woody, plc, layer_height)

# === Print Parameters ===
z_translation_value = 4 * layer_height
end_height = 12 * layer_height
height_accumulation = 0
flg = True

# === Extruder Setup ===
plc.md_extruder_switch("on")
print("Extruder ON, starting print sequence...")
time.sleep(3)

# === Printing Loop ===
while flg:
    print(f"\n=== Starting new layer at z = {z} ===")

    # --- Move to Start Pose ---
    pose = [-100, 0, z, 0, 90, 0]
    woody.write_cartesian_position(pose)
    print(f"Moved to start pose: {pose}")

    # --- Perimeter Path ---
    woody.set_speed(print_speed)
    plc.md_extruder_switch("on")
    print("Extruder ON for perimeter.")

    # Path 1: X move
    pose[0] = -60
    woody.write_cartesian_position(pose)
    print(f"Moving along X: {pose}")

    # Path 2: Y forward
    pose[1] = 175
    woody.write_cartesian_position(pose)
    print(f"Moving along Y forward: {pose}")

    # Path 3: X forward
    pose[0] = 100
    woody.write_cartesian_position(pose)
    print(f"Moving along X forward: {pose}")

    # Path 4: Y back
    pose[1] = 0
    woody.write_cartesian_position(pose)
    print(f"Moving along Y back: {pose}")

    # --- Travel Move (Lift + Y-shift) ---
    pose[2] += 20
    pose[1] = 250
    woody.write_cartesian_position(pose)
    print(f"Traveling to Y-left prep: {pose}")

    distance = 250
    plc.travel(Y_LEFT_MOTION, distance, "mm", "y")
    print(f"Traveling Y-left {distance}mm.")

    # --- Lower Back to Print Height ---
    pose[2] -= 20
    woody.write_cartesian_position(pose)
    print(f"Lowered back to print Z: {pose[2]}")

    # --- Return Paths ---
    pose[1] = -175
    woody.write_cartesian_position(pose)
    print(f"Return path Y=0: {pose}")

    pose[0] = -60
    woody.write_cartesian_position(pose)
    print(f"Return path X back: {pose}")

    pose[1] = 250
    woody.write_cartesian_position(pose)
    print(f"Return path final Y forward: {pose}")

    # --- Travel Back ---
    plc.travel(Y_RIGHT_MOTION, -distance, "mm", "y")

    # --- Increment Z for Next Layer ---
    z += layer_height
    print(f"Incremented Z by {layer_height}. New z = {z}")

print("=== Print job complete ===")
