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
            gear_ratio = 20
        else:
            gear_ratio = 1
        # Convert speed from mm/min to mm/sec
        speed_mm_sec = speed_mm_min / 60

        # Calculate pulses per second (PPS)
        pulses_per_second = (steps_per_rev * gear_ratio/ lead_mm_rev) * speed_mm_sec
        print(pulses_per_second)
        if axis.lower() == "z":
            self.write_single_register(3,0)
            time.sleep(0.2)
            self.write_single_register(3,int(pulses_per_second))
        else:
            self.write_single_register(1,0)
            time.sleep(0.2)
            self.write_single_register(1,int(pulses_per_second))
        return pulses_per_second

    def travel(self, coil_address, distance, unit, speed_mm_per_min):
        """
        Calculate the time to travel a given distance using the speed of the stepper motor.
        
        :param distance_mm: Distance to travel in mm.
        :param speed_mm_per_min: Speed of the motor in mm/min.
        :return: Time to travel the given distance in seconds.
        """
        if distance <= 0 or speed_mm_per_min <= 0:
            print("Distance and speed must be positive values.")
            return 0
        
        if unit.lower() == "inches" or unit.lower() == "in":
            distance_in_inches = distance
            distance = distance * 25.4
            print(f"Traveling {distance_in_inches} inches at {speed_mm_per_min} mm/min.")

        elif unit.lower() == "feet" or unit.lower() == "ft":
            distance_in_feet = distance
            distance = distance * 304.8
            print(f"Traveling {distance_in_feet} feet at {speed_mm_per_min} mm/min.")

        # Calculate the time required to travel the distance
        travel_time = (distance / speed_mm_per_min) * 60
        print(f"travel time {travel_time} seconds")
        
        # Turn on the motor
        self.write_modbus_coils(coil_address, True)
        self.close_connection()
        
        # Wait for the motor to reach the distance
        time.sleep(travel_time)
        
        # Turn off the motor
        self.connect_to_plc()
        self.write_modbus_coils(coil_address, False)

        return travel_time
    
    def reset_coils(self):
        plc = PyPLCConnection(PLC_IP)
        plc.read_single_register(DISTANCE_DATA_ADDRESS)
        plc.write_modbus_coils(GREEN, False)
        plc.write_modbus_coils(Z_DOWN_MOTION, False)
        plc.write_modbus_coils(Z_UP_MOTION, False)
        plc.write_modbus_coils(Y_RIGHT_MOTION, False)
        plc.write_modbus_coils(Y_LEFT_MOTION, False)

if __name__ == "__main__":
    plc = PyPLCConnection(PLC_IP)
    plc.read_single_register(DISTANCE_DATA_ADDRESS)



    




