"""Verify buzzer patterns without blocking callbacks or accessing robot hardware.

Author: E-AIRA maintainers.
Hardware target: mocked ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
"""

from collections import deque
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from eira_brain.llm_task_planner import LLMTaskPlanner


@pytest.fixture
def sound_brain() -> LLMTaskPlanner:
    """Construct a controller with only an observable buzzer interface.

    Returns:
        Planner fixture that cannot command wheels or servos.
    """
    node = object.__new__(LLMTaskPlanner)
    node._mission_lock = threading.RLock()
    node._sound_queue = deque(maxlen=32)
    node._sound_next_at = 0.0
    node._beep_pub = Mock()
    node._sound_parameters = {'sound_feedback': True, 'sound_short_ms': 100,
                              'sound_long_ms': 600, 'sound_gap_s': 0.15,
                              'sound_queue_size': 32}
    node.get_parameter = lambda name: SimpleNamespace(value=node._sound_parameters[name])
    return node


@pytest.mark.parametrize('event,expected', [
    ('mission_started', [100]), ('navigate', [100, 100]),
    ('find', [100, 100, 100]), ('grasp', [600]), ('failed', [600, 100]),
])
def test_requested_patterns_use_existing_uint16_topic(
        sound_brain: LLMTaskPlanner, monkeypatch: pytest.MonkeyPatch,
        event: str, expected: list[int]) -> None:
    """Each lifecycle cue emits the requested sequence with no blocking sleeps.

    Args:
        sound_brain: Planner with a mocked buzzer publisher.
        monkeypatch: Fixture controlling monotonic time and detecting sleeps.
        event: Lifecycle cue requested by the mission controller.
        expected: Buzzer durations in milliseconds.
    """
    clock = [10.0]
    monkeypatch.setattr(time, 'monotonic', lambda: clock[0])
    monkeypatch.setattr(time, 'sleep', Mock(side_effect=AssertionError('blocking sound')))
    sound_brain._queue_sound(event)
    for _ in expected:
        clock[0] += 1.0
        sound_brain._tick_sound()
    assert [call.args[0].data for call in sound_brain._beep_pub.publish.call_args_list] == expected


def test_tones_wait_for_duration_and_silent_gap(
        sound_brain: LLMTaskPlanner, monkeypatch: pytest.MonkeyPatch) -> None:
    """Two short beeps are separate pulses instead of overwriting one driver command.

    Args:
        sound_brain: Planner with short duration 100 ms and silent gap 150 ms.
        monkeypatch: Fixture controlling elapsed time.
    """
    clock = [10.0]
    monkeypatch.setattr(time, 'monotonic', lambda: clock[0])
    sound_brain._queue_sound('navigate')
    clock[0] = 10.24
    sound_brain._tick_sound()
    assert sound_brain._beep_pub.publish.call_count == 1
    clock[0] = 10.25
    sound_brain._tick_sound()
    assert sound_brain._beep_pub.publish.call_count == 2


def test_sound_can_be_disabled_with_pending_tones(sound_brain: LLMTaskPlanner) -> None:
    """Disabling feedback clears pending patterns and prevents direct fallback beeps.

    Args:
        sound_brain: Planner with no real actuator connections.
    """
    sound_brain._sound_parameters['sound_feedback'] = False
    sound_brain._sound_queue.extend([100, 600])
    sound_brain._tick_sound()
    sound_brain._queue_sound('mission_started')
    sound_brain._beep(100)
    sound_brain._beep_pub.publish.assert_not_called()
    assert not sound_brain._sound_queue
