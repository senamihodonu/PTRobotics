# # === Imports ===
# import sys
# import os
# import time
# import threading
# import utils

# print("=== Program initialized ===")

# # === Parameters ===
# speed = 200             # Robot travel speed (mm/s)
# print_speed = 200        # Printing speed (mm/s)
# inside_offset = 6       # Offset for inner infill moves (mm)
# layer_height = 4        # Vertical step per layer (mm)
# z_offset = 20           # Safe Z offset for travel moves (mm)
# x_offset = 13.5         # X-axis offset (mm)
# print_offset = 5        # Vertical offset between passes (mm)
# z_correction = 4        # Small correction in Z for alignment (mm)
# tolerance = 0
# z_increment = layer_height

# print("Parameters set.")


# # === Helper Function ===
# def apply_z_correction(pose, layer_height, tolerance):
#     """Check and apply Z correction safely (extruder OFF during adjustment)."""
#     corrected_z = utils.z_difference(layer_height, pose[2], tolerance)
#     if corrected_z != pose[2]:
#         pose[2] = corrected_z
#         utils.plc.md_extruder_switch("off")
#         utils.woody.write_cartesian_position(pose)  # update robot Z only
#         utils.plc.md_extruder_switch("on")
#     return pose

# # === Optional Machine Vision Mode ===
# if len(sys.argv) > 1 and sys.argv[1].lower() in ("mv", "machinevision"):
#     utils.open_all_cameras()
#     print("Machine vision mode: cameras opened.")
# else:
#     print("Machine vision mode OFF (no cameras opened).")

# # === Robot & PLC Setup ===
# utils.woody.set_speed(speed)
# utils.woody.set_robot_speed_percent(100)
# utils.plc.reset_coils()
# time.sleep(2)
# print("Robot speed configured and PLC coils reset.")

# # === Initial Pose ===
# z = 0
# pose = [-100, 0, z, 0, 90, 0]
# utils.woody.write_cartesian_position(pose)
# print(f"Robot moved to initial pose: {pose}")

# # === Safe Start ===
# utils.plc.md_extruder_switch("off")
# print("Extruder OFF for safe start.")

# while any(utils.plc.read_modbus_coils(c) for c in (8, 9, 14)):
#     print("Safety check: coils active, moving Z down and Y right...")
#     for coil in (utils.Z_DOWN_MOTION, utils.Y_RIGHT_MOTION):
#         utils.plc.write_modbus_coils(coil, True)

# for coil in (utils.Z_DOWN_MOTION, utils.Y_RIGHT_MOTION):
#     utils.plc.write_modbus_coils(coil, False)
# print("Safety check complete.")
# time.sleep(1)


# # === Height Calibration ===
# pose, z = utils.calibrate_height(pose, layer_height)

# temp = z

# # === Print Setup ===
# z_translation_value = 4 * layer_height

# height_accumulation = 0
# flg = True

# utils.plc.md_extruder_switch("on")
# print("Extruder ON, starting print sequence...")
# time.sleep(5)

# # === Printing Loop ===
# while flg:
#     layers = 1
#     print(f"\n=== Starting new layer at z = {z:.2f} mm ===")

#     # --- Move to Start Pose ---
#     pose = [-100, 0, z, 0, 90, 0]
#     utils.woody.write_cartesian_position(pose)
#     print(f"Moved to start pose: {pose}")
#     pose = apply_z_correction(pose, layer_height, tolerance)
#     print(f"Z is{z}")

#     # --- Perimeter Path ---
#     utils.woody.set_speed(print_speed)
#     utils.plc.md_extruder_switch("on")
#     print("Extruder ON for perimeter path.")
#     print(f"Z is{z}")

#     # Path 1: X move
#     pose[0] = -60
#     utils.woody.write_cartesian_position(pose)
#     print(f"Moving along X: {pose}")
#     pose = apply_z_correction(pose, layer_height, tolerance)
#     print(f"Z is{z}")

#     # Path 2: Y forward
#     pose[1] = 400
#     utils.woody.write_cartesian_position(pose)
#     print(f"Moving along Y forward: {pose}")
#     pose = apply_z_correction(pose, layer_height, tolerance)
#     print(f"Z is{z}")

#     # Path 2: Y forward
#     pose[0] = 100
#     utils.woody.write_cartesian_position(pose)
#     print(f"Moving along Y forward: {pose}")
#     pose = apply_z_correction(pose, layer_height, tolerance)
#     print(f"Z is{z}")

#     for y in [300, 200, 150, 100, 50, 0]:
#         pose[1] = y
#         utils.woody.write_cartesian_position(pose)
#         print(f"Moving along Y back: {pose}")
#         pose = apply_z_correction(pose, layer_height, tolerance)
#         print(f"Z is{z}")
    
