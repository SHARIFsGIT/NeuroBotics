#!/usr/bin/env bash
# E-AIRA Phase 0 - read-only inventory of the Yahboom factory image on the Jetson.
#
# WHAT IT DOES
#   Prints facts about the installed software to standard output: platform and
#   JetPack versions, ROS 2 apt packages, colcon workspaces and their packages
#   (version, build type, licence, git origin, source or binary), message and
#   service definitions, executables, launch/config files used by exercises
#   01-33, udev rules, enabled services and autostart entries, running ROS
#   processes, and calibration/map/model files.
#
# WHAT IT NEVER DOES
#   No sudo. No file is created, changed, moved or deleted. No ROS node, launch
#   file, service call or topic command is run. Serial ports, cameras and other
#   devices are never opened (only listed). Environment variables, passwords,
#   keys, tokens and network settings are not printed.
#   Exception, off by default: section 10 runs read-only ROS CLI graph queries
#   when EIRA_LIVE_GRAPH=1 is set; the ROS CLI then writes its own log files
#   under ~/.ros/log. Nothing is published and no service is called.
#
# HOW TO RUN (recommended: from the laptop, so nothing is written on the Jetson)
#   cd ~/NeuroBotics/eira_ws/docs/audit/jetson_inventory
#   ssh jetson@<jetson-host> 'bash -s' < jetson_readonly_inventory.sh \
#       > jetson_inventory_output.txt 2>&1
#   (ssh asks for the Jetson password; the output file is created on the laptop.)
#
# Typical run time on a Jetson Orin NX: 1-3 minutes.

