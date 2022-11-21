import pytest
import platform

if not (platform.machine() in ('x86', 'aarch64', 'arm64')):
    pytest.skip()
