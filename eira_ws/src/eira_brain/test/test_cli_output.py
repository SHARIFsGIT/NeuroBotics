"""Verify readable CLI output and the explicit machine-readable compatibility mode.

Author: E-AIRA contributors.
Hardware target: mocked ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
"""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from std_msgs.msg import String

from eira_brain import eira_cli as cli_module
from eira_brain.eira_cli import CliFrontend, list_waypoints, main


@pytest.fixture
def frontend() -> CliFrontend:
    """Construct an output observer without starting ROS or publishing a mission.

    Returns:
        Frontend following one synthetic mission with color disabled.
    """
    node = object.__new__(CliFrontend)
    node._mission_id = "mine"
    node._settled, node._exit_code = False, 2
    node._json_output, node._color = False, False
    node._last_output = None
    return node


def status_message(**fields: object) -> String:
    """Build a correlated synthetic Brain observation.

    Args:
        **fields: Status fields overriding an ordinary planning observation.

    Returns:
        Original JSON String topic message consumed by the CLI.
    """
    payload = {"mission_id": "mine", "state": "PLANNING", "event": "mission_started",
               "command": "find a red cup", "detail": "planning"}
    return String(data=json.dumps({**payload, **fields}))


def preview_payload() -> dict:
    """Provide a complete nonexecuting preview for CLI mode tests.

    Returns:
        Synthetic planner result with navigation, acquisition and grasp.
    """
    return {"source": "llm", "command": "pick up a red cup at kitchen", "execute": False,
            "actions": [{"action": "navigate", "target": "kitchen"},
                        {"action": "find", "target": "red cup"}, {"action": "grasp"}]}


def test_live_output_is_readable_and_ignores_other_missions(
        frontend: CliFrontend, capsys: pytest.CaptureFixture) -> None:
    """The live observer renders its mission while retaining identity filtering.

    Args:
        frontend: CLI observer without ROS transport.
        capsys: Fixture capturing terminal output.
    """
    frontend._on_status(status_message(mission_id="other"))
    assert capsys.readouterr().out == ""
    frontend._on_status(status_message())
    output = capsys.readouterr().out
    assert "[CLI]" in output
    assert "red cup" in output
    assert '"mission_id"' not in output
    assert "\x1b" not in output


def test_repeated_status_does_not_spam_the_terminal(
        frontend: CliFrontend, capsys: pytest.CaptureFixture) -> None:
    """Timestamp-only changes do not duplicate the same human status line.

    Args:
        frontend: CLI observer with readable output.
        capsys: Fixture capturing terminal output.
    """
    frontend._on_status(status_message(wall_time=1.0))
    first = capsys.readouterr().out
    assert first
    frontend._on_status(status_message(wall_time=2.0))
    assert capsys.readouterr().out == ""


def test_terminal_failures_are_visible_and_preserve_exit_status(
        frontend: CliFrontend, capsys: pytest.CaptureFixture) -> None:
    """Failure observations remain visible even when repeated verbatim.

    Args:
        frontend: CLI observer with readable output.
        capsys: Fixture capturing terminal output.
    """
    message = status_message(state="FAILED", event="mission_finished", success=False,
                             error_reason="navigation status 6", detail="navigation status 6")
    frontend._on_status(message)
    frontend._on_status(message)
    output = capsys.readouterr().out
    assert output.count("Try 2D Pose Estimate in RViz") >= 2
    assert frontend._settled is True
    assert frontend._exit_code == 2


def test_json_live_mode_preserves_complete_original_payload(
        frontend: CliFrontend, capsys: pytest.CaptureFixture) -> None:
    """Explicit JSON mode retains correlation and diagnostic fields without color.

    Args:
        frontend: CLI observer without ROS transport.
        capsys: Fixture capturing machine output.
    """
    frontend._json_output = True
    message = status_message(action_id="0:1", planner="llm", wall_time=12.5)
    frontend._on_status(message)
    assert json.loads(capsys.readouterr().out) == json.loads(message.data)