main() {
  export LC_ALL=C PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0
  sec() { printf '\n### %s\n' "$*"; }
  # Source ROS and every workspace that ~/.bashrc sources, in the same order,
  # so the ament index matches what the exercises used. Sourcing only sets
  # environment variables inside the calling subshell.
  ros_env() {
    [ -f /opt/ros/humble/setup.bash ] && source /opt/ros/humble/setup.bash
    for f in $(grep -oE '[^ "'"'"']+/install/(local_)?setup\.bash' "$HOME/.bashrc" 2>/dev/null \
               | sed "s|^~|$HOME|; s|\$HOME|$HOME|"); do
      [ -f "$f" ] && source "$f" && echo "sourced $f"
    done
  }

  sec "0 RUN"
  date -u +%Y-%m-%dT%H:%M:%SZ
  echo "user=$(id -un) host=$(hostname) home=$HOME shell=$SHELL"

  sec "1 PLATFORM"
  tr -d '\0' < /proc/device-tree/model 2>/dev/null; echo
  head -n 2 /etc/nv_tegra_release 2>/dev/null
  lsb_release -ds 2>/dev/null
  uname -r
  dpkg-query -W -f='${Package}\t${Version}\n' 'nvidia-jetpack' 'nvidia-l4t-core' \
    'cuda-toolkit*' 'tensorrt' 'libnvinfer*' 'libcudnn*' 2>/dev/null | head -n 20
  nvpmodel -q 2>/dev/null | head -n 3
  free -m | head -n 2
  df -h / "$HOME" 2>/dev/null
  echo "cpus=$(nproc)"

  sec "2 PYTHON LIBRARIES (versions from metadata; packages are not imported)"
  python3 --version
  python3 - <<'PY'
import importlib.metadata as md
names = ["torch", "torchvision", "ultralytics", "tensorrt", "onnxruntime",
         "onnxruntime-gpu", "opencv-python", "opencv-contrib-python", "numpy",
         "mediapipe", "dt-apriltags", "transforms3d", "pyserial", "psutil", "PyQt5",
         "scipy", "pycuda", "jetson-stats", "openai-whisper", "sounddevice", "requests"]
for name in names:
    try:
        print(f"{name:24s} {md.version(name)}")
    except md.PackageNotFoundError:
        print(f"{name:24s} -")
PY
  timeout 60 python3 -c "import cv2; b=cv2.getBuildInformation(); print('cv2', cv2.__version__, [l.strip() for l in b.splitlines() if 'NVIDIA CUDA' in l][:1], 'aruco', hasattr(cv2, 'aruco'), 'TrackerVit', hasattr(cv2, 'TrackerVit_create'))" 2>&1 | tail -n 1
  timeout 90 python3 -c "import torch; print('torch', torch.__version__, 'cuda', torch.version.cuda, 'available', torch.cuda.is_available())" 2>&1 | tail -n 1
  timeout 60 python3 -c "import tensorrt as t; print('tensorrt', t.__version__)" 2>&1 | tail -n 1

  sec "3 ROS 2 APT PACKAGES"
  ls /opt/ros 2>&1
  echo "ros-humble-* packages installed: $(dpkg-query -W 'ros-humble-*' 2>/dev/null | wc -l)"
  dpkg-query -W -f='${Package}\t${Version}\n' 'ros-humble-*' 2>/dev/null \
    | grep -E 'nav2|navigation2|slam|cartographer|rtabmap|robot-localization|imu-|laser|ira|gmapping|orbbec|micro-ros|apriltag|joy|teleop|rqt-(graph|reconfigure|image)|rviz2|xacro|state-publisher|cv-bridge|tf-transformations|rosbridge|usb-cam|ros2-control|gazebo|rmw-' \
    | head -n 150

  sec "4 SHELL SETUP (ROS-related lines of ~/.bashrc only)"
  grep -nE '^\s*(source|\.)\s|ROS_|RMW_|CYCLONEDDS|FASTRTPS|FASTDDS|COLCON|AMENT_|PYTHONPATH|LD_LIBRARY_PATH|^\s*alias ' \
    "$HOME/.bashrc" 2>/dev/null | grep -viE 'key|token|pass|secret' | cut -c1-220
  ls -ld /root/M3Pro_ws /root 2>&1

  sec "5 DEVICES AND UDEV RULES (devices listed, never opened)"
  ls -l /dev/myserial /dev/rplidar /dev/ttyUSB* /dev/ttyACM* /dev/ttyCH* /dev/video* /dev/input/js* 2>&1 | head -n 40
  ls -l /dev/serial/by-id /dev/v4l/by-id 2>&1 | head -n 30
  lsusb 2>&1 | head -n 40
  for f in /etc/udev/rules.d/*.rules; do
    [ -f "$f" ] || continue
    echo "== $f"
    grep -vE '^\s*(#|$)' "$f" | cut -c1-250 | head -n 20
  done
  ls /lib/udev/rules.d 2>/dev/null | grep -iE 'orbbec|obsensor|astra|lidar|yahboom|ch34|cp210|serial' | head

  sec "6 SERVICES, AUTOSTART, CRON, DOCKER"
  systemctl list-unit-files --type=service --state=enabled --no-pager --no-legend 2>&1 | head -n 80
  echo "-- user services"
  systemctl --user list-unit-files --state=enabled --no-pager --no-legend 2>&1 | head -n 40
  for f in /etc/systemd/system/*.service "$HOME"/.config/systemd/user/*.service; do
    [ -f "$f" ] || continue
    if grep -qiE 'ros|yahboom|micro|agent|jetson|robot' "$f"; then
      echo "== $f"; grep -vE '^\s*(#|$)' "$f" | cut -c1-220 | head -n 30
    fi
  done
  echo "-- desktop autostart"
  ls -la "$HOME/.config/autostart" 2>&1 | head -n 30
  for f in "$HOME"/.config/autostart/*.desktop; do
    [ -f "$f" ] || continue
    echo "== $f"; grep -E '^(Name|Exec|Hidden|X-GNOME-Autostart-enabled)=' "$f" | cut -c1-220
  done
  echo "-- crontab"
  crontab -l 2>&1 | grep -vE '^\s*#' | head -n 20
  echo "-- docker"
  timeout 20 docker ps -a --format '{{.Names}}\t{{.Image}}\t{{.Status}}' 2>&1 | head -n 20
  timeout 20 docker images --format '{{.Repository}}:{{.Tag}}\t{{.Size}}' 2>&1 | head -n 20

  sec "7 RUNNING ROS / ROBOT PROCESSES"
  ps -eo pid,etimes,args --sort=pid 2>/dev/null \
    | grep -E 'ros|micro|agent|python3|ollama|docker|yahboom|orbbec' \
    | grep -vE 'grep -E|jetson_readonly_inventory|bash -s' | cut -c1-220 | head -n 60

  sec "8 OLLAMA"
  if command -v ollama >/dev/null 2>&1; then
    command -v ollama
    timeout 10 ollama --version 2>&1 | head -n 3
    timeout 15 ollama list 2>&1 | head -n 20
  else
    echo "ollama not installed"
  fi

  sec "9 WORKSPACES, PACKAGES, INTERFACES AND KEY FILES"
  (
    ros_env
    python3 - <<'PY'
import hashlib
import os
import re
import subprocess
import xml.etree.ElementTree as ET

HOME = os.path.expanduser("~")
SKIP = {"build", "install", "log", ".git", "__pycache__", "node_modules", ".cache"}


def hdr(text):
    print(f"\n## {text}", flush=True)


def git(path, *args):
    try:
        out = subprocess.run(["git", "-C", path, *args], capture_output=True, text=True,
                             timeout=10, stdin=subprocess.DEVNULL,
                             env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def clean_url(url):
    return re.sub(r"//[^@/\s]+@", "//", url)


def sha(path):
    try:
        with open(path, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()[:16]
    except OSError:
        return "-"


def show(path, limit=150, strip_comments=True):
    """Print a text file without comments, bounded in length."""
    try:
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    except OSError as exc:
        print(f"   (unreadable: {exc})")
        return
    kept = []
    for line in lines:
        bare = line.strip()
        if not bare:
            continue
        if strip_comments and (bare.startswith("#") or bare.startswith("<!--")):
            continue
        kept.append(line.rstrip()[:200])
    print(f"   [{len(lines)} lines, sha256 {sha(path)}]")
    for line in kept[:limit]:
        print("   " + line)
    if len(kept) > limit:
        print(f"   ... {len(kept) - limit} more non-comment lines")


# ---------------------------------------------------------------- workspaces
hdr("9.1 colcon workspaces under $HOME (install/setup.bash present)")
workspaces = []
for root, dirs, files in os.walk(HOME):
    depth = root[len(HOME):].count(os.sep)
    dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIP | {"src"}]
    if depth > 3:
        dirs[:] = []
    if os.path.isfile(os.path.join(root, "install", "setup.bash")):
        workspaces.append(root)
for ws in sorted(workspaces):
    src = os.path.join(ws, "src")
    print(f"{ws}  src={'yes' if os.path.isdir(src) else 'no'}  "
          f"git={clean_url(git(ws, 'remote', 'get-url', 'origin')) or '-'}")

hdr("9.2 source packages (one line per package.xml)")
print("ws | path | name | version | build_type | license | maintainer_domain | "
      "py/cpp/launch/yaml/urdf/msg+srv+action/so/pyc_only | LICENSE_file | git_origin @ commit")
src_index = {}
for ws in sorted(workspaces):
    src = os.path.join(ws, "src")
    if not os.path.isdir(src):
        continue
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in SKIP]
        if root[len(src):].count(os.sep) > 6:
            dirs[:] = []
        if "package.xml" not in files:
            continue
        try:
            xml = ET.parse(os.path.join(root, "package.xml")).getroot()
        except ET.ParseError:
            print(f"{ws} | {root} | (unparseable package.xml)")
            continue
        name = (xml.findtext("name") or "?").strip()
        version = (xml.findtext("version") or "?").strip()
        licenses = ";".join((e.text or "").strip() for e in xml.findall("license")) or "-"
        domains = ";".join(sorted({(e.get("email") or "").split("@")[-1]
                                   for e in xml.findall("maintainer")})) or "-"
        build_type = (xml.findtext("export/build_type") or
                      ("ament_python" if "setup.py" in files else "ament_cmake?")).strip()
        counts = dict(py=0, cpp=0, launch=0, yaml=0, urdf=0, iface=0, so=0, pyc=0)
        for r2, d2, f2 in os.walk(root):
            d2[:] = [d for d in d2 if d not in SKIP - {"__pycache__"}]
            for fname in f2:
                low = fname.lower()
                if low.endswith((".launch.py", "_launch.py", ".launch.xml", ".launch")):
                    counts["launch"] += 1
                elif low.endswith(".py"):
                    counts["py"] += 1
                elif low.endswith((".cpp", ".cc", ".c", ".hpp", ".h")):
                    counts["cpp"] += 1
                elif low.endswith((".yaml", ".yml", ".lua")):
                    counts["yaml"] += 1
                elif low.endswith((".urdf", ".xacro")):
                    counts["urdf"] += 1
                elif low.endswith((".msg", ".srv", ".action")):
                    counts["iface"] += 1
                elif low.endswith(".so") or ".so." in low:
                    counts["so"] += 1
                elif low.endswith(".pyc") and "__pycache__" not in r2:
                    counts["pyc"] += 1
        has_license = any(f.upper().startswith(("LICENSE", "COPYING")) for f in files)
        repo = root
        origin = ""
        while repo.startswith(src):
            if os.path.exists(os.path.join(repo, ".git")):
                origin = (clean_url(git(repo, "remote", "get-url", "origin")) or "local-git")
                origin += " @ " + (git(repo, "log", "-1", "--format=%h %cs") or "?")
                break
            repo = os.path.dirname(repo)
        print(f"{os.path.basename(ws)} | {os.path.relpath(root, src)} | {name} | {version} | "
              f"{build_type} | {licenses} | {domains} | "
              + "/".join(str(counts[k]) for k in ("py", "cpp", "launch", "yaml", "urdf",
                                                  "iface", "so", "pyc"))
              + f" | {'yes' if has_license else 'no'} | {origin or '-'}")
        src_index.setdefault(name, []).append(root)

hdr("9.3 packages present in install/ but without source in src/")
for ws in sorted(workspaces):
    inst = os.path.join(ws, "install")
    names = set()
    for entry in os.listdir(inst):
        if os.path.isdir(os.path.join(inst, entry, "share", entry)):
            names.add(entry)
    share = os.path.join(inst, "share")
    if os.path.isdir(share):
        names.update(d for d in os.listdir(share)
                     if os.path.isfile(os.path.join(share, d, "package.xml")))
    missing = sorted(n for n in names if n not in src_index)
    print(f"{ws}: {len(names)} installed, without source: {', '.join(missing) or 'none'}")

# --------------------------------------------------------------- ament index
try:
    from ament_index_python.packages import get_packages_with_prefixes
    prefixes = get_packages_with_prefixes()
except Exception as exc:  # noqa: BLE001 - report and continue
    prefixes = {}
    print(f"ament index unavailable: {exc}")

hdr("9.4 all packages NOT under /opt/ros (name -> prefix)")
for name, prefix in sorted(prefixes.items(), key=lambda kv: (kv[1], kv[0].lower())):
    if not prefix.startswith("/opt/ros"):
        print(f"{name:32s} {prefix}")

WANT = [
    "M3Pro_demo", "M3Pro_navigation", "m3pro_bringup", "M3Pro", "yahboomcar_ctrl",
    "calibration", "patrol", "yahboom_M3Pro_laser", "yahboom_laser_filter",
    "ira_laser_tools", "ekf_bringup", "imu_filter_madgwick", "robot_localization",
    "slam_mapping", "slam_view", "slam_gmapping", "openslam_gmapping", "cartographer_ros",
    "slam_toolbox", "rtabmap_launch", "rtabmap_ros", "rtabmap_slam", "nav2_bringup",
    "nav2_map_server", "apriltag_localization", "yahboom_nav2_bringup", "updatecostmap",
    "orbbec_camera", "orbbec_camera_msgs", "yahboom_M3Pro_DepthCam", "yahboom_yolov8",
    "smart_tracker", "arm_kin", "arm_util", "arm_msgs", "arm_interface",
    "micro_ros_agent", "micro_ros_msgs", "yahboom_mapping", "joy", "rqt_reconfigure",
    "rqt_graph", "rqt_image_view", "rviz2",
]

hdr("9.5 packages used by exercises 01-33: prefix, executables, share contents")
for name in WANT:
    prefix = prefixes.get(name)
    if prefix is None:
        print(f"\n{name}: NOT FOUND in ament index")
        continue
    lib = os.path.join(prefix, "lib", name)
    exes = []
    if os.path.isdir(lib):
        for entry in sorted(os.listdir(lib)):
            path = os.path.join(lib, entry)
            if os.path.isfile(path) and os.access(path, os.X_OK):
                try:
                    head = open(path, "rb").read(4)
                except OSError:
                    head = b""
                kind = "ELF" if head == b"\x7fELF" else ("script" if head[:2] == b"#!" else "other")
                exes.append(f"{entry}({kind})")
    share = os.path.join(prefix, "share", name)
    tree = []
    if os.path.isdir(share):
        for entry in sorted(os.listdir(share)):
            path = os.path.join(share, entry)
            if os.path.isdir(path):
                kids = sorted(os.listdir(path))
                tree.append(f"{entry}/[{', '.join(kids[:14])}{', ...' if len(kids) > 14 else ''}]")
            else:
                tree.append(entry)
    print(f"\n{name}: prefix={prefix} source={';'.join(src_index.get(name, [])) or '-'}")
    print(f"   executables: {', '.join(exes) or '-'}")
    print(f"   share: {' '.join(tree)[:900] or '-'}")

hdr("9.6 message / service / action definitions outside /opt/ros")
for name, prefix in sorted(prefixes.items()):
    if prefix.startswith("/opt/ros"):
        continue
    share = os.path.join(prefix, "share", name)
    for kind in ("msg", "srv", "action"):
        folder = os.path.join(share, kind)
        if not os.path.isdir(folder):
            continue
        for fname in sorted(os.listdir(folder)):
            if fname.endswith("." + kind):
                path = os.path.join(folder, fname)
                body = [ln.strip() for ln in open(path, encoding="utf-8", errors="replace")
                        if ln.strip() and not ln.strip().startswith("#")]
                print(f"{name}/{kind}/{fname[:-len(kind) - 1]}: " + " | ".join(body)[:400])


def find_file(pkg, rel):
    candidates = []
    if pkg in prefixes:
        candidates.append(os.path.join(prefixes[pkg], "share", pkg, rel))
    for root in src_index.get(pkg, []):
        candidates.append(os.path.join(root, rel))
    for cand in candidates:
        if os.path.isfile(cand):
            return cand
    return None


hdr("9.7 key configuration and launch files")
FILES = [
    ("m3pro_bringup", "launch/static_tf.launch.py", 120),
    ("m3pro_bringup", "config/common.yaml", 150),
    ("m3pro_bringup", "config/aritag_relocation.yaml", 60),
    ("m3pro_bringup", "launch/apriltag_relocalization.launch.py", 80),
    ("M3Pro", "launch/display.launch.py", 60),
    ("ira_laser_tools", "config/laserscan_merge.yaml", 60),
    ("yahboom_laser_filter", "launch/laser_filter_node.launch.py", 40),
    ("ekf_bringup", "launch/ekf.launch.py", 60),
    ("imu_filter_madgwick", "launch/imu_filter.launch.py", 60),
    ("M3Pro_navigation", "launch/bringup_mod.launch.py", 40),
    ("slam_mapping", "launch/online_async_launch.py", 40),
    ("slam_mapping", "launch/localization_launch.py", 40),
    ("orbbec_camera", "package.xml", 25),
]
for pkg, rel, limit in FILES:
    path = find_file(pkg, rel)
    print(f"\n-- {pkg}/{rel}: {path or 'NOT FOUND'}")
    if path:
        show(path, limit)

hdr("9.8 parameter and data directories of navigation, mapping and EKF packages")
for pkg in ("M3Pro_navigation", "slam_mapping", "ekf_bringup", "imu_filter_madgwick",
            "m3pro_bringup", "arm_kin"):
    for folder in ("param", "params", "config", "map", "maps", "rviz", "urdf"):
        for base in ([os.path.join(prefixes[pkg], "share", pkg)] if pkg in prefixes else []) \
                + src_index.get(pkg, []):
            path = os.path.join(base, folder)
            if os.path.isdir(path):
                entries = []
                for entry in sorted(os.listdir(path)):
                    full = os.path.join(path, entry)
                    if os.path.isfile(full):
                        entries.append(f"{entry}({os.path.getsize(full)}B,{sha(full)[:8]})")
                print(f"{pkg}/{folder} @ {path}: {', '.join(entries)[:900]}")
                break

hdr("9.9 Nav2 parameters: key lines")
for rel in ("param/yahboom_M3Pro.yaml", "param/yahboom_M3Pro_carto.yaml"):
    path = find_file("M3Pro_navigation", rel)
    print(f"\n-- M3Pro_navigation/{rel}: {path or 'NOT FOUND'} sha256={sha(path) if path else '-'}")
    if not path:
        continue
    pattern = re.compile(r"(plugin|robot_base_frame|global_frame|odom_frame_id|base_frame_id|"
                         r"footprint|robot_radius|max_vel|min_vel|max_speed|max_accel|"
                         r"odom_topic|scan_topic|topic:|robot_model_type|transform_tolerance|"
                         r"controller_frequency|holonomic|use_sim_time|default_nav|"
                         r"inflation_radius|resolution)")
    for number, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
        if pattern.search(line) and not line.strip().startswith("#"):
            print(f"   {number:4d} {line.rstrip()[:160]}")

hdr("9.10 EKF / IMU filter / merger parameter files (full, without comments)")
for pkg in ("ekf_bringup", "imu_filter_madgwick"):
    for base in ([os.path.join(prefixes[pkg], "share", pkg)] if pkg in prefixes else []):
        for folder in ("config", "param", "params"):
            path = os.path.join(base, folder)
            if os.path.isdir(path):
                for entry in sorted(os.listdir(path)):
                    if entry.endswith((".yaml", ".yml")):
                        print(f"\n-- {pkg}/{folder}/{entry}")
                        show(os.path.join(path, entry), 120)

hdr("9.11 URDF of the real robot (M3Pro): joint summary")
urdf = find_file("M3Pro", "urdf/m3pro.urdf")
print(f"path={urdf} sha256={sha(urdf) if urdf else '-'}")
if urdf:
    try:
        robot = ET.parse(urdf).getroot()
        print(f"robot={robot.get('name')} links={len(robot.findall('link'))}")
        for joint in robot.findall("joint"):
            origin, limit = joint.find("origin"), joint.find("limit")
            print("   {:22s} {:10s} {:16s} -> {:16s} xyz={} rpy={} lim={}".format(
                joint.get("name"), joint.get("type"), joint.find("parent").get("link"),
                joint.find("child").get("link"),
                origin.get("xyz") if origin is not None else None,
                origin.get("rpy") if origin is not None else None,
                (limit.get("lower"), limit.get("upper")) if limit is not None else None))
    except ET.ParseError as exc:
        print(f"unparseable (xacro?): {exc}")

hdr("9.12 who uses the raw robot topics (static search of workspace sources)")
TOPICS = ["scan0", "scan1", "imu/data_raw", "odom_raw", "vel_raw", "arm6_joints",
          "arm_status", "Curjoints", "JoyState", "/beep", "edition", "voltage"]
EXT = (".py", ".cpp", ".hpp", ".h", ".c", ".yaml", ".xml", ".lua")
hits = {topic: [] for topic in TOPICS}
for name, roots in src_index.items():
    for root in roots:
        for r2, d2, f2 in os.walk(root):
            d2[:] = [d for d in d2 if d not in SKIP]
            for fname in f2:
                if not fname.endswith(EXT):
                    continue
                path = os.path.join(r2, fname)
                try:
                    if os.path.getsize(path) > 2_000_000:
                        continue
                    text = open(path, encoding="utf-8", errors="replace").read().splitlines()
                except OSError:
                    continue
                for number, line in enumerate(text, 1):
                    for topic in TOPICS:
                        if topic in line and len(hits[topic]) < 10:
                            hits[topic].append(f"{name}:{os.path.relpath(path, root)}:{number}: "
                                               f"{line.strip()[:120]}")
for topic, found in hits.items():
    print(f"\n-- '{topic}': {len(found)} hit(s){' (first 10)' if len(found) == 10 else ''}")
    for item in found:
        print("   " + item)
lidar_like = sorted({n for n in src_index if re.search(
    r"lidar|ldlidar|oradar|sllidar|ydlidar|rplidar|ms200|lds|ls01|laser_driver", n, re.I)})
print(f"\nLiDAR-like source packages: {', '.join(lidar_like) or 'none'}")

hdr("9.13 arm kinematics, arm status, calibration and laser filter sources (key lines)")
PATTERN = re.compile(r"create_(publisher|subscription|service|client)|declare_parameter|"
                     r"serial\.Serial|/dev/|\.yaml|urdf|kdl|ikfast|offset|scale|"
                     r"set_ros_scale|write|open\(")
for pkg in ("arm_kin", "arm_util", "calibration", "yahboom_laser_filter", "updatecostmap",
            "yahboom_nav2_bringup"):
    for root in src_index.get(pkg, [])[:1]:
        print(f"\n-- {pkg} @ {root}")
        for r2, d2, f2 in os.walk(root):
            d2[:] = [d for d in d2 if d not in SKIP]
            for fname in sorted(f2):
                if not fname.endswith((".py", ".cpp", ".hpp", ".h")):
                    continue
                path = os.path.join(r2, fname)
                shown = 0
                for number, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
                    bare = line.strip()
                    if bare.startswith(("#", "//")) or not PATTERN.search(bare):
                        continue
                    if shown == 0:
                        print(f"   {os.path.relpath(path, root)}")
                    print(f"      {number:4d} {bare[:140]}")
                    shown += 1
                    if shown >= 25:
                        break

hdr("9.14 calibration, map, model and helper files used by the exercises")
for pkg, rel in (("arm_kin", "param/offset_value.yaml"),
                 ("M3Pro_demo", "M3Pro_demo/LineFollowHSV.text"),
                 ("M3Pro_demo", "LineFollowHSV.text")):
    for root in src_index.get(pkg, []):
        path = os.path.join(root, rel)
        if os.path.isfile(path):
            print(f"\n-- {path}")
            show(path, 30)
for path in ("~/start_agent.sh", "~/joy_control", "~/mircoROS_agent", "~/map", "~/MODELS",
             "~/MODELS/tracker", "~/yahboom_map.pbstream", "~/rtabmap.db", "~/.ros/rtabmap.db",
             "~/yahboomcar_ws/src/yahboom_yolov8/yahboom_yolov8/yolov8/weights"):
    full = os.path.expanduser(path)
    if os.path.isdir(full):
        entries = sorted(os.listdir(full))
        print(f"{path}/ : " + ", ".join(
            f"{e}({os.path.getsize(os.path.join(full, e))}B)" if os.path.isfile(os.path.join(full, e))
            else e + "/" for e in entries[:40]))
    elif os.path.isfile(full):
        print(f"{path} : file {os.path.getsize(full)} B, sha256 {sha(full)}")
    else:
        print(f"{path} : absent")
agent = os.path.expanduser("~/start_agent.sh")
if os.path.isfile(agent):
    print("\n-- ~/start_agent.sh (non-comment lines)")
    show(agent, 20)

hdr("9.15 E-AIRA already on this machine (~/eira_ws): file hashes for comparison with the laptop")
eira_root = os.path.expanduser("~/eira_ws")
eira_src = os.path.join(eira_root, "src")
if os.path.isdir(eira_src):
    print(f"git origin: {clean_url(git(eira_root, 'remote', 'get-url', 'origin')) or '-'}  "
          f"commit: {git(eira_root, 'log', '-1', '--format=%h %cs') or '-'}")
    count = 0
    for r2, d2, f2 in os.walk(eira_src):
        d2[:] = sorted(d for d in d2 if d not in SKIP)
        for fname in sorted(f2):
            if fname.endswith((".py", ".yaml", ".xml", ".rviz", ".cfg", ".world", ".pgm", ".md")):
                path = os.path.join(r2, fname)
                print(f"   {sha(path)[:12]} {os.path.relpath(path, eira_src)}")
                count += 1
    print(f"   {count} files")
else:
    print("~/eira_ws/src absent")
for extra in ("~/NeuroBotics", "~/eira_ws/install", "~/eira_ws/results", "~/eira_ws/bags"):
    print(f"{extra}: {'present' if os.path.exists(os.path.expanduser(extra)) else 'absent'}")
PY
  )

  sec "10 OPTIONAL LIVE ROS GRAPH (runs only with EIRA_LIVE_GRAPH=1)"
  if [ "${EIRA_LIVE_GRAPH:-0}" = "1" ]; then
    # Lists who publishes and subscribes. Publishes nothing and calls nothing,
    # but the ROS CLI writes its own log files under ~/.ros/log. Needs the
    # micro-ROS agent running so the controller board's topics are visible.
    (
      ros_env
      dom=$(grep -oE 'ROS_DOMAIN_ID=[0-9]+' "$HOME/.bashrc" 2>/dev/null | tail -n 1 | cut -d= -f2)
      export ROS_DOMAIN_ID="${dom:-30}"
      echo "ROS_DOMAIN_ID=$ROS_DOMAIN_ID"
      timeout 40 ros2 node list --no-daemon --spin-time 3 2>&1 | head -n 80
      timeout 40 ros2 topic list -t --no-daemon --spin-time 3 2>&1 | head -n 150
      for t in /arm6_joints /arm_joint /scan0 /scan1 /scan /imu/data_raw /imu /odom_raw /odom \
               /cmd_vel /beep /rgb /JoyState /Curjoints /arm_status/arm_joint; do
        echo "-- $t"
        timeout 25 ros2 topic info -v "$t" --no-daemon 2>&1 \
          | grep -E 'Type:|Node name:|Endpoint type:|Reliability:|Publisher count|Subscription count' \
          | head -n 16
      done
    )
  else
    echo "skipped. To include it: ssh jetson@<jetson-host> 'EIRA_LIVE_GRAPH=1 bash -s' < jetson_readonly_inventory.sh"
    echo "(writes ROS CLI log files under ~/.ros/log; run while the micro-ROS agent is running)"
  fi

  sec "END"
}

main "$@" < /dev/null
