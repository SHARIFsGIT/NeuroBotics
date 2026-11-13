#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vision_manager.py — E-AIRA perception: YOLOv8 + RGB-D + TF2, with live video.

This node follows the proven Yahboom ROSMASTER M3 Pro tutorial patterns
(course folders 22/23/25/31/32) and is **never headless**: every synchronized
color+depth pair is annotated (bounding boxes, class names, confidence, live
distance) and published on ``/eira/detect_image`` so RViz always shows what
the perception layer sees.

Pipeline (per synchronized color+depth frame pair)
--------------------------------------------------
1. ``YOLO(yolov8n.pt).track(frame, persist=True, conf=0.4)`` on the color
   image — the exact acquisition call of the working folder-31/32 nodes.
2. The requested target class (case-insensitive match) is located; the
   distance is read from the depth image at the bounding-box center
   (median of a small ROI around it — robust against the zero/NaN pixels
   depth cameras produce at object edges).
3. Pixel + depth → camera-frame 3-D point by pinhole deprojection using the
   **live** intrinsics from ``/camera/color/camera_info``.
4. Camera frame → ``base_link`` via TF2 (the eye-in-hand chain).
5. Results:
   * ``/target_pose``   — geometry_msgs/PoseStamped in ``base_link``
   * ``/eira/detect_image`` — annotated live view of the detector
   * ``/eira/vision/event``  — JSON lifecycle events for the brain

Topic contract
--------------
  subscribe  /camera/color/image_raw    sensor_msgs/Image    (sensor QoS)
  subscribe  /camera/depth/image_raw    sensor_msgs/Image    (sensor QoS)
  subscribe  /camera/color/camera_info  sensor_msgs/CameraInfo
  subscribe  /eira/vision_target       std_msgs/String      (dynamic object label)
  publish    /target_pose               geometry_msgs/PoseStamped (base_link)
  publish    /eira/detect_image         sensor_msgs/Image    (annotated)
  publish    /eira/vision/event         std_msgs/String      (JSON)

The depth stream of the Dabai_DCW2 is registered to the color image (the
audited grasp tutorials sample depth at color-box pixels directly); this
node keeps that assumption.

