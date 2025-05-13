# PLC Motion Control Module

This Python module provides a class-based interface for communicating with a PLC using the Modbus TCP protocol via the pymodbus library. It is designed to control stepper motor movement and read sensor data in a system with Y and Z motion axes.

## Features

- Connect to a PLC over Modbus TCP

- Read/write coils and registers

- Calculate and send motion parameters for Y and Z axes

- Convert between units (mm, inches, feet)

- Estimate travel time and control motion based on distance and speed

- Read distance sensor data

- Gracefully handle connection setup and teardown

## Requirements
  - Python 3.7+
  - `pymodbus` library (Install with `pip install pymodbus`)

## Installation

Step-by-step instructions on how to get your project up and running.

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/projectname.git

   git clone https://github.com/UofI-CDACS/fanuc_ethernet_ip_drivers.git
