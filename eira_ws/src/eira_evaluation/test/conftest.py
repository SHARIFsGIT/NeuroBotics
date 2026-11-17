"""Enable source imports without invoking DDS or hardware nodes.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX; hardware-free tests.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'eira_brain'))
