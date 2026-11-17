"""Exercise manipulation callbacks against mocked ROS topics, services and clocks.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX (no actuator access).
"""

from concurrent.futures import Future
import importlib.util
import json
from pathlib import Path
import sys
import time
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest


class Publisher:
    """Capture topic messages with an explicitly connected mock subscriber."""

    def __init__(self) -> None:
        """Initialize a bounded test's capture buffer."""
        self.messages = []

    def publish(self, message: Any) -> None:
        """Capture a published message instead of accessing a ROS graph."""
        self.messages.append(message)

    def get_subscription_count(self) -> int:
        """Report an available mocked driver."""
        return 1


class FakeNode:
    """Model the Node surface used by manipulation without spinning ROS."""

    def __init__(self, name: str) -> None:
        """Create parameter and topic stores for a named mock node."""
        self.params = {}
        self.publishers = {}
        self.subscribers = {}
        self.client = SimpleNamespace(service_is_ready=lambda: True,
                                      call_async=lambda request: Future())

    def declare_parameter(self, name: str, value: Any) -> Any:
        """Store a parameter default."""
        self.params[name] = value
        return SimpleNamespace(value=value)

    def get_parameter(self, name: str) -> Any:
        """Return a parameter from the test configuration."""
        return SimpleNamespace(value=self.params[name])

    def create_subscription(self, cls: type, topic: str, callback: Any, qos: int) -> Any:
        """Capture topic callback registration."""
        self.subscribers[topic] = callback
        return None

    def create_publisher(self, cls: type, topic: str, qos: int) -> Publisher:
        """Create a capture publisher."""
        self.publishers[topic] = Publisher()
        return self.publishers[topic]

    def create_client(self, cls: type, service: str) -> Any:
        """Provide a mock asynchronous IK client."""
        return self.client

    def create_timer(self, period: float, callback: Any) -> None:
        """Keep tests in control of time and callback execution."""

    def get_logger(self) -> Any:
        """Provide structured-log sinks."""
        return SimpleNamespace(info=lambda text: None, warning=lambda text: None)

    def get_clock(self) -> Any:
        """Return a deterministic ROS clock at ten seconds."""
        from rclpy.time import Time
        return SimpleNamespace(now=lambda: Time(seconds=10.0))

    def destroy_node(self) -> None:
        """Release no hardware resources in this mock."""


