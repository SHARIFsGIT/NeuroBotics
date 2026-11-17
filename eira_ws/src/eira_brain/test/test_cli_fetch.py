"""Check CLI fetch grounding and the real callback bridge without physical motion."""

import json
import math
from collections import OrderedDict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from eira_brain import eira_cli
from eira_brain import llm_task_planner
from eira_brain.eira_cli import preview_plan
from eira_brain.ollama_client import MISSION_START, OllamaClient, OllamaError
from test_mission_safety import brain  # noqa: F401 -- shared mocked ROS fixture


@pytest.fixture
def places(tmp_path: Path) -> Path:
    """Use a measured-place fixture with no saved home waypoint."""
    path = tmp_path / "waypoints.yaml"
    path.write_text("frame: map\nwaypoints:\n  lab_desk: {x: 3, y: -1, yaw: 0}\n")
    return path


@pytest.mark.parametrize("target", ["bottle", "red wine glass", "cell phone", "teddy bear"])
def test_fetch_preview_uses_requested_object_and_symbolic_start(
        places: Path, monkeypatch: pytest.MonkeyPatch, target: str) -> None:
    """Offline fallback must retain class/color and return without requiring home."""
    monkeypatch.setattr(OllamaClient, "generate_plan", Mock(side_effect=OllamaError("offline")))
    result = preview_plan(f"bring me a {target} from lab_desk", waypoints_file=places)
    assert result["execute"] is False
    assert result["source"] == "fallback"
    assert result["actions"] == [
        {"action": "navigate", "target": "lab_desk"},
        {"action": "find", "target": target},
        {"action": "grasp"},
        {"action": "navigate", "target": MISSION_START},
        {"action": "release"},
    ]


@pytest.mark.parametrize("wrong", [
    [{"action": "find", "target": "bottle"}],
    [{"action": "navigate", "target": "lab_desk"},
     {"action": "find", "target": "cup"}, {"action": "grasp"},
     {"action": "navigate", "target": MISSION_START}, {"action": "release"}],
])
def test_valid_but_wrong_llm_fetch_is_replaced(
        places: Path, monkeypatch: pytest.MonkeyPatch, wrong: list) -> None:
    """Vocabulary validation alone cannot accept the wrong object or missing journey."""
    generate = Mock(return_value=json.dumps(wrong))
    monkeypatch.setattr(OllamaClient, "generate_plan", generate)
    result = preview_plan("bring a bottle from lab_desk", waypoints_file=places)
    assert result["source"] == "fallback"
    assert result["actions"][1]["target"] == "bottle"
    assert generate.call_args.kwargs["waypoints"] == ("lab_desk", MISSION_START)


