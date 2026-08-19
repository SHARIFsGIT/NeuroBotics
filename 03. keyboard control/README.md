sh start_agent.sh

ros2 run yahboomcar_ctrl yahboom_keyboard

ros2 run rqt_graph rqt_graph

ros2 topic echo /cmd_vel

ros2 topic info /cmd_vel