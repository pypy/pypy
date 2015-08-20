import py
from rpython.jit.backend import detect_cpu

cpu = detect_cpu.autodetect()
def pytest_runtest_setup(item):
    if cpu != detect_cpu.MODEL_X86_64:
        py.test.skip("x86_64 tests only")
