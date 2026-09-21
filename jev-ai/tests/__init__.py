# Jev AI test package

import sys
from pathlib import Path

# Ensure parent directory is in path for imports
APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
