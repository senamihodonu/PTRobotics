import socket
import sys
import time


def get_humidity(server_ip='172.29.187.113', server_port=5001):
    temperature = None
    humidity = None
    # Create a TCP/IP socket
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect the socket to the server
    client.connect((server_ip, server_port))

    print("Connection established with:", client)

    try:
        # Send data to the server
        message = "go"
        client.sendall(message.encode())
        # Recieve data from server
        response = client.recv(1024).decode("utf-8")

        print("Received from server:", response)

        # Parse response if it's in the expected format
        if "temperature" in response and "humidity" in response:
            try:
                parts = response.split(", ")
                temperature = float(parts[0].split(": ")[1].replace("°C", ""))
                humidity = float(parts[1].split(": ")[1].replace("%", ""))
            except (IndexError, ValueError) as e:
                print("Error parsing sensor data:", e)
        elif response == "error":
            print("Error reading sensor")

    finally:
        # Clean up the connection
        client.close()

    return temperature, humidity
    

if __name__ == "__main__":

    while True:
        temp, hum = get_humidity()
        print(f"Sensor Temperature: {temp}°C")
        print(f"Sensor Humidity: {hum}%")