def test_preview_rejects_unrecorded_fetch_place(
        places: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Preview uses the operator's waypoint file rather than accepting invented places."""
    monkeypatch.setattr(OllamaClient, "generate_plan", Mock(side_effect=OllamaError("offline")))
    with pytest.raises(ValueError, match="unknown waypoint"):
        preview_plan("bring a bottle from kitchen", waypoints_file=places)


def test_custom_model_class_is_preserved_in_preview(
        places: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A custom trained label may be used without substituting a built-in class."""
    monkeypatch.setattr(OllamaClient, "generate_plan", Mock(side_effect=OllamaError("offline")))
    result = preview_plan("bring a wood block from lab_desk", waypoints_file=places,
                          object_classes=("wood block",))
    assert result["actions"][1] == {"action": "find", "target": "wood block"}


def test_preview_explains_start_pose_without_initializing_ros(
        places: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    """Preview shows the runtime pose dependency and performs no ROS initialization."""
    monkeypatch.setattr(OllamaClient, "generate_plan", Mock(side_effect=OllamaError("offline")))
    initialize = Mock()
    monkeypatch.setattr(eira_cli.rclpy, "init", initialize)
    assert eira_cli.main(["--plan-only", "--no-color", "--waypoints-file", str(places),
                          "bring a bottle from lab_desk"]) == 0
    output = capsys.readouterr().out
    assert "mission_start" in output and "does not capture a pose" in output
    initialize.assert_not_called()


@pytest.mark.parametrize("target", ["bottle", "apple", "cell phone"])
def test_cli_fetch_bridge_navigates_before_detection_and_returns_to_start(
        brain, monkeypatch: pytest.MonkeyPatch, target: str) -> None:
    """Drive CLI, Brain and RGB-D handlers together with mocked GPU, Nav2 and arm."""
    # Source imports also work when running only the Brain package's tests.
    source = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(source / "eira_perception"))
    import numpy as np
    from geometry_msgs.msg import PointStamped
    from sensor_msgs.msg import CameraInfo, Image
    from std_msgs.msg import String
    from eira_perception.perception_core import Detection, PositionFilter, TargetTrack
    from eira_perception.vision_manager import ImageContext, VisionManager

    starting_pose = {"x": -1.2, "y": 0.8, "yaw": 0.4}
    brain._state = brain.IDLE
    brain._retries_stamp = None
    brain._map_frame = "map"
    brain._waypoints = {"desk": {"x": 2.0, "y": 3.0, "yaw": 0.0},
                        "home": {"x": 100.0, "y": 100.0, "yaw": 0.0}}
    brain._load_waypoints = Mock()
    brain._capture_start_pose = Mock(return_value=dict(starting_pose))
    brain._spawn_plan_worker = lambda command: brain._plan_worker(command, brain._generation)
    brain._ollama = Mock()
    brain._ollama.generate_plan.side_effect = OllamaError("offline test")
    brain._nav_client = Mock()
    brain._nav_client.server_is_ready.return_value = True
    monkeypatch.setattr(llm_task_planner, "NavigateThroughPoses",
                        SimpleNamespace(Goal=lambda: SimpleNamespace(poses=[])))
    brain._check_amcl_convergence = Mock(return_value=True)
    brain.get_clock = Mock()
    brain.get_clock.return_value.now.return_value.to_msg.return_value = Image().header.stamp
    original_parameter = brain.get_parameter.side_effect
    brain.get_parameter.side_effect = lambda name: (
        SimpleNamespace(value=0.0) if name == "nav_settle_s" else original_parameter(name))

    vision = object.__new__(VisionManager)
    vision._request = {}
    vision._class = vision._color = ""
    vision._generation = 0
    vision._searching = vision._announced = vision._idle_logged = False
    vision._seen_requests = OrderedDict()
    vision._pending = vision._pending_context = None
    vision._model = True
    vision._model_labels = {"cup", "bottle", "apple", "cell phone"}
    vision._track, vision._filter = TargetTrack(), PositionFilter()
    vision._transformer_ready = False
    vision._log, vision._warn, vision._annotate = Mock(), Mock(), Mock()
    vision._check_image_time = Mock(return_value=0.0)
    vision.get_logger = Mock(return_value=Mock())
    parameters = {"continuous_mode": False, "request_cache_size": 256,
                  "color_min_fraction": 0.25,
                  "find_timeout_s": 20.0, "depth_roi_half": 1,
                  "min_depth_m": 0.1, "max_depth_m": 3.0,
                  "target_frame": "base_link", "camera_optical_frame": "camera_optical",
                  "tf_timeout_s": 0.1, "depth_debug": False,
                  "volume_thickness_m": 0.0, "volume_shape": "cuboid"}
    vision._param = lambda name: parameters[name]
    vision._event_pub, vision._pose_pub = Mock(), Mock()
    vision._event_pub.publish.side_effect = brain._on_vision_event
    brain._vision_target_pub.publish.side_effect = vision._on_target

    transformed = PointStamped()
    transformed.header.frame_id = "base_link"
    transformed.header.stamp.sec = 123
    transformed.point.x, transformed.point.y, transformed.point.z = 0.25, 0.0, 0.1
    vision._tf_buffer = SimpleNamespace(transform=Mock(return_value=transformed))
    info = CameraInfo(width=20, height=20)
    info.header.frame_id = "camera_optical"
    info.k = [100., 0., 10., 0., 100., 10., 0., 0., 1.]
    image = Image(width=20, height=20)
    image.header.frame_id, image.header.stamp.sec = "camera_optical", 123
    depth = Image(width=20, height=20, encoding="32FC1")
    depth.header = image.header

    cli = object.__new__(eira_cli.CliFrontend)
    cli._mission_id, cli._command = "fetch-bridge", f"bring a {target} from desk"
    cli._plan_only = cli._quiet = cli._json_output = False
    cli._settled, cli._exit_code, cli._timeout_s = False, 2, 5.0
    cli._color, cli._last_output = False, None
    cli._command_pub = Mock()
    cli._command_pub.get_subscription_count.return_value = 1
    cli._command_pub.publish.side_effect = brain._on_command
    brain._status_pub.publish.side_effect = cli._on_status
    manipulations = []

    def complete_arm(message: String) -> None:
        request = json.loads(message.data)
        manipulations.append(request)
        event = {"grasp": "grasped", "release": "released"}.get(request["command"])
        if event:
            brain._on_manip_event(String(data=json.dumps({
                "mission_id": request["mission_id"], "action_id": request["action_id"],
                "event": event})))

    brain._manip_req_pub.publish.side_effect = complete_arm
    ticks = []

    def spin_once(node, timeout_sec: float) -> None:
        ticks.append(brain._state)
        assert len(ticks) < 30, "mission should finish within bounded mock callbacks"
        if brain._state == brain.WAIT_NAV:
            if brain._plan_idx == 0:
                assert not vision._searching
                assert not vision._pose_pub.publish.called
            brain._nav_result = 4  # GoalStatus.STATUS_SUCCEEDED
        elif brain._state == brain.WAIT_FIND:
            assert len(brain._nav_client.send_goal_async.call_args_list) == 1
            assert vision._request["target"] == target
            vision._process_result([
                Detection((0., 0., 19., 19.), "cup", 0.99, 1),
                Detection((5., 5., 15., 15.), target, 0.9, 2),
            ], ImageContext(vision._generation, np.zeros((20, 20, 3), np.uint8),
                            np.ones((20, 20), np.float32), image, depth, info, None, (20, 20)))
        brain._tick()

    monkeypatch.setattr(eira_cli.rclpy, "ok", lambda: True)
    monkeypatch.setattr(eira_cli.rclpy, "spin_once", spin_once)
    assert cli.run() == 0
    goals = [call.args[0].poses[0].pose for call in brain._nav_client.send_goal_async.call_args_list]
    assert len(goals) == 2
    assert (goals[0].position.x, goals[0].position.y) == (2.0, 3.0)
    assert (goals[1].position.x, goals[1].position.y) == (-1.2, 0.8)
    assert goals[1].orientation.z == pytest.approx(math.sin(0.2))
    assert [request["command"] for request in manipulations] == ["grasp", "release"]
    assert manipulations[0]["target"]["target"] == target
    assert manipulations[0]["target"]["label"] == target
    assert manipulations[0]["target"]["track_id"] == 2
    brain._capture_start_pose.assert_called_once()
    assert cli._settled
