import pytest
import platform

if not (platform.machine() in ('x86_64', 'aarch64', 'arm64', 'riscv64')):
    pytest.skip()
