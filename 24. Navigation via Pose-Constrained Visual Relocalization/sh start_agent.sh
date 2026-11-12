#!/bin/bash
# Tells the computer this is a Bash terminal script.

# ---------------------------------------------------------
# THESE ARE COMMENTED OUT (DISABLED) ALTERNATIVE OPTIONS
# The '#' symbol means "ignore this line". 
# The programmer left these here as notes on how to run the translator using Docker (a tool for running apps in containers).
# ---------------------------------------------------------
# WIFI
#docker run -it --rm -v /dev:/dev -v /dev/shm:/dev/shm --privileged --net=host microros/micro-ros-agent:humble udp4 --port 8090 -v4
# This disabled line shows how you could start the translator using Wi-Fi (udp4) instead of a wire.

# serial
#docker run -it --rm -v /dev:/dev -v /dev/shm:/dev/shm --privileged --net=host 192.168.2.51:5000/micro-ros-agent:humble serial --dev /dev/myserial -b 2000000 -v4
# This disabled line shows how to start it using Docker over a serial (USB) wire.

# serial
#docker start -i 7026de7b7d9b
#docker stop 7026de7b7d9b
# These disabled lines show how to start/stop a specific Docker container using its ID number.
# ---------------------------------------------------------


sleep 5
# Pause for 5 seconds when the robot turns on. 
# This gives the hardware time to wake up before we ask the translator to start working.

gnome-terminal --title=mircoROS_Agent -- bash -c "export ROS_DOMAIN_ID=30 && source /opt/ros/humble/setup.bash && source /home/jetson/mircoROS_agent/install/setup.bash && ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/myserial -b 2000000"
# This is the main event! Let's break down what is inside the quotes:
#
# gnome-terminal --title=mircoROS_Agent --  
# Opens a new terminal window on the screen and names it "mircoROS_Agent".
#
# bash -c "..."  
# Tells the new terminal window to run all the commands inside the quotes.
#
# export ROS_DOMAIN_ID=30  
# Set the walkie-talkie channel to 30! (Just like in the previous script, so all programs talk on the same channel).
#
# &&  
# Means "AND THEN DO THIS NEXT THING".
#
# source /opt/ros/humble/setup.bash  
# Load the main ROS 2 toolbox.
#
# source /home/jetson/mircoROS_agent/install/setup.bash  
# Load the specific micro-ROS Agent toolbox that was installed on this Jetson computer.
#
# ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/myserial -b 2000000  
# FINALLY! Start the translator. 
# "serial" means we are talking over a physical wire (USB), not Wi-Fi.
# "--dev /dev/myserial" tells it exactly which USB port the robotic arm is plugged into.
# "-b 2000000" sets the speed limit (baud rate) of the wire to 2,000,000 bits per second. 
# (That is a very fast data speed, which makes sense because robotic arms need to send a lot of joint data very quickly!)