#     time.sleep(2)
#     utils.plc.md_extruder_switch("off")
#     utils.woody.set_speed(speed)
#     pose[2] += 20
#     utils.woody.write_cartesian_position(pose)

#     distance = 400
#     utils.plc.travel(utils.Y_LEFT_MOTION, distance, 'mm', 'y')  # Travel right


#     pose[1] = 400
#     utils.woody.write_cartesian_position(pose)
#     print(f"Moving along Y forward: {pose}")
#     pose = apply_z_correction(pose, layer_height, tolerance)
#     print(f"Z is{z}")
#     utils.plc.md_extruder_switch("on")
#     time.sleep(1)

#     for y in [300, 200, 100, 0, -100, -200, -300, -400]:
#         pose[1] = y
#         utils.woody.write_cartesian_position(pose)
#         print(f"Moving along Y back: {pose}")
#         pose = apply_z_correction(pose, layer_height, tolerance)
#         print(f"Z is{z}")

#     pose[0] = -60
#     utils.woody.write_cartesian_position(pose)
#     print(f"Moving along Y forward: {pose}")
#     pose = apply_z_correction(pose, layer_height, tolerance)

#     for y in [-300, -200, -100, 0, 100, 200, 300, 400]:
#         pose[1] = y
#         utils.woody.write_cartesian_position(pose)
#         print(f"Moving along Y back: {pose}")
#         pose = apply_z_correction(pose, layer_height, tolerance)
#         print(f"Z is{z}")
    
#     time.sleep(1)
#     utils.plc.md_extruder_switch("off")
#     utils.woody.set_speed(speed)
#     pose[2] += 20
#     utils.woody.write_cartesian_position(pose)

#     # --- Travel Back ---
#     print("Travel back")
#     utils.plc.travel(utils.Y_RIGHT_MOTION, distance, "mm", "y")

#     flg = False


# === Imports ===
import sys
import os
import time
import threading
import utils

print("=== Program initialized ===")

# === Parameters ===
SPEED = 200            # Robot travel speed (mm/s)
PRINT_SPEED = 200       # Printing speed (mm/s)
INSIDE_OFFSET = 6      # Offset for inner infill moves (mm)
LAYER_HEIGHT = 6       # Vertical step per layer (mm)
Z_OFFSET = 20          # Safe Z offset for travel moves (mm)
X_OFFSET = 9           # X-axis offset (mm)
PRINT_OFFSET = 5       # Vertical offset between passes (mm)
Z_CORRECTION = 4       # Small correction in Z for alignment (mm)
TOLERANCE = 0
Z_INCREMENT = LAYER_HEIGHT

print("Parameters set.")

# === Helper Functions ===
def apply_z_correction(pose, layer_height, tolerance, extruding=False):
    """
    Check and apply Z correction safely.
    The extruder is turned OFF during adjustment.
    """
    corrected_z = utils.z_difference(layer_height, pose[2], tolerance)
    if corrected_z != pose[2]:
        pose[2] = corrected_z
        if extruding:
            utils.plc.md_extruder_switch("off")
        utils.woody.write_cartesian_position(pose)
        if extruding:
            utils.plc.md_extruder_switch("on")
    return pose


def safety_check():
    """
    Ensure no safety coils are active before starting.
    Moves Z down and Y right if coils are active.
    """
    while any(utils.plc.read_modbus_coils(c) for c in (8, 9, 14)):
        print("Safety check: coils active, moving Z down and Y right...")
        for coil in (utils.Z_DOWN_MOTION, utils.Y_RIGHT_MOTION):
            utils.plc.write_modbus_coils(coil, True)

    # Turn off safety coils
    for coil in (utils.Z_DOWN_MOTION, utils.Y_RIGHT_MOTION):
        utils.plc.write_modbus_coils(coil, False)

    print("Safety check complete.")
    time.sleep(1)


def move_to_pose(pose, extruding=False):
    """Move robot to a given pose with Z correction."""
    utils.woody.write_cartesian_position(pose)
    return apply_z_correction(pose, LAYER_HEIGHT, TOLERANCE, extruding)


def sweep_y_positions(pose, y_positions, extruding=False):
    """Sweep through a list of Y positions at the current X."""
    for y in y_positions:
        pose[1] = y
        pose = move_to_pose(pose, extruding)
    return pose


def lift_and_travel(pose, travel_distance, direction):
    """Lift Z and travel using PLC motion."""
    utils.plc.md_extruder_switch("off")
    utils.woody.set_speed(SPEED)

    pose[2] += Z_OFFSET
    utils.woody.write_cartesian_position(pose)

    utils.plc.travel(direction, travel_distance, 'mm', 'y')
    return pose


