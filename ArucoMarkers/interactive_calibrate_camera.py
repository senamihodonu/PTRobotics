import cv2
import numpy as np
import os
import glob
import time

# === Calibration pattern settings ===
CHECKERBOARD = (9, 6)  # number of inner corners (width, height)
SQUARE_SIZE_MM = 25.0  # real-world square size in mm

# === Prepare object points for one checkerboard ===
objp = np.zeros((CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1, 2)
objp *= SQUARE_SIZE_MM

# === Ensure folder for calibration images exists ===
SAVE_DIR = "calib_images"
os.makedirs(SAVE_DIR, exist_ok=True)

# === Start webcam ===
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Could not open webcam.")
    exit()

print("🎥 Webcam opened. Press 'C' to capture checkerboard images.")
print("💾 Images will be saved to:", SAVE_DIR)
print("📸 Press 'S' to start calibration when done.")
print("❌ Press 'Q' to quit without calibrating.\n")

capture_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("⚠️ Frame not captured.")
        break

    # Display the frame
    display = frame.copy()
    cv2.putText(display, f"Captured: {capture_count} | Press C=Capture, S=Calibrate, Q=Quit",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.imshow("Calibration Capture", display)

    key = cv2.waitKey(1) & 0xFF

    # --- Capture image ---
    if key == ord('c'):
        img_name = os.path.join(SAVE_DIR, f"calib_{time.strftime('%Y%m%d_%H%M%S')}.jpg")
        cv2.imwrite(img_name, frame)
        capture_count += 1
        print(f"✅ Saved {img_name}")

    # --- Start calibration ---
    elif key == ord('s'):
        print("\n⚙️ Starting calibration using saved images...\n")
        cap.release()
        cv2.destroyAllWindows()
        break

    # --- Quit ---
    elif key == ord('q'):
        print("👋 Exiting without calibration.")
        cap.release()
        cv2.destroyAllWindows()
        exit()

# === Calibration process ===
images = glob.glob(os.path.join(SAVE_DIR, '*.jpg'))
if len(images) == 0:
    print("❌ No images found for calibration.")
    exit()

objpoints = []  # 3D points in real world space
imgpoints = []  # 2D points in image plane

for fname in images:
    img = cv2.imread(fname)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Find checkerboard corners
    ret, corners = cv2.findChessboardCorners(gray, CHECKERBOARD, None)
    if ret:
        objpoints.append(objp)
        corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1),
                                    (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001))
        imgpoints.append(corners2)

        cv2.drawChessboardCorners(img, CHECKERBOARD, corners2, ret)
        cv2.imshow("Detected Corners", img)
        cv2.waitKey(150)

cv2.destroyAllWindows()

if len(objpoints) < 3:
    print("⚠️ Not enough valid checkerboard images for calibration (need ≥ 3).")
    exit()

# === Run calibration ===
ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
    objpoints, imgpoints, gray.shape[::-1], None, None
)

print("\n📷 Camera matrix:\n", mtx)
print("\n🎯 Distortion coefficients:\n", dist.ravel())

# === Save calibration results ===
np.save('camera_matrix.npy', mtx)
np.save('dist_coeffs.npy', dist)

print("\n✅ Calibration complete!")
print("💾 Saved: camera_matrix.npy, dist_coeffs.npy")
