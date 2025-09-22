ArUco Marker Generator
======================

This Python script generates custom ArUco markers using OpenCV’s cv2.aruco module.
ArUco markers are widely used in robotics, computer vision, and augmented reality for pose estimation and object tracking.

Features
--------
- Generate any ArUco marker from the built-in OpenCV dictionaries.
- Specify marker size (in pixels) and save it as an image file.
- Display the generated marker on screen.

Requirements
------------
- Python 3.7 or later
- OpenCV (with the aruco module included)

Install OpenCV with:
    pip install opencv-contrib-python

Usage
-----
Run the script from the command line:

    python generate_aruco.py --dict <dictionary_name> --id <marker_id> --size <pixels> --out <filename.png>

Arguments:
----------
--dict   (default DICT_4X4_50)  ArUco dictionary name (e.g. DICT_4X4_50, DICT_5X5_100, DICT_6X6_250, DICT_7X7_1000)
--id     (default 0)            Marker ID within the selected dictionary
--size   (default 300)          Size of the marker image in pixels (square)
--out    (default aruco_marker.png) Output filename to save the marker

Example:
--------
Generate a 300x300 pixel marker with ID 23 from the DICT_4X4_50 dictionary:

    python generate_aruco.py --dict DICT_4X4_50 --id 23 --size 300 --out marker23.png

This will:
- Save the marker as marker23.png
- Open a window displaying the marker (press any key to close).

Supported Dictionaries:
-----------------------
- DICT_4X4_50
- DICT_4X4_100
- DICT_4X4_250
- DICT_4X4_1000
- DICT_5X5_50 … DICT_7X7_1000
- DICT_ARUCO_ORIGINAL

Notes:
------
- If an unknown dictionary name is entered, the script will list all available options.
- Make sure you have the opencv-contrib-python package installed (the standard opencv-python package does not include aruco).
