"""
Common utilities for backend scripts.

This module sets up the Python path for script execution and provides
shared utilities. Import this module at the top of any script that needs
to import from the backend package.

Usage:
    import scripts._common  # noqa: F401
    # Now you can import from db, models, services, etc.
"""

import sys
from pathlib import Path

# Add backend root to path for imports
# This allows scripts to be run directly (python scripts/foo.py)
# without needing to be run as modules (python -m scripts.foo)
BACKEND_ROOT = Path(__file__).parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
