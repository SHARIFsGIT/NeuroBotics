"""Test bounded navigation recovery without ROS transport or robot movement.

Author: E-AIRA contributors.
Hardware target: mocked ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
"""

from concurrent.futures import Future
import json
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from builtin_interfaces.msg import Time
from geometry_msgs.msg import PoseWithCovarianceStamped
from std_msgs.msg import String

from eira_brain import llm_task_planner as planner_module
from eira_brain.llm_task_planner import LLMTaskPlanner


@pytest.fixture
def recovery_brain() -> LLMTaskPlanner:
    """Create a planner with observable publishers and no active DDS participant.

    Returns:
        Planner with explicit navigation and localization parameter defaults.
    """
    node = object.__new__(LLMTaskPlanner)
    node._mission_lock = threading.RLock()
    node._generation = 1
    node._mission_id = 'navigation-test'
    node._command = 'go home'
    node._action_id = '0:1'
    node._attempt = 0
    node._state = node.EXECUTING
    node._closing = False
    node._plan = [{'action': 'navigate', 'target': 'home'}]
    node._plan_idx = 0
    node._plan_seq = 1
    node._retries_stamp = None
    node._nav_generation = 1
    node._nav_token = None
    node._nav_handles = {}
    node._nav_result = None
    node._nav_goal_handle = None
    node._pending_nav_waypoint = None
    node._nav_discovery_deadline = None
    node._nav_resume_at = None
    node._amcl_pose = None
    node._amcl_received_at = None
    node._mission_queue = []
    node._motion_owner = 'none'
    node._found_context = {}
    node._planner_source = 'fallback'
    node._deadline = None
    node._retries_left = 0
    node._retry_count = 0
    node._scan_count_total = 0
    node._scans_done = 0
    node._scan_until = None
    node._last_target_pub = 0.0
    node._last_vision_event = None
    node._last_manip_event = None
    node._active_action = None
    node._active_vision_request = None
    node._mission_started_at = 100.0
    node._map_frame = 'map'
    node._waypoints = {'home': {'x': 0.0, 'y': 0.0, 'yaw': 0.0}}
    node._clock = SimpleNamespace(now=lambda: SimpleNamespace(
        nanoseconds=100_000_000_000, to_msg=lambda: Time(sec=100, nanosec=0)))
    node.get_clock = Mock(return_value=node._clock)
    node._test_parameters = {
        'sound_feedback': False,
        'action_retries': 1, 'nav_retries': 2, 'nav_settle_s': 3.0,
        'nav_retry_delay_s': 10.0, 'nav_timeout_s': 300.0,
        'find_timeout_s': 25.0, 'grasp_timeout_s': 90.0, 'misc_timeout_s': 15.0,
        'target_republish_s': 1.0, 'nav_server_wait_s': 5.0,
        'amcl_check_enabled': True, 'amcl_xy_variance_max': 0.5,
        'amcl_yaw_variance_max': 0.4, 'amcl_pose_timeout_s': 15.0,
    }
    node.get_parameter = Mock(side_effect=lambda name: SimpleNamespace(
        value=node._test_parameters[name]))
    node.get_logger = Mock(return_value=Mock())
    for name in ('_plan_pub', '_status_pub', '_vision_target_pub', '_manip_req_pub',
                 '_cmd_vel_pub', '_owner_pub', '_beep_pub', '_heartbeat_pub'):
        setattr(node, name, Mock())
    node._nav_client = Mock()
    return node


def amcl_message(xy_variance: float = 0.05, yaw_variance: float = 0.03,
                 frame: str = 'map') -> PoseWithCovarianceStamped:
    """Create an AMCL observation using explicit planar covariance and ROS time.

    Args:
        xy_variance: Variance on both planar translation axes, in square metres.
        yaw_variance: Heading variance in square radians.
        frame: Global frame reported by localization.

    Returns:
        Pose observation with a unit quaternion and a nonzero timestamp.
    """
    message = PoseWithCovarianceStamped()
    message.header.frame_id = frame
    message.header.stamp.sec = 100
    message.pose.pose.orientation.w = 1.0
    covariance = [0.0] * 36
    covariance[0] = covariance[7] = xy_variance
    covariance[35] = yaw_variance
    message.pose.covariance = covariance
    return message


