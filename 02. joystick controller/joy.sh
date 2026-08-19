#!/bin/bash
# This tells the computer: "I am a Bash terminal script. Run me using the Bash language."

sleep 10
# Pause and do nothing for 10 seconds. 
# Why? When a robot first turns on, it takes a few seconds for the Wi-Fi and internal systems to wake up. 
# We wait 10 seconds to make sure the robot is fully awake before we start giving it commands.

source /opt/ros/humble/setup.bash
# "source" means "load these settings into my current terminal".
# This loads the main ROS 2 (Humble) toolbox. Without this, the terminal doesn't know what "ros2" means.

source /home/jetson/yahboomcar_ws/install/setup.bash
# This loads the specific toolbox for the Yahboom robot. 
# It tells the robot where to find the custom code Yahboom wrote (like the yahboomcar_ctrl stuff).

source /home/jetson/M3Pro_ws/install/setup.bash
# This loads another toolbox, specifically for the M3Pro controller hardware.

export ROS_DOMAIN_ID=30
# This is a VERY important ROS 2 concept! 
# Think of ROS_DOMAIN_ID like a walkie-talkie channel. 
# By setting it to 30, you are telling the robot: "Only communicate on channel 30."
# If you had two robots in the same room, you'd set one to channel 30 and the other to channel 31 
# so they don't accidentally send driving commands to each other!

gnome-terminal -- bash -c "cd ~/joy_control && /usr/bin/python3 start_joy_controller.py; exec bash"
# This is the final boss of the script! Let's break it down into pieces:
# 
# gnome-terminal --      -> Opens a brand new, visual terminal window on the screen.
# bash -c "..."          -> Tells that new window to run the commands inside the quotes.
# cd ~/joy_control       -> Go into the folder called 'joy_control' located in the home directory.
# &&                     -> "If the previous command worked, THEN do the next thing."
# /usr/bin/python3 ...   -> Run the Python script! (This is the exact Python file you showed me earlier!)
# ; exec bash            -> When the Python script finishes or crashes, keep the terminal window open 
#                           instead of instantly closing it, so you can see any error messages.