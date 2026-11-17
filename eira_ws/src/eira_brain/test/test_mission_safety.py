"""Regression tests for asynchronous orchestration and ROS message contracts.

Author: E-AIRA contributors.
Hardware target: mocked ROSMASTER M3 Pro orchestration on ROS 2 Humble.
"""

from concurrent.futures import Future
from collections import OrderedDict
import json
from pathlib import Path
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from std_msgs.msg import String

from eira_brain.eira_cli import CliFrontend, preview_plan
from eira_brain.llm_task_planner import LLMTaskPlanner
from eira_brain.ollama_client import OllamaClient, OllamaError
from eira_brain.waypoint_store import load_waypoints, validate_waypoints
from eira_brain.visual_relocalization import quaternion_matrix, recovery_needed


@pytest.fixture
def brain() -> LLMTaskPlanner:
    """Construct a stateful Brain with mocked ROS publishers and services.

    Returns:
        Planner instance without an active DDS participant.
    """
    node = object.__new__(LLMTaskPlanner)
    node._mission_lock = threading.RLock()
    node._generation = 1
    node._mission_id = "mission-a"
    node._command = "find cup"
    node._action_id = "0:1"
    node._state = node.PLANNING
    node._closing = False
    node._plan = []
    node._plan_idx = 0
    node._plan_seq = 0
    node._nav_generation = 1
    node._nav_token = (1, 1)
    node._nav_handles = {}
    node._nav_result = None
    node._nav_goal_handle = None
    node._pending_nav_waypoint = None
    node._mission_queue = []
    node._motion_owner = "none"
    node._found_context = {}
    node._planner_source = "none"
    node._deadline = None
    node._retries_left = 0
    node._waypoints = {"home": {"x": 0.0, "y": 0.0, "yaw": 0.0}}
    for name in ("_plan_pub", "_status_pub", "_vision_target_pub", "_manip_req_pub",
                 "_cmd_vel_pub", "_owner_pub", "_beep_pub"):
        setattr(node, name, Mock())
    node.get_logger = Mock(return_value=Mock())
    node.get_parameter = Mock(side_effect=lambda name: SimpleNamespace(value={
        "mission_queue_len": 4, "target_republish_s": 1.0,
        "nav_server_wait_s": 5.0, "max_plan_steps": 64,
    }.get(name, 1.0)))
    return node


def test_stop_invalidates_blocked_llm_worker(brain: LLMTaskPlanner) -> None:
    """A canceled HTTP worker cannot install its result after stop."""
    entered, release = threading.Event(), threading.Event()

    def generate(command: str, **grounding: object) -> str:
        """Simulate slow external inference.

        Args:
            command: Ignored simulated instruction.
            **grounding: Grounded prompt context supplied by the planner.

        Returns:
            Valid detector action JSON.
        """
        entered.set()
        release.wait(2.0)
        return '[{"action":"find","target":"cup"}]'

    brain._ollama = SimpleNamespace(generate_plan=generate)
    worker = threading.Thread(target=brain._plan_worker, args=("find cup", 1))
    worker.start()
    assert entered.wait(1.0)
    brain._on_command(String(data="stop"))
    release.set()
    worker.join(2.0)
    assert brain._state == brain.IDLE
    brain._plan_pub.publish.assert_not_called()
    assert brain._motion_owner == "none"


def test_old_nav_acceptance_is_canceled(brain: LLMTaskPlanner) -> None:
    """A goal accepted after stop receives a cancel request."""
    brain._state = brain.IDLE
    brain._nav_token = None
    handle = Mock(accepted=True)
    future = Future()
    future.set_result(handle)
    brain._on_goal_response(future, (1, 1))
    handle.cancel_goal_async.assert_called_once()
    assert not brain._nav_handles


def test_old_nav_result_ignored(brain: LLMTaskPlanner) -> None:
    """An old attempt cannot finish the replacement goal."""
    brain._state = brain.WAIT_NAV
    brain._nav_token = (1, 2)
    future = Future()
    future.set_result(SimpleNamespace(status=4))
    brain._on_nav_result(future, (1, 1))
    assert brain._nav_result is None


