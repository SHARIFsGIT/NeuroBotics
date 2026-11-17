# Dabai DCW2 depth acquisition and diagnostics

Author: E-AIRA maintainers.
Hardware target: Jetson Orin NX, ROS 2 Humble/Python 3.10, Dabai DCW2 RGB-D.

For environment setup and the ordered first robot test, start with
[the fresh-start testing guide](FRESH_START_TESTING.md).
For raw RGB without boxes in RViz, start with
[YOLO/RViz diagnostics](YOLO_RVIZ_DIAGNOSTICS.md): detection and 3D depth fusion
are separate stages, and the raw camera topic never contains YOLO overlays.

## Changes and root-cause checks

The earlier pipeline already took a valid-pixel median over a 7x7 center ROI.
It had no full-box/size fallback, rejected unequal RGB/depth dimensions,
deprojected only with color intrinsics, and rejected frames past its short age
limit. These code paths could prevent a visible YOLO detection from producing
a target pose. They do not establish why the physical sensor returns holes;
inspect its actual encoding, pixel statistics and registration using the debug
mode below.

RGB detection runs independently of depth delivery. `sync_slop_s` now bounds
the capture-time difference for an optional cached depth frame; it is not a
requirement for YOLO to receive RGB. Missing/corrupt/unregistered depth cannot
suppress the annotated image. When depth is absent, found-event depth timestamps,
ages and pair skew are null; the optional cup estimate uses the real RGB stamp.

The depth-processing sequence is:

1. Normalize explicit depth units.
2. Resize an already registered depth raster to the detector's color dimensions
   using nearest-neighbor sampling, preserving zero/NaN holes.
3. Try the finite, positive, in-range median in a 21x21 center ROI, clipped to
   the detected box so small objects do not inherit surrounding background depth.
4. If unavailable, try the full clipped detection box.
5. When explicitly enabled for `bbox_depth_class`, optionally estimate range
   using that class's configured height:
   `range_m = real_object_height_m * color_fy / bbox_height_pixels`.

The full-box median can include background. A height estimate depends on object
size, pose and occlusion. Neither is a guarantee of grasp accuracy. Found events
identify `depth_source` as `roi_median`, `bbox_median` or `bbox_estimate` and
include `depth_estimated`, `assumed_object_height_m`, `intrinsics_source`,
`depth_resized`, both camera timestamps/ages, and `pair_skew_s`.

## Configure the actual YAML used on the robot

The shipped `eira_bringup/config/eira_params.yaml` contains all defaults. Update
copied files such as `robot_test/params.yaml` too; a copied launch parameter file
overrides shipped defaults.

```yaml
/**:
  vision_manager:
    ros__parameters:
      depth_camera_info_topic: /camera/depth/camera_info
      depth_roi_half: 10
      sync_slop_s: 2.0
      image_freshness_s: 5.0
      max_image_age_s: 5.0
      bbox_depth_enabled: false
      bbox_depth_class: ''
      real_object_height_m: 0.1
      uint8_depth_scale_m: 0.0
      depth_debug: false
      depth_debug_every_n: 10
```

`image_freshness_s` is the active Vision age threshold. The older
`max_image_age_s` setting remains declared for parameter-file compatibility.
Frames older than the threshold warn and still run through detection; unstamped
or implausibly future-dated messages remain invalid. Camera topic and sync-slop
changes require a restart. Bbox estimation and depth debug can be toggled live.

Measured RGB-D ranging is the default for arbitrary requested objects. To opt
into a height estimate for a particular calibrated object, set
`bbox_depth_class` to its detector class and `real_object_height_m` to its measured
height, then enable `bbox_depth_enabled`. That prior applies only to the named
class. To disable the assumed-height fallback:

```bash
ros2 param set /vision_manager bbox_depth_enabled false
```

## Encoding and camera models

The first depth message logs its actual encoding and dimensions, even while
demand inference is idle. Supported units are:

| Encoding | Interpretation |
|---|---|
| `16UC1` | unsigned 16-bit millimetres, divided by 1000 |
| `mono16` | unsigned 16-bit millimetres on this depth input |
| `32FC1`, `64FC1` | floating-point metres |
| `8UC1`, `mono8` | unknown metric scale unless explicitly calibrated |

