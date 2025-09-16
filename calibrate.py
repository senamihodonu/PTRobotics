import cv2
import numpy as np
import os

# === Setup ===
chessboard_size = (9, 6)  # inner corners per row & col
save_dir = "calib_images"
os.makedirs(save_dir, exist_ok=True)

# Prepare 3D object points
objp = np.zeros((chessboard_size[0] * chessboard_size[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:chessboard_size[0], 0:chessboard_size[1]].T.reshape(-1, 2)

objpoints, imgpoints = [], []
saved_images = []  # Keep track of saved image paths
cap = cv2.VideoCapture(1)
img_count = 0

print("Press 's' = save, 'd' = delete last, 'q' = quit and calibrate.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    ret_corners, corners = cv2.findChessboardCorners(gray, chessboard_size, None)

    if ret_corners:
        cv2.drawChessboardCorners(frame, chessboard_size, corners, ret_corners)

    cv2.putText(frame, f"Saved: {img_count}", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow("Calibration Capture", frame)

    key = cv2.waitKey(1) & 0xFF

    # Save image
    if key == ord("s") and ret_corners:
        img_path = os.path.join(save_dir, f"calib_{img_count}.jpg")
        cv2.imwrite(img_path, frame)
        objpoints.append(objp)
        imgpoints.append(corners)
        saved_images.append(img_path)
        img_count += 1
        print(f"✅ Saved image {img_count} -> {img_path}")

    # Delete last image
    elif key == ord("d") and img_count > 0:
        last_img = saved_images.pop()
        if os.path.exists(last_img):
            os.remove(last_img)
            print(f"🗑️ Deleted last image -> {last_img}")
        objpoints.pop()
        imgpoints.pop()
        img_count -= 1
        print(f"Images remaining: {img_count}")

    # Quit
    elif key == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()

# === Calibration ===
if img_count > 0:
    h, w = gray.shape[:2]
    ret, cameraMatrix, distCoeffs, rvecs, tvecs = cv2.calibrateCamera(
        objpoints, imgpoints, (w, h), None, None
    )

    # Compute reprojection error
    total_error = 0
    for i in range(len(objpoints)):
        imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], cameraMatrix, distCoeffs)
        error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
        total_error += error
    mean_error = total_error / len(objpoints)

    print("\n=== Calibration Results ===")
    print("Camera Matrix:\n", cameraMatrix)
    print("Distortion Coeffs:\n", distCoeffs.ravel())
    print(f"Mean Reprojection Error: {mean_error:.4f} pixels")

    np.savez("calibration_data.npz",
             cameraMatrix=cameraMatrix,
             distCoeffs=distCoeffs,
             rvecs=rvecs,
             tvecs=tvecs,
             error=mean_error)
    print("💾 Calibration data saved to calibration_data.npz")
else:
    print("⚠️ No calibration images captured.")
