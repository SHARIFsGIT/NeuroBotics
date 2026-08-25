# --- IMPORTING ROS 2 LAUNCH TOOLS ---
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    # Hand the list of programs back to ROS 2 to start.
    return LaunchDescription([
      
        # --- THE LASER FILTER NODE ---
        Node(
            package='yahboom_laser_filter',        # Look in the Yahboom custom filter package
            executable='laser_filter_node',        # Find the program that does the filtering
            name='laser_filter_node',              # Give it this name in the ROS 2 network
            
            # Parameters are settings we give to the program. 
            # Here, we are telling the filter to only keep laser data between -180 and +180 degrees.
            # (This represents a full 360-degree circle! -180 is backward, 0 is right, 180 is backward again).
            # If your robot had a blind spot (like the arm blocking the back), you might change this 
            # to something like {'angle_min': -90.0, 'angle_max': 90.0} to only look forward!
            parameters=[
                {'angle_min': -180.0, 'angle_max': 180.0},  
            ]
        )
    ])