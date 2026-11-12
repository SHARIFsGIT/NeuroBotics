#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
waypoint_recorder.py — interactive waypoint recording from RViz.

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
"""

import os
import queue
import re
import threading
from pathlib import Path

import rclpy
import yaml
from geometry_msgs.msg import PointStamped
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

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

    def __init__(self):
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
            candidates.append(Path(param_path).expanduser())

        candidates.append(_SOURCE_TREE_CONFIG)

        try:
            from ament_index_python.packages import (
                get_package_share_directory)
            candidates.append(Path(
                get_package_share_directory("eira_bringup"),
                "config", "waypoints.yaml"))
        except Exception:  # package not installed — dev machines
            pass

        for candidate in candidates:
            if candidate.exists():
                return candidate

        # An explicitly requested (but missing) file is still usable: we
        # create it with a fresh skeleton on first save.
        if candidates:
            return candidates[0]
        raise RuntimeError("no usable waypoints.yaml location found")

    def _load(self) -> dict:
        """Load the database; never raises on malformed/empty files —
        a broken file is backed up rather than silently overwritten."""
        if not self._path.exists():
            return {
                "frame": self.get_parameter("map_frame").value,
                "waypoints": {},
            }
        try:
            with open(self._path, "r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
        except yaml.YAMLError as exc:
            backup = self._path.with_suffix(".yaml.bak")
            os.replace(self._path, backup)
            self.get_logger().error(
                f"waypoints.yaml is malformed ({exc}); moved to {backup}, "
                "starting a fresh database")
            return {"frame": self.get_parameter("map_frame").value,
                    "waypoints": {}}
        data.setdefault("frame", self.get_parameter("map_frame").value)
        data.setdefault("waypoints", {})
        return data

    def waypoint_names(self) -> set:
        return set(self._load().get("waypoints", {}).keys())

    def save_waypoint(self, name: str, x: float, y: float, yaw: float = 0.0):
        """Atomically upsert one waypoint and return the new count.

        Note: PyYAML's safe_dump cannot preserve the hand-written comments
        in the committed file — they are replaced by clean (comment-free)
        YAML on first save. Content is preserved; commentary is not.
        """
        data = self._load()
        data["waypoints"][name] = {
            "x": round(float(x), 3),
            "y": round(float(y), 3),
            "yaw": round(float(yaw), 3),
        }

        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        with open(temp_path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(
                data, handle, sort_keys=False, default_flow_style=False,
                allow_unicode=True)
        os.replace(temp_path, self._path)      # atomic on POSIX
        return len(data["waypoints"])

    # ========================================================
    # ROS CALLBACK (enqueue only — never blocks on stdin)
    # ========================================================

    def _on_clicked_point(self, msg: PointStamped):
        # RViz "Publish Point" supplies x/y only; z carries no meaning for
        # a ground robot and is ignored.
        self._points.put((msg.point.x, msg.point.y))
        self.get_logger().debug(
            f"clicked point queued: ({msg.point.x:.3f}, {msg.point.y:.3f})")

    def next_point(self, timeout: float = 0.5):
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


def _interactive_loop(node: WaypointRecorder):
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

        if name in node.waypoint_names():
            try:
                answer = input(
                    f"    '{name}' already exists — overwrite? [y/N] "
                ).strip().lower()
            except EOFError:
                answer = "n"
            if answer not in ("y", "yes"):
                print(f"    Kept existing '{name}'.", flush=True)
                continue

        count = node.save_waypoint(name, x, y)
        print(f"    Saved '{name}' -> {node._path} "
              f"(now {count} waypoints).", flush=True)


def _spin_quietly(node: Node):
    """Spin wrapper: SIGTERM-triggered shutdowns exit without a traceback."""
    try:
        rclpy.spin(node)
    except ExternalShutdownException:
        pass


def main(args=None):
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
        rclpy.shutdown()


if __name__ == "__main__":
    main()
