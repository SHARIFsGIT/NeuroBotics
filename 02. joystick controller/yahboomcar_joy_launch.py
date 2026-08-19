# --- IMPORTING ROS 2 LAUNCH TOOLS ---
from launch import LaunchDescription  
# The main container (like a director's clipboard) that holds our list of programs to start.

from launch_ros.actions import Node  
# A tool used to start a single ROS 2 program (Node).


# Every ROS 2 Python launch file MUST have this exact function.
# When you type "ros2 launch ..." in the terminal, ROS 2 looks for this function and runs it.
def generate_launch_description():

    # --- DEFINING THE PROGRAM TO RUN ---
    node1 = Node(
        package='joy',           # Look for a package installed on the robot called 'joy'. 
                                 # (The 'joy' package is the standard ROS 2 toolbox for handling gamepads/joysticks).
        
        executable='joy_node',   # Inside that package, find the program named 'joy_node' and run it.
                                 # This program secretly runs in the background, constantly saying: 
                                 # "Is the A button pressed? Yes. Is the left stick pushed? Yes."
    )
    
    # --- THE FINAL LIST ---
    # Put our single program (node1) onto the director's clipboard.
    launch_description = LaunchDescription([node1])
    
    # Hand the clipboard back to ROS 2 so it can start the program.
    return launch_description