Startup failures (ultralytics / weights missing) exit cleanly with an
actionable message instead of a traceback — a perception node that cannot
perceive should say so, not sit silently.
"""

import json
import sys
import time

import cv2
import numpy as np

import rclpy
import tf2_geometry_msgs  # noqa: F401 — registers the PointStamped/PoseStamped
# transformers tf2_ros.Buffer.transform() dispatches on (without it the
# call raises tf2.TypeException and kills the callback).
import tf2_ros
from cv_bridge import CvBridge, CvBridgeError

from geometry_msgs.msg import PointStamped, PoseStamped
from message_filters import ApproximateTimeSynchronizer, Subscriber
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time

from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import String


class VisionManager(Node):
    """YOLOv8 detection + depth fusion → 3-D target pose in base_link.

    Always runs the detector and always publishes the annotated frame; the
    ``find`` request from the brain merely (re)arms the search session and
    swaps the target class.
    """

    def __init__(self):
        super().__init__("vision_manager")

        # --------------------------------------------------------
        # PARAMETERS (defaults mirror the audited course files)
        # --------------------------------------------------------
        # Weights used by the working folder-31 node.
        self.declare_parameter(
            "model_path",
            "/home/jetson/yahboomcar_ws/src/yahboom_yolov8/"
            "yahboom_yolov8/yolov8/weights/yolov8n.pt")
        # Target class — a parameter so demos can hunt bottles, books, ...
        self.declare_parameter("target_class", "cup")
        self.declare_parameter("confidence", 0.4)
        # Topics (remappable without touching the code).
        self.declare_parameter("color_topic", "/camera/color/image_raw")
        self.declare_parameter("depth_topic", "/camera/depth/image_raw")
        self.declare_parameter("camera_info_topic", "/camera/color/camera_info")
        # Frames: color-optical frame comes from camera_info / image headers;
        # this parameter is only the fallback when headers are empty.
        self.declare_parameter("target_frame", "base_link")
        self.declare_parameter("camera_optical_frame",
                               "camera_color_optical_frame")
        # Color/depth are synchronized exactly like the proven transport
        # scripts (folders 22/23): ApproximateTimeSynchronizer, slop 0.5 s.
        self.declare_parameter("sync_slop_s", 0.5)
        # Robust depth: median over a (2r+1)^2 window at the box center.
        self.declare_parameter("depth_roi_half", 3)
        self.declare_parameter("min_depth_m", 0.10)
        self.declare_parameter("max_depth_m", 3.0)
        # Find-session timing (consumed by the brain's WAIT_FIND state).
        self.declare_parameter("find_timeout_s", 20.0)
        self.declare_parameter("lost_after_s", 1.5)
        self.declare_parameter("tf_timeout_s", 0.15)

        # --------------------------------------------------------
        # MODEL — the lazy import gives an actionable error on machines
        # without the ultralytics stack instead of a raw traceback.
        # --------------------------------------------------------
        try:
            from ultralytics import YOLO  # noqa: WPS433 — deliberate lazy import
        except ImportError as exc:
            raise RuntimeError(
                "ultralytics is not installed "
                "(pip install ultralytics>=8, as on the Jetson course image)"
            ) from exc

        model_path = self.get_parameter("model_path").value
        self.get_logger().info(f"loading YOLOv8 weights: {model_path}")
        self._model = YOLO(model_path)
        self._class_names = self._model.names            # {id: label}
        self._conf = float(self.get_parameter("confidence").value)

        self._bridge = CvBridge()
        self._tf_buffer = tf2_ros.Buffer()
        self._tf_listener = tf2_ros.TransformListener(
            self._tf_buffer, self, spin_thread=True)

        # --------------------------------------------------------
        # STATE
        # --------------------------------------------------------
        self._target_class = str(
            self.get_parameter("target_class").value).strip().lower()
        self._searching = False        # find session active (deadline armed)
        self._search_deadline = None   # monotonic deadline for acquisition
        self._announced_found = False  # "found" edge for this acquisition
        self._tracking = False         # target visible on the last frame
        self._last_seen = None         # monotonic time of last valid pose
        self._pose_logged = False      # info-log "pose published" once/edge
        self._camera_info = None       # cached CameraInfo (live intrinsics)
        self._throttle = {}            # log-throttle timestamps, see below

        # --------------------------------------------------------
        # SUBSCRIPTIONS
        # Camera streams arrive with sensor-data (best-effort) QoS from the
        # Orbbec driver — subscribing with the matching profile is what makes
        # the frames actually arrive (reliable subscribers do NOT match a
        # best-effort publisher and silently receive nothing).
        # --------------------------------------------------------
        color_sub = Subscriber(
            self, Image, self.get_parameter("color_topic").value,
            qos_profile=qos_profile_sensor_data)
        depth_sub = Subscriber(
            self, Image, self.get_parameter("depth_topic").value,
            qos_profile=qos_profile_sensor_data)
        self._sync = ApproximateTimeSynchronizer(
            [color_sub, depth_sub],
            queue_size=10,
            slop=float(self.get_parameter("sync_slop_s").value))
        self._sync.registerCallback(self._on_synced_images)

        self.create_subscription(
            CameraInfo, self.get_parameter("camera_info_topic").value,
            self._on_camera_info, qos_profile_sensor_data)

        # Dynamic target switching: the brain publishes the object label it
        # wants found (e.g. 'bottle') whenever a plan contains a 'find'
        # action. Until a message arrives the node hunts its 'target_class'
        # parameter (default 'cup').
        self.create_subscription(
            String, "/eira/vision_target", self._on_target, 10)

        # --------------------------------------------------------
        # PUBLISHERS
        # --------------------------------------------------------
        self._target_pose_pub = self.create_publisher(
            PoseStamped, "/target_pose", 10)
        self._detect_image_pub = self.create_publisher(
            Image, "/eira/detect_image", 10)
        self._event_pub = self.create_publisher(
            String, "/eira/vision/event", 10)

        # Housekeeping timer: emits timeout/lost lifecycle events.
        self.create_timer(0.5, self._housekeeping)

        self.get_logger().info(
            f"vision_manager ready: model={model_path}, "
            f"classes={len(self._class_names)}, conf={self._conf}")
        self.get_logger().info(
            f"Searching for '{self._target_class}'...")

    # ========================================================
    # CALLBACKS
    # ========================================================

    def _on_camera_info(self, msg: CameraInfo):
        # K arrives row-major: fx 0 cx / 0 fy cy / 0 0 1. The audited grasp
        # code hardcodes these intrinsics; we read them live instead.
        self._camera_info = msg

    def _on_target(self, msg: String):
        """Dynamic target switching — the brain names the object to find.

        Each message re-targets the YOLO search class on the fly (the label
        is matched case-insensitively against detections, bidirectionally:
        'red cup' matches the COCO class 'cup'). A new target also (re)arms
        the timed search session whose 'found'/'timeout' events on
        /eira/vision/event the brain's WAIT_FIND state consumes. Before any
        message arrives, the node hunts its 'target_class' param ('cup').
        """
        label = msg.data.strip().lower()
        if not label:
            return
        self._target_class = label
        self._announced_found = False
        self._pose_logged = False
        self._searching = True
        self._search_deadline = time.monotonic() + \
            float(self.get_parameter("find_timeout_s").value)
        self.get_logger().info(f"Searching for {label}...")

    def _on_synced_images(self, color_msg: Image, depth_msg: Image):
        """Main perception tick: detect → depth → deproject → TF → publish.

        Never raises: every failure path logs (throttled) and returns, so a
        bad frame or a missing transform costs one frame, not the node.
        """
        try:
            frame = self._bridge.imgmsg_to_cv2(
                color_msg, desired_encoding="bgr8")
            depth = self._bridge.imgmsg_to_cv2(
                depth_msg, desired_encoding="passthrough")
        except CvBridgeError as exc:
            if self._log_ready("cvbridge", 5.0):
                self.get_logger().warning(f"frame decode failed: {exc}")
            return

        # ---- 1. detection (folder-31/32 call, unchanged semantics) ----
        detections = self._collect_detections(
            self._model.track(
                frame, persist=True, conf=self._conf, verbose=False))

        target = self._select_target(detections)
        depth_m = None
        if target is not None:
            box, name, conf, track_id = target
            u, v = self._box_center(box)
            # ---- 2. depth at the bounding-box center (ROI median) ----
            depth_m = self._depth_at_center(depth, u, v)
            if depth_m is None and self._log_ready("depth", 5.0):
                self.get_logger().warning(
                    f"no valid depth at box center for '{name}' "
                    "(all-zero/NaN ROI or out of "
                    f"{self.get_parameter('min_depth_m').value}-"
                    f"{self.get_parameter('max_depth_m').value} m range)")

        # ---- visual feedback FIRST: the stream never goes dark ----
        self._publish_annotated(frame, detections, target, depth_m,
                                color_msg)

        if target is None or depth_m is None:
            self._tracking = False
            return

        # ---- 3. pixel → camera frame (pinhole, live intrinsics) ----
        point_cam = self._deproject(u, v, depth_m)
        if point_cam is None:
            if self._log_ready("camera_info", 5.0):
                self.get_logger().warning(
                    f"no CameraInfo yet on "
                    f"'{self.get_parameter('camera_info_topic').value}' "
                    "- cannot deproject; waiting for intrinsics")
                self._publish_event("tf_error", detail="camera_info missing")
            return

        # ---- 4. camera frame → base_link (live TF, eye-in-hand) ----
        pose_base = self._transform_to_base(point_cam, color_msg)
        if pose_base is None:
            self._tracking = False
            return  # warning already throttled inside

        # ---- 5. publish the 3-D contract topic ----
        self._target_pose_pub.publish(pose_base)
        if self._pose_logged:
            self.get_logger().debug("Target pose published")
        else:
            self._pose_logged = True
            self.get_logger().info("Target pose published")

        if not self._announced_found:
            self._announced_found = True
            self._searching = False
            self._publish_event(
                "found", label=name, confidence=conf, depth_m=depth_m,
                pixel=[int(u), int(v)], track_id=track_id)
            self.get_logger().info(
                f"{name.capitalize()} found! Distance: {depth_m:.2f}m")

        self._tracking = True
        self._last_seen = time.monotonic()

    # ========================================================
    # DETECTION
    # ========================================================

    def _collect_detections(self, results):
        """Flatten ultralytics results → [(box_xyxy, name, conf, track_id)].

        Track IDs are metadata, not a gate: a detection batch whose IDs have
        not been assigned yet is still used (dropping such batches made the
        previous version miss fresh detections after startup/target loss).
        """
        detections = []
        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            xyxys = self._to_np(boxes.xyxy).reshape(-1, 4)
            if xyxys.shape[0] == 0:
                continue
            class_ids = self._to_np(boxes.cls).reshape(-1).astype(int)
            confs = self._to_np(boxes.conf).reshape(-1)
            if boxes.id is not None:
                track_ids = self._to_np(boxes.id).reshape(-1).astype(int)
            else:
                track_ids = [-1] * len(class_ids)
            names = getattr(result, "names", None) or self._class_names
            for box, class_id, conf, track_id in zip(
                    xyxys, class_ids, confs, track_ids):
                name = str(names.get(int(class_id), "?")) \
                    if isinstance(names, dict) else str(names[int(class_id)])
                detections.append(
                    (box, name.lower(), float(conf), int(track_id)))
        return detections

    def _select_target(self, detections):
        """Best matching detection: case-insensitive containment, both ways
        ("red cup" request ↔ COCO "cup" class). Several instances → track
        the closest one (largest box area ≈ smallest range)."""
        best = None                       # (area, box, name, conf, track_id)
        for box, name, conf, track_id in detections:
            if not self._class_matches(name):
                continue
            area = float((box[2] - box[0]) * (box[3] - box[1]))
            if best is None or area > best[0]:
                best = (area, box, name, conf, track_id)
        if best is None:
            return None
        return best[1], best[2], best[3], best[4]

    def _class_matches(self, class_name: str) -> bool:
        request = self._target_class or ""
        if not class_name or not request:
            return False
        # Both sides lowered → case-insensitive; containment both ways so a
        # request of "red cup" matches class "cup" and vice versa.
        return (class_name in request) or (request in class_name)

    @staticmethod
    def _to_np(tensor) -> np.ndarray:
        """torch tensor OR numpy array → float64 numpy (stub-friendly)."""
        if hasattr(tensor, "cpu"):        # torch → cpu first
            tensor = tensor.cpu()
        if hasattr(tensor, "numpy"):      # torch → numpy
            tensor = tensor.numpy()
        return np.asarray(tensor, dtype=np.float64)

    # ========================================================
    # GEOMETRY
    # ========================================================

    @staticmethod
    def _box_center(box) -> tuple:
        u = (float(box[0]) + float(box[2])) / 2.0
        v = (float(box[1]) + float(box[3])) / 2.0
        return u, v

    def _depth_at_center(self, depth_image: np.ndarray, u: float, v: float):
        """Depth [m] at the bounding-box center or None when unusable.

        A (2r+1)² window around the exact center is median-filtered: depth
        cameras return zeros/NaNs at depth discontinuities, and a single
        center pixel would drop the target far too often. Handles both
        encodings produced by the Dabai_DCW2 driver: 16UC1 (mm, folders
        26-28 course nodes) and 32FC1 (m).
        """
        height, width = depth_image.shape[:2]
        ui, vi = int(round(u)), int(round(v))
        if not (0 <= ui < width and 0 <= vi < height):
            return None

        half = int(self.get_parameter("depth_roi_half").value)
        u0, u1 = max(0, ui - half), min(width, ui + half + 1)
        v0, v1 = max(0, vi - half), min(height, vi + half + 1)
        roi = np.asarray(depth_image[v0:v1, u0:u1], dtype=np.float64)

        if depth_image.dtype == np.uint16:
            roi = roi / 1000.0                       # mm → m
        elif depth_image.dtype not in (np.float32, np.float64):
            if self._log_ready("depth_dtype", 10.0):
                self.get_logger().warning(
                    f"unsupported depth encoding {depth_image.dtype} "
                    "(expected 16UC1 mm or 32FC1 m)")
            return None

        lo = float(self.get_parameter("min_depth_m").value)
        hi = float(self.get_parameter("max_depth_m").value)
        valid = roi[np.isfinite(roi) & (roi >= lo) & (roi <= hi)]
        if valid.size == 0:
            return None
        return float(np.median(valid))

    def _deproject(self, u: float, v: float, depth_m: float):
        """Pixel + depth → camera-frame point using the live camera_info K.

        Standard pinhole model (same math as the folder-23 grasp code, but
        with live intrinsics): x = (u-cx)·z/fx, y = (v-cy)·z/fy, z = depth.
        """
        if self._camera_info is None:
            return None
        k = self._camera_info.k                        # row-major 3x3
        fx, fy, cx, cy = k[0], k[4], k[2], k[5]
        if fx <= 0.0 or fy <= 0.0:
            return None
        x = (u - cx) * depth_m / fx
        y = (v - cy) * depth_m / fy
        return x, y, depth_m

    def _transform_to_base(self, point_cam, color_msg: Image):
        """Camera-optical point → target_frame via the live TF tree.

        Returns a PoseStamped in the target frame, or None when the tree is
        unavailable (throttled warning — the robot keeps running; the grasp
        stage simply gets no fresh pose until TF recovers).
        """
        source = PointStamped()
        source.header.frame_id = self._optical_frame(color_msg)
        # Zero stamp = "latest available transform": robust against clock
        # skew between camera stamps and the TF tree on the eye-in-hand
        # chain (the arm moves, so we always want the freshest extrinsic).
        source.header.stamp = Time().to_msg()
        source.point.x, source.point.y, source.point.z = point_cam

        target_frame = self.get_parameter("target_frame").value
        timeout = rclpy.duration.Duration(
            seconds=float(self.get_parameter("tf_timeout_s").value))
        try:
            point_base = self._tf_buffer.transform(
                source, target_frame, timeout=timeout)
        except Exception as exc:  # noqa: BLE001 — TF must never kill the node
            # TransformException (lookup/extrapolation) is the expected
            # member; tf2.TypeException and friends are not its subclasses,
            # so the catch is deliberately broad — one bad frame costs one
            # skipped pose, never the process.
            if self._log_ready("tf", 5.0):
                self.get_logger().warning(
                    f"TF {source.header.frame_id} → {target_frame} "
                    f"unavailable ({exc}). Is the base bringup "
                    "(car_base.launch.py / robot_state_publisher) running?")
            return None

        pose = PoseStamped()
        pose.header = point_base.header
        pose.header.stamp = color_msg.header.stamp   # real measurement time
        pose.pose.position = point_base.point
        pose.pose.orientation.w = 1.0
        return pose

    def _optical_frame(self, color_msg: Image) -> str:
        """Color optical frame: camera_info > image header > parameter."""
        if self._camera_info is not None and self._camera_info.header.frame_id:
            return self._camera_info.header.frame_id
        if color_msg.header.frame_id:
            return color_msg.header.frame_id
        return self.get_parameter("camera_optical_frame").value

    # ========================================================
    # ANNOTATED VIDEO FEEDBACK (always on — never headless)
    # ========================================================

    def _publish_annotated(self, frame, detections, target, depth_m,
                           color_msg: Image):
        """Draw every detection; highlight the target with live distance."""
        annotated = frame.copy()

        for box, name, conf, _track_id in detections:
            is_target = target is not None and box is target[0]
            x0, y0 = int(box[0]), int(box[1])
            x1, y1 = int(box[2]), int(box[3])
            if is_target:
                cv2.rectangle(annotated, (x0, y0), (x1, y1),
                              (0, 255, 0), thickness=3)
                u, v = self._box_center(box)
                cv2.drawMarker(
                    annotated, (int(u), int(v)), (0, 0, 255),
                    markerType=cv2.MARKER_CROSS, markerSize=20, thickness=2)
                label = f"{name} {conf:.2f}"
                if depth_m is not None:
                    label += f" {depth_m:.2f}m"      # e.g. "cup 0.85m"
            else:
                cv2.rectangle(annotated, (x0, y0), (x1, y1),
                              (128, 128, 128), thickness=1)
                label = f"{name} {conf:.2f}"
            cv2.putText(
                annotated, label, (x0, max(14, y0 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

        # Status HUD (top-left): mirrors the node's own logs.
        if target is not None and depth_m is not None:
            status = f"TRACKING {target[1]} {depth_m:.2f}m"
            status_color = (0, 255, 0)
        elif target is not None:
            status = f"TARGET {target[1]} (no valid depth)"
            status_color = (0, 165, 255)
        else:
            status = f"Searching for '{self._target_class}'..."
            status_color = (0, 215, 255)
        cv2.rectangle(annotated, (0, 0), (420, 28), (0, 0, 0), thickness=-1)
        cv2.putText(
            annotated, status, (8, 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)

        message = self._bridge.cv2_to_imgmsg(annotated, encoding="bgr8")
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = self._optical_frame(color_msg)
        self._detect_image_pub.publish(message)

    # ========================================================
    # EVENTS / HOUSEKEEPING
    # ========================================================

    def _publish_event(self, event: str, **fields):
        message = String()
        payload = {"event": event, "label": self._target_class,
                   "wall_time": time.time()}
        payload.update(fields)
        message.data = json.dumps(payload)
        self._event_pub.publish(message)

    def _housekeeping(self):
        """Lifecycle events: acquisition timeout and tracking loss."""
        now = time.monotonic()

        # Acquisition timeout — the brain retries or aborts (its policy).
        if (self._searching and self._search_deadline is not None
                and now > self._search_deadline):
            self._searching = False
            self._publish_event("timeout")
            self.get_logger().warning(
                f"no '{self._target_class}' found within "
                f"{self.get_parameter('find_timeout_s').value:.0f} s")

        # Tracking lost — stop feeding stale poses to the PID.
        lost_after = float(self.get_parameter("lost_after_s").value)
        if (self._announced_found and not self._tracking
                and self._last_seen is not None
                and now - self._last_seen > lost_after):
            self._announced_found = False
            self._pose_logged = False
            self._publish_event("lost")
            self.get_logger().warning(
                f"target '{self._target_class}' lost")

    # ========================================================
    # UTILITIES
    # ========================================================

    def _log_ready(self, key: str, period: float) -> bool:
        """True at most once per `period` seconds per key (log throttling)."""
        now = time.monotonic()
        due = self._throttle.get(key)
        if due is None or now >= due:
            self._throttle[key] = now + period
            return True
        return False


def main(args=None):
    rclpy.init(args=args)
    try:
        node = VisionManager()
    except RuntimeError as exc:
        # Actionable startup failure (missing ultralytics / weights):
        # message, clean shutdown, non-zero exit — no traceback.
        print(f"[vision_manager] FATAL: {exc}", file=sys.stderr, flush=True)
        rclpy.try_shutdown()
        return 1

    try:
        rclpy.spin(node)
    except (ExternalShutdownException, KeyboardInterrupt):
        pass  # SIGTERM/Ctrl-C — context is already shutting down
    finally:
        node.destroy_node()
        if rclpy.ok():
            # On SIGTERM rclpy's signal handler shuts the context itself;
            # a second shutdown call raises RCLError and spams a traceback.
            rclpy.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
