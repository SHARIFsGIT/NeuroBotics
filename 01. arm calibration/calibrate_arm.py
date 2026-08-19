import serial    # Lets Python talk to hardware over a serial connection (usually a USB cable)
import struct    # Used to pack data into binary format (1s and 0s) so the hardware can understand it
import time      # Lets Python pause and wait
from config_robot import MicroROS_Robot  # Imports the custom "blueprint" for your specific robot

if __name__ == "__main__":
    # Create the robot object. 'debug=False' means "don't print out all the hidden background data to my screen"
    bot = MicroROS_Robot(debug=False)
    
    # Ask the robot's circuit board what software version it is running
    version = bot.read_version()
    print("version:", version)  # Print it to the screen so you can see it
    
    # Turn ON the arm's torque (Torque = motor power/muscle). 
    # '1' means ON. The motors will now lock in place and resist being moved by hand.
    bot.set_arm_torque(1)
    time.sleep(.5)  # Wait half a second for the motors to lock
    
    # Turn OFF the arm's torque. 
    # '0' means OFF. The motors relax and become "floppy" so you can physically move the arm by hand.
    bot.set_arm_torque(0)
    time.sleep(.5)  # Wait half a second for the motors to relax
    
    # *** THIS IS WHERE YOU MOVE THE ARM BY HAND ***
    # The script pauses here and waits for you to type something on your keyboard.
    # While it waits, you are supposed to manually move the robot arm into its perfect "zero" starting position.
    adjust = input("Input y for end of adjusting:")
    
    # Check what you typed.
    # (Note for advanced learners: There is a tiny bug in this original code. It says 'adjust == 'y' or 'Y''. 
    # In Python, 'Y' by itself is always considered "True", so it will actually accept ANY key you press, 
    # not just 'y'. But the programmer's *intention* was to only proceed if you typed 'y' or 'Y'!)
    if adjust == 'y' or 'Y':
        
        # Loop through the numbers 1 to 6 (your arm has 6 joints/motors)
        for i in range(1,7):
            
            # Tell joint number 'i': "Whatever angle you are currently at, save that as your new Zero!"
            state = bot.set_arm_calib_offset(i)
            
            # If the robot replies with a negative number (like -1), it means the save failed.
            if state < 0:
                # So, we try saving it one more time!
                state = bot.set_arm_calib_offset(i)
                
            # Print out which joint we just calibrated and if it worked (state variable)
            print("state=", i, state)
            
        print("Calibration successfully!")  # Yay! The robot's brain has officially learned its new zero position.
        
        # Turn the motor power/torque back ON ('1') so the arm locks into its newly calibrated starting position.
        bot.set_arm_torque(1)
        
        # Delete the 'bot' object from Python's memory. 
        # This is like turning off the lights and locking the door when you leave. 
        # It cleanly closes the serial connection so other programs can use the robot.
        del bot