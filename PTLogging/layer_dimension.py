import cv2
import numpy as np
import os
import csv
from datetime import datetime

# Constants
IMAGE_DIR = "MVImages"
CSV_FILE = os.path.join(IMAGE_DIR, "measurement_log.csv")
PIXELS_PER_MM = 15# Calibration factor (can be improved with known object)

# Ensure image directory exists
os.makedirs(IMAGE_DIR, exist_ok=True)

# Create CSV file if not exists
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "Captured Image", "Processed Image", "Width (mm)", "Height (mm)"])

def get_timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def log_measurements_to_csv(timestamp, captured_name, processed_name, width_mm, height_mm):
    with open(CSV_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, captured_name, processed_name, f"{width_mm:.2f}", f"{height_mm:.2f}"])

    print(f"\n--- Measurement Logged ---\nTimestamp        : {timestamp}")
    print(f"Captured Image   : {captured_name}")
    print(f"Processed Image  : {processed_name}")
    print(f"Width (mm)       : {width_mm:.2f}")
    print(f"Height (mm)      : {height_mm:.2f}\n----------------------------")

def preprocess_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    edges = cv2.Canny(blurred, 50, 150)
    kernel = np.ones((3, 3), np.uint8)
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
    return closed

def measure_object(image):
    processed = preprocess_image(image)
    contours, _ = cv2.findContours(processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 500]
    if not contours:
        print("No significant contours found.")
        return None, None, None

    largest = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest)
    return w / PIXELS_PER_MM, h / PIXELS_PER_MM, (x, y, w, h)

def annotate_and_save(image, timestamp, bbox, width_mm, height_mm):
    x, y, w, h = bbox
    cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 3)
    cv2.putText(image, f"Width: {width_mm:.2f} mm", (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.putText(image, f"Height: {height_mm:.2f} mm", (x, y - 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    processed_name = f"processed_image_{timestamp}.jpg"
    output_path = os.path.join(IMAGE_DIR, processed_name)
    cv2.imwrite(output_path, image)

    return processed_name

def process_image(image, image_name, timestamp):
    width_mm, height_mm, bbox = measure_object(image)
    if width_mm is None:
        print("Could not measure object.")
        return None, None

    processed_name = annotate_and_save(image, timestamp, bbox, width_mm, height_mm)
    log_measurements_to_csv(timestamp, image_name, processed_name, width_mm, height_mm)
    cv2.imshow("Processed Image", image)
    cv2.waitKey(500)
    return width_mm, height_mm

def main():
    cap = cv2.VideoCapture(2)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    print("Press 'C' to capture, 'Q' to quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to read from camera")
            break

        cv2.imshow("Live Feed - Press 'C' to Capture, 'Q' to Quit", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('c'):
            timestamp = get_timestamp()
            image_name = f"captured_image_{timestamp}.jpg"
            image_path = os.path.join(IMAGE_DIR, image_name)
            cv2.imwrite(image_path, frame)
            print(f"Image saved: {image_path}")

            image_copy = frame.copy()
            width_mm, height_mm = process_image(image_copy, image_name, timestamp)
            if width_mm and height_mm:
                print(f"Measured Width: {width_mm:.2f} mm, Height: {height_mm:.2f} mm")

        elif key == ord('q'):
            print("Quitting.")
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
