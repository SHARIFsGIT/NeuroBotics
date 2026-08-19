import serial   # The tool that lets Python talk over a USB/Serial wire
import struct   # Packs normal numbers into raw binary data (1s and 0s) the microcontroller can understand
import time     # Lets Python pause and wait

# --- THE COMMAND DICTIONARY ---
# Think of this like a menu at a restaurant. 
# The first number (like 0x22) is the "Item Number" the microcontroller understands.
# The rest are empty slots waiting to be filled with data (like how many orders you want).
ORDER = {
    "MOTOR_PID": [0x13, 0, 0, 0, 0, 0, 0, 0],       # Address for Motor PID tuning
    "IMU_YAW_PID": [0x14, 0, 0, 0, 0, 0, 0, 0],    # Address for IMU turning PID tuning
    "CAR_TYPE": [0x15, 0],                          # Address to ask what kind of robot chassis this is
    "ARM_TORQUE": [0x22, 0],                        # Address to turn arm motor power ON/OFF
    "ARM_OFFSET": [0x24, 0, 0],                     # Address to calibrate the arm's zero position
    "ARM_MID_VALUE": [0x25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], # Address to set arm middle positions
    "DOMAIN_ID": [0x41, 0, 0],                      # Address for ROS 2 Walkie-Talkie channel
    "ROS_NAMESPACE": [0x42, 0, 0],                  # Address for ROS 2 Name
    "ROS_SCALE_LINE": [0x43, 0, 0, 0],              # Address for forward speed scaling
    "ROS_SCALE_ANGULAR": [0x44, 0, 0, 0],            # Address for turning speed scaling
    "ROBOT_REBOOT": [0x80, 0, 0],                   # Address to reboot the microcontroller
    "ROBOT_CONFIG": [0x81, 0, 0],                   # Address to save/reset config
    "REQUEST_DATA": [0x50, 0, 0],                   # Address used when asking for data
    "FIRMWARE_VERSION": [0x51],                     # Address to ask for software version
}


