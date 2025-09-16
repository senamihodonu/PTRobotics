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
# Pass “mv” or “machinevision” as a CLI argument to enable cameras.
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

# === Initial Pose ===
z = 0
pose = [-100, 0, z, 0, 90, 0]
utils.woody.write_cartesian_position(pose)
print(f"Robot moved to initial pose: {pose}")

# === Safe Start ===
utils.plc.md_extruder_switch("off")
print("Extruder OFF for safe start.")

# Safety check: ensure coils 8, 9, 14 are inactive
while any(utils.plc.read_modbus_coils(c) for c in (8, 9, 14)):
    print("Safety check: coils active, moving Z down and Y right...")
    for coil in (utils.Z_DOWN_MOTION, utils.Y_RIGHT_MOTION):
        utils.plc.write_modbus_coils(coil, True)

# Reset coil states
for coil in (utils.Z_DOWN_MOTION, utils.Y_RIGHT_MOTION):
    utils.plc.write_modbus_coils(coil, False)
print("Safety check complete.")
time.sleep(1)

# # Raise Z to safe height
# # utils.plc.travel(utils.Z_UP_MOTION, 3, "mm", "z")

# === Height Calibration ===
pose, z = utils.calibrate_height(pose, layer_height)

# === Print Setup ===
z_translation_value = 4 * layer_height
end_height = 12 * layer_height
height_accumulation = 0
flg = True

# Turn extruder ON
utils.plc.md_extruder_switch("on")
print("Extruder ON, starting print sequence...")
time.sleep(3)

# === Printing Loop ===
while flg:
    print(f"\n=== Starting new layer at z = {z:.2f} mm ===")

    # --- Move to Start Pose ---
    pose = [-100, 0, z, 0, 90, 0]
    utils.woody.write_cartesian_position(pose)
    print(f"Moved to start pose: {pose}")
    # utils.calibrate_height(pose, layer_height)
    corrected_z = utils.z_difference(layer_height, pose[2], tolerance)
    if corrected_z != pose[2]:
        pose[2] = corrected_z
        utils.woody.write_cartesian_position(pose)  # update robot Z only

    # --- Perimeter Path ---
    utils.woody.set_speed(print_speed)
    utils.plc.md_extruder_switch("on")
    print("Extruder ON for perimeter path.")

    # Path 1: X move
    pose[0] = -60
    utils.woody.write_cartesian_position(pose)
    print(f"Moving along X: {pose}")
    time.sleep(1)
    # utils.calibrate_height(pose, layer_height)
    corrected_z = utils.z_difference(layer_height, pose[2], tolerance)
    if corrected_z != pose[2]:
        pose[2] = corrected_z
        utils.plc.md_extruder_switch("off")
        utils.woody.write_cartesian_position(pose)  # update robot Z only
        utils.plc.md_extruder_switch("on")

    # Path 2: Y forward
    pose[1] = 300
    utils.woody.write_cartesian_position(pose)
    print(f"Moving along Y forward: {pose}")
    # utils.calibrate_height(pose, layer_height)
    corrected_z = utils.z_difference(layer_height, pose[2], tolerance)
    if corrected_z != pose[2]:
        pose[2] = corrected_z
        utils.plc.md_extruder_switch("off")
        utils.woody.write_cartesian_position(pose)  # update robot Z only
        utils.plc.md_extruder_switch("on")

    # Path 3: X forward
    pose[0] = 100
    utils.woody.write_cartesian_position(pose)
    print(f"Moving along X forward: {pose}")
    # utils.calibrate_height(pose, layer_height)
    corrected_z = utils.z_difference(layer_height, pose[2], tolerance)
    if corrected_z != pose[2]:
        pose[2] = corrected_z
        utils.plc.md_extruder_switch("off")
        utils.woody.write_cartesian_position(pose)  # update robot Z only
        utils.plc.md_extruder_switch("on")

    pose[1] = 200
    utils.woody.write_cartesian_position(pose)
    print(f"Moving along Y back: {pose}")
    # utils.calibrate_height(pose, layer_height)
    corrected_z = utils.z_difference(layer_height, pose[2], tolerance)
    if corrected_z != pose[2]:
        pose[2] = corrected_z
        utils.plc.md_extruder_switch("off")
        utils.woody.write_cartesian_position(pose)  # update robot Z only
        utils.plc.md_extruder_switch("on")

    pose[1] = 150
    utils.woody.write_cartesian_position(pose)
    print(f"Moving along Y back: {pose}")
    # utils.calibrate_height(pose, layer_height)
    corrected_z = utils.z_difference(layer_height, pose[2], tolerance)
    if corrected_z != pose[2]:
        pose[2] = corrected_z
        utils.plc.md_extruder_switch("off")
        utils.woody.write_cartesian_position(pose)  # update robot Z only
        utils.plc.md_extruder_switch("on")

    pose[1] = 100
    utils.woody.write_cartesian_position(pose)
    print(f"Moving along Y back: {pose}")
    # utils.calibrate_height(pose, layer_height)
    corrected_z = utils.z_difference(layer_height, pose[2], tolerance)
    if corrected_z != pose[2]:
        pose[2] = corrected_z
        utils.plc.md_extruder_switch("off")
        utils.woody.write_cartesian_position(pose)  # update robot Z only
        utils.plc.md_extruder_switch("on")

    pose[1] = 50
    utils.woody.write_cartesian_position(pose)
    print(f"Moving along Y back: {pose}")
    # utils.calibrate_height(pose, layer_height)
    corrected_z = utils.z_difference(layer_height, pose[2], tolerance)
    if corrected_z != pose[2]:
        pose[2] = corrected_z
        utils.plc.md_extruder_switch("off")
        utils.woody.write_cartesian_position(pose)  # update robot Z only
        utils.plc.md_extruder_switch("on")

    # Path 4: Y back
    pose[1] = 0
    utils.woody.write_cartesian_position(pose)
    print(f"Moving along Y back: {pose}")
    # utils.calibrate_height(pose, layer_height)
    corrected_z = utils.z_difference(layer_height, pose[2], tolerance)
    if corrected_z != pose[2]:
        pose[2] = corrected_z
        utils.plc.md_extruder_switch("off")
        utils.woody.write_cartesian_position(pose)  # update robot Z only
        utils.plc.md_extruder_switch("on")

    # End after one loop (debug mode)
    utils.plc.md_extruder_switch("off")
    z+=4
    layer_height+=layer_height
    if z > 12:
        flg = False



