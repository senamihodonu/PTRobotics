import cv2
import numpy as np

def capture_image():
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return None
    
    print("Press 'C' to capture image")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture image")
            break
        
        cv2.imshow("Live Feed - Press 'C' to Capture", frame)
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('c'):
            image_path = "captured_image.jpg"
            cv2.imwrite(image_path, frame)
            print(f"Image saved as {image_path}")
            cap.release()
            cv2.destroyAllWindows()
            return image_path
    
    cap.release()
    cv2.destroyAllWindows()
    return None

def process_image(image_path):
    # Load the image
    image = cv2.imread(image_path)
    if image is None:
        print("Error: Could not load image.")
        return
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply adaptive thresholding for better edge detection
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter out small contours (noise)
    contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 500]
    
    if not contours:
        print("No significant contours found.")
        return image
    
    # Assume the largest contour is the object
    largest_contour = max(contours, key=cv2.contourArea)
    
    # Get bounding box around the object
    x, y, w, h = cv2.boundingRect(largest_contour)

    reference_mm = 76

    # Convert pixels to mm using width as reference
    # pixels_per_mm = w / reference_mm

    # print(pixels_per_mm)
    
    # Reference object width in mm (Adjust as needed)
    pixels_per_mm = 5.7368421052631575  # Example calibration value
    
    # Calculate real dimensions
    real_width_mm = w / pixels_per_mm
    real_height_mm = h / pixels_per_mm
    
    print(f"Width: {real_width_mm:.2f} mm, Height: {real_height_mm:.2f} mm")
    
    # Draw the bounding box and display dimensions
    cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 3)
    cv2.putText(image, f"Width: {real_width_mm:.2f} mm", (x, y - 20), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    cv2.putText(image, f"Height: {real_height_mm:.2f} mm", (x, y - 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    
    # Save and show the processed image
    cv2.imwrite("processed_image.jpg", image)
    cv2.imshow("Measured Object", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

# Capture image first
image_path = capture_image()
if image_path:
    process_image(image_path)
