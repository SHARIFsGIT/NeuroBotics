#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""waypoint_recorder.py — interactive waypoint recording from RViz.

Workflow
--------
1. Start this node in a terminal and RViz with a map in another.
2. In RViz, use the "Publish Point" tool (toolbar) and click a location on
   the map — RViz publishes the click on ``/clicked_point``.
3. Return to this terminal: the node prints the coordinates and asks for a
   name ("kitchen", "table", "dock", ...).
4. The waypoint is appended to the live ``waypoints.yaml`` — the exact file
   the ``llm_task_planner`` loads its waypoint database from — using an
   atomic write (temp file + ``os.replace``) so a crash can never corrupt
   the existing content.

File resolution (first existing wins)
-------------------------------------
1. the ``waypoints_file`` ROS parameter, if given;
2. the source-tree master ``<workspace>/src/eira_bringup/config/waypoints.yaml``
   (derived from this file's own location, so it works in any workspace
   path; with ``colcon build --symlink-install`` this IS the installed file);
3. the installed ``eira_bringup`` share directory.

Why not ``eira_brain/config/waypoints.yaml``? The brain, the master launch
and the committed configuration all read ``eira_bringup``'s copy; writing
anywhere else would create a second, unused database.

Threading note
--------------
The subscription callback only enqueues the point; all terminal interaction
(``input()``) happens on the main thread while the executor spins on a
background thread — blocking on stdin never stalls ROS callbacks.

Topic contract
--------------
  subscribe  /clicked_point   geometry_msgs/PointStamped   (RViz Publish Point)

Author: E-AIRA contributors.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
"""

import os
import math
import tempfile
import queue
import re
import threading
from pathlib import Path

import rclpy
import yaml
from geometry_msgs.msg import PointStamped
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from ament_index_python.packages import PackageNotFoundError
from eira_brain.waypoint_store import load_waypoints

# This file: <ws>/src/eira_brain/eira_brain/waypoint_recorder.py
_SOURCE_TREE_CONFIG = Path(__file__).resolve().parents[2] / \
    "eira_bringup" / "config" / "waypoints.yaml"

_NAME_OK = re.compile(r"^[a-z0-9_\-]+$")

STARTUP_BANNER = """
============================================================
 Waypoint Recorder Active.
 Click 'Publish Point' in RViz and return to this terminal
 to name the location.