class MicroROS_Robot():
    # This class is the "Translator" between the Jetson (Python) and the bottom board (Microcontroller)

    def __init__(self, port="/dev/myserial", debug=False):
        # Open the serial wire! 2,000,000 bits per second is VERY fast.
        self.__ser = serial.Serial(port, 2000000, timeout=0.05)
        
        # Variables for the "State Machine" (reading data byte by byte)
        self.__rx_FLAG = 0       # What step of reading are we on?
        self.__rx_COUNT = 0      # How many bytes have we read?
        self.__rx_ADDR = 0       # What address is this data for?
        self.__rx_LEN = 0        # How long is the message supposed to be?
        self.__RX_BUF_LEN_MAX = 40  # Maximum size of the inbox
        self.__rx_DATA = bytearray(self.__RX_BUF_LEN_MAX) # The actual inbox array
        
        self.__send_delay = 0.01 # Pause after sending so we don't overwhelm the wire
        self.__read_delay = 0.01 # Pause after asking a question so the chip has time to think
        self.__debug = debug     # If True, print all the raw 1s and 0s to the screen
        self.__data_changed = False # Keeps track of if we need to save changes

        # Protocol "Magic Numbers" (The rules of the language)
        self.__HEAD = 0xFF       # Every message MUST start with 0xFF (Like ringing a doorbell)
        self.__DEVICE_ID = 0xFC # The ID of the microcontroller we are talking to
        self.__RETURN_ID = self.__DEVICE_ID - 1 # The ID the microcontroller uses when it replies back
        self.__COMPLEMENT = 257 - self.__DEVICE_ID # Math used for the checksum
        self.__READ_DATA = 0x50 # The code that means "I want to read data"

        self.CAR_TYPE = 7       # What type of robot is this? (7 likely means Mecanum wheels)


    # --- SENDING DATA ---
    # This builds the "envelope" and mails it.
    def __send(self, key, len=1):
        self.__data_changed = True
        order = ORDER[key][0] # Grab the "menu item number" (e.g., 0x22 for ARM_TORQUE)
        value = []
        value_sum = self.__COMPLEMENT
        
        # Pack up the data values we want to send
        for i in range(0, len):
            value.append(ORDER[key][1 + i])
            value_sum = value_sum + ORDER[key][1 + i]
            
        # Calculate a Checksum. This is a math formula added to the end of the letter.
        # The microcontroller does the same math. If the numbers don't match, it means the wire glitched!
        sum_data = (self.__HEAD + self.__DEVICE_ID + (len + 0x03) + order + value_sum) % 256
        
        # Build the final envelope: [Doorbell, Device ID, Length, Command, Data..., Checksum]
        tx = [self.__HEAD, self.__DEVICE_ID, (len + 0x03), order]
        tx.extend(value)
        tx.append(sum_data)
        
        # Mail the letter! Write the binary data to the USB wire.
        self.__ser.write(tx)
        if self.__send_delay > 0:
            time.sleep(self.__send_delay)
        if self.__debug:
            print ("Send: [0x" + ', 0x'.join('{:02X}'.format(x) for x in tx) + "]")


    # --- REQUESTING DATA ---
    # This sends a letter saying "Hey, please send me the data for address X"
    def __request(self, addr, param=0):
        order = self.__READ_DATA
        buf_len = 5
        sum_data = (buf_len + order + addr + param) % 256
        tx = [self.__HEAD, self.__DEVICE_ID, buf_len, order, addr, param, sum_data]
        
        # Clear out any old junk sitting in the wire
        self.__ser.flushInput()
        self.__ser.flushOutput()
        for i in range(self.__RX_BUF_LEN_MAX):
            self.__rx_DATA[i] = 0
        
        # Send the request
        self.__ser.write(tx)
        if self.__debug:
            print ("Read: [0x" + ', 0x'.join('{:02X}'.format(x) for x in tx) + "]")


    # --- RECEIVING & PARSING DATA ---
    # This is the "State Machine". It reads bytes one by one and pieces the letter back together.
    def __unpack(self):
        n = self.__ser.inWaiting()
        rx_CHECK = 0
        if n <= 0:
            return False # Nothing in the inbox
        
        data_array = self.__ser.read_all()
        if self.__debug:
            print ("rx_data: [0x" + ', 0x'.join('{:02X}'.format(x) for x in data_array) + "]")
            
        for data in data_array:
            # Step 1: Look for the doorbell (0xFF)
            if self.__rx_FLAG == 0:
                if data == self.__HEAD:
                    self.__rx_FLAG = 1 # Found the start of a message!
                else:
                    self.__rx_FLAG = 0

            # Step 2: Check if it's meant for us (0xFB)
            elif self.__rx_FLAG == 1:
                if data == self.__RETURN_ID:
                    self.__rx_FLAG = 2 # Yes, it's for me!
                else:
                    self.__rx_FLAG = 0

            # Step 3: Read the Length of the message
            elif self.__rx_FLAG == 2:
                self.__rx_LEN = data
                self.__rx_FLAG = 3

            # Step 4: Read the Address (What is this data about?)
            elif self.__rx_FLAG == 3:
                self.__rx_ADDR = data
                self.__rx_FLAG = 4
                self.__rx_COUNT = 0

            # Step 5: Read the actual Data payload
            elif self.__rx_FLAG == 4:
                if self.__rx_COUNT < self.__rx_LEN - 3:
                    self.__rx_DATA[self.__rx_COUNT] = data
                    self.__rx_COUNT = self.__rx_COUNT + 1
                if self.__rx_COUNT >= (self.__rx_LEN - 3):
                    self.__rx_FLAG = 5

            # Step 6: Check the Checksum to ensure no data was corrupted over the wire.
            elif self.__rx_FLAG == 5:
                for value in self.__rx_DATA:
                    rx_CHECK = rx_CHECK + value
                rx_CHECK = (self.__rx_LEN + self.__rx_ADDR + rx_CHECK) % 256
                if data == rx_CHECK:
                    # Yay! We successfully received a valid data packet!
                    self.__rx_FLAG = 0
                    self.__rx_COUNT = 0
                    return True
                else:
                    # Uh oh. Checksum failed. The wire must have glitched. Throw away the data.
                    if self.__debug:
                        print("check error:", rx_CHECK, data)
                    self.__rx_FLAG = 0
                    self.__rx_COUNT = 0
                    self.__rx_ADDR = 0
                    self.__rx_LEN = 0
        return False


    # --- CONFIGURATION FUNCTIONS ---
    # (These are the "User-Friendly" buttons you press. They format the data and call __send() or __request())

    # Reboot the microcontroller
    def reboot_device(self):
        ORDER["ROBOT_REBOOT"][1] = 0x5F  # Secret reboot code
        ORDER["ROBOT_REBOOT"][2] = 0x5F
        self.__send("ROBOT_REBOOT", len=2)
        time.sleep(2)
    
    # Wipe all custom settings back to factory defaults
    def reset_factory_config(self):
        ORDER["ROBOT_CONFIG"][1] = 0
        ORDER["ROBOT_CONFIG"][2] = 0x5F
        self.__send("ROBOT_CONFIG", len=2)
        time.sleep(2)

    # Save changes to the microcontroller's permanent memory
    def update_config_data(self):
        if self.__data_changed:
            ORDER["ROBOT_CONFIG"][1] = 1
            ORDER["ROBOT_CONFIG"][2] = 0x5F
            self.__send("ROBOT_CONFIG", len=2)
            self.__data_changed = False
            time.sleep(2)


    # Set the middle position of the arm servos (raw servo units)
    def set_arm_mid_value(self, mid_value=[2000, 2000, 2000, 2000, 1486, 3100]):
        # Check if the values are within a safe range so we don't break the servos
        if 1600 <= mid_value[0] <= 2400 and 1600 <= mid_value[1] <= 2400 and 1600 <= mid_value[2] <= 2400 and \
            1600 <= mid_value[3] <= 2400 and 1186 <= mid_value[4] <= 1786 and 2700 <= mid_value[5] <= 3500:
            
            # struct.pack turns normal Python numbers into binary bytes the servo understands
            value_s1 = bytearray(struct.pack('h', int(mid_value[0])))
            value_s2 = bytearray(struct.pack('h', int(mid_value[1])))
            value_s3 = bytearray(struct.pack('h', int(mid_value[2])))
            value_s4 = bytearray(struct.pack('h', int(mid_value[3])))
            value_s5 = bytearray(struct.pack('h', int(mid_value[4])))
            value_s6 = bytearray(struct.pack('h', int(mid_value[5])))

            # Pack all 6 values into our ORDER array to be sent
            ORDER["ARM_MID_VALUE"][1] = value_s1[0]
            ORDER["ARM_MID_VALUE"][2] = value_s1[1]
            ORDER["ARM_MID_VALUE"][3] = value_s2[0]
            ORDER["ARM_MID_VALUE"][4] = value_s2[1]
            ORDER["ARM_MID_VALUE"][5] = value_s3[0]
            ORDER["ARM_MID_VALUE"][6] = value_s3[1]
            ORDER["ARM_MID_VALUE"][7] = value_s4[0]
            ORDER["ARM_MID_VALUE"][8] = value_s4[1]
            ORDER["ARM_MID_VALUE"][9] = value_s5[0]
            ORDER["ARM_MID_VALUE"][10] = value_s5[1]
            ORDER["ARM_MID_VALUE"][11] = value_s6[0]
            ORDER["ARM_MID_VALUE"][12] = value_s6[1]
            ORDER["ARM_MID_VALUE"][13] = 0
            self.__send("ARM_MID_VALUE", len=13)
        else:
            print("mid_value input error!")

    # Turn arm motor power ON (1) or OFF (0)
    def set_arm_torque(self, enable):
        if enable > 0:
            on = 1
        else:
            on = 0
        ORDER["ARM_TORQUE"][1] = on
        temp = self.__data_changed
        self.__send("ARM_TORQUE", len=1)
        self.__data_changed = temp
    
    # Tell a specific servo to save its current physical position as its new "Zero"
    def set_arm_calib_offset(self, arm_id):
        if arm_id < 1 or arm_id > 6:
            return
        ORDER["ARM_OFFSET"][1] = int(arm_id) & 0xFF
        ORDER["ARM_OFFSET"][2] = 0
        
        # Clear inbox
        for i in range(self.__RX_BUF_LEN_MAX):
            self.__rx_DATA[i] = 0
        self.__ser.flushInput()
        
        # Send the command
        temp = self.__data_changed
        self.__send("ARM_OFFSET", len=2)
        self.__data_changed = temp
        
        # Wait for the microcontroller to reply saying "Success!" or "Failed!"
        state = -1
        for k in range(6):
            time.sleep(.5)
            if self.__unpack():
                if self.__rx_DATA[0] == arm_id:
                    state = self.__rx_DATA[1]
                    return state
        return state

    # Calibrate all 6 servos one by one
    def set_arm_calib_offset_all(self):
        for i in range(6):
            state = robot.set_arm_calib_offset(i+1)
            print("state:", i+1, state)
            time.sleep(.5)

    # Change the ROS 2 Walkie-Talkie Channel!
    def set_ros_domain_id(self, domain_id):
        if domain_id < 0 or domain_id > 101:
            return
        ORDER["DOMAIN_ID"][1] = int(domain_id) & 0xFF
        ORDER["DOMAIN_ID"][2] = 0
        self.__send("DOMAIN_ID", len=2)

    # Give the robot a name (Namespace) so you can run multiple robots in the same room
    def set_ros_namespace(self, ros_namespace):
        name_len = len(ros_namespace)
        if name_len > 10 or name_len < 0:
            return
        name_buf = [0 for i in range(10)]
        name_bytes = bytes(str(ros_namespace), "utf-8")
        for i in range(10):
            if i < len(ros_namespace):
                name_buf[i] = name_bytes[i]
        ORDER["ROS_NAMESPACE"].extend(name_buf)
        ORDER["ROS_NAMESPACE"][1] = name_len
        ORDER["ROS_NAMESPACE"][2] = 0
        self.__send("ROS_NAMESPACE", len=12)

    # Make the robot drive faster or slower (Linear)
    def set_ros_scale_line(self, scale=1.0):
        if scale > 2 or scale < 0:
            return
        bytearray_scale = bytearray(struct.pack('h', int(scale*1000)))
        ORDER["ROS_SCALE_LINE"][1] = bytearray_scale[0]
        ORDER["ROS_SCALE_LINE"][2] = bytearray_scale[1]
        ORDER["ROS_SCALE_LINE"][3] = 0
        self.__send("ROS_SCALE_LINE", len=3)

    # Make the robot turn faster or slower (Angular)
    def set_ros_scale_angular(self, scale=1.0):
        if scale > 2 or scale < 0:
            return
        bytearray_scale = bytearray(struct.pack('h', int(scale*1000)))
        ORDER["ROS_SCALE_ANGULAR"][1] = bytearray_scale[0]
        ORDER["ROS_SCALE_ANGULAR"][2] = bytearray_scale[1]
        ORDER["ROS_SCALE_ANGULAR"][3] = 0
        self.__send("ROS_SCALE_ANGULAR", len=3)

    # Set Motor PID tuning (Proportional, Integral, Derivative) for smooth driving
    def set_motor_pid_parm(self, pid_p, pid_i, pid_d):
        pid_p_s = bytearray(struct.pack('h', int(pid_p*100)))
        pid_i_s = bytearray(struct.pack('h', int(pid_i*100)))
        pid_d_s = bytearray(struct.pack('h', int(pid_d*100)))
        ORDER["MOTOR_PID"][1] = pid_p_s[0]
        ORDER["MOTOR_PID"][2] = pid_p_s[1]
        ORDER["MOTOR_PID"][3] = pid_i_s[0]
        ORDER["MOTOR_PID"][4] = pid_i_s[1]
        ORDER["MOTOR_PID"][5] = pid_d_s[0]
        ORDER["MOTOR_PID"][6] = pid_d_s[1]
        ORDER["MOTOR_PID"][7] = 0
        self.__send("MOTOR_PID", len=7)

    # Set IMU PID tuning (keeps the robot driving straight without drifting)
    def set_imu_yaw_pid_parm(self, pid_p, pid_i, pid_d):
        pid_p_s = bytearray(struct.pack('h', int(pid_p*100)))
        pid_i_s = bytearray(struct.pack('h', int(pid_i*100)))
        pid_d_s = bytearray(struct.pack('h', int(pid_d*100)))
        ORDER["IMU_YAW_PID"][1] = pid_p_s[0]
        ORDER["IMU_YAW_PID"][2] = pid_p_s[1]
        ORDER["IMU_YAW_PID"][3] = pid_i_s[0]
        ORDER["IMU_YAW_PID"][4] = pid_i_s[1]
        ORDER["IMU_YAW_PID"][5] = pid_d_s[0]
        ORDER["IMU_YAW_PID"][6] = pid_d_s[1]
        ORDER["IMU_YAW_PID"][7] = 0
        self.__send("IMU_YAW_PID", len=7)
    

    # --- READING FUNCTIONS ---
    # (These ask the microcontroller a question, wait for a reply, and translate it back to Python)

    def read_car_type(self):
        '''Read what kind of robot chassis this is.'''
        self.__request(ORDER["CAR_TYPE"][0])
        time.sleep(self.__read_delay)
        str_data = None
        if self.__unpack():
            car_type = struct.unpack('h', bytearray(self.__rx_DATA[0:2]))[0]
            str_data = str(car_type)
        return str_data

    def read_arm_mid_value(self):
        '''Read the saved middle positions of the arm servos.'''
        self.__request(ORDER["ARM_MID_VALUE"][0])
        time.sleep(self.__read_delay)
        str_data = None
        if self.__unpack():
            value_s1 = struct.unpack('h', bytearray(self.__rx_DATA[0:2]))[0]
            value_s2 = struct.unpack('h', bytearray(self.__rx_DATA[2:4]))[0]
            value_s3 = struct.unpack('h', bytearray(self.__rx_DATA[4:6]))[0]
            value_s4 = struct.unpack('h', bytearray(self.__rx_DATA[6:8]))[0]
            value_s5 = struct.unpack('h', bytearray(self.__rx_DATA[8:10]))[0]
            value_s6 = struct.unpack('h', bytearray(self.__rx_DATA[10:12]))[0]
            str_data = "%d,%d,%d,%d,%d,%d" % (value_s1, value_s2, value_s3, value_s4, value_s5, value_s6)
        return str_data

    def read_ros_domain_id(self):
        '''Read the current ROS 2 Walkie-Talkie channel.'''
        self.__request(ORDER["DOMAIN_ID"][0])
        time.sleep(self.__read_delay)
        str_data = None
        if self.__unpack():
            domain_id = self.__rx_DATA[0]
            str_data = "%d" % (domain_id)
        return str_data

    def read_ros_namespace(self):
        '''Read the robot's name.'''
        self.__request(ORDER["ROS_NAMESPACE"][0])
        time.sleep(self.__read_delay)
        str_data = None
        if self.__unpack():
            str_data = self.__rx_DATA[1:].decode('utf-8')
        return str_data

    def read_ros_scale_line(self):
        '''Read the forward speed scaling.'''
        self.__request(ORDER["ROS_SCALE_LINE"][0])
        time.sleep(self.__read_delay)
        str_data = None
        if self.__unpack():
            scale = struct.unpack('h', bytearray(self.__rx_DATA[0:2]))[0]/1000.0
            str_data = "%.3f" % scale
        return str_data
    
    def read_ros_scale_angular(self):
        '''Read the turning speed scaling.'''
        self.__request(ORDER["ROS_SCALE_ANGULAR"][0])
        time.sleep(self.__read_delay)
        str_data = None
        if self.__unpack():
            scale = struct.unpack('h', bytearray(self.__rx_DATA[0:2]))[0]/1000.0
            str_data = "%.3f" % scale
        return str_data

    def read_motor_pid_parm(self):
        '''Read the Motor PID tuning numbers.'''
        self.__request(ORDER["MOTOR_PID"][0], 1)
        time.sleep(self.__read_delay)
        str_data = None
        if self.__unpack():
            pid_p = struct.unpack('h', bytearray(self.__rx_DATA[1:3]))[0]/1000.0
            pid_i = struct.unpack('h', bytearray(self.__rx_DATA[3:5]))[0]/1000.0
            pid_d = struct.unpack('h', bytearray(self.__rx_DATA[5:7]))[0]/1000.0
            str_data = "%.3f, %.3f, %.3f" % (pid_p, pid_i, pid_d)
        return str_data

    def read_imu_yaw_pid_parm(self):
        '''Read the IMU PID tuning numbers.'''
        self.__request(ORDER["IMU_YAW_PID"][0], 5)
        time.sleep(self.__read_delay)
        str_data = None
        if self.__unpack():
            pid_p = struct.unpack('h', bytearray(self.__rx_DATA[1:3]))[0]/1000.0
            pid_i = struct.unpack('h', bytearray(self.__rx_DATA[3:5]))[0]/1000.0
            pid_d = struct.unpack('h', bytearray(self.__rx_DATA[5:7]))[0]/1000.0
            str_data = "%.3f, %.3f, %.3f" % (pid_p, pid_i, pid_d)
        return str_data

    def read_version(self):
        '''Read the microcontroller's software version.'''
        self.__request(ORDER["FIRMWARE_VERSION"][0])
        time.sleep(self.__read_delay)
        str_version = None
        if self.__unpack():
            str_version = "%d.%d.%d" % (self.__rx_DATA[0], self.__rx_DATA[1], self.__rx_DATA[2])
        return str_version

    # --- PRINT ALL INFO ---
    # Asks the microcontroller for every single setting and prints it nicely to the screen
    def print_all_firmware_parm(self):
        version = self.read_version()
        print("version:", version)

        domain_id = self.read_ros_domain_id()
        print("domain_id:", domain_id)

        ros_namespace = self.read_ros_namespace()
        print("ros_namespace:", ros_namespace)

        ros_scale_line = self.read_ros_scale_line()
        print("ros_scale_line:", ros_scale_line)

        ros_scale_angular = self.read_ros_scale_angular()
        print("ros_scale_angular:", ros_scale_angular)
 
        motor_pid_parm = self.read_motor_pid_parm()
        print("motor pid parm:", motor_pid_parm)

        imu_pid_parm = self.read_imu_yaw_pid_parm()
        print("imu pid parm:", imu_pid_parm)

        arm_mid = self.read_arm_mid_value()
        print("arm_mid:", arm_mid)


