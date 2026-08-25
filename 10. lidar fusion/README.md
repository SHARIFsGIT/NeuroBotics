sh start_agent.sh

ros2 launch ira_laser_tools merge_multi.launch.py

rviz2

ros2 launch yahboom_laser_filter laser_filter_node.launch.py

rviz2

ros2 run rqt_graph rqt_graph