"""Verify RViz's detector view and its installed resource contract.

Author: E-AIRA maintainers.
Hardware target: ROS 2 Humble, Jetson Orin NX / Dabai DCW2; no GUI or robot required.
"""

from pathlib import Path
import runpy

from pytest import MonkeyPatch
import setuptools
import yaml


PACKAGE = Path(__file__).resolve().parents[1]


def test_vision_debug_separates_raw_and_annotated_image_topics() -> None:
    """RViz must subscribe to the actual detector output using plain Image displays."""
    configuration = yaml.safe_load((PACKAGE / 'config/vision_debug.rviz').read_text())
    displays = configuration['Visualization Manager']['Displays']
    by_topic = {display['Topic']['Value']: display for display in displays}
    assert set(by_topic) == {'/camera/color/image_raw', '/eira/detect_image'}
    for display in displays:
        assert display['Class'] == 'rviz_default_plugins/Image'
        assert display['Enabled'] is True
        assert display['Topic']['Depth'] == 1
        assert display['Topic']['Durability Policy'] == 'Volatile'
    assert by_topic['/camera/color/image_raw']['Topic']['Reliability Policy'] == 'Best Effort'
    assert by_topic['/eira/detect_image']['Topic']['Reliability Policy'] == 'Reliable'


def test_vision_debug_resource_is_included_in_package_install(monkeypatch: MonkeyPatch) -> None:
    """The packaged RViz preset must remain available outside the source checkout.

    Args:
        monkeypatch: Restore setup interception and working directory after inspection.
    """
    metadata = {}
    monkeypatch.chdir(PACKAGE)
    monkeypatch.setattr(setuptools, 'setup', lambda **kwargs: metadata.update(kwargs))
    runpy.run_path(str(PACKAGE / 'setup.py'))
    resources = dict(metadata['data_files'])['share/eira_bringup/config']
    assert 'config/vision_debug.rviz' in resources
    assert 'config/eira_params.yaml' in resources
