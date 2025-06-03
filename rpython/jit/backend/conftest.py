import pytest
import sys
from rpython.jit.backend import detect_cpu

cpu = detect_cpu.autodetect()
IS_ARM64 = cpu.startswith('aarch64')
IS_MACOS = sys.platform == 'darwin'
IS_PYPY = 'pypyjit' in sys.builtin_module_names

# disable the JIT when collecting
if IS_ARM64 and IS_MACOS and IS_PYPY:
    import pypyjit
    pypyjit.set_param("off")
