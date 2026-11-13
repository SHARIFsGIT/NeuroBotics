#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for the deterministic fallback planner (H1 ablation baseline).

The fallback parser is the no-LLM baseline of the paper, so its output for
the benchmark grammar must be pinned. The planner methods only use
class-level state (compiled regexes), so tests instantiate the node class
with object.__new__ to skip rclpy Node construction — no ROS context
needed.
"""

import pytest

from eira_brain.llm_task_planner import LLMTaskPlanner

# Closed action vocabulary — the system's safety envelope.
KNOWN_ACTIONS = {"navigate", "find", "grasp", "release", "home", "speak",
                 "stop"}


@pytest.fixture()
def planner():
    node = object.__new__(LLMTaskPlanner)  # no Node.__init__, no ROS context
    return node


def actions_of(plan):
    return [step["action"] for step in plan]


class TestSingleClauses:
    def test_stop(self, planner):
        assert planner._fallback_plan("stop") == [{"action": "stop"}]

    def test_stop_preempts_compound(self, planner):
        plan = planner._fallback_plan("find the cup and stop")
        assert plan == [{"action": "stop"}]

    def test_fetch_chain(self, planner):
        plan = planner._fallback_plan("bring me a cup from the kitchen")
        assert plan == [
            {"action": "navigate", "target": "kitchen"},
            {"action": "find", "target": "cup"},
            {"action": "grasp"},
            {"action": "navigate", "target": "home"},
            {"action": "release"},
        ]

    def test_goto(self, planner):
        plan = planner._fallback_plan("go to the desk")
        assert plan == [{"action": "navigate", "target": "desk"}]

    def test_find(self, planner):
        plan = planner._fallback_plan("find the bottle")
        assert plan == [{"action": "find", "target": "bottle"}]

    def test_pick_includes_find(self, planner):
        plan = planner._fallback_plan("pick up the bottle")
        assert plan == [{"action": "find", "target": "bottle"},
                        {"action": "grasp"}]

    def test_home(self, planner):
        plan = planner._fallback_plan("return home")
        assert plan == [{"action": "navigate", "target": "home"}]

    def test_release(self, planner):
        plan = planner._fallback_plan("drop the object")
        assert plan == [{"action": "release"}]

    def test_unknown_becomes_speak(self, planner):
        plan = planner._fallback_plan("what is the weather tomorrow")
        assert plan == [{"action": "speak", "target": "command not understood"}]


class TestCompoundClauses:
    def test_and_split_two_finds(self, planner):
        plan = planner._fallback_plan("find the cup and find the bottle")
        assert plan == [{"action": "find", "target": "cup"},
                        {"action": "find", "target": "bottle"}]

    def test_then_split(self, planner):
        plan = planner._fallback_plan("go to the kitchen and then find a cup")
        assert plan == [{"action": "navigate", "target": "kitchen"},
                        {"action": "find", "target": "cup"}]

    def test_goto_and_pick(self, planner):
        plan = planner._fallback_plan("go to the desk and pick up the cup")
        assert plan == [{"action": "navigate", "target": "desk"},
                        {"action": "find", "target": "cup"},
                        {"action": "grasp"}]

    def test_fetch_and_home(self, planner):
        plan = planner._fallback_plan(
            "fetch a cup from the kitchen and go home")
        assert plan == [
            {"action": "navigate", "target": "kitchen"},
            {"action": "find", "target": "cup"},
            {"action": "grasp"},
            {"action": "navigate", "target": "home"},
            {"action": "release"},
            {"action": "navigate", "target": "home"},
        ]


class TestSafetyEnvelope:
    @pytest.mark.parametrize("command", [
        "stop",
        "bring me a cup from the kitchen",
        "go to the desk and pick up the cup",
        "find the bottle and drop it",
        "what is the weather tomorrow",
        "fetch a cup from the kitchen and go home",
    ])
    def test_every_action_in_vocabulary(self, planner, command):
        plan = planner._fallback_plan(command)
        assert plan, "planner must never return an empty plan"
        for step in plan:
            assert step["action"] in KNOWN_ACTIONS, step

    def test_targets_are_words(self, planner):
        for step in planner._fallback_plan(
                "go to the kitchen and find the bottle"):
            if "target" in step:
                assert step["target"].replace("_", "").isalnum()
