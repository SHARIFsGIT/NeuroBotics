# Make the package importable without a colcon install (pytest from source).
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
