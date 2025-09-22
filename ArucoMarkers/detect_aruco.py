import cv2
import numpy as np
import argparse

# === ArUco setup ===
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
aruco_params = cv2.aruco.DetectorParameters()
detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

# === Real marker size in mm ===
MARKER_SIZE_MM = 50  # Set to your actual ArUco marker size

def detect_and_draw(frame):
    """Detect ArUco markers and draw distances to center and frame edges (px + mm) with labels."""
    h, w = frame.shape[:2]
    frame_center = (w // 2, h // 2)

    # Draw frame center
    cv2.circle(frame, frame_center, 6, (255, 0, 0), -1)
    cv2.putText(frame, "Center", (frame_center[0] + 10, frame_center[1]),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    corners, ids, _ = detector.detectMarkers(frame)

    if ids is not None:
        cv2.aruco.drawDetectedMarkers(frame, corners, ids)

        # Estimate pixel/mm scale using the first marker
        c0 = corners[0].reshape((4,2))
        width_px = np.linalg.norm(c0[0] - c0[1])
        px_per_mm = width_px / MARKER_SIZE_MM

        for c, i in zip(corners, ids.flatten()):
            c = c.reshape((4, 2))
            cx, cy = int(c[:, 0].mean()), int(c[:, 1].mean())

            # Draw marker center
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

            # Distance from frame center
            dx, dy = cx - frame_center[0], cy - frame_center[1]
            distance_center_px = np.sqrt(dx**2 + dy**2)
            distance_center_mm = distance_center_px / px_per_mm

            # Distances to edges
            dist_left_px, dist_right_px = cx, w - cx
            dist_top_px, dist_bottom_px = cy, h - cy
            dist_left_mm = dist_left_px / px_per_mm
            dist_right_mm = dist_right_px / px_per_mm
            dist_top_mm = dist_top_px / px_per_mm
            dist_bottom_mm = dist_bottom_px / px_per_mm

            # Draw lines to edges with labels
            cv2.line(frame, (cx, cy), (0, cy), (255, 255, 0), 1)
            cv2.putText(frame, f"{dist_left_mm:.1f}mm", (cx//2, cy-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
            cv2.line(frame, (cx, cy), (w, cy), (255, 255, 0), 1)
            cv2.putText(frame, f"{dist_right_mm:.1f}mm", ((cx+w)//2, cy-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
            cv2.line(frame, (cx, cy), (cx, 0), (255, 255, 0), 1)
            cv2.putText(frame, f"{dist_top_mm:.1f}mm", (cx+5, cy//2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
            cv2.line(frame, (cx, cy), (cx, h), (255, 255, 0), 1)
            cv2.putText(frame, f"{dist_bottom_mm:.1f}mm", (cx+5, (cy+h)//2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

            # Line to frame center
            cv2.line(frame, frame_center, (cx, cy), (0, 255, 255), 2)
            cv2.putText(frame, f"{distance_center_mm:.1f}mm", ((cx + frame_center[0])//2 + 5,
                        (cy + frame_center[1])//2 + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

            # Display marker ID
            cv2.putText(frame, f"ID:{i}", (cx + 10, cy - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Print to console
            print(f"Marker ID {i}: Center={distance_center_mm:.1f}mm, "
                  f"L={dist_left_mm:.1f} R={dist_right_mm:.1f} "
                  f"T={dist_top_mm:.1f} B={dist_bottom_mm:.1f}")

    return frame


def detect_from_image(path):
    img = cv2.imread(path)
    if img is None:
        print(f"❌ Could not read image: {path}")
        return
    result = detect_and_draw(img)
    cv2.imshow("ArUco Detection", result)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ArUco marker detection")
    parser.add_argument("--image", type=str, required=True, help="Path to an image with ArUco markers")
    args = parser.parse_args()

    detect_from_image(args.image)