# --- THE MAIN SCRIPT ---
# This part only runs if you click "Play" on this specific file. 
# It is a test/config script used by the Yahboom team to configure the robot before shipping it to you.
if __name__ == '__main__':

    import platform
    debug = False
    device = platform.system()
    print("Read device:", device)
    
    # Check if we are on Windows or Linux (Jetson)
    if device == 'Windows':
        # Search for a COM port to connect to
        com_index = 1
        while True:
            com_index = com_index + 1
            try:
                com = 'COM%d' % com_index
                robot = MicroROS_Robot(com, debug=debug)
                break
            except:
                if com_index > 256:
                    print("-----------------------No COM Open--------------------------")
                    exit(0)
                continue
        print("--------------------Open %s---------------------" % com)
    else:
        # On the Jetson (Linux), connect to this specific USB port name
        robot = MicroROS_Robot(port="/dev/myserial", debug=debug)
    
    print("Waiting to read the car type")
    while True:
        car_type = robot.read_car_type()
        if car_type is not None:
            print("car_type:", car_type)
            if int(car_type) == robot.CAR_TYPE:
                break # Verify we are talking to the right robot
        time.sleep(.5)

    
    # robot.set_ros_domain_id(30) # You could change the domain ID here!
    # robot.set_motor_pid_parm(0.8, 0.06, 0.5) # You could tune the motor speeds here!
    robot.set_ros_scale_line(1.0)
    robot.set_ros_scale_angular(1.05)
    # arm_mid_value = [2000, 2000, 2000, 2000, 1486, 3100]
    # robot.set_arm_mid_value(arm_mid_value)
    
    # Save any changes to the microcontroller
    robot.update_config_data()

    # Print everything currently saved on the robot
    time.sleep(1)
    robot.print_all_firmware_parm()

    # Reboot the microcontroller so the new settings take effect
    time.sleep(1)
    robot.reboot_device()

    # Keep it running
    try:
        while False:
            # robot.beep(100)
            time.sleep(1)
    except:
        pass
    time.sleep(.1)
    del robot # Cleanly close the USB port