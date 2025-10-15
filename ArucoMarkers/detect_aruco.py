import os
import sys
import time
import cv2
import numpy as np
import argparse

# --- Ensure UTF-8 output for Windows terminals ---
sys.stdout.reconfigure(encoding='utf-8')

# === ArUco setup ===
ARUCO_DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
ARUCO_PARAMS = cv2.aruco.DetectorParameters()
DETECTOR = cv2.aruco.ArucoDetector(ARUCO_DICT, ARUCO_PARAMS)

# === Marker properties ===
MARKER_SIZE_MM = 50  # Actual ArUco marker size in millimeters


def detect_and_draw(frame):
    """
    Detect ArUco markers in the frame, draw annotations, and return distance data.
    """
    h, w = frame.shape[:2]
    frame_center = (w // 2, h // 2)

    # Draw frame center point
    cv2.circle(frame, frame_center, 6, (255, 0, 0), -1)
    cv2.putText(frame, "Center", (frame_center[0] + 10, frame_center[1]),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    corners, ids, _ = DETECTOR.detectMarkers(frame)
    distances_dict = {}

    if ids is not None:
        cv2.aruco.drawDetectedMarkers(frame, corners, ids)

        # Estimate pixel-to-mm scale from the first marker
        first_marker = corners[0].reshape((4, 2))
        width_px = np.linalg.norm(first_marker[0] - first_marker[1])
        px_per_mm = width_px / MARKER_SIZE_MM

        for c, marker_id in zip(corners, ids.flatten()):
            c = c.reshape((4, 2))
            cx, cy = int(c[:, 0].mean()), int(c[:, 1].mean())

            # Draw marker center
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

            # Distances (px and mm)
            dx, dy = cx - frame_center[0], cy - frame_center[1]
            dist_center_px = np.hypot(dx, dy)

            dist_center_mm = dist_center_px / px_per_mm
            dist_left_mm = cx / px_per_mm
            dist_right_mm = (w - cx) / px_per_mm
            dist_top_mm = cy / px_per_mm
            dist_bottom_mm = (h - cy) / px_per_mm

            # Draw helper lines + text
            cv2.line(frame, (cx, cy), (0, cy), (255, 255, 0), 1)
            cv2.putText(frame, f"{dist_left_mm:.1f}mm", (cx // 2, cy - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

            cv2.line(frame, (cx, cy), (w, cy), (255, 255, 0), 1)
            cv2.putText(frame, f"{dist_right_mm:.1f}mm", ((cx + w) // 2, cy - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

            cv2.line(frame, (cx, cy), (cx, 0), (255, 255, 0), 1)
            cv2.putText(frame, f"{dist_top_mm:.1f}mm", (cx + 5, cy // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

            cv2.line(frame, (cx, cy), (cx, h), (255, 255, 0), 1)
            cv2.putText(frame, f"{dist_bottom_mm:.1f}mm", (cx + 5, (cy + h) // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

            # Draw center line
            cv2.line(frame, frame_center, (cx, cy), (0, 255, 255), 2)
            cv2.putText(frame, f"{dist_center_mm:.1f}mm",
                        ((cx + frame_center[0]) // 2 + 5, (cy + frame_center[1]) // 2 + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

            # Label marker
            cv2.putText(frame, f"ID:{marker_id}", (cx + 10, cy - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Store data
            distances_dict[int(marker_id)] = {
                "center_mm": round(dist_center_mm, 2),
                "left_mm": round(dist_left_mm, 2),
                "right_mm": round(dist_right_mm, 2),
                "top_mm": round(dist_top_mm, 2),
                "bottom_mm": round(dist_bottom_mm, 2),
                "center_px": round(dist_center_px, 2),
            }

    return frame, distances_dict


def detect_from_image(path, save_marked=True, return_marked=False, show=False):
    """
    Detect ArUco markers in an image, annotate results, and return measurements.
    """
    abs_path = os.path.abspath(path)
    print(f"🔍 Reading image: {abs_path}")

    img = cv2.imread(abs_path)
    if img is None:
        print(f"[ERROR] Could not read image: {abs_path}")
        return ({}, None) if return_marked else {}

    annotated, distances = detect_and_draw(img)

    print("\n📏 Measured distances (mm):")
    for marker_id, data in distances.items():
        print(f"Marker ID: {marker_id}")
        for key, value in data.items():
            print(f"  {key:10}: {float(value):.2f} mm")

    # Save annotated image
    if save_marked:
        folder, filename = os.path.split(abs_path)
        name, ext = os.path.splitext(filename)

        # Add timestamp to filename
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        marked_path = os.path.join(folder, f"{name}_marked_{timestamp}{ext}")

        cv2.imwrite(marked_path, annotated)
        print(f"\n🖍️ Marked image saved to: {marked_path}")

    # Display window if requested
    if show:
        cv2.imshow("ArUco Detection", annotated)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return (distances, annotated) if return_marked else distances


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Detect ArUco markers and measure distances (in mm)."
    )
    parser.add_argument("--image", required=True, help="Path to input image file.")
    parser.add_argument("--show", action="store_true", help="Display image window.")
    parser.add_argument("--nosave", action="store_true", help="Do not save marked image.")
    parser.add_argument("--returnimg", action="store_true", help="Return annotated image array.")
    args = parser.parse_args()

    detect_from_image(
        path=args.image,
        save_marked=not args.nosave,
        return_marked=args.returnimg,
        show=args.show
    )


if __name__ == "__main__":
    main()
