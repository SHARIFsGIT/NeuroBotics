# Neurobotics — Differential Robot + 5-DOF Arm (ROS 2 Humble / Gazebo Classic)

A simulated mobile-manipulation robot: 4-wheel differential drive base,
6-DOF arm with a 2-finger gripper, a camera mounted on the arm (the DCW2
housing near the wrist) and a 360° 2D lidar. Everything runs in Gazebo
Classic with `ros2_control`.

```
      5-DOF arm + gripper          <- camera (DCW2 housing) looks along the arm;
          |                           line_follow.py bends the arm to aim it at
          |                           the floor (arm straight = camera sees sky)
      4-wheel diff-drive base      <- lidar on the front-right corner
```

---

## 1. Prerequisites

| Software | Version | Check with |
|---|---|---|
| Ubuntu | 22.04 | `lsb_release -a` |
| ROS 2 | Humble | `ros2 --help` |
| Gazebo Classic | 11.x | `gazebo --version` |
| Python OpenCV + Tk | — | `python3 -c "import cv2, tkinter"` |

Install the two Python extras if the check fails:

```bash
sudo apt install python3-opencv python3-tk
```

## 2. Build (one time, and after editing CMakeLists.txt / package.xml)

From the workspace root (`~/neurobotics_ws`):

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install
```

Then open the workspace in EVERY new terminal (or add it to `~/.bashrc`):

```bash
source ~/neurobotics_ws/install/setup.bash
```

> `--symlink-install` means most edits to `scripts/`, `launch/`, `urdf/`,
> `worlds/` and `config/` are live immediately — no rebuild needed.

## 3. Start the simulation

```bash
ros2 launch neurobotics gazebo.launch.py
```

You should see, in order (give it ~20 seconds):

1. Gazebo opens with a white floor, a black line course and three orange boxes
2. The robot spawns at the start of the line
3. Terminal prints `Configured and activated ...` for **joint_broad**, **diff_cont**, **arm_cont**

Options:

```bash
ros2 launch neurobotics gazebo.launch.py gui:=false    # headless (faster, no window)
ros2 launch neurobotics gazebo.launch.py rviz:=true    # also open RViz2
```

**Quick health check** (in a second terminal, workspace sourced):

```bash
ros2 control list_controllers        # all three should be "active"
ros2 topic list                      # /scan, /camera/image_raw, /joint_states, ...
```

| Topic | What it is | Expected rate |
|---|---|---|
| `/diff_cont/cmd_vel_unstamped` | drive commands (Twist) | you publish |
| `/diff_cont/odom` | wheel odometry | 30 Hz |
| `/scan` | 360° lidar | 10 Hz |
| `/camera/image_raw` | 640×480 arm camera (DCW2) | ~5 Hz headless, ~20 Hz with GUI |
| `/joint_states` | all joint angles | 30 Hz |
| `/arm_cont/commands` | 11 arm/gripper positions | you publish |

## 4. Test everything, step by step

Each script runs in a **second terminal** while the simulation keeps running.
Stop any script with `Ctrl+C` (all of them halt the robot on exit).

### 4.1 Drive teleop — `teleop.py`

```bash
ros2 run neurobotics teleop.py
```

| Key | Action | Key | Action |
|---|---|---|---|
| `i` / `,` | forward / backward | `1`..`0` | arm joints (see its help) |
| `j` / `l` | rotate left / right | `g` / `h` | gripper close / open |
| `k` | stop base | `SPACE` | emergency stop |
| `w` / `x` | linear speed ±10% | `q` / `z` | overall speed ±10% |

**Pass:** robot drives **forward** when you press `i` (away from where it
spawned, along the line), rotates in place with `j`/`l`.

### 4.2 Arm GUI — `arm_gui.py`

```bash
ros2 run neurobotics arm_gui.py
```

Drag the six sliders (5 joints + gripper) and watch the arm follow.
`HOME` zeroes everything; `OPEN/CLOSE GRIPPER` works the fingers.

**Pass:** the arm moves smoothly and the gripper fingers open/close together.

### 4.3 Line follower — `line_follow.py`

The robot must be **at the start of the line**. If you drove it away, either
drive it back with teleop or simply restart the simulation (close Gazebo,
relaunch). Then:

```bash
ros2 run neurobotics line_follow.py
```

> The camera looks straight out along the arm (the same direction the
> gripper points), so with the arm straight at HOME it points at the sky
> and sees no line at all — exactly like the real robot. `line_follow.py`
> handles this itself: it first holds the base still, then bends the arm
> forward (`arm2 = arm3 = −0.70`, `arm4 = −0.87` rad), which aims the
> camera about 40° down at the floor 0.4–1.4 m ahead. On Ctrl+C it halts
> the robot and returns the arm to HOME. Just make sure nothing else
> (like `arm_gui.py`) is holding the arm in another pose while it runs.

Two debug windows show what the robot sees (the camera's ROI and the black
line mask with a red centre dot).

**Pass:** the robot drives along the straight, follows the curve to the
right and keeps going down the second straight — staying centred on the tape.

### 4.4 Obstacle avoidance — `obstacle_avoid.py`

The three orange boxes beside the line are its targets.

```bash
ros2 run neurobotics obstacle_avoid.py
```

The script latches its heading from the **IMU** (`/imu`) at startup and
steers back to it whenever the path is clear — wheel odometry cannot see
rotation that happens through tyre scrub, so a heading lock built on it
slowly arcs away. When a box comes within **0.85 m** of the front ±45°
sector, it steers away from whichever side of the sector the box sits on
(box on the right → dodge left, and vice versa).

**Pass:** the robot holds a straight course, visibly swerves around the
right-side box (x ≈ 3.5) and the third box (x ≈ 5), and keeps going
straight. Keep the arm at HOME while this runs — a folded-forward arm
shows up as an obstacle dead ahead. Note the lidar sits on the
**front-right corner**, so right-side boxes are seen earlier than
left-side ones; the first box (left, x ≈ 2) is usually threaded with
clearance rather than dodged.

### 4.5 See the lidar data — `lidar_view.py`

Three ways, from quickest to nicest:

```bash
ros2 topic echo /scan --once    # one full 360-beam sweep, raw numbers
ros2 topic hz /scan             # sweep rate (10 Hz)
ros2 run neurobotics lidar_view.py   # live "mini radar" (below)
```

`lidar_view.py` groups the 360 beams into eight 45° sectors and prints
the nearest distance in each, twice a second — e.g.
`front:0.85m  f-left: -- m ... closest 0.85m at +12.3deg` (+ = left of
dead ahead, `--` = nothing in range). Beams that cross over the robot's
own chassis are filtered out. Point the robot at a box and watch the
front number shrink — this is exactly the signal `obstacle_avoid.py`
reacts to.

RViz can also draw the beams in 3D (see 4.7).

### 4.6 Velocity calibration — `calib_angular.py` / `calib_linear.py`

These run the same procedure you used on the real robot
(`04. angular velocity calibration` / `05. linear velocity calibration`
in the NeuroBotics repo): command a known motion, measure what the robot
actually did, and compute **scale = commanded / measured**.

```bash
ros2 run neurobotics calib_angular.py   # one commanded 360° turn
ros2 run neurobotics calib_linear.py    # one commanded 1 m straight line
```

- **Angular** measures the actual turn from the IMU (on the real robot
  that job is done by the IMU + EKF). Wheel odometry is printed too —
  during a pivot all four wheels skid, and wheel counters cannot see
  skidding, so the two numbers clearly disagree. On the real robot you
  would store the result in the firmware with
  `config_robot.py` → `set_ros_scale_angular` (yours was 1.05); in the
  simulation a wrong scale instead points at `wheel_separation` in
  `config/my_controllers.yaml`.
- **Linear** measures the actual distance travelled from Gazebo ground
  truth (the simulation's "tape measure"), with odometry printed for
  comparison. The real-robot equivalent is `set_ros_scale_line`; in the
  simulation a wrong scale points at `wheel_radius`.

**Pass:** both scales within 2 % of 1.0 (the sim should read ≈ 0.98–1.00;
start/stop transients cost a little).

### 4.7 RViz view (optional)

```bash
ros2 launch neurobotics gazebo.launch.py rviz:=true   # alongside the sim
# or, without Gazebo:
ros2 launch neurobotics display.launch.py             # sliders move every joint
```

RViz shows the robot model, TF frames, the lidar scan, odometry arrows and
the camera image.

## 5. Project structure

```
neurobotics_ws/
├── src/neurobotics/
│   ├── urdf/neurobotics.urdf      # the robot (SolidWorks export, cleaned up)
│   ├── launch/gazebo.launch.py    # sim + controllers (event-driven spawn)
│   ├── launch/display.launch.py   # RViz only
│   ├── config/my_controllers.yaml # diff_cont / joint_broad / arm_cont
│   ├── worlds/line.world          # floor, line course, 3 obstacle boxes
│   ├── rviz/neurobotics.rviz      # pre-configured RViz2 view
│   ├── scripts/                   # teleop / arm_gui / line_follow / obstacle_avoid
│   │                              # calib_angular / calib_linear / lidar_view
│   └── meshes/                    # STL files
└── README.md
```

## 6. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `package 'neurobotics' not found` | You forgot `source ~/neurobotics_ws/install/setup.bash` in this terminal |
| `parser error ... robot_description:=<?xml` on launch | A Humble bug with `gazebo_ros2_control` — already worked around in the launch files; don't hand-edit how `robot_description` is passed |
| `Desired controller update period (0.0333 s) is slower than the gazebo simulation period` | **Harmless warning.** Leave it |
| Camera only ~5 Hz | Normal without the Gazebo GUI (software rendering). With `gui:=true` it runs at ~20 Hz |
| `Moved backwards in time` / robot jumps | Two simulators are running. Run **one** `ros2 launch` at a time; `pkill -f "ros2 launch"` then `pkill -x gzserver`, wait 3 s, relaunch |
| Robot ignores a URDF/script edit, or drives crooked after many test runs | Leftover **background processes from earlier runs** still publishing (old `ros2 launch`es serve a stale `robot_description`, old scripts keep publishing `cmd_vel`). Check with `pgrep -af "ros2"` and kill them all — killing only the first PID you find is not enough |
| gzserver dies right after spawn | Leftover processes from a previous run — same cleanup as above, then relaunch |
| Line follower windows don't appear | The two debug windows need a display (run on the machine's desktop, not over plain SSH). Without one the follower still runs fine — you just get no preview |
| Robot slowly creeps/rotates while idle | A Gazebo solver artifact of the wheel contacts — it freezes the moment anything publishes `cmd_vel`, which every control script here does at startup. Harmless |
| Robot drove backward / wheels spun crazily | That was a physics-stability bug, now fixed. If you re-add wheel joint `damping`/`friction` or raise wheel `effort` above ~2 N·m it can come back — see the comments in `neurobotics.urdf` |
| Scripts print `[ERROR] Could not start ROS 2` | Source both setup files (`/opt/ros/humble` and the workspace) first |

## 7. What was fixed in this cleanup (2026-08)

For your reference — the interesting root causes:

1. **Camera link was missing** from the URDF (deleted during an earlier edit),
   so `line_follow.py` never had images. Restored with correct 45° mount.
2. **"Robot drives backward"** was *unstable wheel motors*, not wrong wiring:
   a 5 N·m velocity motor on the tiny wheel inertia overshoots every 1 ms
   physics step (one wheel was measured spinning at 52 rad/s with zero
   command). Fixed with effort 2 N·m, no joint damping/friction, and ×50
   wheel inertia (all documented inline in the URDF).
3. **Lidar + obstacle_avoid looked at the wrong beams**: the 360° scan starts
   at −180°, so slicing the array's edges read the robot's *rear*; the sensor
   also sat on the rear corner and saw its own arm. Sensor moved to the front
   frame and the script now selects beams by bearing.
4. **Launch files**: hardcoded paths → `$(find neurobotics)`, guessed sleep
   delays → controllers load on a spawn-complete event, XML comments are
   stripped before passing `robot_description` (Humble parser bug).
5. Scripts moved into the package (run with `ros2 run neurobotics ...`),
   rewritten with error handling and watchdogs; package.xml/CMakeLists
   completed; Bengali comments translated.
6. **The robot had two "cameras"** — a working one bolted to the chassis
   front and a dead DCW2 housing mesh on the arm. The real robot only has
   the arm camera, so the chassis camera was removed and the Gazebo sensor
   rebuilt on `arm4`, just behind the DCW2 housing. It now points **along
   the arm's tool axis** (the direction the gripper points), so the view
   physically follows the arm: arm straight = camera sees sky,
   `line_follow.py` bends the arm forward to aim it at the floor. It still
   publishes on `/camera/image_raw`, so RViz and any other listeners work
   unchanged. Gotcha discovered along the way: Gazebo's URDF→SDF conversion
   **drops any `<pose>` inside a sensor that hangs on a fixed-joint link**
   (the link gets welded into its parent and the sensor lands on the link
   origin — often inside a mesh). Sensors must sit on a link behind a real
   joint, like `arm4`.
7. **`wheel_separation` was 30 % wrong** in `my_controllers.yaml` (0.1955
   vs the URDF's true 0.15 m), so odometry under-reported every turn —
   the sim equivalent of an uncalibrated real robot. Fixed, and the new
   `calib_angular.py` would have caught it: it commands a 360° turn and
   compares the IMU against the wheels (during a pivot all four wheels
   skid, so wheel odometry over-reports by ~1.9× even when configured
   correctly — that gap is why the real robot fuses an IMU).
8. **An IMU sensor was added** to the URDF (`libgazebo_ros_imu_sensor`,
   `/imu`, 50 Hz). `obstacle_avoid.py` was rebuilt around it: steering
   away from the *side of the front sector* holding the nearest return
   (it used to always turn left), a heading latch so it resumes its
   original course after a dodge, and it refuses to drive before the
   first scan arrives.
9. **Calibration + lidar tools added** — `calib_angular.py`,
   `calib_linear.py` (the real-robot procedure, see 4.6) and
   `lidar_view.py` (sector view of `/scan`, see 4.5).

## 8. Where to go next

- Publish your first own node: echo the camera and threshold a colour
  (`ros2 topic echo /camera/image_raw --field width`)
- Try `rqt_image_view` to watch the camera comfortably
- Tune `line_follow.py`'s steering gains and watch the behaviour change
- Add a new static obstacle in `worlds/line.world` and re-test the avoider
