"""Regression tests for geometry, color filtering and stable target identity.

Author: E-AIRA contributors. Hardware target: Jetson Orin NX, ROSMASTER M3 Pro.
"""

import math

import numpy as np
import pytest

from eira_perception.perception_core import (
    Detection, PositionFilter, TargetTrack, color_fraction, intersection_over_union,
    metric_depth, object_dimensions, split_target, target_request,
)


def test_correlated_request_and_legacy() -> None:
    """Preserve legacy labels and normalize correlation IDs."""
    assert target_request(' Red Cup ')['target'] == 'red cup'
    request = target_request('{"target":"cup","mission_id":"m1","action_id":3}')
    assert request == {'target': 'cup', 'mission_id': 'm1', 'action_id': '3'}


@pytest.mark.parametrize('payload', ['[]', '{"target":null}', '{"target":""}',
                                     '{"target":"cup","mission_id":[]}'])
def test_invalid_request_rejected(payload: str) -> None:
    """Reject malformed envelopes before changing active target state.

    Args:
        payload: Invalid serialized request.
    """
    with pytest.raises(ValueError):
        target_request(payload)


def test_exact_class_color_separation() -> None:
    """Color adjectives must not be mistaken for detector class substrings."""
    assert split_target('Red Cup') == ('cup', 'red')
    assert split_target('wine glass') == ('wine glass', '')


def test_red_and_blue_are_distinct() -> None:
    """A dominant-color request rejects same-class objects of another color."""
    red = np.full((20, 20, 3), (0, 0, 255), np.uint8)
    assert color_fraction(red, (0, 0, 20, 20), 'red') == 1.0
    assert color_fraction(red, (0, 0, 20, 20), 'blue') == 0.0
    assert color_fraction(red, (30, 30, 40, 40), 'red') == 0.0


def test_identity_does_not_switch_to_larger_neighbor() -> None:
    """Lock a track ID until loss instead of chasing the largest box each frame."""
    track = TargetTrack()
    selected = Detection((0, 0, 20, 20), 'cup', 0.9, 12)
    neighbor = Detection((30, 0, 60, 30), 'cup', 0.9, 13)
    assert track.select([selected]) is selected
    assert track.select([neighbor, selected]) is selected
    assert track.select([neighbor]) is None
    track.reset()
    assert track.select([neighbor]) is neighbor


def test_no_id_requires_spatial_association() -> None:
    """ID-less acquisition cannot jump to a disjoint object."""
    track = TargetTrack(minimum_iou=0.3)
    original = Detection((0, 0, 20, 20), 'cup', 0.9)
    adjacent = Detection((2, 0, 22, 20), 'cup', 0.9)
    distant = Detection((100, 0, 120, 20), 'cup', 0.9)
    track.select([original])
    assert track.select([distant]) is None
    assert track.select([adjacent]) is adjacent
    assert intersection_over_union((0, 0, 0, 0), (0, 0, 0, 0)) == 0.0


def test_trajectory_filter_resets_after_gap_or_jump() -> None:
    """Smooth small changes while avoiding history across distinct objects."""
    smoother = PositionFilter(alpha=0.5, reset_gap_s=1.0, maximum_jump_m=0.5)
    assert smoother.update((1.0, 0, 0), 1.0) == (1.0, 0, 0)
    assert smoother.update((1.2, 0, 0), 1.1)[0] == pytest.approx(1.1)
    assert smoother.update((1.3, 0, 0), 3.0)[0] == pytest.approx(1.3)
    assert smoother.update((3.0, 0, 0), 3.1)[0] == pytest.approx(3.0)
    with pytest.raises(ValueError):
        smoother.update((3.0, 0, 0), 3.0)
    with pytest.raises(ValueError):
        smoother.update((math.nan, 0, 0), 4.0)


def test_depth_units_and_invalid_encoding() -> None:
    """Millimeters and meters produce equivalent geometry."""
    assert metric_depth(np.array([[1234]], np.uint16))[0, 0] == pytest.approx(1.234)
    assert metric_depth(np.array([[1.234]], np.float32))[0, 0] == pytest.approx(1.234)
    with pytest.raises(ValueError):
        metric_depth(np.zeros((2, 2), np.uint8))
    with pytest.raises(ValueError):
        metric_depth(np.zeros((2, 2, 3), np.uint16))


def test_projected_volume_exposes_hidden_dimension_prior() -> None:
    """Avoid inventing a measured volume when hidden thickness is unobservable."""
    result = object_dimensions((0, 0, 100, 50), 1.0, 500, 500)
    assert result['width_m'] == pytest.approx(0.2)
    assert result['height_m'] == pytest.approx(0.1)
    assert result['volume_m3'] is None
    result = object_dimensions((0, 0, 100, 50), 1.0, 500, 500, thickness_m=0.1)
    assert result['volume_m3'] == pytest.approx(0.002)
    assert 'prior' in result['volume_method']
    with pytest.raises(ValueError):
        object_dimensions((0, 0, 100, 50), 1.0, 0, 500)
