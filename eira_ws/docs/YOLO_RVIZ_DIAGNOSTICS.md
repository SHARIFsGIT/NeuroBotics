# YOLO detection in RViz: isolate and verify each stage

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro, Jetson Orin NX, Dabai DCW2,
ROS 2 Humble / Python 3.10.

Seeing `/camera/color/image_raw` in RViz proves that RGB arrives. It does not
prove that YOLO runs. Bounding boxes are published as a **different image** on
`/eira/detect_image`. E-AIRA does not draw on the camera driver's raw topic.

| Topic | Contents | What it establishes |
|---|---|---|
| `/camera/color/image_raw` | Raw RGB image | Camera and RGB transport work |
| `/eira/detect_image` | RGB with YOLO boxes, class names and track IDs | Detector completed an inference |
| `/target_pose` | Calibrated, transformed object pose | Detection plus range, intrinsics and TF work |
| `/eira/vision/event` | Correlated `found`, `timeout`, `failed` events | A requested target completed acquisition or failed |

By default, `continuous_mode=false`: YOLO runs only during a find request and
stops after found/timeout/failure. A quiet detector image while idle is expected.
The image is rendered only while a viewer subscribes, to save Jetson resources.
The continuous preview test below isolates detection from mission execution.

## 1. Use a stationary, isolated test session

Stop an existing E-AIRA master launch with Ctrl+C in its terminal before this
test. Do not leave Brain, grasp executor or another vision manager running.
Keep the robot stationary. This procedure starts only camera, vision and viewers;
it sends no navigation or arm requests. Keep your existing vendor installation,
weights and calibration.

In each terminal load the same ROS/vendor/E-AIRA environment. Replace the vendor
placeholder with the **actual working vendor workspace**, rather than copying
the placeholder literally:

```bash
source /opt/ros/humble/setup.bash
source /ABSOLUTE/PATH/TO/YOUR/VENDOR_WORKSPACE/install/setup.bash
export EIRA_WS="$HOME/NeuroBotics/eira_ws"
source "$EIRA_WS/install/setup.bash"
```

**Why:** all tools must use the same Humble interfaces, DDS configuration and
updated E-AIRA overlay. Expected: sourcing succeeds. Match `ROS_DOMAIN_ID` and
`RMW_IMPLEMENTATION` in terminals and remote RViz stations.

After updating source, build the changed packages once in a prepared terminal:

```bash
cd "$EIRA_WS"
colcon build --symlink-install --packages-select eira_perception eira_bringup
source "$EIRA_WS/install/setup.bash"
```

**Why:** installs updated Python entry points, parameter defaults and the RViz
preset. Expected: both packages finish successfully. Source the overlay again
in other terminals before using it. Prerequisite E-AIRA packages, including
`eira_brain`, must already have been built; use the
[fresh-start build sequence](FRESH_START_TESTING.md) for a fresh checkout.

## 2. Verify one camera stream

Use your existing camera launch if raw RGB already works. Otherwise start the
camera alone in T1:

```bash
ros2 launch orbbec_camera dabai_dcw2.launch.py \
  depth_registration:=true enable_point_cloud:=false \
  enable_colored_point_cloud:=false enable_ir:=false
```

**Why:** starts the native driver with registered depth and avoids unused point
cloud load. Expected: color and depth topics publish. Run only one camera driver.
Exercise 31's bare camera launch defaults registration off; registration matters
for measured 3D geometry, even when RGB bounding boxes already work.

In T3:

```bash
timeout 10s ros2 topic hz /camera/color/image_raw
ros2 topic info /camera/color/image_raw --verbose
timeout 10s ros2 topic hz /camera/depth/image_raw
```

**Why:** checks actual RGB/depth delivery and the publisher's QoS, rather than
only checking node names. Expected: repeated rate estimates and an RGB publisher.
`timeout` ending with status 124 is expected for these bounded rate observations.
RGB detection now continues if depth is absent; a missing depth stream still
needs investigation before measured grasping.

## 3. Start YOLO in continuous preview mode

The exercise uses this model location. Verify it on your robot and replace it
if your vendor workspace lives elsewhere:

```bash
export EIRA_YOLO_MODEL="/home/jetson/yahboomcar_ws/src/yahboom_yolov8/yahboom_yolov8/yolov8/weights/yolov8n.pt"
test -f "$EIRA_YOLO_MODEL"
```

**Why:** checks the real model artifact before launching. Expected: exit status
zero; a failed check means the model path needs correction. Do not use a model
name that would trigger a download or replace Jetson's working CUDA/Torch stack.

In T2, with the environment above loaded:

```bash
ros2 run eira_perception vision_manager --ros-args \
  --params-file "$EIRA_WS/src/eira_bringup/config/eira_params.yaml" \
  -p model_path:="$EIRA_YOLO_MODEL" \
  -p continuous_mode:=true \
  -p bbox_depth_enabled:=false
```

**Why:** runs one detector continuously for visualization while keeping assumed
cup-height distance estimation disabled. Bounding boxes do not require valid
depth, CameraInfo or TF. `/target_pose` still requires valid measured geometry.
The wildcard parameter file selects `vision_manager` by its unchanged node name.

**Expected:** wait for **“YOLO model ready for detection”** after loading and
warmup. Cold CUDA initialization uses `model_load_timeout_s` (45 seconds by
default), rather than the shorter per-frame inference timeout. Do not assume
that the node's earlier “Ready” line means the model is loaded.

E-AIRA supports the exercise's bundled Ultralytics source next to `weights/`.
If the source lives elsewhere, restart the same command with an explicit source
root containing an `ultralytics` directory:

