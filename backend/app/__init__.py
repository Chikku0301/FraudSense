import sys
import os

# Ensure both backend directory and project root directory are on sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_current_dir)
_root_dir = os.path.dirname(_backend_dir)

for _p in [_root_dir, _backend_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
