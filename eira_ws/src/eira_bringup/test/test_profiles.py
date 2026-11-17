"""Validate complete exercise coverage and explicit profile selection.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, hardware-free tests.
"""

from eira_bringup.profiles import PROFILES


def test_every_actual_exercise_is_mapped() -> None:
    """All actual numbered folders have an explicit integration workflow."""
    covered = {number for profile in PROFILES.values() for number in profile.exercises}
    assert covered == set(range(1, 34))


def test_mapping_profiles_do_not_start_motion_controllers() -> None:
    """Mapping/localization profiles must not implicitly start autonomous driving."""
    for name in ('gmapping', 'cartographer', 'slam_toolbox', 'rtabmap_mapping',
                 'rtabmap_localization', 'cartographer_localization'):
        assert not PROFILES[name].motion


def test_profile_argument_scalars_are_launch_strings() -> None:
    """JSON booleans and numbers must not become invalid launch substitutions."""
    from eira_bringup.profiles import launch_argument_values
    assert launch_argument_values({'use_sim_time': True, 'rate': 2.5, 'count': 3}) == {
        'use_sim_time': 'true', 'rate': '2.5', 'count': '3'}


def test_nonfinite_profile_argument_rejected() -> None:
    """A nonfinite launch scalar cannot be passed into a native node."""
    import pytest
    from eira_bringup.profiles import launch_argument_values
    with pytest.raises(ValueError):
        launch_argument_values({'rate': float('nan')})
