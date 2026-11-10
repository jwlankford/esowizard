import sys
from pathlib import Path

# Make ``fakes`` importable from tests in subdirectories.
sys.path.insert(0, str(Path(__file__).parent))
