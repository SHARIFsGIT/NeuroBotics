"""Verify dynamic fetch intent and the captured return pose without robot motion."""

import json
import math
import time
from unittest.mock import Mock

import pytest
from geometry_msgs.msg import TransformStamped

from eira_brain.ollama_client import MISSION_START, OllamaError
from test_mission_safety import brain  # noqa: F401
from test_navigation_recovery import amcl_message, recovery_brain  # noqa: F401


@pytest.mark.parametrize("target", ["banana", "blue wine glass", "cell phone", "orange"])
def test_fetch_preserves_requested_class(brain, target):
    brain._waypoints["lab_table"] = {"x": 3.0, "y": 2.0, "yaw": 0.0}
    plan = brain._fallback_plan(f"bring me a {target} from the lab table")
    assert plan == [
        {"action": "navigate", "target": "lab_table"},
        {"action": "find", "target": target}, {"action": "grasp"},
        {"action": "navigate", "target": MISSION_START}, {"action": "release"},
    ]
    assert brain._validate_command_plan(
        f"bring me a {target} from lab table", plan, ("lab_table", MISSION_START))[0] == plan


@pytest.mark.parametrize("mutation", ["object", "source", "order", "return", "missing", "extra"])
def test_valid_actions_cannot_change_fetch_intent(brain, mutation):
    brain._waypoints["kitchen"] = {"x": 3.0, "y": 2.0, "yaw": 0.0}
    command = "bring banana from kitchen"
    plan = brain._fallback_plan(command)
    if mutation == "object":
        plan[1]["target"] = "cup"
    elif mutation == "source":
        plan[0]["target"] = "home"
    elif mutation == "order":
        plan[0], plan[1] = plan[1], plan[0]
    elif mutation == "return":
        plan[3]["target"] = "home"
    elif mutation == "missing":
        plan.pop()
    else:
        plan.append({"action": "navigate", "target": "home"})
    validated, reason = brain._validate_command_plan(
        command, plan, ("home", "kitchen", MISSION_START))
    assert validated is None and reason


def test_no_localization_rejects_fetch_before_dispatch(brain):
    brain._waypoints["kitchen"] = {"x": 3.0, "y": 2.0, "yaw": 0.0}
    brain._ollama = Mock()
    brain._ollama.generate_plan.side_effect = OllamaError("offline")
    brain._plan_worker("bring cup from kitchen", 1)
    payload = json.loads(brain._plan_pub.publish.call_args.args[0].data)
    assert payload["actions"] == []
    assert "initial robot pose unavailable or stale" in payload["reason"]
    assert brain._state == brain.IDLE
    brain._vision_target_pub.publish.assert_not_called()
    brain._nav_client = Mock()
    brain._nav_client.send_goal_async.assert_not_called()


def test_wrong_llm_object_repairs_then_falls_back_to_requested_object(brain):
    brain._mission_start_pose = {"x": 5.0, "y": -1.0, "yaw": 0.4}
    brain._waypoints["kitchen"] = {"x": 3.0, "y": 2.0, "yaw": 0.0}
    command = "bring banana from kitchen"
    wrong = brain._fallback_plan(command)
    wrong[1]["target"] = "cup"
    brain._ollama = Mock()
    brain._ollama.generate_plan.return_value = json.dumps(wrong)
    brain._plan_worker(command, 1)
    assert brain._ollama.generate_plan.call_count == 2
    assert brain._plan[1]["target"] == "banana"
    assert brain._plan[3]["target"] == MISSION_START
    assert brain._planner_source == "fallback"


def test_start_pose_copies_current_tf_and_normalizes_yaw(recovery_brain):
    node = recovery_brain
    node._test_parameters.update(start_pose_max_age_s=2.0, base_frame="base_link")
    transform = TransformStamped()
    transform.header.frame_id = "map"
    transform.header.stamp.sec = 100
    transform.transform.translation.x, transform.transform.translation.y = 2.0, -3.0
    transform.transform.rotation.z = math.sin(0.3)
    transform.transform.rotation.w = math.cos(0.3)
    node._tf_buffer = Mock()
    node._tf_buffer.lookup_transform.return_value = transform
    captured = node._capture_start_pose()
    assert captured == pytest.approx({"x": 2.0, "y": -3.0, "yaw": 0.6})
    transform.transform.translation.x = 9.0
    assert captured["x"] == 2.0


@pytest.mark.parametrize("stamp,frame,w", [(95, "map", 1.0), (101, "map", 1.0),
                                        (100, "odom", 1.0), (100, "map", 0.0)])
