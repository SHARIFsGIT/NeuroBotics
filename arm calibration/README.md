ros2 topic pub /arm6_joints arm_msgs/msg/ArmJoints {"joint1: 90, joint2: 90, joint3: 90, joint4: 90, joint5: 90, joint6: 180, time: 1500"} --once


python3 ~/calibrate_arm.py


sh start_agent.sh


ros2 launch M3Pro_demo camera_arm_kin.launch.py


ros2 run M3Pro_demo arm_offset