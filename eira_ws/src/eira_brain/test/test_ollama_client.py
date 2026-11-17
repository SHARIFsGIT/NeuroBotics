#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for OllamaClient.extract_json — the defensive JSON extractor.

Small local models wrap plans in prose and code fences; the extractor must
recover the payload in every observed failure mode and return None (never
raise) on garbage. These tests pin that contract.

Author: E-AIRA contributors.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
"""

import pytest

from eira_brain.ollama_client import extract_json


class TestCleanPayloads:
    """Group regression checks for cleanpayloads."""
    def test_plain_array(self) -> None:
        """Verify plain array."""
        text = '[{"action": "navigate", "target": "kitchen"}]'
        assert extract_json(text) == [
            {"action": "navigate", "target": "kitchen"}]

    def test_plain_dict(self) -> None:
        """Verify plain dict."""
        text = '{"action": "stop"}'
        assert extract_json(text) == {"action": "stop"}

    def test_empty_array(self) -> None:
        """Verify empty array."""
        assert extract_json("[]") == []


class TestProseAndFences:
    """Group regression checks for proseandfences."""
    def test_fenced_json(self) -> None:
        """Verify fenced json."""
        text = ('Sure! Here is the plan:\n'
                '```json\n[{"action": "home"}]\n```\nGood luck!')
        assert extract_json(text) == [{"action": "home"}]

    def test_fenced_plain(self) -> None:
        """Verify fenced plain."""
        text = '```\n[{"action": "release"}]\n```'
        assert extract_json(text) == [{"action": "release"}]

    def test_prose_wrapped_array(self) -> None:
        """Verify prose wrapped array."""
        text = ('The robot should do the following: '
                '[{"action": "find", "target": "cup"}] '
                'and then stop.')
        assert extract_json(text) == [{"action": "find", "target": "cup"}]

    def test_trailing_commentary_after_array(self) -> None:
        """Verify trailing commentary after array."""
        text = '[{"action": "speak", "target": "done"}] hope this helps!'
        assert extract_json(text) == [{"action": "speak", "target": "done"}]

    def test_single_dict_in_prose(self) -> None:
        """Verify single dict in prose."""
        text = 'Answer: {"action": "grasp"} that is all.'
        assert extract_json(text) == {"action": "grasp"}


class TestGarbage:
    """Group regression checks for garbage."""
    @pytest.mark.parametrize("text", [
        "",                       # nothing
        "no json here at all",    # prose only
        "[unclosed bracket",      # malformed
        "{broken json",           # malformed
        "42",                     # JSON but scalar, not list/dict
        '"just a string"',        # JSON but scalar, not list/dict
        "null",                   # JSON but scalar, not list/dict
    ])
    def test_returns_none(self, text: str) -> None:
        """Verify returns none.

        Args:
            text: Input text.
        """
        assert extract_json(text) is None