```bash
ros2 run eira_perception vision_manager --ros-args \
  --params-file "$EIRA_WS/src/eira_bringup/config/eira_params.yaml" \
  -p model_path:="$EIRA_YOLO_MODEL" \
  -p yolo_source_dir:=/ABSOLUTE/PATH/CONTAINING/ultralytics \
  -p continuous_mode:=true -p bbox_depth_enabled:=false
```

**Why:** reproduces Exercise 31's explicit Python source-path setup inside the
isolated inference process. Replace the placeholder. Use this as an alternative
after stopping the first vision process, never as a second detector. Expected:
the same model-ready message; missing dependencies retain their actual errors.

## 4. Open the annotated image in RViz

On a terminal with a working desktop/display:

```bash
ros2 run rviz2 rviz2 -d "$EIRA_WS/src/eira_bringup/config/vision_debug.rviz"
```

**Why:** loads separate raw-RGB and YOLO image displays with appropriate QoS.
These are plain **Image** displays, so viewing boxes does not require CameraInfo
or a TF transform. Expected: the raw view is unannotated and the YOLO view shows
boxes on objects the model recognizes. Keep a well-lit cup clearly visible.

To configure existing RViz manually: **Add → Image → Topic →
`/eira/detect_image`**, with Reliable, Volatile, Keep Last and depth 1. The
raw camera display can stay on `/camera/color/image_raw` with Best Effort QoS.
Selecting the raw topic for both displays will show two raw images.

In T3, while RViz remains open:

```bash
ros2 topic info /eira/detect_image --verbose
timeout 10s ros2 topic hz /eira/detect_image
ros2 param get /vision_manager continuous_mode
ros2 param get /vision_manager model_path
```

**Why:** checks the actual detector publisher, viewer subscription, output rate
and active settings. Expected: one detector publisher, at least one viewer
subscription, a nonzero rate after warmup, `true` continuous mode and the model
path you selected. Output is throttled by `max_fps` and actual inference speed;
it is not expected to match the camera's 30 FPS. Topic presence alone does not
establish a completed inference.

## 5. Separate detection from geometry

| Observation | Next check |
|---|---|
| Raw RGB works; YOLO image has no frames | Correct RViz topic; model-ready/error lines; continuous mode; detector publisher/subscriber counts |
| YOLO image updates but has no boxes | Lighting, object size/visibility, model classes and confidence threshold |
| Boxes appear; no `/target_pose` | Depth, calibration, registration and capture-time TF; use the depth guide below |
| Boxes appear on another object but target never completes | Requested class/color must match the object; detection of any class does not satisfy `find cup` |
| Tracking dependency warning, then boxes appear | Detector has degraded to local object association; optional tracking wheels are unavailable |
| Images stop immediately after `found` in demand mode | Expected one-shot acquisition; use continuous preview only for this isolated test |

To inspect calibrated depth after boxes work, use
[Dabai depth diagnostics](DABAI_DEPTH_DEBUG.md). A 3D marker or target pose is a
later stage than a box overlay; failure to see a 3D marker does not establish
failure of YOLO itself.

## 6. Restore normal demand mode and test one request

Stop the continuous preview with Ctrl+C. Restart the same standalone detector
with `continuous_mode:=false`, or change its live setting while it is idle:

```bash
ros2 param set /vision_manager continuous_mode false
ros2 topic pub --once /eira/vision_target std_msgs/msg/String "{data: 'cup'}"
```

**Why:** restores normal CPU-saving behavior and starts one bounded search
without publishing a Brain command. Expected: “Searching for cup”, annotated
frames during acquisition, then found/timeout/failure and idle. Finding a target
requires a usable calibrated pose; with bbox estimation disabled, absent depth
can yield boxes followed by timeout. Open the RViz detector view **before**
the request because acquisition may finish quickly. Repeating a plain standalone
`cup` request starts another acquisition; Brain missions retain their ID-based
duplicate protection.

Finish by stopping the standalone detector before returning to the E-AIRA
master launch. Do not persist `continuous_mode=true` in mission parameters.

## What was checked in the code

All three files in `31. YOLOv8 object detection` were compared with E-AIRA.
The exercise subscribes RGB directly, adds Yahboom's source path before importing
Ultralytics, calls `model.track`, and publishes to `/detect_image`. E-AIRA's
existing topic remains `/eira/detect_image`; it is intentionally preserved.
E-AIRA retains BGR image handling, bounded process isolation, demand mode and
timestamped pose geometry rather than copying the exercise's unbounded callback.

| Exercise-31 implementation | E-AIRA adaptation |
|---|---|
| Hardcoded source-directory append and weight path | Configurable model/source paths with the vendor layout supported |
| `rgb8` conversion passed to the NumPy inference path | `bgr8` conversion consistent with the OpenCV/YOLO image path and output encoding |
| RGB subscription queue of 100 | Bounded sensor-data buffering and at most one inference job |
| Synchronous tracking inside the image callback | Killable inference worker; ROS callbacks remain available |
| Prints complete result objects every frame | Throttled, readable status and failure diagnostics |
| Annotated output omits its source header | Annotated image preserves the RGB acquisition header |
| Publishes `/detect_image` | Preserves E-AIRA's `/eira/detect_image` contract |

The deep queue and synchronous callback can accumulate old images under load;
those exercise patterns are not copied into the mission stack.

The review corrected depth-gated RGB inference, vendor-source import support,
cold inference warmup, geometry failures consuming model retry budgets, and
small depth ROIs accidentally sampling background outside the detection box.
Automated tests exercise these paths with mocked model and camera boundaries.
Actual CUDA inference and camera performance require this robot-side procedure;
they were not validated on the development host.
