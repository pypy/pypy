import os
import pytest
from rpython.jit.backend import detect_cpu

cpu = detect_cpu.autodetect()
IS_X86 = cpu.startswith('x86')
THIS_DIR = os.path.dirname(__file__)

@pytest.hookimpl(tryfirst=True)
def pytest_ignore_collect(path, config):
    path = str(path)
    if not IS_X86:
        if os.path.commonprefix([path, THIS_DIR]) == THIS_DIR:  # workaround for bug in pytest<3.0.5
            return True

def pytest_collect_file():
    if not IS_X86:
        # We end up here when calling py.test .../test_foo.py with a wrong cpu
        # It's OK to kill the whole session with the following line
        pytest.skip("X86 tests skipped: cpu is %r" % (cpu,))

def pytest_runtest_setup(item):
    if cpu == 'x86_64':
        if os.name == "nt":
            pytest.skip("Windows cannot allocate non-reserved memory")
        from rpython.rtyper.lltypesystem import ll2ctypes
        ll2ctypes.do_allocation_in_far_regions()
