# --- IMPORTING ROS 2 LAUNCH TOOLS ---
from launch import LaunchDescription  # The main container that holds our list of programs to start
from launch_ros.actions import Node  # A tool to start a single ROS 2 program (Node)
import os  # Lets Python interact with computer folders and file paths
from launch.actions import IncludeLaunchDescription  # A tool to run ANOTHER launch file inside this one
from launch.launch_description_sources import PythonLaunchDescriptionSource  # Tells ROS the other launch file is written in Python
from ament_index_python.packages import get_package_share_directory  # A ROS 2 tool that finds where a package is installed on the robot


# Every ROS 2 Python launch file MUST have this exact function.
# When you type "ros2 launch ..." in the terminal, ROS 2 secretly calls this function to figure out what to do.
def generate_launch_description():

    # --- PROGRAM 1: THE CAMERA ---
    # We want to turn on the robot's camera. 
    # Instead of writing all the camera setup code here, we use a shortcut and load an existing launch file.
    camera_driver_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
        # Find the folder where the 'orbbec_camera' package lives on the robot.
        get_package_share_directory('orbbec_camera'), 'launch'),
         # Inside that folder, look for a file called 'dabai_dcw2.launch.py' and run it.
         '/dabai_dcw2.launch.py'])
    )
    # "dabai" is likely the model name of your camera. This starts the camera driver so the robot can "see".


    # --- PROGRAM 2: THE MATH BRAIN ---
    # Here we define a single ROS 2 Node (a mini-program) to start.
    kin_node = Node(
     package='arm_kin',       # Look in the 'arm_kin' package (Kinematics = the math of robot arm movement).
     executable='kin_srv',   # Find the program inside it called 'kin_srv' (srv = service).
     name='kin_ik_fk',       # Give this running program the nickname 'kin_ik_fk' so other programs can talk to it.
                             # "ik" stands for Inverse Kinematics, "fk" stands for Forward Kinematics!
    )

    
    # --- THE FINAL LIST ---
    # Hand the "Director's Clapperboard" back to ROS 2.
    # It contains a list of everything we just defined: [Turn on the camera, Turn on the math brain]
    return LaunchDescription([camera_driver_launch, kin_node])