def test_bad_tf_does_not_provide_return_pose(recovery_brain, stamp, frame, w):
    node = recovery_brain
    node._test_parameters.update(start_pose_max_age_s=2.0, base_frame="base_link")
    transform = TransformStamped()
    transform.header.frame_id = frame
    transform.header.stamp.sec = stamp
    transform.transform.rotation.w = w
    node._tf_buffer = Mock()
    node._tf_buffer.lookup_transform.return_value = transform
    assert node._capture_start_pose() is None


def test_fresh_amcl_fallback_captures_start(recovery_brain, monkeypatch):
    node = recovery_brain
    node._test_parameters["start_pose_max_age_s"] = 2.0
    monkeypatch.setattr(time, "monotonic", lambda: 100.0)
    message = amcl_message()
    message.pose.pose.position.x = 4.0
    node._on_amcl_pose(message)
    assert node._capture_start_pose() == {"x": 4.0, "y": 0.0, "yaw": 0.0}


def test_start_capture_happens_when_queue_reserves_next_mission(brain):
    brain._state = brain.IDLE
    brain._mission_queue = [("bring cup from kitchen", "next")]
    brain._load_waypoints = Mock()
    brain._capture_start_pose = Mock(return_value={"x": 4.0, "y": 2.0, "yaw": 0.1})
    brain._spawn_plan_worker = Mock()
    brain._finish_mission()
    brain._capture_start_pose.assert_called_once()
    assert brain._mission_start_pose == {"x": 4.0, "y": 2.0, "yaw": 0.1}
    assert brain._mission_id == "next"


def test_missing_start_cannot_use_colliding_file_waypoint(brain):
    brain._waypoints[MISSION_START] = {"x": 99.0, "y": 99.0, "yaw": 0.0}
    assert MISSION_START not in brain._planning_places()
    assert brain._validate_command_plan("bring cup from home", [])[0] is None


def test_unrecoverable_vision_failure_preserves_details_without_scan(brain):
    brain._state = brain.WAIT_FIND
    brain._plan = [{"action": "find", "target": "banana"}]
    brain._last_target_pub = time.monotonic()
    brain._last_vision_event = {"event": "failed", "reason": "unsupported_target",
                                "detail": "banana is not a label in installed model"}
    brain._begin_scan = Mock()
    brain._check_find()
    brain._begin_scan.assert_not_called()
    payload = json.loads(brain._status_pub.publish.call_args.args[0].data)
    assert "unsupported_target" in payload["error_reason"]
    assert "banana is not a label" in payload["error_reason"]


@pytest.mark.parametrize("suffix", ["come back", "return to the initial position",
                                   "return to starting pose"])
def test_fetch_return_suffix_keeps_start_pose(brain, suffix):
    plan = brain._fallback_plan(f"bring a bottle from the kitchen and {suffix}")
    assert len(plan) == 5
    assert plan[-2] == {"action": "navigate", "target": MISSION_START}


def test_fetch_ignores_trailing_please(brain):
    assert brain._fallback_plan("bring banana from kitchen please")[0]["target"] == "kitchen"


def test_fetch_explicit_home_suffix_remains_named_home(brain):
    command = "bring banana from home then go home"
    plan = brain._fallback_plan(command)
    assert plan[-1] == {"action": "navigate", "target": "home"}
    assert brain._validate_command_plan(command, plan, ("home", MISSION_START))[0] == plan


def test_compound_fetch_after_navigation_is_valid(brain):
    command = "go to home and bring banana from home"
    plan = brain._fallback_plan(command)
    assert brain._validate_command_plan(command, plan, ("home", MISSION_START))[0] == plan


def test_disconnected_vision_reports_missing_node_without_scans(brain):
    brain._state = brain.WAIT_FIND
    brain._plan = [{"action": "find", "target": "banana"}]
    brain._last_target_pub = time.monotonic()
    brain._last_vision_event = None
    brain._deadline = time.monotonic() - 1.0
    brain._vision_target_pub.get_subscription_count.return_value = 0
    brain._begin_scan = Mock()
    brain._check_find()
    brain._begin_scan.assert_not_called()
    payload = json.loads(brain._status_pub.publish.call_args.args[0].data)
    assert "no subscriber on /eira/vision_target" in payload["error_reason"]


def test_model_failure_during_scan_aborts(brain):
    brain._state = brain.SCAN
    brain._last_vision_event = {"event": "failed", "reason": "model_unavailable",
                                "detail": "local weights missing"}
    brain._check_scan()
    assert brain._state == brain.IDLE
    payload = json.loads(brain._status_pub.publish.call_args.args[0].data)
    assert "model_unavailable: local weights missing" in payload["error_reason"]
