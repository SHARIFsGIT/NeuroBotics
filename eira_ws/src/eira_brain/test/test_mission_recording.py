"""Verify recorder process lifecycle and replay isolation without a live ROS graph.

Author: E-AIRA maintainers.
Hardware target: Jetson Orin NX / ROS 2 Humble (mocked process and topic boundaries).
"""

from collections import deque
import json
from pathlib import Path
import signal
import subprocess
import threading
import time
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest
import yaml

from eira_brain import mission_recorder as recording
from eira_brain.mission_recorder import (
    DEFAULT_TOPICS, MissionCapture, MissionRecorder, record_command, stop_process,
)
from eira_brain.mission_replayer import bag_topics, main, replay_command, replay_environment


@pytest.fixture
def recorder(tmp_path: Path) -> Any:
    """Create recorder callbacks with mocked ROS publication and short bounded timing."""
    node = object.__new__(MissionRecorder)
    params = dict(max_event_chars=4096, max_pending_missions=8, boundary_history_size=20,
                  storage_id='sqlite3', capture_config_files=[], use_sim_time=False,
                  compressed_color_topic='/camera/color/image_raw/compressed', jpeg_quality=75,
                  jpeg_max_fps=5.0, discovery_topics=['/eira/plan', '/eira/status'],
                  environment='hardware', random_seed=-1,
                  poll_period_s=.001, min_free_space_mb=1.0, discovery_timeout_s=.1,
                  minimum_capture_s=0.0, post_roll_s=0.0, flush_timeout_s=.01,
                  terminate_timeout_s=.01, kill_timeout_s=.01, max_capture_s=1.0,
                  space_check_period_s=1.0)
    node._p = params.__getitem__
    node.params = params
    node._base = tmp_path
    node._topics = list(DEFAULT_TOPICS)
    node._lock, node._closing = threading.RLock(), threading.Event()
    node._slots = threading.Semaphore(2)
    node._sessions, node._completed, node._threads = {}, deque(maxlen=20), []
    node.messages = []
    node._event_pub = SimpleNamespace(publish=node.messages.append)
    node.get_logger = lambda: SimpleNamespace(info=lambda text: None)
    node.get_subscriptions_info_by_topic = lambda topic: []
    return node


def test_record_command_has_no_shell_and_bounded_cache(tmp_path: Path) -> None:
    """Keep filenames literal and use a modest cache per Jetson recorder process."""
    command = record_command(tmp_path / 'bag with spaces', ['/scan', '/scan', '/tf_static'],
                             'sqlite3', tmp_path / 'qos.yaml', 'unique_recorder', True)
    assert command[:3] == ['ros2', 'bag', 'record']
    assert str(tmp_path / 'bag with spaces') in command
    assert command.count('/scan') == 1
    assert '--node-name' in command
    assert '--max-cache-size' in command
    assert '--use-sim-time' in command


@pytest.mark.parametrize('topics', [[], ['/scan', '--all'], ['/camera bad']])
def test_invalid_record_topics_are_rejected(tmp_path: Path, topics: list[str]) -> None:
    """Reject malformed arguments before launching any external process."""
    with pytest.raises(ValueError):
        record_command(tmp_path, topics, 'sqlite3', tmp_path / 'qos.yaml')


def test_stop_escalates_and_reaps_entire_process_group(monkeypatch: pytest.MonkeyPatch) -> None:
    """A stalled metadata flush must not leave a rosbag child alive indefinitely."""
    process = Mock(pid=123, poll=Mock(return_value=None))
    process.wait.side_effect = [subprocess.TimeoutExpired('bag', .01),
                                subprocess.TimeoutExpired('bag', .01), 0]
    signals = []
    monkeypatch.setattr(recording.os, 'killpg', lambda pid, sig: signals.append((pid, sig)))
    assert stop_process(process, .01, .01) == 'sigkill'
    assert signals == [(123, signal.SIGINT), (123, signal.SIGTERM), (123, signal.SIGKILL)]
    assert process.wait.call_count == 3


def test_ready_discovery_matches_specific_overlapping_recorder(recorder: Any) -> None:
    """An older recorder subscription cannot falsely mark the next mission ready."""
    recorder.get_subscriptions_info_by_topic = lambda topic: [SimpleNamespace(node_name='old')]
    assert not recorder._discovered('new')
    recorder.get_subscriptions_info_by_topic = lambda topic: [SimpleNamespace(node_name='new')]
    assert recorder._discovered('new')


