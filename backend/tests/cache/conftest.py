"""pytest configuration for cache tests.

Cache tests are pure unit tests with no database dependencies.
This conftest prevents loading the parent conftest.py which requires database setup.
"""

import pytest
import sys
from pathlib import Path

# Add parent to path for cache module imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
