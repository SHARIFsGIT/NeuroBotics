"""Enable source-tree perception tests.

Author: E-AIRA contributors. Hardware target: Jetson Orin NX, ROSMASTER M3 Pro.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'eira_brain'))