def test_cancel_visits_every_known_handle(brain: LLMTaskPlanner) -> None:
    """Cancellation covers all accepted goal handles."""
    handles = [Mock(), Mock()]
    brain._nav_handles = {(1, index): value for index, value in enumerate(handles)}
    brain._cancel_navigation()
    for handle in handles:
        handle.cancel_goal_async.assert_called_once()
    assert brain._nav_token is None


def test_timer_callbacks_are_serialized(brain: LLMTaskPlanner) -> None:
    """Concurrent executor threads cannot overlap state-machine handlers."""
    brain._state = brain.EXECUTING
    active = []
    overlaps = []

    def dispatch() -> None:
        """Observe overlap while deliberately yielding the GIL."""
        active.append(1)
        overlaps.append(len(active))
        time.sleep(0.02)
        active.pop()

    brain._dispatch_next_action = dispatch
    workers = [threading.Thread(target=brain._tick) for _ in range(4)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    assert overlaps == [1] * 4


@pytest.mark.parametrize("payload", ["null", "[]", "42", '"found"', "bad json"])
def test_invalid_event_shapes_ignored(brain: LLMTaskPlanner, payload: str) -> None:
    """Malformed/nonobject events cannot enter the state machine."""
    assert brain._correlated_event(String(data=payload)) is None


def test_wrong_action_event_ignored(brain: LLMTaskPlanner) -> None:
    """Events require both action and mission identity."""
    event = {"event": "found", "mission_id": "mission-a", "action_id": "old"}
    assert brain._correlated_event(String(data=json.dumps(event))) is None


def test_late_grasp_success_does_not_timeout(brain: LLMTaskPlanner) -> None:
    """Successful matching events return before testing old deadlines."""
    brain._last_manip_event = {"event": "grasped"}
    brain._deadline = time.monotonic() - 1.0
    brain._action_failed = Mock()
    brain._check_grasp()
    assert brain._plan_idx == 1
    brain._action_failed.assert_not_called()


def test_release_timeout_fails(brain: LLMTaskPlanner) -> None:
    """Unconfirmed release cannot be silently counted as success."""
    brain._plan = [{"action": "release"}]
    brain._last_manip_event = None
    brain._deadline = time.monotonic() - 1.0
    brain._action_failed = Mock()
    brain._check_misc()
    brain._action_failed.assert_called_once_with("manipulation timeout")


@pytest.mark.parametrize("plan", [
    [{"action": "grasp"}],
    [{"action": "find", "target": "cup"}, {"action": "danger"}, {"action": "grasp"}],
    [{"action": "find", "target": "cup"}, {"action": "navigate", "target": "home"},
     {"action": "grasp"}],
    [{"action": "find", "target": 17}],
])
def test_invalid_plans_rejected_whole(brain: LLMTaskPlanner, plan: list) -> None:
    """No partial unsafe plan survives semantic validation."""
    assert brain._validate_plan(plan) is None


def test_color_sort_fallback(brain: LLMTaskPlanner) -> None:
    """Color identity survives deterministic sorting and fetch parsing."""
    plan = brain._fallback_plan("sort red cup into red_bin")
    assert plan[0] == {"action": "find", "target": "red cup"}
    assert plan[2] == {"action": "navigate", "target": "red_bin"}
    assert brain._fallback_plan("bring blue cup from kitchen")[1]["target"] == "blue cup"


def test_plan_preview_never_publishes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Local preview can run without any ROS context or command publisher."""
    monkeypatch.setattr(OllamaClient, "generate_plan", Mock(side_effect=OllamaError("offline")))
    plan = preview_plan("find red cup")
    assert plan["execute"] is False
    assert plan["actions"][0]["target"] == "red cup"
    cli = object.__new__(CliFrontend)
    cli._plan_only, cli._command, cli._command_pub = True, "find cup", Mock()
    assert cli.run() == 0
    cli._command_pub.publish.assert_not_called()


def test_cli_ignores_other_missions() -> None:
    """Another client's success cannot complete this request."""
    cli = object.__new__(CliFrontend)
    cli._mission_id, cli._settled = "mine", False
    cli._on_status(String(data=json.dumps({"mission_id": "other", "state": "DONE"})))
    assert cli._settled is False


@pytest.mark.parametrize("data", [[], {"waypoints": []}, {"frame": ""},
                                  {"waypoints": {"bad": {"x": float("nan")}}}])
def test_waypoint_schema_rejects_invalid_data(data: dict) -> None:
    """Malformed/nonfinite waypoint files are never partly accepted."""
    with pytest.raises(ValueError):
        validate_waypoints(data)


def test_waypoint_load(tmp_path: Path) -> None:
    """Validated database reading is independent of ROS initialization."""
    path = tmp_path / "waypoints.yaml"
    path.write_text("frame: map\nwaypoints:\n  Home: {x: 1, y: 2, yaw: 0}\n")
    assert load_waypoints(path)["waypoints"]["home"]["x"] == 1.0


def test_visual_covariance_thresholds() -> None:
    """Only excessive AMCL covariance triggers visual recovery."""
    covariance = [0.0] * 36
    assert not recovery_needed(covariance, 0.5, 0.4)
    covariance[0] = 0.6
    assert recovery_needed(covariance, 0.5, 0.4)
    assert recovery_needed([float("nan")] * 36, 0.5, 0.4)


def test_visual_quaternion_validation() -> None:
    """Invalid landmark orientations cannot generate initial poses."""
    with pytest.raises(ValueError):
        quaternion_matrix(0.0, 0.0, 0.0, 0.0)
    assert quaternion_matrix(0.0, 0.0, 0.0, 1.0)[3, 3] == 1.0


def test_brain_vision_arm_topic_contract(brain: LLMTaskPlanner) -> None:
    """Drive real Brain/Vision contract handlers through mocked topic delivery."""
    import sys
    source = Path(__file__).resolve().parents[2]
    for package in ("eira_perception", "eira_manipulation"):
        path = str(source / package)
        if path not in sys.path:
            sys.path.insert(0, path)
    from eira_perception.vision_manager import VisionManager
    from eira_manipulation.grasp_policy import request_envelope

    vision = object.__new__(VisionManager)
    vision._request = {}
    vision._searching = False
    vision._announced = False
    vision._generation = 0
    vision._seen_requests = OrderedDict()
    vision._idle_logged = False
    vision._pending = None
    vision._pending_context = None
    vision._model = True
    vision._load_attempts = vision._inference_errors = 0
    vision._next_load = 0.0
    vision._track, vision._filter = Mock(), Mock()
    vision._log = Mock()
    vision._param = Mock(side_effect=lambda name: {
        "continuous_mode": False, "request_cache_size": 256,
        "find_timeout_s": 20.0,
    }.get(name, 20.0))
    vision._event_pub = Mock()
    vision._event_pub.publish.side_effect = brain._on_vision_event
    brain._vision_target_pub.publish.side_effect = vision._on_target
    brain._state = brain.EXECUTING
    brain._plan = [{"action": "find", "target": "red cup"}, {"action": "grasp"}]
    brain._plan_seq = 1
    brain._retries_stamp = None
    brain._last_target_pub = 0.0
    brain._attempt = 0
    brain._dispatch_next_action()
    assert vision._request["target"] == "red cup"
    assert vision._request["mission_id"] == brain._mission_id
    vision._emit("found", label="cup", color="red", width_m=0.045,
                 measurement_stamp_ns=123456, volume_m3=0.0002)
    brain._check_find()
    assert brain._plan_idx == 1
    captured = []

    def arm_request(message: String) -> None:
        """Mock arm service completion while using the real command decoder.

        Args:
            message: Correlated grasp command from the Brain.
        """
        request = request_envelope(message.data)
        captured.append(request)
        brain._on_manip_event(String(data=json.dumps({
            "event": "grasped", "mission_id": request["mission_id"],
            "action_id": request["action_id"]})))

    brain._manip_req_pub.publish.side_effect = arm_request
    brain._dispatch_next_action()
    assert captured[0]["target"]["measurement_stamp_ns"] == 123456
    assert captured[0]["target"]["color"] == "red"
    assert captured[0]["target"]["width_m"] == 0.045
    assert captured[0]["action_id"] != vision._request["action_id"]
    brain._check_grasp()
    assert brain._plan_idx == 2


@pytest.mark.parametrize("transcript,expected", [
    ("Eira, find red cup", "find red cup"),
    ("background conversation", None),
    ("eira", None),
])
def test_voice_activation_gate(transcript: str, expected: str | None) -> None:
    """Publish only a nonempty command following the configured wake word.

    Args:
        transcript: Simulated Whisper worker output.
        expected: Expected command, or None when activation should be rejected.
    """
    from queue import Queue
    from eira_brain.voice_activation import VoiceActivation
    voice = object.__new__(VoiceActivation)
    voice._settings = {"wake_word": "eira", "microphone_enabled": False}
    voice._results = Queue()
    voice._results.put({"event": "transcribed", "text": transcript})
    voice._process = Mock()
    voice._process.is_alive.return_value = True
    voice._retry_at = None
    voice._deadline = None
    voice._publisher, voice._emit = Mock(), Mock()
    voice._ready, voice._busy = True, True
    voice._poll()
    if expected is None:
        voice._publisher.publish.assert_not_called()
    else:
        assert voice._publisher.publish.call_args.args[0].data == expected


def test_safety_revocation_aborts_and_drops_queue(brain: LLMTaskPlanner) -> None:
    """Gate hazards cannot automatically resume an old or queued mission."""
    brain._state = brain.WAIT_NAV
    brain._mission_queue = [("go home", "queued-mission")]
    event = {"event": "edge_blocked_or_stale", "mission_id": brain._mission_id,
             "action_id": brain._action_id}
    brain._on_motion_event(String(data=json.dumps(event)))
    assert brain._state == brain.IDLE
    assert not brain._mission_queue
    assert brain._motion_owner == "none"


def test_found_wrong_target_rejected(brain: LLMTaskPlanner) -> None:
    """Identity alone cannot turn the wrong object into a successful find."""
    brain._state = brain.WAIT_FIND
    brain._plan = [{"action": "find", "target": "red cup"}]
    brain._last_vision_event = None
    event = {"event": "found", "mission_id": brain._mission_id,
             "action_id": brain._action_id, "target": "blue cup"}
    brain._on_vision_event(String(data=json.dumps(event)))
    assert brain._last_vision_event is None


def test_invalid_llm_plan_is_repaired_once(brain: LLMTaskPlanner) -> None:
    """Retry one malformed response with explicit grounding and repair feedback."""
    brain._ollama = Mock()
    brain._ollama.generate_plan.side_effect = ["not JSON", '[{"action":"find","target":"cup"}]']
    brain._plan_worker("find cup", 1)
    assert brain._ollama.generate_plan.call_count == 2
    first, second = brain._ollama.generate_plan.call_args_list
    assert first.kwargs["waypoints"] == ("home",)
    assert first.kwargs["repair_reason"] == ""
    assert second.kwargs["repair_reason"]
    payload = json.loads(brain._plan_pub.publish.call_args.args[0].data)
    assert payload["source"] == "llm"
    assert payload["llm_attempts"] == 2
    assert payload["planning_latency_ms"] >= payload["llm_response_ms"] >= 0.0
    assert payload["planner_reason"] == "grounded LLM plan after repair"


def test_two_invalid_responses_use_grounded_fallback(brain: LLMTaskPlanner) -> None:
    """Unsupported detector labels cannot leak into executable LLM plans."""
    brain._ollama = Mock()
    brain._ollama.generate_plan.return_value = '[{"action":"find","target":"unicorn"}]'
    brain._plan_worker("find cup", 1)
    assert brain._ollama.generate_plan.call_count == 2
    payload = json.loads(brain._plan_pub.publish.call_args.args[0].data)
    assert payload["source"] == "fallback"
    assert "unsupported detector class" in payload["fallback_reason"]
    assert payload["actions"] == [{"action": "find", "target": "cup"}]


def test_llm_transport_failure_reports_fallback_reason(brain: LLMTaskPlanner) -> None:
    """Transport failure is measured and distinctly classified from invalid JSON."""
    brain._ollama = Mock()
    brain._ollama.generate_plan.side_effect = OllamaError("connection refused")
    brain._plan_worker("find cup", 1)
    payload = json.loads(brain._plan_pub.publish.call_args.args[0].data)
    assert payload["llm_attempts"] == 1
    assert payload["source"] == "fallback"
    assert "connection refused" in payload["planner_reason"]


def test_fallback_keeps_multiword_colored_class(brain: LLMTaskPlanner) -> None:
    """Long COCO class names survive deterministic fallback parsing."""
    assert brain._fallback_plan("find blue wine glass") == [
        {"action": "find", "target": "blue wine glass"}]


def test_action_telemetry_has_exact_duration(
        brain: LLMTaskPlanner, monkeypatch: pytest.MonkeyPatch) -> None:
    """Action completion retains its original identity and monotonic duration."""
    brain._plan = [{"action": "find", "target": "cup"}]
    brain._attempt = 2
    monkeypatch.setattr(time, "monotonic", lambda: 10.0)
    brain._begin_action("find", "cup")
    monkeypatch.setattr(time, "monotonic", lambda: 12.5)
    brain._advance()
    events = [json.loads(call.args[0].data) for call in brain._status_pub.publish.call_args_list]
    assert [event["event"] for event in events] == ["action_started", "action_finished"]
    finished = events[-1]
    assert finished["duration_s"] == 2.5
    assert finished["step"] == 0
    assert finished["action"] == "find"
    assert finished["attempt"] == 2
    assert finished["action_id"] == "0:1"
    assert finished["success"] is True
    assert finished["error_reason"] is None
    assert finished["physical_contact_verified"] is False


def test_retry_telemetry_closes_attempt_before_recovery(brain: LLMTaskPlanner) -> None:
    """Failed attempts and retries remain separate measurable records."""
    brain._plan = [{"action": "find", "target": "cup"}]
    brain._attempt = 1
    brain._state = brain.WAIT_FIND
    brain._retries_left = 1
    brain._begin_action("find", "cup")
    brain._action_failed("target acquisition timeout")
    events = [json.loads(call.args[0].data) for call in brain._status_pub.publish.call_args_list]
    assert [event["event"] for event in events] == [
        "action_started", "action_finished", "recovery"]
    assert events[1]["success"] is False
    assert events[1]["error_reason"] == "target acquisition timeout"
    assert events[2]["recovery_kind"] == "retry"
    assert events[2]["retry_index"] == 1
    assert brain._active_action is None


def test_stop_emits_one_canceled_action(brain: LLMTaskPlanner) -> None:
    """Cancellation emits one action result even though all motion paths stop."""
    brain._attempt = 1
    brain._state = brain.WAIT_NAV
    brain._begin_action("navigate", "home")
    brain._on_command(String(data="stop"))
    events = [json.loads(call.args[0].data) for call in brain._status_pub.publish.call_args_list]
    finished = [event for event in events if event.get("event") == "action_finished"]
    assert len(finished) == 1
    assert finished[0]["result"] == "canceled"
    assert finished[0]["success"] is False


def test_benchmark_reset_is_navigation_only(brain: LLMTaskPlanner) -> None:
    """Benchmark reset bypasses inference without commanding the arm or changing AMCL."""
    brain._state = brain.IDLE
    brain._load_waypoints = Mock()
    brain._spawn_plan_worker = Mock()
    brain._on_command(String(data=json.dumps({
        "command": "benchmark reset", "mission_id": "reset-1", "purpose": "benchmark_reset",
        "start_waypoint": "home"})))
    payload = json.loads(brain._plan_pub.publish.call_args.args[0].data)
    assert payload["benchmark_reset"] is True
    assert payload["source"] == "benchmark_reset"
    assert payload["actions"] == [{"action": "navigate", "target": "home"}]
    assert payload["llm_attempts"] == 0
    brain._spawn_plan_worker.assert_not_called()
    brain._manip_req_pub.publish.assert_not_called()


def test_benchmark_reset_rejects_unknown_destination(brain: LLMTaskPlanner) -> None:
    """An invalid reset cannot install an ungrounded navigation destination."""
    brain._state = brain.IDLE
    brain._load_waypoints = Mock()
    brain._on_command(String(data=json.dumps({
        "command": "benchmark reset", "mission_id": "reset-1", "purpose": "benchmark_reset",
        "start_waypoint": "unknown"})))
    payload = json.loads(brain._plan_pub.publish.call_args.args[0].data)
    assert payload["actions"] == []
    assert brain._state == brain.IDLE
    assert "unknown waypoint" in payload["planner_reason"]


def test_benchmark_reset_is_not_queued_while_busy(brain: LLMTaskPlanner) -> None:
    """A reset request cannot silently run after another mission finishes."""
    brain._state = brain.WAIT_GRASP
    brain._on_command(String(data=json.dumps({
        "command": "benchmark reset", "mission_id": "reset-1", "purpose": "benchmark_reset",
        "start_waypoint": "home"})))
    assert brain._state == brain.WAIT_GRASP
    assert not brain._mission_queue
    brain._plan_pub.publish.assert_not_called()


def test_raw_llm_response_is_logged_before_cleanup(brain: LLMTaskPlanner) -> None:
    """Keep original Phi-3 output observable while executing a validated cleaned array."""
    raw = 'Here is the plan:\n```json\n[{"action":"find","target":"cup"}]\n```\nDone.'
    brain._ollama = Mock()
    brain._ollama.generate_plan.return_value = raw
    brain._plan_worker("find cup", 1)
    from eira_brain.console import sanitize_text
    debug = [call.args[0] for call in brain.get_logger().debug.call_args_list]
    assert any('Model reply 1 for mission-a:' in line and sanitize_text(raw, limit=0) in line
               for line in debug)
    info = [call.args[0] for call in brain.get_logger().info.call_args_list]
    assert all('Model reply' not in line for line in info)
    plan = json.loads(brain._plan_pub.publish.call_args.args[0].data)
    assert plan["source"] == "llm"
    assert plan["llm_attempts"] == 1


def test_grasp_refreshes_are_bounded_and_stop_cancels_them(
        brain: LLMTaskPlanner, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fresh pose requests run during a grasp and cannot continue after mission stop."""
    brain._state = brain.WAIT_GRASP
    brain._found_context = {"target": "red cup"}
    brain._last_manip_event = None
    brain._deadline = None
    brain._action_id = "1:1"
    clock = [10.0]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    brain._check_grasp()
    first = json.loads(brain._vision_target_pub.publish.call_args.args[0].data)
    clock[0] = 10.2
    brain._check_grasp()
    assert brain._vision_target_pub.publish.call_count == 1
    clock[0] = 11.0
    brain._check_grasp()
    second = json.loads(brain._vision_target_pub.publish.call_args.args[0].data)
    assert first["target"] == second["target"] == "red cup"
    assert first["mission_id"] == second["mission_id"] == brain._mission_id
    assert first["action_id"] == second["action_id"] == "1:1"
    assert first["refresh_id"] != second["refresh_id"]
    brain._on_command(String(data="stop"))
    canceled = json.loads(brain._vision_target_pub.publish.call_args.args[0].data)
    assert canceled == {**second, "cancel": True}
    count = brain._vision_target_pub.publish.call_count
    clock[0] = 20.0
    brain._tick()
    assert brain._vision_target_pub.publish.call_count == count


def test_completed_grasp_never_starts_another_search(brain: LLMTaskPlanner) -> None:
    """A terminal grasp result is consumed before requesting another expensive update."""
    brain._state = brain.WAIT_GRASP
    brain._found_context = {"target": "red cup"}
    brain._last_manip_event = {"event": "grasped"}
    brain._check_grasp()
    brain._vision_target_pub.publish.assert_not_called()


def test_scan_recovery_requests_a_new_one_shot_search(brain: LLMTaskPlanner) -> None:
    """A scan can reacquire after demand vision has stopped at its previous timeout."""
    brain._state = brain.WAIT_FIND
    brain._plan = [{"action": "find", "target": "cup"}]
    brain._last_target_pub = 0.0
    brain._scans_done = 0
    brain._scan_direction = 1
    brain._vision_refresh_seq = 4
    brain._begin_scan("acquisition_timeout")
    request = json.loads(brain._vision_target_pub.publish.call_args.args[0].data)
    assert request == {"mission_id": "mission-a", "action_id": "0:1", "target": "cup",
                       "refresh_id": 5}
    assert brain._state == brain.SCAN


def test_readable_terminal_keeps_structured_status_evidence(brain: LLMTaskPlanner) -> None:
    """Human error hints must not replace machine codes on existing ROS topics."""
    brain._publish_status('navigation status 6', event='action_finished', action='navigate',
                          result='failed', success=False, error_reason='navigation status 6')
    payload = json.loads(brain._status_pub.publish.call_args.args[0].data)
    assert payload['mission_id'] == 'mission-a'
    assert payload['error_reason'] == 'navigation status 6'
    line = brain.get_logger().info.call_args.args[0]
    assert 'Try 2D Pose Estimate in RViz' in line
    assert 'mission_id' not in line
