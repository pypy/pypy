import sys
import pytest

if sys.platform == "win32":
    pytest.skip("not on windows", allow_module_level=True)

