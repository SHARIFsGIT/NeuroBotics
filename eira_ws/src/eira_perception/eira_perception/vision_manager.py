#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vision_manager.py — E-AIRA perception layer.

Function
--------
Wraps the two perception stacks already validated in this workspace:

* **Acquisition — YOLOv8** (course folder 31): ``ultralytics YOLO(yolov8n.pt)``
  runs ``model.track(frame, persist=True)`` on ``/camera/color/image_raw``.
  We keep the exact model path and inference call of the working course code.

* **Fine tracking — transformer tracker** (course folder 33): the
  ``smart_tracker`` package (``super_tracker`` ONNX node) consumes the same
  color stream (its ``/image_raw`` is remapped onto the camera topic) and is
  selected via ``/tracker_id``. Because that package is a pre-built binary on
  the robot, this node integrates it through a *configurable box topic*
  (``sensor_msgs/RegionOfInterest``). Set ``tracker_mode:=external`` and
  remap ``tracker_box_topic`` to the tracker's actual output (verify with
  ``ros2 topic list`` / ``ros2 topic echo`` on the robot) to run the
  transformer tracker in the loop; ``tracker_mode:=yolov8`` (default) uses
  YOLOv8's own track IDs, mirroring folder 32.

For every synchronized color+depth frame the manager computes the 3D centroid
of the requested object:

    pixel (u, v) + depth  --pinhole, K from /camera/color/camera_info-->  P_cam
    P_cam --tf2 (live eye-in-hand chain)-->  P_base

and publishes it on ``/target_pose`` (``geometry_msgs/PoseStamped``, frame
``base_link``) — the contract the manipulation layer closes its PID loop on.

Topic contract
--------------
  subscribe  /eira/vision/request        std_msgs/String      object label
  subscribe  /camera/color/image_raw     sensor_msgs/Image
  subscribe  /camera/depth/image_raw     sensor_msgs/Image
  subscribe  /camera/color/camera_info   sensor_msgs/CameraInfo
  subscribe  <tracker_box_topic>         sensor_msgs/RegionOfInterest (opt.)
  publish    /target_pose                geometry_msgs/PoseStamped (base_link)
  publish    /target_pose_camera         geometry_msgs/PoseStamped (optical)
  publish    /eira/vision/event          std_msgs/String (JSON)
  publish    /tracker_id                 std_msgs/Int16
  publish    detect_image                sensor_msgs/Image  (debug, folder 31 name)
