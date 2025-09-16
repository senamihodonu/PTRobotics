# === Imports ===
import sys
import os
import time
import threading
import utils

print("=== Program initialized ===")

# === Parameters ===
speed = 200             # Robot travel speed (mm/s)
print_speed = 15        # Printing speed (mm/s)
inside_offset = 6       # Offset for inner infill moves (mm)
layer_height = 4        # Vertical step per layer (mm)
z_offset = 20           # Safe Z offset for travel moves (mm)
x_offset = 13.5         # X-axis offset (mm)
print_offset = 5        # Vertical offset between passes (mm)
z_correction = 4        # Small correction in Z for alignment (mm)
tolerance = 0

print("Parameters set.")

# === Optional Machine Vision Mode ===
if len(sys.argv) > 1 and sys.argv[1].lower() in ("mv", "machinevision"):
    utils.open_all_cameras()
    print("Machine vision mode: cameras opened.")
else:
    print("Machine vision mode OFF (no cameras opened).")

# === Robot & PLC Setup ===
utils.woody.set_speed(speed)
utils.woody.set_robot_speed_percent(100)
utils.plc.reset_coils()
time.sleep(2)
print("Robot speed configured and PLC coils reset.")

# === Safety Check Function ===
def perform_safety_check():
    while any(utils.plc.read_modbus_coils(c) for c in (8, 9, 14)):
        print("Safety check: coils active, moving Z down and Y right...")
        for coil in (utils.Z_DOWN_MOTION, utils.Y_RIGHT_MOTION):
            utils.plc.write_modbus_coils(coil, True)
    # Reset coil states
    for coil in (utils.Z_DOWN_MOTION, utils.Y_RIGHT_MOTION):
        utils.plc.write_modbus_coils(coil, False)
    print("Safety check complete.")
    time.sleep(1)

perform_safety_check()

# === Helper: Move & Correct Z ===
def move_and_correct(pose, axis, value, layer_height, tolerance):
    pose[axis] = value
    utils.woody.write_cartesian_position(pose)
    print(f"Moved axis {axis} to {value}: {pose}")
    corrected_z = utils.z_difference(layer_height, pose[2], tolerance)
    if corrected_z != pose[2]:
        print(f"Z correction applied: {pose[2]} -> {corrected_z}")
        pose[2] = corrected_z
        utils.plc.md_extruder_switch("off")
        utils.woody.write_cartesian_position(pose)  # update Z only
        utils.plc.md_extruder_switch("on")
    return pose

# === Initial Pose ===
z = 0
pose = [-100, 0, z, 0, 90, 0]
utils.woody.write_cartesian_position(pose)
print(f"Robot moved to initial pose: {pose}")

# === Safe Start ===
utils.plc.md_extruder_switch("off")
print("Extruder OFF for safe start.")

# === Height Calibration ===
pose, z = utils.calibrate_height(pose, layer_height)

# === Print Setup ===
end_height = 12
flg = True

# Turn extruder ON
utils.plc.md_extruder_switch("on")
print("Extruder ON, starting print sequence...")
time.sleep(3)

# === Printing Loop ===
while flg:
    print(f"\n=== Starting new layer at z = {z:.2f} mm ===")

    # Reset start pose
    pose = [-100, 0, z, 0, 90, 0]
    utils.woody.write_cartesian_position(pose)

    utils.woody.set_speed(print_speed)
    utils.plc.md_extruder_switch("on")

    # Path sequence (X and Y moves)
    path_moves = [
        (0, -60),   # X move
        (1, 300),   # Y forward
        (0, 100),   # X forward
        (1, 200),   # Y back
        (1, 150),   # Y back
        (1, 100),   # Y back
        (1, 50),    # Y back
        (1, 0),     # Y back
    ]

    for axis, value in path_moves:
        pose = move_and_correct(pose, axis, value, layer_height, tolerance)

    # End layer
    utils.plc.md_extruder_switch("off")

    z += 4                # Z always goes up by a constant 4 mm
    layer_height += 4     # layer_height grows: 4 → 8 → 12 → 16 …

    if z >=end_height:
        flg = False
        print("Reached target height. Print complete.")
