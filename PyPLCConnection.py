import time
from pymodbus.client import ModbusTcpClient 
import sys
import math

LEAD_Y_SCREW = 2.54 #mm
LEAD_Z_SCREW = 5 #mm
DIP_SWITCH_SETTING_Y = 20000 #pulse per revolution
DIP_SWITCH_SETTING_Z = 20000 #pulse per revolution
GREEN = 6
Y_LEFT_MOTION = 4
Y_RIGHT_MOTION = 3
Z_UP_MOTION = 1
Z_DOWN_MOTION = 2
DISTANCE_SENSOR_IN = 5
DISTANCE_DATA_ADDRESS = 6
PPS_Y_ADDRESS = 10
PPS_Z_ADDRESS = 12
PLC_IP = "192.168.1.25"
ROBOT_IP = '192.168.1.101' #Woody
MD_EXTRUDER_ADDRESS = 13
MD_PELLET_UFRAME = 1
MD_PELLET_UTOOL = 1
WOOD_NOZZLE_UFRAME = 2
WOOD_NOZZLE_UTOOL = 2
DISABLE_PIN = 16


print("---------------------------------------------")
class PyPLCConnection:

    def __init__(self, ip_address, port=502):
        self.ip_address = ip_address
        self.port = port
        self.client = self.connect_to_plc()

    
    def connect_to_plc(self):
        try:
            # Create a Modbus TCP client
            self.client = ModbusTcpClient(self.ip_address, port=self.port)
            if self.client.connect():
                print(f"Connected to PLC at Address: {self.ip_address}:{self.port}")
                return self.client
            else:
                print(f"Failed to connect to PLC at Address: {self.ip_address}:{self.port}")
                self.client = None  # Ensure the client is None on failure
        except Exception as e:
            print(f"Error while connecting to PLC: {e}")
            self.client = None


    def write_modbus_coils(self, coil_address, value):
        """Write a Modbus coil and ALWAYS close connection."""
        
        try:
            # ---- ALWAYS OPEN ----
            self.connect_to_plc()
            print(f"Writing {value} to address {coil_address}")

            # Modbus offset (Click PLC starts at 1, pymodbus starts at 0)
            coil_address -= 1

            # Perform write
            result = self.client.write_coil(coil_address, value)

            return result

        except Exception as e:
            print("Error writing coil:", e)
            raise

        finally:
            # ---- ALWAYS CLOSE ----
            self.close_connection()


    def read_modbus_coils(self, coil_address, number_of_coils=1):
        """Read Modbus coils safely with auto-close, even on error."""
        
        try:
            # ---- ALWAYS OPEN ----
            self.connect_to_plc()

            # Adjust for Click PLC addressing (1-based → 0-based)
            coil_address -= 1

            # Read coils
            response = self.client.read_coils(coil_address, number_of_coils)

            # Handle pymodbus response errors gracefully
            if response.isError():
                raise Exception(f"Modbus read error: {response}")

            # Extract only the number of bits requested
            result_list = response.bits[:number_of_coils]

            print(result_list)
            return result_list

        except Exception as e:
            print(f"Error reading Modbus coils: {e}")
            raise  # rethrow so caller knows something went wrong

        finally:
            # ---- ALWAYS CLOSE ----
            self.close_connection()

    
    def read_single_register(self, register_address):
        """Read one holding register safely with auto-close."""

        try:
            # ---- ALWAYS OPEN ----
            self.connect_to_plc()

            # Adjust for Modbus (1-based Click → 0-based pymodbus)
            address = register_address - 1

            # Read the register
            response = self.client.read_holding_registers(address, 1)

            # Check for Modbus-level errors
            if response.isError():
                raise Exception(f"Modbus read error: {response}")

            # Extract register value
            value = response.registers[0]

            print(f"register {register_address} is {value}")
            return value

        except Exception as e:
            print(f"Error reading register {register_address}: {e}")
            raise

        finally:
            # ---- ALWAYS CLOSE ----
            self.close_connection()

   
    def write_single_register(self, register_address, value):
        """Write a single holding register safely with auto-close."""
        try:
            self.connect_to_plc()
            print(f"Writing {value} to register {register_address}")

            address = register_address - 1
            response = self.client.write_register(address, value)

            if response.isError():
                raise Exception(f"Modbus write error: {response}")

        except Exception as e:
            print(f"Error writing register {register_address}: {e}")
            raise

        finally:
            self.close_connection()


    def close_connection(self):
        """Safely close Modbus connection."""
        try:
            if self.client:
                print("Closing Connection")
                self.client.close()
        except:
            print("Warning: PLC connection already closed or failed to close.")


    def distance(self, distance, unit = "mm"):
        if unit.lower() == "in":
            return distance*25.4
        elif unit.lower() == "ft":
            return distance*304.8
        else:
            return distance
        
    def read_current_distance(self):
        # Convert degrees to radians before calculating cosine
        angle_degrees = 21.65
        angle_radians_from_degrees = math.radians(angle_degrees)
        angle_distance = self.read_single_register(DISTANCE_DATA_ADDRESS)
        vertical_distance = angle_distance*math.cos(angle_radians_from_degrees)
        return math.ceil(vertical_distance)

    def calculate_pulse_per_second(self, speed_mm_min, steps_per_rev, lead_mm_rev, axis):
        axis = axis.lower()

        if axis == "z":
            return self.read_single_register(PPS_Z_ADDRESS)
        elif axis == "y":
            return self.read_single_register(PPS_Y_ADDRESS)
        else:
            raise ValueError(f"Unsupported axis '{axis}'")


    def reset_coils(self):
        coil_addresses = [
            GREEN,
            Z_DOWN_MOTION,
            Z_UP_MOTION,
            Y_RIGHT_MOTION,
            Y_LEFT_MOTION,
            MD_EXTRUDER_ADDRESS
        ]

        print("Resetting all coils to False...")
        for coil in coil_addresses:
            self.write_modbus_coils(coil, False)

        print("All coils reset.")



    def md_extruder_switch(self, status):
        """Turn pellet extruder ON or OFF."""
        s = str(status).strip().lower()

        if s in ("on", "1"):
            value = True
        elif s in ("off", "0"):
            value = False
        else:
            print(f"Unsupported extruder value '{status}'. Use ON/OFF.")
            return

        self.write_modbus_coils(MD_EXTRUDER_ADDRESS, value)
        print(f"Extruder turned {status.upper()}")



    def disable_motor(self, value):
        self.write_modbus_coils(DISABLE_PIN, value)
        state = "disabled" if value else "enabled"
        print(f"Motors are {state} (value = {value})")



    def travel(self, coil_address, distance, unit, axis):
        """
        Move stepper motor a given distance using Modbus coil control.
        Pulse rate is read from PLC.
        """

        axis = axis.lower()

        # === Read pulse rate (auto-close inside read_single_register) ===
        if axis == "z":
            pulse_rate = self.read_single_register(PPS_Z_ADDRESS)
            pulses_per_rev = DIP_SWITCH_SETTING_Z
            lead_mm = LEAD_Z_SCREW
            gear_ratio = 20
        elif axis == "y":
            pulse_rate = self.read_single_register(PPS_Y_ADDRESS)
            pulses_per_rev = DIP_SWITCH_SETTING_Y
            lead_mm = LEAD_Y_SCREW
            gear_ratio = 1
        else:
            print(f"Error: Unsupported axis '{axis}'")
            return 0

        # === Validate ===
        if distance <= 0:
            print("Error: Distance must be positive.")
            return 0

        # === Unit conversion ===
        unit = unit.lower()
        if unit in ("inches", "in"):
            distance *= 25.4
        elif unit in ("feet", "ft"):
            distance *= 304.8
        elif unit != "mm":
            print(f"Error: Unsupported unit '{unit}'")
            return 0

        # === Calculate motion parameters ===
        pulses_per_screw_rev = pulses_per_rev * gear_ratio
        pulses_per_mm = pulses_per_screw_rev / lead_mm
        speed_mm_s = pulse_rate / pulses_per_mm
        travel_time = distance / speed_mm_s

        print(
            f"Axis: {axis.upper()}, Distance: {distance:.2f} mm, "
            f"Speed: {speed_mm_s:.3f} mm/s, Travel time: {travel_time:.2f} s"
        )

        # === Turn motor ON ===
        self.write_modbus_coils(coil_address, True)

        # Countdown
        remaining = round(travel_time)
        while remaining > 0:
            sys.stdout.write(f"\rTime remaining: {remaining} s")
            sys.stdout.flush()
            time.sleep(1)
            remaining -= 1

        sys.stdout.write("\rTime remaining: 0 s\n")

        # === Turn motor OFF ===
        self.write_modbus_coils(coil_address, False)

        time.sleep(2)
        return travel_time






if __name__ == "__main__":
    plc = PyPLCConnection(PLC_IP)
    # plc.read_single_register(DISTANCE_DATA_ADDRESS)
    # plc.read_single_register(DISTANCE_DATA_ADDRESS)
    # plc.write_modbus_coils(GREEN, False)
    # plc.write_modbus_coils(Z_DOWN_MOTION, True)
    # plc.write_modbus_coils(Z_UP_MOTION, False)
    # plc.write_modbus_coils(Y_RIGHT_MOTION, False)
    # plc.write_modbus_coils(Y_LEFT_MOTION, False)
    # plc.read_single_register(7)
    plc.md_extruder_switch("off")
    # # plc.calculate_pulse_per_second("z")
    # # plc.travel(Z_UP_MOTION, 1, "in", pps=60000, lead_mm=5, pulses_per_rev=20000)


    # plc.travel(Z_DOWN_MOTION, 4,"mm","z")
    print(plc.read_current_distance())

    plc.disable_motor(False)

    # time.sleep()



    




