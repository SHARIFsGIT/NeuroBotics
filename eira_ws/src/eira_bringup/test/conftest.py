"""Enable source imports for bringup unit tests.

Author: E-AIRA maintainers.
Hardware target: Jetson Orin NX / ROS 2 Humble; tests run without hardware.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'eira_brain'))
