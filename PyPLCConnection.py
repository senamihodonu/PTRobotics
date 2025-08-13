import time
from pymodbus.client import ModbusTcpClient 

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
PPS_Z_ADDRESS = 7
PLC_IP = "192.168.1.25"
ROBOT_IP = '192.168.1.101' #Woody

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
        self.connect_to_plc()
        print("Writing " + str(value) + " to address ", str(coil_address))

        result = None
        # Take care of the offset between pymodbus and the click plc
        coil_address = coil_address - 1

        # pymodbus built in write coil function
        result = self.client.write_coil(coil_address, value)
        self.close_connection()

        return result


    def read_modbus_coils(self, coil_address, number_of_coils=1):
        self.connect_to_plc()
        # Predefining a empty list to store our result
        result_list = []

        # Take care of the offset between pymodbus and the click plc
        coil_address = coil_address - 1

        # Read the modbus address values form the click PLC
        result = self.client.read_coils(coil_address)

        # print("Response from PLC with pymodbus library", result.bits)

        # storing our values form the plc in a list of length
        # 0 to the number of coils we want to read
        result_list = result.bits[0:number_of_coils]
        self.close_connection()
        print(result_list)


        # print("Filtered result of only necessary values", result_list)
        print("register " + str(coil_address+1) + " is " + str(result_list[0]))
        return result_list[0]
    
    def read_single_register(self, register_address):
        self.connect_to_plc()
        result = self.client.read_holding_registers(register_address-1).registers
        print("register " + str(register_address) + " is " + str(result[0]))
        self.close_connection()
        return result[0]
    
    def write_single_register(self, register_address, value):
        print("writing " + str(value) + " to register " + str(register_address))
        self.client.write_register(register_address-1, value)

    def close_connection(self):
        print("Closing Connection")
        self.client.close()

    def distance(self, distance, unit = "mm"):
        if unit.lower() == "in":
            return distance*25.4
        elif unit.lower() == "ft":
            return distance*304.8
        else:
            return distance

    def calculate_pulse_per_second(self,speed_mm_min, steps_per_rev, lead_mm_rev, axis):
        """
        Calculate pulses per second (PPS) for the stepper motor.
        
        :param speed_mm_per_min: Speed of the motor in mm/min.
        :param lead_mm: Lead of the lead screw in mm.
        :param dip_switch_setting: Dip switch setting (multiplier).
        :return: Pulses per second (PPS).
        """
        if axis.lower() == "z":
            pulses_per_second = self.read_single_register(PPS_Z_ADDRESS)
        elif axis.lower() == "y":
            pulses_per_second = self.read_single_register(PPS_Y_ADDRESS)
        # if axis.lower() == "z":
        #     gear_ratio = 20
        # else:
        #     gear_ratio = 1
        # # Convert speed from mm/min to mm/sec
        # speed_mm_sec = speed_mm_min / 60

        # # Calculate pulses per second (PPS)
        # pulses_per_second = (steps_per_rev * gear_ratio/ lead_mm_rev) * speed_mm_sec
        # print(pulses_per_second)
        # if axis.lower() == "z":
        #     self.write_single_register(3,0)
        #     time.sleep(0.2)
        #     self.write_single_register(3,int(pulses_per_second))
        # else:
        #     self.write_single_register(1,0)
        #     time.sleep(0.2)
        #     self.write_single_register(1,int(pulses_per_second))
        return pulses_per_second

    def travel(self, coil_address, distance, unit, speed_mm_per_sec):
        """
        Calculate the time to travel a given distance using the speed of the stepper motor.

        :param coil_address: Modbus coil address to control the motor
        :param distance: Distance to travel (in unit specified)
        :param unit: Unit of the distance ('mm', 'inches', or 'feet')
        :param speed_mm_per_sec: Speed of the motor in mm/sec
        :return: Time to travel the given distance in seconds
        """
        if distance <= 0 or speed_mm_per_sec <= 0:
            print("Distance and speed must be positive values.")
            return 0

        # Convert distance to mm if needed
        unit = unit.lower()
        if unit in ("inches", "in"):
            print(f"Traveling {distance} inches at {speed_mm_per_sec} mm/sec.")
            distance *= 25.4
        elif unit in ("feet", "ft"):
            print(f"Traveling {distance} feet at {speed_mm_per_sec} mm/sec.")
            distance *= 304.8
        elif unit != "mm":
            print(f"Unsupported unit: {unit}")
            return 0

        # Calculate travel time in seconds
        travel_time = distance / speed_mm_per_sec
        print(f"Calculated travel time: {travel_time:.2f} seconds")

        # Turn on motor
        self.connect_to_plc()
        self.write_modbus_coils(coil_address, True)
        self.close_connection()

        # Wait for the duration of travel
        time.sleep(travel_time)

        # Turn off motor
        self.connect_to_plc()
        self.write_modbus_coils(coil_address, False)
        self.close_connection()

        return travel_time

    def reset_coils(self):
        plc = PyPLCConnection(PLC_IP)
        plc.read_single_register(DISTANCE_DATA_ADDRESS)
        plc.write_modbus_coils(GREEN, False)
        plc.write_modbus_coils(Z_DOWN_MOTION, False)
        plc.write_modbus_coils(Z_UP_MOTION, False)
        plc.write_modbus_coils(Y_RIGHT_MOTION, False)
        plc.write_modbus_coils(Y_LEFT_MOTION, False)

    def md_extruder_switch(self, status):
        """
        Turn the MD pellet extruder ON or OFF via Modbus coils.

        :param status: "on" or "off" (case-insensitive)
        """
        md_extruder_address = 13
        status_lower = status.strip().lower()

        if status_lower == "on":
            value = True
        elif status_lower == "off":
            value = False
        else:
            print(f"'{status}' is not a supported value. Please enter 'ON' or 'OFF'.")
            return

        self.write_modbus_coils(md_extruder_address, value)
        print(f"Turning MD pellet extruder {status.strip().upper()}")

    # def travel(self, coil_address, distance, unit, pps=60000, lead_mm=5, pulses_per_rev=20000):
    #     """
    #     Move stepper motor a given distance.

    #     :param coil_address: Modbus coil address to control the motor
    #     :param distance: Distance to travel
    #     :param unit: Unit of the distance ('mm', 'inches', 'feet')
    #     :param pps: Pulses per second to send to the motor
    #     :param lead_mm: Screw lead in mm/rev
    #     :param pulses_per_rev: Number of pulses for one revolution
    #     """

    #     if distance <= 0 or pps <= 0:
    #         print("Distance and PPS must be positive values.")
    #         return 0

    #     # --- Convert distance to mm ---
    #     unit = unit.lower()
    #     if unit in ("inches", "in"):
    #         distance_mm = distance * 25.4
    #     elif unit in ("feet", "ft"):
    #         distance_mm = distance * 304.8
    #     elif unit == "mm":
    #         distance_mm = distance
    #     else:
    #         print(f"Unsupported unit: {unit}")
    #         return 0

    #     # --- Calculate pulses needed ---
    #     mm_per_pulse = lead_mm / pulses_per_rev
    #     pulses_needed = distance_mm / mm_per_pulse

    #     # --- Calculate travel time ---
    #     travel_time = pulses_needed / pps
    #     print(f"Distance: {distance_mm:.3f} mm -> Pulses: {pulses_needed:.0f} -> Time: {travel_time:.3f} s")

    #     # --- Activate motor for calculated time ---
    #     self.connect_to_plc()
    #     self.write_modbus_coils(coil_address, True)
    #     self.close_connection()

    #     time.sleep(travel_time)

    #     self.connect_to_plc()
    #     self.write_modbus_coils(coil_address, False)
    #     self.close_connection()

    #     return travel_time


if __name__ == "__main__":
    plc = PyPLCConnection(PLC_IP)
    plc.read_single_register(DISTANCE_DATA_ADDRESS)
    plc.read_single_register(DISTANCE_DATA_ADDRESS)
    plc.write_modbus_coils(GREEN, False)
    plc.write_modbus_coils(Z_DOWN_MOTION, False)
    plc.write_modbus_coils(Z_UP_MOTION, False)
    plc.write_modbus_coils(Y_RIGHT_MOTION, False)
    plc.write_modbus_coils(Y_LEFT_MOTION, False)
    plc.read_single_register(7)
    plc.md_extruder_switch("off")
    # plc.calculate_pulse_per_second("z")
    # plc.travel(Z_UP_MOTION, 1, "in", pps=60000, lead_mm=5, pulses_per_rev=20000)


    # plc.write_modbus_coils(Z_UP_MOTION, True)  

    # time.sleep()



    




