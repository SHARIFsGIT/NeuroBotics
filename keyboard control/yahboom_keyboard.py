#!/usr/bin/env python
# encoding: utf-8

# --- IMPORTING TOOLS ---
from geometry_msgs.msg import Twist  # The ROS 2 message for movement (speed and turning)
import sys, select, termios, tty     # Secret terminal tools! These let Python read your keypresses INSTANTLY, without waiting for you to press 'Enter'.

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

# This is just a fancy text menu printed to the screen so you know what buttons to press.
msg = """
Control Your SLAM-Bot!
---------------------------
Moving around:
   u    i    o
   j    k    l
   m    ,    .

q/z : increase/decrease max speeds by 10%
w/x : increase/decrease only linear speed by 10%
e/c : increase/decrease only angular speed by 10%
t/T : x and y speed switch
s/S : stop keyboard control
space key, k : force stop
anything else : stop smoothly

CTRL-C to quit
"""

# --- THE MOVEMENT DICTIONARY ---
# This maps a keyboard key to a (forward direction, turn direction).
# 1 means full speed ahead/right, -1 means full reverse/left, 0 means stop.
moveBindings = {
    'i': (1, 0),    # Forward
    'o': (1, -1),   # Forward & Turn Right
    'j': (0, 1),    # Turn Left in place
    'l': (0, -1),   # Turn Right in place
    'u': (1, 1),    # Forward & Turn Left
    ',': (-1, 0),   # Backward
    '.': (-1, 1),   # Backward & Turn Right
    'm': (-1, -1),  # Backward & Turn Left
    # ... (capital letters do the same thing, in case you have capslock on)
    'I': (1, 0),
    'O': (1, -1),
    'J': (0, 1),
    'L': (0, -1),
    'U': (1, 1),
    'M': (-1, -1),
}

# --- THE SPEED DICTIONARY ---
# This maps keys to multipliers. 1.1 means "add 10% speed". .9 means "subtract 10% speed".
speedBindings = {
    'Q': (1.1, 1.1), # Speed up both
    'Z': (.9, .9),   # Slow down both
    'W': (1.1, 1),   # Speed up forward only
    'X': (.9, 1),    # Slow down forward only
    'E': (1, 1.1),   # Speed up turning only
    'C': (1, .9),    # Slow down turning only
    # ... (lowercase letters do the same thing)
    'q': (1.1, 1.1),
    'z': (.9, .9),
    'w': (1.1, 1),
    'x': (.9, 1),
    'e': (1, 1.1),
    'c': (1, .9),
}


class Yahboom_Keybord(Node):
    def __init__(self, name):
        super().__init__(name)  # Name this ROS 2 Node
        
        # Create a publisher to send movement commands to the wheels on the 'cmd_vel' channel
        self.pub = self.create_publisher(Twist, 'cmd_vel', 1)
        
        # Load safety speed limits from the ROS 2 parameter server
        self.declare_parameter("linear_speed_limit", 1.0)
        self.declare_parameter("angular_speed_limit", 5.0)
        self.linenar_speed_limit = self.get_parameter("linear_speed_limit").get_parameter_value().double_value
        self.angular_speed_limit = self.get_parameter("angular_speed_limit").get_parameter_value().double_value
        
        # Save the current terminal settings so we can restore them when the program ends
        self.settings = termios.tcgetattr(sys.stdin)
        
    def getKey(self):
        # THIS IS THE MAGIC TRICK!
        # Normally, Python waits for you to type a whole word and press 'Enter'.
        # These next two lines temporarily hijack your keyboard so Python reads exactly 1 keypress instantly.
        tty.setraw(sys.stdin.fileno())
        rlist, _, _ = select.select([sys.stdin], [], [], 0.1)  # Wait 0.1 seconds for a key
        if rlist:
            key = sys.stdin.read(1)  # Grab that 1 key!
        else:
            key = ''  # No key was pressed
        # Restore the terminal back to normal so you can read the screen properly
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
        return key
        
    def vels(self, speed, turn):
        # Just a helper function to print the current speed nicely on the screen
        return "currently:\tspeed %s\tturn %s " % (speed, turn)		
    
def main():
    rclpy.init()  # Turn on ROS 2
    yahboom_keyboard = Yahboom_Keybord("yahboom_keyboard_ctrl")
    
    # --- STATE VARIABLES ---
    xspeed_switch = True  # If True, keys move you forward/backward. If False, keys slide you sideways!
    (speed, turn) = (0.2, 1.0)  # Starting speeds (20% forward, 100% turning)
    (x, th) = (0, 0)            # Current movement directions (0 = stop)
    status = 0
    stop = False                # Emergency stop flag
    count = 0                   # A counter to make the robot stop if you stop pressing keys
    twist = Twist()             # Create an empty movement message
    
    try:  # The try/except/finally block is for safety. It ensures the robot stops if the program crashes.
        print(msg)  # Print the menu
        print(yahboom_keyboard.vels(speed, turn))  # Print starting speeds
        
        while (1):  # Loop forever
            key = yahboom_keyboard.getKey()  # Listen for a keypress
            
            # Check for special toggle keys
            if key == "t" or key == "T":
                xspeed_switch = not xspeed_switch  # Switch between forward/backward mode and sideways mode
            elif key == "s" or key == "S":
                print ("stop keyboard control: {}".format(not stop))
                stop = not stop  # Toggle pause
            
            # If the key is in our movement dictionary...
            if key in moveBindings.keys():
                x = moveBindings[key][0]   # Get forward direction
                th = moveBindings[key][1]  # Get turn direction
                count = 0                   # Reset the stop counter
            # If the key is in our speed dictionary...
            elif key in speedBindings.keys():
                speed = speed * speedBindings[key][0]  # Multiply speed
                turn = turn * speedBindings[key][1]    # Multiply turn
                count = 0
                
                # Enforce hard speed limits so the robot doesn't go crazy fast
                if speed > yahboom_keyboard.linenar_speed_limit: 
                    speed = yahboom_keyboard.linenar_speed_limit
                    print("Linear speed limit reached!")
                if turn > yahboom_keyboard.angular_speed_limit: 
                    turn = yahboom_keyboard.angular_speed_limit
                    print("Angular speed limit reached!")
                    
                print(yahboom_keyboard.vels(speed, turn))  # Print new speed
                
            # Spacebar = emergency stop
            elif key == ' ': 
                (x, th) = (0, 0)
            else:
                # If you press any other random key (or let go of all keys)
                count = count + 1
                if count > 4:  # If no valid keys are pressed for 4 loops
                    (x, th) = (0, 0)  # Stop moving
                if (key == '\x03'): break  # If you press Ctrl+C, break the loop and quit
                
            # Apply the movement to the Twist message
            if xspeed_switch:
                twist.linear.x = speed * x  # Move forward/backward
            else:
                twist.linear.y = speed * x  # Slide left/right (Mecanum wheels!)
                
            twist.angular.z = turn * th     # Spin left/right
            
            # Send the command to the robot
            if not stop: 
                yahboom_keyboard.pub.publish(twist)  # Drive!
            if stop:
                yahboom_keyboard.pub.publish(Twist()) # Send all zeros (Stop)
                
    except Exception as e: 
        print(e)  # Print any errors
    finally: 
        # No matter what happens (even if it crashes), THIS WILL RUN.
        # Send an empty Twist message (all zeros) to guarantee the robot stops moving!
        yahboom_keyboard.pub.publish(Twist())
        
    # Clean up
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, yahboom_keyboard.settings)  # Restore terminal
    yahboom_keyboard.destroy_node()
    rclpy.shutdown()