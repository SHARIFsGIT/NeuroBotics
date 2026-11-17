"""Check grounded JSON planning without a robot or local model server.

Author: E-AIRA contributors.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
"""

import json
from unittest.mock import Mock

import pytest

from eira_brain.ollama_client import (
    COCO_CLASSES, OllamaClient, build_system_prompt, parse_plan_json, validate_actions,
)


def test_dynamic_prompt_has_three_grounded_examples() -> None:
    """Few-shot plans must use only the supplied robot resources."""
    prompt = build_system_prompt(("lab", "dock"), ("wood block",))
    assert prompt.count("Example ") == 3
    assert 'Valid waypoints: ["dock", "lab"]' in prompt
    assert 'Valid detector classes: ["wood block"]' in prompt
    assert "kitchen" not in prompt
    assert "Valid actions: navigate, find, grasp, release, home, stop, speak." in prompt
    assert "Output ONLY a JSON array" in prompt
    assert len(COCO_CLASSES) == len(set(COCO_CLASSES)) == 80
    for line in prompt.splitlines():
        if line.startswith("Output: "):
            plan, _ = validate_actions(json.loads(line[8:]), ("lab", "dock"), ("wood block",))
            assert plan is not None


@pytest.mark.parametrize("text,expected", [
    ('```json\n[{"action":"home"}]\n```', [{"action": "home"}]),
    ('[{"action":"stop"}]', [{"action": "stop"}]),
    ('Here is [{"action":"home"}]', [{"action": "home"}]),
    ('Before ```JSON\n[{"action":"home"}]\n``` after', [{"action": "home"}]),
    ('Here is\n```json\n```\n[{"action":"stop"}]\n```\nDone', [{"action": "stop"}]),
    ('{"actions":[{"action":"home"}]}', [{"action": "home"}]),
    ('{"action":"home"}', None),
    ('[broken', None),
    ('[{"action":"home"},]', None),
    ('[{"action":"home"}] and [{"action":"stop"}]', None),
    ('```json\n[{"action":"home"}', None),
    ('Nothing to do', None),
])
def test_model_array_parser(text: str, expected: list | None) -> None:
    """Model prose/fences are removed while malformed or competing arrays fail.

    Args:
        text: Candidate response.
        expected: Expected parsed action array.
    """
    assert parse_plan_json(text) == expected


@pytest.mark.parametrize("plan", [
    [{"action": "navigate", "target": "unmapped"}],
    [{"action": "find", "target": "unicorn"}],
    [{"action": "find", "target": "purple cup"}],
    [{"action": "home", "target": "kitchen"}],
    [{"action": "navigate", "target": "home", "speed": 4.0}],
])
def test_invalid_grounding_rejects_entire_plan(plan: list) -> None:
    """Unknown resource targets and unrecognized action fields are rejected.

    Args:
        plan: Invalid candidate action sequence.
    """
    validated, reason = validate_actions(plan, ("home",))
    assert validated is None
    assert reason


def test_legacy_speech_is_still_valid() -> None:
    """Historical speak actions remain accepted by the complete-plan validator."""
    plan, _ = validate_actions([{"action": "speak", "target": "Acknowledged"}], ())
    assert plan == [{"action": "speak", "target": "Acknowledged"}]


def test_client_sends_dynamic_grounding(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP requests ground resources without forcing an incompatible object root.

    Args:
        monkeypatch: Test patch manager for the HTTP transport.
    """
    response = Mock()
    response.read.return_value = b'{"message":{"content":"[{\\"action\\":\\"home\\"}]"}}'
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    transport = Mock(return_value=response)
    monkeypatch.setattr("urllib.request.urlopen", transport)
    result = OllamaClient(retries=0).generate_plan(
        "home", waypoints=("dock",), object_classes=("wood block",), repair_reason="bad JSON")
    assert result == '[{"action":"home"}]'
    payload = json.loads(transport.call_args.args[0].data)
    assert "format" not in payload
    assert payload["stream"] is False
    assert transport.call_args.kwargs["timeout"] == 30.0
    prompt = payload["messages"][0]["content"]
    assert 'Valid waypoints: ["dock"]' in prompt
    assert "wood block" in prompt and "bad JSON" in prompt


def test_prompt_demonstrates_navigation_and_complete_fetch() -> None:
    """Phi-3 receives the requested compact examples with valid robot resource names."""
    prompt = build_system_prompt(("home", "kitchen", "mission_start"), ("cup",))
    assert "Example 1 input: go to the kitchen" in prompt
    assert 'Output: [{"action":"navigate","target":"kitchen"}]' in prompt
    assert "Example 2 input: bring me a cup from the kitchen" in prompt
    outputs = [json.loads(line.removeprefix("Output: ")) for line in prompt.splitlines()
               if line.startswith("Output: ")]
    assert outputs[1] == [
        {"action": "navigate", "target": "kitchen"},
        {"action": "find", "target": "cup"},
        {"action": "grasp"},
        {"action": "navigate", "target": "mission_start"},
        {"action": "release"},
    ]


def test_response_cleanup_does_not_bypass_action_validation() -> None:
    """Recovered arrays still reject unknown locations, classes, and unsafe grasp order."""
    for text in (
            'Sure! ```json\n[{"action":"navigate","target":"unmapped"}]\n```',
            'Plan: [{"action":"find","target":"unicorn"}] thanks',
            'Here is [{"action":"grasp"}]'):
        plan, reason = validate_actions(parse_plan_json(text), ("home",), ("cup",))
        assert plan is None
        assert reason


@pytest.mark.parametrize("command,expected", [
    ("find a stop sign", False),
    ("find stop sign and then go home", False),
    ("stop", True),
    ("please halt", True),
    ("Eira please cancel the mission", True),
    ("find cup and stop", True),
    ('{"command":"find a stop sign","mission_id":"stop"}', False),
    ('{"command":"abort now","mission_id":"trial"}', True),
])
def test_stop_is_an_imperative_clause(command: str, expected: bool) -> None:
    """Detector classes and JSON identifiers cannot accidentally trigger emergency stop.

    Args:
        command: Plain or enveloped instruction.
        expected: Whether the instruction requests immediate stop.
    """
    from eira_brain.ollama_client import is_stop_command
    assert is_stop_command(command) is expected