@pytest.fixture
def node(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Load real manipulation callbacks with only external ROS/hardware boundaries mocked."""
    import rclpy.node
    import tf2_ros
    from geometry_msgs.msg import PoseStamped
    monkeypatch.setattr(rclpy.node, 'Node', FakeNode)
    monkeypatch.setattr(tf2_ros, 'Buffer', lambda: SimpleNamespace())
    monkeypatch.setattr(tf2_ros, 'TransformListener', lambda *args, **kwargs: None)
    for name in ('arm_interface', 'arm_interface.msg', 'arm_interface.srv',
                 'arm_msgs', 'arm_msgs.msg'):
        monkeypatch.setitem(sys.modules, name, ModuleType(name))
    sys.modules['arm_interface.msg'].CurJoints = SimpleNamespace
    sys.modules['arm_interface.srv'].ArmKinemarics = SimpleNamespace(Request=SimpleNamespace)
    sys.modules['arm_msgs.msg'].ArmJoint = SimpleNamespace
    sys.modules['arm_msgs.msg'].ArmJoints = SimpleNamespace
    path = Path(__file__).parents[1] / 'eira_manipulation' / 'grasp_executor.py'
    spec = importlib.util.spec_from_file_location('_eira_mock_manipulation', path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    instance = module.GraspExecutor()
    instance._test_module = module
    target = PoseStamped()
    target.header.frame_id = 'base_link'
    target.header.stamp.sec = 10
    target.pose.position.x = 0.19
    instance._on_target_pose(target)
    instance._on_cur_joints(SimpleNamespace(joints=[90, 140, 20, 10, 90, 90]))
    return instance


def message(payload: Any) -> Any:
    """Wrap JSON data in a mocked String message."""
    return SimpleNamespace(data=json.dumps(payload))


def test_wrong_frame_and_old_measurement_are_ignored(node: Any) -> None:
    """Invalid frames and delayed images must not refresh PID target freshness."""
    from geometry_msgs.msg import PoseStamped
    accepted = node._target
    wrong = PoseStamped()
    wrong.header.frame_id, wrong.header.stamp.sec = 'camera', 10
    node._on_target_pose(wrong)
    wrong.header.frame_id, wrong.header.stamp.sec = 'base_link', 1
    node._on_target_pose(wrong)
    assert node._target is accepted


def test_stop_holds_feedback_and_invalidates_old_ik(node: Any) -> None:
    """A delayed old service reply must never restart motion after stop/new grasp."""
    node._state = node.WAIT_IK
    node.params['joint_feedback_is_measured'] = True
    token = (node._generation, node._ik_id)
    response = Future()
    response.set_result(SimpleNamespace(joint1=90, joint2=90, joint3=20, joint4=10))
    node._stop()
    assert node._six_pub.messages[-1].joint2 == 140
    node._state = node.WAIT_IK
    node._on_ik_response(response, token)
    assert node._steps == []
    assert node._state == node.WAIT_IK


def test_stop_without_feedback_reports_hold_unavailable(node: Any) -> None:
    """Never invent a hold pose from a stale command or configured home position."""
    node._feedback_time = None
    node._stop()
    event = json.loads(node._event_pub.messages[-1].data)
    assert event['arm_hold_sent'] is False
    assert node._six_pub.messages == []


def test_unverified_curjoints_provenance_cannot_command_hold(node: Any) -> None:
    """Desired-pose Curjoints publishers must never masquerade as measured servo feedback."""
    node._stop()
    assert not node._six_pub.messages
    assert json.loads(node._event_pub.messages[-1].data)['arm_hold_sent'] is False


def test_ik_timeout_has_finite_retry_budget(node: Any) -> None:
    """One bounded retry is followed by a correlated failure."""
    node._mission_id, node._action_id = 'm', '2:0'
    node._state = node.WAIT_IK
    node._ik_request = SimpleNamespace()
    node._ik_retries_left = 1
    node._deadline = 0.0
    node._tick()
    assert node._state == node.WAIT_IK
    node._deadline = 0.0
    node._tick()
    event = json.loads(node._event_pub.messages[-1].data)
    assert event['event'] == 'failed'
    assert event['mission_id'] == 'm'
    assert node._state == node.IDLE


def test_release_waits_for_runtime_and_feedback(node: Any) -> None:
    """Home cannot interrupt a gripper command and elapsed time alone cannot verify it."""
    node._request = {}
    node._start_release()
    started = time.monotonic()
    node._tick_sequence(started)
    assert len(node._six_pub.messages) == 1
    node._tick_sequence(started + 3.0)
    assert len(node._single_pub.messages) == 0  # No post-command feedback yet.
    node._feedback_time = started + 0.1
    node._cur_joints = list(node._transport_joints)
    node._tick_sequence(started + 3.0)
    assert len(node._single_pub.messages) == 1
    node._tick_sequence(started + 4.5)
    assert len(node._six_pub.messages) == 1  # Gripper's two-second runtime is incomplete.


def test_nonobject_vision_event_is_ignored(node: Any) -> None:
    """Malformed external JSON must not escape callback boundaries."""
    node._on_vision_event(message([]))
    assert node._metadata == {}


def test_completed_command_is_not_reexecuted(node: Any) -> None:
    """Repeated correlated requests return cached completion without actuator traffic."""
    node._completed[('m', '1:0')] = {'event': 'homed', 'mission_id': 'm', 'action_id': '1:0'}
    node._on_request(message({'mission_id': 'm', 'action_id': '1:0', 'command': 'home'}))
    assert node._state == node.IDLE
    assert node._six_pub.messages == []
    assert json.loads(node._event_pub.messages[-1].data)['event'] == 'homed'


def test_sorting_requires_calibrated_destination(node: Any) -> None:
    """Unknown sorting destinations fail before servo commands."""
    node._request = {'color': 'red'}
    node._start_release()
    assert json.loads(node._event_pub.messages[-1].data)['event'] == 'failed'
    assert not node._steps


def test_thumb_down_cancels_and_ok_confirms_only_waiting_grasp(node: Any) -> None:
    """Gesture commands pass through the same stop/confirmation state machine."""
    node._state = node.WAIT_CONFIRM
    node._on_gesture(message({'gesture': 'OK'}))
    assert node._state == node.ALIGN
    node._on_gesture(message({'gesture': 'Thumb_down'}))
    assert node._state == node.IDLE


def test_stale_acquisition_loss_does_not_abort_new_target(node: Any) -> None:
    """Mission identity alone is insufficient when one mission acquires several objects."""
    node._mission_id = 'm'
    node._metadata = {'mission_id': 'm', 'action_id': 'new-find'}
    node._state = node.ALIGN
    node._on_vision_event(message({'event': 'lost', 'mission_id': 'm', 'action_id': 'old-find'}))
    assert node._state == node.ALIGN


def test_stale_gesture_cannot_confirm_next_grasp(node: Any) -> None:
    """A delayed OK event for a previous action cannot acknowledge a new grasp."""
    node._mission_id, node._action_id = 'm', 'new-grasp'
    node._state = node.WAIT_CONFIRM
    node._on_gesture(message({'gesture': 'OK', 'mission_id': 'm', 'action_id': 'old-grasp'}))
    assert node._state == node.WAIT_CONFIRM


def test_old_target_pose_cannot_satisfy_new_found_context(node: Any) -> None:
    """Cross-topic reordering must not associate a prior object's pose with a new acquisition."""
    node._mission_id = 'm'
    node._metadata = {'mission_id': 'm', 'measurement_stamp_ns': 10000000001}
    assert node._target_stale()
