"""Validated waypoint persistence shared by planner, recorder, and CLI.

Author: E-AIRA contributors.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
"""

import math
from pathlib import Path
from typing import Any

import yaml


def validate_waypoints(data: Any) -> dict[str, Any]:
    """Validate the complete database before using any coordinates.

    Args:
        data: Decoded YAML object.

    Returns:
        Normalized mapping containing frame and named waypoint poses.

    Raises:
        ValueError: Structure, frame, or numeric coordinates are invalid.
    """
    if not isinstance(data, dict):
        raise ValueError("waypoint database must be a mapping")
    frame = data.get("frame", "map")
    points = data.get("waypoints", {})
    if not isinstance(frame, str) or not frame or not isinstance(points, dict):
        raise ValueError("frame must be nonempty and waypoints must be a mapping")
    normalized = {}
    for name, pose in points.items():
        if not isinstance(name, str) or not name or not isinstance(pose, dict):
            raise ValueError("each waypoint must have a string name and mapping pose")
        try:
            coords = {key: float(pose.get(key, 0.0)) for key in ("x", "y", "yaw")}
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError(f"invalid coordinates for {name}") from exc
        if not all(math.isfinite(value) for value in coords.values()):
            raise ValueError(f"nonfinite coordinates for {name}")
        normalized[name.lower()] = coords
    return {"frame": frame, "waypoints": normalized}


def load_waypoints(path: Path) -> dict[str, Any]:
    """Load a waypoint database without accepting partial malformed data.

    Args:
        path: YAML database file.

    Returns:
        Validated frame and waypoint mapping.

    Raises:
        OSError: File cannot be read.
        ValueError: YAML syntax or schema is invalid.
    """
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid waypoint YAML: {exc}") from exc
    return validate_waypoints(data)
