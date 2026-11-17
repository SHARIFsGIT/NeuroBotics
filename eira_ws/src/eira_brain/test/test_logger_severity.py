"""Protect ROS 2 Humble's fixed-severity logger call-site contract.

Author: E-AIRA maintainers.
Hardware target: mocked ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
"""

import ast
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from eira_brain.llm_task_planner import LLMTaskPlanner
from test_mission_safety import brain  # noqa: F401 -- shared mocked orchestration fixture


def test_status_severity_changes_keep_one_info_call_site(
        brain: LLMTaskPlanner, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: F811
    """Warnings and failures remain readable without switching ROS severity.

    Args:
        brain: Planner with mocked publishers and no hardware participant.
        monkeypatch: Fixture selecting portable uncolored text.
    """
    monkeypatch.setenv('NO_COLOR', '1')
    logger = SimpleNamespace(info=Mock())
    brain.get_logger = lambda: logger
    brain._queue_sound = Mock()
    brain._publish_status('ready')
    brain._publish_status('navigation status 6', event='action_finished', action='navigate',
                          success=False, result='failed', error_reason='navigation status 6')
    brain._publish_status('retrying', event='recovery', recovery_kind='retry', retry_index=1)
    brain._publish_status('canceled', event='mission_finished', success=False, result='canceled')
    assert logger.info.call_count == 4
    lines = [call.args[0] for call in logger.info.call_args_list]
    assert 'Ready for commands' in lines[0]
    assert 'ERROR:' in lines[1] and 'Try 2D Pose Estimate in RViz' in lines[1]
    assert 'WARNING:' in lines[2] and 'Retrying' in lines[2]
    assert 'WARNING:' in lines[3] and 'Mission canceled' in lines[3]
    payloads = [json.loads(call.args[0].data)
                for call in brain._status_pub.publish.call_args_list]
    assert payloads[1]['error_reason'] == 'navigation status 6'
    assert payloads[3]['result'] == 'canceled'


@pytest.mark.parametrize('relative', [
    'eira_brain/eira_brain/llm_task_planner.py',
    'eira_manipulation/eira_manipulation/grasp_executor.py',
    'eira_perception/eira_perception/vision_manager.py',
])
def test_core_nodes_never_select_logger_methods_dynamically(relative: str) -> None:
    """Reject the dynamic logger selection that crashes Humble after severity changes.

    Args:
        relative: Core node path relative to the workspace source directory.
    """
    source = Path(__file__).resolve().parents[2] / relative
    tree = ast.parse(source.read_text(encoding='utf-8'))
    for call in ast.walk(tree):
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or (
                call.func.id != 'getattr') or not call.args:
            continue
        target = call.args[0]
        is_logger = isinstance(target, ast.Name) and target.id in ('logger', 'log')
        is_logger = is_logger or (isinstance(target, ast.Call) and isinstance(
            target.func, ast.Attribute) and target.func.attr == 'get_logger')
        assert not is_logger, f'{source}:{call.lineno} dynamically selects a logger method'
