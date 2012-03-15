import py, os
from pypy.jit.backend import detect_cpu

cpu = detect_cpu.autodetect()
def pytest_runtest_setup(item):
    if cpu not in ('x86', 'x86_64'):
        py.test.skip("x86/x86_64 tests skipped: cpu is %r" % (cpu,))
    if cpu == 'x86_64':
        if os.name == "nt":
            py.test.skip("Windows cannot allocate non-reserved memory")
        from pypy.rpython.lltypesystem import ll2ctypes
        ll2ctypes.do_allocation_in_far_regions()