def test_success_waits_three_seconds_without_blocking(
        recovery_brain: LLMTaskPlanner, monkeypatch: pytest.MonkeyPatch) -> None:
    """Successful navigation releases motion and delays the next logical step.

    Args:
        recovery_brain: Planner with mocked hardware interfaces.
        monkeypatch: Fixture controlling time and detecting blocking sleeps.
    """
    node = recovery_brain
    now = [100.0]
    monkeypatch.setattr(time, 'monotonic', lambda: now[0])
    monkeypatch.setattr(time, 'sleep', Mock(side_effect=AssertionError('blocking sleep')))
    node._send_nav_goal = Mock(return_value=True)
    node._dispatch_next_action()
    node._nav_result = 4
    node._check_nav()
    assert node._state == node.NAV_SETTLE
    assert node._nav_resume_at == 103.0
    assert node._motion_owner == 'none'
    assert node._plan_idx == 0
    assert node._active_action is None
    now[0] = 102.99
    node._check_nav_delay()
    assert node._state == node.NAV_SETTLE
    assert node._plan_idx == 0
    now[0] = 103.0
    node._check_nav_delay()
    assert node._state == node.EXECUTING
    assert node._plan_idx == 1
    events = [json.loads(call.args[0].data) for call in node._status_pub.publish.call_args_list]
    finished = [event for event in events if event.get('event') == 'action_finished']
    assert len(finished) == 1
    assert finished[0]['success'] is True
    assert finished[0]['duration_s'] == 0.0


@pytest.mark.parametrize('state', ['NAV_SETTLE', 'NAV_RETRY_WAIT'])
def test_stop_clears_delayed_navigation(
        recovery_brain: LLMTaskPlanner, monkeypatch: pytest.MonkeyPatch, state: str) -> None:
    """An explicit stop cannot leave a timer that dispatches an old navigation.

    Args:
        recovery_brain: Planner with mocked hardware interfaces.
        monkeypatch: Fixture controlling elapsed time.
        state: Recovery state interrupted by the stop command.
    """
    node = recovery_brain
    monkeypatch.setattr(time, 'monotonic', lambda: 100.0)
    node._state = state
    node._nav_resume_at = 110.0
    node._mission_queue = [('go home', 'queued')]
    node._send_nav_goal = Mock(return_value=True)
    node._on_command(String(data='stop'))
    assert node._state == node.IDLE
    assert node._nav_resume_at is None
    assert node._mission_queue == []
    monkeypatch.setattr(time, 'monotonic', lambda: 120.0)
    node._tick()
    node._send_nav_goal.assert_not_called()


@pytest.mark.parametrize('state', ['NAV_SETTLE', 'NAV_RETRY_WAIT'])
def test_heartbeat_remains_available_during_recovery(
        recovery_brain: LLMTaskPlanner, state: str) -> None:
    """Recovery delays retain zero motion ownership while renewing liveness.

    Args:
        recovery_brain: Planner with observable heartbeat and ownership outputs.
        state: Recovery state that must not block the heartbeat callback.
    """
    node = recovery_brain
    node._state = state
    node._publish_heartbeat()
    node._heartbeat_pub.publish.assert_called_once()
    owner = json.loads(node._owner_pub.publish.call_args.args[0].data)
    assert owner['owner'] == 'none'


def test_navigation_has_two_delayed_retries_then_fails(
        recovery_brain: LLMTaskPlanner, monkeypatch: pytest.MonkeyPatch) -> None:
    """Three failed attempts exhaust navigation without resetting its retry budget.

    Args:
        recovery_brain: Planner with explicit navigation retry parameters.
        monkeypatch: Fixture advancing recovery time deterministically.
    """
    node = recovery_brain
    now = [100.0]
    monkeypatch.setattr(time, 'monotonic', lambda: now[0])
    node._send_nav_goal = Mock(return_value=True)
    for attempt in range(3):
        node._dispatch_next_action()
        assert node._attempt == attempt + 1
        assert node._retries_left == 2 - attempt
        node._action_failed('navigation status 6')
        if attempt < 2:
            assert node._state == node.NAV_RETRY_WAIT
            assert node._nav_resume_at == now[0] + 10.0
            now[0] += 9.99
            node._check_nav_delay()
            assert node._state == node.NAV_RETRY_WAIT
            now[0] += 0.01
            node._check_nav_delay()
            assert node._state == node.EXECUTING
    assert node._state == node.IDLE
    assert node._send_nav_goal.call_count == 3
    events = [json.loads(call.args[0].data) for call in node._status_pub.publish.call_args_list]
    assert sum(event.get('event') == 'recovery' for event in events) == 2
    assert events[-1]['event'] == 'mission_finished'
    assert events[-1]['success'] is False


