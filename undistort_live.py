import cv2
import numpy as np
import os
import sys

# === Handle command line argument ===
if len(sys.argv) < 2:
    print("⚠️ Usage: python undistort_live.py <calibration_file.npz>")
    sys.exit(1)

calibration_file = sys.argv[1]

# === Load calibration data ===
if not os.path.exists(calibration_file):
    raise FileNotFoundError(f"❌ Calibration file '{calibration_file}' not found!")

data = np.load(calibration_file)
cameraMatrix = data["cameraMatrix"]
distCoeffs = data["distCoeffs"]
mean_error = float(data["error"]) if "error" in data else None

print(f"Loaded calibration data from {calibration_file}")
if mean_error is not None:
    print(f"Mean Reprojection Error: {mean_error:.4f} pixels")
    if mean_error > 0.5:
        print("⚠️ Warning: Calibration error is high. Capture more images for better accuracy.")

# === Pick camera index based on calibration file ===
if "2mm" in calibration_file:
    cam_index = 1
elif "5mm" in calibration_file:
    cam_index = 0
else:
    cam_index = 0  # fallback if name doesn't match

print(f"✅ Using camera index {cam_index}")
cap = cv2.VideoCapture(cam_index)

if not cap.isOpened():
    raise RuntimeError(f"❌ Could not open camera index {cam_index}")

# === Live undistortion ===
while True:
    ret, frame = cap.read()
    if not ret:
        print("⚠️ Failed to grab frame.")
        break

    h, w = frame.shape[:2]
    newCameraMatrix, roi = cv2.getOptimalNewCameraMatrix(
        cameraMatrix, distCoeffs, (w, h), 1, (w, h)
    )
    undistorted = cv2.undistort(frame, cameraMatrix, distCoeffs, None, newCameraMatrix)

    # Show side-by-side comparison
    combined = cv2.hconcat([frame, undistorted])
    cv2.imshow("Original (Left) vs Undistorted (Right)", combined)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