# === Machine Vision Mode ===
if len(sys.argv) > 1 and sys.argv[1].lower() in ("mv", "machinevision"):
    utils.open_all_cameras()
    print("Machine vision mode: cameras opened.")
else:
    print("Machine vision mode OFF (no cameras opened).")

# === Robot & PLC Setup ===
utils.woody.set_speed(SPEED)
utils.woody.set_robot_speed_percent(100)
utils.plc.reset_coils()
time.sleep(2)
print("Robot speed configured and PLC coils reset.")

# === Initial Pose ===
z = 0
pose = [-100, 0, z, 0, 90, 0]
utils.woody.write_cartesian_position(pose)
print(f"Robot moved to initial pose: {pose}")

# === Safe Start & Safety Check ===
utils.plc.md_extruder_switch("off")
print("Extruder OFF for safe start.")
safety_check()

# === Height Calibration ===
pose, z = utils.calibrate_height(pose, LAYER_HEIGHT)

# === Print Setup ===
utils.plc.md_extruder_switch("on")
print("Extruder ON, starting print sequence...")
time.sleep(4)

# === Printing Loop ===
flg = True
while flg:
    # Perimeter path
    pose = [-110, 0, z, 0, 90, 0]
    pose = move_to_pose(pose)

    # utils.woody.set_speed(PRINT_SPEED)
    # utils.plc.md_extruder_switch("on")
    # pose = sweep_y_positions(pose, [-300, -200, -100, 0, 100, 200, 300, 400], extruding=True)
    # utils.plc.md_extruder_switch("off")

    # Move to opposite X, then print back
    utils.woody.set_speed(SPEED)
    pose[0] = 150
    pose = move_to_pose(pose)

    utils.woody.set_speed(PRINT_SPEED)
    utils.plc.md_extruder_switch("on")
    pose[1] = 400
    pose = move_to_pose(pose)
    # pose = sweep_y_positions(pose, [300, 200, 100, 0, -100, -200, -300, -400], extruding=True)
    utils.plc.md_extruder_switch("off")
    
    
    # Lift and travel left
    pose = lift_and_travel(pose, 400, utils.Y_LEFT_MOTION)
    utils.plc.md_extruder_switch("off")

    pose[1] = -400
    pose = move_to_pose(pose)



    # # Raise Z before next pass
    # utils.woody.set_speed(SPEED)
    # pose[2] += 20
    # utils.woody.write_cartesian_position(pose)



    # print(f"\n=== Starting new layer at z = {z:.2f} mm ===")
    # pose = [-100, 0, z, 0, 90, 0]
    # pose = move_to_pose(pose, extruding=False)

    # # --- Inlined Perimeter Path ---
    # utils.woody.set_speed(PRINT_SPEED)
    # utils.plc.md_extruder_switch("on")
    # print("Extruder ON for perimeter path.")

    # # X move
    # pose[0] = -60
    # pose = move_to_pose(pose,True)

    # # Y forward
    # pose[1] = 200
    # pose = move_to_pose(pose,True)

    # # Y forward
    # pose[1] = 400
    # pose = move_to_pose(pose,True)

    # # X move
    # pose[0] = 100
    # pose = move_to_pose(pose,True)

    # # Y back sweeps
    # pose = sweep_y_positions(pose, [300, 200, 150, 100, 50, 0],True)
    # # --- End Inlined Perimeter Path ---

    # pose[0] = 140
    # pose = move_to_pose(pose,True)

    # # Lift and travel left
    # pose = lift_and_travel(pose, 400, utils.Y_LEFT_MOTION)
    # utils.plc.md_extruder_switch("off")
    

    # # Move forward to start sweeps
    # pose[0] = 100
    # pose[1] = 405
    # pose = move_to_pose(pose)
    # utils.plc.md_extruder_switch("on")
    # utils.woody.set_speed(PRINT_SPEED)
    # time.sleep(2)

    # # Sweeps forward/back
    # pose = sweep_y_positions(pose, [300, 200, 100, 0, -100, -200, -300, -400],True)

    # pose[0] = -60
    # pose = move_to_pose(pose)
    # pose = sweep_y_positions(pose, [-300, -200, -100, 0, 100, 200, 300, 400], True)
    # utils.plc.md_extruder_switch("off")


    # # Lift and travel back
    # pose = lift_and_travel(pose, 400, utils.Y_RIGHT_MOTION)
    # print("Travel back complete.")

    # # End loop for now
    flg = False
