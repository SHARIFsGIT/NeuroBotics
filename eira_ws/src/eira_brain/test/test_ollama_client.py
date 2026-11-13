#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for OllamaClient.extract_json — the defensive JSON extractor.

Small local models wrap plans in prose and code fences; the extractor must
recover the payload in every observed failure mode and return None (never
raise) on garbage. These tests pin that contract.
"""

import pytest

from eira_brain.ollama_client import extract_json


class TestCleanPayloads:
    def test_plain_array(self):
        text = '[{"action": "navigate", "target": "kitchen"}]'
        assert extract_json(text) == [
            {"action": "navigate", "target": "kitchen"}]

    def test_plain_dict(self):
        text = '{"action": "stop"}'
        assert extract_json(text) == {"action": "stop"}

    def test_empty_array(self):
        assert extract_json("[]") == []


class TestProseAndFences:
    def test_fenced_json(self):
        text = ('Sure! Here is the plan:\n'
                '```json\n[{"action": "home"}]\n```\nGood luck!')
        assert extract_json(text) == [{"action": "home"}]

    def test_fenced_plain(self):
        text = '```\n[{"action": "release"}]\n```'
        assert extract_json(text) == [{"action": "release"}]

    def test_prose_wrapped_array(self):
        text = ('The robot should do the following: '
                '[{"action": "find", "target": "cup"}] '
                'and then stop.')
        assert extract_json(text) == [{"action": "find", "target": "cup"}]

    def test_trailing_commentary_after_array(self):
        text = '[{"action": "speak", "target": "done"}] hope this helps!'
        assert extract_json(text) == [{"action": "speak", "target": "done"}]

    def test_single_dict_in_prose(self):
        text = 'Answer: {"action": "grasp"} that is all.'
        assert extract_json(text) == {"action": "grasp"}


class TestGarbage:
    @pytest.mark.parametrize("text", [
        "",                       # nothing
        "no json here at all",    # prose only
        "[unclosed bracket",      # malformed
        "{broken json",           # malformed
        "42",                     # JSON but scalar, not list/dict
        '"just a string"',        # JSON but scalar, not list/dict
        "null",                   # JSON but scalar, not list/dict
    ])
    def test_returns_none(self, text):
        assert extract_json(text) is None