#     # --- Travel Move (Lift + Y-shift) ---
#     utils.plc.md_extruder_switch("off")
#     utils.woody.set_speed(speed)
#     pose[2] += 20
#     pose[1] = 250
#     utils.woody.write_cartesian_position(pose)
#     print(f"Traveling to Y-left prep: {pose}")

#     distance = 50
#     utils.plc.travel(Y_LEFT_MOTION, distance, "mm", "y")
#     print(f"Traveling Y-left {distance}mm.")
#     time.sleep(2)

#     # --- Lower Back to Print Height ---
#     pose[2] -= 20
#     utils.woody.write_cartesian_position(pose)
#     print(f"Lowered back to print Z: {pose[2]}")

#     # --- Return Paths ---
#     utils.woody.set_speed(print_speed)
#     utils.plc.md_extruder_switch("on")
#     time.sleep(2)
#     pose[1] = -175
#     utils.woody.write_cartesian_position(pose)
#     # utils.monitor_distance_sensor(layer_height, True)
#     print(f"Return path Y=0: {pose}")

#     pose[0] = -60
#     utils.woody.write_cartesian_position(pose)
#     # utils.monitor_distance_sensor(layer_height, True)
#     print(f"Return path X back: {pose}")

#     pose[1] = 250
#     utils.woody.write_cartesian_position(pose)
#     print(f"Return path final Y forward: {pose}")
#     # utils.monitor_distance_sensor(layer_height, True)
#     time.sleep(2)
#     utils.woody.set_speed(speed)
#     utils.plc.md_extruder_switch("off")

#     # --- Increment Z for Next Layer ---
#     z += layer_height
#     pose = [-100, 0, z, 0, 90, 0]
#     utils.woody.write_cartesian_position(pose)
#     print(f"Incremented Z by {layer_height}. New z = {z}")

#     # --- Travel Back ---
#     print("Travel back")
#     utils.plc.travel(Y_RIGHT_MOTION, distance, "mm", "y")



# print("=== Print job complete ===")