def test_other_actions_keep_their_original_retry_budget(
        recovery_brain: LLMTaskPlanner) -> None:
    """Increasing navigation retries does not multiply grasp or find attempts.

    Args:
        recovery_brain: Planner whose navigation and generic budgets differ.
    """
    node = recovery_brain
    node._plan = [{'action': 'find', 'target': 'cup'}]
    node._dispatch_next_action()
    assert node._state == node.WAIT_FIND
    assert node._retries_left == 1


def test_retry_wait_does_not_consume_new_navigation_timeout(
        recovery_brain: LLMTaskPlanner, monkeypatch: pytest.MonkeyPatch) -> None:
    """Each navigation gets its full execution budget after the recovery delay.

    Args:
        recovery_brain: Planner with a 300-second navigation execution budget.
        monkeypatch: Fixture controlling the retry delay.
    """
    node = recovery_brain
    now = [100.0]
    monkeypatch.setattr(time, 'monotonic', lambda: now[0])
    node._send_nav_goal = Mock(return_value=True)
    node._dispatch_next_action()
    assert node._deadline == 400.0
    node._action_failed('navigation status 6')
    now[0] = 110.0
    node._check_nav_delay()
    node._dispatch_next_action()
    assert node._deadline == 410.0


def test_fresh_low_covariance_passes(
        recovery_brain: LLMTaskPlanner, monkeypatch: pytest.MonkeyPatch) -> None:
    """A current measured map-frame covariance passes the convergence heuristic.

    Args:
        recovery_brain: Planner with an empty localization cache.
        monkeypatch: Fixture fixing receipt time.
    """
    monkeypatch.setattr(time, 'monotonic', lambda: 100.0)
    recovery_brain._on_amcl_pose(amcl_message())
    assert recovery_brain._check_amcl_convergence() is True


@pytest.mark.parametrize('xy,yaw', [(0.51, 0.03), (0.05, 0.41)])
def test_high_covariance_warns(
        recovery_brain: LLMTaskPlanner, monkeypatch: pytest.MonkeyPatch,
        xy: float, yaw: float) -> None:
    """Excessive translation or heading uncertainty emits the requested warning.

    Args:
        recovery_brain: Planner with explicit covariance thresholds.
        monkeypatch: Fixture fixing receipt time.
        xy: Reported translation variance.
        yaw: Reported heading variance.
    """
    monkeypatch.setattr(time, 'monotonic', lambda: 100.0)
    recovery_brain._on_amcl_pose(amcl_message(xy, yaw))
    assert recovery_brain._check_amcl_convergence() is False
    warnings = recovery_brain.get_logger().warning.call_args_list
    assert any('AMCL uncertainty high, navigation may fail' in str(call.args[0])
               for call in warnings)


@pytest.mark.parametrize('xy,yaw,frame', [
    (float('nan'), 0.03, 'map'),
    (0.05, float('inf'), 'map'),
    (-0.01, 0.03, 'map'),
    (0.05, 0.03, 'odom'),
])
def test_invalid_localization_is_not_converged(
        recovery_brain: LLMTaskPlanner, monkeypatch: pytest.MonkeyPatch,
        xy: float, yaw: float, frame: str) -> None:
    """Wrong-frame or invalid variance cannot masquerade as healthy localization.

    Args:
        recovery_brain: Planner with localization checks enabled.
        monkeypatch: Fixture fixing receipt time.
        xy: Translation variance under test.
        yaw: Heading variance under test.
        frame: Localization frame under test.
    """
    monkeypatch.setattr(time, 'monotonic', lambda: 100.0)
    recovery_brain._on_amcl_pose(amcl_message(xy, yaw, frame))
    assert recovery_brain._check_amcl_convergence() is False


