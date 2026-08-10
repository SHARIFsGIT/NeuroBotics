# This is an auto-start file that runs when the robot boots up.

# --- IMPORTING TOOLS ---
import subprocess  # Lets Python run terminal commands
from PyQt5.QtWidgets import QApplication, QMessageBox  # Tools to make a pop-up graphical window
from PyQt5.QtCore import Qt  # Extra tools for the pop-up window
import psutil  # Lets Python see and kill background running programs (processes)
import rclpy  # The main ROS 2 library for Python
from rclpy.node import Node  # The blueprint for creating a ROS 2 "Node" (a mini-program that talks to the robot)
from geometry_msgs.msg import Twist  # The specific "message" type used to send movement commands (speed/turning)
import time  # Lets Python pause and wait

# --- GLOBAL VARIABLES ---
launch_process = None  # An empty box to hold our first background program later
run_process = None  # An empty box to hold our second background program later


# --- HELPER FUNCTION TO KILL PROGRAMS ---
def kill_process_tree(pid):
    # 'pid' stands for Process ID. It's like a badge number for a running program.
    try:
        parent = psutil.Process(pid)  # Find the main program using its badge number
        for child in parent.children(recursive=True):  # Find any "child" programs it started
            child.kill()  # Forcefully close the children
        parent.kill()  # Finally, forcefully close the main parent program
    except psutil.NoSuchProcess:
        pass  # If the program is already closed, just ignore it and move on (don't crash)
        

# --- WHAT TO DO WHEN THE POP-UP WINDOW IS CLOSED ---
def close_event(event):
    event.accept()  # Tell the computer "Yes, it's okay to close the window"
    kill_process_tree(launch_process.pid)  # Kill the first background program we started
    kill_process_tree(run_process.pid)  # Kill the second background program we started    
    app.quit()  # Close the pop-up application entirely


# --- FUNCTION TO START THE JOYSTICK CONTROL ---
def start_processes():
    global launch_process, run_process  # Tell Python we want to use the empty boxes we made earlier
    
    # Create a pop-up message box on the screen
    msg_box = QMessageBox()
    msg_box.setText("your controller is running...")  # What the text says
    msg_box.setWindowTitle("controller mode ")  # The title at the top of the window
    msg_box.setIcon(QMessageBox.Information)  # Add a little "i" info icon to the window
    msg_box.setStandardButtons(QMessageBox.NoButton)  # Remove the OK/CANCEL buttons so it stays open
    msg_box.setWindowModality(Qt.NonModal)  # Lets the user still click other things while this is open  

    # Start the ROS 2 launch file in the background (like typing: ros2 launch yahboomcar_ctrl yahboomcar_joy_launch.py)
    launch_process = subprocess.Popen(['ros2', 'launch', 'yahboomcar_ctrl', 'yahboomcar_joy_launch.py'])
    
    # Start the actual joystick Python node in the background (like typing: ros2 run yahboomcar_ctrl yahboom_joy_M3Pro)
    run_process = subprocess.Popen(['ros2', 'run', 'yahboomcar_ctrl', 'yahboom_joy_M3Pro'])
    
    print("Joy controller start successful!!!")  # Print a success message to the terminal
    
    msg_box.closeEvent = close_event  # Tell the window "When I close you, run the close_event function above"
    msg_box.show()  # Actually display the window on the screen  

    app.exec_()  # Keep the window open and waiting until someone closes it


# --- CREATING THE ROS 2 NODE ---
class autostart(Node):  # We are creating a mini-program (Node) called 'autostart'
    def __init__(self):  # This runs automatically when the node starts
        super().__init__('autostart_node')  # Give this node the name 'autostart_node' in the ROS 2 system
        
        # Create a "Publisher". Think of this as a radio station broadcasting on channel '/cmd_vel'
        # 'Twist' is the format of the message (it holds forward speed and turning speed). '10' is the buffer size.
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
        twist = Twist()  # Create a blank movement message
        twist.linear.x = 0.0  # Set forward/backward speed to 0 (Stop moving forward)
        twist.linear.y = 0.0  # Set side-to-side speed to 0 (Stop moving sideways)
        twist.angular.z = 0.0  # Set turning speed to 0 (Stop spinning)

        # Waiting for someone to tune into our radio station
        # This loop keeps running as long as nobody is listening to '/cmd_vel'
        while not self.cmd_vel_pub.get_subscription_count():
            self.cmd_vel_pub.publish(twist)  # Shout "STOP" into the void
            self.get_logger().info('Waiting for subscribers...')  # Print a waiting message
            time.sleep(0.1)  # Pause for 0.1 seconds before trying again
            
        # If we get here, it means the robot's motor controller is finally listening!
        self.get_logger().info('Published initial velocity command')  # Print a success message
        self.cmd_vel_pub.publish(twist)  # Send one final STOP command to be absolutely sure the robot is still


# --- THE MAIN SCRIPT STARTS HERE ---
if __name__ == "__main__":

    rclpy.init()  # Turn on the ROS 2 system (boot up the robot's communication network)
    
    auto_start = autostart()  # Run our autostart Node from above (this sends the STOP command and waits for the motors)
    
    app = QApplication([])  # QApplication -> Prepare the system to draw graphical windows on the screen
    
    start_processes()  # Run the function that starts the joystick background programs and shows the pop-up window
    
    rclpy.shutdown()  # Once the pop-up window is closed, turn off the ROS 2 system cleanly.