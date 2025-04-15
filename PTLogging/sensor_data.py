#!/usr/bin/env python3
import socket
import time
import board
import adafruit_dht
import RPi.GPIO as GPIO
import sys

# GPIO pin definitions
RED_LED = 25
GREEN_LED = 26

# Initialize GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(RED_LED, GPIO.OUT)
GPIO.setup(GREEN_LED, GPIO.OUT)

# Turn ON red LED to indicate the program is running
GPIO.output(RED_LED, GPIO.HIGH)
GPIO.output(GREEN_LED, GPIO.LOW)

# Initialize DHT22 sensor (on GPIO 2, physical pin 3)
sensor = adafruit_dht.DHT22(board.D2)

# TCP server configuration
SERVER_IP = '0.0.0.0'
SERVER_PORT = 5001

# Create TCP socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((SERVER_IP, SERVER_PORT))
server_socket.listen(2)

print(f"Server started at {SERVER_IP}:{SERVER_PORT}")

try:
    while True:
        print("Waiting for client connection...")
        connection, client_address = server_socket.accept()
        print(f"Connection established with: {client_address}")

        try:
            while True:
                try:
                    # Read sensor data
                    temperature_c = sensor.temperature
                    humidity = sensor.humidity

                    if temperature_c is None or humidity is None:
                        print("Invalid sensor reading. Retrying...")
                        time.sleep(2)
                        continue

                except RuntimeError as error:
                    print(f"Sensor error: {error}")
                    time.sleep(2)
                    continue

                except Exception as error:
                    print(f"Reinitializing sensor due to unexpected error: {error}")
                    sensor = adafruit_dht.DHT22(board.D2)
                    time.sleep(2)
                    continue

                # Receive request from client
                try:
                    data = connection.recv(1024).decode("utf-8").strip().lower()
                    if not data:
                        print("Client disconnected.")
                        break

                    print("Received from client:", data)

                    # Turn ON green LED to indicate data request
                    GPIO.output(GREEN_LED, GPIO.HIGH)

                    # Send sensor data back
                    response = f"temperature: {temperature_c:.1f}°C, humidity: {humidity:.1f}%"
                    connection.sendall(response.encode("utf-8"))

                    print("Sent to client:", response)

                    # Turn OFF green LED after response
                    GPIO.output(GREEN_LED, GPIO.LOW)

                except Exception as e:
                    print(f"Error communicating with client: {e}")
                    break

                time.sleep(2)

        finally:
            print("Closing client connection...")
            connection.close()

except KeyboardInterrupt:
    print("Program interrupted by user.")

except Exception as e:
    print(f"Fatal error: {e}")

finally:
    print("Shutting down server...")
    server_socket.close()
    GPIO.output(RED_LED, GPIO.LOW)  # Turn OFF red LED on exit
    GPIO.output(GREEN_LED, GPIO.LOW)
    GPIO.cleanup()
    print("GPIO cleaned up. Program terminated.")
