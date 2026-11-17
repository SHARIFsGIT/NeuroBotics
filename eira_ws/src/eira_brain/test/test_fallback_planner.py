#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for the deterministic fallback planner (H1 ablation baseline).

The fallback parser is the no-LLM baseline of the paper, so its output for
the benchmark grammar must be pinned. The planner methods only use
class-level state (compiled regexes), so tests instantiate the node class
with object.__new__ to skip rclpy Node construction — no ROS context
needed.

Author: E-AIRA contributors.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
"""

import pytest

from eira_brain.llm_task_planner import LLMTaskPlanner

# Closed action vocabulary — the system's safety envelope.
KNOWN_ACTIONS = {"navigate", "find", "grasp", "release", "home", "speak",
                 "stop"}


@pytest.fixture()
def planner() -> LLMTaskPlanner:
    """Planner.
    Returns:
        Requested planner.
    """
    node = object.__new__(LLMTaskPlanner)  # no Node.__init__, no ROS context
    return node


def actions_of(plan: list[dict[str, str]]) -> list[str]:
    """Actions of.

    Args:
        plan: Input plan.

    Returns:
        Requested actions of.
    """
    return [step["action"] for step in plan]


class TestSingleClauses:
    """Group regression checks for singleclauses."""
    def test_stop(self, planner: LLMTaskPlanner) -> None:
        """Verify stop.

        Args:
            planner: Input planner.
        """
        assert planner._fallback_plan("stop") == [{"action": "stop"}]

    def test_stop_preempts_compound(self, planner: LLMTaskPlanner) -> None:
        """Verify stop preempts compound.

        Args:
            planner: Input planner.
        """
        plan = planner._fallback_plan("find the cup and stop")
        assert plan == [{"action": "stop"}]

    def test_fetch_chain(self, planner: LLMTaskPlanner) -> None:
        """Verify fetch chain.

        Args:
            planner: Input planner.
        """
        plan = planner._fallback_plan("bring me a cup from the kitchen")
        assert plan == [
            {"action": "navigate", "target": "kitchen"},
            {"action": "find", "target": "cup"},
            {"action": "grasp"},
            {"action": "navigate", "target": "mission_start"},
            {"action": "release"},
        ]

    def test_goto(self, planner: LLMTaskPlanner) -> None:
        """Verify goto.

        Args:
            planner: Input planner.
        """
        plan = planner._fallback_plan("go to the desk")
        assert plan == [{"action": "navigate", "target": "desk"}]

    def test_find(self, planner: LLMTaskPlanner) -> None:
        """Verify find.

        Args:
            planner: Input planner.
        """
        plan = planner._fallback_plan("find the bottle")
        assert plan == [{"action": "find", "target": "bottle"}]

    def test_pick_includes_find(self, planner: LLMTaskPlanner) -> None:
        """Verify pick includes find.

        Args:
            planner: Input planner.
        """
        plan = planner._fallback_plan("pick up the bottle")
        assert plan == [{"action": "find", "target": "bottle"},
                        {"action": "grasp"}]

    def test_home(self, planner: LLMTaskPlanner) -> None:
        """Verify home.

        Args:
            planner: Input planner.
        """
        plan = planner._fallback_plan("return home")
        assert plan == [{"action": "navigate", "target": "home"}]

    def test_release(self, planner: LLMTaskPlanner) -> None:
        """Verify release.

        Args:
            planner: Input planner.
        """
        plan = planner._fallback_plan("drop the object")
        assert plan == [{"action": "release"}]

    def test_unknown_becomes_speak(self, planner: LLMTaskPlanner) -> None:
        """Verify unknown becomes speak.

        Args:
            planner: Input planner.
        """
        plan = planner._fallback_plan("what is the weather tomorrow")
        assert plan == [{"action": "speak", "target": "command not understood"}]


class TestCompoundClauses:
    """Group regression checks for compoundclauses."""
    def test_and_split_two_finds(self, planner: LLMTaskPlanner) -> None:
        """Verify and split two finds.

        Args:
            planner: Input planner.
        """
        plan = planner._fallback_plan("find the cup and find the bottle")
        assert plan == [{"action": "find", "target": "cup"},
                        {"action": "find", "target": "bottle"}]

    def test_then_split(self, planner: LLMTaskPlanner) -> None:
        """Verify then split.

        Args:
            planner: Input planner.
        """
        plan = planner._fallback_plan("go to the kitchen and then find a cup")
        assert plan == [{"action": "navigate", "target": "kitchen"},
                        {"action": "find", "target": "cup"}]

    def test_goto_and_pick(self, planner: LLMTaskPlanner) -> None:
        """Verify goto and pick.

        Args:
            planner: Input planner.
        """
        plan = planner._fallback_plan("go to the desk and pick up the cup")
        assert plan == [{"action": "navigate", "target": "desk"},
                        {"action": "find", "target": "cup"},
                        {"action": "grasp"}]

    def test_fetch_and_home(self, planner: LLMTaskPlanner) -> None:
        """Verify fetch and home.

        Args:
            planner: Input planner.
        """
        plan = planner._fallback_plan(
            "fetch a cup from the kitchen and go home")
        assert plan == [
            {"action": "navigate", "target": "kitchen"},
            {"action": "find", "target": "cup"},
            {"action": "grasp"},
            {"action": "navigate", "target": "mission_start"},
            {"action": "release"},
            {"action": "navigate", "target": "home"},
        ]


class TestSafetyEnvelope:
    """Group regression checks for safetyenvelope."""
    @pytest.mark.parametrize("command", [
        "stop",
        "bring me a cup from the kitchen",
        "go to the desk and pick up the cup",
        "find the bottle and drop it",
        "what is the weather tomorrow",
        "fetch a cup from the kitchen and go home",
    ])
    def test_every_action_in_vocabulary(self, planner: LLMTaskPlanner, command: str) -> None:
        """Verify every action in vocabulary.

        Args:
            planner: Input planner.
            command: Input command.
        """
        plan = planner._fallback_plan(command)
        assert plan, "planner must never return an empty plan"
        for step in plan:
            assert step["action"] in KNOWN_ACTIONS, step

    def test_targets_are_words(self, planner: LLMTaskPlanner) -> None:
        """Verify targets are words.

        Args:
            planner: Input planner.
        """
        for step in planner._fallback_plan(
                "go to the kitchen and find the bottle"):
            if "target" in step:
                assert step["target"].replace("_", "").isalnum()
