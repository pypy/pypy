import pytest
import platform

if not platform.machine().startswith('x86'):
    pytest.skip()