Unsupported scalar depth units become unavailable pixels so the color detector
can still attempt the optional cup-height estimate. Do not assign arbitrary
metres to a depth visualization. Set `uint8_depth_scale_m` only if the actual
producer documents a calibrated raw metre-per-code scale.

Vision subscribes to both existing color CameraInfo and the new depth CameraInfo
input. A fresh depth model is preferred when its optical frame matches the
incoming depth image. Its `fx`, `fy`, `cx`, `cy` are scaled from the calibration
dimensions to the resized sampling raster. For 640x400 to 640x480, `fy` and
`cy` scale by 1.2; horizontal values keep their scale. A mismatched-frame depth
model is ignored with a diagnostic. Missing matching depth calibration uses
color calibration and logs `Using color intrinsics for depth (approximation)`.
Queued inference retains calibration snapshots instead of using later messages.

**Raster resizing does not correct optical parallax, cropping or camera extrinsics.**
Keep native `depth_registration` enabled and verify the actual aligned output.
The retained `depth_registered` requirement excludes explicitly unregistered
depth from measured poses while RGB detection remains available. Proper geometric
registration uses both camera models and the transform
between them, as shown in the upstream
[Humble depth registration implementation](https://github.com/ros-perception/image_pipeline/blob/humble/depth_image_proc/src/register.cpp).

## Inspect a stationary detection

Use the stationary configuration in `ROBOT_TESTING_GUIDE.md`: navigation and
manipulation disabled, scans disabled, robot safely stationary. Inspect:

```bash
ros2 topic echo /camera/depth/image_raw --once --field encoding
ros2 topic echo /camera/depth/camera_info --once
ros2 topic echo /camera/color/camera_info --once
ros2 param get /vision_manager image_freshness_s
ros2 param get /vision_manager depth_roi_half
ros2 param set /vision_manager depth_debug true
ros2 run eira_brain eira_cli "find a cup"
```

Debug output prints five readable INFO lines on every tenth detected-target
frame: center depth/encoding, ROI median/count, full-box range, native image
dimensions, and the actual sampling intrinsics. Normal demand mode stops after
found. For several diagnostic frames, explicitly enable continuous mode during
the stationary test and then restore both switches:

```bash
ros2 param set /vision_manager continuous_mode true
# Observe the cup and the depth diagnostics.
ros2 param set /vision_manager continuous_mode false
ros2 param set /vision_manager depth_debug false
```

ROI failure logs `Depth unavailable at ROI, trying full box`; the last resort
logs `estimated from bbox`. That estimate is also labelled in the readable found
line. Optional depth probes/views retain native depth-pixel coordinates; the
detector samples the resized registered raster.

If all pixels are invalid, inspect the camera producer/stream and actual scene.
The bbox fallback provides a model-based estimate; it does not repair the depth
sensor. Use the native depth image view to distinguish local cup holes from a
globally invalid stream.

## Timestamp and logger guarantees

Measured-depth poses use the original depth acquisition timestamp; bbox estimates
use the original color timestamp. `measurement_stamp_ns` exactly matches
`/target_pose.header.stamp`. RGB/depth timestamps and pair skew are retained in
the event. No old measurement receives a new capture timestamp merely because
processing was delayed. ROS's image timestamp contract is documented in
[sensor_msgs/Image](https://github.com/ros2/common_interfaces/blob/humble/sensor_msgs/msg/Image.msg).

The arm retains its independent stale-pose checks. A delayed image may be useful
for detection/debugging while its pose is still too old for safe control.
Widening synchronization tolerance does not eliminate motion error between two
different camera capture times. Depth CameraInfo is now included in mission bags
and in isolated sensor replay when present; older bags can use the color fallback.

The Brain permanently uses `logger.info(format_status(payload))`. Brain, Vision
and Arm use fixed logger call sites rather than selecting severity methods with
`getattr`. Warning/error styling remains in the readable message. Regression
tests protect this ROS 2 Humble compatibility fix.