def test_missing_and_stale_localization_are_reported(
        recovery_brain: LLMTaskPlanner, monkeypatch: pytest.MonkeyPatch) -> None:
    """Absence and expiry of evidence are distinguished from convergence.

    Args:
        recovery_brain: Planner with a 15-second localization age limit.
        monkeypatch: Fixture advancing time after one healthy observation.
    """
    now = [100.0]
    monkeypatch.setattr(time, 'monotonic', lambda: now[0])
    assert recovery_brain._check_amcl_convergence() is False
    recovery_brain._on_amcl_pose(amcl_message())
    now[0] = 116.0
    assert recovery_brain._check_amcl_convergence() is False


def test_external_localization_can_disable_amcl_checks(
        recovery_brain: LLMTaskPlanner) -> None:
    """Alternative localization stacks can explicitly opt out of AMCL diagnostics.

    Args:
        recovery_brain: Planner without an AMCL observation.
    """
    recovery_brain._test_parameters['amcl_check_enabled'] = False
    assert recovery_brain._check_amcl_convergence() is True


@pytest.mark.parametrize('stamp', [0, 80, 101])
def test_old_or_invalid_sensor_stamp_cannot_be_refreshed_by_receipt(
        recovery_brain: LLMTaskPlanner, monkeypatch: pytest.MonkeyPatch, stamp: int) -> None:
    """New DDS receipt does not make an old, unstamped or future pose current.

    Args:
        recovery_brain: Planner whose ROS clock is at 100 seconds.
        monkeypatch: Fixture holding the local receipt time constant.
        stamp: Producer timestamp that must fail the sensor freshness check.
    """
    monkeypatch.setattr(time, 'monotonic', lambda: 100.0)
    message = amcl_message()
    message.header.stamp.sec = stamp
    recovery_brain._on_amcl_pose(message)
    assert recovery_brain._check_amcl_convergence() is False


def test_covariance_at_threshold_is_accepted(
        recovery_brain: LLMTaskPlanner, monkeypatch: pytest.MonkeyPatch) -> None:
    """Configured maximum variances are inclusive rather than requiring zero error.

    Args:
        recovery_brain: Planner with explicit translation and yaw limits.
        monkeypatch: Fixture fixing receipt time.
    """
    monkeypatch.setattr(time, 'monotonic', lambda: 100.0)
    recovery_brain._on_amcl_pose(amcl_message(xy_variance=0.5, yaw_variance=0.4))
    assert recovery_brain._check_amcl_convergence() is True


def test_uncertain_amcl_warns_before_goal_without_blocking(
        recovery_brain: LLMTaskPlanner, monkeypatch: pytest.MonkeyPatch) -> None:
    """Covariance diagnostics do not create an unbounded dispatch deadlock.

    Args:
        recovery_brain: Planner with a ready mocked Nav2 server.
        monkeypatch: Fixture supplying a portable action goal and current time.
    """
    node = recovery_brain
    monkeypatch.setattr(time, 'monotonic', lambda: 100.0)
    monkeypatch.setattr(planner_module, 'NavigateThroughPoses', SimpleNamespace(
        Goal=lambda: SimpleNamespace(poses=[])))
    node._nav_client.server_is_ready.return_value = True
    node._nav_client.send_goal_async.return_value = Future()
    node._on_amcl_pose(amcl_message(xy_variance=1.0))
    node._dispatch_next_action()
    assert node._state == node.WAIT_NAV
    node._nav_client.send_goal_async.assert_called_once()
    warnings = node.get_logger().warning.call_args_list
    assert any('AMCL uncertainty high, navigation may fail' in str(call.args[0])
               for call in warnings)


def test_late_acceptance_is_canceled_during_retry_wait(
        recovery_brain: LLMTaskPlanner) -> None:
    """A delayed acceptance cannot acquire motion during recovery.

    Args:
        recovery_brain: Planner paused before a new navigation attempt.
    """
    node = recovery_brain
    node._state = node.NAV_RETRY_WAIT
    node._nav_token = None
    handle = Mock(accepted=True)
    future = Future()
    future.set_result(handle)
    node._on_goal_response(future, (1, 1))
    handle.cancel_goal_async.assert_called_once()
    assert node._nav_handles == {}
