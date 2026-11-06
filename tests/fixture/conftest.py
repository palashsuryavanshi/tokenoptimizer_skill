import sys
from pathlib import Path

FIXTURE_ROOT = Path(__file__).resolve().parent
if str(FIXTURE_ROOT) not in sys.path:
    sys.path.insert(0, str(FIXTURE_ROOT))