"""

import json
import time

import cv2
import numpy as np

import rclpy
import tf2_ros
from cv_bridge import CvBridge

from geometry_msgs.msg import PointStamped, PoseStamped
from message_filters import ApproximateTimeSynchronizer, Subscriber
from rclpy.node import Node

from sensor_msgs.msg import CameraInfo, Image, RegionOfInterest
from std_msgs.msg import Int16, String


class VisionManager(Node):
    """YOLOv8 acquisition + tracker follow + depth-fused 3D target pose."""

    def __init__(self):
        super().__init__("vision_manager")

        # --------------------------------------------------------
        # PARAMETERS (defaults mirror the audited course files)
        # --------------------------------------------------------
        # Weights path used by the working folder-31 node.
        self.declare_parameter(
            "model_path",
            "/home/jetson/yahboomcar_ws/src/yahboom_yolov8/"
            "yahboom_yolov8/yolov8/weights/yolov8n.pt")
        self.declare_parameter("confidence", 0.5)
        # "yolov8"  — self-contained: YOLOv8 track IDs (folder 32 pattern)
        # "external"— transformer tracker provides the bbox (folder 33)
        self.declare_parameter("tracker_mode", "yolov8")
        self.declare_parameter("tracker_box_topic", "/tracker/box")
        # Frames: resolved against the live TF tree (eye-in-hand chain).
        self.declare_parameter("target_frame", "base_link")
        self.declare_parameter("camera_optical_frame",
                               "camera_color_optical_frame")
        # Robust depth: median over a (2*r+1)^2 window, zeros/NaNs rejected.
        self.declare_parameter("depth_roi_half", 3)
        self.declare_parameter("max_depth_m", 3.0)
        self.declare_parameter("min_depth_m", 0.10)
        # Event timing.
        self.declare_parameter("find_timeout_s", 20.0)
        self.declare_parameter("lost_after_s", 1.5)
        self.declare_parameter("publish_debug_image", True)

        # --------------------------------------------------------
        # MODEL (lazy fatal: the Jetson image has ultralytics installed)
        # --------------------------------------------------------
        from ultralytics import YOLO  # noqa: WPS433 — deliberate lazy import

        self._model = YOLO(self.get_parameter("model_path").value)
        self._class_names = self._model.names            # {id: label}
        self._conf = float(self.get_parameter("confidence").value)

        self._bridge = CvBridge()
        self._tf_buffer = tf2_ros.Buffer()
        self._tf_listener = tf2_ros.TransformListener(
            self._tf_buffer, self, spin_thread=True)

        # --------------------------------------------------------
        # TRACKING STATE
        # --------------------------------------------------------
        self._target_label = None        # requested object label (lowercase)
        self._search_deadline = None     # wall-clock deadline for acquisition
        self._last_seen = None           # last wall-clock time target was seen
        self._announced_found = False    # emitted "found" only once per task
        self._announced_lost = False
        self._tf_warned = False
        self._camera_info = None         # cached CameraInfo
        self._external_box = None        # latest RegionOfInterest + timestamp
        self._track_id = -1

        # --------------------------------------------------------
        # SUBSCRIPTIONS
        # --------------------------------------------------------
        # RGB + depth are synchronized exactly like the proven transport
        # scripts (folders 22/23): ApproximateTimeSynchronizer, slop 0.5 s.
        color_sub = Subscriber(self, Image, "/camera/color/image_raw")
        depth_sub = Subscriber(self, Image, "/camera/depth/image_raw")
        self._sync = ApproximateTimeSynchronizer(
            [color_sub, depth_sub], queue_size=1, slop=0.5)
        self._sync.registerCallback(self._on_synced_images)

        self.create_subscription(
            CameraInfo, "/camera/color/camera_info", self._on_camera_info, 10)

        self.create_subscription(
            String, "eira/vision/request", self._on_request, 10)

        if self.get_parameter("tracker_mode").value == "external":
            box_topic = self.get_parameter("tracker_box_topic").value
            self.create_subscription(
                RegionOfInterest, box_topic, self._on_external_box, 10)
            self.get_logger().info(
                f"external tracker mode: listening on {box_topic} "
                "(remap to smart_tracker's box output on the robot)")

        # --------------------------------------------------------
        # PUBLISHERS
        # --------------------------------------------------------
        self._target_pose_pub = self.create_publisher(
            PoseStamped, "target_pose", 10)
        self._target_pose_cam_pub = self.create_publisher(
            PoseStamped, "target_pose_camera", 10)
        self._event_pub = self.create_publisher(
            String, "eira/vision/event", 10)
        self._tracker_id_pub = self.create_publisher(Int16, "tracker_id", 10)
        self._debug_pub = self.create_publisher(Image, "detect_image", 1)

        # Housekeeping timer: emits timeout/lost events.
        self.create_timer(0.5, self._housekeeping)

        self.get_logger().info(
            f"vision_manager ready (classes={len(self._class_names)}, "
            f"mode={self.get_parameter('tracker_mode').value})")

    # ========================================================
    # CALLBACKS
    # ========================================================

    def _on_camera_info(self, msg: CameraInfo):
        # K arrives row-major: fx 0 cx / 0 fy cy / 0 0 1 (grasp_transport.py
        # hardcodes the same intrinsics; we read them live instead).
        self._camera_info = msg

    def _on_request(self, msg: String):
        """The brain asks for an object; (re)start acquisition."""
        label = msg.data.strip().lower()
        if not label:
            return
        self._target_label = label
        self._announced_found = False
        self._announced_lost = False
        self._track_id = -1
        # Deadline for acquisition; lost-tracking handling is separate.
        self._search_deadline = time.monotonic() + \
            float(self.get_parameter("find_timeout_s").value)
        self.get_logger().info(f"acquiring target: '{label}'")

    def _on_external_box(self, msg: RegionOfInterest):
        self._external_box = (msg, time.monotonic())

    def _on_synced_images(self, color_msg: Image, depth_msg: Image):
        """Main perception tick: detect → deproject → transform → publish."""
        if self._target_label is None:
            return  # idle: no inference cost until the brain asks (edge-friendly)

        frame_rgb = self._bridge.imgmsg_to_cv2(color_msg, "rgb8")
        depth = self._bridge.imgmsg_to_cv2(depth_msg, "passthrough")

        box, confidence, track_id = self._acquire_box(frame_rgb)
        if box is None:
            return  # housekeeping timer will emit lost/timeout events

        u, v = self._box_center(box)

        # ---- depth at the centroid (robust ROI median) ----
        depth_m = self._median_depth(depth, u, v)
        if depth_m is None:
            return

        # ---- pixel → camera frame (pinhole, folder-23 math) ----
        point_cam = self._deproject(u, v, depth_m)
        if point_cam is None:
            self._publish_event("tf_error", detail="camera_info not received")
            return

        # ---- camera frame → base_link (live TF, eye-in-hand aware) ----
        pose_base = self._transform_to_base(point_cam, color_msg.header.stamp)
        if pose_base is None:
            return  # warning already logged once

        # ---- publish the contract topics ----
        self._publish_pose(self._target_pose_cam_pub, point_cam,
                           self._optical_frame(color_msg),
                           color_msg.header.stamp)
        self._publish_pose(self._target_pose_pub, pose_base.point,
                           pose_base.header.frame_id, pose_base.header.stamp)

        if track_id is not None and track_id >= 0 and track_id != self._track_id:
            self._track_id = int(track_id)
            tracker_id = Int16()
            tracker_id.data = self._track_id
            self._tracker_id_pub.publish(tracker_id)  # smart_tracker handoff

        if not self._announced_found:
            self._announced_found = True
            self._announced_lost = False
            self._publish_event(
                "found", confidence=confidence, depth_m=depth_m,
                pixel=[int(u), int(v)], track_id=self._track_id)
            self.get_logger().info(
                f"target '{self._target_label}' found: "
                f"depth={depth_m:.3f} m, conf={confidence:.2f}")

        self._last_seen = time.monotonic()

        if self.get_parameter("publish_debug_image").value:
            self._publish_debug(frame_rgb, box, u, v, depth_m)

    # ========================================================
    # ACQUISITION / TRACKING
    # ========================================================

    def _acquire_box(self, frame_rgb: np.ndarray):
        """Return (box_xyxy, confidence, track_id) for the requested label.

        * yolov8 mode   — the exact ``model.track(persist=True)`` call of the
          course nodes (folders 31/32); picks the highest-confidence match of
          the requested class, keeps its track ID.
        * external mode — YOLOv8 only *verifies* the class every few frames;
          the transformer tracker (folder 33) supplies the box continuously.
        """
        if self.get_parameter("tracker_mode").value == "external":
            return self._acquire_external(frame_rgb)
        return self._acquire_yolov8(frame_rgb)

    def _acquire_yolov8(self, frame_rgb):
        results = self._model.track(
            frame_rgb, persist=True, conf=self._conf, verbose=False)
        best = None                       # (area, box, conf, tid)
        for result in results:
            boxes = result.boxes
            if boxes is None or boxes.id is None:
                continue
            class_ids = boxes.cls.cpu().numpy().astype(int)
            confidences = boxes.conf.cpu().numpy()
            xyxys = boxes.xyxy.cpu().numpy()
            track_ids = boxes.id.cpu().numpy().astype(int)
            for box, class_id, conf, tid in zip(
                    xyxys, class_ids, confidences, track_ids):
                name = str(self._class_names.get(class_id, "")).lower()
                if not self._label_matches(name):
                    continue
                # When several instances match, track the closest one
                # (largest bounding-box area ≈ smallest range).
                area = float((box[2] - box[0]) * (box[3] - box[1]))
                if best is None or area > best[0]:
                    best = (area, box, float(conf), int(tid))
        if best is None:
            return None, None, None
        return best[1], best[2], best[3]

    def _acquire_external(self, frame_rgb):
        """Transformer-tracker path: external box, YOLOv8 class verification."""
        if self._external_box is None:
            return None, None, None
        box_msg, stamp = self._external_box
        if time.monotonic() - stamp > 1.0:            # stale tracker output
            return None, None, None

        # Occasional YOLOv8 verification pass on the full frame.
        results = self._model.track(
            frame_rgb, persist=True, conf=self._conf, verbose=False)
        confidence = 0.0
        verified = False
        for result in results:
            boxes = result.boxes
            if boxes is None or len(boxes) == 0:
                continue
            for box, class_id, conf in zip(
                    boxes.xyxy.cpu().numpy(),
                    boxes.cls.cpu().numpy().astype(int),
                    boxes.conf.cpu().numpy()):
                name = str(self._class_names.get(class_id, "")).lower()
                if self._label_matches(name):
                    confidence = float(conf)
                    verified = True
                    break
            if verified:
                break

        box = np.array([
            float(box_msg.x_offset), float(box_msg.y_offset),
            float(box_msg.x_offset + box_msg.width),
            float(box_msg.y_offset + box_msg.height)])
        return box, confidence, None

    def _label_matches(self, class_name: str) -> bool:
        """Bidirectional containment: request "red cup" matches class "cup"."""
        request = self._target_label or ""
        if not class_name:
            return False
        return (class_name in request) or (request in class_name)

    # ========================================================
    # GEOMETRY
    # ========================================================

    @staticmethod
    def _box_center(box) -> tuple:
        u = (float(box[0]) + float(box[2])) / 2.0
        v = (float(box[1]) + float(box[3])) / 2.0
        return u, v

    def _median_depth(self, depth_image: np.ndarray, u: float, v: float):
        """Median depth over a small ROI; None when no valid samples.

        Handles both encodings produced by the Dabai_DCW2 driver: 16UC1
        (millimetres) and 32FC1 (metres), exactly as the depth-measurement
        course nodes (folders 26/27/28) do.
        """
        height, width = depth_image.shape[:2]
        ui, vi = int(u), int(v)
        half = int(self.get_parameter("depth_roi_half").value)
        if not (0 <= ui < width and 0 <= vi < height):
            return None

        u0, u1 = max(0, ui - half), min(width, ui + half + 1)
        v0, v1 = max(0, vi - half), min(height, vi + half + 1)
        roi = np.asarray(depth_image[v0:v1, u0:u1], dtype=np.float64)

        if depth_image.dtype == np.uint16:
            roi = roi / 1000.0                       # mm → m

        lo = float(self.get_parameter("min_depth_m").value)
        hi = float(self.get_parameter("max_depth_m").value)
        valid = roi[np.isfinite(roi) & (roi >= lo) & (roi <= hi)]
        if valid.size == 0:
            return None
        return float(np.median(valid))

    def _deproject(self, u: float, v: float, depth_m: float):
        """Pixel + depth → camera-frame point using the live camera_info K."""
        if self._camera_info is None:
            return None
        k = self._camera_info.k                        # row-major 3x3
        fx, fy, cx, cy = k[0], k[4], k[2], k[5]
        x = (u - cx) * depth_m / fx
        y = (v - cy) * depth_m / fy
        z = depth_m
        return x, y, z

    def _transform_to_base(self, point_cam, stamp):
        """camera-optical point → target_frame via the live TF tree.

        Returns a PointStamped in the target frame, or None when the tree is
        unavailable (logged once — a TF-free fallback belongs to future work
        because the eye-in-hand chain genuinely needs the arm joint states).
        """
        source = PointStamped()
        source.header.frame_id = self._optical_frame_from_info()
        source.header.stamp = stamp
        source.point.x, source.point.y, source.point.z = point_cam

        target_frame = self.get_parameter("target_frame").value
        try:
            return self._tf_buffer.transform(
                source, target_frame,
                timeout=rclpy.duration.Duration(seconds=0.15))
        except tf2_ros.TransformException as exc:
            if not self._tf_warned:
                self._tf_warned = True
                self.get_logger().warning(
                    f"TF {source.header.frame_id} → {target_frame} "
                    f"unavailable ({exc}). Is robot_state_publisher "
                    "(car_base.launch.py) running?")
            return None

    def _optical_frame(self, color_msg: Image) -> str:
        return color_msg.header.frame_id or \
            self.get_parameter("camera_optical_frame").value

    def _optical_frame_from_info(self) -> str:
        if self._camera_info is not None and self._camera_info.header.frame_id:
            return self._camera_info.header.frame_id
        return self.get_parameter("camera_optical_frame").value

    # ========================================================
    # PUBLISHING
    # ========================================================

    @staticmethod
    def _publish_pose(publisher, point, frame_id, stamp):
        pose = PoseStamped()
        pose.header.frame_id = frame_id
        pose.header.stamp = stamp
        pose.pose.position.x = float(point[0])
        pose.pose.position.y = float(point[1])
        pose.pose.position.z = float(point[2])
        pose.pose.orientation.w = 1.0
        publisher.publish(pose)

    def _publish_event(self, event: str, **fields):
        message = String()
        payload = {"event": event, "label": self._target_label,
                   "wall_time": time.time()}
        payload.update(fields)
        message.data = json.dumps(payload)
        self._event_pub.publish(message)

    def _publish_debug(self, frame_rgb, box, u, v, depth_m):
        annotated = frame_rgb.copy()
        cv2.rectangle(
            annotated,
            (int(box[0]), int(box[1])), (int(box[2]), int(box[3])),
            color=(0, 255, 0), thickness=2)
        cv2.drawMarker(
            annotated, (int(u), int(v)), color=(255, 0, 0),
            markerType=cv2.MARKER_CROSS, markerSize=18, thickness=2)
        cv2.putText(
            annotated, f"{self._target_label} {depth_m:.2f}m",
            (int(box[0]), max(12, int(box[1]) - 6)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
        self._debug_pub.publish(
            self._bridge.cv2_to_imgmsg(annotated, encoding="rgb8"))

    # ========================================================
    # HOUSEKEEPING (timeout / lost detection)
    # ========================================================

    def _housekeeping(self):
        if self._target_label is None:
            return

        now = time.monotonic()

        # Acquisition timeout — brain moves on (retry policy lives there).
        if (not self._announced_found and self._search_deadline is not None
                and now > self._search_deadline):
            self._publish_event("timeout")
            self.get_logger().warning(
                f"target '{self._target_label}' not found within deadline")
            self._target_label = None
            return

        # Tracking lost — stop feeding stale poses to the PID.
        lost_after = float(self.get_parameter("lost_after_s").value)
        if (self._announced_found and not self._announced_lost
                and self._last_seen is not None
                and now - self._last_seen > lost_after):
            self._announced_lost = True
            self._publish_event("lost")
            self.get_logger().warning(
                f"target '{self._target_label}' lost")


def main(args=None):
    rclpy.init(args=args)
    node = VisionManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