def test_status_and_plan_prebuffer_survives_fast_terminal(
        recorder: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """A mission that finishes during process startup retains complete boundary sidecars."""
    thread = SimpleNamespace(start=lambda: None, is_alive=lambda: True)
    monkeypatch.setattr(recording.threading, 'Thread', lambda **kwargs: thread)
    for data in ({'state': 'PLANNING', 'mission_id': 'm-1', 'detail': 'planning'},
                 {'state': 'PLANNING', 'mission_id': 'queued', 'detail': 'queued'},
                 {'state': 'DONE', 'mission_id': 'm-1', 'detail': 'complete'}):
        recorder._on_status(SimpleNamespace(data=json.dumps(data)))
    recorder._on_plan(SimpleNamespace(data=json.dumps({'mission_id': 'm-1', 'actions': []})))
    assert set(recorder._sessions) == {'m-1'}
    session = recorder._sessions['m-1']
    assert session.terminal.is_set()
    assert len(session.history) == 3
    assert '-' not in session.node_name


def test_capture_writes_manifest_and_flushes_before_complete(
        recorder: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Process creation, subscription readiness and flushed storage are distinct events."""
    session = MissionCapture('m', recorder._base / 'mission_test', time.time())
    session.node_name = 'test_recorder'
    session.terminal_wall = time.time()
    session.terminal_state = 'DONE'
    session.terminal.set()
    recorder._sessions['m'] = session
    recorder.get_subscriptions_info_by_topic = lambda topic: [
        SimpleNamespace(node_name='test_recorder')]

    def popen(command: list[str], **kwargs: Any) -> Any:
        """Provide mock bag storage without spawning a process or publishing ROS data."""
        bag = Path(command[command.index('--output') + 1])
        bag.mkdir()
        (bag / 'metadata.yaml').write_text('mock_metadata: true\n')
        process = SimpleNamespace(returncode=None)
        process.poll = lambda: process.returncode
        return process

    def stop(process: Any, *args: Any) -> str:
        """Complete the mocked graceful metadata flush."""
        process.returncode = 0
        return 'sigint'

    monkeypatch.setattr(recording.subprocess, 'Popen', popen)
    monkeypatch.setattr(recording, 'stop_process', stop)
    recorder._capture(session)
    manifest = json.loads((session.path / 'mission.json').read_text())
    events = [json.loads(message.data)['event'] for message in recorder.messages]
    assert events == ['starting', 'recording', 'ready', 'finalizing', 'complete']
    assert manifest['result'] == 'complete'
    assert 'startup_gap_s' in manifest and 'discovery_gap_s' in manifest
    assert (session.path / 'boundary_events.jsonl').is_file()
    assert not recorder._sessions


def test_storage_failure_is_reported_without_claiming_success(
        recorder: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing executables/storage permissions must produce a failed manifest."""
    session = MissionCapture('m', recorder._base / 'mission_failure', time.time())
    session.node_name = 'test_recorder'
    recorder._sessions['m'] = session
    monkeypatch.setattr(recording.subprocess, 'Popen',
                        Mock(side_effect=OSError('disk unavailable')))
    recorder._capture(session)
    manifest = json.loads((session.path / 'mission.json').read_text())
    assert manifest['result'] == 'failed'
    assert all(json.loads(event.data)['event'] != 'complete' for event in recorder.messages)


def test_analysis_replay_remaps_every_topic_including_commands_and_tf(tmp_path: Path) -> None:
    """Default replay cannot send recorded commands or transforms to original topic names."""
    topics = ['/cmd_vel', '/arm6_joints', '/eira/command', '/tf', '/tf_static', '/eira/status']
    command = replay_command(tmp_path, topics, 'analysis', '/eira/replay')
    for topic in topics:
        assert f'{topic}:=/eira/replay{topic}' in command
    assert '--clock' not in command


def test_perception_replay_excludes_actuation_and_mission_commands(tmp_path: Path) -> None:
    """Perception mode selects only sensors/TF and target labels in a replay namespace."""
    command = replay_command(tmp_path, DEFAULT_TOPICS, 'perception', '/offline')
    selected = command[command.index('--topics') + 1:command.index('--remap')]
    assert '/scan' in selected
    assert '/cmd_vel' not in selected
    assert '/eira/command' not in selected
    assert '/eira/manipulation/request' not in selected


def test_isolated_replay_never_replays_recorded_actuator_outputs(tmp_path: Path) -> None:
    """Reprocessing requests in another DDS domain must still calculate fresh actuator outputs."""
    command = replay_command(tmp_path, DEFAULT_TOPICS, 'isolated', '/unused',
                             include_requests=True, use_clock=True)
    assert '/eira/manipulation/request' in command
    assert '/cmd_vel' not in command
    assert '/arm6_joints' not in command
    assert '--clock' in command
    assert '--remap' not in command


@pytest.mark.parametrize('domain', [None, 0, -1, 233])
def test_original_topic_replay_requires_explicit_other_domain(domain: int | None) -> None:
    """No accidental current-domain original-topic playback is allowed."""
    with pytest.raises(ValueError):
        replay_environment('isolated', domain, {'ROS_DOMAIN_ID': '0'})


def test_isolated_environment_is_local_and_does_not_mutate_parent() -> None:
    """DDS isolation is explicit and inherited only by replay processes."""
    parent = {'ROS_DOMAIN_ID': '0'}
    child = replay_environment('isolated', 42, parent)
    assert child['ROS_DOMAIN_ID'] == '42'
    assert child['ROS_LOCALHOST_ONLY'] == '1'
    assert parent == {'ROS_DOMAIN_ID': '0'}


def test_bag_metadata_and_dry_run_accept_mission_directory(
        tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Operators can inspect the exact replay command before any ROS activation."""
    bag = tmp_path / 'bag'
    bag.mkdir()
    metadata = {'rosbag2_bagfile_information': {'topics_with_message_count': [
        {'topic_metadata': {'name': '/scan'}}]}}
    (bag / 'metadata.yaml').write_text(yaml.safe_dump(metadata))
    assert bag_topics(tmp_path) == (bag, ['/scan'])
    assert main([str(tmp_path), '--dry-run']) == 0
    assert 'Preview only; playback has not started' in capsys.readouterr().out
    assert main([str(tmp_path), '--dry-run', '--json']) == 0
    assert json.loads(capsys.readouterr().out)['event'] == 'replay_plan'


def test_unsafe_default_namespace_and_clock_are_rejected(tmp_path: Path) -> None:
    """A root namespace or generated global clock cannot bypass default replay isolation."""
    with pytest.raises(ValueError):
        replay_command(tmp_path, ['/scan'], 'analysis', '/')
    with pytest.raises(ValueError):
        replay_command(tmp_path, ['/scan'], 'analysis', '/replay', use_clock=True)