def test_readable_preview_never_initializes_ros(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    """Preview formatting cannot accidentally initialize ROS or create a publisher.

    Args:
        monkeypatch: Fixture replacing the model and ROS entry points.
        capsys: Fixture capturing preview output.
    """
    monkeypatch.setattr(cli_module, "preview_plan", Mock(return_value=preview_payload()))
    initialize, constructor = Mock(), Mock()
    monkeypatch.setattr(cli_module.rclpy, "init", initialize)
    monkeypatch.setattr(cli_module, "CliFrontend", constructor)
    assert main(["--plan-only", "--no-color", "pick up a red cup at kitchen"]) == 0
    output = capsys.readouterr().out
    assert "Preview only; nothing sent to robot" in output
    assert "Planner: LLM" in output
    assert "1." in output and "2." in output and "3." in output
    assert "kitchen" in output and "red cup" in output
    assert '"actions"' not in output
    initialize.assert_not_called()
    constructor.assert_not_called()


def test_json_preview_preserves_legacy_envelope(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    """Machine preview consumers can continue reading the complete JSON envelope.

    Args:
        monkeypatch: Fixture replacing model inference.
        capsys: Fixture capturing machine output.
    """
    payload = preview_payload()
    monkeypatch.setattr(cli_module, "preview_plan", Mock(return_value=payload))
    assert main(["--plan-only", "--json", "pick up a red cup at kitchen"]) == 0
    assert json.loads(capsys.readouterr().out) == payload


@pytest.mark.parametrize("json_output", [False, True])
def test_preview_errors_follow_output_mode(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
        json_output: bool) -> None:
    """Invalid previews fail clearly in human and machine modes without publishing.

    Args:
        monkeypatch: Fixture replacing model inference with validation failure.
        capsys: Fixture capturing error output.
        json_output: Whether machine-compatible output was requested.
    """
    monkeypatch.setattr(cli_module, "preview_plan", Mock(side_effect=ValueError("no valid plan")))
    arguments = ["--plan-only", "--no-color", "invalid command"]
    if json_output:
        arguments.insert(0, "--json")
    assert main(arguments) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    if json_output:
        assert json.loads(captured.err) == {"event": "preview_failed", "reason": "no valid plan"}
    else:
        assert "no valid plan" in captured.err
        assert '"event"' not in captured.err


def test_waypoints_are_a_readable_table(
        tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Measured waypoint units and orientation are visible without reading YAML/JSON.

    Args:
        tmp_path: Temporary waypoint database directory.
        capsys: Fixture capturing table output.
    """
    path = tmp_path / "waypoints.yaml"
    path.write_text("frame: map\nwaypoints:\n  home: {x: 1.2, y: -0.5, yaw: 1.57}\n")
    assert list_waypoints(path, color=False) == 0
    output = capsys.readouterr().out
    assert "home" in output and "1.200" in output and "-0.500" in output
    assert "YAW (rad)" in output and "map" in output
    assert '"waypoints"' not in output


def test_waypoint_json_and_missing_file_errors_remain_machine_readable(
        tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """JSON mode remains available for both successful and failed waypoint reads.

    Args:
        tmp_path: Temporary waypoint database directory.
        capsys: Fixture capturing machine output.
    """
    path = tmp_path / "waypoints.yaml"
    path.write_text("frame: map\nwaypoints:\n  home: {x: 0, y: 0, yaw: 0}\n")
    assert list_waypoints(path, json_output=True) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["frame"] == "map" and "home" in payload["waypoints"]
    assert list_waypoints(tmp_path / "missing.yaml", json_output=True) == 1
    assert json.loads(capsys.readouterr().err)["event"] == "waypoint_error"


def test_no_color_flag_overrides_forced_color(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    """A user can request clean captured output despite forced-color environment settings.

    Args:
        monkeypatch: Fixture controlling inference and color environment.
        capsys: Fixture capturing terminal output.
    """
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setattr(cli_module, "preview_plan", Mock(return_value=preview_payload()))
    assert main(["--plan-only", "--no-color", "find cup"]) == 0
    assert "\x1b" not in capsys.readouterr().out


def test_live_cli_options_reach_frontend_without_changing_the_command(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Display flags do not alter the requested mission or its ROS lifecycle.

    Args:
        monkeypatch: Fixture replacing ROS creation with observable mocks.
    """
    initialize, shutdown = Mock(), Mock()
    node = Mock()
    node.run.return_value = 0
    constructor = Mock(return_value=node)
    monkeypatch.setattr(cli_module.rclpy, "init", initialize)
    monkeypatch.setattr(cli_module.rclpy, "shutdown", shutdown)
    monkeypatch.setattr(cli_module.rclpy, "ok", Mock(return_value=True))
    monkeypatch.setattr(cli_module, "CliFrontend", constructor)
    assert main(["--json", "--no-color", "--quiet", "find red cup"]) == 0
    constructor.assert_called_once_with("find red cup", True, timeout_s=1800.0,
                                        json_output=True, color=False)
    initialize.assert_called_once()
    node.destroy_node.assert_called_once()
    shutdown.assert_called_once()
