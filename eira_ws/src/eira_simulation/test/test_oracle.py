"""Verify explicit oracle provenance, frame geometry and failure behavior.

Author: E-AIRA maintainers.
Hardware target: Gazebo Classic M3 Pro / ROS 2 Humble, no physical robot.
"""

import json
from types import SimpleNamespace
from unittest.mock import Mock

from gazebo_msgs.msg import ModelStates
from geometry_msgs.msg import Pose
from rclpy.time import Time
from std_msgs.msg import String
from pytest import MonkeyPatch

from eira_simulation.perception_oracle import PerceptionOracle


def oracle() -> PerceptionOracle:
    """Create an observed model-state oracle without DDS or actuator interfaces.

    Returns:
        Oracle instance with fresh synthetic Gazebo poses and captured publications.
    """
    node = object.__new__(PerceptionOracle)
    parameters = {'max_range_m': 3.0, 'half_fov_rad': 0.65, 'stale_after_s': 1.0,
                  'robot_name': 'eira_m3pro', 'cup_name': 'cup'}
    node.get_parameter = lambda key: SimpleNamespace(value=parameters[key])
    node.get_clock = lambda: SimpleNamespace(now=lambda: Time(seconds=100))
    node.get_logger = Mock(return_value=Mock())
    node._request = {'mission_id': 'sim', 'action_id': '0:1', 'target': 'red cup'}
    node._announced = False
    node._seen = 100.0
    node._pose, node._events = Mock(), Mock()
    models = ModelStates()
    models.name = ['eira_m3pro', 'cup']
    robot, cup = Pose(), Pose()
    robot.orientation.w = cup.orientation.w = 1.0
    robot.position.x = -1.5
    cup.position.x, cup.position.z = 0.8, 0.56
    models.pose = [robot, cup]
    node._models = models
    return node


def test_oracle_event_is_explicitly_labeled_and_correlated(monkeypatch: MonkeyPatch) -> None:
    """Simulation ground truth never masquerades as a learned detector's output."""
    node = oracle()
    monkeypatch.setattr('eira_simulation.perception_oracle.time.monotonic', lambda: 100.1)
    node._tick()
    pose = node._pose.publish.call_args.args[0]
    assert pose.header.frame_id == 'base_link'
    assert pose.pose.position.x == 2.3
    event = json.loads(node._events.publish.call_args.args[0].data)
    assert event['mission_id'] == 'sim' and event['action_id'] == '0:1'
    assert event['ground_truth'] is True
    assert event['source'] == 'simulation_ground_truth'
    assert 'object_contact_verified' not in event


def test_oracle_cannot_find_a_different_colored_object(monkeypatch: MonkeyPatch) -> None:
    """A requested blue cup cannot be satisfied by the known red simulated cup."""
    node = oracle()
    node._on_request(String(data=json.dumps({**node._request, 'target': 'blue cup'})))
    monkeypatch.setattr('eira_simulation.perception_oracle.time.monotonic', lambda: 100.1)
    node._tick()
    node._pose.publish.assert_not_called()
    node._events.publish.assert_not_called()


def test_frozen_model_states_emit_loss(monkeypatch: MonkeyPatch) -> None:
    """An oracle also stops target updates when its actual source freezes."""
    node = oracle()
    node._announced = True
    monkeypatch.setattr('eira_simulation.perception_oracle.time.monotonic', lambda: 102.0)
    node._tick()
    node._pose.publish.assert_not_called()
    assert json.loads(node._events.publish.call_args.args[0].data)['event'] == 'lost'