============================================================
"""


class WaypointRecorder(Node):
    """Records RViz "Publish Point" clicks as named waypoints."""

    def __init__(self) -> None:
        """Initialize validated dependencies and local state."""
        super().__init__("waypoint_recorder")

        # --------------------------------------------------------
        # PARAMETERS
        # --------------------------------------------------------
        self.declare_parameter("waypoints_file", "")
        self.declare_parameter("map_frame", "map")

        self._path = self._resolve_path()
        self._points = queue.Queue()

        # --------------------------------------------------------
        # SUBSCRIPTION  (RViz "Publish Point" tool)
        # --------------------------------------------------------
        self.create_subscription(
            PointStamped, "/clicked_point", self._on_clicked_point, 10)

        self.get_logger().info(
            f"waypoint database: {self._path}")

    # ========================================================
    # FILE RESOLUTION & ACCESS
    # ========================================================

    def _resolve_path(self) -> Path:
        """First existing candidate wins (see module docstring)."""
        candidates = []

        param_path = self.get_parameter("waypoints_file").value
        if param_path:
            return Path(param_path).expanduser().resolve()

        candidates.append(_SOURCE_TREE_CONFIG)

        try:
            from ament_index_python.packages import (
                get_package_share_directory)
            candidates.append(Path(
                get_package_share_directory("eira_bringup"),
                "config", "waypoints.yaml"))
        except PackageNotFoundError:  # package not installed — dev machines
            pass

        for candidate in candidates:
            if candidate.exists():
                return candidate.resolve()

        # An explicitly requested (but missing) file is still usable: we
        # create it with a fresh skeleton on first save.
        if candidates:
            return candidates[0]
        raise RuntimeError("no usable waypoints.yaml location found")

    def _load(self) -> dict:
        """Load validated data without overwriting malformed content.

        Returns:
            Existing database or a new map-frame skeleton.

        Raises:
            OSError: The database cannot be read.
            ValueError: The database schema is invalid.
        """
        if not self._path.exists():
            return {
                "frame": self.get_parameter("map_frame").value,
                "waypoints": {},
            }
        return load_waypoints(self._path)

    def waypoint_names(self) -> set:
        """Return the validated waypoint names currently on disk.
        Returns:
            Set of database waypoint names.
        """
        return set(self._load().get("waypoints", {}).keys())

    def save_waypoint(self, name: str, x: float, y: float, yaw: float = 0.0) -> int:
        """Atomically upsert one waypoint and return the new count.

        Note: PyYAML's safe_dump cannot preserve the hand-written comments
        in the committed file — they are replaced by clean (comment-free)
        YAML on first save. Content is preserved; commentary is not.
        """
        if not _NAME_OK.fullmatch(name) or not all(math.isfinite(v) for v in (x, y, yaw)):
            raise ValueError("invalid waypoint name or coordinates")
        data = self._load()
        data["waypoints"][name] = {
            "x": round(float(x), 3),
            "y": round(float(y), 3),
            "yaw": round(float(yaw), 3),
        }

        self._path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, filename = tempfile.mkstemp(prefix=".waypoints-", suffix=".yaml",
                                                dir=self._path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                yaml.safe_dump(data, handle, sort_keys=False, default_flow_style=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(filename, self._path)
        finally:
            if os.path.exists(filename):
                os.unlink(filename)
        return len(data["waypoints"])

    # ========================================================
    # ROS CALLBACK (enqueue only — never blocks on stdin)
    # ========================================================

    def _on_clicked_point(self, msg: PointStamped) -> None:
        # RViz "Publish Point" supplies x/y only; z carries no meaning for
        # a ground robot and is ignored.
        """Queue finite map-frame coordinates and reject other frames.

        Args:
            msg: Incoming ROS message.
        """
        try:
            expected = self._load()["frame"]
        except (OSError, ValueError) as exc:
            self.get_logger().error(f"waypoint database unreadable: {exc}")
            return
        if msg.header.frame_id != expected:
            self.get_logger().warning(
                f"clicked point frame {msg.header.frame_id!r} differs from {expected!r}")
            return
        if not all(math.isfinite(value) for value in (msg.point.x, msg.point.y)):
            return
        self._points.put((msg.point.x, msg.point.y))
        self.get_logger().debug(
            f"clicked point queued: ({msg.point.x:.3f}, {msg.point.y:.3f})")

    def next_point(self, timeout: float = 0.5) -> tuple[float, float] | None:
        """Block up to ``timeout`` s for the next click; None on timeout."""
        try:
            return self._points.get(timeout=timeout)
        except queue.Empty:
            return None


# ============================================================
# INTERACTIVE MAIN LOOP (terminal I/O lives here, not in ROS)
# ============================================================


def _ask_name(x: float, y: float) -> str:
    """Prompt until a valid name, '' (discard), or EOF/quit."""
    while True:
        print(f"\n[+] Point received: (x={x:.3f}, y={y:.3f})", flush=True)
        try:
            raw = input(
                "    Enter a name for this location "
                "(Enter to discard, 'q' to quit): ").strip()
        except EOFError:
            return "q"
        if raw.lower() in ("q", "quit", "exit"):
            return "q"
        if not raw:
            return ""                       # discard this point
        name = raw.lower().replace(" ", "_")
        if _NAME_OK.match(name):
            return name
        print(f"    '{name}' has unsupported characters; "
              "use letters, digits, '-', '_'.")


def _interactive_loop(node: WaypointRecorder) -> None:
    """Record clicked points until the user exits.

    Args:
        node: Active waypoint recorder.
    """
    while rclpy.ok():
        point = node.next_point(timeout=0.5)
        if point is None:
            continue
        x, y = point

        name = _ask_name(x, y)
        if name == "q":
            print("Quitting waypoint recorder.", flush=True)
            return
        if not name:
            print("    Point discarded.", flush=True)
            continue

        try:
            exists = name in node.waypoint_names()
        except (OSError, ValueError) as exc:
            node.get_logger().error(f"waypoint database unreadable: {exc}")
            continue
        if exists:
            try:
                answer = input(
                    f"    '{name}' already exists — overwrite? [y/N] "
                ).strip().lower()
            except EOFError:
                answer = "n"
            if answer not in ("y", "yes"):
                print(f"    Kept existing '{name}'.", flush=True)
                continue

        try:
            count = node.save_waypoint(name, x, y)
        except (OSError, ValueError) as exc:
            node.get_logger().error(f"waypoint save failed: {exc}")
            continue
        print(f"    Saved '{name}' -> {node._path} "
              f"(now {count} waypoints).", flush=True)


def _spin_quietly(node: Node) -> None:
    """Spin wrapper: SIGTERM-triggered shutdowns exit without a traceback."""
    try:
        rclpy.spin(node)
    except ExternalShutdownException:
        pass


def main(args: list[str] | None = None) -> None:
    """Run the terminal waypoint recorder and ROS background executor.

    Args:
        args: Optional ROS command-line arguments.
    """
    rclpy.init(args=args)
    node = WaypointRecorder()

    # Executor on a background thread; the main thread owns stdin/stdout.
    spinner = threading.Thread(target=_spin_quietly, args=(node,), daemon=True)
    spinner.start()

    print(STARTUP_BANNER, flush=True)
    try:
        _interactive_loop(node)
    except KeyboardInterrupt:
        print("\nQuitting waypoint recorder.", flush=True)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
